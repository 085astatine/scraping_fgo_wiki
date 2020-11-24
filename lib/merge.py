# -*- coding: utf-8 -*-

from typing import List, Optional, TypedDict
from . import item
from . import servant
from . import text


class Item(TypedDict):
    id: int
    rarity: str
    name: text.Text


class Skill(TypedDict):
    name: text.Text
    rank: str
    icon: int


class Skills(TypedDict):
    skill_1: List[Skill]
    skill_2: List[Skill]
    skill_3: List[Skill]


class Resource(TypedDict):
    id: int
    piece: int


class ResourceSet(TypedDict):
    qp: int
    resources: List[Resource]


class SpiritronDress(TypedDict):
    name: text.Text
    resource: ResourceSet


class Servant(TypedDict):
    id: int
    name: text.Text
    alias_name: Optional[text.Text]
    klass: str
    rarity: int
    ascension: List[ResourceSet]
    spiritron_dress: List[SpiritronDress]
    skills: Skills
    skill_reinforcement: List[ResourceSet]


class MergedData(TypedDict):
    items: List[Item]
    servants: List[Servant]


def merge(
        items: List[item.Item],
        servants: List[servant.Servant],
        dictionary: text.Dictionary) -> MergedData:
    return MergedData(
        items=[],
        servants=[])
