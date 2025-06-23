#!/usr/bin/env python

from __future__ import annotations

import logging
import pathlib
import sys

import fgo


def main() -> None:
    # logger
    logger = logging.getLogger("lib")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s:%(levelname)s:%(message)s"
    )
    logger.addHandler(handler)
    # validate servants
    servants = fgo.load_servants(
        pathlib.Path("./data/servant"),
        logger=logger,
    )
    if not fgo.validate_servants(servants, logger=logger):
        sys.exit(1)


if __name__ == "__main__":
    main()
