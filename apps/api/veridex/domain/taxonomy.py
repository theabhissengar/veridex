import json
import os
from dataclasses import dataclass
from pathlib import Path

from veridex.domain.enums import Category
from veridex.domain.errors import ContractError


@dataclass(frozen=True)
class ClassSpec:
    canonical_class: str
    display_name: str
    category: Category
    order_relevant: bool


@dataclass(frozen=True)
class Taxonomy:
    version: str
    classes: dict[str, ClassSpec]

    def get(self, canonical_class: str) -> ClassSpec | None:
        return self.classes.get(canonical_class)


def load_taxonomy(path: Path) -> Taxonomy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    classes: dict[str, ClassSpec] = {}
    for raw in payload["classes"]:
        try:
            category = Category(raw["category"])
        except ValueError as exc:
            raise ContractError("invalid_category", f"Unknown category {raw['category']}") from exc
        spec = ClassSpec(
            canonical_class=raw["canonical_class"],
            display_name=raw["display_name"],
            category=category,
            order_relevant=bool(raw["order_relevant"]),
        )
        classes[spec.canonical_class] = spec
    return Taxonomy(version=str(payload["version"]), classes=classes)


def repo_root() -> Path:
    env = os.environ.get("VERIDEX_REPO_ROOT")
    if env and (Path(env) / "dataset" / "taxonomy.json").is_file():
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dataset" / "taxonomy.json").is_file():
            return parent
    raise FileNotFoundError("dataset/taxonomy.json")


def default_taxonomy() -> Taxonomy:
    return load_taxonomy(repo_root() / "dataset" / "taxonomy.json")
