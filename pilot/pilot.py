"""email-Eu-core pilot for the IC-PBL project.

A fast first pass over every analysis in the 과제수행계획서, so the team can see which
hypotheses hold before the final presentation:
  1. structure and department homophily                  (hypothesis 2)
  2. centrality, maximal cliques, k-core                 (hypothesis 1)
  3. key-player removal vs degree / random baselines     (hypothesis 1)
  4. DeepWalk / node2vec embeddings -> LogReg, RandomForest (hypotheses 2, 3)
  5. 2-layer GCN (plain numpy) on the same folds         (hypothesis 3)

Skip-gram (negative sampling) and the GCN are implemented in numpy so the script needs only
numpy, scipy, scikit-learn, matplotlib and networkx. When networkx is not installed for the
interpreter, set NX_PATH to a directory that contains the networkx package.

Usage:  python pilot.py <data_dir> <out_dir>
"""
import gzip
import json
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import parent_process
from pathlib import Path

# cap BLAS threads before numpy loads: workers run single-threaded so the pool does not oversubscribe the CPU
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1" if parent_process() is not None else "8")

import numpy as np

try:
    import networkx as nx
except ImportError:
    sys.path.append(os.environ["NX_PATH"])
    import networkx as nx

SEED = 0
N_FOLDS = 5
MIN_CLASS = 5  # departments with fewer LCC members are left out of classification
WALKS = dict(num_walks=10, length=80)
SGNS = dict(dim=128, window=10, neg=5, lr=0.025, batch=512)
N2V_CONFIGS = {"deepwalk": (1.0, 1.0), "node2vec_p1_q0.5": (1.0, 0.5), "node2vec_p1_q2": (1.0, 2.0)}
EMB_SEEDS = (0, 1, 2)  # embedding seeds, to see whether DeepWalk vs node2vec gaps exceed seed noise
GCN = dict(hidden=64, dropout=0.5, lr=0.01, wd=5e-4, epochs=200)
REMOVAL_KS = list(range(0, 501))  # removal runs on the LCC (986 nodes); step 1 so thresholds are exact
ADAPTIVE_MAX_K, ADAPTIVE_BATCH = 400, 10
RANDOM_REPEATS = 20
NULL_SHUFFLES = 200

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------- data

def load(data_dir):
    d = Path(data_dir)
    with gzip.open(d / "email-Eu-core.txt.gz", "rt") as f:
        edges = [tuple(map(int, ln.split())) for ln in f if ln.strip()]
    with gzip.open(d / "email-Eu-core-department-labels.txt.gz", "rt") as f:
        labels = dict(tuple(map(int, ln.split())) for ln in f if ln.strip())
    return edges, labels


def undirected(n, edges):
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from((u, v) for u, v in edges if u != v)
    return G


# ---------------------------------------------------------------- 1. structure, homophily

def structure(edges, labels, G):
    n = len(labels)
    DG = nx.DiGraph()
    DG.add_nodes_from(range(n))
    DG.add_edges_from(edges)
    loops = nx.number_of_selfloops(DG)
    DG.remove_edges_from(list(nx.selfloop_edges(DG)))
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    lcc = comps[0]
    H = G.subgraph(lcc)
    diameter, total, pairs = 0, 0, 0
    for s in H:
        dist = nx.single_source_shortest_path_length(H, s)
        diameter = max(diameter, max(dist.values()))
        total += sum(dist.values())
        pairs += len(dist) - 1
    sizes = Counter(labels.values())
    lcc_sizes = Counter(labels[v] for v in lcc)
    m = G.number_of_edges()
    return {
        "nodes": n,
        "directed_edge_lines": len(edges),
        "self_loops": loops,
        "directed_edges_no_loops": DG.number_of_edges(),
        "reciprocity": nx.reciprocity(DG),
        "largest_scc": len(max(nx.strongly_connected_components(DG), key=len)),
        "undirected_edges": m,
        "density": nx.density(G),
        "mean_degree": 2 * m / n,
        "max_degree": max(d for _, d in G.degree()),
        "avg_clustering": nx.average_clustering(G),
        "triangles": sum(nx.triangles(G).values()) // 3,
        "components": len(comps),
        "lcc_nodes": len(lcc),
        "isolated_nodes": sum(1 for v in G if G.degree(v) == 0),
        "lcc_diameter": diameter,
        "lcc_avg_shortest_path": total / pairs,
        "departments": len(sizes),
        "dept_sizes_desc": sorted(sizes.values(), reverse=True),
        "depts_lt5": sum(1 for s in sizes.values() if s < 5),
        "depts_lt10": sum(1 for s in sizes.values() if s < 10),
        "depts_lt5_in_lcc": sum(1 for d in sizes if lcc_sizes.get(d, 0) < 5),
    }, lcc


