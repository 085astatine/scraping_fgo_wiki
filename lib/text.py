from __future__ import annotations

import logging
import pathlib
from typing import Optional

from .io import load_json
from .types import Dictionary, Item, ItemDictionary, Text


def load_item_dictionary(path: pathlib.Path) -> ItemDictionary:
    data = load_json(path)
    if data is None:
        return {}
    return {int(key): value for key, value in data.items()}


def item_name(
    item: Item,
    dictionary: Dictionary,
    *,
    logger: Optional[logging.Logger] = None,
) -> Text:
    logger = logger or logging.getLogger(__name__)
    item_id = item["id"]
    if item_id not in dictionary["item"]:
        logger.warning("Item %d is not found in dictionary", item_id)
    return Text(
        jp=item["name"],
        en=dictionary["item"].get(item_id, item["name"]),
    )
