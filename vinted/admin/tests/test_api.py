from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from vinted.account.orders.models import SaleStatus

from .. import app
from ..api import _stored_photo_url
from ..deps import get_photo_store
from ..deps import get_store

AUTH = ("admin", "secret")

PURCHASES = {
    "1": {
        "seller_id": 10,
        "seller_login": "alice",
        "seller_country": "PL",
        "date": "2026-09-05T10:00:00+02:00",
        "conversation_id": 100,
        "total_price": 120.0,
        "currency": "PLN",
    },
    "2": {
        "seller_id": 20,
        "seller_login": "bob",
        "date": "2026-10-01T10:00:00+02:00",
        "total_price": 50.0,
        "currency": "PLN",
    },
}
ITEMS = {
    "1": [
        {
            "id": 11,
            "title": "Nike Dunk",
            "paid_price": 30.0,
            "_sale_status": "sold",
            "_sell_price": 45.5,
        },
        {"id": 12, "title": "NB 9060", "paid_price": 90.0, "photo_url": "http://p/12.jpg"},
    ],
    "2": [{"id": 21, "title": "Samba", "paid_price": 50.0, "_sale_status": "legacy"}],
}


def _snap(doc_id: str, data: dict, parent_id: str | None = None) -> MagicMock:
    snap = MagicMock(id=doc_id)
    snap.to_dict.return_value = data
    if parent_id is not None:
        snap.reference.parent.parent.id = parent_id
    return snap


@pytest.fixture(autouse=True)
def admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", AUTH[0])
    monkeypatch.setenv("ADMIN_PASSWORD", AUTH[1])


