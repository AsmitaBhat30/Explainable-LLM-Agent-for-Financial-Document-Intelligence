import pandera as pa
from pandera.typing import Series, DataFrame

class DocumentMetadataSchema(pa.DataFrameModel):
    doc_id: Series[str] = pa.Field(str_length={"min_value": 1})
    doc_type: Series[str] = pa.Field(isin=["annual_report", "regulation", "contract", "unknown"])
    source: Series[str] = pa.Field(str_length={"min_value": 1})
    version: Series[str]
    language: Series[str] = pa.Field(str_length=2)
    ingestion_date: Series[str]
    page_count: Series[int] = pa.Field(ge=1)
    file_hash: Series[str] = pa.Field(str_length=64)
    
    class Config:
        strict = True
        coerce = True

class ChunkSchema(pa.DataFrameModel):
    chunk_id: Series[str]
    doc_id: Series[str]
    section: Series[str]
    page_range: Series[object]  # List of ints
    text: Series[str] = pa.Field(str_length={"min_value": 10})
    embedding_version: Series[str]
    
    class Config:
        strict = True