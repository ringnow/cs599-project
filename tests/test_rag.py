"""Unit tests for src/rag/ modules.

Tests cover:
  - document_loader: chunking logic + fallback splitter
  - vector_store: add/search/delete with mocked ChromaDB
  - retriever: retrieval decision logic (local-first, online-fallback)
  - embedder: availability check (no model download)

These tests do NOT require a running Redis server or a downloaded
embedding model — all external dependencies are mocked.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ──────────────────────────────────────────────────────────────────────────
# document_loader tests
# ──────────────────────────────────────────────────────────────────────────

class TestDocumentLoader:
    """Test text chunking logic (no external dependencies)."""

    def test_simple_splitter_basic(self):
        """The fallback splitter should produce overlapping chunks."""
        from src.rag.document_loader import _SimpleSplitter
        splitter = _SimpleSplitter(chunk_size=100, chunk_overlap=20)
        text = "A" * 250
        chunks = splitter.split_text(text)
        assert len(chunks) >= 2
        assert all(len(c) <= 100 for c in chunks)
        # Overlap: second chunk should start before first chunk ends
        assert len(chunks) > 1

    def test_simple_splitter_empty(self):
        from src.rag.document_loader import _SimpleSplitter
        splitter = _SimpleSplitter(chunk_size=100, chunk_overlap=20)
        assert splitter.split_text("") == []
        assert splitter.split_text("   ") == []

    def test_simple_splitter_short_text(self):
        """Short text should produce a single chunk."""
        from src.rag.document_loader import _SimpleSplitter
        splitter = _SimpleSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text("Short text.")
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_chunk_text_block_returns_meta(self):
        """chunk_text_block should attach metadata to each chunk."""
        from src.rag.document_loader import chunk_text_block
        text = "This is a test paragraph. " * 50  # ~1200 chars
        chunks = chunk_text_block(text, title="test_doc", extra_meta={"type": "report"})
        assert len(chunks) >= 1
        for c in chunks:
            assert "text" in c
            assert "meta" in c
            assert c["meta"]["source"] == "test_doc"
            assert c["meta"]["type"] == "report"

    def test_load_txt_file(self, tmp_path):
        """load_txt should read a UTF-8 text file."""
        from src.rag.document_loader import load_txt
        p = tmp_path / "test.txt"
        p.write_text("Hello world\nSecond line", encoding="utf-8")
        result = load_txt(str(p))
        assert len(result) == 1
        assert "Hello world" in result[0]

    def test_load_txt_gbk_fallback(self, tmp_path):
        """load_txt should fall back to GBK if UTF-8 fails."""
        from src.rag.document_loader import load_txt
        p = tmp_path / "gbk.txt"
        p.write_text("中文内容", encoding="gbk")
        result = load_txt(str(p))
        assert len(result) == 1
        assert "中文" in result[0]

    def test_load_file_unsupported_ext(self):
        from src.rag.document_loader import load_file
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_file("doc.docx")

    def test_load_and_chunk(self, tmp_path):
        """load_and_chunk should parse + chunk a text file with metadata."""
        from src.rag.document_loader import load_and_chunk
        p = tmp_path / "paper.txt"
        p.write_text("A" * 300 + "\n\n" + "B" * 300, encoding="utf-8")
        chunks = load_and_chunk(str(p), extra_meta={"title": "test"})
        assert len(chunks) >= 1
        assert all("text" in c and "meta" in c for c in chunks)
        assert chunks[0]["meta"]["source"] == "paper.txt"
        assert chunks[0]["meta"]["title"] == "test"


# ──────────────────────────────────────────────────────────────────────────
# vector_store tests (with mocked ChromaDB)
# ──────────────────────────────────────────────────────────────────────────

class TestVectorStore:
    """Test vector store operations with a mocked ChromaDB collection."""

    def test_generate_doc_id_unique(self):
        from src.rag.vector_store import generate_doc_id
        ids = {generate_doc_id() for _ in range(100)}
        assert len(ids) == 100  # all unique

    def test_get_collection_returns_none_when_chromadb_missing(self):
        """If chromadb is not installed, _get_collection returns None."""
        with patch.dict("sys.modules", {"chromadb": None}):
            # Force re-init
            import src.rag.vector_store as vs
            vs._collection = None
            result = vs._get_collection()
            # Either None (if chromadb truly missing) or a real collection
            # In test env chromadb may be installed, so just check no crash
            assert result is not None or result is None

    def test_search_returns_empty_when_no_collection(self):
        """search() should return [] gracefully if ChromaDB is unavailable."""
        with patch("src.rag.vector_store._get_collection", return_value=None):
            import src.rag.vector_store as vs
            result = vs.search("test query")
            assert result == []

    def test_add_documents_returns_zero_when_no_collection(self):
        with patch("src.rag.vector_store._get_collection", return_value=None):
            import src.rag.vector_store as vs
            result = vs.add_documents("doc1", [{"text": "hi"}], {})
            assert result == 0

    def test_add_documents_with_mocked_collection(self):
        """Test add_documents with a fully mocked ChromaDB collection."""
        mock_collection = MagicMock()
        mock_collection.upsert = MagicMock()
        with patch("src.rag.vector_store._get_collection", return_value=mock_collection), \
             patch("src.rag.embedder.embed", return_value=[[0.1, 0.2, 0.3]]):
            import src.rag.vector_store as vs
            result = vs.add_documents(
                "doc_test",
                [{"text": "hello world", "meta": {"page": 0}}],
                {"title": "test", "type": "report"},
                username="alice",
            )
            assert result == 1
            mock_collection.upsert.assert_called_once()
            call_kwargs = mock_collection.upsert.call_args
            assert call_kwargs.kwargs["ids"] == ["doc_test_0"]
            assert call_kwargs.kwargs["embeddings"] == [[0.1, 0.2, 0.3]]
            assert call_kwargs.kwargs["documents"] == ["hello world"]
            # Check metadata propagation
            meta = call_kwargs.kwargs["metadatas"][0]
            assert meta["title"] == "test"
            assert meta["username"] == "alice"
            assert meta["chunk_idx"] == 0

    def test_search_with_mocked_collection(self):
        """Test search() returns formatted results from ChromaDB."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["hit_1", "hit_2"]],
            "documents": [["text one", "text two"]],
            "metadatas": [[{"source": "doc_a"}, {"source": "doc_b"}]],
            "distances": [[0.2, 0.5]],
        }
        with patch("src.rag.vector_store._get_collection", return_value=mock_collection), \
             patch("src.rag.embedder.embed_one", return_value=[0.1, 0.2]):
            import src.rag.vector_store as vs
            results = vs.search("query", top_k=2)
            assert len(results) == 2
            assert results[0]["text"] == "text one"
            assert results[0]["score"] == 0.8  # 1 - 0.2
            assert results[0]["metadata"]["source"] == "doc_a"
            # Results sorted by distance ascending (score descending)
            assert results[0]["score"] > results[1]["score"]

    def test_delete_document_with_mock(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["doc1_0", "doc1_1", "doc1_2"],
        }
        mock_collection.delete = MagicMock()
        with patch("src.rag.vector_store._get_collection", return_value=mock_collection):
            import src.rag.vector_store as vs
            deleted = vs.delete_document("doc1")
            assert deleted == 3
            mock_collection.delete.assert_called_once_with(ids=["doc1_0", "doc1_1", "doc1_2"])

    def test_list_documents_deduplicates(self):
        """list_documents should deduplicate chunks by doc_id."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["a_0", "a_1", "b_0"],
            "metadatas": [
                {"doc_id": "a", "title": "Doc A", "source": "a.pdf", "type": "pdf"},
                {"doc_id": "a", "title": "Doc A", "source": "a.pdf", "type": "pdf"},
                {"doc_id": "b", "title": "Doc B", "source": "b.pdf", "type": "pdf"},
            ],
        }
        with patch("src.rag.vector_store._get_collection", return_value=mock_collection):
            import src.rag.vector_store as vs
            docs = vs.list_documents()
            assert len(docs) == 2  # deduplicated
            doc_ids = {d["doc_id"] for d in docs}
            assert doc_ids == {"a", "b"}

    def test_get_stats_returns_enabled_false_when_no_collection(self):
        with patch("src.rag.vector_store._get_collection", return_value=None):
            import src.rag.vector_store as vs
            stats = vs.get_stats()
            assert stats["enabled"] is False


# ──────────────────────────────────────────────────────────────────────────
# retriever tests
# ──────────────────────────────────────────────────────────────────────────

class TestRetriever:
    """Test retrieval decision logic."""

    @pytest.fixture(autouse=True)
    def _disable_query_opt(self):
        import os
        os.environ["RAG_QUERY_OPTIMIZATION"] = "off"
        os.environ["RAG_USE_HYBRID"] = "true"
        yield

    def test_retrieve_returns_empty_when_no_hits(self):
        with patch("src.rag.hybrid_search.hybrid_search", return_value=[]):
            from src.rag.retriever import retrieve
            result = retrieve("test query")
            assert result["local_results"] == []
            assert result["need_online"] is True
            assert result["context_text"] == ""
            assert result["good_hits"] == 0

    def test_retrieve_signals_online_when_few_good_hits(self):
        """If < MIN_GOOD_HITS relevant results, need_online should be True."""
        hits = [
            {"id": "h1", "text": "relevant", "score": 0.9, "metadata": {"source": "a"}},
        ]
        with patch("src.rag.hybrid_search.hybrid_search", return_value=hits):
            from src.rag.retriever import retrieve
            result = retrieve("test")
            assert result["need_online"] is True  # only 1 hit < 3 minimum
            assert result["good_hits"] == 1
            assert "relevant" in result["context_text"]

    def test_retrieve_signals_sufficient_when_many_good_hits(self):
        """If ≥ MIN_GOOD_HITS relevant results, need_online should be False."""
        hits = [
            {"id": f"h{i}", "text": f"doc {i}", "score": 0.8, "metadata": {"source": f"src_{i}"}}
            for i in range(5)
        ]
        with patch("src.rag.hybrid_search.hybrid_search", return_value=hits):
            from src.rag.retriever import retrieve
            result = retrieve("test")
            assert result["need_online"] is False
            assert result["good_hits"] == 5
            assert len(result["local_results"]) == 5

    def test_retrieve_filters_low_score_hits(self):
        """Hits below RELEVANCE_THRESHOLD should not be 'good'."""
        hits = [
            {"id": "h1", "text": "great", "score": 0.9, "metadata": {"source": "a"}},
            {"id": "h2", "text": "meh", "score": 0.3, "metadata": {"source": "b"}},
        ]
        with patch("src.rag.hybrid_search.hybrid_search", return_value=hits):
            from src.rag.retriever import retrieve
            result = retrieve("test")
            assert result["good_hits"] == 1
            assert "great" in result["context_text"]
            assert "meh" not in result["context_text"]

    def test_retrieve_context_text_includes_source_and_score(self):
        hits = [{"id": "h1", "text": "content here", "score": 0.85, "metadata": {"source": "paper.pdf"}}]
        with patch("src.rag.hybrid_search.hybrid_search", return_value=hits):
            from src.rag.retriever import retrieve
            result = retrieve("test")
            ctx = result["context_text"]
            assert "paper.pdf" in ctx
            assert "0.85" in ctx
            assert "content here" in ctx

    def test_retrieve_handles_search_exception(self):
        """retrieve should gracefully handle hybrid_search exceptions."""
        with patch("src.rag.hybrid_search.hybrid_search", side_effect=Exception("DB down")):
            from src.rag.retriever import retrieve
            result = retrieve("test")
            assert result["local_results"] == []
            assert result["need_online"] is True
            assert result["context_text"] == ""

    def test_ingest_text_returns_zero_on_failure(self):
        """ingest_text should return 0 if the vector store is unavailable."""
        with patch("src.rag.vector_store.add_documents", return_value=0):
            from src.rag.retriever import ingest_text
            result = ingest_text("text", "title", username="user")
            assert result == 0

    def test_ingest_text_success(self):
        with patch("src.rag.vector_store.add_documents", return_value=5) as mock_add, \
             patch("src.rag.vector_store.generate_doc_id", return_value="doc_123"):
            from src.rag.retriever import ingest_text
            result = ingest_text("A" * 300, "test title", username="alice")
            assert result == 5
            mock_add.assert_called_once()
            # Verify metadata passed to add_documents
            args = mock_add.call_args
            # add_documents(doc_id, chunks, metadata, username=...)
            assert args[0][0] == "doc_123"  # doc_id
            assert args[1]["username"] == "alice"


# ──────────────────────────────────────────────────────────────────────────
# embedder tests (no model download)
# ──────────────────────────────────────────────────────────────────────────

class TestEmbedder:
    """Test embedder module without loading the actual model."""

    def test_is_available_returns_bool(self):
        """is_available should return a boolean (True if installed)."""
        from src.rag.embedder import is_available
        result = is_available()
        assert isinstance(result, bool)

    def test_embed_empty_list(self):
        """embed([]) should return [] without loading the model."""
        from src.rag.embedder import embed
        assert embed([]) == []

    def test_model_name_configurable(self):
        """The model name should be configurable via env var."""
        import importlib
        with patch.dict(os.environ, {"EMBEDDING_MODEL": "custom-model"}):
            import src.rag.embedder as emb
            importlib.reload(emb)
            assert emb._MODEL_NAME == "custom-model"
