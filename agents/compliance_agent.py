from typing import Dict, List
from .base_agent import BaseAgent


class ComplianceAgent(BaseAgent):
    def __init__(self, regulations: List[str]):
        super().__init__("Compliance")
        self.regulations = regulations

    def execute(self, input_data: Dict) -> Dict:
        """Check for regulatory implications."""
        query = input_data.get("query", "")

        # Check for regulatory keywords
        regulatory_flags = []
        risk_level = "LOW"

        risk_keywords = {
            "HIGH": ["gdpr", "personal data", "privacy", "consent"],
            "MEDIUM": ["mifid", "psd2", "compliance", "regulatory"],
        }

        # Checked in severity order (HIGH before MEDIUM) and a later,
        # lower-severity match must never downgrade an already-assigned
        # HIGH classification. A query can legitimately match keywords from
        # both levels (e.g. a PSD2 question that also discusses "personal
        # data"); previously this loop just took whichever level was
        # checked last, silently dropping GDPR/personal-data queries from
        # HIGH to MEDIUM and suppressing requires_review — exactly the flag
        # CLAUDE.md says must not be suppressed for those domains.
        query_lower = query.lower()
        for level, keywords in risk_keywords.items():
            matched = [kw for kw in keywords if kw in query_lower]
            if matched:
                regulatory_flags.extend(matched)
                if risk_level != "HIGH":
                    risk_level = level

        confidence = 0.8 if regulatory_flags else 0.9

        self.log_decision(f"Risk level: {risk_level}", confidence)

        return {
            "risk_level": risk_level,
            "regulatory_flags": regulatory_flags,
            "requires_review": risk_level == "HIGH",
            "confidence": confidence,
            "agent": self.name,
        }
