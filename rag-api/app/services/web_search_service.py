import logging
import os

from config import WEB_SEARCH_MAX_RESULTS

logger = logging.getLogger(__name__)

_client = None


def is_enabled() -> bool:
    return bool(os.getenv("TAVILY_API_KEY"))


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    try:
        from tavily import TavilyClient
        _client = TavilyClient(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Tavily client: {e}")
        return None
    return _client


def search(query: str) -> list[dict]:
    """Run a Tavily web search. Returns [] if disabled or on failure.

    Each result: {"title": str, "url": str, "content": str}
    """
    client = _get_client()
    if client is None:
        logger.info("Web search skipped: TAVILY_API_KEY not set")
        return []

    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=WEB_SEARCH_MAX_RESULTS,
        )
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []

    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })
    return results
