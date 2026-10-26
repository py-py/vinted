from __future__ import annotations

import io

import pillow_heif
import pytest
from PIL import Image

from ..photos import MAX_BYTES
from ..photos import MAX_SIDE
from ..photos import InvalidPhoto
from ..photos import process

ORIENTATION = 0x0112
GPS_IFD = 0x8825


def _encode(img: Image.Image, fmt: str, **kwargs: object) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def _open(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    return img


###############################################################################
#  Resize — Longer Side Capped at MAX_SIDE, Never Upscaled
###############################################################################


def test_shrinks_longer_side_keeping_aspect_ratio() -> None:
    data, w, h = process(_encode(Image.new("RGB", (4000, 3000)), "JPEG"))
    assert (w, h) == (MAX_SIDE, 900)
    assert _open(data).size == (w, h)


def test_shrinks_portrait() -> None:
    _, w, h = process(_encode(Image.new("RGB", (1000, 3200)), "PNG"))
    assert (w, h) == (375, MAX_SIDE)


def test_does_not_upscale() -> None:
    _, w, h = process(_encode(Image.new("RGB", (800, 600)), "WEBP"))
    assert (w, h) == (800, 600)


def test_converts_transparent_png_to_rgb_jpeg() -> None:
    data, _, _ = process(_encode(Image.new("RGBA", (10, 10), (255, 0, 0, 0)), "PNG"))
    assert _open(data).mode == "RGB"


###############################################################################
#  EXIF — Rotation Applied, Metadata Stripped
###############################################################################


def test_applies_exif_rotation() -> None:
    exif = Image.Exif()
    exif[ORIENTATION] = 6  # rotate 90° CW on display
    _, w, h = process(_encode(Image.new("RGB", (400, 200)), "JPEG", exif=exif))
    assert (w, h) == (200, 400)


def test_strips_exif_including_gps() -> None:
    exif = Image.Exif()
    exif[ORIENTATION] = 1
    exif.get_ifd(GPS_IFD)[2] = (52.0, 13.0, 0.0)  # GPSLatitude
    data, _, _ = process(_encode(Image.new("RGB", (100, 100)), "JPEG", exif=exif))
    img = _open(data)
    assert not img.getexif()
    assert "exif" not in img.info


###############################################################################
#  Formats — HEIC Accepted, Non-Images and Oversized Files Rejected
###############################################################################


def test_accepts_mpo_from_iphone() -> None:
    main = Image.new("RGB", (4032, 3024), (200, 0, 0))
    depth = Image.new("RGB", (576, 432), (0, 0, 0))
    data = _encode(main, "MPO", save_all=True, append_images=[depth])
    assert Image.open(io.BytesIO(data)).format == "MPO"
    jpeg, w, h = process(data)
    assert (w, h) == (MAX_SIDE, 900)
    assert _open(jpeg).getpixel((10, 10))[0] > 150  # the main frame, not the depth map


def test_accepts_heic() -> None:
    heif = pillow_heif.from_pillow(Image.new("RGB", (2400, 1600), (0, 128, 255)))
    buf = io.BytesIO()
    heif.save(buf, quality=50)
    data, w, h = process(buf.getvalue())
    assert (w, h) == (MAX_SIDE, 800)
    assert _open(data).size == (w, h)


@pytest.mark.parametrize("data", [b"", b"not an image", b"%PDF-1.4\n"])
def test_rejects_non_images(data: bytes) -> None:
    with pytest.raises(InvalidPhoto):
        process(data)


def test_rejects_unsupported_format() -> None:
    with pytest.raises(InvalidPhoto, match="GIF"):
        process(_encode(Image.new("RGB", (10, 10)), "GIF"))


def test_rejects_truncated_image() -> None:
    data = _encode(Image.effect_noise((500, 500), 64).convert("RGB"), "JPEG")
    with pytest.raises(InvalidPhoto):
        process(data[: len(data) // 2])


def test_rejects_oversized_file() -> None:
    with pytest.raises(InvalidPhoto, match="larger"):
        process(b"\0" * (MAX_BYTES + 1))
