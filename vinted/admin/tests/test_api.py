from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from vinted.account.orders.models import SaleStatus

from .. import app
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
        {"id": 11, "title": "Nike Dunk", "paid_price": 30.0, "_sale_status": "sold"},
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


######
# PURCHASES
######


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


######
# ITEMS
######


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


######
# STATS
######


def test_stats(client: TestClient) -> None:
    body = client.get("/api/stats").json()
    assert body["purchases"] == 2
    assert body["items"] == 3
    assert body["spent_pln"] == 170.0
    assert body["by_status"] == {"sold": 1, "none": 2}
    assert body["by_month"] == [
        {"month": "2026-09", "purchases": 1, "items": 2, "spent_pln": 120.0},
        {"month": "2026-10", "purchases": 1, "items": 1, "spent_pln": 50.0},
    ]
