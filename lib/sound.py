import logging
import re
from typing import Optional, TypedDict
import requests
import lxml.html
from .servant import Resource, ResourceSet


_logger = logging.getLogger(__name__)


class Sound(TypedDict):
    source: str
    index: int
    title: str
    resource: ResourceSet


def sound_list() -> list[Sound]:
    result: list[Sound] = []
    source_list = [
        'Part1',
        'Part1_5',
        'Part2',
        'Event']
    # request
    url = 'https://kamigame.jp/fgo/初心者攻略/サウンドプレイヤー.html'
    response = requests.get(url)
    etree = lxml.html.fromstring(response.content)
    xpath = '//table[starts-with(@class, "wt")]'
    for i, table in enumerate(etree.xpath(xpath)):
        source = source_list[i]
        for k, row in enumerate(table.xpath('tbody/tr')):
            sound = _parse_sound(source, k, row)
            if sound is not None:
                _logger.info(
                        'sound: %s, %d, "%s"',
                        sound['source'],
                        sound['index'],
                        sound['title'])
                result.append(sound)
    return result


def _parse_sound(
        source: str,
        index: int,
        row: lxml.html.HtmlElement) -> Optional[Sound]:
    cells = row.xpath('td')
    if len(cells) < 2:
        _logger.error('parse failed: %s, %d', source, index)
        return None
    return Sound(
            source=source,
            index=index,
            title=cells[1].text_content().strip(),
            resource=_parse_resource(cells[2]))


def _parse_resource(
        cell: lxml.html.HtmlElement) -> ResourceSet:
    resources: list[Resource] = []
    img = cell.xpath('span/a/img')
    if img:
        item = img[0].get('alt').strip()
        piece_match = re.match(r'[0-9]+(?=個)', cell.text_content())
        if piece_match is None:
            _logger.error('piece match failed %s', cell.text_content())
        piece = int(piece_match.group()) if piece_match is not None else -1
        _logger.debug('resource: %s x %d', item, piece)
        resources.append(Resource(name=item, piece=piece))
    else:
        _logger.debug('resource: none')
    return ResourceSet(
            qp=0,
            resources=resources)
