"""
Interactive query interface for the document intelligence system.
Usage: python -m scripts.query_system
"""

import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentQuerySystem:
    """Interactive query interface."""
    
    def __init__(self):
        self.features_dir = Path("data/features")
        
        # Load model
        logger.info("Loading embedding model...")
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Load FAISS index
        index_path = self.features_dir / "faiss.index"
        logger.info(f"Loading FAISS index from {index_path}")
        self.index = faiss.read_index(str(index_path))
        
        # Load chunks
        chunks_path = self.features_dir / "chunks.json"
        logger.info(f"Loading chunks from {chunks_path}")
        with open(chunks_path, 'r') as f:
            self.chunks = json.load(f)
        
        logger.info(f"System ready! {len(self.chunks)} chunks indexed")
    
    def query(self, question: str, top_k: int = 5):
        """Query the system."""
        logger.info(f"\nQuery: {question}")
        
        # Embed query
        query_embedding = self.model.encode([question], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Display results
        logger.info(f"\nTop {top_k} Results:")
        logger.info("="*60)
        
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
            chunk = self.chunks[idx]
            logger.info(f"\nRank {rank} (Score: {score:.3f})")
            logger.info(f"Document: {chunk['doc_id']}")
            logger.info(f"Section: {chunk.get('section', 'N/A')}")
            logger.info(f"Text: {chunk['text'][:200]}...")
            logger.info("-"*60)
        
        return indices[0], scores[0]
    
    def interactive(self):
        """Interactive query loop."""
        print("\n" + "="*60)
        print("DOCUMENT INTELLIGENCE SYSTEM - Interactive Mode")
        print("="*60)
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                question = input("Your question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if not question:
                    continue
                
                self.query(question)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")


def main():
    try:
        system = DocumentQuerySystem()
        system.interactive()
    except FileNotFoundError as e:
        logger.error(f"Missing files: {e}")
        logger.error("Please run these commands first:")
        logger.error("  1. python download_real_data_sources.py")
        logger.error("  2. python -m ingestion.process_documents")
        logger.error("  3. python -m transformation.embed_all_documents")


if __name__ == "__main__":
    main()

