#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import re
import time
from typing import NamedTuple, List, Optional
import lxml.html
import requests


class CraftEssence(NamedTuple):
    id: int
    rarity: int
    name: str


def parse_row(
        row: lxml.html.HtmlElement,
        logger: Optional[logging.Logger] = None) -> Optional[CraftEssence]:
    logger = logger or logging.getLogger(__name__)
    cells = row.xpath('td')
    # id, rarity
    id_cell = cells[0].text_content().strip()
    rarity_cell = cells[1].text_content().strip()
    logger.debug('id, rarity: %s, %s', id_cell, rarity_cell)
    # id range
    id_range_match = re.match('(?P<begin>[0-9]+)-(?P<end>[0-9]+)', id_cell)
    if id_range_match:
        logger.debug(
                'id range: %d - %d',
                int(id_range_match.group('begin')),
                int(id_range_match.group('end')))
    elif id_cell.isdigit():
        logger.debug('id: %d', int(id_cell))
        name = cells[2].text_content().strip()
        result = CraftEssence(
                id=int(id_cell),
                rarity=int(rarity_cell),
                name=name)
        logger.debug('parse row: %s', result)
        return result
    logger.debug('this row is not target')
    return None


def parse_bond_craft_essences(
        logger: Optional[logging.Logger]) -> List[CraftEssence]:
    logger = logger or logging.getLogger(__name__)
    result: List[CraftEssence] = []
    url = 'https://w.atwiki.jp/f_go/pages/1106.html'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//*[@id="wikibody"]/div[3]/div/div/table/tbody/tr[td]'
    for row in root.xpath(xpath):
        cells = row.xpath('td')
        if not cells[4].text.strip().isdigit():
            continue
        # servant
        servant_id = int(cells[0].text)
        servant_name = cells[2].xpath('a')[0].text
        logger.debug('servant: No.%03d %s', servant_id, servant_name)
        # craft essence
        craft_essence_id = int(cells[4].text)
        craft_essence_rarity = 4
        craft_essence_name = cells[5].xpath('a')[0].text
        logger.info(
                'id=%d, rarity=%d, name="%s"',
                craft_essence_id,
                craft_essence_rarity,
                craft_essence_name)
        result.append(CraftEssence(
                id=craft_essence_id,
                rarity=craft_essence_rarity,
                name=craft_essence_name))
        logger.info('bond: %s', result[-1])
    return result


def main(logger: Optional[logging.Logger] = None):
    logger = logger or logging.getLogger(__name__)
    sleep = 1.0
    craft_essences: List[CraftEssence] = []
    # bond craft essences
    craft_essences.extend(parse_bond_craft_essences(logger=logger))
    time.sleep(sleep)
    # normal craft essence
    url = 'https://w.atwiki.jp/f_go/pages/32.html'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//*[@id="wikibody"]/div[3]/div/div/table/tbody/tr[td]'
    for row in root.xpath(xpath):
        craft_essence = parse_row(row, logger)
        if craft_essence is not None:
            if not any(x.id == craft_essence.id for x in craft_essences):
                craft_essences.append(craft_essence)
                logger.info('normal: %s', craft_essence)
            else:
                logger.debug('duplicated: %s', craft_essence)
    # sort by id
    craft_essences.sort(key=lambda x: x.id)
    # write as csv
    with open('craft_essences.csv', mode='w') as csv:
        for craft_essence in craft_essences:
            csv.write('{0.id},{0.rarity},"{0.name}"\n'.format(craft_essence))


if __name__ == '__main__':
    logger = logging.getLogger('craft_essence')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
                fmt='%(name)s::%(levelname)s::%(message)s')
    logger.addHandler(handler)
    main(logger=logger)
