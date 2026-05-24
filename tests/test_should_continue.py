from thumbnail_agent.nodes import should_continue


def _state(rating, iteration, target=8, max_iter=3):
    return {
        "rating": rating,
        "iteration": iteration,
        "target_rating": target,
        "max_iterations": max_iter,
    }


def test_routes_to_saver_when_rating_meets_target():
    assert should_continue(_state(rating=8, iteration=1)) == "saver"


def test_routes_to_saver_when_rating_exceeds_target():
    assert should_continue(_state(rating=9, iteration=1)) == "saver"


def test_routes_to_saver_when_iteration_cap_hit():
    assert should_continue(_state(rating=5, iteration=3)) == "saver"


def test_routes_to_prompt_writer_when_below_target_and_under_cap():
    assert should_continue(_state(rating=6, iteration=2)) == "prompt_writer"
