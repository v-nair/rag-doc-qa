import os
import logging
from openai import OpenAI, OpenAIError

from config import CHAT_MODEL
from services.embedding_service import embed_query
from services.vector_store_service import query_chunks

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def answer_question(question: str, doc_id: str | None = None) -> tuple[str, list[dict]]:
    query_embedding = embed_query(question)
    retrieved_chunks = query_chunks(query_embedding, doc_id=doc_id)

    if not retrieved_chunks:
        return "No relevant content found in the uploaded documents.", []

    context = "\n\n---\n\n".join(
        [f"[Chunk {i + 1}]\n{chunk['text']}" for i, chunk in enumerate(retrieved_chunks)]
    )

    prompt = f"""You are a helpful assistant that answers questions based strictly on the provided document context.
If the answer is not found in the context, say so clearly.

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

    return response.choices[0].message.content, retrieved_chunks
