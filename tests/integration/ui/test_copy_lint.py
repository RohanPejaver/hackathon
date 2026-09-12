"""02 §Unsupported claims + 26 §constraint 5–6, applied to every string B authors in the UI.
A's lint covers policy templates; this covers the static shell: no prohibited claim word, no
green hue anywhere, no accusatory or per-person copy, no worker/customer identity field."""

import re
from pathlib import Path

STATIC = Path("src/ui/static")
FILES = [STATIC / "index.html", STATIC / "inspector.html", STATIC / "app.js", STATIC / "style.css"]

PROHIBITED = re.compile(
    r"\bsafe\b|\bunsafe\b|\bcontaminat\w*|allergen[- ]free|\bsanitiz\w*|\bdisinfect\w*", re.I
)
ACCUSATORY = re.compile(r"\byou (forgot|failed|contaminated|missed)\b|\bstreak\b|\bscore\b", re.I)
IDENTITY = re.compile(r"worker[_ ]?(name|id)\b|employee|customer[_ ]?name|\bface\b", re.I)


def _text(p: Path) -> str:
    """Source with comments stripped: comments quote the rules they enforce."""
    t = p.read_text()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    return re.sub(r"^\s*//.*$", "", t, flags=re.M)


def test_no_prohibited_claim_words_in_ui_copy():
    for p in FILES:
        for i, line in enumerate(_text(p).splitlines(), 1):
            assert not PROHIBITED.search(line), f"{p}:{i}: {line.strip()}"


def test_never_accusatory_never_per_person():
    for p in FILES:
        t = _text(p)
        assert not ACCUSATORY.search(t), p
        assert not IDENTITY.search(t), p


def test_no_green_anywhere():
    css = _text(STATIC / "style.css")
    hexes = re.findall(r"#([0-9a-fA-F]{6})\b", css)
    for h in hexes:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        assert not (g > r + 20 and g > b + 20), f"green-dominant colour #{h} in style.css"
    assert not re.search(
        r"\bgreen\b|\blime\b|--green|--lime|--teal|--jade|--emerald",
        css + _text(STATIC / "app.js"),
        re.I,
    )


def test_hmi_rules_radius_shadow_gradient_charts():
    css = _text(STATIC / "style.css")
    for m in re.finditer(r"border-radius:\s*([^;]+);", css):
        v = m.group(1).strip()
        assert v in ("var(--r)", "0", "2px", "3px"), v
    assert "box-shadow" not in css
    assert "gradient(" not in css
    assert (
        "<canvas" not in _text(STATIC / "index.html")
        and "chart" not in _text(STATIC / "app.js").lower()
    )


def test_no_runtime_network_dependency_or_forbidden_toolkit():
    for p in FILES:
        t = _text(p).replace("http://www.w3.org/2000/svg", "")  # the SVG namespace, not a fetch
        assert "http://" not in t and "https://" not in t, p
        for bad in ("lucide", "tailwind", "shadcn", "cdn.", "unpkg", "jsdelivr", "googleapis"):
            assert bad not in t.lower(), f"{bad} in {p}"


def test_worker_surface_copy_matches_26():
    js = _text(STATIC / "app.js")
    assert "This is an observation, not a determination. Confirm with the cook." in js
    assert "PROTOCOL ONLY — VISION UNAVAILABLE" in js
