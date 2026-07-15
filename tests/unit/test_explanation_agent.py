import pytest

from agents.explanation_agent import ExplanationAgent


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeLLMClient:
    """Mimics the OpenAI SDK's client.chat.completions.create(...) shape."""

    def __init__(
        self,
        content="Strong customer authentication is required for electronic payments.",
    ):
        self.chat = _FakeChat(content)


CHUNKS = [
    {
        "doc_id": "psd2_2015",
        "section": "Article 97",
        "page_range": [124, 124],
        "text": "Payment service providers shall apply strong customer authentication.",
    }
]


def test_execute_uses_injected_llm_client():
    fake_client = _FakeLLMClient(
        content="PSD2 requires strong customer authentication."
    )
    agent = ExplanationAgent(fake_client, model="gpt-4o-mini")

    result = agent.execute(
        {
            "query": "Does PSD2 require strong customer authentication?",
            "retrieved_chunks": CHUNKS,
            "compliance": {"regulatory_flags": ["psd2"], "confidence": 0.9},
            "retrieval_confidence": 0.9,
        }
    )

    assert result["answer"] == "PSD2 requires strong customer authentication."
    assert result["citations"] == [
        {"doc_id": "psd2_2015", "section": "Article 97", "page_range": [124, 124]}
    ]
    assert fake_client.chat.completions.last_kwargs["model"] == "gpt-4o-mini"


def test_call_llm_raises_without_configured_client():
    agent = ExplanationAgent(llm_client=None)

    with pytest.raises(RuntimeError):
        agent.execute(
            {
                "query": "Any question?",
                "retrieved_chunks": CHUNKS,
                "compliance": {},
                "retrieval_confidence": 0.5,
            }
        )


def test_prompt_includes_query_and_context():
    fake_client = _FakeLLMClient()
    agent = ExplanationAgent(fake_client)

    agent.execute(
        {
            "query": "Does PSD2 require strong customer authentication?",
            "retrieved_chunks": CHUNKS,
            "compliance": {},
            "retrieval_confidence": 0.9,
        }
    )

    sent_prompt = fake_client.chat.completions.last_kwargs["messages"][-1]["content"]
    assert "Does PSD2 require strong customer authentication?" in sent_prompt
    assert (
        "Payment service providers shall apply strong customer authentication."
        in sent_prompt
    )
