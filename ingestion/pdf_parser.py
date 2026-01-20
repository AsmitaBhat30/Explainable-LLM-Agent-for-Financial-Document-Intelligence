import hashlib
import PyPDF2
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class DocumentParser:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        
    def parse_pdf(self, pdf_path: Path) -> Dict:
        """Extract text and metadata from PDF."""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Extract text
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # Generate hash for versioning
            doc_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Extract metadata
            metadata = {
                "doc_id": doc_hash[:16],
                "doc_type": self._infer_type(pdf_path),
                "source": "public",
                "version": datetime.now().strftime("%Y"),
                "language": "en",
                "ingestion_date": datetime.now().isoformat(),
                "page_count": len(reader.pages),
                "file_hash": doc_hash,
                "file_path": str(pdf_path)
            }
            
            return {
                "metadata": metadata,
                "text": text,
                "page_count": len(reader.pages)
            }
    
    def _infer_type(self, path: Path) -> str:
        """Infer document type from filename."""
        name = path.stem.lower()
        if "annual" in name or "report" in name:
            return "annual_report"
        elif "regulation" in name or "mifid" in name or "psd2" in name:
            return "regulation"
        elif "contract" in name:
            return "contract"
        return "unknown"