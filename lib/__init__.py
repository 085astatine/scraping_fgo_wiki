from __future__ import annotations

import logging

from .io import load_json, save_json
from .merge import merge
from .servant import (
    ServantLogger,
    load_costumes,
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
    ItemID,
    Resource,
    ResourceSet,
    Servant,
    ServantDictionary,
    ServantDictionaryValue,
    ServantID,
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
