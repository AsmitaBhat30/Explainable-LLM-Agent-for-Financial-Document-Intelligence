import logging
import json
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    """Compliance-focused audit logging."""
    
    def __init__(self, log_file: str = "audit.log"):
        self.logger = logging.getLogger("audit")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_query(self, user: str, query: str, context: Dict[str, Any]):
        """Log query with full context."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "query",
            "user": user,
            "query": query,
            "context": context
        }
        self.logger.info(json.dumps(entry))
    
    def log_retrieval(self, query_id: str, documents: list, scores: list):
        """Log which documents influenced the answer."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "retrieval",
            "query_id": query_id,
            "documents": [
                {"doc_id": d, "score": s} 
                for d, s in zip(documents, scores)
            ]
        }
        self.logger.info(json.dumps(entry))
    
    def log_agent_decision(self, agent_name: str, decision: Dict[str, Any]):
        """Log agent decisions for auditability."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "agent_decision",
            "agent": agent_name,
            "decision": decision
        }
        self.logger.info(json.dumps(entry))