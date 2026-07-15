from agents.compliance_agent import ComplianceAgent


def test_low_risk_when_no_keywords_match():
    agent = ComplianceAgent(regulations=["basel3"])

    result = agent.execute(
        {"query": "What is the minimum leverage ratio under Basel III?"}
    )

    assert result["risk_level"] == "LOW"
    assert result["regulatory_flags"] == []
    assert result["requires_review"] is False


def test_medium_risk_for_psd2_keyword():
    agent = ComplianceAgent(regulations=["psd2"])

    result = agent.execute(
        {"query": "Does PSD2 require strong customer authentication?"}
    )

    assert result["risk_level"] == "MEDIUM"
    assert result["requires_review"] is False


def test_high_risk_for_gdpr_keyword():
    agent = ComplianceAgent(regulations=["gdpr"])

    result = agent.execute({"query": "What is required for valid consent under GDPR?"})

    assert result["risk_level"] == "HIGH"
    assert result["requires_review"] is True


def test_high_risk_survives_medium_keyword_in_same_query():
    """Regression test: a query that mentions both a MEDIUM-level keyword
    (e.g. "psd2") and a HIGH-level keyword (e.g. "personal data") must stay
    HIGH. The original implementation iterated risk levels and let whichever
    level matched last overwrite risk_level unconditionally, so a query
    mentioning "psd2" after "personal data" was silently downgraded to
    MEDIUM and requires_review flipped to False -- exactly the flag
    CLAUDE.md says must never be suppressed for personal-data domains.
    """
    agent = ComplianceAgent(regulations=["psd2", "gdpr"])

    result = agent.execute(
        {
            "query": (
                "Under PSD2, may a payment service provider process "
                "personal data for fraud prevention purposes?"
            )
        }
    )

    assert result["risk_level"] == "HIGH"
    assert result["requires_review"] is True
    assert "personal data" in result["regulatory_flags"]
    assert "psd2" in result["regulatory_flags"]


def test_flags_collected_from_both_levels_regardless_of_final_risk_level():
    agent = ComplianceAgent(regulations=["mifid", "gdpr"])

    result = agent.execute(
        {"query": "Is this compliance question about mifid consent rules?"}
    )

    assert result["risk_level"] == "HIGH"
    assert set(result["regulatory_flags"]) == {"consent", "mifid", "compliance"}
