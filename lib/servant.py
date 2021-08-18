#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum
import logging
import pathlib
import re
import time
from typing import Literal, Optional, TypedDict
import lxml.html
import requests
from .io import load_json, save_json
from .text import Text


_logger = logging.getLogger(__name__)


class Skill(TypedDict):
    slot: int
    level: int
    name: str
    rank: str
    icon: int


class Skills(TypedDict):
    skill_1: list[Skill]
    skill_2: list[Skill]
    skill_3: list[Skill]


class Resource(TypedDict):
    name: str
    piece: int


class ResourceSet(TypedDict):
    qp: int
    resources: list[Resource]


class Costume(TypedDict):
    id: int
    name: str
    resource: ResourceSet


class Servant(TypedDict):
    id: int
    name: str
    alias_name: Optional[str]
    klass: str
    rarity: int
    skills: Skills
    append_skills: Skills
    costumes: list[Costume]
    ascension_resources: list[ResourceSet]
    skill_resources: list[ResourceSet]
    append_skill_resources: list[ResourceSet]


class _ServantTable(TypedDict):
    id: int
    klass: str
    rarity: int
    name: str
    url: str


class _ResourceSetParserMode(enum.Enum):
    ASCENSION = enum.auto()
    SKILL = enum.auto()


class _ResourceSetParser:
    def __init__(self, mode: _ResourceSetParserMode) -> None:
        self._mode = mode
        self._result: list[ResourceSet] = []
        self._level: Optional[int] = None
        self._resources: list[Resource] = []

    def push(self, cell: lxml.html.HtmlElement):
        text = cell.text_content().strip()
        if not text:
            return
        # level
        if self._parse_level(text):
            return
        # resource
        if self._level is not None:
            self._resources.extend(_parse_resource(text))

    def result(self) -> list[ResourceSet]:
        if self._level is not None:
            self._pack()
        return self._result

    def _pack(self) -> None:
        self._result.append(_to_resource_set(self._resources))
        self._resources = []

    def _parse_level(self, text) -> bool:
        level: Optional[int] = None
        # parse
        if self._mode is _ResourceSetParserMode.ASCENSION:
            level = _parse_ascension_level(text)
        elif self._mode is _ResourceSetParserMode.SKILL:
            level = _parse_skill_level(text)
        # pack
        if level is not None:
            _logger.debug('Lv.%d -> Lv.%d', level, level + 1)
            if self._level is not None:
                self._pack()
            self._level = level
            return True
        return False


def _to_resource_set(resources: list[Resource]) -> ResourceSet:
    result = ResourceSet(qp=0, resources=[])
    for resource in resources:
        if resource['name'] == 'QP':
            result['qp'] += resource['piece']
        else:
            result['resources'].append(resource)
    return result


def _parse_resource(text: str) -> list[Resource]:
    result: list[Resource] = []
    regexp = re.compile(r'(?P<item>.+),(x|)(?P<piece>[0-9万]+)')
    match = regexp.search(text)
    while match:
        resource = Resource(
                name=match.group('item'),
                piece=int(match.group('piece').replace('万', '0000')))
        _logger.debug(
                'resource %s x %d',
                resource['name'],
                resource['piece'])
        result.append(resource)
        text = regexp.sub('', text, count=1)
        match = regexp.search(text)
    return result


def _parse_ascension_level(text: str) -> Optional[int]:
    match = re.match(r'(?P<level>[0-9]+)段階', text)
    if match:
        return int(match.group('level'))
    return None


def _parse_skill_level(text: str) -> Optional[int]:
    match = re.match(r'Lv(?P<current>[0-9]+)→Lv(?P<next>[0-9]+)', text)
    if match:
        level = int(match.group('current'))
        next_level = int(match.group('next'))
        assert level + 1 == next_level
        return level
    return None


def _parse_servant_table() -> list[_ServantTable]:
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
            '詐': 'Pretender',  # プリテンダー
            '獣': 'Beast'}  # ビースト
    # access
    response = requests.get(url)
    etree = lxml.html.fromstring(response.text)
    xpath = ('/html/body//div[@id="wikibody"]/div[1]/div/'
             'table/tbody/tr[td]')
    # サーヴァントリスト作成
    result: list[_ServantTable] = []
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
        result.append(_ServantTable(
                id=servant_id,
                name=servant_name,
                klass=servant_class,
                rarity=rarity,
                url=servant_url))
    return result


