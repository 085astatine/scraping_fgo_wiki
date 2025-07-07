#!/usr/bin/env python

# pylint: disable=too-many-lines

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
import re
import time
import urllib.parse
from typing import Literal, Optional, TypedDict

import fake_useragent
import lxml.html
import requests

import fgo
import fgo.english


def main() -> None:
    # logger
    logger = create_logger()
    logger.info("english_servant")
    # option
    option = Option(**vars(argument_parser().parse_args()))
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("option: %s", option)
    # session
    session = create_session(logger=logger)
    # servant links
    links_path = pathlib.Path("data/english/servant/link.json")
    links = get_servant_links(
        links_path,
        session,
        logger,
        option,
    )
    if option.targets:
        links = [link for link in links if link["id"] in option.targets]
    # costumes
    costumes = group_costumes_by_servant(
        get_costumes(
            pathlib.Path("data/english/servant"),
            session,
            logger,
            option,
        ),
        links,
    )
    # patch
    patch_path = pathlib.Path("data/english/servant/patch.json")
    patch = load_patch(patch_path, logger)
    # servants
    servant_directory = pathlib.Path("data/english/servant")
    servants = get_servants(
        servant_directory,
        session,
        links,
        costumes,
        patch,
        logger,
        option,
    )
    # to English dictionary
    english_dictionary = to_dictionary(servants)
    dictionary_path = pathlib.Path("data/english/servant.json")
    if not option.no_save:
        logger.info('save english dictionary to "%s"', dictionary_path)
        fgo.save_json(dictionary_path, english_dictionary)


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
    no_save: bool
    no_patch: bool
    targets: list[int]
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
        "--no-save",
        dest="no_save",
        action="store_true",
        help="skip saving JSON files",
    )
    parser.add_argument(
        "--no-patch",
        dest="no_patch",
        action="store_true",
        help="skip applying patch file",
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="targets",
        nargs="+",
        action="extend",
        type=int,
        help="target servant id",
        metavar="SERVANT_ID",
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
) -> list[fgo.english.ServantLink]:
    if option.force_update or not path.exists():
        links = request_servant_links(
            session,
            logger,
            option.request_interval,
            option.request_timeout,
        )
        # save
        if not option.no_save:
            logger.info('save servant links to "%s"', path)
            fgo.save_json(path, links)
        time.sleep(option.request_interval)
    else:
        links = fgo.english.load_servant_links(path, logger=logger) or []
    return links


def request_servant_links(
    session: requests.Session,
    logger: logging.Logger,
    request_interval: float,
    request_timeout: float,
) -> list[fgo.english.ServantLink]:
    links: list[fgo.english.ServantLink] = []
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
) -> list[fgo.english.ServantLink]:
    links: list[fgo.english.ServantLink] = []
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
        url = urllib.parse.urljoin("https://fategrandorder.fandom.com", href)
        links.append(fgo.english.ServantLink(id=servant_id, url=url, title=title))
    return links


def get_costumes(
    directory: pathlib.Path,
    session: requests.Session,
    logger: logging.Logger,
    option: Option,
) -> list[fgo.english.CostumeData]:
    path = directory.joinpath("costume.json")
    if option.force_update or not path.exists():
        costume_types: list[fgo.english.CostumeType] = ["full", "simple"]
        costumes: list[fgo.english.CostumeData] = []
        for costume_type in costume_types:
            source = get_costume_data(
                costume_type,
                directory.joinpath(f"data/{costume_type}_costume.txt"),
                session,
                logger,
                option,
            )
            if source is None:
                continue
            costumes.extend(parse_costume_list(costume_type, source, logger))
        # sort by costume_id
        costumes.sort(key=lambda costume: costume["costume_id"])
        # save
        if not option.no_save:
            logger.info('save costumes to "%s"', path)
            fgo.save_json(path, costumes)
    else:
        costumes = fgo.load_json(path) or []
    return costumes


def get_costume_data(
    costume_type: fgo.english.CostumeType,
    path: pathlib.Path,
    session: requests.Session,
    logger: logging.Logger,
    option: Option,
) -> Optional[str]:
    if option.force_update or not path.exists():
        # request
        data = request_costume_list(
            costume_type,
            session,
            logger,
            option.request_timeout,
        )
        # save
        if not option.no_save and data is not None:
            logger.info('save costume list to "%s"', path)
            path.write_text(data, encoding="utf-8")
        time.sleep(option.request_interval)
    else:
        data = path.read_text(encoding="utf-8")
    return data


