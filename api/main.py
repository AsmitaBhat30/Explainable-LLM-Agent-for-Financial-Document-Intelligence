import asyncio
import json
import logging
import os
import time
from typing import List, Optional

import faiss
import numpy as np
import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from openai import OpenAI, RateLimitError, APIStatusError
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from agents.compliance_agent import ComplianceAgent
from agents.explanation_agent import ExplanationAgent
from agents.retriever_agent import RetrieverAgent
from auth.crud import authenticate_user, create_user, get_user_by_username
from auth.database import Base, engine, get_db
from auth.dependencies import get_current_user
from auth.jwt import create_access_token
from auth.models import User
from auth.schemas import Token, UserCreate, UserResponse
from indexing.vector_store import FaissVectorStore
from monitoring.audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Load project config
# ---------------------------------------------------------------------------

with open("configs/base.yaml") as _f:
    _cfg = yaml.safe_load(_f)

_security_cfg = _cfg.get("security", {})
ENABLE_AUTH: bool = _security_cfg.get("enable_auth", True)

_monitoring_cfg = _cfg.get("monitoring", {})
_audit_log_path: str = _monitoring_cfg.get("audit_log_path", "logs/audit.log")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Fintech Document Intelligence API")
logger = logging.getLogger(__name__)
audit = AuditLogger(log_file=_audit_log_path)

_cors_origins: List[str] = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"null|file://.*",  # allow file:// when opening HTML directly
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


_embedder: Optional[SentenceTransformer] = None
_vector_store: Optional[FaissVectorStore] = None
_retriever: Optional[RetrieverAgent] = None
_compliance: Optional[ComplianceAgent] = None
_explanation: Optional[ExplanationAgent] = None


