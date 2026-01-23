from typing import List, Dict

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
                "category": "missing_info"
            },
            {
                "name": "ambiguous_question",
                "query": "What are the requirements?",
                "expected_behavior": "Should ask for clarification",
                "category": "ambiguous"
            },
            {
                "name": "out_of_scope",
                "query": "What is the weather today?",
                "expected_behavior": "Should decline or indicate out of scope",
                "category": "out_of_scope"
            },
            {
                "name": "conflicting_info",
                "query": "What is the maximum leverage ratio?",
                "expected_behavior": "Should note conflicting sources if present",
                "category": "conflict"
            },
            {
                "name": "temporal_query",
                "query": "What was the regulation in 2020 vs 2023?",
                "expected_behavior": "Should distinguish between time periods",
                "category": "temporal"
            }
        ]
    
    @staticmethod
    def get_failure_cases() -> Dict:
        """Document known failure cases."""
        return {
            "table_extraction": {
                "description": "Complex tables with merged cells may not parse correctly",
                "impact": "Financial data in tables may be incomplete",
                "mitigation": "Manual review for table-heavy documents",
                "status": "Known limitation"
            },
            "scanned_pdfs": {
                "description": "OCR quality varies with scan quality",
                "impact": "Text extraction may have errors",
                "mitigation": "Confidence thresholds, OCR quality checks",
                "status": "Partially mitigated"
            },
            "cross_document": {
                "description": "References across documents not resolved",
                "impact": "May miss related information in other documents",
                "mitigation": "Document linking in roadmap",
                "status": "Future enhancement"
            }
        }