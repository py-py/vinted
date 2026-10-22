from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from vinted.account.orders.models import SaleStatus
from vinted.admin import app
from vinted.admin.deps import get_store
from vinted.admin.purchases import _allocate_pln

AUTH = ("admin", "secret")


@pytest.fixture(autouse=True)
def admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", AUTH[0])
    monkeypatch.setenv("ADMIN_PASSWORD", AUTH[1])


@pytest.fixture
def store() -> Iterator[MagicMock]:
    store = MagicMock()
    store.purchases.stream.return_value = []
    store.client.collection_group.return_value.stream.return_value = []
    app.dependency_overrides[get_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


@pytest.fixture
def client(store: MagicMock) -> TestClient:
    return TestClient(app)


######
# AUTH
######


def test_missing_credentials_is_401(client: TestClient) -> None:
    assert client.get("/").status_code == 401


def test_wrong_password_is_401(client: TestClient) -> None:
    assert client.get("/", auth=(AUTH[0], "wrong")).status_code == 401


def test_unconfigured_auth_is_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD")
    assert client.get("/", auth=AUTH).status_code == 503


######
# INDEX
######


def test_index_renders(client: TestClient) -> None:
    response = client.get("/", auth=AUTH)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


######
# SET STATUS
######


def test_set_status(client: TestClient, store: MagicMock) -> None:
    response = client.post("/items/1/2/status", json={"status": "sold"}, auth=AUTH)
    assert response.status_code == 200
    assert response.json() == {"tx_id": "1", "item_id": "2", "status": "sold"}
    store.set_item_status.assert_called_once_with("1", "2", SaleStatus.SOLD)


def test_set_status_rejects_unknown_value(client: TestClient, store: MagicMock) -> None:
    response = client.post("/items/1/2/status", json={"status": "bogus"}, auth=AUTH)
    assert response.status_code == 422
    store.set_item_status.assert_not_called()


######
# ALLOCATE PLN
######


def test_allocate_pln_splits_total_by_paid_price() -> None:
    purchase = {"currency": "PLN", "total_price": 120.0}
    items = [{"id": 1, "paid_price": 30.0}, {"id": 2, "paid_price": 90.0}]
    assert _allocate_pln(purchase, items) == {1: 30.0, 2: 90.0}


def test_allocate_pln_includes_fees_proportionally() -> None:
    purchase = {"currency": "PLN", "total_price": 110.0}
    items = [{"id": 1, "paid_price": 50.0}, {"id": 2, "paid_price": 50.0}]
    assert _allocate_pln(purchase, items) == {1: 55.0, 2: 55.0}


def test_allocate_pln_skips_items_without_price() -> None:
    purchase = {"currency": "PLN", "total_price": 100.0}
    items = [{"id": 1, "paid_price": 100.0}, {"id": 2}]
    assert _allocate_pln(purchase, items) == {1: 100.0}


@pytest.mark.parametrize(
    "purchase",
    [
        {"currency": "EUR", "total_price": 100.0},
        {"currency": "PLN", "total_price": None},
        {"currency": "PLN", "total_price": 0},
    ],
)
def test_allocate_pln_returns_empty_when_not_allocatable(purchase: dict) -> None:
    assert _allocate_pln(purchase, [{"id": 1, "paid_price": 10.0}]) == {}
