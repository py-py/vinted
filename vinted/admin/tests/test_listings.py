from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from unittest.mock import MagicMock

import pillow_heif
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from ...listing.describe import ListingText
from ...listing.photos import MAX_PHOTOS_PER_LISTING
from .. import app
from .. import listings
from ..deps import get_photo_store
from ..deps import get_store

AUTH = ("admin", "secret")
LISTING_ID = "0b3c1f8e-3a1e-4d4e-9f5a-2f0a8c6c1d11"
PHOTO_A = "6f1d2b0c-1111-4a4a-8b8b-000000000001"
PHOTO_B = "6f1d2b0c-2222-4a4a-8b8b-000000000002"
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def _photo(photo_id: str) -> dict:
    return {
        "id": photo_id,
        "path": f"listing/{LISTING_ID}/{photo_id}.jpeg",
        "width": 1200,
        "height": 900,
        "bytes": 1234,
        "created_at": NOW,
    }


def _listing(photos: list[dict] | None = None) -> dict:
    return {"id": LISTING_ID, "created_at": NOW, "updated_at": NOW, "photos": photos or []}


def _jpeg(size: tuple[int, int] = (3200, 2400)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", AUTH[0])
    monkeypatch.setenv("ADMIN_PASSWORD", AUTH[1])


@pytest.fixture
def store() -> Iterator[MagicMock]:
    store = MagicMock()
    store.get_listing.return_value = _listing([_photo(PHOTO_A), _photo(PHOTO_B)])
    app.dependency_overrides[get_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def photos() -> Iterator[MagicMock]:
    photos = MagicMock()
    photos.upload_listing_photo.side_effect = lambda lid, pid, _: f"listing/{lid}/{pid}.jpeg"
    app.dependency_overrides[get_photo_store] = lambda: photos
    yield photos
    app.dependency_overrides.clear()


@pytest.fixture
def client(store: MagicMock, photos: MagicMock) -> TestClient:
    client = TestClient(app)
    client.auth = AUTH
    return client


###############################################################################
#  Listings — Create, List, Get and Delete
###############################################################################


def test_create_listing(client: TestClient, store: MagicMock) -> None:
    store.create_listing.return_value = _listing()
    resp = client.post("/api/listings")
    assert resp.status_code == 201
    assert resp.json()["id"] == LISTING_ID
    assert resp.json()["photos"] == []


def test_update_listing_strips_and_clears_blank(client: TestClient, store: MagicMock) -> None:
    resp = client.patch(
        f"/api/listings/{LISTING_ID}", json={"title": "  Nike Sunray  ", "description": " "}
    )
    assert resp.status_code == 200
    store.update_listing.assert_called_once_with(
        LISTING_ID, {"title": "Nike Sunray", "description": None}
    )


def test_update_listing_leaves_omitted_fields(client: TestClient, store: MagicMock) -> None:
    client.patch(f"/api/listings/{LISTING_ID}", json={"title": "Nike"})
    store.update_listing.assert_called_once_with(LISTING_ID, {"title": "Nike"})


def test_update_listing_returns_saved_fields(client: TestClient, store: MagicMock) -> None:
    store.get_listing.return_value = {**_listing(), "title": "Nike", "description": "Size 27"}
    body = client.patch(f"/api/listings/{LISTING_ID}", json={}).json()
    assert (body["title"], body["description"]) == ("Nike", "Size 27")
    store.update_listing.assert_not_called()


def test_update_missing_listing_is_404(client: TestClient, store: MagicMock) -> None:
    store.get_listing.return_value = None
    assert client.patch(f"/api/listings/{LISTING_ID}", json={"title": "x"}).status_code == 404
    store.update_listing.assert_not_called()


###############################################################################
#  Describe — Title and Description Suggested From the Photos
###############################################################################


def test_describe_sends_stored_photos_in_order(
    client: TestClient, photos: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    photos.download_listing_photo.side_effect = lambda _, pid: {PHOTO_A: b"a"}.get(pid)
    calls = []

    def fake_describe(data: list[bytes]) -> ListingText:
        calls.append(data)
        return ListingText(title="Nike", description="Size 27")

    monkeypatch.setattr(listings, "describe", fake_describe)
    resp = client.post(f"/api/listings/{LISTING_ID}/describe")
    assert resp.status_code == 200
    assert resp.json() == {"title": "Nike", "description": "Size 27"}
    # PHOTO_B is missing from GCS and is skipped.
    assert calls == [[b"a"]]


def test_describe_without_photos_is_409(client: TestClient, store: MagicMock) -> None:
    store.get_listing.return_value = _listing()
    assert client.post(f"/api/listings/{LISTING_ID}/describe").status_code == 409


def test_describe_llm_failure_is_502(
    client: TestClient, photos: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    photos.download_listing_photo.return_value = b"a"

    def broken(_: list[bytes]) -> ListingText:
        raise RuntimeError("DeepSeek is down")

    monkeypatch.setattr(listings, "describe", broken)
    assert client.post(f"/api/listings/{LISTING_ID}/describe").status_code == 502


def test_analyze_saves_title_and_description(
    client: TestClient, store: MagicMock, photos: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    photos.download_listing_photo.return_value = b"a"
    monkeypatch.setattr(
        listings, "describe", lambda _: ListingText(title="Nike", description="Size 27")
    )
    resp = client.post(f"/api/listings/{LISTING_ID}/analyze")
    assert resp.status_code == 200
    store.update_listing.assert_called_once_with(
        LISTING_ID, {"title": "Nike", "description": "Size 27"}
    )


def test_analyze_failure_saves_nothing(
    client: TestClient, store: MagicMock, photos: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    photos.download_listing_photo.return_value = b"a"

    def broken(_: list[bytes]) -> ListingText:
        raise RuntimeError("DeepSeek is down")

    monkeypatch.setattr(listings, "describe", broken)
    assert client.post(f"/api/listings/{LISTING_ID}/analyze").status_code == 502
    store.update_listing.assert_not_called()


def test_list_listings(client: TestClient, store: MagicMock) -> None:
    store.list_listings.return_value = [_listing([_photo(PHOTO_A)])]
    body = client.get("/api/listings").json()
    assert [p["url"] for p in body[0]["photos"]] == [
        f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}"
    ]


def test_get_listing_returns_photos_in_order(client: TestClient) -> None:
    body = client.get(f"/api/listings/{LISTING_ID}").json()
    assert [p["id"] for p in body["photos"]] == [PHOTO_A, PHOTO_B]


def test_get_missing_listing_is_404(client: TestClient, store: MagicMock) -> None:
    store.get_listing.return_value = None
    assert client.get(f"/api/listings/{LISTING_ID}").status_code == 404


def test_non_uuid_listing_id_is_422(client: TestClient) -> None:
    assert client.get("/api/listings/not-a-uuid").status_code == 422


def test_delete_listing_removes_photos_and_doc(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    assert client.delete(f"/api/listings/{LISTING_ID}").status_code == 204
    photos.delete_listing_photos.assert_called_once_with(LISTING_ID)
    store.delete_listing.assert_called_once_with(LISTING_ID)


###############################################################################
#  Upload — Processed, Stored in GCS, Appended in Firestore
###############################################################################


def test_upload_resizes_and_stores(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert (body["width"], body["height"]) == (1200, 900)
    assert body["url"] == f"/api/listings/{LISTING_ID}/photos/{body['id']}"

    lid, pid, data = photos.upload_listing_photo.call_args.args
    assert (lid, pid) == (LISTING_ID, body["id"])
    assert Image.open(io.BytesIO(data)).size == (1200, 900)
    assert body["bytes"] == len(data)

    stored = store.add_listing_photo.call_args.args[1]
    assert stored["path"] == f"listing/{LISTING_ID}/{body['id']}.jpeg"


def test_upload_accepts_heic_sent_as_octet_stream(client: TestClient) -> None:
    buf = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (100, 50))).save(buf, quality=50)
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.heic", buf.getvalue(), "application/octet-stream")},
    )
    assert resp.status_code == 201
    assert (resp.json()["width"], resp.json()["height"]) == (100, 50)


def test_upload_rejects_non_image(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422
    photos.upload_listing_photo.assert_not_called()
    store.add_listing_photo.assert_not_called()


def test_upload_rejects_too_large(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vinted.admin.listings.MAX_BYTES", 10)
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.jpg", _jpeg((20, 20)), "image/jpeg")},
    )
    assert resp.status_code == 413


def test_upload_to_full_listing_is_409(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.get_listing.return_value = _listing(
        [_photo(str(uuid.uuid4())) for _ in range(MAX_PHOTOS_PER_LISTING)]
    )
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 409
    photos.upload_listing_photo.assert_not_called()


def test_upload_losing_the_race_for_the_last_slot_drops_the_file(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.add_listing_photo.return_value = False
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 409
    lid, photo, limit = store.add_listing_photo.call_args.args
    assert limit == MAX_PHOTOS_PER_LISTING
    photos.delete_listing_photo.assert_called_once_with(LISTING_ID, photo["id"])


def test_upload_to_missing_listing_is_404(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.get_listing.return_value = None
    resp = client.post(
        f"/api/listings/{LISTING_ID}/photos",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 404
    photos.upload_listing_photo.assert_not_called()


###############################################################################
#  Replace — Edited Photo Takes the Old One's Place
###############################################################################


def test_replace_photo_keeps_position_with_new_id(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.replace_listing_photo.return_value = _photo(PHOTO_A)
    resp = client.put(
        f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}",
        files={"file": ("a.jpg", _jpeg((1800, 2400)), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] != PHOTO_A
    assert (body["width"], body["height"]) == (900, 1200)

    lid, old_id, stored = store.replace_listing_photo.call_args.args
    assert (lid, old_id, stored["id"]) == (LISTING_ID, PHOTO_A, body["id"])
    photos.delete_listing_photo.assert_called_once_with(LISTING_ID, PHOTO_A)


def test_replace_unknown_photo_is_404(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    resp = client.put(
        f"/api/listings/{LISTING_ID}/photos/{uuid.uuid4()}",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 404
    photos.upload_listing_photo.assert_not_called()
    store.replace_listing_photo.assert_not_called()


def test_replace_photo_deleted_meanwhile_drops_upload(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.replace_listing_photo.return_value = None
    resp = client.put(
        f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 404
    new_id = photos.upload_listing_photo.call_args.args[1]
    photos.delete_listing_photo.assert_called_once_with(LISTING_ID, new_id)


###############################################################################
#  Photos — Serve, Delete and Reorder
###############################################################################


def test_get_photo_serves_immutable_jpeg(client: TestClient, photos: MagicMock) -> None:
    photos.download_listing_photo.return_value = b"jpeg"
    resp = client.get(f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}")
    assert resp.status_code == 200
    assert resp.content == b"jpeg"
    assert resp.headers["content-type"] == "image/jpeg"
    assert "immutable" in resp.headers["cache-control"]


def test_get_missing_photo_is_404(client: TestClient, photos: MagicMock) -> None:
    photos.download_listing_photo.return_value = None
    assert client.get(f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}").status_code == 404


def test_delete_photo(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    store.remove_listing_photo.return_value = _photo(PHOTO_A)
    assert client.delete(f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}").status_code == 204
    store.remove_listing_photo.assert_called_once_with(LISTING_ID, PHOTO_A)
    photos.delete_listing_photo.assert_called_once_with(LISTING_ID, PHOTO_A)


def test_delete_unknown_photo_is_404(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    store.remove_listing_photo.return_value = None
    assert client.delete(f"/api/listings/{LISTING_ID}/photos/{PHOTO_A}").status_code == 404
    photos.delete_listing_photo.assert_not_called()


def test_reorder_photos(client: TestClient, store: MagicMock) -> None:
    store.reorder_listing_photos.return_value = [_photo(PHOTO_B), _photo(PHOTO_A)]
    resp = client.patch(
        f"/api/listings/{LISTING_ID}/photos", json={"photo_ids": [PHOTO_B, PHOTO_A]}
    )
    assert resp.status_code == 200
    assert [p["id"] for p in resp.json()] == [PHOTO_B, PHOTO_A]
    store.reorder_listing_photos.assert_called_once_with(LISTING_ID, [PHOTO_B, PHOTO_A])


def test_reorder_with_stale_ids_is_409(client: TestClient, store: MagicMock) -> None:
    store.reorder_listing_photos.side_effect = ValueError("mismatch")
    resp = client.patch(f"/api/listings/{LISTING_ID}/photos", json={"photo_ids": [PHOTO_A]})
    assert resp.status_code == 409
