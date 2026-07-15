"""Real end-to-end integration tests for the RetrieverAgent ->
ComplianceAgent -> ExplanationAgent pipeline.

Runs the actual pipeline over the full golden + adversarial dataset
(evaluation/test_cases.py, 33 + 5 = 38 queries) against a real in-memory
FAISS index (per CLAUDE.md: "Never mock the FAISS vector store in
integration tests -- use a real in-memory index"), and scores the result
with the real EvaluationMetrics faithfulness/hallucination logic.

Two pieces are test doubles, and both are necessary and documented rather
than hidden:

1. The embedding function. The production embedder
   (sentence-transformers/all-MiniLM-L6-v2, per configs/base.yaml)
   requires a ~90MB model download on first use, which this test suite
   avoids for hermetic/offline CI runs. `_lexical_embed` is a real,
   deterministic TF-IDF-style bag-of-words embedding -- not a mock of
   FAISS or of the agents, just a lighter-weight embedding technique than
   the production model, following the same precedent already set by
   `tests/unit/test_metrics.py`'s `fake_embed`. It is measurably worse at
   semantic matching than a real sentence embedding model (see
   `test_retrieval_finds_correct_document` below, threshold documented
   inline) -- that gap is expected and is a real limitation of lexical
   embeddings on paraphrased queries, not a bug in the pipeline.

2. The LLM client. ExplanationAgent refuses to run without a real
   `llm_client` (agents/explanation_agent.py's `_call_llm` has no stub
   fallback by design, so a real OPENAI_API_KEY is required for
   scripts/run_evaluation.py). `_ExtractiveTestLLM` stands in for that
   here: it is wired in through the exact same
   `client.chat.completions.create(...)` shape ExplanationAgent expects
   (see tests/unit/test_explanation_agent.py's `_FakeLLMClient`), and it
   answers *only* using sentences copied from the retrieved context --
   modeling a well-behaved LLM that never asserts a fact absent from
   context, per the system prompt in
   ExplanationAgent._call_llm. It does not fabricate ungrounded content,
   so it cannot be used to claim a specific hallucination rate for the
   real (LLM-backed) system -- getting that number requires running
   scripts/run_evaluation.py with a real OPENAI_API_KEY, which these tests
   do not have access to.

What this test suite *does* verify for real: the three agents are wired
together correctly, retrieval runs against real (if imperfect, given the
lexical substitute) semantic search rather than being bypassed with oracle
context, the compliance classification is scored against ground truth
("compliance accuracy" per .claude/skills/evaluate.md), and the
faithfulness/hallucination scoring machinery in evaluation/metrics.py
produces internally consistent numbers over a 38-query set large enough
for percentage-point granularity to mean something.
"""

import math
import re
from typing import Dict, List

import numpy as np
import pytest

