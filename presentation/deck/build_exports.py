"""Prepare offline copies of the deck: a print page for a vector PDF, and the speaker notes for the PPTX.

Usage: python build_exports.py <deck root> <out dir>
Writes <out dir>/print.html (all slides, one 1920x1080 page each) and <out dir>/notes.json (id, notes) in deck order.
"""
import html
import json
import re
import sys
from pathlib import Path

root, out = Path(sys.argv[1]), Path(sys.argv[2])
deck = json.loads((root / "project" / "deck.json").read_text(encoding="utf-8"))
NET = "/_blob/b9faf58bc70a3e455b36f3a6ecf325ab"
net_local = (Path(__file__).parent / "network_dark.png").as_uri()

sections, notes = [], []
for sid in deck["order"]:
    s = (root / "project" / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    m = re.search(r"<aside>(.*?)</aside>", s, re.S)
    notes.append({"id": sid, "notes": html.unescape(m.group(1).strip()) if m else ""})
    sections.append(s.replace(NET, net_local))

links = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in deck["faces"].values())
(out / "print.html").write_text(
    f'<!doctype html><html><head><meta charset="utf-8"><title>{deck["title"]}</title>{links}<style>'
    '@page{size:1920px 1080px;margin:0} html,body{margin:0;padding:0} *{box-sizing:border-box;'
    '-webkit-print-color-adjust:exact;print-color-adjust:exact} p,h1,h2,h3,ul{margin:0} ul{padding-left:1.2em} '
    'aside{display:none} a{color:inherit} body{word-break:keep-all;overflow-wrap:break-word} '
    'table{border-collapse:collapse;width:100%} td,th{border:1px solid #d9dee6;padding:0.35em 0.6em} '
    'section{position:relative;width:1920px;height:1080px;overflow:hidden;break-after:page;page-break-after:always}'
    f'</style></head><body>{"".join(sections)}</body></html>', encoding="utf-8")
(out / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(sections), "slides")
