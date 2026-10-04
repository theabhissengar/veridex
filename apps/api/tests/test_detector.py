from pathlib import Path

import pytest

from veridex.domain.errors import DomainError
from veridex.pipeline.detector import YoloDetector
from veridex.pipeline.ocr import PaddleOcrEngine


def test_missing_weights_fail_closed(tmp_path: Path):
    with pytest.raises(DomainError) as caught:
        YoloDetector(tmp_path / "missing.pt", allow_unreviewed=True, license_text="reviewed")
    assert caught.value.code == "weights_missing"


def test_unreviewed_detector_license_is_refused(tmp_path: Path):
    weights = tmp_path / "yolo.pt"
    weights.write_bytes(b"not a model")
    with pytest.raises(DomainError) as caught:
        YoloDetector(weights, allow_unreviewed=False, license_text="")
    assert caught.value.code == "license_unreviewed"


def test_missing_paddleocr_fails_without_inventing_text(tmp_path: Path):
    engine = PaddleOcrEngine(allow_unreviewed=True, license_text="")
    with pytest.raises(DomainError) as caught:
        engine.recognize(str(tmp_path / "page.png"))
    assert caught.value.code == "ocr_unavailable"
