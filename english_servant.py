#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
import re
import time
from typing import Optional, TypedDict

import fake_useragent
import lxml.html
import requests

import lib
import lib.english


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("english_servant")
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # load servants
    servants_jp: dict[lib.ServantID, lib.Servant] = {
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
    servant_links = get_servant_links(
        servant_links_path,
        session,
        logger,
        option,
    )
    # servant data
    servant_data_directory = pathlib.Path("data/english/servant/data")
    servant_data = get_servant_data(
        session,
        servant_data_directory,
        servant_links,
        logger,
        option,
    )
    # servants
    servant_directory = pathlib.Path("data/english/servant")
    servants_en = get_servants(
        servant_directory,
        servant_links,
        servant_data,
        logger,
        option,
    )
    # compare English with Japanese
    compare_servants(servants_en, servants_jp, logger)
    # to English dictionary
    english_dictionary = to_dictionary(servants_en)
    dictionary_path = pathlib.Path("data/english/servant.json")
    logger.info('save english dictionary to "%s"', dictionary_path)
    lib.save_json(dictionary_path, english_dictionary)


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
    force_update: bool
    request_interval: float
    request_timeout: float


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
    parser.add_argument(
        "--request-timeout",
        dest="request_timeout",
        type=float,
        default=10.0,
        help="request timeout seconds (default: %(default)s)",
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


def get_servant_links(
    path: pathlib.Path,
    session: requests.Session,
    logger: logging.Logger,
    option: Option,
) -> dict[lib.ServantID, lib.english.ServantLink]:
    if option.force_update or not path.exists():
        links = request_servant_links(
            session,
            logger,
            option.request_interval,
            option.request_timeout,
        )
        logger.info('save servant links to "%s"', path)
        lib.save_json(path, links)
        time.sleep(option.request_interval)
    else:
        links = lib.english.load_servant_links(path, logger=logger) or []
    return {link["id"]: link for link in links}


def request_servant_links(
    session: requests.Session,
    logger: logging.Logger,
    request_interval: float,
    request_timeout: float,
) -> list[lib.english.ServantLink]:
    links: list[lib.english.ServantLink] = []
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
        response = session.get(url, timeout=request_timeout)
        logger.debug("response: %d", response.status_code)
        if not response.ok:
            logger.error('failed to request "%s"', url)
            break
        root = lxml.html.fromstring(response.text)
        links.extend(parse_servant_links(root, logger))
        time.sleep(request_interval)
    # sort by servant id
    links.sort(key=lambda link: link["id"])
    return links


def parse_servant_links(
    root: lxml.html.HtmlElement,
    logger: logging.Logger,
) -> list[lib.english.ServantLink]:
    links: list[lib.english.ServantLink] = []
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
        links.append(lib.english.ServantLink(id=servant_id, url=url, title=title))
    return links


def get_servant_data(
    session: requests.Session,
    directory: pathlib.Path,
    links: dict[lib.ServantID, lib.english.ServantLink],
    logger: logging.Logger,
    option: Option,
) -> dict[lib.ServantID, str]:
    unplayable_ids = lib.unplayable_servant_ids()
    servant_data: dict[lib.ServantID, str] = {}
    for link in links.values():
        # check playable
        if link["id"] in unplayable_ids:
            logger.info("skip unplayable servant %03d %s", link["id"], link["title"])
            continue
        path = directory.joinpath(f"{link['id']:03d}.txt")
        if option.force_update or not path.exists():
            # request data
            data = request_servant_data(session, link, logger, option.request_timeout)
            if data is not None:
                logger.info(
                    'save %03d %s data to "%s"',
                    link["id"],
                    link["title"],
                    path,
                )
                path.write_text(data, encoding="utf-8")
            time.sleep(option.request_interval)
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
    link: lib.english.ServantLink,
    logger: logging.Logger,
    request_timeout: float,
) -> Optional[str]:
    # request URL
    logger.info('request %03d %s to "%s"', link["id"], link["title"], link["url"])
    response = session.get(
        link["url"],
        params={"action": "edit"},
        timeout=request_timeout,
    )
    logger.debug("response: %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', link["url"])
        return None
    root = lxml.html.fromstring(response.text)
    return root.xpath('//textarea[@name="wpTextbox1"]/text()')[0]


def get_servants(
    directory: pathlib.Path,
    links: dict[lib.ServantID, lib.english.ServantLink],
    sources: dict[lib.ServantID, str],
    logger: logging.Logger,
    option: Option,
) -> dict[lib.ServantID, lib.english.Servant]:
    servants: dict[lib.ServantID, lib.english.Servant] = {}
    for servant_id, source in sources.items():
        path = directory.joinpath(f"{servant_id:03d}.json")
        servant: Optional[lib.english.Servant]
        if option.force_update or not path.exists():
            # parse source
            link = links.get(servant_id, None)
            if link is None:
                logger.error("servant ID %03d does not exist in links", servant_id)
                continue
            servant = parse_servant_data(
                link,
                source,
                lib.ServantLogger(logger, servant_id, link["title"]),
            )
            logger.info('save servant to "%s"', path)
            lib.save_json(path, servant)
        else:
            # load from file
            servant = lib.english.load_servant(path, logger=logger)
        if servant is not None:
            servants[servant["id"]] = servant
    return servants


def parse_servant_data(
    link: lib.english.ServantLink,
    source: str,
    logger: lib.ServantLogger,
) -> lib.english.Servant:
    # false name
    false_name = parse_false_name(source, logger)
    # active skills
    active_skills = parse_active_skills(source, logger)
    # append skills
    append_skills = parse_append_skills(source, logger)
    # costumes
    costumes = parse_costumes(source, logger)
    # ascension resources
    ascension_resources = parse_ascension_resources(source, logger)
    # active skill resource
    active_skill_resources = parse_active_skill_resources(source, logger)
    # append skill resource
    append_skill_resources = parse_append_skill_resources(source, logger)
    return lib.english.Servant(
        id=link["id"],
        name=link["title"],
        false_name=false_name,
        active_skills=active_skills,
        append_skills=append_skills,
        costumes=costumes,
        ascension_resources=ascension_resources,
        active_skill_resources=active_skill_resources,
        append_skill_resources=append_skill_resources,
    )


def parse_false_name(
    source: str,
    logger: lib.ServantLogger,
) -> Optional[str]:
    match = re.search(
        r"\|aka = .?\{\{Tooltip\|Before True Name Reveal\|(?P<name>.+?)\}\}",
        source,
    )
    if match is None:
        return None
    false_name = match.group("name")
    logger.info('false name "%s"', false_name)
    return false_name


def parse_active_skills(
    source: str,
    logger: lib.ServantLogger,
) -> list[list[lib.english.Skill]]:
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
) -> list[list[lib.english.Skill]]:
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
) -> list[lib.english.Skill]:
    logger.debug("[%s] input=%s", target, repr(source))
    # Remove {{Unlock|...}} or {{unlock:...}}
    source = re.sub(r"\{\{[Uu]nlock\|.+\}\}\n", "", source)
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