def homophily(G, labels, edges, lcc):
    m = G.number_of_edges()
    same = sum(labels[u] == labels[v] for u, v in G.edges())
    vol = Counter()
    for v, d in G.degree():
        vol[labels[v]] += d
    expected = sum((x / (2 * m)) ** 2 for x in vol.values())
    directed = [(u, v) for u, v in set(edges) if u != v]
    per_node = np.array([sum(labels[u] == labels[v] for u in G[v]) / G.degree(v) for v in G if G.degree(v)])
    # null model: same graph, department labels shuffled across nodes (department sizes kept)
    rng = np.random.default_rng(SEED)
    eu = np.array(list(G.edges()))
    lab = np.array([labels[v] for v in range(len(labels))])
    null = np.array([(p[eu[:, 0]] == p[eu[:, 1]]).mean() for p in (rng.permutation(lab) for _ in range(NULL_SHUFFLES))])
    depts = {}
    for v in lcc:
        depts.setdefault(labels[v], set()).add(v)
    return {
        "edge_homophily": same / m,
        "expected_if_random": expected,
        "shuffled_label_null_mean": float(null.mean()),
        "shuffled_label_null_std": float(null.std()),
        "z_vs_shuffled_null": float((same / m - null.mean()) / null.std()),
        "dept_modularity_lcc": nx.community.modularity(G.subgraph(lcc), list(depts.values())),
        "directed_edge_homophily": sum(labels[u] == labels[v] for u, v in directed) / len(directed),
        "assortativity": nx.attribute_assortativity_coefficient(G, "dept"),
        "node_homophily_mean": float(per_node.mean()),
        "node_homophily_median": float(np.median(per_node)),
        "share_nodes_majority_same_dept": float((per_node > 0.5).mean()),
    }


# ---------------------------------------------------------------- 2. centrality, cliques

def centrality(G, labels):
    deg = nx.degree_centrality(G)
    clo = nx.closeness_centrality(G)
    btw = nx.betweenness_centrality(G)
    active = [v for v in G if G.degree(v)]

    def cross(v):
        return sum(labels[u] != labels[v] for u in G[v]) / G.degree(v)

    def row(v):
        return {"node": v, "dept": labels[v], "degree": G.degree(v), "betweenness": round(btw[v], 4),
                "closeness": round(clo[v], 4), "neighbour_depts": len({labels[u] for u in G[v]}),
                "cross_dept_frac": round(cross(v), 3)}

    from scipy.stats import spearmanr
    top_b = sorted(G, key=btw.get, reverse=True)[:10]
    top_d = sorted(G, key=deg.get, reverse=True)[:10]
    top_c = sorted(G, key=clo.get, reverse=True)[:10]
    return {
        "top10_betweenness": [row(v) for v in top_b],
        "top10_degree": [row(v) for v in top_d],
        "overlap_top10_betweenness_degree": len(set(top_b) & set(top_d)),
        "overlap_top10_betweenness_closeness": len(set(top_b) & set(top_c)),
        "spearman_betweenness_degree": float(spearmanr([btw[v] for v in active], [deg[v] for v in active])[0]),
        "betweenness_share_top10": sum(btw[v] for v in top_b) / sum(btw.values()),
        "top10_betweenness_distinct_depts": len({labels[v] for v in top_b}),
        "cross_dept_frac_mean_all": float(np.mean([cross(v) for v in active])),
        "cross_dept_frac_mean_top10_betweenness": float(np.mean([cross(v) for v in top_b])),
        "cross_dept_frac_mean_top10_degree": float(np.mean([cross(v) for v in top_d])),
        "neighbour_depts_mean_top10_degree": float(np.mean([len({labels[u] for u in G[v]}) for v in top_d])),
        "neighbour_depts_mean_all": float(np.mean([len({labels[u] for u in G[v]}) for v in active])),
        "neighbour_depts_mean_top10_betweenness": float(np.mean([len({labels[u] for u in G[v]}) for v in top_b])),
    }, btw, deg


