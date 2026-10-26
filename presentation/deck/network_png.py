"""Draw the email-Eu-core LCC (spring layout from the site data) as a transparent PNG for the dark cover."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

site, out = sys.argv[1], sys.argv[2]
d = json.load(open(site, encoding="utf-8"))
nodes = np.array([n[:2] for n in d["nodes"]], dtype=float)
deg = np.array([n[3] for n in d["nodes"]], dtype=float)
brank = np.array([n[4] for n in d["nodes"]], dtype=float)
nodes = (nodes - nodes.min(0)) / (nodes.max(0) - nodes.min(0))
segs = nodes[np.array(d["edges"])]

fig = plt.figure(figsize=(8, 8), dpi=200)
ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
ax.set_axis_off()
ax.add_collection(LineCollection(segs, colors=(0.78, 0.84, 0.94, 0.05), linewidths=0.35))
top = brank <= 10
size = 2 + 10 * np.sqrt(deg / deg.max())
ax.scatter(nodes[~top, 0], nodes[~top, 1], s=size[~top], c="#8fb2f0", alpha=0.85, linewidths=0)
ax.scatter(nodes[top, 0], nodes[top, 1], s=70, c="#f07a45", edgecolors="#14213d", linewidths=1.2, zorder=3)
ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02); ax.set_aspect("equal")
fig.savefig(out, transparent=True)
print("top10 brank nodes:", int(top.sum()))
