from __future__ import annotations

import logging
import pathlib
from typing import Optional

from .io import load_json
from .types import Item


def load_items(
    path: pathlib.Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[Item]]:
    logger = logger or logging.getLogger(__name__)
    logger.info('load items from "%s"', path)
    items = load_json(path)
    if items is None:
        logger.error('failed to load items from "%s"', path)
        return None
    return items
