import logging
from typing import TypedDict
import lxml.html
import requests
from .text import Text


_logger = logging.getLogger(__name__)


class Item(TypedDict):
    id: int
    rarity: str
    name: str


def item_list() -> list[Item]:
    url = "https://grandorder.wiki/Items"
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//h2[span[normalize-space()="Item List"]]/following-sibling::table//tr[td]'
    target_item_types = ["Ascension", "Skill"]
    result: list[Item] = []
    for row in root.xpath(xpath):
        item_type = row.xpath("td[4]")[0].text.strip()
        if not any(x in item_type for x in target_item_types):
            continue
        item_id = int(row.xpath("td[1]")[0].text)
        name_cell = row.xpath("td[3]")[0]
        name = name_cell.xpath("br/following-sibling::text()")[0].strip()
        rarity = row.xpath("td[2]/div")[0].get("class").replace("itembox", "")
        if rarity not in ["Bronze", "Silver", "Gold"]:
            _logger.error(
                'item %d: %s has unknown ratiry "%s"',
                item_id,
                name,
                rarity,
            )
        _logger.debug(
            "item %d: %s rarity:%s, type:%s",
            item_id,
            name,
            rarity,
            item_type,
        )
        result.append({"id": item_id, "rarity": rarity, "name": name})
    return result


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
