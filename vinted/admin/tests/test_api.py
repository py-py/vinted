from __future__ import annotations

from collections.abc import Iterator
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
            "_sale_item_id": 51,
        },
        {"id": 12, "title": "NB 9060", "paid_price": 90.0, "photo_url": "http://p/12.jpg"},
    ],
    "2": [{"id": 21, "title": "Samba", "paid_price": 50.0, "_sale_status": "legacy"}],
}
SALES = {
    "5": {
        "buyer_id": 50,
        "buyer_login": "carol",
        "buyer_country": "DE",
        "date": "2026-10-10T10:00:00+02:00",
        "items_price": 80.0,
        "shipment_price": 12.0,
        "currency": "PLN",
    },
    "6": {"buyer_login": "dave", "date": "2026-08-01T10:00:00+02:00", "currency": "PLN"},
}
SALE_ITEMS = {
    "5": [
        {"id": 51, "title": "Nike Dunk", "listed_price": 60.0, "sold_price": 60.0},
        {"id": 52, "title": "Jordan 1", "photo_url": "http://p/52.jpg", "sold_price": 20.0},
    ],
    "6": [{"id": 61, "title": "Puma"}],
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
    store.sales.stream.return_value = [_snap(k, v) for k, v in SALES.items()]
    store.client.collection_group.return_value.stream.return_value = [
        _snap(str(i["id"]), i, parent_id=tx)
        for tx, items in (ITEMS | SALE_ITEMS).items()
        for i in items
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
#  Sales — Items Join, Search and Date Filters
###############################################################################


def test_sales_newest_first_with_items(client: TestClient) -> None:
    body = client.get("/api/sales").json()
    assert [s["tx_id"] for s in body] == ["5", "6"]
    assert [i["id"] for i in body[0]["items"]] == [51, 52]
    assert body[0]["items"][1]["photo_urls"] == ["http://p/52.jpg"]
    assert body[0]["items_price"] == 80.0


def test_sales_search_matches_buyer_and_title(client: TestClient) -> None:
    assert [s["tx_id"] for s in client.get("/api/sales", params={"q": "dave"}).json()] == ["6"]
    assert [s["tx_id"] for s in client.get("/api/sales", params={"q": "jordan"}).json()] == ["5"]


def test_sales_date_range(client: TestClient) -> None:
    params = {"date_from": "2026-10-01"}
    assert [s["tx_id"] for s in client.get("/api/sales", params=params).json()] == ["5"]


def test_purchases_exclude_sale_items(client: TestClient) -> None:
    items = client.get("/api/items").json()["items"]
    assert {i["id"] for i in items} == {11, 12, 21}


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


def test_items_sale_link(client: TestClient) -> None:
    by_id = {i["id"]: i for i in client.get("/api/items").json()["items"]}
    assert by_id[11]["sale_item_id"] == 51
    assert by_id[12]["sale_item_id"] is None


@pytest.mark.parametrize("sale_item_id", [61, None])
def test_update_item_sale(client: TestClient, store: MagicMock, sale_item_id: int | None) -> None:
    response = client.patch("/api/items/1/12/sale", json={"sale_item_id": sale_item_id})
    assert response.status_code == 200
    assert response.json() == {"tx_id": "1", "item_id": "12", "sale_item_id": sale_item_id}
    store.set_item_sale_item_id.assert_called_once_with("1", "12", sale_item_id)


def test_update_item_sale_unknown_item(client: TestClient, store: MagicMock) -> None:
    # 12 is a purchase item, not a sale item.
    response = client.patch("/api/items/1/12/sale", json={"sale_item_id": 12})
    assert response.status_code == 404
    store.set_item_sale_item_id.assert_not_called()


def test_update_item_sale_rejects_non_positive(client: TestClient) -> None:
    response = client.patch("/api/items/1/12/sale", json={"sale_item_id": 0})
    assert response.status_code == 422


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
