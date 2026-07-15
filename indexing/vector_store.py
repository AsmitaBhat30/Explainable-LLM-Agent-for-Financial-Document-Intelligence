"""In-memory FAISS-backed vector store.

RetrieverAgent (agents/retriever_agent.py) expects to be handed a
`vector_store` object exposing `.search(query_embedding, k) -> List[Dict]`,
where each result dict carries a `score` plus the retrieved chunk's
metadata. Nothing in the codebase actually implemented that interface --
transformation/embed_all_documents.py builds embeddings and
scripts/query_system.py talks to a raw faiss.Index directly, but the two
were never wired together behind the interface RetrieverAgent expects. This
fills that gap so retrieval can actually be exercised end-to-end instead of
being bypassed (as evaluation/test_cases.py's gold `context_chunks` were
being fed straight into ExplanationAgent).
"""

from typing import Dict, List, Sequence

import faiss
import numpy as np


class FaissVectorStore:
    """Exact (non-approximate) cosine-similarity search over an in-memory
    FAISS index.

    Uses `IndexFlatIP` over L2-normalized vectors, i.e. cosine similarity.
    configs/base.yaml names an IVF index (`vector_store.index_type: IVF`),
    which trades exactness for speed on large corpora via clustering; that
    optimization isn't needed for the corpus sizes exercised in tests and
    evaluation, so the flat (exact) index is used here. Swapping in
    `faiss.IndexIVFFlat` behind the same `.add` / `.search` interface would
    apply that optimization for a large production corpus without changing
    any caller.
    """

    def __init__(self, dim: int):
        if dim <= 0:
            raise ValueError(f"dim must be positive, got {dim}")
        self.dim = dim
        self._index = faiss.IndexFlatIP(dim)
        self._chunks: List[Dict] = []

    @property
    def ntotal(self) -> int:
        return self._index.ntotal

    def add(self, chunks: Sequence[Dict], embeddings: np.ndarray) -> None:
        """Index `chunks`, each embedded by the corresponding row of
        `embeddings`. Chunk dicts are stored as-is (e.g. doc_id, section,
        text, page_range) and returned alongside their score on search.
        """
        vectors = np.array(embeddings, dtype="float32", copy=True)
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"Expected embeddings of shape (n, {self.dim}), got {vectors.shape}"
            )
        if vectors.shape[0] != len(chunks):
            raise ValueError(
                f"Got {len(chunks)} chunks but {vectors.shape[0]} embeddings"
            )
        if vectors.shape[0] == 0:
            return
        faiss.normalize_L2(vectors)
        self._index.add(vectors)
        self._chunks.extend(dict(c) for c in chunks)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict]:
        """Return up to `k` chunks most similar to `query_embedding`, each
        with a `score` key (cosine similarity, higher is better) merged in.
        Returns [] if the store is empty rather than raising, so callers
        (e.g. RetrieverAgent) can treat "no index built yet" the same as
        "no matches found".
        """
        if self._index.ntotal == 0:
            return []

        query = np.array(np.atleast_2d(query_embedding), dtype="float32", copy=True)
        if query.shape[1] != self.dim:
            raise ValueError(
                f"Expected query embedding of dim {self.dim}, got {query.shape[1]}"
            )
        faiss.normalize_L2(query)

        k = min(k, self._index.ntotal)
        scores, indices = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = dict(self._chunks[idx])
            chunk["score"] = float(score)
            results.append(chunk)
        return results
