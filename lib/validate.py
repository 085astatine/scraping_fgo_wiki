import logging
import pathlib
import re
from typing import Literal
import jsonschema
from .io import load_json
from .servant import Costume, Servant, Skills
from .schema import servant as servant_schema


_logger = logging.getLogger(__name__)


def validate_servant(
        servant: Servant) -> bool:
    result = True
    prefix = '[{0}: {1}]'.format(
            servant.get('id', 'None'),
            servant.get('name', 'None'))
    # validate with JSONSchema
    try:
        jsonschema.validate(
            instance=servant,
            schema=servant_schema())
    except jsonschema.exceptions.ValidationError as error:
        _logger.error(f'{prefix} JSONSchema validaton error\n{error}')
        return False
    # check skills
    if not _validate_skills(prefix, 'skill', servant['skills']):
        result = False
    if not _validate_skills(prefix, 'append_skill', servant['append_skills']):
        result = False
    # check costumes
    if not _validate_costumes(prefix, servant['costumes']):
        result = False
    return result


def validate_servants(
        directory: pathlib.Path,
        *,
        halt_on_error: bool = False) -> bool:
    result = True
    for file in _servant_files(directory):
        # load
        _logger.info(f'load {file}')
        servant = load_json(file)
        if servant is None:
            _logger.info(f'failed to load {file}')
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


def _validate_skills(
        prefix: str,
        target: Literal['skill', 'append_skill'],
        skills: Skills) -> bool:

    def _to_key(
            slot: Literal[1, 2, 3]
    ) -> Literal['skill_1', 'skill_2', 'skill_3']:
        return (
            'skill_1' if slot == 1
            else 'skill_2' if slot == 2
            else 'skill_3')

    def _validate(slot: Literal[1, 2, 3]) -> bool:
        result = True
        levels = [skill['level'] for skill in skills[_to_key(slot)]]
        if min(levels) != 1:
            result = False
            _logger.error(f'{prefix} minimum level != 1 in {target} {slot}')
        if levels != list(range(min(levels), max(levels) + 1)):
            result = False
            _logger.error(
                    f'{prefix} levels are not consective in {target} {slot}')
        return result

    # validate skill 1, 2, 3
    result = True
    if not _validate(1):
        result = False
    if not _validate(2):
        result = False
    if not _validate(3):
        result = False
    return result


def _validate_costumes(
        prefix: str,
        costumes: list[Costume]) -> bool:
    costume_ids = [costume['id'] for costume in costumes]
    result = costume_ids == sorted(set(costume_ids))
    if not result:
        _logger.error(f'{prefix} costume IDs are not sorted')
    return result


def _servant_files(directory: pathlib.Path) -> list[pathlib.Path]:
    files = [
        file for file in directory.iterdir()
        if re.match(r'[0-9]{3}\.json', file.name)]
    return sorted(files)
