from __future__ import annotations

from typing import Literal, Optional, TypedDict

from ..types import CostumeID, Resource, ServantID

# pylint: disable=duplicate-code
type CostumeType = Literal["full", "simple"]


class Text(TypedDict):
    en: str
    jp: str


class Skill(TypedDict):
    name: str
    rank: str


class Costume(TypedDict):
    name: str
    text_jp: str
    text_en: str
    resource: Resource


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


class CostumeData(TypedDict):
    costume_id: CostumeID
    costume_type: CostumeType
    servant: str
    stage: str
    name: Text
    resource: Resource
