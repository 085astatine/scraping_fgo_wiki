#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
import re
import time
import unicodedata
from typing import Literal, Optional, TypedDict

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
    # update servants
    update_servants(
        directory,
        session,
        links,
        group_costumes_by_servant(costumes),
        logger,
        option,
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


def group_costumes_by_servant(
    costumes: list[Costume],
) -> dict[lib.ServantID, list[lib.Costume]]:
    result: dict[lib.ServantID, list[lib.Costume]] = {}
    for costume in costumes:
        result.setdefault(costume["servant_id"], []).append(
            lib.Costume(
                id=costume["costume_id"],
                name=costume["name"],
                resource=costume["resource"],
            )
        )
    return result


def update_servants(
    directory: pathlib.Path,
    session: requests.Session,
    links: list[ServantLink],
    costumes: dict[lib.ServantID, list[lib.Costume]],
    logger: logging.Logger,
    option: Option,
) -> None:
    for link in links:
        path = directory.joinpath(f"{link['id']:03d}.json")
        if option.force_update or not path.exists():
            servant = request_servant(
                session,
                link,
                costumes.get(link["id"], []),
                lib.ServantLogger(logger, link["id"], link["name"]),
            )
            if servant is not None:
                logger.info(
                    'save servant %03d %s to "%s"',
                    servant["id"],
                    servant["name"],
                    path,
                )
                lib.save_json(path, servant)
            time.sleep(option.request_interval)
        else:
            logger.info("skip updating %03d %s", link["id"], link["name"])


def request_servant(
    session: requests.Session,
    link: ServantLink,
    costumes: list[lib.Costume],
    logger: lib.ServantLogger,
) -> Optional[lib.Servant]:
    logger.info('request "%s"', link["url"])
    response = session.get(link["url"])
    logger.debug("response %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', link["url"])
        return None
    root = lxml.html.fromstring(response.text)
    return parse_servant_page(root, link, costumes, logger)


def parse_servant_page(
    root: lxml.html.HtmlElement,
    link: ServantLink,
    costumes: list[lib.Costume],
    logger: lib.ServantLogger,
) -> lib.Servant:
    # skills
    logger.debug("skills")
    skills = parse_skills(root, logger)
    # append skills
    logger.debug("append skills")
    append_skills = parse_append_skills(root, logger)
    # ascension rescources
    logger.debug("ascension resources")
    ascension_resources = parse_ascension_resources(root, logger)
    # skill rsources
    logger.debug("skill resources")
    skill_resources = parse_skill_resources(root, logger)
    # append skill resources
    logger.debug("append skill resources")
    append_skill_resources = parse_append_skill_resources(root, logger)
    return lib.Servant(
        id=link["id"],
        name=link["name"],
        false_name=None,
        klass=link["klass"],
        rarity=link["rarity"],
        skills=skills,
        append_skills=append_skills,
        costumes=costumes,
        ascension_resources=ascension_resources,
        skill_resources=skill_resources,
        append_skill_resources=append_skill_resources,
    )


def parse_skills(
    root: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> lib.Skills:
    skills: lib.Skills = [[] for _ in range(3)]
    for node in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="保有スキル"]'
        "/following-sibling::h4"
    ):
        skill = parse_skill(node, logger)
        if skill is None:
            continue
        logger.debug(
            'skill %d-%d: "%s" (rank: "%s", icon: %d)',
            skill["slot"],
            skill["level"],
            skill["name"],
            skill["rank"],
            skill["icon"],
        )
        skills[skill["slot"] - 1].append(skill)
    # check
    lib.validate_skills(skills, logger)
    return skills


def parse_append_skills(
    root: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> lib.AppendSkills:
    skills: lib.AppendSkills = [[] for _ in range(5)]
    for node in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="アペンドスキル"]'
        "/following-sibling::div/h4"
    ):
        skill = parse_skill(node, logger)
        if skill is None:
            continue
        logger.debug(
            'append skill %d-%d: "%s" (rank: "%s", icon: %d)',
            skill["slot"],
            skill["level"],
            skill["name"],
            skill["rank"],
            skill["icon"],
        )
        skills[skill["slot"] - 1].append(skill)
    # check
    lib.validate_append_skills(skills, logger)
    return skills


