from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from .. import app
from ..deps import get_store
from ..purchases import _allocate_pln

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


@pytest.mark.parametrize("path", ["/api/stats", "/", "/items"])
def test_missing_credentials_is_401(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_wrong_password_is_401(client: TestClient) -> None:
    assert client.get("/api/stats", auth=(AUTH[0], "wrong")).status_code == 401


def test_unconfigured_auth_is_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD")
    assert client.get("/api/stats", auth=AUTH).status_code == 503


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


def test_allocate_pln_falls_back_to_listed_price() -> None:
    purchase = {"currency": "PLN", "total_price": 100.0}
    items = [
        {"id": 1, "paid_price": 10.0, "listed_price": 25.0},
        {"id": 2, "listed_price": 75.0},
    ]
    assert _allocate_pln(purchase, items) == {1: 25.0, 2: 75.0}


def test_allocate_pln_skips_items_without_weight() -> None:
    purchase = {"currency": "PLN", "total_price": 100.0}
    items = [{"id": 1, "listed_price": 100.0}, {"id": 2}]
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