def request_costume_list(
    costume_type: fgo.english.CostumeType,
    session: requests.Session,
    logger: logging.Logger,
    request_timeout: float,
) -> Optional[str]:
    url = costume_list_url(costume_type)
    logger.info('request "%s"', url)
    response = session.get(
        url,
        params={"action": "edit"},
        timeout=request_timeout,
    )
    logger.debug("response: %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', url)
        return None
    root = lxml.html.fromstring(response.text)
    return root.xpath('//textarea[@name="wpTextbox1"]/text()')[0]


def costume_list_url(costume_type: fgo.english.CostumeType) -> str:
    match costume_type:
        case "full":
            return "https://fategrandorder.fandom.com/wiki/Sub:Costume_Dress/Full_Costume_List"
        case "simple":
            return "https://fategrandorder.fandom.com/wiki/Sub:Costume_Dress/Simple_Costume_List"


def parse_costume_list(
    costume_type: fgo.english.CostumeType,
    source: str,
    logger: logging.Logger,
) -> list[fgo.english.CostumeData]:
    costumes: list[fgo.english.CostumeData] = []
    for row in re.findall(
        r"(?<=\|-).+?(?=\|[-}])",
        source,
        flags=re.DOTALL,
    ):
        costumes.append(
            parse_costume_list_item(
                costume_type,
                row,
                logger,
            )
        )
    return costumes


def parse_costume_list_item(
    costume_type: fgo.english.CostumeType,
    text: str,
    logger: logging.Logger,
) -> fgo.english.CostumeData:
    cells = re.sub(
        r"({{.+?}}|\[\[.+?\]\]|(?P<delimiter>\|))",
        lambda x: "\t" if x.group("delimiter") else x.group(0),
        text.replace("\n", "").removeprefix("|"),
    ).split("\t")
    # costume id
    costume_id = int(cells[0])
    # servant & stage
    servant, stage = parse_costume_servant(cells[1], logger)
    # name
    name_jp, name_en = parse_costume_name(cells[2])
    logger.debug(
        'costume %d: servant="%s", jp="%s", en="%s"',
        costume_id,
        servant,
        name_jp,
        name_en,
    )
    # resource
    resource = parse_costume_resource(cells[5], costume_id, logger)
    return fgo.english.CostumeData(
        costume_id=costume_id,
        costume_type=costume_type,
        servant=servant,
        stage=stage,
        name={
            "en": name_en,
            "jp": name_jp,
        },
        resource=resource,
    )


def parse_costume_servant(
    text: str,
    logger: logging.Logger | fgo.ServantLogger,
) -> tuple[str, str]:
    match = re.match(
        r"{{(?P<servant>.+)\|stage=(?P<stage>.+)}}",
        text,
    )
    if match is None:
        logger.error('failed to parse servant and stage from "%s"', text)
        return "", ""
    return match.group("servant"), match.group("stage")


def parse_costume_name(
    text: str,
) -> tuple[str, str]:
    # {jp}<br>{en}
    if "<br>" in text:
        jp, en = text.split("<br>", maxsplit=1)
        # {{Ruby|(text)|(ruby)}}
        ruby_match = re.match(
            r"{{Ruby\|(?P<text>.+)\|(?P<ruby>.+)}}",
            jp,
        )
        if ruby_match:
            jp = ruby_match.group("text")
        # remove quotation ''...'' & replace <br> with space
        en = en.removeprefix("''").removesuffix("''").replace("<br>", " ")
        return jp, en
    # english name only
    return text, text


def parse_costume_resource(
    text: str,
    costume_id,
    logger: logging.Logger,
) -> fgo.Resource:
    resource = fgo.Resource(qp=0, items=[])
    for name, piece in re.findall(
        r"{{(?P<name>.+?)\|(?P<piece>[0-9]+M?)}}",
        text,
    ):
        number = int(piece.replace("M", "000000"))
        logger.debug(
            'costume %d: resouce "%s" x %d',
            costume_id,
            name,
            number,
        )
        if name == "QP":
            resource["qp"] = number
        else:
            resource["items"].append(
                fgo.Items(
                    name=name,
                    piece=number,
                )
            )
    return resource


def group_costumes_by_servant(
    costumes: list[fgo.english.CostumeData],
    links: list[fgo.english.ServantLink],
) -> dict[fgo.ServantID, list[fgo.english.CostumeData]]:
    link_to_id: dict[str, fgo.ServantID] = {
        urllib.parse.unquote(
            link["url"]
            .removeprefix("https://fategrandorder.fandom.com/wiki/")
            .removesuffix(".html")
            .replace("_", " ")
        ): link["id"]
        for link in links
    }
    result: dict[fgo.ServantID, list[fgo.english.CostumeData]] = {}
    for costume in costumes:
        servant_id = link_to_id.get(costume["servant"], None)
        if servant_id is not None:
            result.setdefault(servant_id, []).append(costume)
    return result


def load_patch(
    path: pathlib.Path,
    logger: logging.Logger,
) -> dict[fgo.ServantID, list[fgo.Patch]]:
    logger.info('load patch from "%s"', path)
    data = fgo.load_json(path)
    if data is None:
        logger.error('failed to load patch from "%s"', path)
        return {}
    return {int(servant_id): patch for servant_id, patch in data.items()}


def get_servants(
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    directory: pathlib.Path,
    session: requests.Session,
    links: list[fgo.english.ServantLink],
    costumes: dict[fgo.ServantID, list[fgo.english.CostumeData]],
    patches: dict[fgo.ServantID, list[fgo.Patch]],
    logger: logging.Logger,
    option: Option,
) -> dict[fgo.ServantID, fgo.english.Servant]:
    servants: dict[fgo.ServantID, fgo.english.Servant] = {}
    unplayable_ids = fgo.unplayable_servant_ids()
    for link in links:
        servant_id = link["id"]
        # check playable
        if servant_id in unplayable_ids:
            logger.info("skip unplayable servant %03d %s", link["id"], link["title"])
            continue
        # logger
        servant_logger = fgo.ServantLogger(logger, servant_id, link["title"])
        # get servant
        path = directory.joinpath(f"{servant_id:03d}.json")
        servant: Optional[fgo.english.Servant]
        if option.force_update or not path.exists():
            # get source
            source = get_servant_data(
                directory.joinpath(f"data/{servant_id:03d}.txt"),
                session,
                link,
                servant_logger,
                option,
            )
            if source is None:
                servant_logger.error("failed to get source")
                continue
            # parse source
            servant = parse_servant_data(
                link,
                source,
                costumes.get(servant_id, []),
                servant_logger,
            )
            # patch
            if not option.no_patch and servant_id in patches:
                fgo.apply_patches(
                    servant,
                    patches[servant_id],
                    logger=servant_logger,
                )
            # save
            if not option.no_save:
                servant_logger.info('save servant to "%s"', path)
                fgo.save_json(path, servant)
        else:
            # load from file
            servant = fgo.english.load_servant(path, logger=logger)
        if servant is not None:
            servants[servant["id"]] = servant
    return servants


def get_servant_data(
    path: pathlib.Path,
    session: requests.Session,
    link: fgo.english.ServantLink,
    logger: fgo.ServantLogger,
    option: Option,
) -> Optional[str]:
    if option.force_update or not path.exists():
        # request
        data = request_servant_data(
            session,
            link,
            logger,
            option.request_interval,
        )
        # save
        if not option.no_save and data is not None:
            logger.info(
                'save %03d %s data to "%s"',
                link["id"],
                link["title"],
                path,
            )
            path.write_text(data, encoding="utf-8")
        time.sleep(option.request_interval)
    else:
        data = load_servant_data(path, logger)
    return data


def request_servant_data(
    session: requests.Session,
    link: fgo.english.ServantLink,
    logger: fgo.ServantLogger,
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


def load_servant_data(
    path: pathlib.Path,
    logger: fgo.ServantLogger,
) -> Optional[str]:
    logger.info('load servant from "%s"', path)
    if not path.exists():
        logger.error('"%s" does not exist', path)
        return None
    return path.read_text(encoding="utf-8")


def parse_servant_data(
    link: fgo.english.ServantLink,
    source: str,
    costume_data: list[fgo.english.CostumeData],
    logger: fgo.ServantLogger,
) -> fgo.english.Servant:
    # false name
    false_name = parse_false_name(source, logger)
    # class
    servant_class = parse_servant_class(source, logger)
    # stars
    stars = parse_stars(source, logger)
    # active skills
    active_skills = parse_active_skills(source, logger)
    # append skills
    append_skills = parse_append_skills(source, logger)
    # ascension resources & costumes
    ascension_resources, costumes = parse_ascension_table(
        source,
        stars,
        costume_data,
        logger,
    )
    # active skill resource
    active_skill_resources = parse_active_skill_resources(source, stars, logger)
    # append skill resource
    append_skill_resources = parse_append_skill_resources(source, stars, logger)
    return fgo.english.Servant(
        id=link["id"],
        name=link["title"],
        false_name=false_name,
        klass=servant_class,
        rarity=stars,
        active_skills=active_skills,
        append_skills=append_skills,
        costumes=costumes,
        ascension_resources=ascension_resources,
        active_skill_resources=active_skill_resources,
        append_skill_resources=append_skill_resources,
    )


def parse_false_name(
    source: str,
    logger: fgo.ServantLogger,
) -> Optional[str]:
    match = re.search(
        r"\|aka = .?\{\{Tooltip\|Before True Name Reveal\|(?P<name>.+?)\}\}",
        source,
    )
    if match is None:
        return None
    false_name = match.group("name")
    logger.debug('false name "%s"', false_name)
    return false_name


def parse_servant_class(
    source: str,
    logger: fgo.ServantLogger,
) -> str:
    match = re.search(
        r"\|class = (?P<class>.+)",
        source,
    )
    if match is None:
        logger.error("failed to get class")
        return ""
    servant_class = match.group("class").replace(" ", "")
    logger.debug('class "%s"', servant_class)
    return servant_class


def parse_stars(
    source: str,
    logger: fgo.ServantLogger,
) -> int:
    match = re.search(
        r"\|stars = (?P<stars>[0-5])",
        source,
    )
    if match is None:
        logger.error("failed to get stars")
        return -1
    stars = int(match.group("stars"))
    logger.debug("stars %d", stars)
    return stars


def parse_active_skills(
    source: str,
    logger: fgo.ServantLogger,
) -> list[list[fgo.english.Skill]]:
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
    logger: fgo.ServantLogger,
) -> list[list[fgo.english.Skill]]:
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
    logger: fgo.ServantLogger,
) -> list[fgo.english.Skill]:
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
    logger.debug("[%s] %s", target, repr(skill))
    return skill


