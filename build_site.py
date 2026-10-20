"""Inline site_data.json into index.src.html and write two self-contained pages:

- index.html          the page body only (the Artifact publisher adds the document skeleton)
- docs/index.html     a full HTML document for GitHub Pages (serve the docs/ folder)

Usage:  python build_site.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "index.src.html").read_text(encoding="utf-8")
data = (HERE / "site_data.json").read_text(encoding="utf-8")
assert src.count("/*__DATA__*/") == 1
# guard against a stray "</script>" inside the JSON ending the script block early
body = src.replace("/*__DATA__*/", data.replace("</", "<\\/"))
(HERE / "index.html").write_text(body, encoding="utf-8")

head_end = body.index("<style>")  # title, metas and font links come before the style block
standalone = (
    "<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
    + body[:head_end] + body[head_end:body.index("</style>") + len("</style>")]
    + "\n</head>\n<body>\n" + body[body.index("</style>") + len("</style>"):] + "\n</body>\n</html>\n"
)
(HERE / "docs").mkdir(exist_ok=True)
(HERE / "docs" / "index.html").write_text(standalone, encoding="utf-8")
print("wrote index.html", len(body.encode("utf-8")), "bytes; docs/index.html", len(standalone.encode("utf-8")), "bytes")
