# rag-ui

React frontend for the [RAG Document Q&A](../README.md) project. Provides a PDF upload interface, document list, and a question-answer panel that shows retrieved source chunks alongside the answer.

## Relationship to Other Services

| Service | Direction | Description |
| --- | --- | --- |
| `rag-api` | → calls | Uploads PDFs, fetches document list, sends questions, receives answers + sources |

## Service Structure

```text
src/
├── main.jsx     # React entry point
├── index.css    # Global styles
└── App.jsx      # Upload panel, document list, Q&A form, source display
```

## Starting This Service

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173` — requires `rag-api` running on port 8000.

## API Calls Made

| Method | Endpoint | When |
| --- | --- | --- |
| `POST` | `/documents/upload` | User selects and uploads a PDF |
| `GET` | `/documents` | On mount and after every upload/delete |
| `DELETE` | `/documents/{doc_id}` | User clicks delete on a document |
| `POST` | `/query` | User submits a question |

## Logic — Pseudocode

```text
ON mount:
    documents = GET /documents

ON file selected:
    SET selectedFile = file

ON upload clicked:
    POST /documents/upload (FormData with file)
    documents = GET /documents   // refresh list

ON delete clicked (doc_id):
    DELETE /documents/{doc_id}
    documents = GET /documents   // refresh list

ON question submitted:
    SET loading = true
    { answer, sources } = POST /query { question, doc_id? }
    SET loading = false
    RENDER answer + source chunk cards
```

## Design Notes

- **Axios** — all API calls use Axios with async/await
- **Source cards** — each retrieved chunk is rendered with its filename and chunk index so users can verify context
- **Optional scoping** — users can optionally select a document to restrict the query to that PDF only