def parse_skill_rank(text: str) -> fgo.english.Skill:
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
    match = re.match(rf"^(?P<name>.+)\|(?P<rank>{rank_pattern})\s*$", text)
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
    return to_skill(text, "")


def to_skill(name: str, rank: str) -> fgo.english.Skill:
    # remove (Active Skill)
    name = name.removesuffix(" (Active Skill)")
    return fgo.english.Skill(
        name=name,
        rank=rank if rank != "None" else "",
    )


def parse_ascension_table(
    source: str,
    stars: int,
    costume_data: list[fgo.english.CostumeData],
    logger: fgo.ServantLogger,
) -> tuple[list[fgo.Resource], list[fgo.english.Costume]]:
    logger.debug("ascension & costume")
    section = parse_section(source, "Ascension")
    if section is None:
        return [], []
    rows = parse_resource_table(section, "Ascension", logger)
    if rows is None:
        return [], []
    ascension_resources = to_ascension_resources(rows, stars)
    costumes = to_costumes(rows, costume_data, logger)
    return ascension_resources, costumes


def parse_active_skill_resources(
    source: str,
    stars: int,
    logger: fgo.ServantLogger,
) -> list[fgo.Resource]:
    logger.debug("active skill resources")
    section = parse_section(source, "Skill Reinforcement")
    if section is None:
        return []
    match = re.search(
        r"Active( Skills)?\s*=(?P<table>.+?)\|-\|",
        section,
        flags=re.DOTALL,
    )
    if match is None:
        return []
    rows = parse_resource_table(
        match.group("table"),
        "Skillreinforcement",
        logger,
    )
    if rows is None:
        return []
    return to_skill_resources(rows, stars)


