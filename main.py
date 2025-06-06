#!/usr/bin/env python

from __future__ import annotations

import argparse
import logging
import pathlib
from typing import Final

import lib

_REQUEST_INTERVAL: Final[float] = 2.0


def load_dict(
    path: pathlib.Path,
    *,
    force_update: bool = False,
) -> lib.Dictionary:
    # item
    item_path = path.joinpath("item.json")
    item_dict = lib.load_json(item_path)
    if item_dict is None or force_update:
        item_dict = lib.item_dict()
        lib.save_json(item_path, item_dict)
    # servant
    servant_path = path.joinpath("servant.json")
    servant_dict = lib.load_json(servant_path)
    if servant_dict is None or force_update:
        servant_dict = lib.servant_dict()
        lib.save_json(servant_path, servant_dict)
    # skill
    skill_path = path.joinpath("skill.json")
    skill_dict = lib.load_json(skill_path)
    if skill_dict is None or force_update:
        skill_dict = lib.skill_dict()
        lib.save_json(skill_path, skill_dict)
    return lib.Dictionary(
        item=item_dict,
        servant=servant_dict,
        skill=skill_dict,
    )


def load_items(path: pathlib.Path) -> list[lib.Item]:
    items = lib.load_json(path)
    if items is None:
        return []
    return items


def load_servants(
    path: pathlib.Path,
    *,
    force_update: bool = False,
    request_interval: float = _REQUEST_INTERVAL,
) -> list[lib.Servant]:
    return lib.servant_list(
        directory=path,
        force_update=force_update,
        request_interval=request_interval,
    )


def load_sounds(
    path: pathlib.Path,
    *,
    force_update: bool = False,
) -> list[lib.Sound]:
    sounds = lib.load_json(path)
    if sounds is None or force_update:
        sounds = lib.sound_list()
        lib.save_json(path, sounds)
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
        choices=["dict", "servant", "sound", "merge"],
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
    # item
    if option.mode in ["merge"]:
        logger.info("run: item")
        items = load_items(pathlib.Path("data/items.json"))
    # servant
    if option.mode in ["servant", "merge"]:
        logger.info("run: servant")
        servants = load_servants(
            pathlib.Path("data/servant/"),
            force_update=option.force,
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
        data = lib.merge(items, servants, sounds, dictionary)
        lib.save_json(pathlib.Path("data/master_data.json"), data)


if __name__ == "__main__":
    main()
