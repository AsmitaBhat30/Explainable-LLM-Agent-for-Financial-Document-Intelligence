"""
Process all raw documents through the ingestion pipeline.
Usage: python -m ingestion.process_documents
"""

import logging
from pathlib import Path
from document_processors import DocumentProcessorOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*60)
    logger.info("DOCUMENT INGESTION PIPELINE")
    logger.info("="*60)
    
    orchestrator = DocumentProcessorOrchestrator(
        raw_dir="data/raw",
        parsed_dir="data/parsed"
    )
    
    documents = orchestrator.process_all()
    
    logger.info("="*60)
    logger.info("INGESTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Documents processed: {len(documents)}")
    logger.info(f"Output directory: data/parsed/")


if __name__ == "__main__":
    main()

