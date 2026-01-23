import pytest
from transformation.chunker import StructureAwareChunker

def test_chunker_basic():
    """Test basic chunking functionality."""
    chunker = StructureAwareChunker(chunk_size=10, overlap=2)
    
    text = "This is a test document with multiple sections."
    metadata = {"doc_id": "test_001"}
    
    chunks = chunker.chunk_document(text, metadata)
    
    assert len(chunks) > 0
    assert all("chunk_id" in c for c in chunks)
    assert all("text" in c for c in chunks)

def test_chunker_preserves_metadata():
    """Test that chunker preserves document metadata."""
    chunker = StructureAwareChunker()
    
    metadata = {
        "doc_id": "test_002",
        "doc_type": "annual_report"
    }
    
    chunks = chunker.chunk_document("Sample text", metadata)
    
    assert all(c["doc_id"] == "test_002" for c in chunks)