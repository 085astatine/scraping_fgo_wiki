# -*- coding: utf-8 -*-

import logging
from typing import Dict, List, Optional, TypedDict
from . import item
from . import servant
from . import text


_logger = logging.getLogger(__name__)


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
    spiritron_dresses: List[SpiritronDress]
    skills: Skills
    skill_resources: List[ResourceSet]


class MergedData(TypedDict):
    items: List[Item]
    servants: List[Servant]


def _convert_text(
        text_: str,
        dictionary: Dict[str, text.Text]) -> text.Text:
    if text_ not in dictionary:
        _logger.warning('"%s" is not found in dictionary data', text_)
    return dictionary.get(
            text_,
            text.Text(
                jp=text_,
                en=text_))


def _convert_item(
        item_: item.Item,
        dictionary: text.Dictionary) -> Item:
    return Item(
        id=item_['id'],
        rarity=item_['rarity'],
        name=_convert_text(item_['name'], dictionary['item']))


def _convert_skill(
        skill: servant.Skill,
        dictionary: text.Dictionary) -> Skill:
    return Skill(
            name=_convert_text(skill['name'], dictionary['skill']),
            rank=skill['rank'],
            icon=skill['icon'])


def _convert_skills(
        skills: servant.Skills,
        dictionary: text.Dictionary) -> Skills:
    return Skills(
        skill_1=[_convert_skill(skill, dictionary)
                 for skill in skills['skill_1']],
        skill_2=[_convert_skill(skill, dictionary)
                 for skill in skills['skill_2']],
        skill_3=[_convert_skill(skill, dictionary)
                 for skill in skills['skill_3']])


def _convert_resource(
        resource: servant.Resource,
        items: List[item.Item]) -> Resource:
    invalid_item_id = 0
    item_id = [item['id'] for item in items
               if item['name'] == resource['name']]
    if len(item_id) != 1:
        _logger.error('item ID is not found: name="%s"', resource['name'])
    return Resource(
            id=item_id[0] if len(item_id) == 1 else invalid_item_id,
            piece=resource['piece'])


def _convert_resource_set(
        resource_set: servant.ResourceSet,
        items: List[item.Item]) -> ResourceSet:
    return ResourceSet(
            qp=resource_set['qp'],
            resources=[_convert_resource(resource, items)
                       for resource in resource_set['resources']])


def _convert_spiritron_dress(
        spritron_dress: servant.SpiritronDress,
        items: List[item.Item]) -> SpiritronDress:
    return SpiritronDress(
            name=_convert_text(spritron_dress['name'], {}),
            resource=_convert_resource_set(spritron_dress['resource'], items))


def _convert_servant(
        servant_: servant.Servant,
        items: List[item.Item],
        dictionary: text.Dictionary) -> Servant:
    return Servant(
            id=servant_['id'],
            name=_convert_text(servant_['name'], dictionary['servant']),
            alias_name=(
                _convert_text(servant_['alias_name'], dictionary['servant'])
                if servant_['alias_name'] is not None else None),
            klass=servant_['klass'],
            rarity=servant_['rarity'],
            ascension=[
                _convert_resource_set(resource, items)
                for resource in servant_['ascension']],
            spiritron_dresses=[
                _convert_spiritron_dress(dress, items)
                for dress in servant_['spiritron_dresses']],
            skills=_convert_skills(servant_['skills'], dictionary),
            skill_resources=[
                _convert_resource_set(resource, items)
                for resource in servant_['skill_resources']])


def merge(
        items: List[item.Item],
        servants: List[servant.Servant],
        dictionary: text.Dictionary) -> MergedData:
    return MergedData(
        items=[_convert_item(item, dictionary) for item in items],
        servants=[_convert_servant(servant, items, dictionary)
                  for servant in servants])
