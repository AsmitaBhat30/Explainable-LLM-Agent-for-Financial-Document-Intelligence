import logging
import re
import time
from typing import Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

EmbedFn = Callable[[List[str]], np.ndarray]


def _split_sentences(text: str) -> List[str]:
    """Naive sentence splitter — sufficient for faithfulness scoring."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class EvaluationMetrics:
    def __init__(
        self,
        embed_fn: Optional[EmbedFn] = None,
        faithfulness_threshold: float = 0.5,
    ):
        """
        embed_fn: maps a list of strings to an (n, d) array of embeddings in a
            shared vector space, e.g.
            SentenceTransformer("all-MiniLM-L6-v2").encode. Required for
            calculate_faithfulness / a real calculate_hallucination_rate;
            without it, hallucination rate falls back to a citation-presence
            proxy (see calculate_hallucination_rate).
        faithfulness_threshold: minimum cosine similarity between an answer
            sentence and its best-matching context chunk for that sentence to
            count as grounded.
        """
        self.results: List[Dict] = []
        self.embed_fn = embed_fn
        self.faithfulness_threshold = faithfulness_threshold

    def calculate_faithfulness(self, answer: str, context_chunks: List[Dict]) -> Dict:
        """Groundedness check: does every claim in the answer have support
        in the retrieved context?

        Splits the answer into sentences and embeds each one alongside the
        retrieved chunk text (in a single embed_fn call, so both live in the
        same vector space), then flags any sentence whose best-matching
        chunk falls below faithfulness_threshold as unsupported. This is a
        proxy for faithfulness/groundedness (per-sentence, not a full NLI
        entailment check) but unlike citation-presence it actually looks at
        whether the generated text matches the retrieved content.
        """
        if self.embed_fn is None:
            raise ValueError(
                "calculate_faithfulness requires an embed_fn (e.g. "
                "SentenceTransformer('all-MiniLM-L6-v2').encode) — none was "
                "provided to EvaluationMetrics()."
            )

        sentences = _split_sentences(answer)
        if not sentences:
            return {
                "faithfulness_score": 0.0,
                "unsupported_sentences": [],
                "total_sentences": 0,
            }

        context_texts = [c.get("text", "") for c in context_chunks if c.get("text")]
        if not context_texts:
            return {
                "faithfulness_score": 0.0,
                "unsupported_sentences": sentences,
                "total_sentences": len(sentences),
            }

        # Embed sentences and context together so they land in one
        # consistent vector space, regardless of embed_fn implementation.
        all_vecs = np.atleast_2d(np.asarray(self.embed_fn(sentences + context_texts)))
        sentence_vecs = all_vecs[: len(sentences)]
        context_vecs = all_vecs[len(sentences) :]

        unsupported = []
        supported_count = 0
        for sentence, svec in zip(sentences, sentence_vecs):
            best_sim = max(_cosine_sim(svec, cvec) for cvec in context_vecs)
            if best_sim >= self.faithfulness_threshold:
                supported_count += 1
            else:
                unsupported.append(sentence)

        return {
            "faithfulness_score": supported_count / len(sentences),
            "unsupported_sentences": unsupported,
            "total_sentences": len(sentences),
        }

    def calculate_hallucination_rate(self, answers: List[Dict]) -> float:
        """Fraction of answers containing at least one sentence unsupported
        by the context it was generated from.

        Each answer dict should carry both "answer" (generated text) and
        "context_chunks" (the chunks retrieved for that query). If no
        embed_fn is configured, or an individual answer is missing
        context_chunks, this degrades to the coarser citation-presence proxy
        (no citations => hallucinated), which only checks that *something*
        was cited, not that the answer text is actually grounded in it.
        """
        if not answers:
            return 0.0

        if self.embed_fn is None:
            logger.warning(
                "No embed_fn configured on EvaluationMetrics — falling back "
                "to the citation-presence proxy for hallucination rate. "
                "This does not verify the answer text is grounded in the "
                "retrieved context."
            )
            hallucinated = sum(1 for a in answers if not a.get("citations"))
            return hallucinated / len(answers)

        hallucinated = 0
        for a in answers:
            context_chunks = a.get("context_chunks")
            if context_chunks is None:
                logger.warning(
                    "Answer %r has no context_chunks recorded — cannot "
                    "verify groundedness, counting as hallucinated.",
                    a.get("name", a.get("answer", ""))[:60],
                )
                hallucinated += 1
                continue
            result = self.calculate_faithfulness(a.get("answer", ""), context_chunks)
            if result["unsupported_sentences"]:
                hallucinated += 1

        return hallucinated / len(answers)

    def calculate_citation_coverage(self, answers: List[Dict]) -> float:
        """Calculate percentage of answers with citations."""
        if not answers:
            return 0.0

        with_citations = sum(1 for a in answers if a.get("citations"))
        return with_citations / len(answers)

    def measure_consistency(self, query: str, n_runs: int = 5) -> float:
        """Measure answer consistency across multiple runs."""
        # Stub - would run same query multiple times
        return 0.85  # Example consistency score

    def measure_latency(self, func, *args, **kwargs) -> tuple:
        """Measure function execution time."""
        start = time.time()
        result = func(*args, **kwargs)
        latency = time.time() - start
        return result, latency

    def generate_report(self) -> Dict:
        """Generate evaluation report."""
        faithfulness_scores = []
        if self.embed_fn is not None:
            for r in self.results:
                context_chunks = r.get("context_chunks")
                if context_chunks is not None:
                    faithfulness_scores.append(
                        self.calculate_faithfulness(
                            r.get("answer", ""), context_chunks
                        )["faithfulness_score"]
                    )

        return {
            "hallucination_rate": self.calculate_hallucination_rate(self.results),
            "citation_coverage": self.calculate_citation_coverage(self.results),
            "mean_faithfulness": (
                float(np.mean(faithfulness_scores)) if faithfulness_scores else None
            ),
            "mean_latency": (
                float(np.mean([r.get("latency", 0) for r in self.results]))
                if self.results
                else 0.0
            ),
            "total_queries": len(self.results),
        }
