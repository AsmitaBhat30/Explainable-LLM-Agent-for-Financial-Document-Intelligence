"""
Run data validation checks on processed documents.
Usage: python -m validation.run_checks
"""

import json
import pandas as pd
from pathlib import Path
import logging
from validation.quality_checks import QualityChecker
from validation.schemas import DocumentMetadataSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*60)
    logger.info("DATA VALIDATION CHECKS")
    logger.info("="*60)
    
    parsed_dir = Path("data/parsed")
    checker = QualityChecker()
    
    # Load all documents
    documents = []
    for json_file in parsed_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            documents.append(json.load(f))
    
    logger.info(f"Loaded {len(documents)} documents")
    
    # Run quality checks
    failed = 0
    for doc in documents:
        is_valid, errors = checker.validate_document(doc)
        if not is_valid:
            logger.error(f"Document {doc.get('doc_id')} failed validation:")
            for error in errors:
                logger.error(f"  - {error}")
            failed += 1
    
    # Validate metadata schema
    try:
        metadata_df = pd.DataFrame([doc["metadata"] for doc in documents])
        DocumentMetadataSchema.validate(metadata_df)
        logger.info("✓ Metadata schema validation passed")
    except Exception as e:
        logger.error(f"✗ Metadata schema validation failed: {e}")
        failed += 1
    
    # Summary
    logger.info("="*60)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total documents: {len(documents)}")
    logger.info(f"Passed: {len(documents) - failed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("✓ All validation checks passed!")
    else:
        logger.warning(f"⚠ {failed} validation issues found")


if __name__ == "__main__":
    main()
