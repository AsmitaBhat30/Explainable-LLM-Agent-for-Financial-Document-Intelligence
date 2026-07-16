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
        flags = compliance.get("regulatory_flags", [])
        flags_line = f"Relevant regulations: {', '.join(flags)}.\n" if flags else ""
        return f"""Answer the question using ONLY the context passages below.

RULES — follow exactly:
1. Answer the question directly. Do NOT generate your own questions.
2. Do NOT include "Q:" / "A:" markers or any dialogue format.
3. Every factual claim must be supported by the context. Do not add external knowledge.
4. If the context does not contain enough information, respond with exactly:
   "The provided documents do not contain sufficient information to answer this question."
5. Be concise. No preamble, no filler.

{flags_line}QUESTION: {query}

CONTEXT PASSAGES:
{context}

ANSWER:"""

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
                        "You are a compliance research assistant. "
                        "Answer questions using ONLY the context passages given by the user. "
                        "Never generate your own questions. Never use the 'Q:' or 'A:' format. "
                        "Never add information not present in the context. "
                        "Be direct and concise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    def _extract_citations(self, chunks: List[Dict]) -> List[Dict]:
        """Extract citation information including a text snippet for UI preview."""
        return [
            {
                "doc_id": c["doc_id"],
                "section": c["section"],
                "page_range": c.get("page_range", []),
                "score": round(float(c.get("score", 0.0)), 4),
                "text": c.get("text", "")[:600],
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
