"""Stateless helpers for the admin web app."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
from PIL import ImageOps

from .constants import FORMAT_BY_EXT
from .constants import LOSSY_QUALITY
from .constants import MAX_SHORT_SIDE


def compress_image(data: bytes, ext: str) -> bytes:
    """Downscale so the shorter side is ≤ MAX_SHORT_SIDE (no upscaling) and re-encode.

    Format is preserved from the extension; lossy formats are re-saved at LOSSY_QUALITY.
    Raises ValueError/OSError if the bytes aren't a decodable image.
    """
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)  # bake in orientation before resizing
        width, height = img.size
        short = min(width, height)
        if short > MAX_SHORT_SIDE:
            scale = MAX_SHORT_SIDE / short
            img = img.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.LANCZOS,
            )

        buf = BytesIO()
        fmt = FORMAT_BY_EXT[ext]
        if fmt == "JPEG":
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")  # JPEG has no alpha
            img.save(buf, "JPEG", quality=LOSSY_QUALITY, optimize=True, progressive=True)
        elif fmt == "WEBP":
            img.save(buf, "WEBP", quality=LOSSY_QUALITY, method=6)
        elif fmt == "PNG":
            img.save(buf, "PNG", optimize=True)
        else:  # GIF — saves the current (first) frame
            img.save(buf, "GIF")
        return buf.getvalue()
