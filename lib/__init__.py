from __future__ import annotations

import logging

from .io import load_json, save_json
from .item import ItemNameConverter, load_items
from .merge import merge
from .servant import (
    ServantLogger,
    load_costumes,
    load_servant_links,
    load_servant_names,
    load_servants,
    servant_dict,
    skill_dict,
    unplayable_servant_ids,
)
from .sound import Sound, sound_list
from .text import load_item_dictionary
from .types import (
    AppendSkills,
    Costume,
    CostumeData,
    CostumeID,
    Dictionary,
    Item,
    ItemDictionary,
    ItemID,
    ItemsByID,
    Resource,
    ResourceByID,
    ResourceSet,
    Servant,
    ServantDictionary,
    ServantDictionaryValue,
    ServantID,
    ServantLink,
    ServantName,
    Skill,
    Skills,
    Text,
)
from .validate import (
    validate_append_skills,
    validate_servant,
    validate_servants,
    validate_skills,
)

logging.getLogger(__package__).addHandler(logging.NullHandler())
