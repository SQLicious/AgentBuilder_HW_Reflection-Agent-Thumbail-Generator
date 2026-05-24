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


def test_generator_saves_png_and_increments_iteration(tmp_path):
    import base64 as b64
    fake_b64 = b64.b64encode(b"fakepngbytes").decode()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(b64_json=fake_b64)]

    mock_client = MagicMock()
    mock_client.images.generate.return_value = mock_response

    with patch("thumbnail_agent.nodes.OpenAI", return_value=mock_client):
        from thumbnail_agent.nodes import generator
        from pathlib import Path
        state = _base_state(
            current_prompt="A great thumbnail prompt.",
            iteration=0,
            output_dir=str(tmp_path),
        )
        result = generator(state)

    assert result["iteration"] == 1
    saved = Path(result["image_path"])
    assert saved.exists()
    assert saved.name == "iter_1.png"
    assert saved.read_bytes() == b"fakepngbytes"
    mock_client.images.generate.assert_called_once_with(
        model="gpt-image-1",
        prompt="A great thumbnail prompt.",
        size="1536x1024",
        n=1,
    )


def test_critic_returns_rating_critique_and_appends_history(tmp_path):
    fake_png = tmp_path / "iter_1.png"
    fake_png.write_bytes(b"fakepng")

    mock_structured = MagicMock()
    mock_structured.invoke.return_value = MagicMock(rating=6, critique="Text too small.")

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("thumbnail_agent.nodes.ChatOpenAI", return_value=mock_llm):
        from thumbnail_agent.nodes import critic, CritiqueOutput
        state = _base_state(
            topic="Python AI",
            current_prompt="Bold Python thumbnail.",
            image_path=str(fake_png),
            iteration=1,
        )
        result = critic(state)

    assert result["rating"] == 6
    assert result["critique"] == "Text too small."
    assert len(result["history"]) == 1
    entry = result["history"][0]
    assert entry["iteration"] == 1
    assert entry["rating"] == 6
    assert entry["prompt"] == "Bold Python thumbnail."
    assert entry["image_path"] == str(fake_png)
    mock_llm.with_structured_output.assert_called_once_with(CritiqueOutput)


def test_saver_picks_best_rating_and_writes_final_and_report(tmp_path):
    iter1 = tmp_path / "iter_1.png"
    iter2 = tmp_path / "iter_2.png"
    iter1.write_bytes(b"img1")
    iter2.write_bytes(b"img2")

    history = [
        {
            "iteration": 1,
            "prompt": "First prompt",
            "image_path": str(iter1),
            "rating": 5,
            "critique": "Too cluttered.",
        },
        {
            "iteration": 2,
            "prompt": "Revised prompt",
            "image_path": str(iter2),
            "rating": 8,
            "critique": "Great clarity now.",
        },
    ]

    from thumbnail_agent.nodes import saver
    state = _base_state(
        topic="Python AI",
        output_dir=str(tmp_path),
        history=history,
    )
    saver(state)

    final = tmp_path / "final.png"
    assert final.exists()
    assert final.read_bytes() == b"img2"

    report = tmp_path / "report.md"
    assert report.exists()
    content = report.read_text()
    assert "First prompt" in content
    assert "Revised prompt" in content
    assert "5/10" in content
    assert "8/10" in content
    assert "Too cluttered" in content
