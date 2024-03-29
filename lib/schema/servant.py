from typing import Any
from .enum import item, klass


def servant() -> dict[str, Any]:
    schema = {
      'type': 'object',
      'properties': {
        'id': {
          'type': 'integer',
          'minimum': 1,
        },
        'name': {'type': 'string'},
        'alias_name': {
            'type': ['null', 'string'],
        },
        'klass': klass(),
        'rarity': {
          'type': 'integer',
          'minimum': 0,
          'maximum': 5,
        },
        'costumes': {
          'type': 'array',
          'items': costume(),
        },
        'skills': skills(),
        'append_skills': append_skills(),
        'ascension_resources': {
          'type': 'array',
          'items': resource(),
          'minItems': 4,
          'maxItems': 4,
        },
        'skill_resources': {
          'type': 'array',
          'items': resource(),
          'minItems': 9,
          'maxItems': 9,
        },
        'append_skill_resources': {
          'type': 'array',
          'items': resource(),
          'minItems': 9,
          'maxItems': 9,
        },
      },
      'required': [
        'id',
        'name',
        'alias_name',
        'klass',
        'rarity',
        'costumes',
        'skills',
        'append_skills',
        'ascension_resources',
        'skill_resources',
        'append_skill_resources',
      ],
      'additionalProperties': False,
    }
    return schema


def skill(slot: int) -> dict[str, Any]:
    schema = {
      'type': 'object',
      'properties': {
        'slot': {'const': slot},
        'level': {'type': 'integer'},
        'name': {'type': 'string'},
        'rank': {'type': 'string'},
        'icon': {'type': 'integer'},
      },
      'required': ['slot', 'level', 'name', 'rank', 'icon'],
      'additionalProperties': False,
    }
    return schema


def skills() -> dict[str, Any]:
    skill_slots = [1, 2, 3]
    schema = {
      'type': 'object',
      'properties': {
        f'skill_{slot}': {
          'type': 'array',
          'items': skill(slot),
          'minItems': 1,
        } for slot in skill_slots
      },
      'required': [f'skill_{slot}' for slot in skill_slots],
      'additionalProperties': False,
    }
    return schema


def append_skills() -> dict[str, Any]:
    skill_slots = [1, 2, 3]
    schema = {
      'type': 'object',
      'properties': {
        f'skill_{slot}': {
          'type': 'array',
          'items': skill(slot),
          'minItems': 1,
          'maxItems': 1,
        } for slot in skill_slots
      },
      'required': [f'skill_{slot}' for slot in skill_slots],
      'additionalProperties': False,
    }
    return schema


def item_resource() -> dict[str, Any]:
    schema = {
      'type': 'object',
      'properties': {
        'name': item(),
        'piece': {
          'type': 'integer',
          'minimum': 0,
        },
      },
      'required': ['name', 'piece'],
      'additionalProperties': False,
    }
    return schema


def resource() -> dict[str, Any]:
    schema = {
      'type': 'object',
      'properties': {
        'qp': {
          'type': 'integer',
          'minimum': 0,
        },
        'resources': {
          'type': 'array',
          'items': item_resource(),
        },
      },
      'required': ['qp', 'resources'],
      'additionalProperties': False,
    }
    return schema


def costume() -> dict[str, Any]:
    schema = {
      'type': 'object',
      'properties': {
        'id': {
          'type': 'integer',
          'minimum': 1,
        },
        'name': {'type': 'string'},
        'resource': resource(),
      },
      'required': ['id', 'name', 'resource'],
      'additionalProperties': False,
    }
    return schema
