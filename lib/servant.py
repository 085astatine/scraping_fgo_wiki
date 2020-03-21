#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import time
from typing import List, NamedTuple, TypedDict
import lxml.html
import requests


_interval = 1.0

_logger = logging.getLogger(__name__)


class Resource(NamedTuple):
    name: str
    piece: int


class RequiredResource(NamedTuple):
    level: int
    resources: List[Resource]


_Servant = TypedDict(
        '_Servant',
        {'id': int,
         'class': str,
         'rarity': int,
         'name': str,
         'url': str,
         'skill_reinforcement': List[RequiredResource]},
        total=False)


class _RequiredResourceParser:
    def __init__(self) -> None:
        self._result: List[RequiredResource] = []
        self._level = 0
        self._next_level = 0
        self._resources: List[Resource] = []

    def push(self, cell: lxml.html.HtmlElement):
        text = cell.text_content().strip()
        if not text:
            return
        # level
        level_match = re.match(
                r'Lv(?P<privious>[0-9]+)→Lv(?P<next>[0-9]+)',
                text)
        if level_match:
            privious_level = int(level_match.group('privious'))
            next_level = int(level_match.group('next'))
            _logger.debug('Lv.%d -> Lv.%d', privious_level, next_level)
            assert privious_level == self._level + 1
            assert next_level == privious_level + 1
            if self._level != 0:
                self._pack()
            self._level = privious_level
            self._next_level = next_level
        else:
            resource_regexp = re.compile(
                    r'(?P<item>.+),(x|)(?P<piece>[0-9万]+)')
            resource_match = resource_regexp.search(text)
            while resource_match:
                resource = Resource(
                        name=resource_match.group('item'),
                        piece=int(resource_match.group('piece')
                                  .replace('万', '0000')))
                _logger.debug(
                        'resource %s x %d',
                        resource.name,
                        resource.piece)
                self._resources.append(resource)
                text = resource_regexp.sub('', text, count=1)
                resource_match = resource_regexp.search(text)

    def result(self) -> List[RequiredResource]:
        if self._level < self._next_level:
            self._pack()
        return self._result

    def _pack(self) -> None:
        self._result.append(RequiredResource(
                level=self._level,
                resources=self._resources))
        self._level = self._next_level
        self._resources = []


def _parse_servant_table():
    # URL: サーヴァント > 一覧 > 番号順
    url = 'https://w.atwiki.jp/f_go/pages/713.html'
    # 入手不可サーヴァントID
    ignore_servant_ids = (
            83,  # ソロモン
            149,  # ティアマト
            151,  # ゲーティア
            152,  # ソロモン
            168,  # ビーストIII/R
            240)  # ビーストIII/L
    # クラス変換
    to_servant_class = {
            '剣': 'Saber',  # セイバー
            '弓': 'Archer',  # アーチャー
            '槍': 'Lancer',  # ランサー
            '騎': 'Rider',  # ライダー
            '術': 'Caster',  # キャスター
            '殺': 'Assassin',  # アサシン
            '狂': 'Berserker',  # バーサーカー
            '盾': 'Shielder',  # シールダー
            '裁': 'Ruler',  # ルーラー
            '讐': 'Avenger',  # アヴェンジャー
            '分': 'AlterEgo',  # アルターエゴ
            '月': 'MoonCancer',  # ムーンキャンサー
            '降': 'Foreigner',  # フォーリナー
            '獣': 'Beast'}  # ビースト
    # access
    response = requests.get(url)
    etree = lxml.html.fromstring(response.text)
    xpath = ('/html/body//div[@id="wikibody"]/div[2]/div/'
             'table/tbody/tr[td]')
    # サーヴァントリスト作成
    result: List[_Servant] = []
    for row in etree.xpath(xpath):
        servant_id = int(row.xpath('td[1]')[0].text)
        if servant_id in ignore_servant_ids:
            continue
        rarity = int(row.xpath('td[2]')[0].text)
        servant_name = row.xpath('td[3]//a')[0].text
        servant_class = to_servant_class[row.xpath('td[4]')[0].text.strip()]
        servant_url = row.xpath('td[3]//a')[0].get('href')
        _logger.debug(
                'servant %d: %s, rarity:%d class:%s, url:%s',
                servant_id,
                servant_name,
                rarity,
                servant_class,
                servant_url)
        result.append({
                'id': servant_id,
                'name': servant_name,
                'class': servant_class,
                'rarity': rarity,
                'url': servant_url})
    return result


def _parse_servant_page(servant: _Servant):
    # access
    response = requests.get('https:{0}'.format(servant['url']))
    root = lxml.html.fromstring(response.text)
    # スキル強化
    servant['skill_reinforcement'] = _parse_skill_reinforcement(root)


def _parse_skill_reinforcement(
        root: lxml.html.HtmlElement) -> List[RequiredResource]:
    parser = _RequiredResourceParser()
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="スキル強化"]'
            '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    for row in root.xpath(xpath):
        for cell in row.xpath('td'):
            parser.push(cell)
    return parser.result()


def servant_list():
    result = _parse_servant_table()
    time.sleep(_interval)
    for servant in result:
        time.sleep(_interval)
        _parse_servant_page(servant)
