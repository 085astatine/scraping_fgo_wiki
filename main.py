#!/usr/bin/env python

from __future__ import annotations

import argparse
import logging
import pathlib
from typing import Final

import fgo

_REQUEST_INTERVAL: Final[float] = 2.0


def load_dict(
    path: pathlib.Path,
    *,
    force_update: bool = False,
) -> fgo.Dictionary:
    # item
    item = fgo.load_item_dictionary(pathlib.Path("data/english/item.json")) or {}
    # servant
    servant_path = path.joinpath("servant.json")
    servant_dict = fgo.load_json(servant_path)
    if servant_dict is None or force_update:
        servant_dict = fgo.servant_dict()
        fgo.save_json(servant_path, servant_dict)
    # skill
    skill_path = path.joinpath("skill.json")
    skill_dict = fgo.load_json(skill_path)
    if skill_dict is None or force_update:
        skill_dict = fgo.skill_dict()
        fgo.save_json(skill_path, skill_dict)
    return fgo.Dictionary(
        item=item,
        servant=servant_dict,
        skill=skill_dict,
    )


def load_sounds(
    path: pathlib.Path,
    *,
    force_update: bool = False,
) -> list[fgo.Sound]:
    sounds = fgo.load_json(path)
    if sounds is None or force_update:
        sounds = fgo.sound_list()
        fgo.save_json(path, sounds)
    return sounds


def main() -> None:
    # logger
    logger = logging.getLogger("lib")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s:%(levelname)s:%(message)s",
    )
    logger.addHandler(handler)
    # arg parser
    parser = argparse.ArgumentParser(description="Fate/Grand Order scrayping")
    parser.add_argument(
        "mode",
        choices=["dict", "sound", "merge"],
        help="scraping target",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="set log level to debug",
    )
    parser.add_argument(
        "-f",
        "--force",
        dest="force",
        action="store_true",
        help="force update",
    )
    parser.add_argument(
        "--request-interval",
        dest="request_interval",
        type=float,
        default=_REQUEST_INTERVAL,
        help="request intarval seconds (default: %(default)s)",
        metavar="SECONDS",
    )
    # option
    option = parser.parse_args()
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # dict
    if option.mode in ["dict", "merge"]:
        logger.info("run: dict")
        dictionary = load_dict(
            pathlib.Path("data/dictionary/"),
            force_update=option.force or option.mode == "dict",
        )
    # sound
    if option.mode in ["sound", "merge"]:
        logger.info("run: sound")
        sounds = load_sounds(
            pathlib.Path("data/sound.json"),
            force_update=option.force,
        )
    # master data
    if option.mode == "merge":
        logger.info("run: merge")
        items = fgo.load_items(pathlib.Path("data/items.json")) or []
        servants = fgo.load_servants(
            pathlib.Path("data/servant/"),
            logger=logger,
        )
        data = fgo.merge(items, servants, sounds, dictionary)
        fgo.save_json(pathlib.Path("data/master_data.json"), data)


if __name__ == "__main__":
    main()
