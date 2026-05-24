import os
import logging
from openai import OpenAI, OpenAIError

from config import CHAT_MODEL
from services.embedding_service import embed_query
from services.vector_store_service import query_chunks
from services.web_search_service import search as web_search

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def answer_question(
    question: str,
    doc_id: str | None = None,
    use_web_search: bool = False,
) -> tuple[str, list[dict], bool]:
    """Retrieve relevant chunks (documents + optional web) and answer using GPT-4o.

    Args:
        question:        The user's natural-language question.
        doc_id:          If provided, restricts document retrieval to a single doc.
        use_web_search:  If True, also fetch top web results via Tavily and include them as context.

    Returns:
        ``(answer, sources, web_search_used)`` where ``sources`` is the combined list of
        document chunks and web result entries (each shaped as a chunk-like dict).
    """
    query_embedding = embed_query(question)
    doc_chunks = query_chunks(query_embedding, doc_id=doc_id)

    web_chunks: list[dict] = []
    web_used = False
    if use_web_search:
        web_results = web_search(question)
        web_used = bool(web_results)
        for i, r in enumerate(web_results):
            web_chunks.append({
                "text": r["content"],
                "metadata": {
                    "doc_id": "web",
                    "filename": r["title"] or r["url"] or "web result",
                    "chunk_index": i,
                    "source_type": "web",
                    "url": r["url"],
                },
            })

    all_chunks = doc_chunks + web_chunks
    if not all_chunks:
        msg = (
            "No relevant content found in the uploaded documents."
            if not use_web_search
            else "No relevant content found in documents or on the web."
        )
        return msg, [], web_used

    context_parts = []
    for i, chunk in enumerate(doc_chunks):
        context_parts.append(f"[Document Chunk {i + 1}]\n{chunk['text']}")
    for i, chunk in enumerate(web_chunks):
        meta = chunk["metadata"]
        context_parts.append(
            f"[Web Result {i + 1} — {meta['filename']} ({meta.get('url', '')})]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    instruction = (
        "You are a helpful assistant. Answer the question using the provided context. "
        "When the context contains both document chunks and web results, prefer document "
        "chunks but use web results to fill gaps. Cite web sources by URL when used. "
        "If the answer is not in the context, say so clearly."
        if use_web_search
        else "You are a helpful assistant that answers questions based strictly on the provided document context. "
        "If the answer is not found in the context, say so clearly."
    )

    prompt = f"""{instruction}

Context:
{context}

Question: {question}

Answer:"""

    try:
        response = _get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise

    return response.choices[0].message.content, all_chunks, web_used
