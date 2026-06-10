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
import time
import threading
from typing import Dict, List, Optional

import requests

from src.agent.state import SearchResult
from src.config import config
from src.models.key_store import get_key_store
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Rate limiter for Semantic Scholar API (1 req/s limit for free tier)
# ============================================================================

_semantic_scholar_lock = threading.Lock()
_semantic_scholar_next_allowed = 0.0

def _rate_limit_semantic_scholar():
    """Ensure at most 1 request per second to Semantic Scholar API
    by tracking the earliest allowed time for the NEXT request."""
    global _semantic_scholar_next_allowed
    with _semantic_scholar_lock:
        now = time.time()
        if now < _semantic_scholar_next_allowed:
            time.sleep(_semantic_scholar_next_allowed - now)
        _semantic_scholar_next_allowed = time.time() + 1.0


# ============================================================================
# Web Search — Multiple backends with fallback
# ============================================================================


def _bocha_search(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search using BoCha API (https://api.bocha.cn/v1/web-search)."""
    api_key = _get_search_api_key("bocha")
    if not api_key:
        logger.warning("[BoCha] 未配置 API Key（请在服务商管理 → 搜索工具 API Key 中配置）")
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
            logger.warning("[BoCha] API error: %s", data)
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
        logger.warning("[BoCha] Search failed: %s", e)
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
            logger.info("[search] BoCha returned %d results", len(results))
            return results
    except Exception as e:
        msg = f"BoCha: {e}"
        errors.append(msg)
        logger.warning("[search] %s", msg)

    # 2. Try Brave Search (fallback, requires API key)
    brave_key = _get_search_api_key("brave")
    if brave_key:
        try:
            results = _brave_search(query, max_results, brave_key)
            if results:
                logger.info("[search] Brave returned %d results", len(results))
                return results
        except Exception as e:
            msg = f"Brave: {e}"
            errors.append(msg)
            logger.warning("[search] %s", msg)
    else:
        errors.append("Brave: 未配置 API Key")

    # 3. All backends failed
    logger.warning("[search] ⚠️ All web search backends failed for query: %s...", query[:50])
    for err in errors:
        logger.warning("  - %s", err)
    logger.info("[search] 💡 提示: 在「服务商管理」→「搜索工具 API Key」中配置 BoCha API Key")
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
        logger.warning("[Brave] Search failed: %s", e)
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
        logger.warning("[arXiv] Search failed: %s", e)
        return []


# ============================================================================
# Academic Search — Semantic Scholar (arXiv 替代, 免费, 无需 API key)
# ============================================================================

def semantic_scholar_search(query: str, max_results: int = 3) -> List[SearchResult]:
    """Search Semantic Scholar for academic papers.

    Free API, optional API key for higher rate limits.
    API key stored securely via the encrypted key store (same as LLM keys).

    Returns enriched SearchResult objects with PDF links, citations, authors, etc.
    """
    try:
        api_key = _get_search_api_key("semantic_scholar")
        logger.debug("[SemanticScholar] API key %s", '✓ found' if api_key else '✗ NOT FOUND')

        # Rate limit: free tier allows max 1 req/s
        _rate_limit_semantic_scholar()

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
        else:
            logger.warning("[SemanticScholar] ⚠️ 未配置 API Key，使用免费接口（可能被限流 429）")
        params = {
            "query": query,
            "limit": min(max_results, 10),
            "fields": "title,url,abstract,year,paperId,openAccessPdf,citationCount,influentialCitationCount,tldr,publicationTypes,journal,authors",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for p in data.get("data", []):
            # Extract open access PDF URL if available
            pdf_url = ""
            is_oa = False
            oa_info = p.get("openAccessPdf")
            if oa_info and isinstance(oa_info, dict) and oa_info.get("url"):
                pdf_url = oa_info["url"]
                is_oa = True

            # Extract TLDR summary
            tldr = ""
            tldr_info = p.get("tldr")
            if tldr_info and isinstance(tldr_info, dict) and tldr_info.get("text"):
                tldr = tldr_info["text"]

            # Extract authors
            authors = []
            for a in p.get("authors", []):
                if isinstance(a, dict) and a.get("name"):
                    authors.append(a["name"])

            # Extract journal
            journal = ""
            journal_info = p.get("journal")
            if journal_info and isinstance(journal_info, dict) and journal_info.get("name"):
                journal = journal_info["name"]

            results.append(SearchResult(
                title=p.get("title", "No title"),
                url=p.get("url", f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}"),
                snippet=(p.get("abstract") or ""),  # Save FULL abstract, not truncated
                source="semantic_scholar",
                pdf_url=pdf_url,
                is_open_access=is_oa,
                citation_count=p.get("citationCount", 0),
                influential_citation_count=p.get("influentialCitationCount", 0),
                tldr=tldr,
                publication_types=p.get("publicationTypes", []),
                journal=journal,
                authors=authors,
                year=p.get("year", 0),
                paper_id=p.get("paperId", ""),
            ))
        if results:
            logger.info("[SemanticScholar] returned %d results", len(results))
            oa_count = sum(1 for r in results if r.is_open_access)
            if oa_count:
                logger.info("[SemanticScholar]   %d papers have open access PDFs", oa_count)
        return results
    except Exception as e:
        logger.warning("[SemanticScholar] Search failed: %s", e)
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
        response = requests.get(url, headers=headers, timeout=15)
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
        logger.warning("[extract] Content extraction failed for %s: %s", url, e)
        return ""


def extract_paper_content(paper: SearchResult) -> str:
    """Extract full text content from an academic paper.

    Priority:
    1. Download and parse Open Access PDF (if available)
    2. Call Semantic Scholar Paper API for full abstract + TLDR
    3. Try to fetch paper from arXiv (if applicable)
    4. Use already available data (abstract + tldr)

    Args:
        paper: SearchResult with paper metadata

    Returns:
        Extracted text content (up to 4000 chars)
    """
    # Priority 1: Download Open Access PDF
    if paper.pdf_url and paper.is_open_access:
        try:
            logger.info("  ⬇️ 正在下载 PDF: %s...", paper.title[:50])
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(paper.pdf_url, headers=headers, timeout=30, stream=True)
            resp.raise_for_status()

            # Try to parse with PyMuPDF
            try:
                import fitz  # PyMuPDF
                pdf_data = resp.content
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                full_text = []
                for page_num in range(min(len(doc), 10)):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        full_text.append(text.strip())
                doc.close()

                if full_text:
                    content = "\n\n".join(full_text)
                    if len(content) > 4000:
                        content = content[:4000]
                        last_period = content.rfind("。")
                        last_newline = content.rfind("\n\n")
                        cut = max(last_period, last_newline)
                        if cut > 2000:
                            content = content[:cut+1]
                    logger.info("  ✅ PDF 提取完成: %d 字", len(content))
                    return content
            except ImportError:
                logger.warning("  ⚠️ PyMuPDF 未安装，跳过 PDF 解析")
            except Exception as pdf_err:
                logger.warning("  ⚠️ PDF 解析失败: %s", pdf_err)
        except Exception as dl_err:
            logger.warning("  ⚠️ PDF 下载失败: %s", dl_err)

    # Priority 2: Call Semantic Scholar Paper API for full abstract
    if paper.paper_id:
        try:
            _rate_limit_semantic_scholar()
            api_key = _get_search_api_key("semantic_scholar")
            headers = {}
            if api_key:
                headers["x-api-key"] = api_key
            url = f"https://api.semanticscholar.org/graph/v1/paper/{paper.paper_id}"
            params = {"fields": "title,abstract,tldr,year,citationCount,venue,publicationVenue"}
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            parts = []
            abstract = data.get("abstract", "") or ""
            if abstract:
                parts.append(f"[Abstract] {abstract}")
            tldr_info = data.get("tldr")
            if tldr_info and isinstance(tldr_info, dict) and tldr_info.get("text"):
                parts.append(f"[TLDR] {tldr_info['text']}")

            if parts:
                content = "\n\n".join(parts)
                if len(content) > 3500:
                    content = content[:3500]
                logger.info("  ✅ Semantic Scholar API 返回 %d 字（含完整摘要）", len(content))
                return content
        except Exception as e:
            logger.warning("  ⚠️ S2 API 获取详情失败: %s", str(e)[:60])

    # Priority 3: Use already available data (abstract + tldr)
    parts = []
    if paper.tldr:
        parts.append(f"[TLDR] {paper.tldr}")
    if paper.snippet:
        full_abstract = paper.snippet
        if len(full_abstract) > 2000:
            full_abstract = full_abstract[:2000]
        parts.append(f"[Abstract] {full_abstract}")
    if parts:
        total = sum(len(p) for p in parts)
        logger.info("  ℹ️ 使用已有摘要/TLDR (%d 字)", total)
        return "\n\n".join(parts)

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
            "has_key": bool(key_store.get_key("semantic_scholar_search")),
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
