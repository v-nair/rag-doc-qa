import io
import uuid
from pypdf import PdfReader

from config import CHUNK_SIZE, CHUNK_OVERLAP


def parse_and_chunk(file_bytes: bytes) -> tuple[str, list[str]]:
    doc_id = str(uuid.uuid4())
    text = _extract_text(file_bytes)
    chunks = _split_text(text)
    return doc_id, chunks


def _extract_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages.append(extracted)
    return "\n".join(pages)


def _split_text(text: str) -> list[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks
