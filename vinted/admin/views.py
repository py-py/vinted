from __future__ import annotations

from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter
from sqladmin.filters import StaticValuesFilter

from ..db.models import Item
from ..domain.enums import ItemStatus


class ItemAdmin(ModelView, model=Item):
    """Admin view for scraped items and their analyses."""

    name = "Item"
    name_plural = "Items"
    icon = "fa-solid fa-tag"

    column_list = [
        Item.id,
        Item.title,
        Item.catalog_id,
        Item.price,
        Item.status,
        Item.source,
        Item.created_at,
    ]
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

    page_size = 50
    page_size_options = [25, 50, 100, 200]
    can_export = True