from agents.compliance_agent import ComplianceAgent
from agents.explanation_agent import ExplanationAgent
from agents.retriever_agent import RetrieverAgent
from evaluation.metrics import EvaluationMetrics
from evaluation.test_cases import AdversarialTestSuite, TestSetGenerator
from indexing.vector_store import FaissVectorStore

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NO_CONTEXT_ANSWER = (
    "I do not have enough information in the retrieved context to answer this."
)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class _LexicalEmbedder:
    """TF-IDF-weighted bag-of-words embedding, fit once on the corpus of
    context chunk texts. See module docstring: a real, deterministic
    embedding technique used as an offline-friendly stand-in for the
    production SentenceTransformer model, not a mock of anything.
    """

    def __init__(self, corpus_texts: List[str]):
        doc_freq: Dict[str, int] = {}
        for text in corpus_texts:
            for word in set(_tokenize(text)):
                doc_freq[word] = doc_freq.get(word, 0) + 1
        n_docs = len(corpus_texts)
        self._vocab = {word: i for i, word in enumerate(sorted(doc_freq))}
        self._idf = np.array(
            [math.log((n_docs + 1) / (doc_freq[w] + 1)) + 1 for w in sorted(doc_freq)]
        )

    @property
    def dim(self) -> int:
        return len(self._vocab)

    def __call__(self, texts: List[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype="float32")
        for row, text in enumerate(texts):
            counts: Dict[str, int] = {}
            for word in _tokenize(text):
                counts[word] = counts.get(word, 0) + 1
            for word, count in counts.items():
                idx = self._vocab.get(word)
                if idx is not None:
                    vectors[row, idx] = count * self._idf[idx]
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _ExtractiveTestLLM:
    """Test double for a real LLM API (see module docstring, point 2)."""

    class _Completions:
        def create(self, **kwargs):
            prompt = kwargs["messages"][-1]["content"]
            return _FakeResponse(_ExtractiveTestLLM._answer_from_prompt(prompt))

    class _Chat:
        def __init__(self):
            self.completions = _ExtractiveTestLLM._Completions()

    def __init__(self):
        self.chat = _ExtractiveTestLLM._Chat()

    @staticmethod
    def _answer_from_prompt(prompt: str) -> str:
        marker = "Context:\n"
        if marker not in prompt:
            return _NO_CONTEXT_ANSWER
        context_block = prompt.split(marker, 1)[1].split("\n\nCompliance notes:")[0]

        # _build_context (agents/explanation_agent.py) joins chunks as
        # "[Doc: ..., Section: ...]\n{text}", separated by blank lines.
        # Use only the top-ranked (first) chunk's actual text, and split
        # on ". "/"! "/"? " (matching EvaluationMetrics._split_sentences'
        # own lookbehind regex) rather than every literal period, so an
        # abbreviation inside a section label in the header line (e.g.
        # "Ch. 4") can't be mistaken for a sentence boundary in the text.
        top_block = next((b for b in context_block.split("\n\n") if b.strip()), "")
        _, _, text = top_block.partition("]\n")
        text = text.strip() or top_block.strip()

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return _NO_CONTEXT_ANSWER
        return " ".join(sentences[:2])


@pytest.fixture(scope="module")
def golden_cases() -> List[Dict]:
    return TestSetGenerator.get_golden_dataset()


@pytest.fixture(scope="module")
def adversarial_cases() -> List[Dict]:
    return AdversarialTestSuite.get_test_cases()


@pytest.fixture(scope="module")
def embedder(golden_cases) -> _LexicalEmbedder:
    corpus_texts = [
        chunk["text"] for case in golden_cases for chunk in case["context_chunks"]
    ]
    return _LexicalEmbedder(corpus_texts)


@pytest.fixture(scope="module")
def vector_store(golden_cases, embedder) -> FaissVectorStore:
    chunks = [chunk for case in golden_cases for chunk in case["context_chunks"]]
    store = FaissVectorStore(dim=embedder.dim)
    embeddings = embedder([c["text"] for c in chunks])
    store.add(chunks, embeddings)
    return store


def _run_case(retriever, compliance_agent, explanation_agent, embedder, case) -> Dict:
    query = case["query"]
    query_embedding = embedder([query])[0]

    retrieval = retriever.execute({"query": query, "query_embedding": query_embedding})
    retrieved_chunks = retrieval["retrieved_chunks"]

    compliance = compliance_agent.execute(
        {"query": query, "retrieved_chunks": retrieved_chunks}
    )

    explanation = explanation_agent.execute(
        {
            "query": query,
            "retrieved_chunks": retrieved_chunks,
            "compliance": compliance,
            "retrieval_confidence": retrieval["confidence"],
        }
    )

    return {
        "name": case["name"],
        "answer": explanation["answer"],
        "citations": explanation["citations"],
        "context_chunks": retrieved_chunks,
        "predicted_risk_level": compliance["risk_level"],
        "gold_risk_level": case.get("compliance", {}).get("risk_level"),
        "top1_doc_id": retrieved_chunks[0]["doc_id"] if retrieved_chunks else None,
        "top1_section": retrieved_chunks[0]["section"] if retrieved_chunks else None,
    }


def test_retrieval_finds_correct_document(golden_cases, embedder, vector_store):
    """Real RetrieverAgent + real FAISS index: for each golden query, is
    the gold chunk the top-1 result among all 33 pooled chunks (i.e. real
    distractors, not a per-query oracle context)?

    Threshold is deliberately loose (>= 50%). The lexical embedder (see
    module docstring) has no notion of synonymy or paraphrase -- e.g. a
    query asking about the "Net Stable Funding Ratio" using CRR's exact
    Article number will beat one phrased more generically, purely on word
    overlap. A real semantic embedding model is expected to do
    substantially better; this threshold protects against a wiring
    regression (e.g. retrieval always returning the same chunk, or FAISS
    scores being computed incorrectly), not a claim about production
    retrieval quality.
    """
    retriever = RetrieverAgent(vector_store, top_k=3)

    correct = 0
    for case in golden_cases:
        query_embedding = embedder([case["query"]])[0]
        result = retriever.execute(
            {"query": case["query"], "query_embedding": query_embedding}
        )
        assert result["retrieved_chunks"], f"no chunks retrieved for {case['name']}"
        top = result["retrieved_chunks"][0]
        gold = case["context_chunks"][0]
        if (top["doc_id"], top["section"]) == (gold["doc_id"], gold["section"]):
            correct += 1

    accuracy = correct / len(golden_cases)
    assert accuracy >= 0.5, (
        f"retrieval top-1 accuracy {accuracy:.2%} fell below the wiring-"
        f"regression floor of 50% (lexical embedder, {len(golden_cases)} queries)"
    )


def test_end_to_end_pipeline(golden_cases, adversarial_cases, embedder, vector_store):
    """Full Retriever -> Compliance -> Explanation -> Metrics chain over
    all 38 queries. Asserts the pipeline produces a well-formed report and
    prints the resulting hallucination rate for visibility -- this is not
    asserted against a specific target value. See module docstring: with a
    well-behaved test LLM that only ever echoes retrieved context, a low
    hallucination rate here reflects that the *metric plumbing* is
    working, not a measurement of the real (LLM-backed) system's
    faithfulness. Getting that requires scripts/run_evaluation.py with a
    real OPENAI_API_KEY.
    """
    retriever = RetrieverAgent(vector_store, top_k=3)
    compliance_agent = ComplianceAgent(regulations=["gdpr", "mifid", "psd2"])
    explanation_agent = ExplanationAgent(_ExtractiveTestLLM(), model="test-extractive")

    metrics = EvaluationMetrics(embed_fn=embedder, faithfulness_threshold=0.2)

    results = [
        _run_case(retriever, compliance_agent, explanation_agent, embedder, case)
        for case in golden_cases + adversarial_cases
    ]
    metrics.results = results

    report = metrics.generate_report()

    assert report["total_queries"] == len(golden_cases) + len(adversarial_cases) == 38
    assert 0.0 <= report["hallucination_rate"] <= 1.0
    assert 0.0 <= report["citation_coverage"] <= 1.0
    assert report["mean_faithfulness"] is not None
    assert 0.0 <= report["mean_faithfulness"] <= 1.0

    labeled = [r for r in results if r["gold_risk_level"] is not None]
    assert len(labeled) == len(golden_cases)
    compliance_accuracy = sum(
        1 for r in labeled if r["predicted_risk_level"] == r["gold_risk_level"]
    ) / len(labeled)
    # All 33 gold labels were generated from ComplianceAgent's own (fixed)
    # logic (see evaluation/test_cases.py docstring), so this should be
    # exactly 1.0 -- a genuine deviation here means either the golden
    # labels or ComplianceAgent's classification logic drifted.
    assert compliance_accuracy == 1.0

    print(f"\n[integration] total_queries={report['total_queries']}")
    print(f"[integration] hallucination_rate={report['hallucination_rate']:.4f}")
    print(f"[integration] citation_coverage={report['citation_coverage']:.4f}")
    print(f"[integration] mean_faithfulness={report['mean_faithfulness']:.4f}")
    print(f"[integration] compliance_accuracy={compliance_accuracy:.4f}")


def test_pipeline_flags_a_fabricated_answer(vector_store, embedder):
    """Guard against the blind spot in test_end_to_end_pipeline above: an
    always-grounded test LLM would pass that test even if
    calculate_faithfulness had a bug that always returned "supported"
    regardless of input. This runs the real chain with an LLM double that
    answers with a claim absent from the retrieved context, and checks the
    metrics module actually catches it through the full pipeline (not just
    in the unit tests in tests/unit/test_metrics.py, which call
    calculate_faithfulness directly rather than via Retriever/Compliance/
    Explanation).
    """

    class _FabricatingLLM:
        class _Completions:
            def create(self, **kwargs):
                return _FakeResponse(
                    "The Basel Committee requires all banks to hold gold "
                    "reserves equal to 50% of deposits, effective 2030."
                )

        class _Chat:
            def __init__(self):
                self.completions = _FabricatingLLM._Completions()

        def __init__(self):
            self.chat = _FabricatingLLM._Chat()

    retriever = RetrieverAgent(vector_store, top_k=3)
    compliance_agent = ComplianceAgent(regulations=["psd2"])
    explanation_agent = ExplanationAgent(_FabricatingLLM(), model="test-fabricating")

    query = "Does PSD2 require strong customer authentication for electronic payments?"
    result = _run_case(
        retriever,
        compliance_agent,
        explanation_agent,
        embedder,
        {"name": "fabrication_probe", "query": query},
    )

    metrics = EvaluationMetrics(embed_fn=embedder, faithfulness_threshold=0.2)
    faithfulness = metrics.calculate_faithfulness(
        result["answer"], result["context_chunks"]
    )
    assert faithfulness["unsupported_sentences"] != []
    assert faithfulness["faithfulness_score"] < 1.0

    hallucination_rate = metrics.calculate_hallucination_rate([result])
    assert hallucination_rate == 1.0


def test_agent_orchestration(vector_store, embedder):
    """Narrow, exact-value trace of a single query through all three
    agents, checking the handoff between them rather than aggregate
    statistics: RetrieverAgent's output feeds ComplianceAgent and
    ExplanationAgent's inputs correctly, and the citation returned
    actually matches what was retrieved (not the gold chunk).
    """
    retriever = RetrieverAgent(vector_store, top_k=3)
    compliance_agent = ComplianceAgent(regulations=["psd2"])
    explanation_agent = ExplanationAgent(_ExtractiveTestLLM(), model="test-extractive")

    query = "Does PSD2 require strong customer authentication for electronic payments?"
    query_embedding = embedder([query])[0]

    retrieval = retriever.execute({"query": query, "query_embedding": query_embedding})
    assert retrieval["agent"] == "Retriever"
    assert retrieval["retrieved_chunks"]
    top_chunk = retrieval["retrieved_chunks"][0]
    assert top_chunk["doc_id"] == "psd2_2015"
    assert top_chunk["section"] == "Article 97"

    compliance = compliance_agent.execute(
        {"query": query, "retrieved_chunks": retrieval["retrieved_chunks"]}
    )
    assert compliance["agent"] == "Compliance"
    assert compliance["risk_level"] == "MEDIUM"
    assert "psd2" in compliance["regulatory_flags"]
    assert compliance["requires_review"] is False

    explanation = explanation_agent.execute(
        {
            "query": query,
            "retrieved_chunks": retrieval["retrieved_chunks"],
            "compliance": compliance,
            "retrieval_confidence": retrieval["confidence"],
        }
    )
    assert explanation["agent"] == "Explanation"
    assert explanation["citations"][0]["doc_id"] == "psd2_2015"
    assert explanation["citations"][0]["section"] == "Article 97"

    faithfulness = EvaluationMetrics(embed_fn=embedder).calculate_faithfulness(
        explanation["answer"], retrieval["retrieved_chunks"]
    )
    assert faithfulness["unsupported_sentences"] == []
