import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages" / "contracts"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_taxonomy_and_example_ground_truth_match_contracts() -> None:
    jsonschema.validate(json.loads((ROOT / "dataset" / "taxonomy.json").read_text(encoding="utf-8")), _schema("taxonomy.schema.json"))
    jsonschema.validate(json.loads((CONTRACTS / "examples" / "ground_truth.complete.json").read_text(encoding="utf-8")), _schema("ground_truth.schema.json"))


def test_unknown_coverage_value_is_rejected() -> None:
    schema = {
        "type": "string",
        "enum": ["complete", "partial", "limited", "unassessed"],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate("unknown", schema)


def test_unknown_role_is_rejected() -> None:
    schema = _schema("investigation_question.schema.json")
    payload = {
        "question_key": "item:usb_c_cable:presence",
        "subject": "usb_c_cable",
        "aspect": "presence",
        "required_roles": ["not_a_role"],
        "canonical_class": "usb_c_cable",
        "primary": False,
        "applicability": "applicable",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
