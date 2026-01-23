from typing import List, Dict
import numpy as np
from .base_agent import BaseAgent

class RetrieverAgent(BaseAgent):
    def __init__(self, vector_store, top_k: int = 5):
        super().__init__("Retriever")
        self.vector_store = vector_store
        self.top_k = top_k
        
    def execute(self, input_data: Dict) -> Dict:
        """Retrieve relevant document chunks."""
        query = input_data["query"]
        query_embedding = input_data["query_embedding"]
        
        # Search vector store
        results = self.vector_store.search(query_embedding, k=self.top_k)
        
        # Calculate confidence based on similarity scores
        if results:
            confidence = float(np.mean([r["score"] for r in results]))
        else:
            confidence = 0.0
        
        self.log_decision(f"Retrieved {len(results)} chunks", confidence)
        
        return {
            "retrieved_chunks": results,
            "confidence": confidence,
            "agent": self.name
        }