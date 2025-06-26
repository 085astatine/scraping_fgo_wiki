from __future__ import annotations

import logging
import pathlib
import re
from typing import Any, MutableMapping, Optional

from .io import load_json
from .types import CostumeData, Servant, ServantLink, ServantName


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


def load_servant_links(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[ServantLink]]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load servant links from "%s"', path)
    links = load_json(path)
    if links is None:
        logger.error('failed to load servant links from "%s"', path)
        return None
    return links


def load_servant_names(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[ServantName]]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load servant names from "%s"', path)
    names = load_json(path)
    if names is None:
        logger.error('failed to load servant names from "%s"', path)
        return None
    return names


def load_costumes(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[CostumeData]]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load costumes from "%s"', path)
    costumes = load_json(path)
    if costumes is None:
        logger.error('failed to load costumes from "%s"', path)
        return None
    return costumes


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
