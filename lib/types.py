from __future__ import annotations

from typing import NotRequired, Optional, TypedDict

type ItemID = int  # pylint: disable=invalid-name
type ServantID = int  # pylint: disable=invalid-name
type CostumeID = int  # pylint: disable=invalid-name


class Item(TypedDict):
    id: ItemID
    rarity: str
    name: str


class Skill(TypedDict):
    slot: int
    level: int
    name: str
    rank: str
    icon: int


type Skills = list[list[Skill]]
type AppendSkills = list[list[Skill]]


class Items(TypedDict):
    name: str
    piece: int


class Resource(TypedDict):
    qp: int
    resources: list[Items]


class ItemsByID(TypedDict):
    id: ItemID
    piece: int


class ResourceByID(TypedDict):
    qp: int
    items: list[ItemsByID]


class Costume(TypedDict):
    id: CostumeID
    name: str
    resource: Resource


class Servant(TypedDict):
    id: ServantID
    name: str
    false_name: Optional[str]
    ascension_names: Optional[list[str]]
    klass: str
    rarity: int
    skills: Skills
    append_skills: AppendSkills
    costumes: list[Costume]
    ascension_resources: list[Resource]
    skill_resources: list[Resource]
    append_skill_resources: list[Resource]


class ServantLink(TypedDict):
    id: ServantID
    klass: str
    rarity: int
    name: str
    url: str


class ServantName(TypedDict):
    id: ServantID
    name: NotRequired[str]
    false_name: NotRequired[str]
    ascension_names: NotRequired[list[str]]


class CostumeData(TypedDict):
    costume_id: CostumeID
    servant_id: ServantID
    name: str
    flavor_text: str
    resource: Resource


class Text(TypedDict):
    jp: str
    en: str


type ItemDictionary = dict[ItemID, str]


class ServantDictionaryValue(TypedDict):
    name: str
    false_name: Optional[str]
    skills: list[list[str]]
    append_skills: list[list[str]]


type ServantDictionary = dict[ServantID, ServantDictionaryValue]


class Dictionary(TypedDict):
    item: ItemDictionary
    servant: dict[str, Text]
    skill: dict[str, Text]
