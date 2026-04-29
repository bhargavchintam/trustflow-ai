"""Render the LangGraph state machine to docs/graph.png and docs/graph.mmd.

Run from the backend/ directory:
    uv run python scripts/render_graph.py

Requires network access to mermaid.ink (LangGraph's default mermaid renderer).
Falls back to writing only the .mmd source if PNG generation fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.agent import get_graph  # noqa: E402

DOCS = Path(__file__).resolve().parent.parent.parent / "docs"
DOCS.mkdir(parents=True, exist_ok=True)


def main() -> None:
    g = get_graph().get_graph()
    mmd = g.draw_mermaid()
    (DOCS / "graph.mmd").write_text(mmd)
    print(f"[render_graph] wrote {DOCS / 'graph.mmd'}")

    try:
        png_bytes = g.draw_mermaid_png()
        (DOCS / "graph.png").write_bytes(png_bytes)
        print(f"[render_graph] wrote {DOCS / 'graph.png'} ({len(png_bytes)} bytes)")
    except Exception as e:
        print(f"[render_graph] PNG generation failed ({type(e).__name__}: {e}); .mmd only")


if __name__ == "__main__":
    main()
