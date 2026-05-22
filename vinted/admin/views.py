from __future__ import annotations

import html
import json
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter
from sqladmin.filters import StaticValuesFilter

from ..db.models import Item
from ..domain.enums import ItemStatus

_STATUS_COLORS = {
    ItemStatus.new.value: "secondary",
    ItemStatus.analyzed.value: "info",
    ItemStatus.notified.value: "success",
    ItemStatus.skipped.value: "warning",
    ItemStatus.failed.value: "danger",
}
_REC_COLORS = {"buy": "success", "negotiate": "warning", "skip": "danger"}
_MUTED = Markup('<span class="text-muted">—</span>')


def _badge(text: str, color: str) -> Markup:
    return Markup(f'<span class="badge bg-{color}">{html.escape(str(text))}</span>')


def _status_badge(model: Item, _: str) -> Markup:
    return _badge(model.status, _STATUS_COLORS.get(model.status, "light"))


def _verdict(model: Item, _: str) -> Markup:
    analysis = model.analysis or {}
    rating = analysis.get("rating")
    rec = analysis.get("recommendation")
    if not rating and not rec:
        return _MUTED
    parts: list[str] = []
    if rating:
        stars = "★" * int(rating) + "☆" * (5 - int(rating))
        parts.append(f'<span class="text-warning" title="{rating}/5">{stars}</span>')
    if rec:
        color = _REC_COLORS.get(rec, "secondary")
        parts.append(f'<span class="badge bg-{color}">{html.escape(rec)}</span>')
    return Markup(" ".join(parts))


def _price(model: Item, _: str) -> str:
    return f"{model.price:.0f} zł"


def _created(model: Item, _: str) -> str:
    return model.created_at.strftime("%Y-%m-%d %H:%M") if model.created_at else "—"


def _json_block(value: Any) -> Markup:
    if not value:
        return _MUTED
    dumped = html.escape(json.dumps(value, ensure_ascii=False, indent=2))
    style = "max-height:24rem;overflow:auto"
    return Markup(f'<pre class="mb-0" style="{style}">{dumped}</pre>')


def _json_detail(attr: str):
    return lambda model, _: _json_block(getattr(model, attr))


def _gallery(urls: list[str], size: int) -> Markup:
    """Render a PhotoSwipe gallery: ``.pswp-gallery`` of ``<a><img></a>`` links.

    Each ``<a>`` points at the full image; the thumbnail is the same image scaled
    down via CSS. PhotoSwipe (wired up in templates/sqladmin/base.html) turns
    clicks into a modal — a single image opens alone, several open as a carousel.
    """
    if not urls:
        return _MUTED
    links = "".join(
        f'<a href="{html.escape(u)}" target="_blank" rel="noopener">'
        f'<img src="{html.escape(u)}" alt="" loading="lazy" '
        f'style="height:{size}px;width:{size}px;object-fit:cover;border-radius:6px;margin:2px" '
        f'onerror="this.style.opacity=0.3"></a>'
        for u in urls
    )
    return Markup(f'<div class="pswp-gallery d-flex flex-wrap">{links}</div>')


def _list_thumb(model: Item, _: str) -> Markup:
    """A single clickable thumbnail (the first image) for the list view."""
    return _gallery((model.image_urls or [])[:1], 48)


def _thumbnails(model: Item, _: str) -> Markup:
    """All images as a clickable carousel for the details view."""
    return _gallery(model.image_urls or [], 80)


class ItemAdmin(ModelView, model=Item):
    """Admin view for scraped items and their analyses."""

    name = "Item"
    name_plural = "Items"
    icon = "fa-solid fa-tag"

    column_list = [
        Item.id,
        Item.image_urls,
        Item.title,
        Item.catalog_id,
        Item.price,
        Item.status,
        Item.analysis,
        Item.source,
        Item.created_at,
    ]
    column_labels = {
        Item.catalog_id: "Catalog",
        Item.analysis: "Verdict",
        Item.image_urls: "Images",
        Item.created_at: "Created",
        Item.analyzed_at: "Analyzed",
    }
    column_searchable_list = [Item.id, Item.title, Item.catalog_id]
    column_sortable_list = [Item.price, Item.status, Item.created_at, Item.analyzed_at]
    column_default_sort = [(Item.created_at, True)]
    column_filters = [
        StaticValuesFilter(
            Item.status,
            [(s.value, s.value) for s in ItemStatus],
            title="Status",
        ),
        AllUniqueStringValuesFilter(Item.source, title="Source"),
        AllUniqueStringValuesFilter(Item.catalog_id, title="Catalog"),
    ]

    column_formatters = {
        Item.image_urls: _list_thumb,
        Item.status: _status_badge,
        Item.analysis: _verdict,
        Item.price: _price,
        Item.created_at: _created,
    }
    column_formatters_detail = {
        Item.status: _status_badge,
        Item.image_urls: _thumbnails,
        Item.properties: _json_detail("properties"),
        Item.seller: _json_detail("seller"),
        Item.analysis: _json_detail("analysis"),
    }

    page_size = 50
    page_size_options = [25, 50, 100, 200]
    can_export = True
