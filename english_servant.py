#!/usr/bin/env python

from __future__ import annotations

import argparse
import logging
import pathlib
import re
import time
from typing import Optional, TypedDict

import fake_useragent
import lxml.html
import requests

import lib


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("english_servant")
    # option
    option = argument_parser().parse_args()
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # session
    session = create_session(logger=logger)
    # servant links
    servant_links_path = pathlib.Path("data/english/servant/link.json")
    if option.force_update or not servant_links_path.exists():
        servant_links = request_servant_links(session, logger)
        logger.info('save servant links to "%s"', servant_links_path)
        lib.save_json(servant_links_path, servant_links)
    else:
        servant_links = load_servant_links(servant_links_path, logger)


def create_logger() -> logging.Logger:
    logger = logging.getLogger("english_servant")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s:%(levelname)s:%(message)s",
    )
    logger.addHandler(handler)
    return logger


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate English servant dictionary",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="set log level to debug",
    )
    parser.add_argument(
        "-f",
        "--force",
        dest="force_update",
        action="store_true",
        help="force update",
    )
    return parser


def create_session(
    *,
    logger: Optional[logging.Logger] = None,
) -> requests.Session:
    logger = logger or logging.getLogger(__name__)
    session = requests.Session()
    # user-agent
    user_agent = fake_useragent.UserAgent(
        os="Windows",
        browsers="Firefox",
        platforms="desktop",
    ).random
    logger.debug('fake user-agent: "%s"', user_agent)
    session.headers["User-Agent"] = user_agent
    return session


class ServantLink(TypedDict):
    id: int
    url: str
    title: str


type ServantLinks = dict[int, ServantLink]


def load_servant_links(
    path: pathlib.Path,
    logger: logging.Logger,
) -> ServantLinks:
    logger.info('load servant links from "%s"', path)
    links = lib.load_json(path)
    if links is None:
        logger.error('Failed to load "%s"', path)
        return {}
    return {int(key): value for key, value in links.items()}


def request_servant_links(
    session: requests.Session,
    logger: logging.Logger,
) -> ServantLinks:
    links: list[ServantLink] = []
    urls = [
        "https://fategrandorder.fandom.com/wiki/Sub:Servant_List_by_ID/1-100",
        "https://fategrandorder.fandom.com/wiki/Sub:Servant_List_by_ID/101-200",
        "https://fategrandorder.fandom.com/wiki/Sub:Servant_List_by_ID/201-300",
        "https://fategrandorder.fandom.com/wiki/Sub:Servant_List_by_ID/301-400",
        "https://fategrandorder.fandom.com/wiki/Sub:Servant_List_by_ID/401-500",
    ]
    for url in urls:
        # request URL
        logger.info('request "%s"', url)
        response = session.get(url)
        logger.debug("response: %d", response.status_code)
        if not response.ok:
            logger.error('failed to request "%s"', url)
            break
        root = lxml.html.fromstring(response.text)
        links.extend(parse_servant_links(root, logger))
        time.sleep(5)
    # sort by servant id
    links.sort(key=lambda link: link["id"])
    return {link["id"]: link for link in links}


def parse_servant_links(
    root: lxml.html.HtmlElement,
    logger: logging.Logger,
) -> list[ServantLink]:
    links: list[ServantLink] = []
    table_rows = root.xpath(
        '//table[contains(@class, "wikitable sortable")]/tbody/tr[td]'
    )
    for row in table_rows:
        servant_id = int(row.xpath("td[1]/text()")[0])
        href = row.xpath("td[3]/a/@href")[0]
        title = row.xpath("td[3]/a[@href]/text()")[0]
        logger.debug(
            'servant: id=%03d, href="%s", title="%s"',
            servant_id,
            href,
            title,
        )
        url = f"https://fategrandorder.fandom.com/{href}"
        links.append(ServantLink(id=servant_id, url=url, title=title))
    return links


if __name__ == "__main__":
    main()
