from __future__ import annotations

from typing import Optional, TypedDict

from ..types import Resource, ServantID


class Skill(TypedDict):
    name: str
    rank: str


class Costume(TypedDict):
    name: str
    text_jp: str
    text_en: str
    resources: Resource


class Servant(TypedDict):
    id: ServantID
    name: str
    false_name: Optional[str]
    klass: str
    rarity: int
    active_skills: list[list[Skill]]
    append_skills: list[list[Skill]]
    costumes: list[Costume]
    ascension_resources: list[Resource]
    active_skill_resources: list[Resource]
    append_skill_resources: list[Resource]


class ServantLink(TypedDict):
    id: ServantID
    url: str
    title: str
