#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import logging
import pathlib
import re
import time
import unicodedata
from typing import Literal, Optional

import fake_useragent
import lxml.html
import requests

import fgo


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
    if option.targets:
        links = [link for link in links if link["id"] in option.targets]
    # servant names
    servant_names_path = directory.joinpath("name.json")
    servant_names = {
        name["id"]: name
        for name in fgo.load_servant_names(servant_names_path, logger=logger) or []
    }
    # costumes
    costumes_path = directory.joinpath("costumes.json")
    costumes = group_costumes_by_servant(
        fgo.load_costumes(costumes_path, logger=logger)
    )
    # patch
    patch_path = directory.joinpath("patch.json")
    patch = load_patch(patch_path, logger)
    # update servants
    update_servants(
        directory,
        session,
        links,
        servant_names,
        costumes,
        patch,
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
    no_save: bool
    targets: list[int]
    request_interval: float
    request_timeout: float


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update Servant Data",
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
) -> list[fgo.ServantLink]:
    if option.force_update or not path.exists():
        links = request_servant_links(session, logger, option.request_timeout)
        if not option.no_save:
            logger.info('save servant links to "%s"', path)
            fgo.save_json(path, links)
        time.sleep(option.request_interval)
    else:
        links = fgo.load_servant_links(path, logger=logger) or []
    return links


