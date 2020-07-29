# -*- coding: utf-8 -*-

import logging
from typing import List, TypedDict
import lxml.html
import requests
from .text import Text


_logger = logging.getLogger(__name__)


Item = TypedDict(
    'Item',
    {'id': int,
     'rarity': str,
     'name': Text})


def item_list() -> List[Item]:
    url = 'https://grandorder.wiki/Items'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = (
            '//h2[span[normalize-space()="Item List"]]'
            '/following-sibling::table//tr[td]')
    target_item_types = ['Ascension', 'Skill']
    result: List[Item] = []
    for row in root.xpath(xpath):
        item_type = row.xpath('td[4]')[0].text.strip()
        if not any(map(lambda x: x in item_type, target_item_types)):
            continue
        item_id = int(row.xpath('td[1]')[0].text)
        name_cell = row.xpath('td[3]')[0]
        name_jp = name_cell.xpath('br/following-sibling::text()')[0].strip()
        name_en = name_cell.xpath('a')[0].text.strip()
        icon_cell = row.xpath('td[2]')[0]
        rarity = row.xpath('td[2]/div')[0].get('class').replace('itembox', '')
        if rarity not in ['Bronze', 'Silver', 'Gold']:
            _logger.error(
                    'item %d: %s(%s) has unknown ratiry "%s"',
                    item_id,
                    name_jp,
                    name_en,
                    rarity)
        _logger.debug(
                'item %d: %s(%s) rarity:%s, type:%s',
                item_id,
                name_jp,
                name_en,
                rarity,
                item_type)
        result.append({
                'id': item_id,
                'rarity': rarity,
                'name': {
                    'jp': name_jp,
                    'en': name_en}})
    return result