def clique_task(n, edge_list, labels, time_cap=240):
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edge_list)
    t0 = time.time()
    hist, largest, purities, complete = Counter(), [], [], True

    def purity(c):
        return Counter(labels[v] for v in c).most_common(1)[0][1] / len(c)

    for i, c in enumerate(nx.find_cliques(G), 1):
        hist[len(c)] += 1
        if len(c) >= 3:
            purities.append(purity(c))
            if not largest or len(c) > len(largest[0]):
                largest = [c]  # keep every clique of the maximum size, not a sample
            elif len(c) == len(largest[0]):
                largest.append(c)
        if i % 5000 == 0 and time.time() - t0 > time_cap:
            complete = False
            break
    top_purity = np.array([purity(c) for c in largest])
    lead = Counter(Counter(labels[v] for v in c).most_common(1)[0][0] for c in largest)
    core = nx.core_number(G)
    kmax = max(core.values())
    kcore = [v for v, k in core.items() if k == kmax]
    return {
        "maximal_cliques_total": sum(hist.values()),
        "maximal_cliques_size_ge3": sum(c for s, c in hist.items() if s >= 3),
        "max_clique_size": max(hist),
        "clique_size_hist": dict(sorted(hist.items())),
        "mean_dept_purity_size_ge3": float(np.mean(purities)),
        "share_pure_cliques_size_ge3": float(np.mean(np.array(purities) == 1.0)),
        "max_size_cliques": {"count": len(largest), "distinct_nodes": len(set().union(*map(set, largest))),
                             "purity_mean": round(float(top_purity.mean()), 3),
                             "purity_median": round(float(np.median(top_purity)), 3),
                             "share_purity_ge_0.8": round(float((top_purity >= 0.8).mean()), 3),
                             "leading_dept_counts": dict(lead.most_common(5))},
        "enumeration_complete": complete,
        "seconds": round(time.time() - t0, 1),
        "max_kcore": kmax,
        "max_kcore_nodes": len(kcore),
        "max_kcore_distinct_depts": len({labels[v] for v in kcore}),
    }


# ---------------------------------------------------------------- 3. key-player removal

def comp_stats(H, n):
    """(largest component / n, second-largest component / n, number of components)."""
    sizes = sorted((len(c) for c in nx.connected_components(H)), reverse=True) + [0, 0]
    return sizes[0] / n, sizes[1] / n, len(sizes) - 2


def curve_static(G, order, n):
    H, out, done = G.copy(), [], 0
    for k in REMOVAL_KS:
        H.remove_nodes_from(order[done:k])
        done = k
        out.append((k, *comp_stats(H, n)))
    return out


def curve_adaptive_degree(G, n):
    H, out, done = G.copy(), [], 0
    for k in REMOVAL_KS:
        while done < k:
            H.remove_node(max(H.degree, key=lambda x: x[1])[0])
            done += 1
        out.append((k, *comp_stats(H, n)))
    return out


def adaptive_betweenness_task(nodes, edge_list):
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edge_list)
    n = len(nodes)
    out, removed = [(0, *comp_stats(G, n))], []
    while len(removed) < ADAPTIVE_MAX_K:
        b = nx.betweenness_centrality(G)
        top = sorted(b, key=b.get, reverse=True)[:ADAPTIVE_BATCH]
        G.remove_nodes_from(top)
        removed += top
        out.append((len(removed), *comp_stats(G, n)))
    return {"curve": out, "removed": removed}


def removal_summary(curve, n):
    lookup = {c[0]: c[1] for c in curve}
    half = next((c[0] for c in curve if c[1] < 0.5), None)
    peak = max(curve, key=lambda c: c[2])  # q_c: where the second-largest component peaks
    return {"lcc_at": {f"{k} ({k / n:.0%})": round(lookup[k], 3) for k in (10, 50, 100, 200, 300) if k in lookup},
            "components_at_100": next((c[3] for c in curve if c[0] == 100), None),
            "k_when_lcc_below_half": half if half is not None else f"not reached by k={curve[-1][0]}",
            "q_when_lcc_below_half": round(half / n, 3) if half is not None else None,
            "lcc_over_remaining_at_300": round(lookup[300] / (1 - 300 / n), 3) if 300 in lookup else None,
            "second_component_peak": {"k": peak[0], "q": round(peak[0] / n, 3), "size_frac": round(peak[2], 3)},
            "range_covered_q": round(curve[-1][0] / n, 3)}


