import json
import pathlib
from typing import Any, Optional

import yaml


def load_json(path: pathlib.Path) -> Optional[Any]:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def save_json(path: pathlib.Path, data: Any) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with path.open(mode="w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def load_yaml(path: pathlib.Path) -> Optional[Any]:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_yaml(path: pathlib.Path, data: Any) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with path.open(mode="w", encoding="utf-8") as file:
        yaml.dump(
            data,
            file,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
