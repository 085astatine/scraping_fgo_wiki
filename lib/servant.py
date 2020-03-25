#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import enum
import logging
import re
import time
from typing import Dict, List, NamedTuple, Optional, Tuple, TypedDict
import lxml.html
import requests
from .item import Item
from .text import Text


_interval = 1.0

_logger = logging.getLogger(__name__)


Skill = TypedDict(
        'Skill',
        {'order': int,
         'is_upgraded': bool,
         'name': Text,
         'rank': str,
         'icon': int})


Resource = TypedDict(
        'Resource',
        {'id': int,
         'piece': int})


RequiredResource = TypedDict(
        'RequiredResource',
        {'qp': int,
         'resources': List[Resource]})


SpiritronDress = TypedDict(
        'SpiritronDress',
        {'name': Text,
         'required': RequiredResource})


Servant = TypedDict(
        'Servant',
        {'id': int,
         'name': Text,
         'class': str,
         'rarity': int,
         'ascension': List[RequiredResource],
         'spiritron_dress': List[SpiritronDress],
         'skill': List[Skill],
         'skill_reinforcement': List[RequiredResource]})


class _Skill(NamedTuple):
    order: int
    is_upgraded: bool
    name: str
    rank: str
    icon: int

    def normalize(self, translator: Dict[str, str]) -> Skill:
        if self.name not in translator:
            _logger.error('Skill name %s is not found', self.name)
        return {'order': self.order,
                'is_upgraded': self.is_upgraded,
                'name': {
                    'jp': self.name,
                    'en': translator.get(self.name, self.name)},
                'rank': self.rank,
                'icon': self.icon}


class _Resource(NamedTuple):
    name: str
    piece: int

    def normalize(self, items: List[Item]) -> Resource:
        item_id = [item['id'] for item in items
                   if item['name']['jp'] == self.name]
        if len(item_id) != 1:
            _logger.error('item ID error: %s', self.name)
        return {'id': item_id[0] if item_id else 0,
                'piece': self.piece}


class _RequiredResource(NamedTuple):
    level: int
    resources: List[_Resource]

    def normalize(self, items: List[Item]) -> RequiredResource:
        qp = 0
        resources: List[Resource] = []
        for resource in self.resources:
            if resource.name == 'QP':
                qp = resource.piece
            else:
                resources.append(resource.normalize(items))
        return {'qp': qp,
                'resources': resources}


class _SpiritronDress(NamedTuple):
    name: str
    resources: List[_Resource]

    def normalize(self, items: List[Item]) -> SpiritronDress:
        qp = 0
        resources: List[Resource] = []
        for resource in self.resources:
            if resource.name == 'QP':
                qp = resource.piece
            else:
                resources.append(resource.normalize(items))
        return {'name': {
                    'jp': self.name,
                    'en': self.name},
                'required': {
                    'qp': qp,
                    'resources': resources}}


_Servant = TypedDict(
        '_Servant',
        {'id': int,
         'class': str,
         'rarity': int,
         'name_jp': str,
         'name_en': str,
         'url': str,
         'ascension': List[_RequiredResource],
         'spiritron_dress': List[_SpiritronDress],
         'skill': List[_Skill],
         'skill_reinforcement': List[_RequiredResource]},
        total=False)


class _RequiredResourceParserMode(enum.Enum):
    ASCENSION = enum.auto()
    SKILL_REINFORCEMENT = enum.auto()


