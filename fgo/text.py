from __future__ import annotations

import logging
import pathlib
from typing import Optional

from .io import load_json
from .types import ItemDictionary, ServantDictionary


def load_item_dictionary(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[ItemDictionary]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load item dictionary from "%s"', path)
    data = load_json(path)
    if data is None:
        logger.error('failed to load item dictionary from "%s"', path)
        return None
    return {int(key): value for key, value in data.items()}


def load_servant_dictionary(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[ServantDictionary]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load servant dictionary from "%s"', path)
    data = load_json(path)
    if data is None:
        logger.error('failed to load servant dictionary from "%s"', path)
        return None
    return {int(key): value for key, value in data.items()}
