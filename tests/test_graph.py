from thumbnail_agent.graph import build_graph


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_has_all_five_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert {"web_search", "prompt_writer", "generator", "critic", "saver"}.issubset(node_names)


def test_graph_has_conditional_edge_from_critic():
    graph = build_graph()
    edges = graph.get_graph().edges
    source_nodes = {e[0] for e in edges}
    assert "critic" in source_nodes
