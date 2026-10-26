"""Korean-labelled figures for the 10/26 presentation, rebuilt from the pilot code and saved embeddings.

Usage:  python make_figures.py   (needs numpy, scipy, scikit-learn, matplotlib, networkx; NX_PATH as for pilot.py)
Writes figures/removal_ko.png, figures/tsne_ko.png and caches the removal curves in figures/removal_curves.npz.
"""
import os
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pilot"))
import pilot  # noqa: E402  (sets BLAS threads and imports networkx the same way)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

def korean_font():
    """Malgun Gothic on Windows, else the first Korean font installed (Nanum, Noto CJK, Apple SD Gothic)."""
    if Path("C:/Windows/Fonts/malgun.ttf").exists():
        return "C:/Windows/Fonts/malgun.ttf"
    for f in font_manager.findSystemFonts():
        if any(k in f for k in ("NanumGothic", "NotoSansCJK", "NotoSansKR", "AppleSDGothicNeo", "AppleGothic")):
            return f
    sys.exit("No Korean font found: install Malgun Gothic, Nanum Gothic or Noto Sans CJK KR")


FONT = korean_font()
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({"font.family": font_manager.FontProperties(fname=FONT).get_name(),
                     "axes.unicode_minus": False})

# deck palette: categorical slots 1-3 of the validated reference palette, muted chrome
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURFACE = "#14213d", "#4a5263", "#898781", "#e1e0d9", "#fcfcfb"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

edges, labels = pilot.load(ROOT / "data" / "email-Eu-core")
n = len(labels)
G = pilot.undirected(n, edges)
lcc = max(nx.connected_components(G), key=len)
G_lcc = G.subgraph(lcc).copy()
N = len(lcc)


def removal_curves():
    cache = OUT / "removal_curves.npz"
    if cache.exists():
        return dict(np.load(cache))
    btw = nx.betweenness_centrality(G)
    deg = dict(G.degree())
    order_b = [v for v in sorted(G, key=btw.get, reverse=True) if v in lcc]
    order_d = [v for v in sorted(G, key=deg.get, reverse=True) if v in lcc]
    rng = random.Random(pilot.SEED)
    rand = []
    for _ in range(pilot.RANDOM_REPEATS):
        order = sorted(lcc)
        rng.shuffle(order)
        rand.append([c[1] for c in pilot.curve_static(G_lcc, order, N)])
    adaptive = pilot.adaptive_betweenness_task(sorted(lcc), list(G_lcc.edges()))["curve"]
    curves = {
        "k": np.array(pilot.REMOVAL_KS),
        "degree_static": np.array([c[1] for c in pilot.curve_static(G_lcc, order_d, N)]),
        "degree_adaptive": np.array([c[1] for c in pilot.curve_adaptive_degree(G_lcc, N)]),
        "betweenness_static": np.array([c[1] for c in pilot.curve_static(G_lcc, order_b, N)]),
        "betweenness_adaptive_k": np.array([c[0] for c in adaptive]),
        "betweenness_adaptive": np.array([c[1] for c in adaptive]),
        "random": np.array(rand),
    }
    np.savez(cache, **curves)
    return curves


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=17, length=0, pad=8)
    ax.grid(color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def plot_removal(c):
    fig, ax = plt.subplots(figsize=(11.6, 6.6), dpi=200, facecolor=SURFACE)
    style(ax)
    x = c["k"] / N
    ax.plot(x, 1 - x, color="#c3c2b7", lw=1.6, ls=(0, (2, 3)))  # explained in the slide's legend
    rand = c["random"]
    ax.fill_between(x, rand.min(0), rand.max(0), color="#d6d4cc", lw=0)
    ax.plot(x, rand.mean(0), color=MUTED, lw=2.4)
    ax.plot(x, c["degree_adaptive"], color=BLUE, lw=2.4)
    xb = c["betweenness_adaptive_k"] / N
    ax.plot(xb, c["betweenness_adaptive"], color=ORANGE, lw=2.4)
    ax.axhline(0.5, color=INK2, lw=1.2, ls=(0, (4, 3)))
    ax.text(0.005, 0.515, "LCC 절반", color=INK2, fontsize=15)
    # where each strategy first drops below half (exact from the curves); series names live in the slide legend
    for xs, ys, col, (dx, ty, ha) in ((xb, c["betweenness_adaptive"], ORANGE, (-0.009, 0.375, "right")),
                                       (x, c["degree_adaptive"], BLUE, (0.008, 0.53, "left")),
                                       (x, rand.mean(0), MUTED, (-0.006, 0.435, "right"))):
        i = int(np.argmax(ys < 0.5))
        ax.plot([xs[i]], [ys[i]], "o", ms=9, color=col, mec=SURFACE, mew=2, zorder=5)
        ax.text(xs[i] + dx, ty, f"{xs[i]:.1%}", color=INK, fontsize=17, ha=ha, va="bottom", fontweight="bold")
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1.02)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("제거한 노드 비율 (LCC 986명 기준)", color=INK2, fontsize=18, labelpad=10)
    ax.set_ylabel("최대 연결 요소 크기 / 986", color=INK2, fontsize=18, labelpad=10)
    fig.tight_layout()
    fig.savefig(OUT / "removal_ko.png", facecolor=SURFACE)
    plt.close(fig)


def plot_tsne():
    from sklearn.manifold import TSNE
    emb = np.load(ROOT / "pilot" / "results" / "emb_deepwalk.npy")
    nodes = np.array(sorted(lcc))
    xy = TSNE(n_components=2, init="pca", random_state=pilot.SEED, perplexity=30).fit_transform(emb[nodes])
    dept = np.array([labels[v] for v in nodes])
    top = [d for d, _ in Counter(dept.tolist()).most_common(3)]
    fig, ax = plt.subplots(figsize=(8.4, 7.6), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    other = ~np.isin(dept, top)
    ax.scatter(xy[other, 0], xy[other, 1], s=16, color="#cfcdc5", lw=0)
    for d, col in zip(top, (BLUE, ORANGE, AQUA)):
        sel = dept == d
        ax.scatter(xy[sel, 0], xy[sel, 1], s=26, color=col, edgecolor=SURFACE, lw=0.6)
        cx, cy = np.median(xy[sel], axis=0)
        ax.annotate(f"부서 {d} ({sel.sum()}명)", (cx, cy), xytext=(0, 34), textcoords="offset points",
                    ha="center", fontsize=17, color=INK, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=SURFACE, ec=col, lw=1.5))
    ax.text(0.01, 0.01, "회색: 나머지 부서", transform=ax.transAxes, color=MUTED, fontsize=15)
    fig.tight_layout()
    fig.savefig(OUT / "tsne_ko.png", facecolor=SURFACE)
    plt.close(fig)
    return top


if __name__ == "__main__":
    curves = removal_curves()
    plot_removal(curves)
    print("removal figure written")
    print("tsne top depts:", plot_tsne())
