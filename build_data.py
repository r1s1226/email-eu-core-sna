"""Export the data behind the results website (website/site_data.json).

Everything comes from the pilot (pilot/pilot.py and pilot/results): the undirected, loop-free
email-Eu-core graph, its 986-node largest component, the removal orders, the removal curves,
the DeepWalk t-SNE and the classification metrics.

Usage:  python build_data.py   (needs numpy, scipy, scikit-learn, networkx; NX_PATH as for pilot.py)
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pilot"))
import pilot  # noqa: E402

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

edges, labels = pilot.load(ROOT / "data" / "email-Eu-core")
n = len(labels)
G = pilot.undirected(n, edges)
lcc = sorted(max(nx.connected_components(G), key=len))
H = G.subgraph(lcc).copy()
idx = {v: i for i, v in enumerate(lcc)}  # node id -> position in the exported arrays
res = json.loads((ROOT / "pilot" / "results" / "pilot_results.json").read_text(encoding="utf-8"))

# layout for the hero drawing: force-directed, fixed seed so the picture is reproducible
pos = nx.spring_layout(H, seed=pilot.SEED, iterations=300, k=0.9 / np.sqrt(len(lcc)))
xy = np.array([pos[v] for v in lcc])
xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0))

# t-SNE of the seed-0 DeepWalk embedding, same settings as the slides
from sklearn.manifold import TSNE  # noqa: E402
emb = np.load(ROOT / "pilot" / "results" / "emb_deepwalk.npy")
ts = TSNE(n_components=2, init="pca", random_state=pilot.SEED, perplexity=30).fit_transform(emb[lcc])
ts = (ts - ts.min(0)) / (ts.max(0) - ts.min(0))

btw = nx.betweenness_centrality(G)
btw_rank = {v: r for r, v in enumerate(sorted(lcc, key=btw.get, reverse=True), 1)}

# removal orders replayed by the page: adaptive betweenness (every 10, to k=400), adaptive degree, one random order
adaptive_b = pilot.adaptive_betweenness_task(lcc, list(H.edges()))["removed"]
Hd, adaptive_d = H.copy(), []
while Hd.number_of_nodes() > len(lcc) // 2:
    v = max(Hd.degree, key=lambda x: x[1])[0]
    Hd.remove_node(v)
    adaptive_d.append(v)
rng = random.Random(pilot.SEED)
rand_order = list(lcc)
rng.shuffle(rand_order)

# curves for the chart (cached by 발표/make_figures.py), thinned to every 2nd k
cur = dict(np.load(ROOT / "발표" / "figures" / "removal_curves.npz"))
keep = cur["k"] % 2 == 0
curves = {
    "k": cur["k"][keep].tolist(),
    "degree": np.round(cur["degree_adaptive"][keep], 4).tolist(),
    "random_mean": np.round(cur["random"].mean(0)[keep], 4).tolist(),
    "random_min": np.round(cur["random"].min(0)[keep], 4).tolist(),
    "random_max": np.round(cur["random"].max(0)[keep], 4).tolist(),
    "betweenness_k": cur["betweenness_adaptive_k"].tolist(),
    "betweenness": np.round(cur["betweenness_adaptive"], 4).tolist(),
}

dept_sizes = Counter(labels[v] for v in lcc)
cls = res["classification"]
out = {
    "n_lcc": len(lcc),
    "nodes": [[round(float(xy[i, 0]), 4), round(float(xy[i, 1]), 4), labels[v], G.degree(v),
               btw_rank[v], round(float(ts[i, 0]), 4), round(float(ts[i, 1]), 4), v] for i, v in enumerate(lcc)],
    "node_fields": ["x", "y", "dept", "degree", "betweenness_rank", "tsne_x", "tsne_y", "id"],
    "edges": [[idx[u], idx[v]] for u, v in H.edges()],
    "orders": {"betweenness": [idx[v] for v in adaptive_b], "degree": [idx[v] for v in adaptive_d],
               "random": [idx[v] for v in rand_order]},
    "curves": curves,
    "dept_sizes": dict(sorted(dept_sizes.items(), key=lambda kv: -kv[1])),
    "structure": {k: res["structure"][k] for k in ("nodes", "directed_edge_lines", "self_loops", "undirected_edges",
                                                   "lcc_nodes", "isolated_nodes", "reciprocity", "avg_clustering",
                                                   "lcc_avg_shortest_path", "lcc_diameter", "departments")},
    "homophily": res["homophily"],
    "centrality": {k: res["centrality"][k] for k in ("top10_betweenness", "spearman_betweenness_degree",
                                                     "overlap_top10_betweenness_degree", "cross_dept_frac_mean_all",
                                                     "cross_dept_frac_mean_top10_betweenness",
                                                     "cross_dept_frac_mean_top10_degree",
                                                     "neighbour_depts_mean_all", "neighbour_depts_mean_top10_betweenness",
                                                     "neighbour_depts_mean_top10_degree")},
    "cliques": {k: res["cliques"][k] for k in ("maximal_cliques_size_ge3", "max_clique_size", "max_size_cliques",
                                               "max_kcore", "max_kcore_nodes", "max_kcore_distinct_depts")},
    "removal": {k: v for k, v in res["removal"].items() if isinstance(v, dict)},
    "classification": {
        "n2v": {name: cls[name]["logreg"] for name in ("deepwalk", "node2vec_p1_q0.5", "node2vec_p1_q2")},
        "seed0": {
            "majority": cls["majority_class"], "vote": cls["neighbour_vote"],
            "label_spreading": {k: cls["label_spreading"][k] for k in ("acc", "macro_f1")},
            "deepwalk_logreg": {"acc": 0.749, "macro_f1": 0.6343},
            "mlp": cls["mlp_deepwalk_features"], "gcn": cls["gcn_deepwalk_features"],
            "gcn_identity": cls["gcn_identity"],
        },
        "paired": {k: v for k, v in res["paired_seed0"].items() if k != "per_fold_acc_macro_f1"},
        "set": res["classification_set"],
    },
}
# the seed-0 DeepWalk + LogReg row must match the paired per-fold values it was taken from
per = np.array(res["paired_seed0"]["per_fold_acc_macro_f1"]["deepwalk"]["logreg"])
assert abs(per[:, 0].mean() - 0.749) < 5e-4 and abs(per[:, 1].mean() - 0.6343) < 5e-4, per.mean(0)
(HERE / "site_data.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("nodes", len(out["nodes"]), "edges", len(out["edges"]), "orders",
      {k: len(v) for k, v in out["orders"].items()}, "bytes", (HERE / "site_data.json").stat().st_size)
