from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from ...repositories.items_repo import ItemsRepository
from ..deps import items_repo_dep

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}")
async def get_item(
    item_id: str,
    repo: ItemsRepository = Depends(items_repo_dep),
) -> dict:
    item = await repo.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
