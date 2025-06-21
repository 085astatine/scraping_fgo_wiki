from __future__ import annotations

from typing import Any

from .enum import item, klass


def servant() -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "minimum": 1,
            },
            "name": {"type": "string"},
            "false_name": {
                "type": ["null", "string"],
            },
            "ascension_names": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                ],
            },
            "klass": klass(),
            "rarity": {
                "type": "integer",
                "minimum": 0,
                "maximum": 5,
            },
            "costumes": {
                "type": "array",
                "items": costume(),
            },
            "skills": skills(),
            "append_skills": append_skills(),
            "ascension_resources": {
                "type": "array",
                "items": resource(),
                "minItems": 4,
                "maxItems": 4,
            },
            "skill_resources": {
                "type": "array",
                "items": resource(),
                "minItems": 9,
                "maxItems": 9,
            },
            "append_skill_resources": {
                "type": "array",
                "items": resource(),
                "minItems": 9,
                "maxItems": 9,
            },
        },
        "required": [
            "id",
            "name",
            "false_name",
            "ascension_names",
            "klass",
            "rarity",
            "costumes",
            "skills",
            "append_skills",
            "ascension_resources",
            "skill_resources",
            "append_skill_resources",
        ],
        "additionalProperties": False,
    }
    return schema


def skill() -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "slot": {"type": "integer"},
            "level": {"type": "integer"},
            "name": {"type": "string"},
            "rank": {"type": "string"},
            "icon": {"type": "integer"},
        },
        "required": ["slot", "level", "name", "rank", "icon"],
        "additionalProperties": False,
    }
    return schema


def skills() -> dict[str, Any]:
    schema = {
        "type": "array",
        "items": {
            "type": "array",
            "items": skill(),
            "minItems": 1,
        },
        "minItems": 3,
        "maxItems": 3,
    }
    return schema


def append_skills() -> dict[str, Any]:
    schema = {
        "type": "array",
        "items": {
            "type": "array",
            "items": skill(),
            "minItems": 1,
            "maxItems": 1,
        },
        "minItems": 5,
        "maxItems": 5,
    }
    return schema


def items() -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "name": item(),
            "piece": {
                "type": "integer",
                "minimum": 0,
            },
        },
        "required": ["name", "piece"],
        "additionalProperties": False,
    }
    return schema


def resource() -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "qp": {
                "type": "integer",
                "minimum": 0,
            },
            "items": {
                "type": "array",
                "items": items(),
            },
        },
        "required": ["qp", "items"],
        "additionalProperties": False,
    }
    return schema


def costume() -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "minimum": 1,
            },
            "name": {"type": "string"},
            "resource": resource(),
        },
        "required": ["id", "name", "resource"],
        "additionalProperties": False,
    }
    return schema
