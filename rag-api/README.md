# rag-api

FastAPI backend service for the [RAG Document Q&A](../README.md) project. Handles PDF upload, text chunking, embedding generation, vector storage, and retrieval-augmented generation.

## Relationship to Other Services

| Service | Direction | Description |
| --- | --- | --- |
| `rag-ui` | ← receives requests | UI uploads PDFs and sends questions via REST |
| OpenAI Embeddings API | → calls | Embeds document chunks and query text |
| OpenAI Chat API | → calls | Generates answers using retrieved context |
| ChromaDB | ↔ reads/writes | Stores and queries vector embeddings |

## Service Structure

```text
app/
├── main.py                      # FastAPI app, lifespan, CORS, routes
├── models.py                    # Pydantic request/response models
├── config.py                    # Model names, chunk settings, ChromaDB path
└── services/
    ├── document_service.py      # PDF text extraction and chunk splitting
    ├── embedding_service.py     # OpenAI text-embedding-3-small client
    ├── vector_store_service.py  # ChromaDB CRUD and cosine similarity search
    └── rag_service.py           # Orchestrates retrieval + GPT-4o generation
```

## Configuration

`.env` (copy from `.env.example`):

```text
OPENAI_API_KEY=sk-...
```

`config.py` values:

| Constant | Value | Purpose |
| --- | --- | --- |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI model for vector embeddings |
| `CHAT_MODEL` | `gpt-4o` | OpenAI model for answer generation |
| `CHUNK_SIZE` | `1000` | Max characters per document chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `TOP_K_RESULTS` | `5` | Chunks retrieved per query |
| `CHROMA_PATH` | `/chroma_db` | ChromaDB persistence path (Docker volume) |

## Starting This Service

```bash
cp .env.example .env   # add OPENAI_API_KEY
docker compose up --build
```

Runs on `http://localhost:8000` · Swagger docs at `http://localhost:8000/docs`

## Logic — Pseudocode

```text
// ── UPLOAD ──────────────────────────────────────────────────
FUNCTION upload_document(pdf_bytes, filename):

    text = pypdf.extract_text(pdf_bytes)

    chunks = split(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

    embeddings = OpenAI.embed(chunks, model=EMBEDDING_MODEL)

    ChromaDB.store(chunks, embeddings, metadata={ filename, doc_id, chunk_index })

    RETURN { doc_id, chunk_count }


// ── QUERY ────────────────────────────────────────────────────
FUNCTION query(question, doc_id=None):

    q_embedding = OpenAI.embed(question, model=EMBEDDING_MODEL)

    top_chunks = ChromaDB.cosine_search(q_embedding, n=TOP_K_RESULTS, filter=doc_id)

    context = JOIN(top_chunks)
    answer  = GPT-4o.complete("Answer using only this context:\n{context}\n\n{question}")

    RETURN { answer, sources: top_chunks }
```

## Design Notes

- **Thread-safe ChromaDB init** — `PersistentClient` is lazily initialised with a `threading.Lock` to avoid race conditions on startup
- **Named Docker volume** — ChromaDB data persists at `/chroma_db` across container restarts
- **Scoped queries** — `doc_id` filter lets the UI query one document or all documents
- **Chunk overlap** — 200-char overlap prevents answers being split across chunk boundaries
