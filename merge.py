#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
from typing import Literal, Optional, TypedDict

import fgo


def main() -> None:
    # logger
    logger = create_logger()
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # items
    items = (
        fgo.load_items(
            pathlib.Path("data/items.json"),
            logger=logger,
        )
        or []
    )
    # servants
    servants = fgo.load_servants(
        pathlib.Path("data/servant/"),
        logger=logger,
    )
    # sounds
    sounds = load_sounds(
        pathlib.Path("data/sound.json"),
        logger=logger,
    )
    # dictionary
    dictionary = load_dictionary(logger)
    # merge
    merged_data = merge(items, servants, sounds, dictionary, logger)
    path = pathlib.Path("data/merged_data.json")
    logger.info('save merged data to "%s"', path)
    fgo.save_json(path, merged_data)


def create_logger() -> logging.Logger:
    logger = logging.getLogger("merge")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(name)s:%(levelname)s:%(message)s",
    )
    logger.addHandler(handler)
    return logger


@dataclasses.dataclass(frozen=True)
class Option:
    verbose: bool


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge item, servant, sound",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="set log level to debug",
    )
    return parser


def load_sounds(
    path: pathlib.Path,
    logger: logging.Logger,
) -> list[fgo.Sound]:
    logger.info('load sounds from "%s"', path)
    sounds = fgo.load_json(path)
    if sounds is None:
        logger.error('failed to load sournds from "%s"', path)
        return []
    return sounds


def load_dictionary(logger: logging.Logger) -> fgo.Dictionary:
    item = fgo.load_item_dictionary(
        pathlib.Path("data/english/item.json"),
        logger=logger,
    )
    servant = fgo.load_servant_dictionary(
        pathlib.Path("data/english/servant.json"),
        logger=logger,
    )
    return fgo.Dictionary(
        item=item or {},
        servant=servant or {},
    )


class Item(TypedDict):
    id: int
    rarity: str
    name: fgo.Text


class Skill(TypedDict):
    slot: int
    level: int
    name: fgo.Text
    rank: str
    icon: int


class ActiveSkills(TypedDict):
    skill_1: list[Skill]
    skill_2: list[Skill]
    skill_3: list[Skill]


class AppendSkills(TypedDict):
    skill_1: list[Skill]
    skill_2: list[Skill]
    skill_3: list[Skill]
    skill_4: list[Skill]
    skill_5: list[Skill]


class Costume(TypedDict):
    id: int
    name: fgo.Text
    resource: fgo.ResourceByID


class Servant(TypedDict):
    id: int
    name: fgo.Text
    false_name: Optional[fgo.Text]
    klass: str
    rarity: int
    skills: ActiveSkills
    append_skills: AppendSkills
    costumes: list[Costume]
    ascension_resources: list[fgo.ResourceByID]
    skill_resources: list[fgo.ResourceByID]
    append_skill_resources: list[fgo.ResourceByID]


class Sound(TypedDict):
    source: str
    index: int
    title: fgo.Text
    resource: fgo.ResourceByID


class MergedData(TypedDict):
    items: list[Item]
    servants: list[Servant]
    sounds: list[Sound]


