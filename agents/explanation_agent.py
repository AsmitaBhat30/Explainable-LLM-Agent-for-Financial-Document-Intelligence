from typing import Dict, List
from .base_agent import BaseAgent

class ExplanationAgent(BaseAgent):
    def __init__(self, llm_client):
        super().__init__("Explanation")
        self.llm = llm_client
        
    def execute(self, input_data: Dict) -> Dict:
        """Generate traceable answer with citations."""
        chunks = input_data.get("retrieved_chunks", [])
        query = input_data.get("query", "")
        compliance_info = input_data.get("compliance", {})
        
        # Build context from chunks
        context = self._build_context(chunks)
        
        # Generate answer with LLM
        prompt = self._create_prompt(query, context, compliance_info)
        answer = self._call_llm(prompt)
        
        # Extract citations
        citations = self._extract_citations(chunks)
        
        # Calculate confidence
        confidence = min(
            input_data.get("retrieval_confidence", 0.5),
            compliance_info.get("confidence", 0.5)
        )
        
        self.log_decision("Answer generated", confidence)
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "potential_risks": self._identify_risks(compliance_info),
            "agent": self.name
        }
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context from retrieved chunks."""
        return "\n\n".join([
            f"[Doc: {c['doc_id']}, Section: {c['section']}]\n{c['text']}"
            for c in chunks
        ])
    
    def _create_prompt(self, query: str, context: str, compliance: Dict) -> str:
        """Create LLM prompt with safety guidelines."""
        return f"""Answer the following question based ONLY on the provided context.

Question: {query}

Context:
{context}

Compliance notes: {compliance.get('regulatory_flags', [])}

Provide a clear answer with citations. If you cannot answer based on the context, say so explicitly."""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API (stub for now)."""
        # In production: call OpenAI/Anthropic API
        return "Answer based on provided documents [implementation needed]"
    
    def _extract_citations(self, chunks: List[Dict]) -> List[Dict]:
        """Extract citation information."""
        return [
            {
                "doc_id": c["doc_id"],
                "section": c["section"],
                "page_range": c.get("page_range", [])
            }
            for c in chunks
        ]
    
    def _identify_risks(self, compliance: Dict) -> List[str]:
        """Identify potential risks or missing information."""
        risks = []
        
        if compliance.get("risk_level") == "HIGH":
            risks.append("High regulatory sensitivity - requires legal review")
        
        if compliance.get("requires_review"):
            risks.append("Manual compliance check recommended")
        
        return risks