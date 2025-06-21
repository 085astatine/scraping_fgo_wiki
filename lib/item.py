from __future__ import annotations

import logging
import pathlib
from typing import Optional

from .io import load_json
from .types import Item, ItemID, Items, ItemsByID, Resource, ResourceByID


def load_items(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[Item]]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load items from "%s"', path)
    items = load_json(path)
    if items is None:
        logger.error('failed to load items from "%s"', path)
        return None
    return items


class ItemNameConverter:
    def __init__(
        self,
        data: dict[str, ItemID],
        *,
        default_id: Optional[int] = None,
        logger: Optional[logging.Logger | logging.LoggerAdapter] = None,
    ) -> None:
        self._data = data
        self._default_id = default_id
        self._logger = logger or logging.getLogger(__name__)

    def item_id(self, item_name: str) -> Optional[ItemID]:
        item_id = self._data.get(item_name, None)
        if item_id is None:
            self._logger.error('item ID is not found: name="%s"', item_name)
            if self._default_id is not None:
                return self._default_id
            return None
        return item_id

    def items(self, items: Items) -> Optional[ItemsByID]:
        item_id = self.item_id(items["name"])
        if item_id is None:
            return None
        return ItemsByID(id=item_id, piece=items["piece"])

    def resource(self, resource: Resource) -> Optional[ResourceByID]:
        ok = True
        result: list[ItemsByID] = []
        for items in resource["items"]:
            value = self.items(items)
            if value is None:
                ok = False
            else:
                result.append(value)
        if not ok:
            return None
        return ResourceByID(qp=resource["qp"], items=result)
