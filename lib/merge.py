from __future__ import annotations

import logging
from typing import Optional, TypedDict

from . import sound, text, types

# pylint: disable=duplicate-code
_logger = logging.getLogger(__name__)


class Item(TypedDict):
    id: int
    rarity: str
    name: types.Text


class Skill(TypedDict):
    slot: int
    level: int
    name: types.Text
    rank: str
    icon: int


type Skills = list[list[Skill]]
type AppendSkills = list[list[Skill]]


class Resource(TypedDict):
    id: int
    piece: int


class ResourceSet(TypedDict):
    qp: int
    resources: list[Resource]


class Costume(TypedDict):
    id: int
    name: types.Text
    resource: ResourceSet


class Servant(TypedDict):
    id: int
    name: types.Text
    alias_name: Optional[types.Text]
    klass: str
    rarity: int
    skills: Skills
    append_skills: AppendSkills
    costumes: list[Costume]
    ascension_resources: list[ResourceSet]
    skill_resources: list[ResourceSet]
    append_skill_resources: list[ResourceSet]


class Sound(TypedDict):
    source: str
    index: int
    title: types.Text
    resource: ResourceSet


class MergedData(TypedDict):
    items: list[Item]
    servants: list[Servant]
    sounds: list[Sound]


def _convert_text(
    text_: str,
    dictionary: dict[str, types.Text],
) -> types.Text:
    if text_ not in dictionary:
        _logger.warning('"%s" is not found in dictionary data', text_)
    return dictionary.get(text_, types.Text(jp=text_, en=text_))


def _convert_item(
    item: types.Item,
    dictionary: types.Dictionary,
    logger: logging.Logger,
) -> Item:
    return Item(
        id=item["id"],
        rarity=item["rarity"],
        name=text.item_name(item, dictionary, logger=logger),
    )


def _convert_skill(
    skill: types.Skill,
    dictionary: types.Dictionary,
) -> Skill:
    return Skill(
        slot=skill["slot"],
        level=skill["level"],
        name=_convert_text(skill["name"], dictionary["skill"]),
        rank=skill["rank"],
        icon=skill["icon"],
    )


def _convert_skills(
    skills: types.Skills,
    dictionary: types.Dictionary,
) -> Skills:
    return [
        [_convert_skill(skill, dictionary) for skill in skill_n] for skill_n in skills
    ]


def _convert_append_skills(
    skills: types.AppendSkills,
    dictionary: types.Dictionary,
) -> AppendSkills:
    return [
        [_convert_skill(skill, dictionary) for skill in skill_n] for skill_n in skills
    ]


def _convert_resource(
    resource: types.Resource,
    items: list[types.Item],
) -> Resource:
    invalid_item_id = 0
    item_id = [item["id"] for item in items if item["name"] == resource["name"]]
    if len(item_id) != 1:
        _logger.error('item ID is not found: name="%s"', resource["name"])
    return Resource(
        id=item_id[0] if len(item_id) == 1 else invalid_item_id, piece=resource["piece"]
    )


def _convert_resource_set(
    resource_set: types.ResourceSet,
    items: list[types.Item],
) -> ResourceSet:
    return ResourceSet(
        qp=resource_set["qp"],
        resources=[
            _convert_resource(resource, items) for resource in resource_set["resources"]
        ],
    )


def _convert_costume(
    costume: types.Costume,
    items: list[types.Item],
) -> Costume:
    return Costume(
        id=costume["id"],
        name=_convert_text(costume["name"], {}),
        resource=_convert_resource_set(costume["resource"], items),
    )


def _convert_servant(
    servant_: types.Servant,
    items: list[types.Item],
    dictionary: types.Dictionary,
) -> Servant:
    return Servant(
        id=servant_["id"],
        name=_convert_text(servant_["name"], dictionary["servant"]),
        alias_name=(
            _convert_text(servant_["false_name"], dictionary["servant"])
            if servant_["false_name"] is not None
            else None
        ),
        klass=servant_["klass"],
        rarity=servant_["rarity"],
        skills=_convert_skills(servant_["skills"], dictionary),
        append_skills=_convert_append_skills(servant_["append_skills"], dictionary),
        costumes=[_convert_costume(costume, items) for costume in servant_["costumes"]],
        ascension_resources=[
            _convert_resource_set(resource, items)
            for resource in servant_["ascension_resources"]
        ],
        skill_resources=[
            _convert_resource_set(resource, items)
            for resource in servant_["skill_resources"]
        ],
        append_skill_resources=[
            _convert_resource_set(resource, items)
            for resource in servant_["append_skill_resources"]
        ],
    )


def _convert_sound(
    sound_: sound.Sound,
    items: list[types.Item],
) -> Sound:
    return Sound(
        source=sound_["source"],
        index=sound_["index"],
        title=_convert_text(sound_["title"], {}),
        resource=_convert_resource_set(sound_["resource"], items),
    )


def merge(
    items: list[types.Item],
    servants: list[types.Servant],
    sounds: list[sound.Sound],
    dictionary: types.Dictionary,
) -> MergedData:
    return MergedData(
        items=[_convert_item(item, dictionary, _logger) for item in items],
        servants=[_convert_servant(servant, items, dictionary) for servant in servants],
        sounds=[_convert_sound(sound, items) for sound in sounds],
    )
