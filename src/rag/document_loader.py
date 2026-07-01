"""Document parsing + chunking for RAG ingestion.

Supports PDF, TXT, and Markdown. Uses recursive character splitting
with overlap to preserve context across chunk boundaries.
"""
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Chunk size and overlap tuned for academic text (denser than web content).
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))

_splitter = None


def _get_splitter():
    """Lazy-init the text splitter (avoids importing langchain at module load)."""
    global _splitter
    if _splitter is None:
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            _splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", "。", ".", " ", ""],
            )
        except ImportError:
            logger.warning(
                "langchain not installed; using simple character chunking. "
                "Run: pip install langchain for better chunking."
            )
            _splitter = _SimpleSplitter(CHUNK_SIZE, CHUNK_OVERLAP)
    return _splitter


class _SimpleSplitter:
    """Fallback splitter when langchain is not available."""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
        return [c for c in chunks if c.strip()]


def load_pdf(path: str) -> List[str]:
    """Extract text from PDF, one string per page."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed; PDF parsing disabled. Run: pip install PyMuPDF")
        return []
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text)
    doc.close()
    return pages


def load_txt(path: str) -> List[str]:
    """Load a plain text or Markdown file."""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return [f.read()]
        except UnicodeDecodeError:
            continue
    return []


def load_file(path: str) -> List[str]:
    """Load any supported file → list of text segments (one per page/section).

    Supported: .pdf, .txt, .md
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return load_pdf(path)
    elif ext in (".txt", ".md"):
        return load_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext} (supported: .pdf, .txt, .md)")


def chunk_text(text: str) -> List[str]:
    """Split a text block into overlapping chunks."""
    return _get_splitter().split_text(text)


def load_and_chunk(path: str, extra_meta: Optional[Dict] = None) -> List[Dict]:
    """Load a file and split it into chunks with metadata.

    Returns: [{"text": "...", "meta": {"page": 0, "source": "...", ...}}]
    """
    segments = load_file(path)
    filename = os.path.basename(path)
    chunks = []
    splitter = _get_splitter()
    for page_idx, text in enumerate(segments):
        for chunk in splitter.split_text(text):
            meta = {"page": page_idx, "source": filename}
            if extra_meta:
                meta.update(extra_meta)
            chunks.append({"text": chunk, "meta": meta})
    logger.info("Loaded %s → %d chunks", filename, len(chunks))
    return chunks


def chunk_text_block(text: str, title: str = "", extra_meta: Optional[Dict] = None) -> List[Dict]:
    """Chunk a raw text block (e.g. a generated research report) for ingestion.

    This is used by research_skill.py to auto-ingest generated reports.
    """
    splitter = _get_splitter()
    chunks = []
    for c in splitter.split_text(text):
        meta = {"source": title or "generated"}
        if extra_meta:
            meta.update(extra_meta)
        chunks.append({"text": c, "meta": meta})
    return chunks
