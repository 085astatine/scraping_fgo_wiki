#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib

import lib
import lib.english


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("english_compare")
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # load english items
    en_items = lib.load_item_dictionary(
        pathlib.Path("data/english/item.json"),
        logger=logger,
    )
    if en_items is None:
        return
    # load english servants
    en_servants: dict[lib.ServantID, lib.english.Servant] = {
        servant["id"]: servant
        for servant in lib.english.load_servants(
            pathlib.Path("data/english/servant"),
            logger=logger,
        )
    }
    # load japanese items
    jp_items = lib.load_items(
        pathlib.Path("data/items.json"),
        logger=logger,
    )
    if jp_items is None:
        return
    # load japanese servants
    jp_servants: dict[lib.ServantID, lib.Servant] = {
        servant["id"]: servant
        for servant in lib.load_servants(
            pathlib.Path("data/servant"),
            logger=logger,
        )
    }
    # compare items
    compare_items(en_items, jp_items, logger)
    # compare servants
    compare_servants(
        en_servants,
        {value: key for key, value in en_items.items()},
        jp_servants,
        {item["name"]: item["id"] for item in jp_items},
        logger,
    )


def create_logger() -> logging.Logger:
    logger = logging.getLogger("english_servant")
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
        description="Compare English Data with Japanese Data",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="set log level to debug",
    )
    return parser


def compare_items(
    en_items: lib.ItemDictionary,
    jp_items: list[lib.Item],
    logger: logging.Logger,
) -> None:
    en_item_ids = set(en_items.keys())
    jp_item_ids = set(jp_item["id"] for jp_item in jp_items)
    en_only_item_ids = en_item_ids - jp_item_ids
    if en_only_item_ids:
        logger.error(
            "item IDs (%s) are only in English",
            ", ".join(str(item_id) for item_id in en_only_item_ids),
        )
    jp_only_item_ids = jp_item_ids - en_item_ids
    if jp_only_item_ids:
        logger.error(
            "item IDs (%s) are only in Japanse",
            ", ".join(str(item_id) for item_id in jp_only_item_ids),
        )


def compare_servants(
    en_servants: dict[lib.ServantID, lib.english.Servant],
    en_items: dict[str, lib.ItemID],
    jp_servants: dict[lib.ServantID, lib.Servant],
    jp_items: dict[str, lib.ItemID],
    logger: logging.Logger,
) -> None:
    for servant_id, jp_servant in jp_servants.items():
        servant_logger = lib.ServantLogger(logger, servant_id, jp_servant["name"])
        servant_logger.debug("start comparing")
        en_servant = en_servants.get(servant_id, None)
        if en_servant is not None:
            compare_servant(
                en_servant,
                lib.ItemNameConverter(
                    en_items,
                    logger=servant_logger,
                ),
                jp_servant,
                lib.ItemNameConverter(
                    jp_items,
                    logger=servant_logger,
                ),
                servant_logger,
            )
        else:
            servant_logger.error("does not exits in English")


def compare_servant(
    en_servant: lib.english.Servant,
    en_items: lib.ItemNameConverter,
    jp_servant: lib.Servant,
    jp_items: lib.ItemNameConverter,
    logger: lib.ServantLogger,
) -> None:
    logger.info("start comparing")
    # id
    if en_servant["id"] != jp_servant["id"]:
        logger.error("servant IDs do not match")
    # false name
    if en_servant["false_name"] is not None:
        if jp_servant["false_name"] is None:
            logger.error("only English has an false name")
    else:
        if jp_servant["false_name"] is not None:
            logger.error("only Japanese has an false name")
    # class
    if en_servant["klass"] != jp_servant["klass"]:
        logger.error(
            'klass is different: en="%s", jp="%s"',
            en_servant["klass"],
            jp_servant["klass"],
        )
    # rarity
    if en_servant["rarity"] != jp_servant["rarity"]:
        logger.error(
            "rarity is different: en=%d, jp=%d",
            en_servant["rarity"],
            jp_servant["rarity"],
        )
    # active skills
    compare_skills(
        "skill",
        en_servant["active_skills"],
        jp_servant["skills"],
        logger,
    )
    # append skills
    compare_skills(
        "append_skill",
        en_servant["append_skills"],
        jp_servant["append_skills"],
        logger,
    )
    # ascension resources
    compare_resources(
        "ascension_resource",
        en_servant["ascension_resources"],
        en_items,
        jp_servant["ascension_resources"],
        jp_items,
        logger,
    )
    # active skill resources
    compare_resources(
        "active_skill_resources",
        en_servant["active_skill_resources"],
        en_items,
        jp_servant["skill_resources"],
        jp_items,
        logger,
    )
    # append skill resources
    compare_resources(
        "append_skill_resources",
        en_servant["append_skill_resources"],
        en_items,
        jp_servant["append_skill_resources"],
        jp_items,
        logger,
    )


