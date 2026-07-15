from agents.compliance_agent import ComplianceAgent
from evaluation.test_cases import AdversarialTestSuite, TestSetGenerator

# One representative doc_id prefix per domain named in the project README /
# CLAUDE.md: SEC EDGAR 10-K, MiFID II, PSD2, GDPR, CRR, BaFin, Basel III,
# ECB Supervisory Manual.
EXPECTED_DOMAIN_PREFIXES = {
    "sec": "SEC EDGAR 10-K",
    "mifid2": "MiFID II",
    "psd2": "PSD2",
    "gdpr": "GDPR",
    "crr": "CRR",
    "bafin": "BaFin",
    "basel": "Basel III",
    "ecb": "ECB Supervisory Manual",
}

REQUIRED_CASE_KEYS = {"name", "query", "context_chunks", "compliance"}
REQUIRED_CHUNK_KEYS = {"doc_id", "section", "text"}
REQUIRED_COMPLIANCE_KEYS = {
    "risk_level",
    "regulatory_flags",
    "requires_review",
    "confidence",
}


def test_golden_dataset_has_enough_cases_for_percentage_point_granularity():
    """At n=4 (the original size) every case is worth 25 percentage points
    of any rate-based metric -- too coarse to report or target a specific
    percentage. n>=30 means a single case is worth roughly 1/n <= ~3.3
    points, which is what makes a metric like "hallucination rate: 3.2%"
    even meaningful to state.
    """
    cases = TestSetGenerator.get_golden_dataset()
    assert len(cases) >= 30


def test_golden_dataset_case_names_are_unique():
    cases = TestSetGenerator.get_golden_dataset()
    names = [c["name"] for c in cases]
    assert len(names) == len(set(names))


def test_golden_dataset_cases_have_required_schema():
    for case in TestSetGenerator.get_golden_dataset():
        missing = REQUIRED_CASE_KEYS - case.keys()
        assert not missing, f"{case.get('name')} missing keys: {missing}"

        assert case["context_chunks"], f"{case['name']} has no context_chunks"
        for chunk in case["context_chunks"]:
            missing_chunk_keys = REQUIRED_CHUNK_KEYS - chunk.keys()
            assert (
                not missing_chunk_keys
            ), f"{case['name']} chunk missing keys: {missing_chunk_keys}"
            assert chunk["text"].strip(), f"{case['name']} has an empty chunk text"

        missing_compliance_keys = REQUIRED_COMPLIANCE_KEYS - case["compliance"].keys()
        assert (
            not missing_compliance_keys
        ), f"{case['name']} compliance dict missing keys: {missing_compliance_keys}"
        assert case["compliance"]["risk_level"] in {"LOW", "MEDIUM", "HIGH"}


def test_golden_dataset_covers_all_eight_regulatory_domains():
    cases = TestSetGenerator.get_golden_dataset()
    prefixes_seen = {c["context_chunks"][0]["doc_id"].split("_")[0] for c in cases}

    missing_domains = {
        label
        for prefix, label in EXPECTED_DOMAIN_PREFIXES.items()
        if prefix not in prefixes_seen
    }
    assert not missing_domains, f"no golden case for: {missing_domains}"


def test_golden_dataset_compliance_labels_match_real_agent_output():
    """The "compliance" dict on each case is a gold label scored against
    ComplianceAgent's actual output (the "compliance accuracy" metric named
    in .claude/skills/evaluate.md) -- not something fed straight into
    ExplanationAgent. If this drifts, either the fixture is stale or
    ComplianceAgent's classification logic changed; either way the gold
    labels need to be revisited, not silently ignored.
    """
    agent = ComplianceAgent(regulations=[])

    for case in TestSetGenerator.get_golden_dataset():
        gold = case["compliance"]
        predicted = agent.execute({"query": case["query"]})

        assert predicted["risk_level"] == gold["risk_level"], case["name"]
        assert set(predicted["regulatory_flags"]) == set(
            gold["regulatory_flags"]
        ), case["name"]
        assert predicted["requires_review"] == gold["requires_review"], case["name"]


def test_adversarial_suite_still_has_cases():
    cases = AdversarialTestSuite.get_test_cases()
    assert len(cases) >= 5
    for case in cases:
        assert {"name", "query", "expected_behavior", "category"} <= case.keys()
