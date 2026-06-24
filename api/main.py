from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import asyncio
import json

app = FastAPI(title="Fintech Document Intelligence API")
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """Stream responses in real-time."""
    
    async def generate():
        # Step 1
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'step': 1, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 2
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating embedding...', 'step': 2, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 3
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...', 'step': 3, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 4: Retrieved docs
        docs = [
            {
                "doc_id": "psd2_2015",
                "section": "Article 97",
                "score": 0.92,
                "text": "Payment service providers shall apply strong customer authentication..."
            }
        ]
        yield f"data: {json.dumps({'type': 'retrieval', 'documents': docs})}\n\n"
        
        # Step 5: Stream answer
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...', 'step': 4, 'total': 4})}\n\n"
        
        answer = "Yes, PSD2 Article 97 requires strong customer authentication for electronic payment transactions."
        for i, word in enumerate(answer.split()):
            yield f"data: {json.dumps({'type': 'token', 'token': word + ' ', 'index': i})}\n\n"
            await asyncio.sleep(0.05)
        
        # Step 6: Complete
        result = {
            'type': 'complete',
            'answer': answer,
            'citations': [{'doc_id': 'psd2_2015', 'section': 'Article 97', 'page': 124}],
            'confidence': 0.89,
            'risk_level': 'MEDIUM',
            'latency_ms': 2100
        }
        yield f"data: {json.dumps(result)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
    """Stream responses in real-time."""
    
    async def generate():
        # Step 1: Processing
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'step': 1, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 2: Embedding
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating embedding...', 'step': 2, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 3: Searching
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...', 'step': 3, 'total': 4})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 4: Retrieved docs
        docs = [
            {"doc_id": "psd2_2015", "section": "Article 97", "score": 0.92, 
             "text": "Strong customer authentication required..."}
        ]
        yield f"data: {json.dumps({'type': 'retrieval', 'documents': docs})}\n\n"
        
        # Step 5: Stream answer word by word
        answer = "Yes, PSD2 Article 97 requires strong customer authentication for electronic payments."
        for i, word in enumerate(answer.split()):
            yield f"data: {json.dumps({'type': 'token', 'token': word + ' ', 'index': i})}\n\n"
            await asyncio.sleep(0.05)
        
        # Step 6: Complete
        yield f"data: {json.dumps({'type': 'complete', 'answer': answer, 'citations': [{'doc_id': 'psd2_2015', 'section': 'Article 97', 'page': 124}], 'confidence': 0.89, 'risk_level': 'MEDIUM', 'latency_ms': 2100})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/")
def read_root():
    """Homepage - shows API is running."""
    return {
        "message": "Fintech Document Intelligence API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "query": "/query",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

SECRET_TOKEN = "dev-token-12345"  # Development only!

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify token."""
    if credentials.credentials != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return "authenticated_user"

def process_query(request: QueryRequest) -> dict:
    """Process query through agent pipeline (stub)."""
    # In production: full agent orchestration
    return {
        "answer": "Sample answer",
        "citations": [],
        "confidence": 0.85,
        "potential_risks": [],
        "compliance_risk_level": "LOW"
    }