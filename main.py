#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import pathlib
from typing import List
import lib


def load_dict(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> lib.Dictionary:
    # item
    item_path = path.joinpath('item.json')
    item_dict = lib.load_json(item_path)
    if item_dict is None or force_update:
        item_dict = lib.item_dict()
        lib.save_json(item_path, item_dict)
    # servant
    servant_path = path.joinpath('servant.json')
    servant_dict = lib.load_json(servant_path)
    if servant_dict is None or force_update:
        servant_dict = lib.servant_dict()
        lib.save_json(servant_path, servant_dict)
    # skill
    skill_path = path.joinpath('skill.json')
    skill_dict = lib.load_json(skill_path)
    if skill_dict is None or force_update:
        skill_dict = lib.skill_dict()
        lib.save_json(skill_path, skill_dict)
    return lib.Dictionary(
            item=item_dict,
            servant=servant_dict,
            skill=skill_dict)


def load_items(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> List[lib.Item]:
    items = lib.load_json(path)
    if items is None or force_update:
        items = lib.item_list()
        lib.save_json(path, items)
    return items


def load_servants(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> List[lib.Servant]:
    return lib.servant_list(
            directory=path,
            force_update=force_update)


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
    # dict
    if option.mode in ['dict', 'merge']:
        logger.info('run: dict')
        dictionary = load_dict(
                pathlib.Path('data/dictionary/'),
                force_update=option.force or option.mode == 'dict')
    # item
    if option.mode in ['item', 'merge']:
        logger.info('run: item')
        items = load_items(
                pathlib.Path('data/items.json'),
                force_update=option.force or option.mode == 'item')
    # servant
    if option.mode in ['servant', 'merge']:
        logger.info('run: servant')
        servants = load_servants(
                pathlib.Path('data/servant/'),
                force_update=option.force)
    # master data
    master_data_path = pathlib.Path('data/master_data.json')
    master_data = {
            'items': items,
            'servants': servants}
    lib.save_json(master_data_path, master_data)


if __name__ == '__main__':
    main()