def parse_skill_rank(text: str) -> lib.english.Skill:
    rank_pattern = "((EX|[A-E])[+-]*)|None"
    # <name>/Rank <rank>( (name))?(|<rank>)?(|preupgrade=y)
    match = re.match(
        rf"^(?P<name>.+?)/Rank (?P<rank>{rank_pattern})"
        rf"(\s*\([\w& ]+\))?(\|(({rank_pattern})|preupgrade=y))?$",
        text,
    )
    if match:
        return to_skill(name=match.group("name"), rank=match.group("rank"))
    # <name>|<rank>
    match = re.match(rf"^(?P<name>.+)\|(?P<rank>{rank_pattern})$", text)
    if match:
        return to_skill(name=match.group("name"), rank=match.group("rank"))
    # <name> <rank>
    match = re.match(rf"^(?P<name>.+?) (?P<rank>{rank_pattern})$", text)
    if match:
        return to_skill(name=match.group("name"), rank=match.group("rank"))
    # <name> '<rank>'
    match = re.match(rf"^(?P<name>.+?) '(?P<rank>{rank_pattern})'$", text)
    if match:
        return to_skill(name=match.group("name"), rank=match.group("rank"))
    return lib.english.Skill(name=text, rank="")


def to_skill(name: str, rank: str) -> lib.english.Skill:
    return lib.english.Skill(
        name=name,
        rank=rank if rank != "None" else "",
    )


