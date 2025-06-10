from __future__ import annotations

import logging
import pathlib
import re
from typing import Any, MutableMapping, Optional

import lxml.html
import requests

from .io import load_json
from .text import Text
from .types import Servant


def load_servants(
    directory: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> list[Servant]:
    logger = logger or logging.getLogger(__name__)
    servants: list[Servant] = []
    pattern = re.compile(r"^(?P<id>[0-9]{3}).json$")
    for file in directory.iterdir():
        if not file.is_file():
            continue
        match = pattern.match(file.name)
        if match is None:
            continue
        servant = load_servant(file, logger=logger)
        if servant is None:
            continue
        # check if filename match servant ID
        if int(match.group("id")) != servant["id"]:
            logger.error(
                'file name mismatch servant ID: path="%s", servant_id=%d',
                file,
                servant["id"],
            )
        servants.append(servant)
    # sort by servant ID
    servants.sort(key=lambda servant: servant["id"])
    return servants


def load_servant(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[Servant]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load servant from "%s"', path)
    servant = load_json(path)
    if servant is None:
        logger.error('failed to load "%s"', path)
        return None
    logger.debug(
        'loaded servant: %03d "%s"',
        servant["id"],
        servant["name"],
    )
    return servant


def unplayable_servant_ids() -> list[int]:
    return [
        83,  # ソロモン
        149,  # ティアマト
        151,  # ゲーティア
        152,  # ソロモン
        168,  # ビーストIII/R
        240,  # ビーストIII/L
        333,  # ビーストIV
        411,  # Ｅ－フレアマリー
        412,  # Ｅ－アクアマリー
        436,  # Ｅ－グランマリー
    ]


class ServantLogger(logging.LoggerAdapter):
    def __init__(
        self,
        logger: logging.Logger,
        servant_id: int,
        servant_name: str,
    ) -> None:
        super().__init__(logger)
        self._id = servant_id
        self._name = servant_name

    def process(
        self,
        msg: Any,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        return super().process(f"[{self._id:03d}: {self._name}] {msg}", kwargs)


def servant_dict(
    *,
    logger: Optional[logging.Logger] = None,
) -> dict[str, Text]:
    logger = logger or logging.getLogger(__name__)
    url = "https://grandorder.wiki/Servant_List"
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//table[@class="wikitable sortable"]//tr[td]'
    result: dict[str, Text] = {}
    for row in reversed(root.xpath(xpath)):
        cells = row.xpath("td")
        servant_id = int(cells[0].text.strip())
        name_en = cells[2].xpath("a")[0].text
        name_jp = cells[2].xpath("br/following-sibling::text()")[0].strip()
        if ";" in name_jp:
            name_jp = name_jp.split(";")[0]
        logger.debug('servant %03d: jp="%s", en="%s"', servant_id, name_jp, name_en)
        result[name_jp] = {"jp": name_jp, "en": name_en}
    return result


def skill_dict(
    *,
    logger: Optional[logging.Logger] = None,
) -> dict[str, Text]:
    logger = logger or logging.getLogger(__name__)
    url = "https://grandorder.wiki/Skills"
    response = requests.get(url)
    root = lxml.html.fromstring(response.text)
    xpath = '//h1[text()="Skills"]/following-sibling::div//table/tr[td]'
    result: dict[str, Text] = {}
    for row in root.xpath(xpath):
        name_cell = row.xpath("td[1]")[0]
        name_jp = name_cell.xpath("a/following-sibling::text()")[0].strip()
        name_en = name_cell.xpath("a")[0].text.strip()
        logger.debug('skill: jp="%s" en="%s"', name_jp, name_en)
        result[name_jp] = {"jp": name_jp, "en": name_en}
    return result
