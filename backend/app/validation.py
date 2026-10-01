"""Input validation and bounded I/O.

Three rules hold everywhere in this module:

1. Nothing is trusted because a client said so. An upload's declared MIME type
   is checked against its actual magic bytes, and the declared filename is
   checked against both.
2. Every read is bounded. A declared ``Content-Length`` is rejected before any
   byte is read, and the body is read in chunks with an early abort, so an
   oversized or lying upload cannot exhaust memory.
3. Failures raise :class:`~backend.app.errors.AppError` subclasses, so they
   render identically on both the v1 and the legacy routes.
"""
from __future__ import annotations

import os

from backend.app.config import SETTINGS
from backend.app.errors import (
    InvalidUrl, MissingInput, PayloadTooLarge, UnsupportedMediaType, UnreadableImage,
    ValidationFailed,
)
from ml.features_module_b import hostname as parsed_hostname
from ml.features_module_b import is_ip as parsed_is_ip
from ml.features_module_b import parse_url

#: Declared MIME type -> (allowed extensions, required magic-byte prefix).
IMAGE_SIGNATURES: dict[str, tuple[frozenset[str], bytes]] = {
    'image/png': (frozenset({'.png'}), b'\x89PNG\r\n\x1a\n'),
    'image/jpeg': (frozenset({'.jpg', '.jpeg', '.jpe'}), b'\xff\xd8\xff'),
    'image/webp': (frozenset({'.webp'}), b'RIFF'),
    'image/bmp': (frozenset({'.bmp', '.dib'}), b'BM'),
}

#: How much of the body is inspected for a magic-byte signature.
_SIGNATURE_WINDOW = 32

#: Read granularity for bounded upload reads.
_CHUNK_BYTES = 64 * 1024

GENERIC_URL_MESSAGE = (
    'Invalid URL. Expected an HTTP(S) address such as https://example.com/login.'
)


def normalize_url(raw: str | None) -> str:
    """Validate a URL without touching the network.

    Schemeless input is accepted (Module B's parser adds HTTP for analysis);
    everything else that a browser would not navigate to is refused with 422.
    """
    candidate = (raw or '').strip()
    if not candidate:
        raise MissingInput('url must be a non-empty string.')
    if len(candidate) > SETTINGS.max_url_chars:
        raise InvalidUrl(
            f'url exceeds the {SETTINGS.max_url_chars}-character limit.',
            details={'max_chars': SETTINGS.max_url_chars},
        )
    try:
        if len(candidate) > 8192 or any(ch.isspace() or ord(ch) < 32 for ch in candidate) or '\\' in candidate:
            raise ValueError('Invalid characters or length')
        parse_url(candidate)
        host = parsed_hostname(candidate)
        if not host or ('.' not in host and host != 'localhost' and not parsed_is_ip(host)):
            raise ValueError('Invalid host')
    except (ValueError, UnicodeError):
        raise InvalidUrl(GENERIC_URL_MESSAGE) from None
    return candidate


def normalize_message(raw: str | None) -> str:
    """Trim and bound submitted message text."""
    text = (raw or '').strip()
    if not text:
        raise MissingInput('Message text must not be empty.')
    if len(text) > SETTINGS.max_text_chars:
        raise ValidationFailed(
            f'Message exceeds the {SETTINGS.max_text_chars}-character limit.',
            module='module_c',
            details={'max_chars': SETTINGS.max_text_chars},
        )
    return text


def _extension_of(filename: str | None) -> str:
    if not filename:
        return ''
    return os.path.splitext(filename)[1].lower()


def detect_image_type(content: bytes) -> str | None:
    """Identify an image by magic bytes only. `None` when unrecognised."""
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if content.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'image/webp'
    if content[:2] == b'BM':
        return 'image/bmp'
    return None


def validate_image_upload(content: bytes, *, declared_type: str | None,
                          filename: str | None) -> str:
    """Verify an upload's declared type, filename extension and real bytes.

    Returns the verified MIME type.

    Raises 415 when the client declared a type we do not accept, and 400 when a
    type is declared but the bytes disagree — a client sending a mislabelled or
    truncated file deserves a different fix than one sending an unsupported type.
    """
    declared = (declared_type or '').split(';')[0].strip().lower()
    if declared not in IMAGE_SIGNATURES:
        raise UnsupportedMediaType(
            'Unsupported image type. Upload a PNG, JPEG, WebP or BMP chat screenshot.',
            details={'allowed': sorted(IMAGE_SIGNATURES)},
        )

    if len(content) < _SIGNATURE_WINDOW and not detect_image_type(content):
        raise UnreadableImage('Uploaded image file is empty or truncated.')

    actual = detect_image_type(content[:_SIGNATURE_WINDOW])
    if actual is None:
        raise UnreadableImage(
            'Uploaded file is not a readable PNG, JPEG, WebP or BMP image. '
            'The declared content type does not match the file contents.'
        )
    if actual != declared:
        raise UnreadableImage(
            'Uploaded file contents do not match the declared content type. '
            'Upload a PNG, JPEG, WebP or BMP chat screenshot.',
            details={'declared': declared},
        )

    allowed_extensions, _ = IMAGE_SIGNATURES[declared]
    extension = _extension_of(filename)
    # An absent filename is fine (a mobile client may send a blob); a present
    # one that contradicts the bytes is not.
    if extension and extension not in allowed_extensions:
        raise UnreadableImage(
            'The file extension does not match the file contents.',
            details={'declared': declared},
        )
    return actual


async def read_upload_bounded(upload, *, max_bytes: int | None = None) -> bytes:
    """Read at most `max_bytes` from an upload, aborting early.

    ``upload`` is a Starlette ``UploadFile`` whose async ``read()`` is used in
    chunks, so a lying or unbounded body cannot force an unbounded allocation
    on our side. Starlette accumulates ``upload.size`` as the multipart body is
    parsed, so an already-oversized part is rejected before a single chunk is
    copied; the loop below still caps what a slow-drip body can make us hold.
    (The coarser whole-request ceiling lives in
    :class:`backend.app.middleware.RequestSizeMiddleware`.)
    """
    limit = max_bytes or SETTINGS.max_image_bytes
    received = getattr(upload, 'size', None)
    if received is not None and received > limit:
        raise PayloadTooLarge(
            f'Uploaded image exceeds the {limit // (1024 * 1024)} MB size limit.',
            details={'max_bytes': limit},
        )

    buffer = bytearray()
    while True:
        chunk = await upload.read(_CHUNK_BYTES)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise PayloadTooLarge(
                f'Uploaded image exceeds the {limit // (1024 * 1024)} MB size limit.',
                details={'max_bytes': limit},
            )
    return bytes(buffer)