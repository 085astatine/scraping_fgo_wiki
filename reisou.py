#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import re
from typing import NamedTuple, List, Optional
import lxml.html
import requests


class Reisou(NamedTuple):
    id: int
    rarity: int
    name: str


def parse_row(
        row: lxml.html.HtmlElement,
        logger: Optional[logging.Logger] = None) -> List[Reisou]:
    logger = logger or logging.getLogger(__name__)
    result: List[Reisou] = []
    # id, rarity
    id_cell = row.xpath('td[1]')[0].text_content().strip()
    rarity_cell = row.xpath('td[2]')[0].text_content().strip()
    logger.debug('id, rarity: %s, %s', id_cell, rarity_cell)
    # id range
    id_range_match = re.match('(?P<begin>[0-9]+)-(?P<end>[0-9]+)', id_cell)
    if id_range_match:
        begin = int(id_range_match.group('begin'))
        end = int(id_range_match.group('end'))
        logger.debug('id range: %d - %d', begin, end)
    elif id_cell.isdigit():
        logger.debug('id: %d', int(id_cell))
        name = row.xpath('td[3]')[0].xpath('a')[0].text.strip()
        logger.info(
                'id=%d, rarity=%d, name="%s"',
                int(id_cell),
                int(rarity_cell),
                name)
        result.append(Reisou(
                id=int(id_cell),
                rarity=int(rarity_cell),
                name=name))
    else:
        logger.debug('this row is not target')
    return result


def main(logger: Optional[logging.Logger] = None):
    logger = logger or logging.getLogger(__name__)
    # reisou list
    reisou_list: List[Reisou] = []
    url = 'https://w.atwiki.jp/f_go/pages/32.html'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//*[@id="wikibody"]/div[3]/div/div/table/tbody/tr[td]'
    for row in root.xpath(xpath):
        reisou_list.extend(parse_row(row, logger))
    # write as csv
    with open('reisou.csv', mode='w') as csv:
        for reisou in reisou_list:
            csv.write('{0.id},{0.rarity},"{0.name}"\n'.format(reisou))


if __name__ == '__main__':
    logger = logging.getLogger('reisou')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
                fmt='%(name)s::%(levelname)s::%(message)s')
    logger.addHandler(handler)
    main(logger=logger)
