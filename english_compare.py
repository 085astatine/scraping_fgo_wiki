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
    compare_servants(en_servants, jp_servants, logger)


def create_logger() -> logging.Logger:
    logger = logging.getLogger("english_servant")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s:%(levelname)s:%(message)s",
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
    en: dict[lib.ServantID, lib.english.Servant],
    jp: dict[lib.ServantID, lib.Servant],
    logger: logging.Logger,
) -> None:
    for servant_id, jp_servant in jp.items():
        servant_logger = lib.ServantLogger(logger, servant_id, jp_servant["name"])
        servant_logger.debug("start comparing")
        en_servant = en.get(servant_id, None)
        if en_servant is not None:
            compare_servant(en_servant, jp_servant, servant_logger)
        else:
            servant_logger.error("does not exits in English")


def compare_servant(
    en: lib.english.Servant,
    jp: lib.Servant,
    logger: lib.ServantLogger,
) -> None:
    # id
    if en["id"] != jp["id"]:
        logger.error("servant IDs do not match")
    # false name
    if en["false_name"] is not None:
        if jp["false_name"] is None:
            logger.error("only English has an false name")
    else:
        if jp["false_name"] is not None:
            logger.error("only Japanese has an false name")
    # active skills
    compare_skills("skill", en["active_skills"], jp["skills"], logger)
    # append skills
    compare_skills("append skill", en["append_skills"], jp["append_skills"], logger)


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


if __name__ == "__main__":
    main()
