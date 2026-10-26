"""
Listing photo processing: any supported upload -> EXIF-free JPEG, at most 1200 px on the
longer side.

EXIF orientation is applied to the pixels first, then all metadata is dropped, so GPS
coordinates from phone photos never reach storage.
"""

from __future__ import annotations

import io

from PIL import Image
from PIL import ImageOps
from PIL import UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

# Plenty for Vinted, and keeps the photos sent to the LLM small.
MAX_SIDE = 1200
MAX_BYTES = 25 * 1024 * 1024
JPEG_QUALITY = 85
# Decompression-bomb guard: ~100 MP covers any phone camera (a 200 MP sensor bins to 50 MP).
Image.MAX_IMAGE_PIXELS = 100_000_000

# Checked on the decoded file, not the upload's Content-Type: browsers often send HEIC as
# application/octet-stream.
# MPO: iPhone JPEGs with extra embedded frames (depth, HDR gain map); Pillow reads the main one.
ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "HEIF"}


class InvalidPhoto(ValueError):
    """Upload is not a supported image, or is too large."""


def process(data: bytes) -> tuple[bytes, int, int]:
    """Normalize an uploaded image. Returns (jpeg_bytes, width, height)."""
    if len(data) > MAX_BYTES:
        raise InvalidPhoto(f"file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ALLOWED_FORMATS:
            raise InvalidPhoto(f"unsupported image format: {img.format}")
        # Decoding happens lazily, so truncated files and bombs surface here, not in open().
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
        raise InvalidPhoto(str(e)) from e

    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)  # never upscales

    out = io.BytesIO()
    # No exif=/icc_profile= passed, so the saved file carries no metadata.
    img.save(out, "JPEG", quality=JPEG_QUALITY, progressive=True, optimize=True)
    return out.getvalue(), img.width, img.height