def compare_skills(
    target: str,
    en: list[list[lib.english.Skill]],
    jp: list[list[lib.Skill]],
    logger: lib.ServantLogger,
) -> None:
    # slots
    if len(en) != len(jp):
        logger.error(
            "%s: slots don't match (en:%d, jp:%d)",
            target,
            len(en),
            len(jp),
        )
    # skill
    slots = len(en)
    for i in range(slots):
        compare_skill(f"{target} {i+1}", en[i], jp[i], logger)


def compare_skill(
    target: str,
    en: list[lib.english.Skill],
    jp: list[lib.Skill],
    logger: lib.ServantLogger,
) -> None:
    # levels
    if len(en) != len(jp):
        logger.error(
            "%s: levels don't match (en:%d, jp:%d)",
            target,
            len(en),
            len(jp),
        )
        return
    # rank
    levels = len(en)
    for i in range(levels):
        if en[i]["rank"] != jp[i]["rank"]:
            logger.error(
                '%s: rank don\'t match at level %d (en:"%s", jp:"%s")',
                f"{target}-{i+1}",
                i,
                en[i]["rank"],
                jp[i]["rank"],
            )


def compare_resources(
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    target: str,
    en_resources: list[lib.Resource],
    en_items: lib.ItemNameConverter,
    jp_resources: list[lib.Resource],
    jp_items: lib.ItemNameConverter,
    logger: lib.ServantLogger,
) -> None:
    # length
    if len(en_resources) != len(jp_resources):
        logger.error("[%s] different length", target)
    # element
    for i, (en_resource, jp_resource) in enumerate(zip(en_resources, jp_resources)):
        compare_resource(
            f"{target}-{i}",
            en_resource,
            en_items,
            jp_resource,
            jp_items,
            logger,
        )


def compare_resource(
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    target: str,
    en_resource: lib.Resource,
    en_items: lib.ItemNameConverter,
    jp_resource: lib.Resource,
    jp_items: lib.ItemNameConverter,
    logger: lib.ServantLogger,
) -> None:
    en = en_items.resource(en_resource)
    jp = jp_items.resource(jp_resource)
    if en is None:
        logger.error(
            '[%s] failed to convert english resource: "%s"',
            target,
            en_resource,
        )
    if jp is None:
        logger.error(
            '[%s] failed to convet japanese resource: "%s"',
            target,
            jp_resource,
        )
    if en is not None and jp is not None and en != jp:
        en_sorted = sorted_resource(en)
        jp_sorted = sorted_resource(jp)
        if en_sorted == jp_sorted:
            logger.warning("[%s] items are in a differenct order", target)
        else:
            logger.error(
                '[%s] resource is diffrent: en="%s", jp="%s"',
                target,
                en_resource,
                jp_resource,
            )


def sorted_resource(resource: lib.ResourceByID) -> lib.ResourceByID:
    return lib.ResourceByID(
        qp=resource["qp"],
        items=sorted(resource["items"], key=lambda item: item["id"]),
    )


if __name__ == "__main__":
    main()