def parse_append_skill_resources(
    source: str,
    stars: int,
    logger: fgo.ServantLogger,
) -> list[fgo.Resource]:
    logger.debug("append skill resources")
    section = parse_section(source, "Skill Reinforcement")
    if section is None:
        return []
    match = re.search(
        r"Append( Skills)?\s*=(?P<table>.+?)</tabber>",
        section,
        flags=re.DOTALL,
    )
    if match is None:
        return []
    rows = parse_resource_table(
        match.group("table"),
        "Skillreinforcement",
        logger,
    )
    if rows is None:
        return []
    return to_skill_resources(rows, stars)


def parse_section(
    source: str,
    title: str,
) -> Optional[str]:
    match = re.search(
        rf"==\s*{title}\s*==(?P<section>.*?)==",
        source,
        flags=re.DOTALL,
    )
    if match is None:
        return None
    return match.group("section")


@dataclasses.dataclass(frozen=True)
class ItemsRow:
    index: int
    key: int
    item: str
    piece: int


@dataclasses.dataclass(frozen=True)
class QPRow:
    index: int
    key: Literal["qp"]
    value: int


@dataclasses.dataclass(frozen=True)
class TextRow:
    index: int
    key: str
    text: str


type ResourceTableRow = ItemsRow | QPRow | TextRow


