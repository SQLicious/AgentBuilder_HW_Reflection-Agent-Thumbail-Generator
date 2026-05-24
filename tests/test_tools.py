from unittest.mock import MagicMock, patch


def test_search_topic_returns_joined_snippets():
    mock_results = {
        "results": [
            {"content": "Python is widely used for AI."},
            {"content": "Libraries like PyTorch are popular."},
        ]
    }
    with patch("thumbnail_agent.tools.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_results

        from thumbnail_agent.tools import search_topic
        result = search_topic("Python AI")

    assert "Python is widely used for AI." in result
    assert "Libraries like PyTorch are popular." in result
    instance.search.assert_called_once_with("Python AI", max_results=5)


def test_search_topic_handles_empty_results():
    with patch("thumbnail_agent.tools.TavilyClient") as MockClient:
        MockClient.return_value.search.return_value = {"results": []}
        from thumbnail_agent.tools import search_topic
        result = search_topic("obscure topic")
    assert result == ""
