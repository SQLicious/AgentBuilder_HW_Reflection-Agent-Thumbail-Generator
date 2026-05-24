"""
thumbnail_agent/make_diagram.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generates graph.mmd (Mermaid source) and graph.png (rendered diagram).

Run from the project root:
    python -m thumbnail_agent.make_diagram

If PNG rendering fails (requires an internet call to mermaid.ink), the
Mermaid source is still written so you can paste it at https://mermaid.live
"""

import base64
import logging
import time
import urllib.request
import zlib
from pathlib import Path

from rich.logging import RichHandler

from .graph import build_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)
logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parent  # saves graph.* next to the package

NODE_COLORS = {
    "web_search":    "#4A90D9",  # blue   — research
    "strategy":      "#9B59B6",  # purple — planning
    "prompt_writer": "#16A085",  # teal   — writing
    "generator":     "#E67E22",  # orange — generation
    "critic":        "#E74C3C",  # red    — evaluation
    "saver":         "#27AE60",  # green  — output
}


def _inject_node_colors(mmd_text: str) -> str:
    extra = []
    for node, color in NODE_COLORS.items():
        cls = f"node_{node}"
        extra.append(f"    classDef {cls} fill:{color},color:#fff,stroke:none")
        extra.append(f"    class {node} {cls};")
    return mmd_text.rstrip() + "\n" + "\n".join(extra) + "\n"


def _render_png(mmd_text: str, max_retries: int = 5, retry_delay: float = 2.0) -> bytes:
    # Kroki uses zlib-compressed + base64url encoding
    encoded = base64.urlsafe_b64encode(zlib.compress(mmd_text.encode(), level=9)).decode()
    url = f"https://kroki.io/mermaid/png/{encoded}"
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return resp.read()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    raise last_exc


def main():
    graph = build_graph()

    mmd_text = graph.get_graph().draw_mermaid()
    mmd_text = _inject_node_colors(mmd_text)

    mmd_path = OUT_DIR / "graph.mmd"
    mmd_path.write_text(mmd_text, encoding="utf-8")
    logger.info("graph.mmd  written -> %s", mmd_path)

    try:
        png_bytes = _render_png(mmd_text, max_retries=5, retry_delay=2.0)
        png_path = OUT_DIR / "graph.png"
        png_path.write_bytes(png_bytes)
        logger.info("graph.png  written -> %s", png_path)
    except Exception as exc:
        logger.warning("PNG render failed: %s", exc)
        logger.info("Paste graph.mmd into https://mermaid.live to view the diagram.")


if __name__ == "__main__":
    main()