def merge(
    items: list[fgo.Item],
    servants: list[fgo.Servant],
    sounds: list[fgo.Sound],
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> MergedData:
    # item name -> item id
    item_converter = fgo.ItemNameConverter(
        {item["name"]: item["id"] for item in items},
        default_id=0,
        logger=logger,
    )
    return MergedData(
        items=convert_items(
            items,
            dictionary,
            logger,
        ),
        servants=convert_servants(
            servants,
            item_converter,
            dictionary,
            logger,
        ),
        sounds=convert_sounds(
            sounds,
            item_converter,
            logger,
        ),
    )


def convert_items(
    items: list[fgo.Item],
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> list[Item]:
    return [convert_item(item, dictionary, logger) for item in items]


def convert_item(
    item: fgo.Item,
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> Item:
    return Item(
        id=item["id"],
        rarity=item["rarity"],
        name=get_item_text(item, dictionary, logger),
    )


def get_item_text(
    item: fgo.Item,
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> fgo.Text:
    if item["id"] not in dictionary["item"]:
        logger.warning("Item %d is not found in dictionary", item["id"])
    return fgo.Text(
        jp=item["name"],
        en=dictionary["item"].get(item["id"], item["name"]),
    )


def convert_servants(
    servants: list[fgo.Servant],
    items: fgo.ItemNameConverter,
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> list[Servant]:
    return [convert_servant(servant, items, dictionary, logger) for servant in servants]


def convert_servant(
    servant: fgo.Servant,
    items: fgo.ItemNameConverter,
    dictionary: fgo.Dictionary,
    logger: logging.Logger,
) -> Servant:
    servant_logger = fgo.ServantLogger(logger, servant["id"], servant["name"])
    servant_logger.info("start conversion")
    return Servant(
        id=servant["id"],
        name=servant_name(servant, dictionary),
        false_name=servant_false_name(servant, dictionary, servant_logger),
        klass=servant["klass"],
        rarity=servant["rarity"],
        skills=convert_active_skills(
            servant["skills"],
            dictionary,
            servant["id"],
            servant_logger,
        ),
        append_skills=convert_append_skills(
            servant["append_skills"],
            dictionary,
            servant["id"],
            servant_logger,
        ),
        costumes=convert_costumes(
            servant["costumes"],
            dictionary,
            servant["id"],
            items,
            servant_logger,
        ),
        ascension_resources=convert_resources(
            servant["ascension_resources"],
            items,
            servant_logger,
        ),
        skill_resources=convert_resources(
            servant["skill_resources"],
            items,
            servant_logger,
        ),
        append_skill_resources=convert_resources(
            servant["append_skill_resources"],
            items,
            servant_logger,
        ),
    )


def servant_name(
    servant: fgo.Servant,
    dictionary: fgo.Dictionary,
) -> fgo.Text:
    return fgo.Text(
        jp=servant["name"],
        en=dictionary["servant"][servant["id"]]["name"],
    )


def servant_false_name(
    servant: fgo.Servant,
    dictionary: fgo.Dictionary,
    logger: fgo.ServantLogger,
) -> Optional[fgo.Text]:
    false_name_jp = servant["false_name"]
    if false_name_jp is None:
        return None
    false_name_en = dictionary["servant"][servant["id"]]["false_name"]
    if false_name_en is None:
        logger.error("there is not false name in English")
        false_name_en = false_name_jp
    return fgo.Text(
        jp=false_name_jp,
        en=false_name_en,
    )


def convert_active_skills(
    skills: list[list[fgo.Skill]],
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    logger: fgo.ServantLogger,
) -> ActiveSkills:
    args = (dictionary, servant_id, logger)
    return ActiveSkills(
        skill_1=convert_skills("skills", skills[0], *args),
        skill_2=convert_skills("skills", skills[1], *args),
        skill_3=convert_skills("skills", skills[2], *args),
    )


def convert_append_skills(
    skills: list[list[fgo.Skill]],
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    logger: fgo.ServantLogger,
) -> AppendSkills:
    args = (dictionary, servant_id, logger)
    return AppendSkills(
        skill_1=convert_skills("append_skills", skills[0], *args),
        skill_2=convert_skills("append_skills", skills[1], *args),
        skill_3=convert_skills("append_skills", skills[2], *args),
        skill_4=convert_skills("append_skills", skills[3], *args),
        skill_5=convert_skills("append_skills", skills[4], *args),
    )


def convert_skills(
    mode: Literal["skills", "append_skills"],
    skills: list[fgo.Skill],
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    logger: fgo.ServantLogger,
) -> list[Skill]:
    return [
        convert_skill(mode, skill, dictionary, servant_id, logger) for skill in skills
    ]


def convert_skill(
    mode: Literal["skills", "append_skills"],
    skill: fgo.Skill,
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    logger: fgo.ServantLogger,
) -> Skill:
    return Skill(
        slot=skill["slot"],
        level=skill["level"],
        name=fgo.Text(
            jp=skill["name"],
            en=skill_name(mode, skill, dictionary["servant"][servant_id], logger),
        ),
        rank=skill["rank"],
        icon=skill["icon"],
    )


def skill_name(
    mode: Literal["skills", "append_skills"],
    skill: fgo.Skill,
    dictionary: fgo.ServantDictionaryValue,
    logger: fgo.ServantLogger,
) -> str:
    try:
        return dictionary[mode][skill["slot"] - 1][skill["level"] - 1]
    except IndexError:
        logger.error(
            "there is not %s skill(slot=%d, level=%d) in dictionary",
            mode,
            skill["slot"],
            skill["level"],
        )
        return skill["name"]


def convert_costumes(
    costumes: list[fgo.Costume],
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    items: fgo.ItemNameConverter,
    logger: fgo.ServantLogger,
) -> list[Costume]:
    return [
        convert_costume(i, costume, dictionary, servant_id, items, logger)
        for i, costume in enumerate(costumes)
    ]


def convert_costume(
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    index: int,
    costume: fgo.Costume,
    dictionary: fgo.Dictionary,
    servant_id: fgo.ServantID,
    items: fgo.ItemNameConverter,
    logger: fgo.ServantLogger,
) -> Costume:
    resource = items.resource(costume["resource"])
    if resource is None:
        logger.error('failed to convert resource: "%s"', resource)
        resource = fgo.ResourceByID(qp=0, items=[])
    return Costume(
        id=costume["id"],
        name=fgo.Text(
            jp=costume["name"],
            en=costume_name(index, costume, dictionary["servant"][servant_id], logger),
        ),
        resource=resource,
    )


def costume_name(
    index: int,
    costume: fgo.Costume,
    dictionary: fgo.ServantDictionaryValue,
    logger: fgo.ServantLogger,
) -> str:
    try:
        return dictionary["costumes"][index]
    except IndexError:
        logger.error("there is not costume %d in dictionary", index)
        return costume["name"]


def convert_resources(
    resources: list[fgo.Resource],
    item_conveter: fgo.ItemNameConverter,
    logger: fgo.ServantLogger,
) -> list[fgo.ResourceByID]:
    result: list[fgo.ResourceByID] = []
    for resource in resources:
        value = item_conveter.resource(resource)
        if value is None:
            logger.error('failed to convert resource: "%s"', resource)
            value = fgo.ResourceByID(qp=0, items=[])
        result.append(value)
    return result


def convert_sounds(
    sounds: list[fgo.Sound],
    items: fgo.ItemNameConverter,
    logger: logging.Logger,
) -> list[Sound]:
    return [convert_sound(sound, items, logger) for sound in sounds]


def convert_sound(
    sound: fgo.Sound,
    items: fgo.ItemNameConverter,
    logger: logging.Logger,
) -> Sound:
    resource = items.resource(sound["resource"])
    if resource is None:
        logger.error('failed to convert resource: "%s"', resource)
        resource = fgo.ResourceByID(qp=0, items=[])
    return Sound(
        source=sound["source"],
        index=sound["index"],
        title=fgo.Text(
            jp=sound["title"],
            en=sound["title"],
        ),
        resource=resource,
    )


if __name__ == "__main__":
    main()
