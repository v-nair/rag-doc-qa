import chromadb
import logging
import threading

from config import CHROMA_PATH, COLLECTION_NAME, TOP_K_RESULTS

logger = logging.getLogger(__name__)

_client = None
_collection = None
_lock = threading.Lock()


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:
            _client = chromadb.PersistentClient(path=CHROMA_PATH)
            _collection = _client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
    return _collection


def add_chunks(
    doc_id: str,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]]
) -> None:
    collection = _get_collection()
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )


def query_chunks(
    query_embedding: list[float],
    doc_id: str | None = None
) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    where = {"doc_id": doc_id} if doc_id else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K_RESULTS,
        where=where,
        include=["documents", "metadatas", "distances"]
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })
    return chunks


def list_documents() -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    result = collection.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for metadata in result["metadatas"]:
        doc_id = metadata["doc_id"]
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "filename": metadata["filename"],
                "chunk_count": 0
            }
        docs[doc_id]["chunk_count"] += 1
    return list(docs.values())


def delete_document(doc_id: str) -> int:
    collection = _get_collection()
    result = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas"]
    )
    ids_to_delete = result["ids"]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)
