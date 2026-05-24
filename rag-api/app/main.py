import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAIError

from config import SUPPORTED_EXTENSIONS
from models import DocumentListItem, DocumentResponse, QueryRequest, QueryResponse, SourceChunk
from services.document_service import UnsupportedFileType, parse_and_chunk
from services.embedding_service import embed_texts
from services.rag_service import answer_question
from services.vector_store_service import add_chunks, delete_document, list_documents
from services.web_search_service import is_enabled as web_search_enabled

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in environment variables")
    logger.info("rag-api ready")
    yield
    logger.info("Shutting down rag-api")


app = FastAPI(
    title="RAG Document Q&A API",
    description="Upload PDFs and ask questions using Retrieval-Augmented Generation",
    version="1.0.0",
    lifespan=lifespan,
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
    return {
        "status": "rag-api is running",
        "supported_uploads": sorted(SUPPORTED_EXTENSIONS),
        "web_search_enabled": web_search_enabled(),
    }


@app.post("/documents/upload", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        doc_id, chunks = parse_and_chunk(file_bytes, file.filename)
    except UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Parse error for {file.filename}: {e}")
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    if not chunks:
        raise HTTPException(status_code=422, detail="No content could be extracted from the file")

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
        answer, chunks, web_used = answer_question(
            req.question,
            doc_id=req.doc_id,
            use_web_search=req.use_web_search,
        )
    except OpenAIError:
        raise HTTPException(status_code=502, detail="AI service unavailable")

    sources = [
        SourceChunk(
            text=chunk["text"][:300],
            doc_id=chunk["metadata"]["doc_id"],
            filename=chunk["metadata"]["filename"],
            chunk_index=chunk["metadata"]["chunk_index"],
            source_type=chunk["metadata"].get("source_type", "document"),
            url=chunk["metadata"].get("url"),
        )
        for chunk in chunks
    ]

    return QueryResponse(answer=answer, sources=sources, web_search_used=web_used)
