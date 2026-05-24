"""Seed the database with sample items for local testing.

Run with::

    uv run python -m vinted.db.seed          # upsert sample rows
    uv run python -m vinted.db.seed --clear  # wipe the table first

Data flows through ``ItemsRepository`` (the real write path), so this also acts
as a smoke test for the SQL layer. Images are placeholder URLs; nothing is
uploaded to GCS.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import delete

from ..domain.analysis import BaseAnalysis
from ..domain.analysis import PriceRange
from ..domain.analysis import SkiBootsAnalysis
from ..domain.enums import ConditionState
from ..domain.enums import ItemStatus
from ..domain.enums import Recommendation
from ..domain.enums import SellerTrust
from ..domain.product import VintedProduct
from ..domain.product import VintedSeller
from .models import Item
from .session import get_sessionmaker


def _img(item_id: str, n: int = 3) -> list[str]:
    # Lorem Picsum placeholder photos; the seed keeps each image stable & distinct.
    return [f"https://picsum.photos/seed/{item_id}-{i}/400/400" for i in range(1, n + 1)]


def _ski_boots(**overrides) -> SkiBootsAnalysis:
    base = dict(
        rating=4,
        recommendation=Recommendation.buy,
        brand="Salomon",
        model="S/Pro 120",
        year="2022/2023",
        condition_state=ConditionState.good,
        condition_notes="Light wear on the shells, liners in good shape, buckles intact.",
        asking_price_pln=320.0,
        estimated_delivery_pln=18.0,
        estimated_resale_pln=PriceRange(min=550.0, max=700.0),
        profit_estimate_pln=PriceRange(min=180.0, max=320.0),
        roi_percent=78.0,
        red_flags=[],
        green_flags=["Popular flex", "Recent model", "Trusted seller"],
        seller_trust=SellerTrust.high,
        negotiate_target=None,
        negotiate_message=None,
        summary=(
            "Хорошее соотношение цены и качества, ботинки популярной модели в хорошем состоянии."
        ),
        sale_strategy="Выставить на OLX за 650 PLN, подчеркнуть свежий год и состояние колодки.",
        flex_index="120",
        mondo_size="27.5",
        eu_size="42",
        is_rental=False,
        estimated_age_years="2-3",
        safety_warning=None,
    )
    base.update(overrides)
    return SkiBootsAnalysis(**base)


def _skis(**overrides) -> BaseAnalysis:
    base = dict(
        rating=3,
        recommendation=Recommendation.negotiate,
        brand="Rossignol",
        model="Experience 84",
        year="2021/2022",
        condition_state=ConditionState.satisfactory,
        condition_notes="Base has a few scratches, edges fine, bindings adjustable.",
        asking_price_pln=400.0,
        estimated_delivery_pln=30.0,
        estimated_resale_pln=PriceRange(min=550.0, max=650.0),
        profit_estimate_pln=PriceRange(min=80.0, max=180.0),
        roi_percent=33.0,
        red_flags=["Base scratches", "Older season"],
        green_flags=["Versatile all-mountain ski", "Bindings included"],
        seller_trust=SellerTrust.medium,
        negotiate_target=330.0,
        negotiate_message="Предложить 330 PLN, сославшись на царапины на скользящей поверхности.",
        summary="Универсальные лыжи, но цена завышена под состояние — есть смысл торговаться.",
        sale_strategy="Перепродать за 600 PLN после шлифовки канта.",
    )
    base.update(overrides)
    return BaseAnalysis(**base)


# (product, analysis | None, status | None). status is applied via the repo:
#   - analysis present  -> save_analysis(status)
#   - analysis None, status set -> set_status (e.g. failed)
#   - both None -> left as "new"
def _dataset() -> list[tuple[VintedProduct, BaseAnalysis | None, ItemStatus | None]]:
    return [
        (
            VintedProduct(
                id="9001",
                title="Salomon S/Pro 120 ski boots 27.5",
                description="Buty narciarskie Salomon S/Pro 120, sezon 2022/23, mało używane.",
                catalog_id="2683",
                url="https://www.vinted.pl/items/9001",
                price=320.0,
                properties={"Rozmiar": "42", "Marka": "Salomon", "Stan": "Bardzo dobry"},
                image_urls=_img("9001"),
                seller=VintedSeller(
                    id=5001, username="ski_pro_pl", country="PL", feedback_count=128
                ),
            ),
            _ski_boots(rating=5, recommendation=Recommendation.buy),
            ItemStatus.notified,
        ),
        (
            VintedProduct(
                id="9002",
                title="Atomic Hawx Ultra 100",
                description="Buty Atomic Hawx Ultra 100, flex 100, rozmiar 28.0.",
                catalog_id="2683",
                url="https://www.vinted.pl/items/9002",
                price=280.0,
                properties={"Rozmiar": "43", "Marka": "Atomic"},
                image_urls=_img("9002"),
                seller=VintedSeller(
                    id=5002, username="zimowy_sklep", country="PL", feedback_count=54
                ),
            ),
            _ski_boots(
                brand="Atomic",
                model="Hawx Ultra 100",
                flex_index="100",
                mondo_size="28.0",
                eu_size="43",
                rating=4,
                recommendation=Recommendation.negotiate,
                negotiate_target=240.0,
                negotiate_message="Предложить 240 PLN — флекс ниже топового, рынок насыщен.",
            ),
            ItemStatus.notified,
        ),
        (
            VintedProduct(
                id="9003",
                title="Rossignol Experience 84 + bindings 170cm",
                description="Narty Rossignol Experience 84, długość 170 cm, z wiązaniami.",
                catalog_id="4733",
                url="https://www.vinted.pl/items/9003",
                price=400.0,
                properties={"Długość": "170 cm", "Marka": "Rossignol"},
                image_urls=_img("9003"),
                seller=VintedSeller(
                    id=5003, username="gory_i_narty", country="PL", feedback_count=31
                ),
            ),
            _skis(rating=3, recommendation=Recommendation.negotiate),
            ItemStatus.analyzed,
        ),
        (
            VintedProduct(
                id="9004",
                title="Nordica rental ski boots 25.0",
                description="Buty narciarskie Nordica, używane, ślady wypożyczalni.",
                catalog_id="2652",
                url="https://www.vinted.pl/items/9004",
                price=120.0,
                properties={"Rozmiar": "39", "Marka": "Nordica"},
                image_urls=_img("9004", 2),
                seller=VintedSeller(
                    id=5004, username="okazje_zima", country="PL", feedback_count=9
                ),
            ),
            _ski_boots(
                brand="Nordica",
                model="Cruise 60",
                flex_index="60",
                mondo_size="25.0",
                eu_size="39",
                rating=2,
                recommendation=Recommendation.skip,
                condition_state=ConditionState.satisfactory,
                is_rental=True,
                estimated_age_years="8+",
                safety_warning="Старые ботинки из проката, возможна деградация пластика.",
                red_flags=["Rental markings", "Low flex", "Old age"],
                green_flags=[],
                seller_trust=SellerTrust.low,
                roi_percent=-10.0,
                profit_estimate_pln=PriceRange(min=-30.0, max=20.0),
                summary="Прокатные ботинки в плохом состоянии — не покупать.",
            ),
            ItemStatus.skipped,
        ),
        (
            VintedProduct(
                id="9005",
                title="Head Supershape e-Rally 163cm",
                description="Narty Head Supershape, świetny stan.",
                catalog_id="4733",
                url="https://www.vinted.pl/items/9005",
                price=650.0,
                properties={"Długość": "163 cm", "Marka": "Head"},
                image_urls=_img("9005"),
                seller=VintedSeller(
                    id=5005, username="alpy_outlet", country="PL", feedback_count=72
                ),
            ),
            None,
            None,  # left as "new"
        ),
        (
            VintedProduct(
                id="9006",
                title="Tecnica Mach1 MV 110",
                description="Buty Tecnica Mach1, rozmiar 27.0.",
                catalog_id="2683",
                url="https://www.vinted.pl/items/9006",
                price=300.0,
                properties={"Rozmiar": "42", "Marka": "Tecnica"},
                image_urls=_img("9006"),
                seller=VintedSeller(
                    id=5006, username="narciarz12", country="PL", feedback_count=23
                ),
            ),
            None,
            None,  # left as "new"
        ),
        (
            VintedProduct(
                id="9007",
                title="Fischer RC One 173cm (broken listing)",
                description="Narty Fischer RC One.",
                catalog_id="4733",
                url="https://www.vinted.pl/items/9007",
                price=480.0,
                properties={"Długość": "173 cm"},
                image_urls=[],
                seller=None,  # broken listing: no seller -> exercises nullable FK
            ),
            None,
            ItemStatus.failed,
        ),
        (
            VintedProduct(
                id="9008",
                title="Lange RX 130 LV 28.5",
                description="Buty Lange RX 130, flex 130, topowy model.",
                catalog_id="2683",
                url="https://www.vinted.pl/items/9008",
                price=450.0,
                properties={"Rozmiar": "44", "Marka": "Lange", "Stan": "Jak nowe"},
                image_urls=_img("9008", 4),
                seller=VintedSeller(
                    id=5008, username="pro_skier", country="PL", feedback_count=210
                ),
            ),
            _ski_boots(
                brand="Lange",
                model="RX 130 LV",
                flex_index="130",
                mondo_size="28.5",
                eu_size="44",
                rating=5,
                recommendation=Recommendation.buy,
                asking_price_pln=450.0,
                estimated_resale_pln=PriceRange(min=750.0, max=900.0),
                profit_estimate_pln=PriceRange(min=250.0, max=400.0),
                roi_percent=72.0,
                green_flags=["Top-tier model", "Like new", "Top-rated seller"],
                summary="Топовая модель в состоянии «как новые» по выгодной цене — брать.",
            ),
            ItemStatus.notified,
        ),
    ]


# Status -> (recommendation, rating) for generated rows. ``new``/``failed`` carry
# no analysis; the rest get a synthetic one matching the catalog's schema.
_GEN_CYCLE: list[tuple[ItemStatus, Recommendation | None, int | None]] = [
    (ItemStatus.notified, Recommendation.buy, 5),
    (ItemStatus.analyzed, Recommendation.negotiate, 3),
    (ItemStatus.new, None, None),
    (ItemStatus.skipped, Recommendation.skip, 2),
    (ItemStatus.notified, Recommendation.buy, 4),
    (ItemStatus.failed, None, None),
]
_GEN_COUNTRIES = ["PL", "DE", "FR", "IT", "ES", "CZ"]
# Distinct (catalog, brand, model) combos; catalog 4733 == skis, others == boots.
_GEN_PRODUCTS = [
    ("2683", "Salomon", "S/Pro 100"),
    ("4733", "Völkl", "Deacon 76"),
    ("2652", "Atomic", "Hawx 90"),
    ("2683", "Tecnica", "Cochise 110"),
    ("4733", "Blizzard", "Rustler 9"),
    ("2652", "Lange", "RX 120"),
    ("2683", "Nordica", "Speedmachine 95"),
    ("4733", "Elan", "Wingman 82"),
    ("2652", "Head", "Edge LYT 80"),
    ("2683", "Dalbello", "Panterra 100"),
    ("4733", "Dynastar", "Speed 4x4"),
    ("2652", "Rossignol", "Alltrack 90"),
]


def _generated(count: int, *, first_id: int = 9009) -> list[tuple]:
    """Synthesize ``count`` extra items, cycling catalog, status and verdict."""
    out: list[tuple[VintedProduct, BaseAnalysis | None, ItemStatus | None]] = []
    for k in range(count):
        vid = str(first_id + k)
        status, rec, rating = _GEN_CYCLE[k % len(_GEN_CYCLE)]
        catalog, brand, model = _GEN_PRODUCTS[k % len(_GEN_PRODUCTS)]
        is_ski = catalog == "4733"
        price = 150.0 + (k % 8) * 55
        product = VintedProduct(
            id=vid,
            title=f"{brand} {model}",
            description=f"{brand} {model}, używane, stan dobry.",
            catalog_id=catalog,
            url=f"https://www.vinted.pl/items/{vid}",
            price=price,
            properties={"Marka": brand, "Rozmiar": str(38 + k % 8)},
            image_urls=_img(vid) if status is not ItemStatus.failed else [],
            seller=VintedSeller(
                # 6 distinct sellers reused across 12 items -> some own multiple.
                id=5101 + k % 6,
                username=f"seller_{5101 + k % 6}",
                country=_GEN_COUNTRIES[k % len(_GEN_COUNTRIES)],
                feedback_count=10 + k * 7,
                last_seen_at=datetime.now(UTC) - timedelta(days=k),
            ),
        )
        if status in (ItemStatus.notified, ItemStatus.analyzed, ItemStatus.skipped):
            make = _skis if is_ski else _ski_boots
            analysis = make(
                brand=brand, model=model, rating=rating, recommendation=rec, asking_price_pln=price
            )
            out.append((product, analysis, status))
        elif status is ItemStatus.failed:
            out.append((product, None, ItemStatus.failed))
        else:
            out.append((product, None, None))
    return out


async def seed(clear: bool = False) -> None:
    # Import here to avoid a circular import (repo imports db.models/session).
    from ..repositories.items_repo import ItemsRepository

    if clear:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Item))
            await session.commit()
        print("Cleared items table.")

    repo = ItemsRepository()

    dataset = _dataset() + _generated(12)  # 8 curated + 12 generated = 20
    for product, analysis, status in dataset:
        await repo.save_product(product)
        if analysis is not None and status is not None:
            await repo.save_analysis(product.id, analysis, status=status)
        elif status is not None:
            await repo.set_status(product.id, status)
        label = status.value if status else ItemStatus.new.value
        print(f"  + {product.id}  {label:<9} {product.title}")

    print(f"Seeded {len(dataset)} items.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="vinted.db.seed")
    parser.add_argument("--clear", action="store_true", help="Delete all rows before seeding")
    args = parser.parse_args()
    asyncio.run(seed(clear=args.clear))


if __name__ == "__main__":
    main()
