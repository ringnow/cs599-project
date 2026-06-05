"""Tool definitions for the research agent.

Supports multiple search backends with automatic fallback:
1. MCP-based search (Tavily, etc.) — most reliable with proxy
2. DuckDuckGo (free, no API key) — may not work in some regions
3. Brave Search (requires API key) — more reliable
4. Semantic Scholar (academic papers, free)

Search API keys are managed through the same key store as LLM providers.
"""
import json
import re
from typing import Dict, List, Optional

import requests

from src.agent.state import SearchResult
from src.config import config
from src.models.key_store import get_key_store

# ============================================================================
# Web Search — Multiple backends with fallback
# ============================================================================


def _bocha_search(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search using BoCha API (https://api.bocha.cn/v1/web-search)."""
    api_key = _get_search_api_key("bocha")
    if not api_key:
        print("[BoCha] 未配置 API Key（请在服务商管理 → 搜索工具 API Key 中配置）")
        return []
    try:
        url = "https://api.bocha.cn/v1/web-search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {"query": query, "summary": True, "count": max_results}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            print(f"[BoCha] API error: {data}")
            return []
        results = []
        for r in data.get("data", {}).get("webPages", {}).get("value", []):
            results.append(SearchResult(
                title=r.get("name", "No title"),
                url=r.get("url", ""),
                snippet=r.get("snippet", r.get("summary", "")),
                source="web"
            ))
        return results
    except Exception as e:
        print(f"[BoCha] Search failed: {e}")
        return []


def web_search(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search the web using available backends.

    Priority:
    1. BoCha (best in China, needs API key)
    2. Brave Search (fallback, if API key configured)
    3. Return empty if all fail
    """
    errors = []

    # 1. Try BoCha (stable in China)
    try:
        results = _bocha_search(query, max_results)
        if results:
            print(f"[search] BoCha returned {len(results)} results")
            return results
    except Exception as e:
        msg = f"BoCha: {e}"
        errors.append(msg)
        print(f"[search] {msg}")

    # 2. Try Brave Search (fallback, requires API key)
    brave_key = _get_search_api_key("brave")
    if brave_key:
        try:
            results = _brave_search(query, max_results, brave_key)
            if results:
                print(f"[search] Brave returned {len(results)} results")
                return results
        except Exception as e:
            msg = f"Brave: {e}"
            errors.append(msg)
            print(f"[search] {msg}")
    else:
        errors.append("Brave: 未配置 API Key")

    # 3. All backends failed
    print(f"[search] ⚠️ All web search backends failed for query: {query[:50]}...")
    for err in errors:
        print(f"  - {err}")
    print("[search] 💡 提示: 在「服务商管理」→「搜索工具 API Key」中配置 BoCha API Key")
    return []


def _brave_search(query: str, max_results: int = 5, api_key: str = "") -> List[SearchResult]:
    """Search using Brave Search API.

    Requires BRAVE_API_KEY. Get one at: https://api.search.brave.com/app/keys
    """
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": min(max_results, 20), "offset": 0}

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("web", {}).get("results", []):
            results.append(SearchResult(
                title=r.get("title", "No title"),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                source="web"
            ))
        return results
    except Exception as e:
        print(f"[Brave] Search failed: {e}")
        return []


# ============================================================================
# Academic Search — arXiv (保留但不再默认使用，由 Semantic Scholar 替代)
# ============================================================================

def arxiv_search(query: str, max_results: int = 3) -> List[SearchResult]:
    """Search arXiv for academic papers using the arxiv library."""
    try:
        import arxiv as arxiv_lib
        search = arxiv_lib.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv_lib.SortCriterion.Relevance
        )
        client = arxiv_lib.Client(page_size=max_results, delay_seconds=1, num_retries=1)
        results = []
        for r in client.results(search):
            results.append(SearchResult(
                title=r.title or "No title",
                url=r.entry_id or (f"https://arxiv.org/abs/{r.get_short_id()}" if hasattr(r, 'get_short_id') else ""),
                snippet=(r.summary or "")[:500],
                source="arxiv"
            ))
        return results
    except Exception as e:
        print(f"[arXiv] Search failed: {e}")
        return []


# ============================================================================
# Academic Search — Semantic Scholar (arXiv 替代, 免费, 无需 API key)
# ============================================================================

def semantic_scholar_search(query: str, max_results: int = 3) -> List[SearchResult]:
    """Search Semantic Scholar for academic papers.

    Free API, optional API key for higher rate limits.
    API key stored securely via the encrypted key store (same as LLM keys).
    """
    try:
        api_key = _get_search_api_key("semantic_scholar")
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
        params = {
            "query": query,
            "limit": min(max_results, 10),
            "fields": "title,url,abstract,year",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for p in data.get("data", []):
            results.append(SearchResult(
                title=p.get("title", "No title"),
                url=p.get("url", f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}"),
                snippet=(p.get("abstract") or "")[:500],
                source="semantic_scholar",
            ))
        if results:
            print(f"[SemanticScholar] returned {len(results)} results")
        return results
    except Exception as e:
        print(f"[SemanticScholar] Search failed: {e}")
        return []


# ============================================================================
# Content Extraction
# ============================================================================

def extract_web_content(url: str) -> str:
    """Extract main content from a web page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()

        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.texts = []
                self.skip = False
                self.skip_tags = {'script', 'style', 'nav', 'header', 'footer'}

            def handle_starttag(self, tag, attrs):
                if tag in self.skip_tags:
                    self.skip = True

            def handle_endtag(self, tag):
                if tag in self.skip_tags:
                    self.skip = False

            def handle_data(self, data):
                if not self.skip:
                    self.texts.append(data)

        extractor = TextExtractor()
        extractor.feed(response.text)
        content = ' '.join(extractor.texts)
        content = re.sub(r'\s+', ' ', content).strip()
        return content[:3000] if content else ""
    except Exception as e:
        print(f"[extract] Content extraction failed for {url}: {e}")
        return ""


# ============================================================================
# Search API Key Management
# ============================================================================

def _get_search_api_key(search_provider: str) -> Optional[str]:
    """Get API key for a search provider from the key store.

    Keys are stored with prefix: BRAVE_API_KEY, SERPAPI_API_KEY, etc.
    """
    key_store = get_key_store()
    key_name = f"{search_provider}_search"
    return key_store.get_key(key_name)


def set_search_api_key(search_provider: str, api_key: str):
    """Set API key for a search provider.

    Args:
        search_provider: 'brave' or 'serpapi'
        api_key: The API key
    """
    key_store = get_key_store()
    key_name = f"{search_provider}_search"
    key_store.set_key(key_name, api_key)


def list_search_backends() -> List[Dict]:
    """List available search backends and their status."""
    key_store = get_key_store()
    backends = [
        {
            "name": "bocha",
            "display_name": "博查 BoCha",
            "description": "国内搜索引擎，需 API Key（open.bocha.cn），推荐首选",
            "has_key": bool(key_store.get_key("bocha")),
            "requires_key": True,
            "website": "https://open.bocha.cn",
        },
        {
            "name": "brave",
            "display_name": "Brave Search",
            "description": "更稳定，需要 API Key（api.search.brave.com）",
            "has_key": bool(key_store.get_key("brave")),
            "requires_key": True,
            "website": "https://api.search.brave.com/app/keys",
        },
        {
            "name": "semantic_scholar",
            "display_name": "Semantic Scholar",
            "description": "学术论文搜索引擎，可选 API Key（免费，提高限频）",
            "has_key": bool(key_store.get_key("semantic_scholar")),
            "requires_key": True,
            "website": "https://api.semanticscholar.org/",
        },
    ]
    return backends


# ============================================================================
# Tool Registry
# ============================================================================

TOOLS = {
    "web_search": web_search,
    "semantic_scholar_search": semantic_scholar_search,
    "extract_web_content": extract_web_content,
}


def get_tool_schemas() -> List[Dict]:
    """Get OpenAI-compatible function schemas for tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information on a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return (default: 5)", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "semantic_scholar_search",
                "description": "Search Semantic Scholar for academic papers and research",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return (default: 3)", "default": 3}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_web_content",
                "description": "Extract main text content from a web page URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to extract content from"}
                    },
                    "required": ["url"]
                }
            }
        }
    ]