def parse_resource_table(
    source: str,
    title: str,
    logger: fgo.ServantLogger,
) -> Optional[list[ResourceTableRow]]:
    body = re.search(
        rf"{{{{{title}"
        r"(?P<body>(\|[a-z0-9]+\s*=\s*({{.+?}}|(\[\[.*?\]\]|[^|])*))+)}}",
        source.replace("\n", ""),
    )
    if body is None:
        return None
    result: list[ResourceTableRow] = []
    for row in re.findall(
        r"\|.+?\s*=\s*(?:{{.+?}}|(?:\[\[.*?\]\]|[^|])*)",
        body.group("body"),
    ):
        value = parse_resource_table_row(row)
        logger.debug("%s", value)
        if value is not None:
            result.append(value)
    return result


def parse_resource_table_row(row: str) -> Optional[ItemsRow | QPRow | TextRow]:
    match = re.match(
        r"\|(?P<index>[0-9]+)(?P<key>([1-4]|qp|name|jdef|ndef|icon))"
        r"\s*=\s*"
        r"(({{(?P<item>[^|]+?)(\|(?P<piece>[0-9,]+)?\s*)?\}\})|(?P<text>.+))",
        row,
    )
    if match is None:
        return None
    index = int(match.group("index"))
    match match.group("key"):
        case "1" | "2" | "3" | "4":
            item = match.group("item")
            piece = match.group("piece")
            if item is not None:
                return ItemsRow(
                    index=index,
                    key=int(match.group("key")),
                    item=item.strip(),
                    piece=int(piece) if piece is not None else 1,
                )
        case "qp":
            if match.group("piece") is not None:
                return QPRow(
                    index=index,
                    key="qp",
                    value=int(match.group("piece").replace(",", "")),
                )
        case _:
            if match.group("text") is not None:
                return TextRow(
                    index=index,
                    key=match.group("key"),
                    text=match.group("text").strip(),
                )
    return None


def to_ascension_resources(
    rows: list[ResourceTableRow],
    stars: int,
) -> list[fgo.Resource]:
    resources = [fgo.Resource(qp=0, items=[]) for _ in range(4)]
    for row in rows:
        index = row.index - 1
        if not 0 <= index <= 3:
            continue
        match row:
            case ItemsRow(item=item, piece=piece):
                resources[index]["items"].append(fgo.Items(name=item, piece=piece))
    # set QP
    for i, qp in enumerate(ascension_qp(stars)):
        if resources[i]["items"] and resources[i]["qp"] == 0:
            resources[i]["qp"] = qp
    return resources


def to_skill_resources(
    rows: list[ResourceTableRow],
    stars: int,
) -> list[fgo.Resource]:
    resources = [fgo.Resource(qp=0, items=[]) for _ in range(9)]
    for row in rows:
        index = row.index - 1
        if not 0 <= index <= 8:
            continue
        match row:
            case ItemsRow(item=item, piece=piece):
                resources[index]["items"].append(fgo.Items(name=item, piece=piece))
    # set QP
    for i, qp in enumerate(skill_reinforcement_qp(stars)):
        if resources[i]["items"] and resources[i]["qp"] == 0:
            resources[i]["qp"] = qp
    return resources


class CostumeData(TypedDict, total=False):
    name: str
    stage: str
    text_en: str
    text_jp: str
    items: list[fgo.Items]
    qp: int


def to_costumes(
    rows: list[ResourceTableRow],
    costume_data: list[fgo.english.CostumeData],
    logger: fgo.ServantLogger,
) -> list[fgo.english.Costume]:
    # parse rows
    costumes = parse_costume_rows(rows, logger)
    # to costumes
    result: list[fgo.english.Costume] = []
    for costume in costumes:
        if "stage" not in costume:
            continue
        data = next(
            (data for data in costume_data if data["stage"] == costume["stage"]),
            None,
        )
        if data is None:
            logger.error('failed to get "%s" from costume data', costume["stage"])
            continue
        value = to_costume(data, costume, logger)
        if value is not None:
            result.append(value)
    # sort by id
    result.sort(key=lambda costume: costume["id"])
    return result


