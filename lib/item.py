from __future__ import annotations

import logging

import lxml.html
import requests

from .text import Text

_logger = logging.getLogger(__name__)


def item_dict() -> dict[str, Text]:
    url = "https://grandorder.wiki/Items"
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//h2[span[normalize-space()="Item List"]]/following-sibling::table//tr[td]'
    target_item_types = ["Ascension", "Skill"]
    result: dict[str, Text] = {}
    for row in root.xpath(xpath):
        item_type = row.xpath("td[4]")[0].text.strip()
        if not any(x in item_type for x in target_item_types):
            continue
        name_cell = row.xpath("td[3]")[0]
        name_jp = name_cell.xpath("br/following-sibling::text()")[0].strip()
        name_en = name_cell.xpath("a")[0].text.strip()
        _logger.debug("jp: %s, en: %s", name_jp, name_en)
        result[name_jp] = {"jp": name_jp, "en": name_en}
    return result
