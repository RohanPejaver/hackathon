#!/usr/bin/env bash
# Device B. Vendors every UI asset into src/ui/static/vendor/ (39 §6.1: no runtime network
# dependency of any kind). Run once with connectivity; the outputs are committed.
set -euo pipefail
cd "$(dirname "$0")/.."
V=src/ui/static/vendor
mkdir -p "$V/fonts" "$V/icons"

# Open Props — single CSS file, design tokens, no build step.
curl -fsSL "https://unpkg.com/open-props@1.7.4/open-props.min.css" -o "$V/open-props.min.css"
[ -s "$V/open-props.min.css" ] || { echo "open-props download is empty" >&2; exit 1; }

# Phosphor Icons — regular weight SVGs, inlined into one local sprite. Deliberately not Lucide.
ICONS="hand knife square tray jar warning warning-octagon check x eye-slash video-camera-slash
arrows-clockwise prohibit list-checks receipt pulse clock arrow-counter-clockwise lock pause
hand-soap circle-dashed check-square drop cooking-pot bread waves"
{
  echo '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
  for i in $ICONS; do
    body=$(curl -fsSL "https://cdn.jsdelivr.net/npm/@phosphor-icons/core@2.1.1/assets/regular/${i}.svg" \
      | sed -e 's/<svg[^>]*>//' -e 's/<\/svg>//' | tr -d '\n') || { echo "MISSING icon: $i" >&2; continue; }
    echo "<symbol id=\"ph-${i}\" viewBox=\"0 0 256 256\">${body}</symbol>"
  done
  echo '</svg>'
} > "$V/icons/phosphor-sprite.svg"

# Archivo + IBM Plex Sans + IBM Plex Mono — self-hosted woff2 (latin subset).
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CSS=$(curl -fsSL -A "$UA" "https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap")
python3 - "$CSS" "$V/fonts" <<'PY'
import re, sys, urllib.request, pathlib
css, out = sys.argv[1], pathlib.Path(sys.argv[2])
blocks = re.findall(r"/\* (\w+) \*/\s*@font-face \{(.*?)\}", css, re.S)
lines = []
for subset, body in blocks:
    if subset != "latin":
        continue
    fam = re.search(r"font-family: '([^']+)'", body).group(1)
    wt = re.search(r"font-weight: (\d+)", body).group(1)
    url = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
    fname = f"{fam.replace(' ', '')}-{wt}.woff2"
    urllib.request.urlretrieve(url, out / fname)
    lines.append(
        f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{wt};font-display:swap;"
        f"src:url('fonts/{fname}') format('woff2');}}"
    )
(out.parent / "fonts.css").write_text("\n".join(lines) + "\n")
print(f"{len(lines)} font faces written")
PY
# Fail loudly if anything vendored is empty — a silent 0-byte asset is a black screen on stage.
empty=$(find "$V" -type f -empty)
if [ -n "$empty" ]; then echo "EMPTY VENDORED FILE(S):" >&2; echo "$empty" >&2; exit 1; fi
[ "$(wc -c < "$V/open-props.min.css")" -gt 10000 ] || { echo "open-props.min.css too small" >&2; exit 1; }
[ "$(grep -c '<symbol' "$V/icons/phosphor-sprite.svg")" -ge 20 ] || { echo "phosphor sprite incomplete" >&2; exit 1; }
ls -la "$V" "$V/fonts" "$V/icons"
