# -*- coding: utf-8 -*-

import json
import pathlib
from typing import Any, Optional


def load_json(
        path: pathlib.Path) -> Optional[Any]:
    if not path.exists():
        return None
    with path.open() as file:
        return json.load(file)


def save_json(
        path: pathlib.Path,
        data: Any) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with path.open(mode='w') as file:
        json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2)
