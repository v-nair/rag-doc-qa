from pydantic import BaseModel, field_validator


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class DocumentListItem(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class QueryRequest(BaseModel):
    question: str
    doc_id: str | None = None

    @field_validator("question")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be empty")
        return v.strip()


class SourceChunk(BaseModel):
    text: str
    doc_id: str
    filename: str
    chunk_index: int


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
