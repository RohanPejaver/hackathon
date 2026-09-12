# Allergen Cross-Contamination Safety Layer

A prep-station safety layer that keeps a live model of which hands, tools, surfaces and
shared containers currently carry which allergens, and checks that the allergen reset
protocol actually happened before a restricted order is prepared.

The specification lives in `docs/` and is authoritative; code implements it. Start with
`docs/README.md`.

## Run

```bash
uv venv --python 3.11 && source .venv/bin/activate
pip install -e '.[dev]'            # core + runtime + dev; no camera library
pytest -q tests/integration        # B's suite; A's is tests/unit tests/replay tests/property
ruff check . && ruff format --check . && lint-imports
uvicorn src.runtime.app:app        # the demo, PROTOCOL_ONLY, no camera attached
```

Then open `http://127.0.0.1:8000/` (worker display) and `/inspector` (read-only state +
event timeline). No network is required after install; every UI asset is vendored.

`pip install -e '.[perception]'` is only for a machine with the overhead camera.
