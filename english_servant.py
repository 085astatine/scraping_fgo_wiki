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
    # load servants
    servants: dict[int, lib.Servant] = {
        servant["id"]: servant
        for servant in lib.load_servants(
            pathlib.Path("data/servant"),
            logger=logger,
        )
    }
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
    # servant data
    servant_data_directory = pathlib.Path("data/english/servant/data")
    servant_data = get_servant_data(
        session,
        servant_data_directory,
        servant_links,
        logger,
        option,
    )


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


def get_servant_data(
    session: requests.Session,
    directory: pathlib.Path,
    links: ServantLinks,
    logger: logging.Logger,
    option: argparse.Namespace,
) -> dict[int, str]:
    unplayable_ids = lib.unplayable_servant_ids()
    servant_data: dict[int, str] = {}
    for link in links.values():
        # check playable
        if link["id"] in unplayable_ids:
            logger.info("skip unplayable servant %03d %s", link["id"], link["title"])
            continue
        path = directory.joinpath(f"{link['id']:03d}.txt")
        if option.force_update or not path.exists():
            # request data
            data = request_servant_data(session, link, logger)
            if data is not None:
                logger.info(
                    'save %03d %s data to "%s"',
                    link["id"],
                    link["title"],
                    path,
                )
                path.write_text(data, encoding="utf-8")
            time.sleep(5)
        else:
            # load data
            data = load_servant_data(path, logger)
        # add to servant_data
        if data is not None:
            servant_data[link["id"]] = data
    return servant_data


def load_servant_data(
    path: pathlib.Path,
    logger: logging.Logger,
) -> Optional[str]:
    logger.info('load servant from "%s"', path)
    if not path.exists():
        logger.error('"%s" does not exist', path)
        return None
    return path.read_text(encoding="utf-8")


def request_servant_data(
    session: requests.Session,
    link: ServantLink,
    logger: logging.Logger,
) -> Optional[str]:
    # request URL
    logger.info('request %03d %s to "%s"', link["id"], link["title"], link["url"])
    response = session.get(link["url"], params={"action": "edit"})
    logger.debug("response: %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', link["url"])
        return None
    root = lxml.html.fromstring(response.text)
    return root.xpath('//textarea[@name="wpTextbox1"]/text()')[0]


class Skill(TypedDict):
    name: str
    rank: str


def parse_servant_data(
    source: str,
    logger: lib.ServantLogger,
) -> None:
    # alias name
    alias_name = parse_alias_name(source, logger)
    # active skills
    skills = parse_active_skills(source, logger)
    # append skills
    append_skills = parse_append_skills(source, logger)


def parse_alias_name(
    source: str,
    logger: lib.ServantLogger,
) -> Optional[str]:
    match = re.search(
        r"\|aka = .?\{\{Tooltip\|Before True Name Reveal\|(?P<name>.+?)\}\}",
        source,
    )
    if match is None:
        return None
    alias_name = match.group("name")
    logger.info('alias name "%s"', alias_name)
    return alias_name


def parse_active_skills(
    source: str,
    logger: lib.ServantLogger,
) -> list[list[Skill]]:
    match = re.search(
        r"==\s*Active Skills\s*==\n"
        r"<tabber>\n"
        r"First Skill=\n"
        r"(?P<skill_1>(.*\n)+?)"
        r"\|-\|\n"
        r"Second Skill=\n"
        r"(?P<skill_2>(.*\n)+?)"
        r"\|-\|\n"
        r"Third Skill=\n"
        r"(?P<skill_3>(.*\n)+?)"
        r"</tabber>\n",
        source,
    )
    if match is None:
        logger.error("failed to match active skill")
        return []
    return [
        parse_skill("skill 1", match.group("skill_1"), logger),
        parse_skill("skill 2", match.group("skill_2"), logger),
        parse_skill("skill 3", match.group("skill_3"), logger),
    ]


def parse_append_skills(
    source: str,
    logger: lib.ServantLogger,
) -> list[list[Skill]]:
    match = re.search(
        r"==\s*Append Skills\s*==\n"
        r"<tabber>\n"
        r"First Skill=\n"
        r"(?P<skill_1>(.*\n)+?)"
        r"\|-\|\n"
        r"Second Skill=\n"
        r"(?P<skill_2>(.*\n)+?)"
        r"\|-\|\n"
        r"Third Skill=\n"
        r"(?P<skill_3>(.*\n)+?)"
        r"\|-\|\n"
        r"Fourth Skill=\n"
        r"(?P<skill_4>(.*\n)+?)"
        r"\|-\|\n"
        r"Fifth Skill=\n"
        r"(?P<skill_5>(.*\n)+?)"
        r"</tabber>\n",
        source,
    )
    if match is None:
        return []
    return [
        parse_skill("append skill 1", match.group("skill_1"), logger),
        parse_skill("append skill 2", match.group("skill_2"), logger),
        parse_skill("append skill 3", match.group("skill_3"), logger),
        parse_skill("append skill 4", match.group("skill_4"), logger),
        parse_skill("append skill 5", match.group("skill_5"), logger),
    ]


def parse_skill(
    target: str,
    source: str,
    logger: lib.ServantLogger,
) -> list[Skill]:
    logger.debug("[%s] input=%s", target, repr(source))
    # Remove {{Unlock|...}}
    source = re.sub(r"\{\{Unlock\|.+\}\}\n", "", source)
    # mult level
    if source.startswith("{{#tag:tabber"):
        skill = [
            parse_skill_rank(skill_texts.split("=")[0])
            for skill_texts in source.removeprefix("{{#tag:tabber|\n")
            .removesuffix("}}")
            .split("{{!}}-{{!}}\n")
        ]
        skill.reverse()
    else:
        skill = []
        match = re.match(r"\{\{:(?P<skill>.+)\}\}\n", source)
        if match:
            skill.append(parse_skill_rank(match.group("skill")))
    logger.info("[%s] %s", target, repr(skill))
    return skill


def parse_skill_rank(text: str) -> Skill:
    rank_pattern = "(EX|[A-E])[+-]*"
    # <name>|<rank>
    match = re.match(rf"^(?P<name>.+)\|(?P<rank>{rank_pattern})$", text)
    if match:
        return Skill(name=match.group("name"), rank=match.group("rank"))
    # <name> <rank>
    match = re.match(rf"^(?P<name>.+?) (?P<rank>{rank_pattern})$", text)
    if match:
        return Skill(name=match.group("name"), rank=match.group("rank"))
    # <name> '<rank>'
    match = re.match(rf"^(?P<name>.+?) '(?P<rank>{rank_pattern})'$", text)
    if match:
        return Skill(name=match.group("name"), rank=match.group("rank"))
    return Skill(name=text, rank="")


if __name__ == "__main__":
    main()
