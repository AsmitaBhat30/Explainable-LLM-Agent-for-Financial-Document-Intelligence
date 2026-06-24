"""
Embed all processed documents and build vector index.
Usage: python -m transformation.embed_all_documents
"""

import json
import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Dict
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentEmbedder:
    """Embed all documents and create searchable vector index."""
    
    def __init__(
        self,
        parsed_dir: str = "data/parsed",
        output_dir: str = "data/features",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.parsed_dir = Path(parsed_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.all_chunks = []
        self.embeddings = []
    
    def load_all_documents(self) -> List[Dict]:
        """Load all processed documents from parsed directory."""
        documents = []
        
        json_files = list(self.parsed_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} processed documents")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")
        
        return documents
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Chunk all documents into searchable pieces."""
        from transformation.chunker import StructureAwareChunker
        
        chunker = StructureAwareChunker(chunk_size=512, overlap=50)
        all_chunks = []
        
        logger.info("Chunking documents...")
        for doc in tqdm(documents):
            metadata = {
                "doc_id": doc["doc_id"],
                "doc_type": doc["doc_type"],
                "source": doc["source"],
                "title": doc["title"]
            }
            
            chunks = chunker.chunk_document(doc["text"], metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks")
        return all_chunks
    
    def embed_chunks(self, chunks: List[Dict]) -> np.ndarray:
        """Generate embeddings for all chunks."""
        logger.info("Generating embeddings...")
        
        texts = [chunk["text"] for chunk in chunks]
        
        # Batch encode for efficiency
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        logger.info(f"Embedding shape: {embeddings.shape}")
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()
        
        return embeddings
    
    def build_faiss_index(self, embeddings: np.ndarray):
        """Build FAISS index for fast similarity search."""
        logger.info("Building FAISS index...")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create index (use IndexFlatIP for cosine similarity)
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(embeddings)
        
        logger.info(f"FAISS index built with {index.ntotal} vectors")
        return index
    
    def save_artifacts(self, chunks: List[Dict], index):
        """Save chunks and FAISS index."""
        # Save chunks as JSON
        chunks_file = self.output_dir / "chunks.json"
        logger.info(f"Saving chunks to {chunks_file}")
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        # Save FAISS index
        index_file = self.output_dir / "faiss.index"
        logger.info(f"Saving FAISS index to {index_file}")
        faiss.write_index(index, str(index_file))
        
        # Save metadata separately (without embeddings for readability)
        metadata_file = self.output_dir / "chunks_metadata.json"
        metadata = [
            {k: v for k, v in chunk.items() if k != "embedding"}
            for chunk in chunks
        ]
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info("All artifacts saved successfully")
    
    def run(self):
        """Execute full embedding pipeline."""
        logger.info("="*60)
        logger.info("DOCUMENT EMBEDDING PIPELINE")
        logger.info("="*60)
        
        # Step 1: Load documents
        documents = self.load_all_documents()
        if not documents:
            logger.error("No documents found! Run document processing first.")
            return
        
        # Step 2: Chunk documents
        chunks = self.chunk_documents(documents)
        self.all_chunks = chunks
        
        # Step 3: Generate embeddings
        embeddings = self.embed_chunks(chunks)
        self.embeddings = embeddings
        
        # Step 4: Build FAISS index
        index = self.build_faiss_index(embeddings)
        
        # Step 5: Save everything
        self.save_artifacts(chunks, index)
        
        # Summary
        logger.info("="*60)
        logger.info("EMBEDDING COMPLETE")
        logger.info("="*60)
        logger.info(f"Documents processed: {len(documents)}")
        logger.info(f"Total chunks: {len(chunks)}")
        logger.info(f"Embedding dimension: {self.embedding_dim}")
        logger.info(f"Output directory: {self.output_dir}")


def main():
    embedder = DocumentEmbedder()
    embedder.run()


if __name__ == "__main__":
    main()
