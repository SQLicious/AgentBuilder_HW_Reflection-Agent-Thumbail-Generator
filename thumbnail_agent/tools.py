from tavily import TavilyClient


def search_topic(topic: str) -> str:
    client = TavilyClient()
    results = client.search(topic, max_results=5)
    snippets = [r["content"] for r in results.get("results", [])]
    return "\n\n".join(snippets)
