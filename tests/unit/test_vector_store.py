import numpy as np
import pytest

from indexing.vector_store import FaissVectorStore


def _unit_vectors(rows: int, dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(rows, dim)).astype("float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors


def test_search_on_empty_store_returns_empty_list():
    store = FaissVectorStore(dim=4)

    results = store.search(np.zeros((1, 4), dtype="float32"), k=5)

    assert results == []


def test_add_and_search_returns_nearest_chunk_with_score():
    store = FaissVectorStore(dim=3)
    chunks = [
        {"doc_id": "a", "text": "alpha"},
        {"doc_id": "b", "text": "beta"},
    ]
    embeddings = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype="float32",
    )
    store.add(chunks, embeddings)

    results = store.search(np.array([[1.0, 0.0, 0.0]], dtype="float32"), k=1)

    assert len(results) == 1
    assert results[0]["doc_id"] == "a"
    assert "score" in results[0]
    assert results[0]["score"] == pytest.approx(1.0, abs=1e-5)


def test_search_k_is_capped_at_index_size():
    store = FaissVectorStore(dim=3)
    store.add(
        [{"doc_id": "a"}, {"doc_id": "b"}],
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype="float32"),
    )

    results = store.search(np.array([[1.0, 0.0, 0.0]], dtype="float32"), k=10)

    assert len(results) == 2


def test_add_rejects_mismatched_chunk_and_embedding_counts():
    store = FaissVectorStore(dim=3)

    with pytest.raises(ValueError):
        store.add(
            [{"doc_id": "a"}, {"doc_id": "b"}],
            np.array([[1.0, 0.0, 0.0]], dtype="float32"),
        )


def test_add_rejects_wrong_dimension():
    store = FaissVectorStore(dim=3)

    with pytest.raises(ValueError):
        store.add([{"doc_id": "a"}], np.array([[1.0, 0.0]], dtype="float32"))


def test_search_orders_results_by_similarity_descending():
    store = FaissVectorStore(dim=8)
    embeddings = _unit_vectors(5, 8, seed=1)
    chunks = [{"doc_id": f"doc_{i}"} for i in range(5)]
    store.add(chunks, embeddings)

    query = embeddings[2:3]
    results = store.search(query, k=5)

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["doc_id"] == "doc_2"


def test_original_chunk_dict_is_not_mutated():
    store = FaissVectorStore(dim=3)
    chunk = {"doc_id": "a"}
    store.add([chunk], np.array([[1.0, 0.0, 0.0]], dtype="float32"))

    store.search(np.array([[1.0, 0.0, 0.0]], dtype="float32")),

    assert "score" not in chunk
