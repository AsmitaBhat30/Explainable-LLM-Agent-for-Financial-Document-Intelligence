import asyncio
import json
import logging
import os
from typing import List, Optional

import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.crud import authenticate_user, create_user, get_user_by_username
from auth.database import Base, engine, get_db
from auth.dependencies import get_current_user
from auth.jwt import create_access_token
from auth.models import User
from auth.schemas import Token, UserCreate, UserResponse
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


@app.on_event("startup")
def _create_tables() -> None:
    Base.metadata.create_all(bind=engine)


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

    async def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'step': 1, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating embedding...', 'step': 2, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...', 'step': 3, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)

        docs = [
            {
                "doc_id": "psd2_2015",
                "section": "Article 97",
                "score": 0.92,
                "text": "Payment service providers shall apply strong customer authentication...",
            }
        ]
        yield f"data: {json.dumps({'type': 'retrieval', 'documents': docs})}\n\n"

        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...', 'step': 4, 'total': 4})}\n\n"

        answer = "Yes, PSD2 Article 97 requires strong customer authentication for electronic payment transactions."
        for i, word in enumerate(answer.split()):
            yield f"data: {json.dumps({'type': 'token', 'token': word + ' ', 'index': i})}\n\n"
            await asyncio.sleep(0.05)

        result = {
            "type": "complete",
            "answer": answer,
            "citations": [{"doc_id": "psd2_2015", "section": "Article 97", "page": 124}],
            "confidence": 0.89,
            "risk_level": "MEDIUM",
            "latency_ms": 2100,
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