@pytest.fixture
def store() -> Iterator[MagicMock]:
    store = MagicMock()
    store.purchases.stream.return_value = [_snap(k, v) for k, v in PURCHASES.items()]
    store.client.collection_group.return_value.stream.return_value = [
        _snap(str(i["id"]), i, parent_id=tx) for tx, items in ITEMS.items() for i in items
    ]
    app.dependency_overrides[get_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def client(store: MagicMock) -> TestClient:
    client = TestClient(app)
    client.auth = AUTH
    return client


def test_api_requires_auth(store: MagicMock) -> None:
    assert TestClient(app).get("/api/items").status_code == 401


###############################################################################
#  Purchases — Search and Date Filters
###############################################################################


def test_purchases_newest_first_with_items(client: TestClient) -> None:
    body = client.get("/api/purchases").json()
    assert [p["tx_id"] for p in body] == ["2", "1"]
    assert [i["id"] for i in body[1]["items"]] == [11, 12]
    assert body[1]["items"][0]["price_pln"] == 30.0


def test_purchases_search_matches_item_title(client: TestClient) -> None:
    body = client.get("/api/purchases", params={"q": "dunk"}).json()
    assert [p["tx_id"] for p in body] == ["1"]


def test_purchases_date_range(client: TestClient) -> None:
    params = {"date_from": "2026-09-01", "date_to": "2026-09-30"}
    body = client.get("/api/purchases", params=params).json()
    assert [p["tx_id"] for p in body] == ["1"]


###############################################################################
#  Items — Status Filter, Search and Pagination
###############################################################################


def test_items_flat_list(client: TestClient) -> None:
    body = client.get("/api/items").json()
    assert body["total"] == 3
    assert [i["id"] for i in body["items"]] == [21, 11, 12]
    assert body["items"][2]["photo_urls"] == ["http://p/12.jpg"]


def test_items_unknown_status_falls_back_to_none(client: TestClient) -> None:
    body = client.get("/api/items").json()
    assert body["items"][0]["status"] == "none"


def test_items_filter_by_status(client: TestClient) -> None:
    body = client.get("/api/items", params={"status": ["sold", "none"]}).json()
    assert [i["id"] for i in body["items"]] == [21, 11, 12]
    body = client.get("/api/items", params={"status": "sold"}).json()
    assert [i["id"] for i in body["items"]] == [11]


def test_items_rejects_unknown_status_filter(client: TestClient) -> None:
    assert client.get("/api/items", params={"status": "bogus"}).status_code == 422


def test_items_search(client: TestClient) -> None:
    body = client.get("/api/items", params={"q": "ALICE"}).json()
    assert [i["id"] for i in body["items"]] == [11, 12]


def test_items_pagination(client: TestClient) -> None:
    body = client.get("/api/items", params={"page": 2, "size": 2}).json()
    assert body == {**body, "total": 3, "page": 2, "size": 2}
    assert [i["id"] for i in body["items"]] == [12]


def test_update_item_status(client: TestClient, store: MagicMock) -> None:
    response = client.patch("/api/items/1/12", json={"status": "listed"})
    assert response.status_code == 200
    assert response.json() == {"tx_id": "1", "item_id": "12", "status": "listed"}
    store.set_item_status.assert_called_once_with("1", "12", SaleStatus.LISTED)


@pytest.mark.parametrize("price", [80.0, None])
def test_update_item_sell_price(client: TestClient, store: MagicMock, price: float | None) -> None:
    response = client.patch("/api/items/1/12/sell-price", json={"sell_price": price})
    assert response.status_code == 200
    assert response.json() == {"tx_id": "1", "item_id": "12", "sell_price": price}
    store.set_item_sell_price.assert_called_once_with("1", "12", price)


def test_update_item_sell_price_rejects_negative(client: TestClient) -> None:
    response = client.patch("/api/items/1/12/sell-price", json={"sell_price": -1})
    assert response.status_code == 422


@pytest.mark.parametrize(("has", "ids"), [("true", [11]), ("false", [21, 12])])
def test_items_filter_by_sell_price(client: TestClient, has: str, ids: list[int]) -> None:
    body = client.get("/api/items", params={"has_sell_price": has}).json()
    assert [i["id"] for i in body["items"]] == ids


def test_items_sell_price(client: TestClient) -> None:
    by_id = {i["id"]: i for i in client.get("/api/items").json()["items"]}
    assert by_id[11]["sell_price"] == 45.5
    assert by_id[12]["sell_price"] is None


###############################################################################
#  Stats — Totals and Monthly Breakdown
###############################################################################


def test_stats(client: TestClient) -> None:
    body = client.get("/api/stats").json()
    assert body["purchases"] == 2
    assert body["items"] == 3
    assert body["spent_pln"] == 170.0
    assert body["sold_pln"] == 45.5
    assert body["sold_items"] == 1
    assert body["by_status"] == {"sold": 1, "none": 2}
    assert body["by_month"] == [
        {"month": "2026-09", "purchases": 1, "items": 2, "spent_pln": 120.0},
        {"month": "2026-10", "purchases": 1, "items": 1, "spent_pln": 50.0},
    ]


###############################################################################
#  Photos — GCS Fallback for Deleted Listings
###############################################################################


@pytest.fixture
def photos() -> Iterator[MagicMock]:
    photos = MagicMock()
    app.dependency_overrides[get_photo_store] = lambda: photos
    yield photos
    app.dependency_overrides.pop(get_photo_store, None)


def test_stored_photo_url() -> None:
    url = "https://images1.vinted.net/t/abc_12/f800/1.jpeg?s=x"
    assert _stored_photo_url(12, url) == "/api/photos/12/abc_12"
    assert _stored_photo_url(12, "http://p/12.jpg") == ""


def test_items_stored_photo_urls(client: TestClient) -> None:
    item = next(i for i in client.get("/api/items").json()["items"] if i["id"] == 12)
    assert item["stored_photo_urls"] == [""]


def test_get_photo_from_gcs(client: TestClient, photos: MagicMock) -> None:
    photos.download_photo.return_value = b"jpeg"
    resp = client.get("/api/photos/12/abc_12")
    assert resp.status_code == 200
    assert resp.content == b"jpeg"
    assert resp.headers["content-type"] == "image/jpeg"
    photos.download_photo.assert_called_once_with(12, "abc_12")


def test_get_photo_missing(client: TestClient, photos: MagicMock) -> None:
    photos.download_photo.return_value = None
    assert client.get("/api/photos/12/nope").status_code == 404


def test_get_photo_rejects_bad_token(client: TestClient, photos: MagicMock) -> None:
    assert client.get("/api/photos/12/a.b").status_code == 422
    photos.download_photo.assert_not_called()


###############################################################################
#  Sales — Create, List and Photos
###############################################################################

JPEG = b"\xff\xd8\xff\xe0jpeg"
SALE_ID = "aB3xK9mQ2pL7nR4tW8yZ"
PHOTO_ID = "0" * 32


def test_create_sale(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    store.new_sale_id.return_value = SALE_ID
    resp = client.post(
        "/api/sales",
        data={"title": " Nike Dunk ", "description": "Size 42", "price_pln": "150"},
        files=[("photos", ("a.jpg", JPEG, "image/jpeg")), ("photos", ("b.jpg", JPEG))],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == SALE_ID
    assert body["title"] == "Nike Dunk"
    assert body["price_pln"] == 150.0
    assert len(body["photo_urls"]) == 2
    assert body["photo_urls"][0].startswith(f"/api/sales/{SALE_ID}/photos/")
    assert photos.upload_sale_photo.call_count == 2
    saved = store.save_sale.call_args.args[1]
    assert saved["description"] == "Size 42"
    assert len(saved["photos"]) == 2


def test_create_sale_requires_photo(client: TestClient, store: MagicMock) -> None:
    assert client.post("/api/sales", data={"title": "x"}).status_code == 422
    store.save_sale.assert_not_called()


def test_create_sale_rejects_non_jpeg(
    client: TestClient, store: MagicMock, photos: MagicMock
) -> None:
    resp = client.post(
        "/api/sales", data={"title": "x"}, files={"photos": ("a.png", b"\x89PNG", "image/png")}
    )
    assert resp.status_code == 422
    photos.upload_sale_photo.assert_not_called()
    store.save_sale.assert_not_called()


def test_list_sales(client: TestClient, store: MagicMock) -> None:
    created = datetime(2026, 10, 23, 12, tzinfo=UTC)
    store.list_sales.return_value = [
        (SALE_ID, {"title": "Samba", "photos": [PHOTO_ID], "created_at": created}),
    ]
    [sale] = client.get("/api/sales").json()
    assert sale["title"] == "Samba"
    assert sale["price_pln"] is None
    assert sale["photo_ids"] == [PHOTO_ID]
    assert sale["photo_urls"] == [f"/api/sales/{SALE_ID}/photos/{PHOTO_ID}"]
    assert sale["created_at"] == "2026-10-23T12:00:00+00:00"


OLD_A, OLD_B = "a" * 32, "b" * 32


@pytest.fixture
def stored_sale(store: MagicMock) -> dict:
    sale = {"title": "Old", "description": "d", "price_pln": 10.0, "photos": [OLD_A, OLD_B]}
    store.get_sale.return_value = sale
    return sale


def test_update_sale(
    client: TestClient, store: MagicMock, photos: MagicMock, stored_sale: dict
) -> None:
    resp = client.put(
        f"/api/sales/{SALE_ID}",
        data={"title": "New", "layout": ["new", OLD_B]},
        files={"photos": ("c.jpg", JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New"
    assert body["description"] == ""
    assert body["price_pln"] is None
    new_id = body["photo_ids"][0]
    assert body["photo_ids"] == [new_id, OLD_B]
    photos.upload_sale_photo.assert_called_once_with(SALE_ID, new_id, JPEG)
    photos.delete_sale_photo.assert_called_once_with(SALE_ID, OLD_A)
    assert store.update_sale.call_args.args[1]["photos"] == [new_id, OLD_B]


def test_update_sale_reorder_only(
    client: TestClient, store: MagicMock, photos: MagicMock, stored_sale: dict
) -> None:
    data = {"title": "Old", "layout": [OLD_B, OLD_A], "price_pln": "12.5"}
    resp = client.put(f"/api/sales/{SALE_ID}", data=data)
    assert resp.status_code == 200
    assert resp.json()["photo_ids"] == [OLD_B, OLD_A]
    assert resp.json()["price_pln"] == 12.5
    photos.upload_sale_photo.assert_not_called()
    photos.delete_sale_photo.assert_not_called()


def test_update_sale_rejects_foreign_photo_id(
    client: TestClient, store: MagicMock, photos: MagicMock, stored_sale: dict
) -> None:
    resp = client.put(f"/api/sales/{SALE_ID}", data={"title": "x", "layout": ["c" * 32]})
    assert resp.status_code == 422
    store.update_sale.assert_not_called()


def test_update_sale_rejects_file_count_mismatch(
    client: TestClient, store: MagicMock, photos: MagicMock, stored_sale: dict
) -> None:
    resp = client.put(f"/api/sales/{SALE_ID}", data={"title": "x", "layout": ["new", OLD_A]})
    assert resp.status_code == 422
    store.update_sale.assert_not_called()


def test_update_sale_missing(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    store.get_sale.return_value = None
    resp = client.put(f"/api/sales/{SALE_ID}", data={"title": "x", "layout": [OLD_A]})
    assert resp.status_code == 404


def test_delete_sale(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    store.delete_sale.return_value = True
    assert client.delete(f"/api/sales/{SALE_ID}").status_code == 204
    store.delete_sale.assert_called_once_with(SALE_ID)
    photos.delete_sale_photos.assert_called_once_with(SALE_ID)


def test_delete_sale_missing(client: TestClient, store: MagicMock, photos: MagicMock) -> None:
    store.delete_sale.return_value = False
    assert client.delete(f"/api/sales/{SALE_ID}").status_code == 404
    photos.delete_sale_photos.assert_not_called()


def test_delete_sale_rejects_bad_id(client: TestClient, store: MagicMock) -> None:
    assert client.delete("/api/sales/short").status_code == 422
    assert client.delete(f"/api/sales/{SALE_ID[:-1]}_").status_code == 422
    store.delete_sale.assert_not_called()


def test_get_sale_photo(client: TestClient, photos: MagicMock) -> None:
    photos.download_sale_photo.return_value = JPEG
    resp = client.get(f"/api/sales/{SALE_ID}/photos/{PHOTO_ID}")
    assert resp.status_code == 200
    assert resp.content == JPEG
    photos.download_sale_photo.assert_called_once_with(SALE_ID, PHOTO_ID)


def test_get_sale_photo_rejects_bad_id(client: TestClient, photos: MagicMock) -> None:
    assert client.get(f"/api/sales/{SALE_ID}/photos/nope").status_code == 422
    photos.download_sale_photo.assert_not_called()
