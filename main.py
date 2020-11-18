#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import pathlib
from typing import List
import lib


def load_items(
        path: pathlib.Path,
        *,
        force_update: bool = False) -> List[lib.Item]:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    if path.exists() and not force_update:
        with path.open() as item_file:
            items = json.load(item_file)
    else:
        items = lib.item_list()
        with path.open(mode='w') as item_file:
            json.dump(
                    items,
                    item_file,
                    ensure_ascii=False,
                    indent=2)
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
    # item
    if option.mode in ['item', 'merge']:
        items = load_items(
                pathlib.Path('data/items.json'),
                force_update=option.force or option.mode == 'item')
    # servant
    servant_path = pathlib.Path('data/servants.json')
    if not servant_path.parent.exists():
        servant_path.parent.mkdir(parents=True)
    if servant_path.exists() and not force_update:
        with servant_path.open() as servant_file:
            servants = json.load(servant_file)
    else:
        servants = lib.servant.servant_list(items)
        with servant_path.open(mode='w') as servant_file:
            json.dump(
                    servants,
                    servant_file,
                    ensure_ascii=False,
                    indent=2)
    # master data
    master_data_path = pathlib.Path('data/master_data.json')
    if not master_data_path.parent.exists():
        master_data_path.parent.mkdir(parents=True)
    master_data = {
            'items': items,
            'servants': servants}
    with master_data_path.open(mode='w') as master_data_file:
        json.dump(
                master_data,
                master_data_file,
                ensure_ascii=False,
                indent=2)


if __name__ == '__main__':
    main()
