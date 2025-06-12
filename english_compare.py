#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("english_compare")
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)


def create_logger() -> logging.Logger:
    logger = logging.getLogger("english_servant")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s:%(levelname)s:%(message)s",
    )
    logger.addHandler(handler)
    return logger


@dataclasses.dataclass(frozen=True)
class Option:
    verbose: bool


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare English Data with Japanese Data",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="set log level to debug",
    )
    return parser


if __name__ == "__main__":
    main()
