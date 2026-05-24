from unittest.mock import MagicMock, patch


def _base_state(**kwargs):
    return {
        "topic": "Python AI",
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
        **kwargs,
    }


def test_web_search_writes_summary():
    with patch("thumbnail_agent.nodes.search_topic", return_value="Python is great for AI."):
        from thumbnail_agent.nodes import web_search
        result = web_search(_base_state())
    assert result == {"search_summary": "Python is great for AI."}


def test_prompt_writer_first_iteration():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="A bold thumbnail prompt.")
    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import prompt_writer
        result = prompt_writer(_base_state(search_summary="Python is great."))
    assert result == {"current_prompt": "A bold thumbnail prompt."}


def test_prompt_writer_includes_critique_on_revision():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Revised prompt.")
    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import prompt_writer
        state = _base_state(
            search_summary="Python is great.",
            critique="Text too small, no focal subject.",
            iteration=1,
        )
        result = prompt_writer(state)

    messages = mock_llm.invoke.call_args[0][0]
    human_content = messages[1].content
    assert "Text too small" in human_content
    assert result == {"current_prompt": "Revised prompt."}
