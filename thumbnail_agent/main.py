import argparse
from datetime import datetime
from pathlib import Path

from .graph import build_graph


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower())[:40]


def run(topic: str, stream: bool, target_rating: int, max_iterations: int) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(Path("outputs") / f"{ts}_{_slugify(topic)}")

    initial_state = {
        "topic": topic,
        "search_summary": "",
        "current_prompt": "",
        "image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": target_rating,
        "max_iterations": max_iterations,
        "output_dir": output_dir,
    }

    graph = build_graph()

    if stream:
        from rich.console import Console
        console = Console()
        for chunk in graph.stream(initial_state):
            node_name = next(iter(chunk))
            console.print(f"[bold green]→ {node_name}[/bold green]")
    else:
        graph.invoke(initial_state)

    print(f"\nDone. Output: {output_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Thumbnail Designer Agent")
    parser.add_argument("topic", help="Video topic")
    parser.add_argument("--stream", action="store_true", help="Stream node updates live")
    parser.add_argument("--target-rating", type=int, default=8)
    parser.add_argument("--max-iterations", type=int, default=3)
    args = parser.parse_args()
    run(args.topic, args.stream, args.target_rating, args.max_iterations)


if __name__ == "__main__":
    main()
