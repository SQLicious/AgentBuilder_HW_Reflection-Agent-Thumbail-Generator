import operator
from thumbnail_agent.state import ThumbnailState


def test_history_reducer_accumulates():
    h1 = [{"iteration": 1, "rating": 5}]
    h2 = [{"iteration": 2, "rating": 7}]
    assert operator.add(h1, h2) == [
        {"iteration": 1, "rating": 5},
        {"iteration": 2, "rating": 7},
    ]


def test_state_fields_exist():
    state: ThumbnailState = {
        "topic": "test",
        "search_summary": "",
        "current_prompt": "",
        "image_path": "",
        "rating": 0,
        "critique": "",
        "iteration": 0,
        "history": [],
        "target_rating": 8,
        "max_iterations": 3,
        "output_dir": "outputs/test",
    }
    assert state["topic"] == "test"
    assert state["history"] == []
