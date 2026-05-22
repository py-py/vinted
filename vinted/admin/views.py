from __future__ import annotations

import html
import json
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqladmin.filters import StaticValuesFilter
from sqladmin.filters import get_column_obj
from sqlalchemy import Select
from wtforms.fields import SelectField

from ..db.models import Item
from ..domain.enums import Catalog
from ..domain.enums import ItemStatus


def _catalog_label(catalog: Catalog) -> str:
    return catalog.name.replace("_", " ").title()


class IntStaticValuesFilter(StaticValuesFilter):
    """StaticValuesFilter that coerces the URL value to int for integer columns."""

    async def get_filtered_query(self, query: Select, value: object, model: object) -> Select:
        if value == "":
            return query
        return query.filter(get_column_obj(self.column, model) == int(value))


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


def _catalog(model: Item, _: str) -> str | Markup:
    if model.catalog_id is None:
        return _MUTED
    try:
        return _catalog_label(Catalog(model.catalog_id))
    except ValueError:
        return str(model.catalog_id)


def _verdict(model: Item, _: str) -> Markup:
    analysis = model.analysis or {}
    rating = analysis.get("rating")
    rec = analysis.get("recommendation")
    if not rating and not rec:
        return _MUTED
    parts: list[str] = []
    if rating:
        parts.append(f'<span class="fw-semibold">{int(rating)}/5</span>')
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
        Item.created_at,
    ]
    column_labels = {
        Item.catalog_id: "Catalog",
        Item.analysis: "Verdict",
        Item.image_urls: "Images",
        Item.created_at: "Created",
        Item.analyzed_at: "Analyzed",
    }
    column_searchable_list = [Item.id, Item.title]
    column_sortable_list = [Item.price, Item.status, Item.created_at, Item.analyzed_at]
    column_default_sort = [(Item.created_at, True)]
    column_filters = [
        StaticValuesFilter(
            Item.status,
            [(s.value, s.value) for s in ItemStatus],
            title="Status",
        ),
        IntStaticValuesFilter(
            Item.catalog_id,
            [(str(c.value), _catalog_label(c)) for c in Catalog],
            title="Catalog",
        ),
    ]

    column_formatters = {
        Item.image_urls: _list_thumb,
        Item.catalog_id: _catalog,
        Item.status: _status_badge,
        Item.analysis: _verdict,
        Item.price: _price,
        Item.created_at: _created,
    }
    column_formatters_detail = {
        Item.catalog_id: _catalog,
        Item.status: _status_badge,
        Item.image_urls: _thumbnails,
        Item.properties: _json_detail("properties"),
        Item.seller: _json_detail("seller"),
        Item.analysis: _json_detail("analysis"),
    }

    # JSONB fields get a CodeMirror editor; status gets a Select2 dropdown
    # (both wired up in templates/sqladmin/base.html).
    form_widget_args = {
        "properties": {"class": "json-codemirror"},
        "image_urls": {"class": "json-codemirror"},
        "seller": {"class": "json-codemirror"},
        "analysis": {"class": "json-codemirror"},
        "status": {"class": "form-control select2-field"},
    }
    # Render status as a <select> with the ItemStatus choices.
    form_overrides = {"status": SelectField}
    form_args = {"status": {"choices": [(s.value, s.value) for s in ItemStatus]}}

    page_size = 50
    page_size_options = [25, 50, 100, 200]
    can_export = True
