from typing import Dict, List
from .base_agent import BaseAgent

class ComplianceAgent(BaseAgent):
    def __init__(self, regulations: List[str]):
        super().__init__("Compliance")
        self.regulations = regulations
        
    def execute(self, input_data: Dict) -> Dict:
        """Check for regulatory implications."""
        chunks = input_data.get("retrieved_chunks", [])
        query = input_data.get("query", "")
        
        # Check for regulatory keywords
        regulatory_flags = []
        risk_level = "LOW"
        
        risk_keywords = {
            "HIGH": ["gdpr", "personal data", "privacy", "consent"],
            "MEDIUM": ["mifid", "psd2", "compliance", "regulatory"]
        }
        
        query_lower = query.lower()
        for level, keywords in risk_keywords.items():
            if any(kw in query_lower for kw in keywords):
                risk_level = level
                regulatory_flags.extend([kw for kw in keywords if kw in query_lower])
        
        confidence = 0.8 if regulatory_flags else 0.9
        
        self.log_decision(f"Risk level: {risk_level}", confidence)
        
        return {
            "risk_level": risk_level,
            "regulatory_flags": regulatory_flags,
            "requires_review": risk_level == "HIGH",
            "confidence": confidence,
            "agent": self.name
        }