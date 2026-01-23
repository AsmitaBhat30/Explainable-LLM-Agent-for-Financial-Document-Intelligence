from typing import List, Dict
import time
import numpy as np

class EvaluationMetrics:
    def __init__(self):
        self.results = []
        
    def calculate_hallucination_rate(self, answers: List[Dict]) -> float:
        """Estimate hallucination rate based on citation coverage."""
        if not answers:
            return 0.0
        
        hallucinated = sum(1 for a in answers if not a.get("citations"))
        return hallucinated / len(answers)
    
    def calculate_citation_coverage(self, answers: List[Dict]) -> float:
        """Calculate percentage of answers with citations."""
        if not answers:
            return 0.0
        
        with_citations = sum(1 for a in answers if a.get("citations"))
        return with_citations / len(answers)
    
    def measure_consistency(self, query: str, n_runs: int = 5) -> float:
        """Measure answer consistency across multiple runs."""
        # Stub - would run same query multiple times
        return 0.85  # Example consistency score
    
    def measure_latency(self, func, *args, **kwargs) -> tuple:
        """Measure function execution time."""
        start = time.time()
        result = func(*args, **kwargs)
        latency = time.time() - start
        return result, latency
    
    def generate_report(self) -> Dict:
        """Generate evaluation report."""
        return {
            "hallucination_rate": self.calculate_hallucination_rate(self.results),
            "citation_coverage": self.calculate_citation_coverage(self.results),
            "mean_latency": np.mean([r.get("latency", 0) for r in self.results]),
            "total_queries": len(self.results)
        }