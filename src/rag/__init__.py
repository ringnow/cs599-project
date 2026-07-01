"""RAG (Retrieval-Augmented Generation) module for CS599.

Submodules:
  - embedder:         Sentence-transformers embedding model (lazy singleton)
  - vector_store:     ChromaDB persistent vector store
  - document_loader:  PDF/TXT/Word parsing + recursive chunking
  - retriever:        Retrieval decision maker (hybrid search + query optimization)
  - hybrid_search:    BM25 + vector + rerank fusion
  - query_optimizer:  Query rewriting, HyDE, multi-query expansion
"""
