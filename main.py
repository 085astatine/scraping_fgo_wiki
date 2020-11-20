#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import pathlib
from typing import Any, List
import lib


def save_json(
        path: pathlib.Path,
        data: Any) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with path.open(mode='w') as file:
        json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2)


def load_dict(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> lib.Dictionary:
    # item
    item_path = path.joinpath('item.json')
    if item_path.exists() and not force_update:
        with item_path.open() as item_file:
            item_dict = json.load(item_file)
    else:
        item_dict = lib.item_dict()
        save_json(item_path, item_dict)
    # servant
    servant_path = path.joinpath('servant.json')
    if servant_path.exists() and not force_update:
        with servant_path.open() as servant_file:
            servant_dict = json.load(servant_file)
    else:
        servant_dict = lib.servant_dict()
        save_json(servant_path, servant_dict)
    # skill
    skill_path = path.joinpath('skill.json')
    if skill_path.exists() and not force_update:
        with skill_path.open() as skill_file:
            skill_dict = json.load(skill_file)
    else:
        skill_dict = lib.skill_dict()
        save_json(skill_path, skill_dict)
    return {'item': item_dict,
            'servant': servant_dict,
            'skill': skill_dict}


def load_items(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> List[lib.Item]:
    if path.exists() and not force_update:
        with path.open() as item_file:
            items = json.load(item_file)
    else:
        items = lib.item_list()
        save_json(path, items)
    return items


def main():
    # logger
    logger = logging.getLogger('lib')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
                fmt='%(asctime)s %(name)s:%(levelname)s:%(message)s')
    logger.addHandler(handler)
    # arg parser
    parser = argparse.ArgumentParser(
            description='Fate/Grand Order scrayping')
    parser.add_argument(
            'mode',
            choices=['dict', 'item', 'servant', 'merge'],
            help='scraping target')
    parser.add_argument(
            '-v', '--verbose',
            dest='verbose',
            action='store_true',
            help='set log level to debug')
    parser.add_argument(
            '-f', '--force',
            dest='force',
            action='store_true',
            help='force update')
    # option
    option = parser.parse_args()
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug('option: %s', option)
    force_update = option.force
    # dict
    if option.mode in ['dict', 'merge']:
        dictionary = load_dict(
                pathlib.Path('data/dictionary/'),
                force_update=option.force or option.mode == 'dict')
    # item
    if option.mode in ['item', 'merge']:
        items = load_items(
                pathlib.Path('data/items.json'),
                force_update=option.force or option.mode == 'item')
    # servant
    servant_path = pathlib.Path('data/servants.json')
    if servant_path.exists() and not force_update:
        with servant_path.open() as servant_file:
            servants = json.load(servant_file)
    else:
        servants = lib.servant.servant_list(items)
        save_json(servant_path, servants)
    # master data
    master_data_path = pathlib.Path('data/master_data.json')
    master_data = {
            'items': items,
            'servants': servants}
    save_json(master_data_path, master_data)


if __name__ == '__main__':
    main()
