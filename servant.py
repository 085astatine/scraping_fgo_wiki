#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
import time
from typing import Optional, TypedDict

import fake_useragent
import lxml.html
import requests

import lib


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("servant")
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # session
    session = create_session()
    # root directory
    directory = pathlib.Path("data/servant")
    # links
    links_path = directory.joinpath("link.json")
    links = get_servant_links(links_path, session, logger, option)
    # costumes
    costumes_path = directory.joinpath("costumes.json")
    costumes = load_costumes(costumes_path, logger)
    # WIP
    lib.servant_list(
        links,
        costumes,
        directory=directory,
        force_update=option.force_update,
        request_interval=option.request_interval,
    )


def create_logger() -> logging.Logger:
    logger = logging.getLogger("servant")
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
    force_update: bool
    request_interval: float


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
    parser.add_argument(
        "--request-interval",
        dest="request_interval",
        type=float,
        default=5.0,
        help="request interval seconds (default: %(default)s)",
        metavar="SECONDS",
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
    id: lib.ServantID
    klass: str
    rarity: int
    name: str
    url: str


def get_servant_links(
    path: pathlib.Path,
    session: requests.Session,
    logger: logging.Logger,
    option: Option,
) -> list[ServantLink]:
    if option.force_update or not path.exists():
        links = request_servant_links(session, logger)
        logger.info('save servant links to "%s"', path)
        lib.save_json(path, links)
        time.sleep(option.request_interval)
    else:
        links = load_servant_links(path, logger)
    return links


def load_servant_links(
    path: pathlib.Path,
    logger: logging.Logger,
) -> list[ServantLink]:
    logger.info('load servant links from "%s"', path)
    links = lib.load_json(path)
    if links is None:
        logger.error('failed to load servant links from "%s"', path)
        return []
    return links


def request_servant_links(
    session: requests.Session,
    logger: logging.Logger,
) -> list[ServantLink]:
    url = "https://w.atwiki.jp/f_go/pages/713.html"
    logger.info('request: "%s"', url)
    response = session.get(url)
    logger.debug("reqponse %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', url)
        return []
    root = lxml.html.fromstring(response.text)
    return parse_servant_links(root, logger)


def parse_servant_links(
    root: lxml.html.HtmlElement,
    logger: logging.Logger,
) -> list[ServantLink]:
    unplayable_ids = lib.unplayable_servant_ids()
    to_servant_class = {
        "剣": "Saber",  # セイバー
        "弓": "Archer",  # アーチャー
        "槍": "Lancer",  # ランサー
        "騎": "Rider",  # ライダー
        "術": "Caster",  # キャスター
        "殺": "Assassin",  # アサシン
        "狂": "Berserker",  # バーサーカー
        "盾": "Shielder",  # シールダー
        "裁": "Ruler",  # ルーラー
        "讐": "Avenger",  # アヴェンジャー
        "分": "AlterEgo",  # アルターエゴ
        "月": "MoonCancer",  # ムーンキャンサー
        "降": "Foreigner",  # フォーリナー
        "詐": "Pretender",  # プリテンダー
        "獣": "Beast",  # ビースト
    }
    links: list[ServantLink] = []
    for row in root.xpath(
        '//h2[normalize-space()="サーヴァント一覧"]/'
        "following-sibling::div[1]//"
        "table/tbody/tr[td]"
    ):
        servant_id = int(row.xpath("td[1]")[0].text)
        if servant_id in unplayable_ids:
            logger.debug("skip unplayable servant %03d", servant_id)
            continue
        rarity = int(row.xpath("td[2]")[0].text)
        name = row.xpath("td[3]//a")[0].text
        klass = to_servant_class[row.xpath("td[4]")[0].text.strip()]
        href = row.xpath("td[3]//a")[0].get("href")
        link = ServantLink(
            id=servant_id,
            name=name,
            klass=klass,
            rarity=rarity,
            url=f"https:{href}",
        )
        logger.debug(
            'link to %03d: %s (rarity:%d, class:%s, url:"%s")',
            link["id"],
            link["name"],
            link["rarity"],
            link["klass"],
            link["url"],
        )
        links.append(link)
    # sort by servant ID
    links.sort(key=lambda link: link["id"])
    return links


class Costume(TypedDict):
    costume_id: lib.CostumeID
    servant_id: lib.ServantID
    name: str
    flavor_text: str
    resource: lib.ResourceSet


def load_costumes(
    path: pathlib.Path,
    logger: logging.Logger,
) -> list[Costume]:
    logger.info('load costumes from "%s"', path)
    costumes = lib.load_json(path)
    if costumes is None:
        logger.error('failed to load costumes from "%s"', path)
        return []
    return costumes


if __name__ == "__main__":
    main()
