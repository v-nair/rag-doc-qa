# RAG Document Q&A

Upload **PDF, DOCX, XLSX, CSV, PNG, or JPEG** files and ask questions about them using Retrieval-Augmented Generation. Embedded and standalone images are described with **GPT-4o vision**, and answers can optionally pull in **live web search results** via Tavily. Built with FastAPI, ChromaDB, OpenAI, and React.

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

Files are parsed by extension (PDF → pymupdf, DOCX → python-docx, XLSX → openpyxl, CSV → stdlib, PNG/JPEG → vision). Embedded images inside PDFs and DOCX files plus any standalone uploaded image are sent to GPT-4o vision and the returned descriptions are inlined as text. Everything is then split into 1000-character chunks with 200-character overlap, embedded via `text-embedding-3-small`, and stored in ChromaDB.

Queries embed the question and retrieve the top 5 most similar chunks by cosine similarity. When the **"Include web search"** toggle is on, the question is also sent to Tavily and its top results are merged into the LLM context, clearly labelled.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Vector DB | ChromaDB (persistent, Docker named volume) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Generation | OpenAI GPT-4o |
| Vision | OpenAI GPT-4o (multimodal) |
| PDF Parsing | PyMuPDF (`fitz`) |
| DOCX Parsing | python-docx + zipfile |
| Excel/CSV | openpyxl, stdlib `csv` |
| Image Handling | Pillow |
| Web Search | Tavily |
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
cp .env.example .env        # paste your OPENAI_API_KEY (required)
                            # and TAVILY_API_KEY (optional, enables web search)
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
| `GET` | `/` | Health + advertised supported uploads + web-search availability |
| `POST` | `/documents/upload` | Upload PDF/DOCX/XLSX/CSV/PNG/JPEG — parse, chunk, embed, store |
| `GET` | `/documents` | List all uploaded documents |
| `DELETE` | `/documents/{doc_id}` | Delete a document and all its chunks |
| `POST` | `/query` | Ask a question, optionally with web search, receive answer + sources |

**POST /query — request:**

```json
{
  "question": "What are the key findings?",
  "doc_id": "optional-uuid-to-scope-to-one-document",
  "use_web_search": false
}
```

**POST /query — response:**

```json
{
  "answer": "The key findings are...",
  "web_search_used": true,
  "sources": [
    {
      "text": "...relevant excerpt...",
      "doc_id": "abc-123",
      "filename": "report.pdf",
      "chunk_index": 4,
      "source_type": "document",
      "url": null
    },
    {
      "text": "...web snippet...",
      "doc_id": "web",
      "filename": "Page Title",
      "chunk_index": 0,
      "source_type": "web",
      "url": "https://example.com/article"
    }
  ]
}
```

## Logic — Pseudocode

```text
// ── UPLOAD ──────────────────────────────────────────────────
FUNCTION upload_document(pdf_bytes, filename):

    text = extract_text_from_pdf(pdf_bytes)

    chunks = []
    FOR i in range(0, len(text), CHUNK_SIZE - OVERLAP):
        chunks.APPEND(text[i : i + CHUNK_SIZE])

    embeddings = OpenAI.embed(chunks)          // text-embedding-3-small

    ChromaDB.store(
        ids        = [doc_id + "_chunk_0", "_chunk_1", ...],
        embeddings = embeddings,
        documents  = chunks,
        metadata   = [{ filename, doc_id, chunk_index }, ...]
    )

    RETURN doc_id


// ── QUERY ────────────────────────────────────────────────────
FUNCTION query(question, doc_id=None):

    question_embedding = OpenAI.embed(question)

    top_chunks = ChromaDB.similarity_search(
        query_embedding = question_embedding,
        n_results       = 5,
        where           = { doc_id } IF doc_id ELSE None    // optional filter
    )

    context = JOIN(top_chunks, separator="\n\n")
    prompt  = "Answer using only this context:\n{context}\n\nQuestion: {question}"

    answer = OpenAI GPT-4o.complete(prompt)

    RETURN { answer, sources: top_chunks }
```

## What This Demonstrates

- **RAG pipeline** — full retrieve-then-generate architecture built from scratch
- **Vector embeddings** — OpenAI `text-embedding-3-small`, stored and queried via cosine similarity
- **ChromaDB** — persistent vector database with metadata filtering per document
- **Multi-format ingestion** — PDF, DOCX, XLSX, CSV, PNG, JPEG all funnel into one chunk pipeline
- **Multimodal extraction** — embedded images inside PDFs/DOCX and standalone images are described via GPT-4o vision and made searchable as text
- **Hybrid retrieval** — optional Tavily web search merged with vector results, with web sources visibly labelled in the UI
- **Multi-document support** — query across all documents or scope to one
- **FastAPI** — async file upload, service layer architecture, Pydantic models
- **Docker** — named volumes for ChromaDB persistence across container restarts