def _parse_servant_page(servant: _ServantTable) -> Servant:
    # access
    response = requests.get('https:{0}'.format(servant['url']))
    root = lxml.html.fromstring(response.text)
    # 霊基再臨用素材
    _logger.debug('ascension resources')
    ascension_resources = _parse_ascension_resources(root)
    if len(ascension_resources) != 4:
        _logger.error(
                'servant %s: ascension resources parsing failed',
                servant['name'])
    # スキル
    _logger.debug('skills')
    skills = _parse_skill(root, 'skill')
    # スキル強化用素材
    _logger.debug('skill resources')
    skill_resources = _parse_skill_resources(root, 'skill')
    if len(skill_resources) != 9:
        _logger.error(
                'servant %s: skill resources parsing failed',
                servant['name'])
    # アペンドスキル
    _logger.debug('append skills')
    append_skills = _parse_skill(root, 'append_skill')
    # スキル強化用素材
    _logger.debug('append skill resources')
    append_skill_resources = _parse_skill_resources(root, 'append_skill')
    if len(skill_resources) != 9:
        _logger.error(
                'servant %s: append skill resources parsing failed',
                servant['name'])
    # 霊衣
    _logger.debug('costumes')
    costumes = _parse_costumes(root)
    return Servant(
            id=servant['id'],
            name=servant['name'],
            alias_name=None,
            klass=servant['klass'],
            rarity=servant['rarity'],
            skills=skills,
            append_skills=append_skills,
            costumes=costumes,
            ascension_resources=ascension_resources,
            skill_resources=skill_resources,
            append_skill_resources=append_skill_resources)


def _parse_ascension_resources(
        root: lxml.html.HtmlElement) -> list[ResourceSet]:
    parser = _ResourceSetParser(
            mode=_ResourceSetParserMode.ASCENSION)
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="霊基再臨"]'
            '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    for row in root.xpath(xpath):
        for cell in row.xpath('td'):
            parser.push(cell)
    return parser.result()


def _parse_skill(
        root: lxml.html.HtmlElement,
        target: Literal['skill', 'append_skill']) -> Skills:
    skill_slots: dict[int, list[Skill]] = {i: [] for i in range(1, 4)}
    if target == 'skill':
        xpath = (
                '//div[@id="wikibody"]'
                '//h3[normalize-space()="保有スキル"]'
                '/following-sibling::h4')
    elif target == 'append_skill':
        xpath = (
                '//div[@id="wikibody"]'
                '//h3[normalize-space()="アペンドスキル"]'
                '/following-sibling::div/h4')
    for node in root.xpath(xpath):
        text = node.text_content().strip()
        # slot, level, name, rank
        match = re.match(
                r'Skill(?P<slot>[123])'
                r'(|(?P<upgraded>(|\[強化後(|(?P<level>[0-9]+)))\]))'
                r'：(?P<name>.+)',
                text)
        if not match:
            continue
        slot = int(match.group('slot'))
        level = (1 if match.group('upgraded') is None
                 else 2 if match.group('level') is None
                 else int(match.group('level')) + 1)
        name = match.group('name').strip()
        rank = ''
        rank_match = re.match(
                r'(?P<name>.+)\s+(?P<rank>(EX|[A-E])[\+-]*)',
                name)
        if rank_match:
            name = rank_match.group('name').strip()
            rank = rank_match.group('rank')
        _logger.debug(
                'skill %d Lv.%d: %s%s',
                slot,
                level,
                name,
                ' rank: {0}'.format(rank) if rank else '')
        # icon
        icon_node = node.xpath(
            'following-sibling::div[1]/table//td[@rowspan]')[0]
        icon_text = icon_node.text_content().strip()
        icon_match = re.match(r'(?P<id>[0-9]+)(,(?P<rank>.+)|)', icon_text)
        if icon_match:
            icon_id = int(icon_match.group('id'))
            _logger.debug('skill icon %d: %s', icon_id, name)
        else:
            icon_id = 0
            _logger.warning('skill icon not found: %s', icon_text)
        skill_slots[slot].append(Skill(
                slot=slot,
                level=level,
                name=name,
                rank=rank,
                icon=icon_id))
    # check
    if not all(len(slot) > 0 for slot in skill_slots.values()):
        _logger.error('there is a missing skill slot')
    if not all(skill['level'] == i + 1
               for slot in skill_slots.values()
               for i, skill in enumerate(slot)):
        _logger.error('duplicate or missing skill levels')
    return Skills(
            skill_1=skill_slots[1],
            skill_2=skill_slots[2],
            skill_3=skill_slots[3])


