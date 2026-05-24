from langgraph.graph import END, START, StateGraph

from .nodes import critic, generator, prompt_writer, saver, should_continue, strategy, web_search
from .state import ThumbnailState


def build_graph():
    builder = StateGraph(ThumbnailState)

    builder.add_node("web_search", web_search)
    builder.add_node("strategy", strategy)
    builder.add_node("prompt_writer", prompt_writer)
    builder.add_node("generator", generator)
    builder.add_node("critic", critic)
    builder.add_node("saver", saver)

    builder.add_edge(START, "web_search")
    builder.add_edge("web_search", "strategy")
    builder.add_edge("strategy", "prompt_writer")
    builder.add_edge("prompt_writer", "generator")
    builder.add_edge("generator", "critic")
    builder.add_conditional_edges(
        "critic",
        should_continue,
        {"prompt_writer": "prompt_writer", "saver": "saver"},
    )
    builder.add_edge("saver", END)

    return builder.compile()
