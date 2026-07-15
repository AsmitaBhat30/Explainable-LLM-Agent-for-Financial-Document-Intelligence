from typing import Dict, List
from .base_agent import BaseAgent


class ExplanationAgent(BaseAgent):
    def __init__(
        self,
        llm_client,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ):
        super().__init__("Explanation")
        self.llm = llm_client
        self.model = model
        self.temperature = temperature

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
            compliance_info.get("confidence", 0.5),
        )

        self.log_decision("Answer generated", confidence)

        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "potential_risks": self._identify_risks(compliance_info),
            "agent": self.name,
        }

    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context from retrieved chunks."""
        return "\n\n".join(
            [
                f"[Doc: {c['doc_id']}, Section: {c['section']}]\n{c['text']}"
                for c in chunks
            ]
        )

    def _create_prompt(self, query: str, context: str, compliance: Dict) -> str:
        """Create LLM prompt with safety guidelines."""
        return f"""Answer the following question based ONLY on the provided context.

Question: {query}

Context:
{context}

Compliance notes: {compliance.get('regulatory_flags', [])}

Provide a clear answer with citations. If you cannot answer based on the
context, say so explicitly."""

    def _call_llm(self, prompt: str) -> str:
        """Call the injected LLM client to generate a grounded answer.

        No stub fallback: an unconfigured llm_client is a setup error, not a
        degraded mode, since a fabricated answer would silently defeat the
        faithfulness/hallucination metrics downstream.
        """
        if self.llm is None:
            raise RuntimeError(
                "ExplanationAgent has no llm_client configured. Construct "
                "one with a real OpenAI-compatible client, e.g. "
                "OpenAI(api_key=os.environ['OPENAI_API_KEY']), and pass it "
                "into ExplanationAgent(llm_client=...)."
            )

        response = self.llm.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a compliance research assistant. Answer "
                        "strictly from the provided context. Never state a "
                        "fact that is not present in the context, and say "
                        "explicitly when the context is insufficient."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    def _extract_citations(self, chunks: List[Dict]) -> List[Dict]:
        """Extract citation information."""
        return [
            {
                "doc_id": c["doc_id"],
                "section": c["section"],
                "page_range": c.get("page_range", []),
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
