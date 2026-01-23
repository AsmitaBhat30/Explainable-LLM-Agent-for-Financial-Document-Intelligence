from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class EmbeddingPipeline:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for chunks."""
        texts = [chunk["text"] for chunk in chunks]
        
        # Batch embedding generation
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=True)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()
        
        # Log statistics
        self._log_embedding_stats(embeddings)
        
        return chunks
    
    def _log_embedding_stats(self, embeddings: np.ndarray):
        """Log embedding quality metrics."""
        # Calculate mean similarity
        similarities = np.dot(embeddings, embeddings.T)
        mean_sim = np.mean(similarities[np.triu_indices_from(similarities, k=1)])
        
        logger.info(f"Embedding statistics:")
        logger.info(f"  Shape: {embeddings.shape}")
        logger.info(f"  Mean norm: {np.mean(np.linalg.norm(embeddings, axis=1)):.4f}")
        logger.info(f"  Mean similarity: {mean_sim:.4f}")
        
        # Detect potential collapse
        if mean_sim > 0.9:
            logger.warning("High mean similarity detected - possible representation collapse!")