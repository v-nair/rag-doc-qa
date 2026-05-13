from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAIError
from dotenv import load_dotenv
import logging
import os

from models import DocumentResponse, DocumentListItem, QueryRequest, QueryResponse, SourceChunk
from services.document_service import parse_and_chunk
from services.embedding_service import embed_texts
from services.vector_store_service import add_chunks, list_documents, delete_document
from services.rag_service import answer_question

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is not set in environment variables")

app = FastAPI(
    title="RAG Document Q&A API",
    description="Upload PDFs and ask questions using Retrieval-Augmented Generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {"status": "rag-api is running"}


@app.post("/documents/upload", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        doc_id, chunks = parse_and_chunk(file_bytes)
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise HTTPException(status_code=422, detail="Could not parse PDF")

    if not chunks:
        raise HTTPException(status_code=422, detail="No text could be extracted from the PDF")

    try:
        embeddings = embed_texts(chunks)
    except OpenAIError as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=502, detail="Embedding service unavailable")

    add_chunks(doc_id, file.filename, chunks, embeddings)
    logger.info(f"Uploaded {file.filename} as {doc_id} ({len(chunks)} chunks)")
    return DocumentResponse(doc_id=doc_id, filename=file.filename, chunk_count=len(chunks))


@app.get("/documents", response_model=list[DocumentListItem], tags=["Documents"])
def get_documents():
    return list_documents()


@app.delete("/documents/{doc_id}", tags=["Documents"])
def remove_document(doc_id: str):
    deleted = delete_document(doc_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    logger.info(f"Deleted document {doc_id} ({deleted} chunks removed)")
    return {"status": "deleted", "doc_id": doc_id, "chunks_removed": deleted}


@app.post("/query", response_model=QueryResponse, tags=["Query"])
def query(req: QueryRequest):
    try:
        answer, chunks = answer_question(req.question, req.doc_id)
    except OpenAIError:
        raise HTTPException(status_code=502, detail="AI service unavailable")

    sources = [
        SourceChunk(
            text=chunk["text"][:300],
            doc_id=chunk["metadata"]["doc_id"],
            filename=chunk["metadata"]["filename"],
            chunk_index=chunk["metadata"]["chunk_index"]
        )
        for chunk in chunks
    ]

    return QueryResponse(answer=answer, sources=sources)