def parse_costume_rows(
    rows: list[ResourceTableRow],
    logger: fgo.ServantLogger,
) -> list[CostumeData]:
    data: dict[int, CostumeData] = {}
    for row in rows:
        if row.index <= 4:
            continue
        match row:
            case ItemsRow(index=index, item=item, piece=piece):
                items = fgo.Items(name=item, piece=piece)
                data.setdefault(index, {}).setdefault("items", []).append(items)
            case QPRow(index=index, value=value):
                data.setdefault(index, {})["qp"] = value
            case TextRow(index=index, key=key, text=text):
                match key:
                    case "name":
                        name = re.sub("<br/?>", " ", text)
                        data.setdefault(index, {})["name"] = name
                    case "icon":
                        stage = parse_costume_servant(text, logger)[1]
                        data.setdefault(index, {})["stage"] = stage
                    case "jdef":
                        text_jp = re.sub("<br/?>", "\n", text)
                        data.setdefault(index, {})["text_jp"] = text_jp
                    case "ndef":
                        text_en = re.sub("<br/?>", "\n", text)
                        data.setdefault(index, {})["text_en"] = text_en
    return list(data.values())


def to_costume(
    data_from_list: fgo.english.CostumeData,
    data_from_servant: CostumeData,
    logger: fgo.ServantLogger,
) -> Optional[fgo.english.Costume]:
    costume_id = data_from_list["costume_id"]
    # check stage
    if data_from_list["stage"] != data_from_servant.get("stage", ""):
        logger.error("costume %d: stage do not match", costume_id)
        return None
    # compare name
    if data_from_list["name"]["en"] != data_from_servant.get("name", ""):
        logger.warning(
            'costume %d: name.en do not match ("%s" != "%s")',
            costume_id,
            data_from_list["name"]["en"],
            data_from_servant.get("name", ""),
        )
    # compare resource
    if data_from_list["resource"]["qp"] != data_from_servant.get("qp", 0):
        logger.warning(
            "cotume %s: resource.qp do not match (%d != %d)",
            costume_id,
            data_from_list["resource"]["qp"],
            data_from_servant.get("qp", 0),
        )
    if data_from_list["resource"]["items"] != data_from_servant.get("items", []):
        logger.warning(
            "costume %d: resource.items do not match (%s != %s)",
            costume_id,
            data_from_list["resource"]["items"],
            data_from_servant.get("items", []),
        )
    return fgo.english.Costume(
        id=data_from_list["costume_id"],
        type=data_from_list["costume_type"],
        name=data_from_list["name"],
        flavor_text={
            "en": data_from_servant.get("text_en", ""),
            "jp": data_from_servant.get("text_jp", ""),
        },
        resource=data_from_list["resource"],
    )


def ascension_qp(stars: int) -> list[int]:
    table: list[list[int]] = [
        [0, 0, 0, 0],
        [10000, 30000, 90000, 300000],
        [15000, 45000, 150000, 450000],
        [30000, 100000, 300000, 900000],
        [50000, 150000, 500000, 1500000],
        [100000, 300000, 1000000, 3000000],
    ]
    row: int = 0
    match stars:
        case 1 | 2 | 3 | 4 | 5:
            row = stars
        case 0:
            row = 2
    return table[row]


def skill_reinforcement_qp(stars: int) -> list[int]:
    base_qp: list[int] = [
        10000,
        20000,
        60000,
        80000,
        200000,
        250000,
        500000,
        600000,
        1000000,
    ]
    factor: float = 0.0
    match stars:
        case 1:
            factor = 1.0
        case 2 | 0:
            factor = 2.0
        case 3:
            factor = 5.0
        case 4:
            factor = 10.0
        case 5:
            factor = 20.0
    return [int(qp * factor) for qp in base_qp]


def to_dictionary(
    servants: dict[fgo.ServantID, fgo.english.Servant],
) -> fgo.ServantDictionary:
    return {
        servant_id: to_dictionary_value(servant)
        for servant_id, servant in servants.items()
    }


def to_dictionary_value(
    servant: fgo.english.Servant,
) -> fgo.ServantDictionaryValue:
    return fgo.ServantDictionaryValue(
        name=servant["name"],
        false_name=servant["false_name"],
        skills=[
            [skill["name"] for skill in skill_n] for skill_n in servant["active_skills"]
        ],
        append_skills=[
            [skill["name"] for skill in skill_n] for skill_n in servant["append_skills"]
        ],
        costumes=[costume["name"]["en"] for costume in servant["costumes"]],
    )


if __name__ == "__main__":
    main()
