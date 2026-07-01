# Explainable LLM Agent for Financial Document Intelligence

## Project Overview

A RAG-based AI system that ingests financial/regulatory PDFs, answers compliance questions, and produces traceable explanations with citations. Built for risk and compliance teams.

**Domains covered:** SEC EDGAR 10-K filings, MiFID II, PSD2, GDPR, CRR, BaFin Documents, Basel III, ECB Supervisory Manual.

## Architecture

```
ingestion/        PDF parsing → data/raw → data/parsed
transformation/   Chunking (512 tok, 50 overlap) + FAISS embeddings
agents/           Retriever → Compliance → Explanation pipeline
api/              FastAPI (port 8000) with SSE streaming
validation/       Pydantic schemas + quality checks
monitoring/       Prometheus metrics + audit logger
evaluation/       Test cases + metrics (faithfulness, citation coverage)
```

**Agent pipeline:** `RetrieverAgent` → `ComplianceAgent` → `ExplanationAgent`. Each logs decisions via `BaseAgent.log_decision()` for audit trail.

## Stack

- Python 3.10+, FastAPI, LangChain, OpenAI API
- sentence-transformers (`all-MiniLM-L6-v2`), FAISS (IVF index)
- Pydantic v2, Pandera for schema validation
- pytest + pytest-cov, black, flake8, mypy
- Docker / docker-compose, DVC for data versioning
- Prometheus for metrics

## Code Conventions

- **Formatting:** `black` (line length 88). Run before committing.
- **Linting:** `flake8` — fix all warnings, no `# noqa` unless justified.
- **Types:** `mypy` with strict mode. All public functions must have type annotations.
- **Tests:** pytest. Unit tests in `tests/unit/`, integration in `tests/integration/`. Never mock the FAISS vector store in integration tests — use a real in-memory index.
- **No stubs in production paths.** The `_call_llm` stub in `ExplanationAgent` and hardcoded token in `api/main.py` (`SECRET_TOKEN`) must not be shipped as-is.
- **Comments:** only for non-obvious compliance logic or LLM prompt rationale. No docstrings paraphrasing type signatures.

## Security & Compliance Rules

- **PII redaction is always on** (`security.pii_redaction: true` in config). Never disable it.
- **Do not log raw query text** that may contain PII — use hashed identifiers in audit logs.
- **The hardcoded `SECRET_TOKEN = "dev-token-12345"` in `api/main.py:152` is dev-only.** Never commit or suggest production secrets in source files; use env vars / secrets manager.
- **CORS is open (`allow_origins=["*"]`)** — flag this in any PR targeting production.
- High-risk regulatory domains (GDPR, personal data, privacy) trigger `requires_review=True` — don't suppress that flag in code paths.
- Data retention is 90 days per config; don't write code that bypasses retention logic.

## Running the Project

```bash
# Start API server
uvicorn api.main:app --reload --port 8000

# Run via Docker
docker-compose up --build

# Ingest documents
python ingestion/process_documents.py

# Embed all documents
python transformation/embed_all_documents.py

# Query the system
python scripts/query_system.py

# Run evaluation
python scripts/run_evaluation.py
```

## Testing

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
pytest tests/unit/ -v            # unit only
pytest tests/integration/ -v     # integration only
```

## Linting & Type Checking

```bash
black .
flake8 .
mypy . --ignore-missing-imports
```

## Config

All runtime parameters live in `configs/base.yaml`. Override via env vars or pass a custom config path. Do not hardcode values that belong in config.

## Agent Extension Pattern

To add a new agent:
1. Subclass `BaseAgent` in `agents/`
2. Implement `execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]`
3. Call `self.log_decision(...)` for every significant decision
4. Wire into the pipeline in `api/main.py` or `scripts/query_system.py`
5. Add unit tests in `tests/unit/`