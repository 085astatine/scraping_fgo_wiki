from typing import TypedDict


class Text(TypedDict):
    jp: str
    en: str


class Dictionary(TypedDict):
    item: dict[str, Text]
    servant: dict[str, Text]
    skill: dict[str, Text]