def request_servant_links(
    session: requests.Session,
    logger: logging.Logger,
    request_timeout: float,
) -> list[fgo.ServantLink]:
    url = "https://w.atwiki.jp/f_go/pages/713.html"
    logger.info('request: "%s"', url)
    response = session.get(url, timeout=request_timeout)
    logger.debug("reqponse %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', url)
        return []
    root = lxml.html.fromstring(response.text)
    return parse_servant_links(root, logger)


def parse_servant_links(
    root: lxml.html.HtmlElement,
    logger: logging.Logger,
) -> list[fgo.ServantLink]:
    unplayable_ids = fgo.unplayable_servant_ids()
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
    links: list[fgo.ServantLink] = []
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
        link = fgo.ServantLink(
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


def group_costumes_by_servant(
    costumes: Optional[list[fgo.CostumeData]],
) -> dict[fgo.ServantID, list[fgo.Costume]]:
    if costumes is None:
        return {}
    result: dict[fgo.ServantID, list[fgo.Costume]] = {}
    for costume in costumes:
        result.setdefault(costume["servant_id"], []).append(
            fgo.Costume(
                id=costume["costume_id"],
                name=costume["name"],
                resource=costume["resource"],
            )
        )
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


def update_servants(
    ## pylint: disable=too-many-arguments, too-many-positional-arguments
    directory: pathlib.Path,
    session: requests.Session,
    links: list[fgo.ServantLink],
    servant_names: dict[fgo.ServantID, fgo.ServantName],
    costumes: dict[fgo.ServantID, list[fgo.Costume]],
    patches: dict[fgo.ServantID, list[fgo.Patch]],
    logger: logging.Logger,
    option: Option,
) -> None:
    for link in links:
        path = directory.joinpath(f"{link['id']:03d}.json")
        servant_logger = fgo.ServantLogger(logger, link["id"], link["name"])
        if option.force_update or not path.exists():
            page_text = servant_page(
                session,
                directory.joinpath(f"page/{link['id']:03d}.html"),
                link,
                servant_logger,
                option,
            )
            if page_text is None:
                logger.error("failed to get page data")
                continue
            servant = parse_servant_page(
                lxml.html.fromstring(page_text),
                link,
                servant_names.get(link["id"], None),
                costumes.get(link["id"], []),
                servant_logger,
            )
            # patch
            if link["id"] in patches:
                fgo.apply_patches(
                    servant,
                    patches[link["id"]],
                    logger=servant_logger,
                )
            if not option.no_save and servant is not None:
                logger.info(
                    'save servant %03d %s to "%s"',
                    servant["id"],
                    servant["name"],
                    path,
                )
                fgo.save_json(path, servant)
        else:
            logger.info("skip updating %03d %s", link["id"], link["name"])


def servant_page(
    session: requests.Session,
    path: pathlib.Path,
    link: fgo.ServantLink,
    logger: fgo.ServantLogger,
    option: Option,
) -> Optional[str]:
    if option.force_update or not path.exists():
        # request
        text = request_servant_page(
            session,
            link,
            logger,
            option.request_timeout,
        )
        # save
        if not option.no_save and text is not None:
            logger.info('save page to "%s"', path)
            path.write_text(text, encoding="utf-8")
        time.sleep(option.request_interval)
    else:
        # load page
        logger.info('load page from "%s"', path)
        text = path.read_text(encoding="utf-8")
    return text


def request_servant_page(
    session: requests.Session,
    link: fgo.ServantLink,
    logger: fgo.ServantLogger,
    request_timeout: float,
) -> Optional[str]:
    response = session.get(link["url"], timeout=request_timeout)
    logger.debug("response %d", response.status_code)
    if not response.ok:
        logger.error('failed to request "%s"', link["url"])
        return None
    return response.text


def parse_servant_page(
    root: lxml.html.HtmlElement,
    link: fgo.ServantLink,
    servant_name: Optional[fgo.ServantName],
    costumes: list[fgo.Costume],
    logger: fgo.ServantLogger,
) -> fgo.Servant:
    # name, false_name, ascension_names
    servant_name = servant_name or fgo.ServantName(id=link["id"])
    name = servant_name.get("name", None) or link["name"]
    false_name = servant_name.get("false_name", None)
    ascension_names = servant_name.get("ascension_names", None)
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
    return fgo.Servant(
        id=link["id"],
        name=name,
        false_name=false_name,
        ascension_names=ascension_names,
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
    logger: fgo.ServantLogger,
) -> fgo.Skills:
    skills: fgo.Skills = [[] for _ in range(3)]
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
    fgo.validate_skills(skills, logger)
    return skills


def parse_append_skills(
    root: lxml.html.HtmlElement,
    logger: fgo.ServantLogger,
) -> fgo.AppendSkills:
    skills: fgo.AppendSkills = [[] for _ in range(5)]
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
    fgo.validate_append_skills(skills, logger)
    return skills


def parse_skill(
    node: lxml.html.HtmlElement,
    logger: fgo.ServantLogger,
) -> Optional[fgo.Skill]:
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
    return fgo.Skill(
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
    logger: fgo.ServantLogger,
) -> int:
    text = node.text_content().strip()
    match = re.match(r"(?P<id>[0-9]+)(,(?P<rank>.+))?", text)
    if match is None:
        logger.warning('faild to parse as a skill icon "%s"', text)
        return 0
    return int(match.group("id"))


def parse_ascension_resources(
    root: lxml.html.HtmlElement,
    logger: fgo.ServantLogger,
) -> list[fgo.Resource]:
    parser = ResourceParser(mode="ascension", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="霊基再臨"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


def parse_skill_resources(
    root: lxml.html.HtmlElement,
    logger: fgo.ServantLogger,
) -> list[fgo.Resource]:
    parser = ResourceParser(mode="skill", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="スキル強化"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


def parse_append_skill_resources(
    root: lxml.html.HtmlElement,
    logger: fgo.ServantLogger,
) -> list[fgo.Resource]:
    parser = ResourceParser(mode="skill", logger=logger)
    for cell in root.xpath(
        '//div[@id="wikibody"]'
        '//h3[normalize-space()="アペンドスキル強化"]'
        "/following-sibling::div[1]/div/table[1]/tbody/tr/td"
    ):
        parser.push(cell)
    return parser.result()


class ResourceParser:
    def __init__(
        self,
        mode: Literal["ascension", "skill"],
        logger: fgo.ServantLogger,
    ) -> None:
        self._mode = mode
        self._logger = logger
        self._result: list[fgo.Resource] = []
        self._level: Optional[int] = None
        self._items: list[fgo.Items] = []

    def push(self, cell: lxml.html.HtmlElement):
        text = cell.text_content().strip()
        if not text:
            return
        # level
        if self._parse_level(text):
            return
        # items
        if self._level is not None:
            self._items.extend(parse_items(text, self._logger))

    def result(self) -> list[fgo.Resource]:
        if self._level is not None:
            self._pack()
        return self._result

    def _pack(self) -> None:
        self._result.append(to_resource(self._items))
        self._items = []

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


def to_resource(items: list[fgo.Items]) -> fgo.Resource:
    result = fgo.Resource(qp=0, items=[])
    for item in items:
        if item["name"] == "QP":
            result["qp"] += item["piece"]
        else:
            result["items"].append(item)
    return result


def parse_items(
    text: str,
    logger: fgo.ServantLogger,
) -> list[fgo.Items]:
    result: list[fgo.Items] = []
    regexp = re.compile(r"(?P<item>.+),x?(?P<piece>[0-9万]+)")
    match = regexp.search(text)
    while match:
        items = fgo.Items(
            name=match.group("item"),
            piece=int(match.group("piece").replace("万", "0000")),
        )
        logger.debug("items %s x %d", items["name"], items["piece"])
        result.append(items)
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
