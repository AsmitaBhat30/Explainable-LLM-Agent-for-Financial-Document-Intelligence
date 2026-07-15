from typing import List, Dict


class TestSetGenerator:
    """Golden dataset: queries paired with known-correct retrieved context,
    so evaluation can score faithfulness/citation coverage without depending
    on a live FAISS index having been built from ingested documents.

    Each case's "compliance" dict is a gold label for the risk
    classification a domain expert would assign -- used to score
    ComplianceAgent's *actual* output against ground truth (the
    "compliance accuracy" metric named in .claude/skills/evaluate.md),
    not something fed directly into ExplanationAgent. ComplianceAgent's
    real keyword-matching logic is a coarse proxy for that judgment and
    will not agree with every label here; disagreements are exactly what
    the compliance-accuracy metric exists to surface (e.g. it has no
    keyword for CRR/Basel capital-ratio language, so those cases are
    correctly LOW-risk by the agent's own logic and expert judgment alike,
    but a query that only mentions "own funds" without a matched keyword
    will under-classify a genuinely regulatory question -- a known
    limitation, not a bug to route around in the fixture).

    31 queries spanning all 8 domains named in the project README
    (SEC EDGAR 10-K, MiFID II, PSD2, GDPR, CRR, BaFin, Basel III, ECB
    Supervisory Manual) -- enough that a single hallucinated answer moves
    the rate by roughly 1/31 (~3.2 percentage points), rather than the
    25-point jumps a 4-case set produced.
    """

    @staticmethod
    def get_golden_dataset() -> List[Dict]:
        """Return golden test cases with self-contained context chunks."""
        return [
            # --- PSD2 -------------------------------------------------
            {
                "name": "psd2_strong_customer_auth",
                "query": (
                    "Does PSD2 require strong customer authentication for "
                    "electronic payments?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "psd2_2015",
                        "section": "Article 97",
                        "page_range": [124, 124],
                        "text": (
                            "Payment service providers shall apply strong "
                            "customer authentication where the payer initiates "
                            "an electronic payment transaction."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["psd2"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "psd2_sca_exemptions",
                "query": (
                    "What do the Regulatory Technical Standards under PSD2 "
                    "cover regarding exemptions from strong customer "
                    "authentication?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "psd2_2015",
                        "section": "Article 98, RTS on SCA",
                        "page_range": [125, 125],
                        "text": (
                            "The Regulatory Technical Standards specify the "
                            "exemptions from the application of strong "
                            "customer authentication, based on the level of "
                            "risk, the amount and recurrence of the payment "
                            "transaction, and the payment channel used for "
                            "its execution."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["psd2", "regulatory"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "psd2_access_to_payment_systems",
                "query": (
                    "What does PSD2 require regarding access of payment "
                    "institutions to payment systems?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "psd2_2015",
                        "section": "Article 35",
                        "page_range": [61, 61],
                        "text": (
                            "Member States shall ensure that the rules on "
                            "access of authorised payment institutions to "
                            "payment systems are objective, non-discriminatory "
                            "and proportionate, and that they do not inhibit "
                            "access more than is necessary to safeguard "
                            "against specific risks."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["psd2"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "psd2_fraud_prevention_personal_data",
                "query": (
                    "Under PSD2, may a payment service provider process "
                    "personal data for fraud prevention purposes?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "psd2_2015",
                        "section": "Article 94",
                        "page_range": [70, 70],
                        "text": (
                            "Payment service providers may process personal "
                            "data necessary for the prevention, investigation "
                            "and detection of payment fraud, provided that "
                            "such processing is carried out in accordance "
                            "with applicable data protection law."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "HIGH",
                    "regulatory_flags": ["personal data", "psd2"],
                    "requires_review": True,
                    "confidence": 0.8,
                },
            },
            # --- GDPR ---------------------------------------------------
            {
                "name": "gdpr_consent_basis",
                "query": (
                    "Under GDPR, what is required for consent to be a valid "
                    "legal basis for processing personal data?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "gdpr_2016",
                        "section": "Article 7",
                        "page_range": [37, 37],
                        "text": (
                            "Consent must be freely given, specific, informed "
                            "and unambiguous, and the controller must be able "
                            "to demonstrate that the data subject has "
                            "consented to processing of personal data."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "HIGH",
                    "regulatory_flags": ["gdpr", "personal data", "consent"],
                    "requires_review": True,
                    "confidence": 0.8,
                },
            },
            {
                "name": "gdpr_right_to_erasure",
                "query": (
                    "Under GDPR, when must a controller erase a data "
                    "subject's personal data?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "gdpr_2016",
                        "section": "Article 17",
                        "page_range": [43, 43],
                        "text": (
                            "The data subject shall have the right to obtain "
                            "from the controller the erasure of personal data "
                            "without undue delay where, among other grounds, "
                            "the data is no longer necessary for the purposes "
                            "for which it was collected or the data subject "
                            "withdraws consent."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "HIGH",
                    "regulatory_flags": ["gdpr", "personal data"],
                    "requires_review": True,
                    "confidence": 0.8,
                },
            },
            {
                "name": "gdpr_breach_notification",
                "query": "What is the GDPR breach notification deadline?",
                "context_chunks": [
                    {
                        "doc_id": "gdpr_2016",
                        "section": "Article 33",
                        "page_range": [51, 51],
                        "text": (
                            "In the case of a personal data breach, the "
                            "controller shall without undue delay and, where "
                            "feasible, not later than 72 hours after having "
                            "become aware of it, notify the breach to the "
                            "competent supervisory authority."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "HIGH",
                    "regulatory_flags": ["gdpr"],
                    "requires_review": True,
                    "confidence": 0.8,
                },
            },
            {
                "name": "gdpr_processing_principles",
                "query": (
                    "What are the core principles relating to processing of "
                    "personal data under GDPR?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "gdpr_2016",
                        "section": "Article 5",
                        "page_range": [35, 35],
                        "text": (
                            "Personal data shall be processed lawfully, "
                            "fairly and in a transparent manner, collected "
                            "for specified, explicit and legitimate purposes, "
                            "and kept accurate, limited to what is necessary, "
                            "and retained no longer than necessary for the "
                            "purposes for which it is processed."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "HIGH",
                    "regulatory_flags": ["gdpr", "personal data"],
                    "requires_review": True,
                    "confidence": 0.8,
                },
            },
            # --- MiFID II -------------------------------------------------
            {
                "name": "mifid2_best_execution",
                "query": (
                    "What does MiFID II require regarding best execution of "
                    "client orders?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "mifid2_2014",
                        "section": "Article 27",
                        "page_range": [58, 58],
                        "text": (
                            "Investment firms shall take all sufficient steps "
                            "to obtain, when executing orders, the best "
                            "possible result for their clients taking into "
                            "account price, costs, speed, likelihood of "
                            "execution and settlement, size, nature and any "
                            "other relevant consideration."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["mifid"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "mifid2_best_interests",
                "query": (
                    "What does MiFID II Article 24 require regarding a "
                    "firm's duty to act in clients' best interests?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "mifid2_2014",
                        "section": "Article 24",
                        "page_range": [54, 54],
                        "text": (
                            "Investment firms shall act honestly, fairly and "
                            "professionally in accordance with the best "
                            "interests of their clients, and shall ensure "
                            "that all information addressed to clients is "
                            "fair, clear and not misleading."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["mifid"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "mifid2_product_governance",
                "query": (
                    "What are the MiFID II product governance requirements "
                    "for firms that manufacture financial instruments?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "mifid2_2014",
                        "section": "Article 16(3)",
                        "page_range": [48, 48],
                        "text": (
                            "Investment firms which manufacture financial "
                            "instruments for sale to clients shall maintain, "
                            "operate and review a process for the approval "
                            "of each financial instrument, specifying an "
                            "identified target market of end clients within "
                            "the relevant category of clients for each "
                            "instrument."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["mifid"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "mifid2_suitability_assessment",
                "query": (
                    "What must a firm assess under MiFID II before providing "
                    "investment advice?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "mifid2_2014",
                        "section": "Article 25",
                        "page_range": [56, 56],
                        "text": (
                            "When providing investment advice or portfolio "
                            "management, the investment firm shall obtain the "
                            "necessary information regarding the client's "
                            "knowledge and experience, financial situation "
                            "and investment objectives so as to recommend "
                            "suitable investment services and financial "
                            "instruments."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["mifid"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            # --- Basel III ------------------------------------------------
            {
                "name": "basel3_leverage_ratio",
                "query": (
                    "What is the minimum leverage ratio requirement under " "Basel III?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "basel_iii_2017",
                        "section": "Leverage Ratio Framework, para 5",
                        "page_range": [3, 3],
                        "text": (
                            "The Basel III leverage ratio framework sets a "
                            "minimum Tier 1 leverage ratio requirement of 3%, "
                            "calculated as Tier 1 capital divided by total "
                            "exposure measure."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "basel3_capital_conservation_buffer",
                "query": (
                    "What is the Basel III capital conservation buffer " "requirement?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "basel_iii_2017",
                        "section": "Capital Conservation Buffer",
                        "page_range": [55, 55],
                        "text": (
                            "Basel III requires banks to hold a capital "
                            "conservation buffer of 2.5% of risk-weighted "
                            "assets, comprised of Common Equity Tier 1 "
                            "capital, above the regulatory minimum, with "
                            "restrictions on capital distributions if the "
                            "buffer is not met."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "basel3_liquidity_coverage_ratio",
                "query": (
                    "What is the minimum Liquidity Coverage Ratio under the "
                    "Basel III framework?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "basel_iii_2017",
                        "section": "Liquidity Coverage Ratio",
                        "page_range": [9, 9],
                        "text": (
                            "The Liquidity Coverage Ratio requires banks to "
                            "hold a stock of high-quality liquid assets "
                            "sufficient to cover total net cash outflows over "
                            "a 30-day stress period, with a minimum ratio of "
                            "100%."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "basel3_net_stable_funding_ratio",
                "query": "What does the Basel III Net Stable Funding Ratio require?",
                "context_chunks": [
                    {
                        "doc_id": "basel_iii_2017",
                        "section": "Net Stable Funding Ratio",
                        "page_range": [23, 23],
                        "text": (
                            "The Net Stable Funding Ratio requires banks to "
                            "maintain a stable funding profile in relation to "
                            "the composition of their assets and off-balance "
                            "sheet activities, with available stable funding "
                            "required to be at least 100% of required stable "
                            "funding over a one-year horizon."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            # --- CRR (Capital Requirements Regulation) -----------------
            {
                "name": "crr_own_funds_requirements",
                "query": (
                    "What are the minimum own funds requirements for banks "
                    "under the CRR?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "crr_2013",
                        "section": "Article 92",
                        "page_range": [40, 40],
                        "text": (
                            "Institutions shall at all times satisfy a "
                            "Common Equity Tier 1 capital ratio of 4.5%, a "
                            "Tier 1 capital ratio of 6%, and a Total capital "
                            "ratio of 8%, each expressed as a percentage of "
                            "the total risk exposure amount."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "crr_leverage_ratio_calculation",
                "query": "How is the leverage ratio calculated under the CRR?",
                "context_chunks": [
                    {
                        "doc_id": "crr_2013",
                        "section": "Article 429",
                        "page_range": [212, 212],
                        "text": (
                            "The leverage ratio shall be calculated as an "
                            "institution's Tier 1 capital divided by that "
                            "institution's total exposure measure, expressed "
                            "as a percentage, and institutions shall "
                            "maintain a leverage ratio of at least 3%."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "crr_liquidity_coverage_ratio",
                "query": (
                    "What liquidity coverage ratio must institutions "
                    "maintain under the CRR?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "crr_2013",
                        "section": "Article 412",
                        "page_range": [198, 198],
                        "text": (
                            "Institutions shall hold liquid assets, the sum "
                            "of the values of which covers the liquidity "
                            "outflows less the liquidity inflows under "
                            "stressed conditions, such that the liquidity "
                            "coverage ratio does not fall below 100%."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "crr_net_stable_funding_ratio",
                "query": (
                    "What is the Net Stable Funding Ratio requirement "
                    "introduced under the CRR?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "crr_2013",
                        "section": "Article 413",
                        "page_range": [199, 199],
                        "text": (
                            "Institutions shall maintain a net stable "
                            "funding ratio of at least 100%, calculated as "
                            "the amount of available stable funding divided "
                            "by the amount of required stable funding, to "
                            "limit overreliance on short-term wholesale "
                            "funding."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            # --- BaFin --------------------------------------------------
            {
                "name": "bafin_marisk_risk_management",
                "query": (
                    "What does BaFin's MaRisk circular require regarding a "
                    "bank's risk management framework?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "bafin_marisk_2021",
                        "section": "AT 4.1",
                        "page_range": [12, 12],
                        "text": (
                            "Institutions must establish a proper business "
                            "organisation which encompasses an appropriate "
                            "and effective risk management framework, "
                            "including strategies, a process for "
                            "identifying, assessing, managing, monitoring "
                            "and communicating risks, and an adequate "
                            "internal control system."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "bafin_wphg_organizational_requirements",
                "query": (
                    "What organizational requirements does the WpHG impose "
                    "on investment services firms in Germany to ensure "
                    "compliance?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "bafin_wphg",
                        "section": "Section 80 WpHG",
                        "page_range": [44, 44],
                        "text": (
                            "Investment services enterprises must maintain "
                            "the organisational precautions necessary to "
                            "comply with their obligations under the "
                            "Securities Trading Act, including measures to "
                            "identify and manage conflicts of interest and "
                            "to ensure compliance with conduct of business "
                            "obligations."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "MEDIUM",
                    "regulatory_flags": ["compliance"],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "bafin_kwg_internal_control_systems",
                "query": (
                    "What does Section 25a of the KWG require regarding "
                    "internal control systems at German banks?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "bafin_kwg",
                        "section": "Section 25a KWG",
                        "page_range": [31, 31],
                        "text": (
                            "Institutions must have a proper business "
                            "organisation, including internal control "
                            "procedures comprising a risk management system, "
                            "and adequate staffing and technical-"
                            "organisational resources, proportionate to the "
                            "nature, scale and complexity of their business "
                            "activities."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "bafin_large_exposure_reporting",
                "query": (
                    "What large exposure reporting obligations does BaFin "
                    "impose on credit institutions?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "bafin_grosskredit",
                        "section": "Large Exposures Circular",
                        "page_range": [7, 7],
                        "text": (
                            "Institutions must report to BaFin and the "
                            "Bundesbank on a quarterly basis all exposures "
                            "that equal or exceed 10% of their eligible "
                            "capital, and must not exceed an exposure of 25% "
                            "of eligible capital to any single counterparty "
                            "or group of connected clients."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            # --- ECB Supervisory Manual ---------------------------------
            {
                "name": "ecb_srep_purpose",
                "query": (
                    "What is the purpose of the ECB's Supervisory Review "
                    "and Evaluation Process (SREP)?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "ecb_supervisory_manual",
                        "section": "SREP Methodology, Ch. 1",
                        "page_range": [5, 5],
                        "text": (
                            "The Supervisory Review and Evaluation Process "
                            "is the common methodology used by the ECB and "
                            "national competent authorities to assess and "
                            "measure risks faced by each supervised "
                            "institution, forming the basis for supervisory "
                            "decisions on capital, liquidity and qualitative "
                            "measures."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "ecb_pillar2_requirement",
                "query": (
                    "What is the Pillar 2 Requirement (P2R) set by the ECB "
                    "under SREP?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "ecb_supervisory_manual",
                        "section": "SREP Methodology, Ch. 4",
                        "page_range": [41, 41],
                        "text": (
                            "The Pillar 2 Requirement is a bank-specific "
                            "capital requirement that applies in addition to "
                            "the minimum own funds requirement, addressing "
                            "risks which are underestimated or not covered "
                            "by the Pillar 1 minimum capital requirements, "
                            "and must be met with at least 56.25% Common "
                            "Equity Tier 1 capital."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "ecb_ssm_direct_supervision_scope",
                "query": (
                    "Which institutions does the ECB directly supervise "
                    "under the Single Supervisory Mechanism?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "ecb_supervisory_manual",
                        "section": "SSM Framework, Ch. 2",
                        "page_range": [14, 14],
                        "text": (
                            "The ECB directly supervises significant "
                            "institutions, generally those with total "
                            "assets exceeding EUR 30 billion or that are "
                            "otherwise designated as significant, while "
                            "national competent authorities continue to "
                            "directly supervise less significant "
                            "institutions."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "ecb_onsite_inspection_powers",
                "query": (
                    "What on-site inspection powers does the ECB have under "
                    "the Single Supervisory Mechanism?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "ecb_supervisory_manual",
                        "section": "SSM Framework, Ch. 6",
                        "page_range": [88, 88],
                        "text": (
                            "The ECB may conduct all necessary on-site "
                            "inspections at the business premises of credit "
                            "institutions, and may authorise national "
                            "competent authorities or appoint independent "
                            "experts to carry out such inspections on its "
                            "behalf."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            # --- SEC EDGAR 10-K filings ----------------------------------
            {
                "name": "sec_10k_item1a_risk_factors",
                "query": "What must a company disclose under Item 1A of Form 10-K?",
                "context_chunks": [
                    {
                        "doc_id": "sec_form_10k_2023",
                        "section": "Item 1A, Risk Factors",
                        "page_range": [8, 8],
                        "text": (
                            "Item 1A requires registrants to disclose the "
                            "most significant factors that make an "
                            "investment in the company speculative or risky, "
                            "organized under relevant subcaptions, with any "
                            "risk generic to the industry as a whole "
                            "disclosed only where material."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "sec_10k_item7_mda",
                "query": (
                    "What does Item 7 of Form 10-K require regarding "
                    "Management's Discussion and Analysis?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "sec_form_10k_2023",
                        "section": "Item 7, MD&A",
                        "page_range": [34, 34],
                        "text": (
                            "Item 7 requires a discussion of the "
                            "registrant's financial condition, changes in "
                            "financial condition, and results of operations, "
                            "including a discussion of liquidity, capital "
                            "resources, and known trends or uncertainties "
                            "that are reasonably likely to have a material "
                            "effect on the registrant's financial condition."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "sec_regsk_item303_liquidity_disclosure",
                "query": (
                    "Under Regulation S-K Item 303, what must a company "
                    "disclose about its liquidity?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "sec_reg_sk",
                        "section": "Item 303(b)(1)",
                        "page_range": [3, 3],
                        "text": (
                            "Item 303 of Regulation S-K requires disclosure "
                            "of any known trends or any known demands, "
                            "commitments, events or uncertainties that will "
                            "result in, or that are reasonably likely to "
                            "result in, the registrant's liquidity increasing "
                            "or decreasing in a material way, and "
                            "identification of the course of action the "
                            "registrant has taken or proposes to take to "
                            "remedy any deficiency."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "sec_inline_xbrl_requirement",
                "query": (
                    "What structured data format does the SEC require for "
                    "10-K financial statements?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "sec_reg_st",
                        "section": "Rule 405",
                        "page_range": [2, 2],
                        "text": (
                            "Registrants must tag financial statements using "
                            "Inline XBRL (eXtensible Business Reporting "
                            "Language) in accordance with Rule 405 of "
                            "Regulation S-T, embedding machine-readable data "
                            "directly within the human-readable HTML "
                            "document."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
            {
                "name": "sec_10k_item9a_internal_controls",
                "query": (
                    "What must Item 9A of Form 10-K disclose about internal "
                    "control over financial reporting?"
                ),
                "context_chunks": [
                    {
                        "doc_id": "sec_form_10k_2023",
                        "section": "Item 9A, Controls and Procedures",
                        "page_range": [61, 61],
                        "text": (
                            "Item 9A requires management's assessment of the "
                            "effectiveness of the registrant's internal "
                            "control over financial reporting as of the end "
                            "of the fiscal year, as mandated by Section 404 "
                            "of the Sarbanes-Oxley Act, along with "
                            "disclosure of any material weaknesses "
                            "identified."
                        ),
                    }
                ],
                "compliance": {
                    "risk_level": "LOW",
                    "regulatory_flags": [],
                    "requires_review": False,
                    "confidence": 0.9,
                },
            },
        ]


class AdversarialTestSuite:
    """Test cases for stress testing the system."""

    @staticmethod
    def get_test_cases() -> List[Dict]:
        """Return adversarial test cases."""
        return [
            {
                "name": "missing_document",
                "query": "What is the capital requirement for tier 3 banks?",
                "expected_behavior": "Should indicate insufficient information",
                "category": "missing_info",
            },
            {
                "name": "ambiguous_question",
                "query": "What are the requirements?",
                "expected_behavior": "Should ask for clarification",
                "category": "ambiguous",
            },
            {
                "name": "out_of_scope",
                "query": "What is the weather today?",
                "expected_behavior": "Should decline or indicate out of scope",
                "category": "out_of_scope",
            },
            {
                "name": "conflicting_info",
                "query": "What is the maximum leverage ratio?",
                "expected_behavior": "Should note conflicting sources if present",
                "category": "conflict",
            },
            {
                "name": "temporal_query",
                "query": "What was the regulation in 2020 vs 2023?",
                "expected_behavior": "Should distinguish between time periods",
                "category": "temporal",
            },
        ]

    @staticmethod
    def get_failure_cases() -> Dict:
        """Document known failure cases."""
        return {
            "table_extraction": {
                "description": (
                    "Complex tables with merged cells may not parse correctly"
                ),
                "impact": "Financial data in tables may be incomplete",
                "mitigation": "Manual review for table-heavy documents",
                "status": "Known limitation",
            },
            "scanned_pdfs": {
                "description": "OCR quality varies with scan quality",
                "impact": "Text extraction may have errors",
                "mitigation": "Confidence thresholds, OCR quality checks",
                "status": "Partially mitigated",
            },
            "cross_document": {
                "description": "References across documents not resolved",
                "impact": "May miss related information in other documents",
                "mitigation": "Document linking in roadmap",
                "status": "Future enhancement",
            },
        }
