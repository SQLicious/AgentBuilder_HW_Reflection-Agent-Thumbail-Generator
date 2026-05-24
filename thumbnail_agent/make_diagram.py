from pathlib import Path

from .graph import build_graph


def main() -> None:
    graph = build_graph()
    png_data = graph.get_graph().draw_mermaid_png()
    Path("graph.png").write_bytes(png_data)
    print("graph.png written")


if __name__ == "__main__":
    main()