class _RequiredResourceParser:
    def __init__(self, mode: _RequiredResourceParserMode) -> None:
        self._mode = mode
        self._result: List[_RequiredResource] = []
        self._level = 0
        self._next_level = 0
        self._resources: List[_Resource] = []

    def push(self, cell: lxml.html.HtmlElement):
        text = cell.text_content().strip()
        if not text:
            return
        # level
        if self._parse_level(text):
            return
        # resource
        self._resources.extend(_parse_resource(text))

    def result(self) -> List[_RequiredResource]:
        if self._level < self._next_level:
            self._pack()
        return self._result

    def _pack(self) -> None:
        self._result.append(_RequiredResource(
                level=self._level,
                resources=self._resources))
        self._level = self._next_level
        self._resources = []

    def _parse_level(self, text) -> bool:
        levels: Optional[Tuple[int, int]] = None
        # parse
        Mode = _RequiredResourceParserMode
        if self._mode is Mode.ASCENSION:
            levels = _parse_ascension_level(text)
        if self._mode is Mode.SKILL_REINFORCEMENT:
            levels = _parse_skill_level(text)
        # pack
        if levels is not None:
            privious_level = levels[0]
            next_level = levels[1]
            _logger.debug('Lv.%d -> Lv.%d', privious_level, next_level)
            assert privious_level == self._level + 1
            assert next_level == privious_level + 1
            if self._level != 0:
                self._pack()
            self._level = privious_level
            self._next_level = next_level
            return True
        return False


def _parse_resource(text: str) -> List[_Resource]:
    result: List[_Resource] = []
    regexp = re.compile(r'(?P<item>.+),(x|)(?P<piece>[0-9万]+)')
    match = regexp.search(text)
    while match:
        resource = _Resource(
                name=match.group('item'),
                piece=int(match.group('piece').replace('万', '0000')))
        _logger.debug(
                'resource %s x %d',
                resource.name,
                resource.piece)
        result.append(resource)
        text = regexp.sub('', text, count=1)
        match = regexp.search(text)
    return result


def _parse_ascension_level(text: str) -> Optional[Tuple[int, int]]:
    match = re.match(r'(?P<level>[0-9]+)段階', text)
    if match:
        return (int(match.group('level')), int(match.group('level')) + 1)
    return None


def _parse_skill_level(text: str) -> Optional[Tuple[int, int]]:
    match = re.match(r'Lv(?P<privious>[0-9]+)→Lv(?P<next>[0-9]+)', text)
    if match:
        return (int(match.group('privious')), int(match.group('next')))
    return None


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
                'name_jp': servant_name,
                'class': servant_class,
                'rarity': rarity,
                'url': servant_url})
    return result


def _parse_servant_page(servant: _Servant):
    # access
    response = requests.get('https:{0}'.format(servant['url']))
    root = lxml.html.fromstring(response.text)
    # 霊基再臨
    servant['ascension'] = _parse_ascension(root)
    # スキル
    servant['skill'] = _parse_skill(root)
    # スキル強化
    servant['skill_reinforcement'] = _parse_skill_reinforcement(root)
    # 霊衣開放
    servant['spiritron_dress'] = _parse_spiritron_dress(root)


def _parse_ascension(
        root: lxml.html.HtmlElement) -> List[_RequiredResource]:
    parser = _RequiredResourceParser(
            mode=_RequiredResourceParserMode.ASCENSION)
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="霊基再臨"]'
            '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    for row in root.xpath(xpath):
        for cell in row.xpath('td'):
            parser.push(cell)
    return parser.result()


def _parse_skill(
        root: lxml.html.HtmlElement) -> List[_Skill]:
    result = []
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="保有スキル"]'
            '/following-sibling::h4')
    for node in root.xpath(xpath):
        text = node.text_content().strip()
        # order, name, rank
        match = re.match(
                r'Skill(?P<order>[123])(?P<upgraded>(|\[強化後\]))'
                r'：(?P<name>.+)',
                text)
        if not match:
            continue
        order = int(match.group('order'))
        is_upgraded = bool(match.group('upgraded'))
        name = match.group('name')
        rank = ''
        rank_match = re.match(
                r'(?P<name>.+)\s+(?P<rank>(EX|[A-E])[\+-]*)',
                name)
        if rank_match:
            name = rank_match.group('name')
            rank = rank_match.group('rank')
        _logger.debug(
                'skill %d%s: %s%s',
                order,
                '(upgraded)' if is_upgraded else '',
                name,
                ' rank: {0}'.format(rank) if rank else '')
        # icon
        icon_node = node.xpath(
            'following-sibling::div[1]/table//td[@rowspan]')[0]
        icon_text = icon_node.text_content().strip()
        icon_match = re.match(r'(?P<id>[0-9]+),((?P<rank>.+)|)', icon_text)
        if icon_match:
            icon_id = int(icon_match.group('id'))
            _logger.debug('skill icon %d: %s', icon_id, name)
        else:
            icon_id = 0
            _logger.warning('skill icon not found: %s', icon_text)
        result.append(_Skill(
                order=order,
                is_upgraded=is_upgraded,
                name=name,
                rank=rank,
                icon=icon_id))
    return result


