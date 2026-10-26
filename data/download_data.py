"""Download SNAP email-Eu-core into data/email-Eu-core/ (the data is not stored in this repository).

Usage:  python data/download_data.py
Source: https://snap.stanford.edu/data/email-Eu-core.html  (please cite Leskovec et al. 2007 and Yin et al. 2017)
"""
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "email-Eu-core"
FILES = ["email-Eu-core.txt.gz", "email-Eu-core-department-labels.txt.gz"]

OUT.mkdir(exist_ok=True)
for name in FILES:
    dest = OUT / name
    if dest.exists():
        print("already there:", dest)
        continue
    urllib.request.urlretrieve(f"https://snap.stanford.edu/data/{name}", dest)
    print("downloaded:", dest, dest.stat().st_size, "bytes")
