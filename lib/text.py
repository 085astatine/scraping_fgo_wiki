from __future__ import annotations

import pathlib
from typing import TypedDict

from .io import load_json
from .types import ItemDictionary


class Text(TypedDict):
    jp: str
    en: str


class Dictionary(TypedDict):
    item: ItemDictionary
    servant: dict[str, Text]
    skill: dict[str, Text]


def load_item_dictionary(path: pathlib.Path) -> ItemDictionary:
    data = load_json(path)
    if data is None:
        return {}
    return {int(key): value for key, value in data.items()}
