from typing import List, Dict
import re

class StructureAwareChunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
    def chunk_document(self, text: str, metadata: Dict) -> List[Dict]:
        """Create structure-aware chunks."""
        chunks = []
        
        # Detect sections (simplified - extend with NLP)
        sections = self._detect_sections(text)
        
        chunk_id = 0
        for section_name, section_text, page_hint in sections:
            # Chunk within sections
            section_chunks = self._chunk_text(section_text)
            
            for chunk_text in section_chunks:
                chunks.append({
                    "chunk_id": f"{metadata['doc_id']}_chunk_{chunk_id}",
                    "doc_id": metadata["doc_id"],
                    "section": section_name,
                    "page_range": page_hint,
                    "text": chunk_text,
                    "embedding_version": "v1"
                })
                chunk_id += 1
        
        return chunks
    
    def _detect_sections(self, text: str) -> List[tuple]:
        """Detect document sections (simplified)."""
        # Pattern for common headers
        section_pattern = r'^([A-Z][A-Za-z\s]{3,30})\n'
        
        sections = []
        current_section = "Introduction"
        current_text = []
        
        for line in text.split('\n'):
            match = re.match(section_pattern, line)
            if match:
                # Save previous section
                if current_text:
                    sections.append((current_section, '\n'.join(current_text), [0, 0]))
                current_section = match.group(1)
                current_text = []
            else:
                current_text.append(line)
        
        # Add final section
        if current_text:
            sections.append((current_section, '\n'.join(current_text), [0, 0]))
        
        return sections
    
    def _chunk_text(self, text: str) -> List[str]:
        """Chunk text with overlap."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks