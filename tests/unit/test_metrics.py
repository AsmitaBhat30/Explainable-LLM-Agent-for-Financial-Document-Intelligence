import re

import numpy as np
import pytest

from evaluation.metrics import EvaluationMetrics


def fake_embed(texts):
    """Deterministic bag-of-words 'embedding' for tests — no network or
    model download required. Called once per calculate_faithfulness
    invocation over the combined sentence+context list, so the resulting
    vectors always share one vocabulary/vector space.
    """
    vocab = sorted({w for t in texts for w in re.findall(r"[a-z0-9]+", t.lower())})
    vecs = []
    for t in texts:
        words = re.findall(r"[a-z0-9]+", t.lower())
        vecs.append([float(words.count(w)) for w in vocab])
    return np.array(vecs, dtype=float)


PSD2_SENTENCE = (
    "Payment service providers shall apply strong customer authentication "
    "for electronic payments."
)

WEATHER_SENTENCE = (
    "The weather forecast for tomorrow predicts heavy snowfall in the " "mountains."
)

CONTEXT_CHUNKS = [
    {
        "doc_id": "psd2_2015",
        "section": "Article 97",
        "text": PSD2_SENTENCE,
    }
]


def test_faithfulness_supported_sentence_scores_one():
    metrics = EvaluationMetrics(embed_fn=fake_embed)
    answer = PSD2_SENTENCE

    result = metrics.calculate_faithfulness(answer, CONTEXT_CHUNKS)

    assert result["faithfulness_score"] == 1.0
    assert result["unsupported_sentences"] == []
    assert result["total_sentences"] == 1


def test_faithfulness_flags_unrelated_claim():
    metrics = EvaluationMetrics(embed_fn=fake_embed, faithfulness_threshold=0.5)
    answer = WEATHER_SENTENCE

    result = metrics.calculate_faithfulness(answer, CONTEXT_CHUNKS)

    assert result["faithfulness_score"] == 0.0
    assert result["unsupported_sentences"] == [answer]


def test_faithfulness_mixed_sentences_partial_score():
    metrics = EvaluationMetrics(embed_fn=fake_embed, faithfulness_threshold=0.5)
    answer = (
        "Payment service providers shall apply strong customer authentication "
        "for electronic payments. Also, the stock market closed higher today."
    )

    result = metrics.calculate_faithfulness(answer, CONTEXT_CHUNKS)

    assert result["total_sentences"] == 2
    assert result["faithfulness_score"] == 0.5
    assert len(result["unsupported_sentences"]) == 1


def test_faithfulness_no_context_chunks_all_unsupported():
    metrics = EvaluationMetrics(embed_fn=fake_embed)

    result = metrics.calculate_faithfulness("Some claim with no context.", [])

    assert result["faithfulness_score"] == 0.0
    assert result["unsupported_sentences"] == ["Some claim with no context."]


def test_faithfulness_without_embed_fn_raises():
    metrics = EvaluationMetrics()

    with pytest.raises(ValueError):
        metrics.calculate_faithfulness("Any answer.", CONTEXT_CHUNKS)


def test_hallucination_rate_uses_faithfulness_when_embed_fn_present():
    metrics = EvaluationMetrics(embed_fn=fake_embed, faithfulness_threshold=0.5)
    answers = [
        {
            "answer": PSD2_SENTENCE,
            "citations": [{"doc_id": "psd2_2015"}],
            "context_chunks": CONTEXT_CHUNKS,
        },
        {
            "answer": WEATHER_SENTENCE,
            "citations": [{"doc_id": "psd2_2015"}],
            "context_chunks": CONTEXT_CHUNKS,
        },
    ]

    rate = metrics.calculate_hallucination_rate(answers)

    # Second answer is unsupported by its own cited context, despite having
    # a citation — the citation-presence proxy would have missed this.
    assert rate == 0.5


def test_hallucination_rate_missing_context_counts_as_hallucinated():
    metrics = EvaluationMetrics(embed_fn=fake_embed)
    answers = [{"answer": "Some answer.", "citations": [{"doc_id": "x"}]}]

    rate = metrics.calculate_hallucination_rate(answers)

    assert rate == 1.0


def test_hallucination_rate_falls_back_to_citation_proxy_without_embed_fn(caplog):
    metrics = EvaluationMetrics()
    answers = [
        {"answer": "a", "citations": [{"doc_id": "x"}]},
        {"answer": "b", "citations": []},
    ]

    rate = metrics.calculate_hallucination_rate(answers)

    assert rate == 0.5
    assert "falling back" in caplog.text.lower()


def test_citation_coverage():
    metrics = EvaluationMetrics()
    answers = [{"citations": [{"doc_id": "x"}]}, {"citations": []}]

    assert metrics.calculate_citation_coverage(answers) == 0.5


def test_generate_report_includes_mean_faithfulness():
    metrics = EvaluationMetrics(embed_fn=fake_embed, faithfulness_threshold=0.5)
    metrics.results = [
        {
            "answer": PSD2_SENTENCE,
            "citations": [{"doc_id": "psd2_2015"}],
            "context_chunks": CONTEXT_CHUNKS,
            "latency": 1.0,
        }
    ]

    report = metrics.generate_report()

    assert report["mean_faithfulness"] == 1.0
    assert report["hallucination_rate"] == 0.0
    assert report["total_queries"] == 1


def test_generate_report_mean_faithfulness_none_without_embed_fn():
    metrics = EvaluationMetrics()
    metrics.results = [{"answer": "a", "citations": [], "latency": 1.0}]

    report = metrics.generate_report()

    assert report["mean_faithfulness"] is None
