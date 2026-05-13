# RAG Document Q&A

Upload PDF documents and ask questions about them using Retrieval-Augmented Generation. Built with FastAPI, ChromaDB, OpenAI embeddings, and React.

## Architecture

```text
React UI (Vite)        FastAPI Backend           OpenAI              ChromaDB
     │                       │                      │                     │
     │  POST /documents/upload│                      │                     │
     │ ─────────────────────► │  text-embedding-     │                     │
     │                        │  3-small (chunks)    │                     │
     │                        │ ───────────────────► │                     │
     │                        │  embeddings[]        │                     │
     │                        │ ◄─────────────────── │                     │
     │                        │  store vectors + metadata                  │
     │                        │ ──────────────────────────────────────────►│
     │                        │                      │                     │
     │  POST /query            │                      │                     │
     │ ─────────────────────► │  embed question      │                     │
     │                        │ ───────────────────► │                     │
     │                        │  cosine similarity search                  │
     │                        │ ──────────────────────────────────────────►│
     │                        │  top-5 chunks        │                     │
     │                        │ ◄──────────────────────────────────────────│
     │                        │  GPT-4o answer from context                │
     │                        │ ───────────────────► │                     │
     │  {answer, sources}      │                      │                     │
     │ ◄───────────────────── │                      │                     │
```

PDFs are parsed, split into 1000-character chunks with 200-character overlap, embedded via `text-embedding-3-small`, and stored in ChromaDB. Queries embed the question, retrieve the top 5 most similar chunks by cosine similarity, and pass them as context to GPT-4o.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Vector DB | ChromaDB (persistent, Docker named volume) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Generation | OpenAI GPT-4o |
| PDF Parsing | pypdf |
| Frontend | React 19, Vite, Axios |
| Infrastructure | Docker, Docker Compose |

## Project Structure

```text
rag-doc-qa/
├── rag-api/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, middleware, routes
│   │   ├── models.py                    # Pydantic request/response models
│   │   ├── config.py                    # Model names, chunk settings, ChromaDB path
│   │   └── services/
│   │       ├── document_service.py      # PDF parsing and text chunking
│   │       ├── embedding_service.py     # OpenAI embeddings
│   │       ├── vector_store_service.py  # ChromaDB CRUD and similarity search
│   │       └── rag_service.py           # Retrieval + GPT-4o generation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── rag-ui/
    └── src/
        └── App.jsx                      # Upload, document list, Q&A, sources UI
```

## Running Locally

**Prerequisites:** Docker, Node.js, OpenAI API key

**Backend:**

```bash
cd rag-api
cp .env.example .env        # paste your OPENAI_API_KEY
docker compose up --build
```

**Frontend:**

```bash
cd rag-ui
npm install
npm run dev
```

| Service | URL |
| --- | --- |
| API | <http://localhost:8000> |
| Interactive API docs | <http://localhost:8000/docs> |
| UI | <http://localhost:5173> |

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/documents/upload` | Upload a PDF — parse, chunk, embed, store |
| `GET` | `/documents` | List all uploaded documents |
| `DELETE` | `/documents/{doc_id}` | Delete a document and all its chunks |
| `POST` | `/query` | Ask a question, receive an answer with sources |

**POST /query — request:**

```json
{
  "question": "What are the key findings?",
  "doc_id": "optional-uuid-to-scope-to-one-document"
}
```

**POST /query — response:**

```json
{
  "answer": "The key findings are...",
  "sources": [
    {
      "text": "...relevant excerpt...",
      "doc_id": "abc-123",
      "filename": "report.pdf",
      "chunk_index": 4
    }
  ]
}
```

## What This Demonstrates

- **RAG pipeline** — full retrieve-then-generate architecture built from scratch
- **Vector embeddings** — OpenAI `text-embedding-3-small`, stored and queried via cosine similarity
- **ChromaDB** — persistent vector database with metadata filtering per document
- **PDF processing** — text extraction and fixed-size chunking with overlap
- **Multi-document support** — query across all documents or scope to one
- **FastAPI** — async file upload, service layer architecture, Pydantic models
- **Docker** — named volumes for ChromaDB persistence across container restarts