def plot_removal(curves, rand, n, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ks = np.array(REMOVAL_KS) / n
    ax.fill_between(ks, rand.min(0), rand.max(0), color="0.8", label="random (min–max, 20 runs)")
    ax.plot(ks, rand.mean(0), color="0.4", lw=1.5, label="random (mean)")
    ax.plot(ks, 1 - ks, color="0.55", ls=":", lw=1, label="removal alone: (N-k)/N")
    for name, curve in curves.items():
        color = "tab:blue" if name.startswith("degree") else "tab:red"
        ls = "-" if "adaptive" in name else "--"
        ax.plot([c[0] / n for c in curve], [c[1] for c in curve], color=color, ls=ls, lw=1.8, label=name)
    ax.set_xlabel("fraction of LCC nodes removed")
    ax.set_ylabel("largest connected component / N")
    ax.set_title(f"email-Eu-core: key-player removal (undirected LCC, N={n})")
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 4. embeddings

def make_walks(adj, start_nodes, p, q, num_walks, length, seed):
    rnd = random.Random(seed)
    nbr_sets = [set(a) for a in adj]
    uniform = p == 1 and q == 1
    wmax = max(1 / p, 1.0, 1 / q)
    walks = np.empty((num_walks * len(start_nodes), length), dtype=np.int64)
    row = 0
    for _ in range(num_walks):
        order = list(start_nodes)
        rnd.shuffle(order)
        for s in order:
            nb = adj[s]
            walk = [s, nb[int(rnd.random() * len(nb))]]
            while len(walk) < length:
                prev, cur = walk[-2], walk[-1]
                nb = adj[cur]
                if uniform:
                    walk.append(nb[int(rnd.random() * len(nb))])
                    continue
                pset = nbr_sets[prev]
                while True:  # rejection sampling of the node2vec 2nd-order transition
                    x = nb[int(rnd.random() * len(nb))]
                    w = 1 / p if x == prev else (1.0 if x in pset else 1 / q)
                    if rnd.random() * wmax < w:
                        break
                walk.append(x)
            walks[row] = walk
            row += 1
    return walks


def sgns(walks, n, dim, window, neg, lr, batch, seed):
    """Skip-gram with negative sampling, mini-batch SGD with linear learning-rate decay."""
    rng = np.random.default_rng(seed)
    w_in = ((rng.random((n, dim)) - 0.5) / dim).astype(np.float32)
    w_out = np.zeros((n, dim), np.float32)
    freq = np.bincount(walks.ravel(), minlength=n).astype(np.float64) ** 0.75
    cdf = np.cumsum(freq / freq.sum())
    cs, xs = [], []
    for o in range(1, window + 1):
        a, b = walks[:, :-o].ravel(), walks[:, o:].ravel()
        cs += [a, b]
        xs += [b, a]
    centre, ctx = np.concatenate(cs), np.concatenate(xs)
    perm = rng.permutation(len(centre))
    total = len(perm)
    lab = np.zeros((1, neg + 1), np.float32)
    lab[0, 0] = 1
    for s in range(0, total, batch):
        idx = perm[s:s + batch]
        c = centre[idx]
        negs = np.minimum(np.searchsorted(cdf, rng.random((len(idx), neg))), n - 1)
        tgt = np.concatenate([ctx[idx, None], negs], axis=1)
        vc, vt = w_in[c], w_out[tgt]
        score = np.clip(np.einsum("bd,bkd->bk", vc, vt), -10, 10)
        g = (lab - 1 / (1 + np.exp(-score))) * np.float32(lr * max(1e-4, 1 - s / total))
        # scatter-add the per-pair updates (same result as np.add.at, ~1.5x faster via a sparse product)
        w_in += scatter(c, n) @ np.einsum("bk,bkd->bd", g, vt)
        w_out += scatter(tgt.ravel(), n) @ (g[:, :, None] * vc[:, None, :]).reshape(-1, dim)
    return w_in


def scatter(idx, n):
    """Sparse n x len(idx) matrix whose product with a (len(idx), d) array sums rows per index."""
    import scipy.sparse as sp
    return sp.csr_matrix((np.ones(len(idx), np.float32), (idx, np.arange(len(idx)))), shape=(n, len(idx)))


def embed_task(name, n, adj, start_nodes, p, q, seed):
    t0 = time.time()
    walks = make_walks(adj, start_nodes, p, q, WALKS["num_walks"], WALKS["length"], seed)
    t1 = time.time()
    emb = sgns(walks, n, seed=seed, **SGNS)
    return name, emb, round(t1 - t0, 1), round(time.time() - t1, 1), seed


# ---------------------------------------------------------------- 5. classification

def score(y_true, y_pred):
    from sklearn.metrics import accuracy_score, f1_score
    return accuracy_score(y_true, y_pred), f1_score(y_true, y_pred, average="macro")


def summarize(scores):
    a = np.array(scores)
    return {"acc": round(a[:, 0].mean(), 4), "acc_std": round(a[:, 0].std(), 4),
            "macro_f1": round(a[:, 1].mean(), 4), "macro_f1_std": round(a[:, 1].std(), 4)}


def eval_embedding(X, nodes, y, folds):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    out = {}
    for clf in ("logreg", "random_forest"):
        sc = []
        for tr, te in folds:
            Xtr, Xte = X[nodes[tr]], X[nodes[te]]
            if clf == "logreg":
                scaler = StandardScaler().fit(Xtr)
                model = LogisticRegression(max_iter=3000).fit(scaler.transform(Xtr), y[tr])
                pred = model.predict(scaler.transform(Xte))
            else:
                model = RandomForestClassifier(n_estimators=500, n_jobs=-1, random_state=SEED).fit(Xtr, y[tr])
                pred = model.predict(Xte)
            sc.append(score(y[te], pred))
        out[clf] = summarize(sc)
    return out


def eval_baselines(G, nodes, y, folds):
    major_sc, vote_sc = [], []
    for tr, te in folds:
        train_lab = {int(nodes[i]): int(y[i]) for i in tr}
        major = Counter(y[tr].tolist()).most_common(1)[0][0]
        major_sc.append(score(y[te], np.full(len(te), major)))
        pred = []
        for i in te:
            c = Counter(train_lab[u] for u in G[int(nodes[i])] if u in train_lab)
            pred.append(c.most_common(1)[0][0] if c else major)
        vote_sc.append(score(y[te], np.array(pred)))
    return {"majority_class": summarize(major_sc), "neighbour_vote": summarize(vote_sc)}


def eval_label_spreading(G, nodes, y, folds, n_classes, alpha=0.2):
    """Label spreading (Zhou et al. 2004): F = (I - alpha S)^-1 Y0 with S = D^-1/2 A D^-1/2.

    alpha=0.2 is scikit-learn's LabelSpreading default. On this graph alpha near 1 collapses to
    predicting the department with the most high-degree labelled nodes (acc ~0.21 at 0.99).
    """
    n = G.number_of_nodes()
    A = nx.to_numpy_array(G, nodelist=range(n))
    d = A.sum(1)
    dinv = np.where(d > 0, 1 / np.sqrt(np.maximum(d, 1e-12)), 0.0)
    M = np.eye(n) - alpha * (A * dinv[:, None] * dinv[None, :])
    sc = []
    for tr, te in folds:
        Y0 = np.zeros((n, n_classes))
        Y0[nodes[tr], y[tr]] = 1
        F = np.linalg.solve(M, Y0)
        sc.append(score(y[te], F[nodes[te]].argmax(1)))
    return summarize(sc)


def gcn_step(A, AX, W1, W2, train, Y, mask, wd):
    """Loss and gradients of a 2-layer GCN: softmax(A relu(A X W1) W2), CE on train rows."""
    Z1 = AX @ W1
    H1 = np.maximum(Z1, 0) * mask
    AH = A @ H1
    Z2 = AH @ W2
    logits = Z2[train]
    logits = logits - logits.max(1, keepdims=True)
    logp = logits - np.log(np.exp(logits).sum(1, keepdims=True))
    P = np.exp(logp)
    loss = -logp[np.arange(len(train)), Y.argmax(1)].mean() + 0.5 * wd * (W1 ** 2).sum()
    dZ2 = np.zeros_like(Z2)
    dZ2[train] = (P - Y) / len(train)
    dW2 = AH.T @ dZ2
    dH1 = A.T @ (dZ2 @ W2.T)
    dZ1 = dH1 * mask * (Z1 > 0)
    dW1 = AX.T @ dZ1 + wd * W1
    return loss, dW1, dW2


def gcn_gradcheck():
    rng = np.random.default_rng(1)
    n, f, h, c = 7, 4, 5, 3
    A = rng.random((n, n))
    A = (A + A.T) / 2
    AX = A @ rng.normal(size=(n, f))
    W1, W2 = rng.normal(size=(f, h)), rng.normal(size=(h, c))
    train = np.array([0, 2, 3, 5])
    Y = np.eye(c)[[0, 1, 2, 1]]
    mask = (rng.random((n, h)) > 0.3) / 0.7
    _, g1, g2 = gcn_step(A, AX, W1, W2, train, Y, mask, 1e-2)
    worst = 0.0
    for W, g in ((W1, g1), (W2, g2)):
        for idx in np.ndindex(W.shape):
            old = W[idx]
            W[idx] = old + 1e-6
            lp = gcn_step(A, AX, W1, W2, train, Y, mask, 1e-2)[0]
            W[idx] = old - 1e-6
            lm = gcn_step(A, AX, W1, W2, train, Y, mask, 1e-2)[0]
            W[idx] = old
            worst = max(worst, abs((lp - lm) / 2e-6 - g[idx]))
    return worst


def gcn_fit_predict(A, X, train, y_train, test, n_classes, seed):
    rng = np.random.default_rng(seed)
    hidden, drop, lr, wd = GCN["hidden"], GCN["dropout"], GCN["lr"], GCN["wd"]
    AX = A @ X
    glorot = lambda a, b: rng.uniform(-1, 1, (a, b)) * np.sqrt(6 / (a + b))
    params = [glorot(X.shape[1], hidden), glorot(hidden, n_classes)]
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    Y = np.eye(n_classes)[y_train]
    for t in range(1, GCN["epochs"] + 1):
        mask = (rng.random((A.shape[0], hidden)) >= drop) / (1 - drop)
        _, g1, g2 = gcn_step(A, AX, params[0], params[1], train, Y, mask, wd)
        for i, g in enumerate((g1, g2)):  # Adam
            m[i] = 0.9 * m[i] + 0.1 * g
            v[i] = 0.999 * v[i] + 0.001 * g * g
            params[i] -= lr * (m[i] / (1 - 0.9 ** t)) / (np.sqrt(v[i] / (1 - 0.999 ** t)) + 1e-8)
    Z2 = A @ np.maximum(AX @ params[0], 0) @ params[1]
    return Z2[test].argmax(1)


def eval_gcn(A, X, nodes, y, folds, n_classes):
    sc = []
    for f, (tr, te) in enumerate(folds):
        pred = gcn_fit_predict(A, X, nodes[tr], y[tr], nodes[te], n_classes, SEED + f)
        sc.append(score(y[te], pred))
    return summarize(sc)


def paired_seed0(A, embeddings, nodes, y, folds, n_classes):
    """Per-fold scores on the seed-0 embeddings, so methods sharing the folds can be compared fold by fold."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    n = A.shape[0]
    per = {}
    for name, X in embeddings.items():
        X = X.astype(np.float64)
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
        per[name] = {"logreg": [], "gcn": [], "mlp": []}
        for f, (tr, te) in enumerate(folds):
            scaler = StandardScaler().fit(X[nodes[tr]])
            model = LogisticRegression(max_iter=3000).fit(scaler.transform(X[nodes[tr]]), y[tr])
            per[name]["logreg"].append(score(y[te], model.predict(scaler.transform(X[nodes[te]]))))
            if name in ("deepwalk", "node2vec_p1_q0.5"):  # same networks and seeds as eval_gcn
                per[name]["gcn"].append(score(y[te], gcn_fit_predict(A, Xs, nodes[tr], y[tr], nodes[te], n_classes, SEED + f)))
                per[name]["mlp"].append(score(y[te], gcn_fit_predict(np.eye(n), Xs, nodes[tr], y[tr], nodes[te], n_classes, SEED + f)))

    def diff(a, b):
        d = np.array(a) - np.array(b)
        return {"acc_diff_mean": round(float(d[:, 0].mean()), 4), "acc_folds_better": int((d[:, 0] > 0).sum()),
                "acc_folds_tied": int((d[:, 0] == 0).sum()),
                "macro_f1_diff_mean": round(float(d[:, 1].mean()), 4), "macro_f1_folds_better": int((d[:, 1] > 0).sum()),
                "folds": len(d)}

    out = {}
    for name in ("deepwalk", "node2vec_p1_q0.5"):
        out[f"{name}: gcn - mlp"] = diff(per[name]["gcn"], per[name]["mlp"])
        out[f"{name}: gcn - logreg"] = diff(per[name]["gcn"], per[name]["logreg"])
    for other in ("node2vec_p1_q0.5", "node2vec_p1_q2"):
        out[f"logreg: deepwalk - {other}"] = diff(per["deepwalk"]["logreg"], per[other]["logreg"])
    out["per_fold_acc_macro_f1"] = {name: {k: [[round(a, 4), round(b, 4)] for a, b in v] for k, v in p.items() if v}
                                    for name, p in per.items()}
    return out


def plot_tsne(emb, lcc, labels, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    nodes = np.array(sorted(lcc))
    xy = TSNE(n_components=2, init="pca", random_state=SEED, perplexity=30).fit_transform(emb[nodes])
    top = [d for d, _ in Counter(labels[v] for v in nodes).most_common(8)]
    dept = np.array([labels[v] for v in nodes])
    fig, ax = plt.subplots(figsize=(7, 6))
    other = ~np.isin(dept, top)
    ax.scatter(xy[other, 0], xy[other, 1], s=6, c="0.82", label="other depts")
    cmap = plt.get_cmap("tab10")
    for i, d in enumerate(top):
        sel = dept == d
        ax.scatter(xy[sel, 0], xy[sel, 1], s=9, color=cmap(i), label=f"dept {d} (n={sel.sum()})")
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=7, markerscale=2, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main

def to_json(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def main():
    data_dir, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    edges, labels = load(data_dir)
    n = len(labels)
    assert sorted(labels) == list(range(n)), "labels must cover nodes 0..n-1"
    assert all(u < n and v < n for u, v in edges)
    G = undirected(n, edges)
    nx.set_node_attributes(G, labels, "dept")
    edge_list = list(G.edges())
    adj = [sorted(G[v]) for v in range(n)]
    start_nodes = [v for v in range(n) if adj[v]]
    lcc = max(nx.connected_components(G), key=len)
    G_lcc = G.subgraph(lcc).copy()
    n_lcc = len(lcc)
    res = {"settings": {"seed": SEED, "folds": N_FOLDS, "min_class": MIN_CLASS, "walks": WALKS, "sgns": SGNS,
                        "node2vec_configs": N2V_CONFIGS, "embedding_seeds": EMB_SEEDS, "gcn": GCN,
                        "adaptive_betweenness_batch": ADAPTIVE_BATCH, "null_shuffles": NULL_SHUFFLES,
                        "graph": "undirected, self-loops removed; removal experiment on the LCC"}}

    with ProcessPoolExecutor(max_workers=11) as pool:
        fut_cliques = pool.submit(clique_task, n, edge_list, labels)
        fut_adaptive = pool.submit(adaptive_betweenness_task, sorted(lcc), list(G_lcc.edges()))
        fut_emb = [pool.submit(embed_task, name, n, adj, start_nodes, p, q, seed)
                   for name, (p, q) in N2V_CONFIGS.items() for seed in EMB_SEEDS]

        res["gcn_gradcheck_max_abs_err"] = gcn_gradcheck()
        log(f"GCN gradient check max abs error {res['gcn_gradcheck_max_abs_err']:.2e}")
        assert res["gcn_gradcheck_max_abs_err"] < 1e-5, "GCN gradients are wrong"
        res["structure"], lcc_check = structure(edges, labels, G)
        assert lcc_check == lcc
        log(f"structure: {res['structure']['undirected_edges']} undirected edges, LCC {res['structure']['lcc_nodes']}")
        res["homophily"] = homophily(G, labels, edges, lcc)
        log(f"homophily: {res['homophily']['edge_homophily']:.3f} vs shuffled "
            f"{res['homophily']['shuffled_label_null_mean']:.3f}, modularity {res['homophily']['dept_modularity_lcc']:.3f}")
        res["centrality"], btw, deg = centrality(G, labels)
        log("centrality done")

        order_b = [v for v in sorted(G, key=btw.get, reverse=True) if v in lcc]
        order_d = [v for v in sorted(G, key=deg.get, reverse=True) if v in lcc]
        curves = {"degree (static)": curve_static(G_lcc, order_d, n_lcc),
                  "degree (adaptive, every 1)": curve_adaptive_degree(G_lcc, n_lcc),
                  "betweenness (static)": curve_static(G_lcc, order_b, n_lcc)}
        rng = random.Random(SEED)
        rand_curves = []
        for _ in range(RANDOM_REPEATS):
            order = sorted(lcc)
            rng.shuffle(order)
            rand_curves.append(curve_static(G_lcc, order, n_lcc))
        rand = np.array([[c[1] for c in rc] for rc in rand_curves])
        rand_second = np.array([[c[2] for c in rc] for rc in rand_curves])
        log("static removal curves done")

        # classification set: LCC nodes in departments with >= MIN_CLASS LCC members
        from sklearn.model_selection import StratifiedKFold
        cnt = Counter(labels[v] for v in lcc)
        nodes = np.array(sorted(v for v in lcc if cnt[labels[v]] >= MIN_CLASS))
        classes = sorted({labels[v] for v in nodes})
        y = np.array([classes.index(labels[v]) for v in nodes])
        folds = list(StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(nodes, y))
        res["classification_set"] = {"nodes": len(nodes), "classes": len(classes),
                                     "dropped_lcc_nodes": len(lcc) - len(nodes),
                                     "train_fraction_per_fold": round(1 - 1 / N_FOLDS, 2)}
        cls = eval_baselines(G, nodes, y, folds)
        cls["label_spreading"] = eval_label_spreading(G, nodes, y, folds, len(classes))
        log(f"baselines: {cls}")

        A = nx.to_numpy_array(G, nodelist=range(n)) + np.eye(n)
        dinv = 1 / np.sqrt(A.sum(1))
        A = A * dinv[:, None] * dinv[None, :]
        cls["gcn_identity"] = eval_gcn(A, np.eye(n), nodes, y, folds, len(classes))
        log(f"gcn identity: {cls['gcn_identity']}")

        embeddings, timing, per_seed = {}, {}, {}
        for fut in fut_emb:
            name, emb, t_walk, t_train, seed = fut.result()
            if seed == SEED:
                embeddings[name] = emb
                np.save(out_dir / f"emb_{name}.npy", emb)
            timing[f"{name}/seed{seed}"] = {"walk_s": t_walk, "train_s": t_train}
            per_seed.setdefault(name, []).append(eval_embedding(emb, nodes, y, folds))
            log(f"{name} seed {seed}: {per_seed[name][-1]}")
        for name, runs in per_seed.items():
            cls[name] = {}
            for clf in runs[0]:
                accs = [r[clf]["acc"] for r in runs]
                f1s = [r[clf]["macro_f1"] for r in runs]
                cls[name][clf] = {"acc": round(float(np.mean(accs)), 4), "macro_f1": round(float(np.mean(f1s)), 4),
                                  "acc_seed_std": round(float(np.std(accs)), 4),
                                  "macro_f1_seed_std": round(float(np.std(f1s)), 4),
                                  "macro_f1_fold_std_seed0": runs[0][clf]["macro_f1_std"], "seeds": len(runs)}
        for name in ("deepwalk", "node2vec_p1_q0.5"):
            X = embeddings[name].astype(np.float64)
            X = (X - X.mean(0)) / (X.std(0) + 1e-9)
            cls[f"gcn_{name}_features"] = eval_gcn(A, X, nodes, y, folds, len(classes))
            # same 2-layer network with the adjacency replaced by I: isolates the effect of message passing
            cls[f"mlp_{name}_features"] = eval_gcn(np.eye(n), X, nodes, y, folds, len(classes))
            log(f"gcn / mlp on {name}: {cls[f'gcn_{name}_features']} / {cls[f'mlp_{name}_features']}")
        res["classification"] = cls
        res["paired_seed0"] = paired_seed0(A, embeddings, nodes, y, folds, len(classes))
        res["embedding_timing"] = timing

        res["cliques"] = fut_cliques.result()
        log(f"cliques: {res['cliques']['maximal_cliques_size_ge3']} (>=3), max size {res['cliques']['max_clique_size']}")
        adaptive = fut_adaptive.result()
        curves[f"betweenness (adaptive, every {ADAPTIVE_BATCH})"] = adaptive["curve"]
        log("adaptive betweenness removal done")

    res["removal"] = {name: removal_summary(c, n_lcc) for name, c in curves.items()}
    rand_mean = list(zip(REMOVAL_KS, rand.mean(0), rand_second.mean(0), [None] * len(REMOVAL_KS)))
    res["removal"]["random (mean of 20)"] = removal_summary(rand_mean, n_lcc)
    res["removal"]["adaptive_betweenness_first10_removed"] = [
        {"node": v, "dept": labels[v], "initial_degree": G.degree(v)} for v in adaptive["removed"][:10]]
    res["removal"]["note"] = (f"undirected LCC, N={n_lcc}; adaptive betweenness recomputed every "
                              f"{ADAPTIVE_BATCH} removals and only up to k={ADAPTIVE_MAX_K}")
    plot_removal(curves, rand, n_lcc, out_dir / "removal_curve.png")
    best = max(N2V_CONFIGS, key=lambda k: cls[k]["logreg"]["macro_f1"])
    plot_tsne(embeddings[best], lcc, labels, out_dir / "tsne.png", f"t-SNE of {best} embeddings (LCC)")
    res["tsne_embedding"] = best
    res["runtime_s"] = round(time.time() - T0, 1)
    (out_dir / "pilot_results.json").write_text(json.dumps(res, indent=1, default=to_json, ensure_ascii=False),
                                                encoding="utf-8")
    log(f"wrote {out_dir / 'pilot_results.json'}")


if __name__ == "__main__":
    main()
