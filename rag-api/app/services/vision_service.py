import base64
import io
import logging
import os
from PIL import Image
from openai import OpenAI, OpenAIError

from config import VISION_MODEL, MIN_IMAGE_SIDE_PX

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

DESCRIBE_PROMPT = (
    "Describe this image in detail for document retrieval. "
    "Capture any text shown, charts, diagrams, tables, people, "
    "or notable objects. Be factual and concise."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def is_image_meaningful(image_bytes: bytes) -> bool:
    """Skip tiny decorative images (icons, logos, separators)."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            w, h = im.size
            return w >= MIN_IMAGE_SIDE_PX and h >= MIN_IMAGE_SIDE_PX
    except Exception as e:
        logger.warning(f"Could not open image for size check: {e}")
        return False


def describe_image(image_bytes: bytes, mime: str = "image/png") -> str | None:
    """Return a natural-language description of an image, or None on failure."""
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = _get_client().chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DESCRIBE_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=400,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.warning(f"Vision API error, skipping image: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error describing image: {e}")
        return None