def _parse_skill_resources(
        root: lxml.html.HtmlElement,
        target: Literal['skill', 'append_skill']) -> list[ResourceSet]:
    parser = _ResourceSetParser(
            mode=_ResourceSetParserMode.SKILL)
    if target == 'skill':
        xpath = (
                '//div[@id="wikibody"]'
                '//h3[normalize-space()="スキル強化"]'
                '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    elif target == 'append_skill':
        xpath = (
                '//div[@id="wikibody"]'
                '//h3[normalize-space()="アペンドスキル強化"]'
                '/following-sibling::div[1]/div/table[1]/tbody/tr[td]')
    for row in root.xpath(xpath):
        for cell in row.xpath('td'):
            parser.push(cell)
    return parser.result()


def _parse_costumes(
        root: lxml.html.HtmlElement) -> list[Costume]:
    result: list[Costume] = []
    xpath = (
            '//div[@id="wikibody"]'
            '//h3[normalize-space()="霊衣開放"]'
            '/following-sibling::div'
            '[preceding-sibling::h3[position()=1'
            ' and normalize-space()="霊衣開放"]]'
            '/table')
    for table in root.xpath(xpath):
        name = table.xpath('tbody/tr[1]/th')[0].text.strip()
        _logger.debug('costume: %s', name)
        resources: list[Resource] = []
        for cell in table.xpath(
                'tbody/tr[td[1 and normalize-space()="必要素材"]]'
                '/td[position() > 1]'):
            resources.extend(_parse_resource(cell.text_content()))
        result.append(Costume(
                id=0,
                name=name,
                resource=_to_resource_set(resources)))
    return result


def _load_servant_table(
        *,
        path: Optional[pathlib.Path] = None,
        force_update: bool = False,
        request_interval: float = 1.0) -> list[_ServantTable]:
    # load
    if path is not None and not force_update:
        result = load_json(path)
        if result is not None:
            _logger.debug('servant table is loaded from "%s"', path)
            return result
    # request
    result = _parse_servant_table()
    time.sleep(request_interval)
    # save
    if path is not None:
        save_json(path, result)
        _logger.debug('savant table is saved to "%s"', path)
    return result


def _load_servant(
        data: _ServantTable,
        *,
        path: Optional[pathlib.Path] = None,
        force_update: bool = False,
        request_interval: float = 1.0) -> Servant:
    # load
    if path is not None and not force_update:
        result = load_json(path)
        if result is not None:
            _logger.debug(
                    'servant "%s" is loaded from "%s"',
                    data['name'],
                    path)
            # check
            assert result['id'] == data['id']
            return result
    # request
    result = _parse_servant_page(data)
    time.sleep(request_interval)
    # save
    if path is not None:
        save_json(path, result)
        _logger.debug('servant "%s" is saved to "%s"', data['name'], path)
    return result


def servant_list(
        *,
        directory: Optional[pathlib.Path] = None,
        force_update: bool = False,
        request_interval: float = 1.0) -> list[Servant]:
    servant_table = _load_servant_table(
            path=(directory.joinpath('list.json')
                  if directory is not None else None),
            force_update=force_update,
            request_interval=request_interval)
    time.sleep(request_interval)
    result: list[Servant] = []
    for row in servant_table:
        _logger.info('servant: %s', row['name'])
        result.append(_load_servant(
                row,
                path=(directory.joinpath(f'{row["id"]:03d}.json')
                      if directory is not None else None),
                force_update=force_update,
                request_interval=request_interval))
    return result


def servant_dict() -> dict[str, Text]:
    url = 'https://grandorder.wiki/Servant_List'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//table[@class="wikitable sortable"]//tr[td]'
    result: dict[str, Text] = {}
    for row in reversed(root.xpath(xpath)):
        cells = row.xpath('td')
        servant_id = int(cells[0].text.strip())
        name_en = cells[2].xpath('a')[0].text
        name_jp = cells[2].xpath('br/following-sibling::text()')[0].strip()
        if ';' in name_jp:
            name_jp = name_jp.split(';')[0]
        _logger.debug(
                'servant %03d: jp="%s", en="%s"',
                servant_id,
                name_jp,
                name_en)
        result[name_jp] = {'jp': name_jp, 'en': name_en}
    return result


def skill_dict() -> dict[str, Text]:
    url = 'https://grandorder.wiki/Skills'
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//h1[text()="Skills"]/following-sibling::div//table/tr[td]'
    result: dict[str, Text] = {}
    for row in root.xpath(xpath):
        name_cell = row.xpath('td[1]')[0]
        name_jp = name_cell.xpath('a/following-sibling::text()')[0].strip()
        name_en = name_cell.xpath('a')[0].text.strip()
        _logger.debug('skill: jp="%s" en="%s"', name_jp, name_en)
        result[name_jp] = {'jp': name_jp, 'en': name_en}
    return result