@app.on_event("startup")
def _startup() -> None:
    global _embedder, _vector_store, _retriever, _compliance, _explanation

    Base.metadata.create_all(bind=engine)

    _agents_cfg = _cfg.get("agents", {})
    _embed_cfg = _cfg.get("embeddings", {})
    _features_dir = _cfg.get("data", {}).get("features_dir", "data/features")

    # --- Embedder ---
    model_name: str = _embed_cfg.get("model", "sentence-transformers/all-MiniLM-L6-v2")
    logger.info("Loading embedding model: %s", model_name)
    _embedder = SentenceTransformer(model_name)

    # --- Vector store ---
    index_path = os.path.join(_features_dir, "faiss.index")
    chunks_path = os.path.join(_features_dir, "chunks_metadata.json")
    if os.path.exists(index_path) and os.path.exists(chunks_path):
        logger.info("Loading FAISS index from %s", index_path)
        raw_index = faiss.read_index(index_path)
        dim = raw_index.d
        _vector_store = FaissVectorStore(dim=dim)
        _vector_store._index = raw_index
        with open(chunks_path, encoding="utf-8") as f:
            _vector_store._chunks = json.load(f)
        logger.info("Loaded %d vectors into vector store", _vector_store.ntotal)
    else:
        logger.warning(
            "FAISS index not found at %s — run embed_all_documents.py first. "
            "Retrieval will return empty results.",
            index_path,
        )
        _vector_store = FaissVectorStore(dim=384)

    # --- Agents ---
    top_k: int = _agents_cfg.get("retriever", {}).get("top_k", 5)
    _retriever = RetrieverAgent(vector_store=_vector_store, top_k=top_k)
    _compliance = ComplianceAgent(regulations=["GDPR", "MiFID II", "PSD2", "Basel III", "BaFin"])

    _exp_cfg = _agents_cfg.get("explanation", {})
    llm_base_url = os.getenv("LLM_BASE_URL")  # e.g. http://localhost:11434/v1 for Ollama
    llm_model = os.getenv("LLM_MODEL") or _exp_cfg.get("model", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY") or "ollama"  # Ollama ignores the key value

    if llm_base_url:
        llm_client = OpenAI(base_url=llm_base_url, api_key=api_key)
        logger.info("ExplanationAgent using local LLM at %s (model: %s)", llm_base_url, llm_model)
    elif api_key and api_key != "ollama":
        llm_client = OpenAI(api_key=api_key)
        logger.info("ExplanationAgent using OpenAI (model: %s)", llm_model)
    else:
        logger.error("Neither LLM_BASE_URL nor OPENAI_API_KEY is set — ExplanationAgent will raise on queries")
        return

    _explanation = ExplanationAgent(
        llm_client=llm_client,
        model=llm_model,
        temperature=_exp_cfg.get("temperature", 0.0),
    )


# ---------------------------------------------------------------------------
# Conditional auth dependency
# When security.enable_auth is False in configs/base.yaml, the guard
# passes through without requiring a token (useful for local dev/testing).
# ---------------------------------------------------------------------------

_oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def auth_guard(
    token: Optional[str] = Depends(_oauth2_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not ENABLE_AUTH:
        return None
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user(token=token, db=db)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        audit.log_auth_event(form_data.username, "login", success=False, detail="bad credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username})
    audit.log_auth_event(user.username, "login", success=True)
    return Token(access_token=token, token_type="bearer")


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    if get_user_by_username(db, body.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    user = create_user(db, body.username, body.password)
    return user


# ---------------------------------------------------------------------------
# Query models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    include_compliance_check: Optional[bool] = True


class Citation(BaseModel):
    doc_id: str
    section: str
    page_range: List[int]


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    confidence: float
    potential_risks: List[str]
    compliance_risk_level: str


# ---------------------------------------------------------------------------
# Protected query route
# ---------------------------------------------------------------------------

@app.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    current_user: Optional[User] = Depends(auth_guard),
) -> StreamingResponse:
    username = current_user.username if current_user else "anonymous"
    audit.log_query(username, request.query, {"top_k": request.top_k})

    query = request.query

    if _retriever is None or _compliance is None or _explanation is None:
        raise HTTPException(
            status_code=503,
            detail="Pipeline not ready — check server startup logs (OPENAI_API_KEY set? FAISS index built?)",
        )

    async def generate():
        t0 = time.monotonic()

        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'step': 1, 'total': 4})}\n\n"

        # --- Step 1: embed query (blocking; run in thread pool) ---
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating embedding...', 'step': 2, 'total': 4})}\n\n"
        loop = asyncio.get_event_loop()
        query_embedding: np.ndarray = await loop.run_in_executor(
            None, lambda: _embedder.encode([query], convert_to_numpy=True)[0]
        )

        # --- Step 2: retrieve ---
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...', 'step': 3, 'total': 4})}\n\n"
        retrieval_result = await loop.run_in_executor(
            None,
            lambda: _retriever.execute(
                {"query": query, "query_embedding": query_embedding}
            ),
        )
        chunks = retrieval_result["retrieved_chunks"]
        retrieval_confidence = retrieval_result["confidence"]

        docs_payload = [
            {
                "doc_id": c.get("doc_id", ""),
                "section": c.get("section", ""),
                "score": round(c.get("score", 0.0), 4),
                "text": c.get("text", "")[:300],
            }
            for c in chunks
        ]
        yield f"data: {json.dumps({'type': 'retrieval', 'documents': docs_payload})}\n\n"

        # --- Step 3: compliance check ---
        compliance_result = _compliance.execute({"query": query})

        # --- Step 4: explanation ---
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...', 'step': 4, 'total': 4})}\n\n"
        try:
            explanation_result = await loop.run_in_executor(
                None,
                lambda: _explanation.execute(
                    {
                        "query": query,
                        "retrieved_chunks": chunks,
                        "compliance": compliance_result,
                        "retrieval_confidence": retrieval_confidence,
                    }
                ),
            )
        except RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'OpenAI quota exceeded — add credits at platform.openai.com/account/billing'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        except APIStatusError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': f'OpenAI API error {exc.status_code}: {exc.message}'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        answer: str = explanation_result["answer"]
        citations = explanation_result["citations"]
        confidence = explanation_result["confidence"]
        potential_risks = explanation_result["potential_risks"]

        # Stream answer tokens
        words = answer.split()
        for i, word in enumerate(words):
            yield f"data: {json.dumps({'type': 'token', 'token': word + ' ', 'index': i})}\n\n"
            await asyncio.sleep(0.02)

        latency_ms = round((time.monotonic() - t0) * 1000)
        result = {
            "type": "complete",
            "answer": answer,
            "citations": citations,
            "confidence": round(confidence, 4),
            "risk_level": compliance_result["risk_level"],
            "requires_review": compliance_result["requires_review"],
            "potential_risks": potential_risks,
            "regulatory_flags": compliance_result["regulatory_flags"],
            "latency_ms": latency_ms,
        }
        yield f"data: {json.dumps(result)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.get("/")
def read_root() -> dict:
    return {
        "message": "Fintech Document Intelligence API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {"docs": "/docs", "query": "/query/stream", "health": "/health"},
    }


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "version": "1.0.0"}