def _parse_skill_reinforcement(
        root: lxml.html.HtmlElement) -> List[_RequiredResource]:
    parser = _RequiredResourceParser(
            mode=_RequiredResourceParserMode.SKILL_REINFORCEMENT)
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="スキル強化"]'
            '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    for row in root.xpath(xpath):
        for cell in row.xpath('td'):
            parser.push(cell)
    return parser.result()


def _parse_spiritron_dress(
        root: lxml.html.HtmlElement) -> List[_SpiritronDress]:
    result: List[_SpiritronDress] = []
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="霊衣開放"]'
            '/following-sibling::div'
            '[preceding-sibling::h3[position()=1'
            ' and normalize-space()="霊衣開放"]]'
            '/table')
    for table in root.xpath(xpath):
        name = table.xpath('tbody/tr[1]/th')[0].text.strip()
        resources: List[_Resource] = []
        for cell in table.xpath(
                'tbody/tr[td[1 and normalize-space()="必要素材"]]'
                '/td[position() > 1]'):
            resources.extend(_parse_resource(cell.text_content()))
        result.append(_SpiritronDress(
                name=name,
                resources=resources))
    return result


def _parse_name_en(
        servants: List[_Servant]) -> None:
    url = ('https://raw.githubusercontent.com'
           '/WeebMogul/Fate--Grand-Order-Servant-Data-Extractor'
           '/master/FGO_Servant_Data.csv')
    response = requests.get(url)
    reader = csv.DictReader(
            response.text
                    .replace('\ufeff', '')
                    .replace('\u3000', ' ').split('\n'))
    for row in reader:
        servant_id = int(row['ID'])
        name_en = row['Name']
        for servant in (servant for servant in servants
                        if servant['id'] == servant_id):
            servant['name_en'] = name_en


def _parse_skill_en() -> Dict[str, str]:
    url = 'https://grandorder.wiki/Skills'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//h1[text()="Skills"]/following-sibling::div//table/tr[td]'
    translator: Dict[str, str] = {}
    for row in root.xpath(xpath):
        name_cell = row.xpath('td[1]')[0]
        name_jp = name_cell.xpath('a/following-sibling::text()')[0].strip()
        name_en = name_cell.xpath('a')[0].text.strip()
        _logger.debug(
                'skill: %s (%s)',
                name_jp,
                name_en)
        translator[name_jp] = name_en
    return translator


def _normalize(
        servant: _Servant,
        items: List[Item],
        skill_translator: Dict[str, str]) -> Servant:
    assert len(servant['ascension']) == 4
    assert len(servant['skill_reinforcement']) == 9
    return {'id': servant['id'],
            'name': {
                'jp': servant['name_jp'],
                'en': servant['name_en']},
            'class': servant['class'],
            'rarity': servant['rarity'],
            'ascension': [
                    x.normalize(items) for x in servant['ascension']],
            'spiritron_dress': [
                    x.normalize(items) for x in servant['spiritron_dress']],
            'skill': [
                    x.normalize(skill_translator) for x in servant['skill']],
            'skill_reinforcement': [
                    x.normalize(items)
                    for x in servant['skill_reinforcement']]}


def servant_list(items: List[Item]) -> List[Servant]:
    servants = _parse_servant_table()
    time.sleep(_interval)
    for servant in servants:
        _logger.info('servant: %s', servant['name_jp'])
        time.sleep(_interval)
        _parse_servant_page(servant)
    time.sleep(_interval)
    _parse_name_en(servants)
    time.sleep(_interval)
    skill_translator = _parse_skill_en()
    return [_normalize(servant, items, skill_translator)
            for servant in servants]
