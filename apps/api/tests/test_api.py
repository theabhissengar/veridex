import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

os.environ["VERIDEX_DATABASE_URL"] = "postgresql+psycopg://veridex:veridex@localhost:5433/veridex_test"
os.environ["VERIDEX_STORAGE_ROOT"] = tempfile.mkdtemp(prefix="veridex-api-")

from veridex.api.app import app  # noqa: E402
from veridex.config import config_dir  # noqa: E402
from veridex.db.base import Base  # noqa: E402
from veridex.db import models  # noqa: E402, F401
from veridex.pipeline.detector import StubDetector  # noqa: E402
from veridex.pipeline.ocr import StubOcr  # noqa: E402
from veridex.pipeline.run import run_investigation  # noqa: E402

BOX = {
    "raw_label": "usb_c_cable",
    "detector_confidence": 0.9,
    "bbox": {"x": 0.2, "y": 0.2, "w": 0.3, "h": 0.3},
}


def _postgres():
    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg is not installed")
    try:
        connection = psycopg.connect("postgresql://veridex:veridex@localhost:5433/veridex", autocommit=True)
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = 'veridex_test'").fetchone()
    if exists is None:
        connection.execute("CREATE DATABASE veridex_test")
    connection.close()


@pytest.fixture(scope="module")
def client():
    _postgres()
    engine = app.state.session_factory.kw["bind"]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def _order(client, case_id: str) -> None:
    response = client.put(
        f"/api/v1/cases/{case_id}/order",
        json={
            "external_order_id": "ORD-1",
            "seller_name": "Seller",
            "buyer_name": "Buyer",
            "ordered_at": "2026-01-01T00:00:00Z",
            "currency": "USD",
            "items": [{"sku": "CABLE", "name": "USB-C cable", "canonical_class": "usb_c_cable", "quantity": 1}],
        },
    )
    assert response.status_code == 200, response.text


def _clip(path: Path, seconds: int) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    completed = subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=64x64:d={seconds}", "-r", "1", str(path)],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.decode()[-300:])


def _run(investigation_id: str, scripted: dict) -> None:
    session = app.state.session_factory()
    try:
        run_investigation(
            session,
            uuid.UUID(investigation_id),
            detector=StubDetector(scripted),
            ocr=StubOcr(),
            storage=app.state.storage,
            taxonomy=app.state.taxonomy,
            acceptance_path=config_dir() / "acceptance.json",
            max_duration_ms=app.state.settings.max_duration_ms,
            license_unreviewed=True,
        )
    finally:
        session.close()


def test_claim_role_and_mime_errors(client):
    created = client.post("/api/v1/cases", json={"title": "Claim errors"})
    assert created.status_code == 201
    case_id = created.json()["id"]
    _order(client, case_id)
    claim = client.post(
        f"/api/v1/cases/{case_id}/claims",
        json={"claim_type": "missing_item", "party": "customer", "canonical_class": "cardboard_box"},
    )
    assert claim.status_code == 422
    assert set(claim.json()["detail"]) == {"code", "message"}
    upload = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        data={"role": "not_a_role", "party": "seller"},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert upload.status_code == 422
    assert upload.json()["detail"]["code"] == "invalid_evidence"
    mime = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        data={"role": "packing_video", "party": "seller"},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert mime.status_code == 422
    assert mime.json()["detail"]["code"] == "invalid_mime"


def test_investigation_snapshot_and_second_run(client, tmp_path: Path):
    created = client.post("/api/v1/cases", json={"title": "Cable dispute", "claimed_dispute_type": "missing_item"})
    case_id = created.json()["id"]
    _order(client, case_id)
    clip = tmp_path / "four.mp4"
    _clip(clip, 4)
    uploaded = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        data={"role": "packing_video", "party": "seller"},
        files={"file": ("four.mp4", clip.read_bytes(), "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    started = client.post(f"/api/v1/cases/{case_id}/investigations")
    assert started.status_code == 202
    first_id = started.json()["id"]
    assert started.json()["questions"] is None
    detail = client.get(f"/api/v1/investigations/{first_id}")
    assert detail.json()["questions"] is None
    _run(first_id, {index: [BOX] for index in range(1, 8)})
    finished = client.get(f"/api/v1/investigations/{first_id}")
    assert finished.json()["status"] == "completed"
    assert isinstance(finished.json()["questions"], list)
    assert finished.json()["questions"]
    coverage = client.get(f"/api/v1/investigations/{first_id}/coverage").json()["items"]
    packing = next(row for row in coverage if row["role"] == "packing_video")
    assert packing["final_coverage"] == "unassessed"
    assert packing["suggested_coverage"] != "complete"
    observations = client.get(f"/api/v1/investigations/{first_id}/observations").json()["items"]
    objects = [row for row in observations if row["observation_type"] == "object"]
    assert len(objects) == 1
    assert objects[0]["canonical_class"] == "usb_c_cable"
    confirmed = client.put(
        f"/api/v1/cases/{case_id}/coverage/packing_video",
        json={"final_coverage": "complete", "final_basis": "Operator watched the clip."},
    )
    assert confirmed.status_code == 200
    second = client.post(f"/api/v1/cases/{case_id}/investigations")
    assert second.status_code == 202
    second_id = second.json()["id"]
    _run(second_id, {index: [BOX] for index in range(1, 8)})
    first_again = client.get(f"/api/v1/investigations/{first_id}")
    assert first_again.json()["questions"]
    assert client.get(f"/api/v1/investigations/{first_id}/coverage").json()["items"][0]["final_coverage"] == "unassessed"
    proven = [
        row
        for row in client.get(f"/api/v1/investigations/{second_id}/findings").json()["items"]
        if row["status"] == "proven"
    ]
    assert proven
    assert proven[0]["observation_strength"]
    assert proven[0]["evidence_references"][0]["detector_confidence"] == 0.9


def test_one_frame_does_not_become_an_observation(client, tmp_path: Path):
    created = client.post("/api/v1/cases", json={"title": "One frame"})
    case_id = created.json()["id"]
    _order(client, case_id)
    clip = tmp_path / "one.mp4"
    _clip(clip, 1)
    uploaded = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        data={"role": "packing_video", "party": "seller"},
        files={"file": ("one.mp4", clip.read_bytes(), "video/mp4")},
    )
    assert uploaded.status_code == 201
    client.put(
        f"/api/v1/cases/{case_id}/coverage/packing_video",
        json={"final_coverage": "complete", "final_basis": "Short clip."},
    )
    started = client.post(f"/api/v1/cases/{case_id}/investigations")
    investigation_id = started.json()["id"]
    _run(investigation_id, {1: [BOX]})
    observations = client.get(f"/api/v1/investigations/{investigation_id}/observations").json()["items"]
    assert [row for row in observations if row["observation_type"] == "object"] == []
    assert client.get(f"/api/v1/investigations/{investigation_id}").json()["questions"] is not None
