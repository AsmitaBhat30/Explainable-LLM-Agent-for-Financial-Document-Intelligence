from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class QualityChecker:
    def __init__(self, min_pages: int = 1, min_text_length: int = 100):
        self.min_pages = min_pages
        self.min_text_length = min_text_length
        
    def validate_document(self, doc_data: Dict) -> tuple[bool, List[str]]:
        """Run quality checks on parsed document."""
        errors = []
        
        # Page count check
        if doc_data.get("page_count", 0) < self.min_pages:
            errors.append(f"Page count {doc_data.get('page_count')} below minimum {self.min_pages}")
        
        # Text length check
        text_len = len(doc_data.get("text", ""))
        if text_len < self.min_text_length:
            errors.append(f"Text length {text_len} below minimum {self.min_text_length}")
        
        # Empty sections check
        if not doc_data.get("text", "").strip():
            errors.append("Document contains no text content")
        
        # Metadata completeness
        required_fields = ["doc_id", "doc_type", "source", "ingestion_date"]
        metadata = doc_data.get("metadata", {})
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")
        
        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Validation failed for document: {errors}")
        
        return is_valid, errors