def parse_costumes(
    source: str,
    logger: lib.ServantLogger,
) -> list[lib.english.Costume]:
    logger.debug("costumes")
    match = re.search(
        r"==\s*Ascension\s*==\n\{\{Ascension\n(?P<body>(\|.+\n)+?)\}\}",
        source,
    )
    if match is None:
        return []
    costumes = parse_costume_data(match.group("body").split("\n"), logger)
    return costumes


def parse_costume_data(
    lines: list[str],
    logger: lib.ServantLogger,
) -> list[lib.english.Costume]:
    indexes: set[int] = set()
    name: dict[int, str] = {}
    text_en: dict[int, str] = {}
    text_jp: dict[int, str] = {}
    resources: dict[int, list[lib.Resource]] = {}
    qp: dict[int, int] = {}
    for line in lines:
        match = re.match(
            r"\|(?P<index>[0-9]+)(?P<key>(name|jdef|ndef|icon|qp|[1-4]))"
            r"\s*=\s*(?P<value>.*)",
            line,
        )
        if match is None:
            continue
        index = int(match.group("index"))
        # skil ascension resources
        if index <= 4:
            continue
        logger.debug(
            "costume %d: key(%s), value(%s)",
            int(match.group("index")),
            match.group("key"),
            match.group("value"),
        )
        indexes.add(index)
        match match.group("key"):
            case "name":
                name[index] = match.group("value")
            case "jdef":
                text_jp[index] = match.group("value").replace("<br/>", "\n")
            case "ndef":
                text_en[index] = match.group("value")
            case "qp":
                qp_match = re.match(
                    r"\{\{QP\|(?P<qp>[0-9,]+)\}\}",
                    match.group("value"),
                )
                if qp_match:
                    qp[index] = int(qp_match.group("qp").replace(",", ""))
            case "1" | "2" | "3" | "4":
                resource_match = re.match(
                    r"\{\{(?P<name>.+)\|(?P<piece>[0-9]+)\}\}",
                    match.group("value"),
                )
                if resource_match:
                    resources.setdefault(index, []).append(
                        lib.Resource(
                            name=resource_match["name"],
                            piece=int(resource_match["piece"]),
                        )
                    )
    # to costumes
    costumes: list[lib.english.Costume] = []
    for index in indexes:
        costumes.append(
            lib.english.Costume(
                name=name.get(index, ""),
                text_jp=text_jp.get(index, ""),
                text_en=text_en.get(index, ""),
                resources=lib.ResourceSet(
                    qp=qp.get(index, 0),
                    resources=resources.get(index, []),
                ),
            )
        )
    return costumes


