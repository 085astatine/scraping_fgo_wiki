from __future__ import annotations

from typing import Optional, TypedDict


class Item(TypedDict):
    id: int
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


class Resource(TypedDict):
    name: str
    piece: int


class ResourceSet(TypedDict):
    qp: int
    resources: list[Resource]


class Costume(TypedDict):
    id: int
    name: str
    resource: ResourceSet


class Servant(TypedDict):
    id: int
    name: str
    alias_name: Optional[str]
    klass: str
    rarity: int
    skills: Skills
    append_skills: AppendSkills
    costumes: list[Costume]
    ascension_resources: list[ResourceSet]
    skill_resources: list[ResourceSet]
    append_skill_resources: list[ResourceSet]