def parse_skill(
    node: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> Optional[lib.Skill]:
    match = re.match(
        r"Skill(?P<slot>[0-9+])"
        r"(?P<upgraded>\[強化後(?P<level>[0-9]+)?\])?"
        r"：(?P<name>.+)",
        node.text_content().strip(),
    )
    if not match:
        return None
    slot = int(match.group("slot"))
    level = (
        1
        if match.group("upgraded") is None
        else 2 if match.group("level") is None else int(match.group("level")) + 1
    )
    # name rank
    name, rank = parse_skill_rank(match.group("name"))
    # icon
    icon = parse_skill_icon(
        node.xpath("following-sibling::div[1]/table//td[@rowspan]")[0],
        logger,
    )
    return lib.Skill(
        slot=slot,
        level=level,
        name=name,
        rank=rank,
        icon=icon,
    )


def parse_skill_rank(name: str) -> tuple[str, str]:
    # half width katakana -> full width katakana
    name = re.sub(
        r"[\uff66-\uff9f]+",  # \uff66: ｦ - \uff9f: ﾟ
        lambda x: unicodedata.normalize("NFKC", x.group(0)),
        name,
    )
    # rank
    rank = ""
    match = re.match(r"(?P<name>.+)\s+(?P<rank>(EX|[A-E])[+-]*)", name)
    if match:
        name = match.group("name").strip()
        rank = match.group("rank")
    return (name, rank)


def parse_skill_icon(
    node: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> int:
    text = node.text_content().strip()
    match = re.match(r"(?P<id>[0-9]+)(,(?P<rank>.+))?", text)
    if match is None:
        logger.warning('faild to parse as a skill icon "%s"', text)
        return 0
    return int(match.group("id"))


def parse_ascension_resources(
    root: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    parser = ResourceSetParser(mode="ascension", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="霊基再臨"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


def parse_skill_resources(
    root: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    parser = ResourceSetParser(mode="skill", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="スキル強化"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


def parse_append_skill_resources(
    root: lxml.html.HtmlElement,
    logger: lib.ServantLogger,
) -> list[lib.ResourceSet]:
    parser = ResourceSetParser(mode="skill", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="アペンドスキル強化"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


class ResourceSetParser:
    def __init__(
        self,
        mode: Literal["ascension", "skill"],
        logger: lib.ServantLogger,
    ) -> None:
        self._mode = mode
        self._logger = logger
        self._result: list[lib.ResourceSet] = []
        self._level: Optional[int] = None
        self._resources: list[lib.Resource] = []

    def push(self, cell: lxml.html.HtmlElement):
        text = cell.text_content().strip()
        if not text:
            return
        # level
        if self._parse_level(text):
            return
        # resource
        if self._level is not None:
            self._resources.extend(parse_resource(text, self._logger))

    def result(self) -> list[lib.ResourceSet]:
        if self._level is not None:
            self._pack()
        return self._result

    def _pack(self) -> None:
        self._result.append(to_resource_set(self._resources))
        self._resources = []

    def _parse_level(self, text) -> bool:
        level: Optional[int] = None
        # parse
        if self._mode == "ascension":
            level = parse_ascension_level(text)
        elif self._mode == "skill":
            level = parse_skill_level(text)
        # pack
        if level is not None:
            self._logger.debug("Lv.%d -> Lv.%d", level, level + 1)
            if self._level is not None:
                self._pack()
            self._level = level
            return True
        return False


def to_resource_set(resources: list[lib.Resource]) -> lib.ResourceSet:
    result = lib.ResourceSet(qp=0, resources=[])
    for resource in resources:
        if resource["name"] == "QP":
            result["qp"] += resource["piece"]
        else:
            result["resources"].append(resource)
    return result


def parse_resource(
    text: str,
    logger: lib.ServantLogger,
) -> list[lib.Resource]:
    result: list[lib.Resource] = []
    regexp = re.compile(r"(?P<item>.+),x?(?P<piece>[0-9万]+)")
    match = regexp.search(text)
    while match:
        resource = lib.Resource(
            name=match.group("item"),
            piece=int(match.group("piece").replace("万", "0000")),
        )
        logger.debug("resource %s x %d", resource["name"], resource["piece"])
        result.append(resource)
        text = regexp.sub("", text, count=1)
        match = regexp.search(text)
    return result


def parse_ascension_level(text: str) -> Optional[int]:
    match = re.match(r"(?P<level>[0-9]+)段階", text)
    if match:
        return int(match.group("level"))
    return None


def parse_skill_level(text: str) -> Optional[int]:
    match = re.match(r"Lv(?P<current>[0-9]+)→Lv(?P<next>[0-9]+)", text)
    if match:
        level = int(match.group("current"))
        next_level = int(match.group("next"))
        assert level + 1 == next_level
        return level
    return None


if __name__ == "__main__":
    main()
