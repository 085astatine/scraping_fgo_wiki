#!/usr/bin/env python

import logging
import pathlib
import sys
import lib


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
    servant_directory = pathlib.Path("./data/servant")
    if not lib.validate_servants(servant_directory):
        sys.exit(1)


if __name__ == "__main__":
    main()
