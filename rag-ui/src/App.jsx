import { useState, useEffect, useRef } from "react"
import axios from "axios"

const API_URL = "http://localhost:8000"

const styles = {
  card: {
    background: "#fff",
    border: "1px solid #e5e5e5",
    borderRadius: 8,
    padding: "20px 24px",
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: 600,
    marginBottom: 14,
    color: "#111",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  docRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 14px",
    borderRadius: 6,
    border: "1px solid",
    cursor: "pointer",
    transition: "background 0.1s",
  },
  deleteBtn: {
    padding: "4px 10px",
    borderRadius: 4,
    border: "1px solid #e00",
    background: "#fff",
    color: "#e00",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
    flexShrink: 0,
  },
  errorText: {
    color: "#e00",
    fontSize: 13,
    marginTop: 8,
    margin: "8px 0 0",
  },
}

const SUPPORTED_ACCEPT = ".pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg"

export default function App() {
  const [documents, setDocuments] = useState([])
  const [selectedDocId, setSelectedDocId] = useState(null)
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [sources, setSources] = useState([])
  const [webSearchUsed, setWebSearchUsed] = useState(false)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [webSearchAvailable, setWebSearchAvailable] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [queryError, setQueryError] = useState("")
  const fileInputRef = useRef(null)

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API_URL}/documents`)
      setDocuments(res.data)
    } catch {
      // silent — API may not be running yet
    }
  }

  useEffect(() => {
    axios.get(`${API_URL}/documents`)
      .then(res => setDocuments(res.data))
      .catch(() => {})
    axios.get(`${API_URL}/`)
      .then(res => setWebSearchAvailable(Boolean(res.data?.web_search_enabled)))
      .catch(() => {})
  }, [])

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadError("")
    setUploading(true)
    const formData = new FormData()
    formData.append("file", file)
    try {
      await axios.post(`${API_URL}/documents/upload`, formData)
      await fetchDocuments()
    } catch (err) {
      setUploadError(err.response?.data?.detail || "Upload failed.")
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleDelete = async (docId) => {
    try {
      await axios.delete(`${API_URL}/documents/${docId}`)
      if (selectedDocId === docId) setSelectedDocId(null)
      setAnswer("")
      setSources([])
      await fetchDocuments()
    } catch {
      // silent
    }
  }

  const handleQuery = async () => {
    if (!question.trim() || loading) return
    setLoading(true)
    setAnswer("")
    setSources([])
    setWebSearchUsed(false)
    setQueryError("")
    try {
      const res = await axios.post(`${API_URL}/query`, {
        question: question.trim(),
        doc_id: selectedDocId,
        use_web_search: useWebSearch,
      })
      setAnswer(res.data.answer)
      setSources(res.data.sources)
      setWebSearchUsed(Boolean(res.data.web_search_used))
    } catch (err) {
      setQueryError(err.response?.data?.detail || "Query failed.")
    } finally {
      setLoading(false)
    }
  }

  const selectedDoc = documents.find((d) => d.doc_id === selectedDocId)
  const hasDocuments = documents.length > 0
  const canAsk = !loading && question.trim().length > 0 && (hasDocuments || useWebSearch)

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", padding: "0 20px" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24, color: "#111" }}>
        RAG Document Q&amp;A
      </h1>

      {/* Upload */}
      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Upload Document</h2>
        <label
          style={{
            display: "inline-block",
            padding: "9px 18px",
            background: uploading ? "#ccc" : "#0070f3",
            color: "#fff",
            borderRadius: 6,
            cursor: uploading ? "not-allowed" : "pointer",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          {uploading ? "Uploading..." : "+ Upload Document"}
          <input
            ref={fileInputRef}
            type="file"
            accept={SUPPORTED_ACCEPT}
            style={{ display: "none" }}
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
        <div style={{ fontSize: 12, color: "#666", marginTop: 10 }}>
          PDF, DOCX, XLSX, CSV, PNG, JPG · images and PDF embedded images are described via GPT-4o vision
        </div>
        {uploadError && <p style={styles.errorText}>{uploadError}</p>}
      </section>

      {/* Document list */}
      {hasDocuments && (
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Documents</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div
              onClick={() => setSelectedDocId(null)}
              style={{
                ...styles.docRow,
                borderColor: selectedDocId === null ? "#0070f3" : "#e5e5e5",
                background: selectedDocId === null ? "#f0f7ff" : "#fafafa",
              }}
            >
              <div>
                <div style={{ fontWeight: 500, fontSize: 14 }}>All Documents</div>
                <div style={{ color: "#888", fontSize: 12 }}>
                  {documents.length} document{documents.length !== 1 ? "s" : ""}
                </div>
              </div>
            </div>

            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                onClick={() => setSelectedDocId(doc.doc_id)}
                style={{
                  ...styles.docRow,
                  borderColor: selectedDocId === doc.doc_id ? "#0070f3" : "#e5e5e5",
                  background: selectedDocId === doc.doc_id ? "#f0f7ff" : "#fff",
                }}
              >
                <div style={{ minWidth: 0, marginRight: 12 }}>
                  <div
                    style={{
                      fontWeight: 500,
                      fontSize: 14,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {doc.filename}
                  </div>
                  <div style={{ color: "#888", fontSize: 12 }}>{doc.chunk_count} chunks</div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(doc.doc_id)
                  }}
                  style={styles.deleteBtn}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Query */}
      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>
          Ask a Question
          {selectedDoc && (
            <span style={{ fontSize: 13, fontWeight: 400, color: "#0070f3" }}>
              — {selectedDoc.filename}
            </span>
          )}
        </h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            placeholder={
              hasDocuments || useWebSearch
                ? "Ask something..."
                : "Upload a document or enable web search..."
            }
            disabled={loading || (!hasDocuments && !useWebSearch)}
            style={{
              flex: 1,
              padding: "10px 14px",
              borderRadius: 6,
              border: "1px solid #e5e5e5",
              fontSize: 14,
              outline: "none",
              background: (!hasDocuments && !useWebSearch) ? "#fafafa" : "#fff",
            }}
          />
          <button
            onClick={handleQuery}
            disabled={!canAsk}
            style={{
              padding: "10px 20px",
              background: canAsk ? "#0070f3" : "#ccc",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: canAsk ? "pointer" : "not-allowed",
              fontSize: 14,
              fontWeight: 500,
              whiteSpace: "nowrap",
            }}
          >
            {loading ? "Searching..." : "Ask"}
          </button>
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 12,
            fontSize: 13,
            color: webSearchAvailable ? "#222" : "#999",
            cursor: webSearchAvailable ? "pointer" : "not-allowed",
          }}
        >
          <input
            type="checkbox"
            checked={useWebSearch}
            disabled={!webSearchAvailable}
            onChange={(e) => setUseWebSearch(e.target.checked)}
          />
          Include web search results
          {!webSearchAvailable && (
            <span style={{ fontSize: 12, color: "#999" }}>
              (set TAVILY_API_KEY in .env to enable)
            </span>
          )}
        </label>
        {queryError && <p style={styles.errorText}>{queryError}</p>}
      </section>

      {/* Answer */}
      {answer && (
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Answer</h2>
          <p style={{ lineHeight: 1.75, fontSize: 15, color: "#222", margin: 0 }}>{answer}</p>
        </section>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>
            Sources
            {webSearchUsed && (
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  color: "#0a7d2a",
                  background: "#e6f7ec",
                  padding: "2px 8px",
                  borderRadius: 10,
                }}
              >
                web search active
              </span>
            )}
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {sources.map((src, i) => {
              const isWeb = src.source_type === "web"
              return (
                <div
                  key={i}
                  style={{
                    background: isWeb ? "#f0f9ff" : "#f9f9f9",
                    border: "1px solid",
                    borderColor: isWeb ? "#cfe6f7" : "#e5e5e5",
                    borderRadius: 6,
                    padding: "10px 14px",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color: "#666",
                      marginBottom: 6,
                      fontWeight: 500,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: 0.4,
                        color: "#fff",
                        background: isWeb ? "#0070f3" : "#777",
                        padding: "2px 6px",
                        borderRadius: 3,
                      }}
                    >
                      {isWeb ? "Web" : "Doc"}
                    </span>
                    {isWeb && src.url ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#0070f3", textDecoration: "none" }}
                      >
                        {src.filename}
                      </a>
                    ) : (
                      <span>
                        {src.filename} · chunk {src.chunk_index + 1}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: "#333", lineHeight: 1.6 }}>{src.text}</div>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
