from __future__ import annotations

import logging
from typing import Literal, Optional

import jsonschema

from .schema import servant as servant_schema
from .servant import ServantLogger
from .types import AppendSkills, Costume, Servant, Skill, Skills


def validate_servant(
    servant: Servant,
    logger: ServantLogger,
) -> bool:
    logger.info("start validation")
    result = True
    # validate with JSONSchema
    try:
        jsonschema.validate(instance=servant, schema=servant_schema())
    except jsonschema.exceptions.ValidationError as error:
        logger.error("JSONSchema validaton error %s", error)
        return False
    # check skills
    if not validate_skills(servant["skills"], logger):
        result = False
    # check append skills
    if not validate_append_skills(servant["append_skills"], logger):
        result = False
    # check costumes
    if not _validate_costumes(servant["costumes"], logger):
        result = False
    return result


def validate_servants(
    servants: list[Servant],
    *,
    logger: Optional[logging.Logger] = None,
    halt_on_error: bool = False,
) -> bool:
    logger = logger or logging.getLogger(__name__)
    result = True
    for servant in servants:
        if not validate_servant(
            servant,
            ServantLogger(logger, servant["id"], servant["name"]),
        ):
            # validate servant
            result = False
        if halt_on_error:
            break
    return result


def validate_skills(
    skills: Skills,
    logger: ServantLogger,
) -> bool:
    result = True
    # slots
    if len(skills) != 3:
        result = False
        logger.error("skills require 3 slots")
    # skill
    for i, skill in enumerate(skills):
        if not _validate_skill_n("skill", i + 1, skill, logger):
            result = False
    return result


def validate_append_skills(
    skills: AppendSkills,
    logger: ServantLogger,
) -> bool:
    result = True
    # slots
    if len(skills) != 5:
        result = False
        logger.error("append skills require 5 slots")
    # append skill
    for i, skill in enumerate(skills):
        if not _validate_skill_n("append skill", i + 1, skill, logger):
            result = False
    return result


def _validate_skill_n(
    target: Literal["skill", "append skill"],
    slot: int,
    skill_n: list[Skill],
    logger: ServantLogger,
) -> bool:
    result = True
    # size
    if not skill_n:
        result = False
        logger.error("%s %d is empty", target, slot)
    # slot
    if any(skill["slot"] != slot for skill in skill_n):
        result = False
        logger.error("exist unexpected slot in %s %d", target, slot)
    # level
    levels = [skill["level"] for skill in skill_n]
    if levels != list(range(1, len(levels) + 1)):
        result = False
        logger.error("levels are not consective in %s %d", target, slot)
    return result


def _validate_costumes(
    costumes: list[Costume],
    logger: ServantLogger,
) -> bool:
    costume_ids = [costume["id"] for costume in costumes]
    result = costume_ids == sorted(set(costume_ids))
    if not result:
        logger.error("costume IDs are not sorted")
    return result
