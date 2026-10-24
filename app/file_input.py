"""Turn an uploaded chart screenshot or results PDF into a Messages API content block."""

import base64

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
SUPPORTED_DOCUMENT_TYPES = {"application/pdf"}


class UnsupportedFileTypeError(Exception):
    pass


def build_content_block(data: bytes, media_type: str) -> dict:
    """Base64-encode the file and wrap it in the shape Claude expects.
    Images -> {"type": "image", ...}; PDFs -> {"type": "document", ...}."""
    encoded = base64.standard_b64encode(data).decode("utf-8")

    if media_type in SUPPORTED_IMAGE_TYPES:
        block_type = "image"
    elif media_type in SUPPORTED_DOCUMENT_TYPES:
        block_type = "document"
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type {media_type!r}; expected an image "
            f"({sorted(SUPPORTED_IMAGE_TYPES)}) or a PDF."
        )

    return {
        "type": block_type,
        "source": {"type": "base64", "media_type": media_type, "data": encoded},
    }
