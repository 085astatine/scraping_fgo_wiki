from __future__ import annotations

import functools
import logging
import operator
from typing import Any, Optional, TypedDict


class Patch[T](TypedDict):
    path: list[str]
    before: T
    after: T


def apply_patch(
    data: Any,
    patch: Patch[Any],
    *,
    logger: Optional[logging.Logger | logging.LoggerAdapter] = None,
) -> None:
    logger = logger or logging.getLogger(__name__)
    try:
        parent = functools.reduce(operator.getitem, patch["path"][:-1], data)
        before = parent[patch["path"][-1]]
    except (IndexError, KeyError) as error:
        logger.error(
            "failed to apply patch with %s(%s)",
            type(error).__name__,
            error,
        )
        return
    if before != patch["before"]:
        logger.error(
            'patch %s: before is different. actual="%s", expected="%s"',
            ".".join(str(x) for x in patch["path"]),
            before,
            patch["before"],
        )
        return
    logger.debug(
        'patch %s: apply "%s" -> "%s"',
        ".".join(str(x) for x in patch["path"]),
        before,
        patch["after"],
    )
    parent[patch["path"][-1]] = patch["after"]


def apply_patches(
    data: Any,
    patches: list[Patch[Any]],
    *,
    logger: Optional[logging.Logger | logging.LoggerAdapter] = None,
) -> None:
    logger = logger or logging.getLogger(__name__)
    for patch in patches:
        apply_patch(data, patch, logger=logger)
