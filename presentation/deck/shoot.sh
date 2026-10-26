#!/bin/sh
# Screenshot slide pages in shots/ (all, or the names given) with headless Edge, then save half-size JPEG copies.
cd "$(dirname "$0")/shots"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
PROFILE="$(cygpath -w "${TEMP:-/tmp}")\\edge-shot-profile"  # throwaway Edge profile, kept apart from the user's own
if [ $# -eq 0 ]; then set -- *.html; fi
for f in "$@"; do
  b="${f%.html}"
  timeout 60 "$EDGE" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE" \
    --window-size=2000,1250 --virtual-time-budget=10000 \
    --screenshot="$(cygpath -w "$PWD/$b.png")" "file:///$(cygpath -m "$PWD/$f")" >/dev/null 2>&1
done
python -c "
import glob
from PIL import Image
fs=sorted(glob.glob('[0-9]*.png'))
for f in fs: Image.open(f).convert('RGB').crop((0,0,1920,1080)).resize((960,540)).save('s_'+f.replace('.png','.jpg'),quality=88)
print(len(fs),'shots')"