def parse_ascension_resources(
    source: str,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    logger.debug("ascension resources")
    match = re.search(
        r"==\s*Ascension\s*==\n\{\{Ascension\n(?P<body>(\|.+\n)+?)\}\}",
        source,
    )
    if match is None:
        return []
    resources = parse_resource_set(
        match.group("body").split("\n"),
        4,
        logger,
    )
    # qp
    for i, qp in enumerate(ascension_qp()):
        if resources[i]["resources"]:
            resources[i]["qp"] = qp
    return resources


def parse_active_skill_resources(
    source: str,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    logger.debug("active skill resources")
    match = re.search(
        r"Active=\n\{\{Skillreinforcement\n(?P<body>(\|.+\n)+?)\}\}",
        source,
    )
    if match is None:
        return []
    resources = parse_resource_set(
        match.group("body").split("\n"),
        9,
        logger,
    )
    # qp
    for i, qp in enumerate(skill_qp()):
        if resources[i]["resources"]:
            resources[i]["qp"] = qp
    return resources


def parse_append_skill_resources(
    source: str,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    logger.debug("append skill resources")
    match = re.search(
        r"Append=\n\{\{Skillreinforcement\n(?P<body>(\|.+\n)+?)\}\}",
        source,
    )
    if match is None:
        return []
    resources = parse_resource_set(
        match.group("body").split("\n"),
        9,
        logger,
    )
    # qp
    for i, qp in enumerate(skill_qp()):
        if resources[i]["resources"]:
            resources[i]["qp"] = qp
    return resources


def parse_resource_set(
    lines: list[str],
    max_level: int,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    resources: list[lib.ResourceSet] = [
        lib.ResourceSet(qp=0, resources=[]) for _ in range(max(0, max_level))
    ]
    for line in lines:
        resource = parse_resource(line)
        if resource is None:
            continue
        logger.debug(
            '%d-%d "%s" x %d',
            resource["level"],
            resource["index"],
            resource["item"],
            resource["piece"],
        )
        if 1 <= resource["level"] and resource["level"] <= max_level:
            resources[resource["level"] - 1]["resources"].append(
                lib.Resource(
                    name=resource["item"],
                    piece=resource["piece"],
                )
            )
    return resources


class Resource(TypedDict):
    level: int
    index: int
    item: str
    piece: int


def parse_resource(line: str) -> Optional[Resource]:
    match = re.match(
        r"\|(?P<level>[0-9]+)(?P<index>[0-9])"
        r"\s*=\s*\{\{(?P<item>.+)\|(?P<piece>[0-9]+)\}\}",
        line,
    )
    if match is None:
        return None
    return Resource(
        level=int(match.group("level")),
        index=int(match.group("index")),
        item=match.group("item"),
        piece=int(match.group("piece")),
    )


def ascension_qp() -> list[int]:
    return [
        100000,
        300000,
        1000000,
        3000000,
    ]


def skill_qp() -> list[int]:
    return [
        200000,
        400000,
        1200000,
        1600000,
        4000000,
        5000000,
        10000000,
        12000000,
        20000000,
    ]


def compare_servants(
    en: dict[lib.ServantID, lib.english.Servant],
    jp: dict[lib.ServantID, lib.Servant],
    logger: logging.Logger,
) -> None:
    for servant_id, jp_servant in jp.items():
        servant_logger = lib.ServantLogger(logger, servant_id, jp_servant["name"])
        servant_logger.debug("start comparing")
        en_servant = en.get(servant_id, None)
        if en_servant is not None:
            compare_servant(en_servant, jp_servant, servant_logger)
        else:
            servant_logger.error("does not exits in English")


def compare_servant(
    en: lib.english.Servant,
    jp: lib.Servant,
    logger: lib.ServantLogger,
) -> None:
    # id
    if en["id"] != jp["id"]:
        logger.error("servant IDs do not match")
    # false name
    if en["false_name"] is not None:
        if jp["false_name"] is None:
            logger.error("only English has an false name")
    else:
        if jp["false_name"] is not None:
            logger.error("only Japanese has an false name")
    # active skills
    compare_skills("skill", en["active_skills"], jp["skills"], logger)
    # append skills
    compare_skills("append skill", en["append_skills"], jp["append_skills"], logger)


def compare_skills(
    target: str,
    en: list[list[lib.english.Skill]],
    jp: list[list[lib.Skill]],
    logger: lib.ServantLogger,
) -> None:
    # slots
    if len(en) != len(jp):
        logger.error(
            "%s: slots don't match (en:%d, jp:%d)",
            target,
            len(en),
            len(jp),
        )
    # skill
    slots = len(en)
    for i in range(slots):
        compare_skill(f"{target} {i+1}", en[i], jp[i], logger)


def compare_skill(
    target: str,
    en: list[lib.english.Skill],
    jp: list[lib.Skill],
    logger: lib.ServantLogger,
) -> None:
    # levels
    if len(en) != len(jp):
        logger.error(
            "%s: levels don't match (en:%d, jp:%d)",
            target,
            len(en),
            len(jp),
        )
        return
    # rank
    levels = len(en)
    for i in range(levels):
        if en[i]["rank"] != jp[i]["rank"]:
            logger.error(
                '%s: rank don\'t match at level %d (en:"%s", jp:"%s")',
                f"{target}-{i+1}",
                i,
                en[i]["rank"],
                jp[i]["rank"],
            )


def to_dictionary(
    servants: dict[lib.ServantID, lib.english.Servant],
) -> lib.ServantDictionary:
    return {
        servant_id: to_dictionary_value(servant)
        for servant_id, servant in servants.items()
    }


def to_dictionary_value(
    servant: lib.english.Servant,
) -> lib.ServantDictionaryValue:
    return lib.ServantDictionaryValue(
        name=servant["name"],
        false_name=servant["false_name"],
        skills=[
            [skill["name"] for skill in skill_n] for skill_n in servant["active_skills"]
        ],
        append_skills=[
            [skill["name"] for skill in skill_n] for skill_n in servant["append_skills"]
        ],
    )


if __name__ == "__main__":
    main()
