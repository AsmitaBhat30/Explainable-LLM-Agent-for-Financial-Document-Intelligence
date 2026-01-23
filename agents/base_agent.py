from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic."""
        pass
    
    def log_decision(self, decision: str, confidence: float):
        """Log agent decisions for audit trail."""
        print(f"[{self.name}] Decision: {decision} (confidence: {confidence:.2f})")