# -*- coding: utf-8 -*-

from typing import Dict, TypedDict


class Text(TypedDict):
    jp: str
    en: str


class Dictionary(TypedDict):
    item: Dict[str, Text]
    servant: Dict[str, Text]
    skill: Dict[str, Text]
