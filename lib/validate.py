from __future__ import annotations

import logging
import pathlib
import re
from typing import TYPE_CHECKING, Literal

import jsonschema

from .io import load_json
from .schema import servant as servant_schema

if TYPE_CHECKING:
    from .servant import AppendSkills, Costume, Servant, Skill, Skills

_logger = logging.getLogger(__name__)


def validate_servant(servant: Servant) -> bool:
    result = True
    prefix = "[{0}: {1}]".format(
        servant.get("id", "None"),
        servant.get("name", "None"),
    )
    # validate with JSONSchema
    try:
        jsonschema.validate(instance=servant, schema=servant_schema())
    except jsonschema.exceptions.ValidationError as error:
        _logger.error(f"{prefix} JSONSchema validaton error\n{error}")
        return False
    # check skills
    if not validate_skills(prefix, servant["skills"]):
        result = False
    if not validate_append_skills(prefix, servant["append_skills"]):
        result = False
    # check costumes
    if not _validate_costumes(prefix, servant["costumes"]):
        result = False
    return result


def validate_servants(
    directory: pathlib.Path,
    *,
    halt_on_error: bool = False,
) -> bool:
    result = True
    for file in _servant_files(directory):
        # load
        _logger.info(f"load {file}")
        servant = load_json(file)
        if servant is None:
            _logger.info(f"failed to load {file}")
            result = False
            if halt_on_error:
                return result
            continue
        # validate servant
        if not validate_servant(servant):
            result = False
            if halt_on_error:
                return result
    return result


def validate_skills(
    prefix: str,
    skills: Skills,
) -> bool:
    result = True
    # slots
    if len(skills) != 3:
        result = False
        logger.error(f"{prefix} skills require 3 slots")
    # skill
    for i, skill in enumerate(skills):
        if not _validate_skill_n(i + 1, skills[i], _logger, prefix, "skill"):
            result = False
    return result


def validate_append_skills(
    prefix: str,
    skills: AppendSkills,
) -> bool:
    result = True
    # slots
    if len(skills) != 5:
        result = False
        logger.error(f"{prefix} append skills require 5 slots")
    # append skill
    for i, skill in enumerate(skills):
        if not _validate_skill_n(i + 1, skills[i], _logger, prefix, "append_skill"):
            result = False
    return result


def _validate_skill_n(
    slot: int,
    skill_n: list[Skill],
    logger: logging.Logger,
    prefix: str,
    target: Literal["skill", "append_skill"],
) -> bool:
    result = True
    # size
    if not skill_n:
        result = False
        logger.error(f"{prefix} {target} {slot} is empty")
    # slot
    if any(skill["slot"] != slot for skill in skill_n):
        result = False
        logger.error(f"{prefix} exist unexpected slot in {target} {slot}")
    # level
    levels = [skill["level"] for skill in skill_n]
    if levels != list(range(1, len(levels) + 1)):
        result = False
        logger.error(f"{prefix} levels are not consective in {target} {slot}")
    return result


def _validate_costumes(
    prefix: str,
    costumes: list[Costume],
) -> bool:
    costume_ids = [costume["id"] for costume in costumes]
    result = costume_ids == sorted(set(costume_ids))
    if not result:
        _logger.error(f"{prefix} costume IDs are not sorted")
    return result


def _servant_files(directory: pathlib.Path) -> list[pathlib.Path]:
    files = [
        file for file in directory.iterdir() if re.match(r"[0-9]{3}\.json", file.name)
    ]
    return sorted(files)
