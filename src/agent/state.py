"""State definitions for the research agent graph."""
from typing import Annotated, List, Optional, TypedDict
from dataclasses import dataclass, field


def merge_lists(left: Optional[list], right: Optional[list]) -> list:
    """Merge two lists, handling None."""
    if left is None and right is None:
        return []
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str  # 'web' or 'semantic_scholar'
    # Extended fields for academic papers (Semantic Scholar)
    pdf_url: str = ""           # Open Access PDF URL if available
    is_open_access: bool = False
    citation_count: int = 0
    influential_citation_count: int = 0
    tldr: str = ""              # TLDR summary from Semantic Scholar
    publication_types: list = None  # e.g., ["JournalArticle", "Conference"]
    journal: str = ""           # Journal name
    authors: list = None        # List of author names
    year: int = 0
    paper_id: str = ""          # Semantic Scholar paper ID
    content: str = ""           # Full text content after extraction
    evaluation: str = ""        # LLM evaluation result
    is_cited: bool = False      # Whether this paper is cited in final report


@dataclass
class ResearchStep:
    """A single step in the research process."""
    step_number: int
    action: str  # 'decompose', 'search', 'extract', 'synthesize', 'complete'
    query: str = ""
    results: List[SearchResult] = field(default_factory=list)
    summary: str = ""
    timestamp: str = ""


class ResearchState(TypedDict):
    """State for the research agent LangGraph.

    This TypedDict defines the complete state that flows through the graph.
    Each key can be updated by nodes and passed to the next node.
    """
    # Input
    topic: str                          # Original research topic

    # Decomposition
    sub_questions: Annotated[List[str], merge_lists]  # Broken-down questions

    # Current execution
    current_question_index: int         # Which sub-question we're working on
    current_question: str               # Current sub-question being researched

    # Research data
    search_results: Annotated[List[SearchResult], merge_lists]  # All search results
    extracted_content: Annotated[List[str], merge_lists]  # Extracted content snippets

    # Process tracking
    steps: Annotated[List[ResearchStep], merge_lists]  # Execution steps
    iteration_count: int                # Number of iterations done

    # Output
    report: str                         # Final research report
    status: str                         # 'in_progress', 'completed', 'error'
    error_message: str                  # Error details if status is 'error'
