from pathlib import Path
from typing import Protocol

from veridex.domain.errors import DomainError


class Detector(Protocol):
    name: str
    version: str

    def detect(self, image_path: str) -> list[dict]: ...


class YoloDetector:
    def __init__(self, weights: Path, *, allow_unreviewed: bool, license_text: str) -> None:
        if not weights.is_file():
            raise DomainError(
                "weights_missing",
                "Detector weights were not found. The investigation stopped instead of inventing detections.",
            )
        if not license_text and not allow_unreviewed:
            raise DomainError(
                "license_unreviewed",
                "The detector license has not been reviewed. Set VERIDEX_ALLOW_UNREVIEWED_MODEL only for a local prototype.",
            )
        self.weights = weights
        self.name = "yolov8n"
        self.version = weights.name
        self._model = None

    def detect(self, image_path: str) -> list[dict]:
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(self.weights))
        rows = []
        for result in self._model.predict(image_path, verbose=False):
            names = result.names
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                xyxy = box.xyxyn[0].tolist()
                rows.append(
                    {
                        "raw_label": names.get(cls_id, str(cls_id)),
                        "detector_confidence": float(box.conf[0]),
                        "bbox": {
                            "x": xyxy[0],
                            "y": xyxy[1],
                            "w": xyxy[2] - xyxy[0],
                            "h": xyxy[3] - xyxy[1],
                        },
                    }
                )
        return rows


class StubDetector:
    """Test double. The product worker does not select this unless VERIDEX_DETECTOR=stub."""

    def __init__(self, scripted: dict[int, list[dict]] | None = None) -> None:
        self.scripted = scripted or {}
        self.name = "stub"
        self.version = "test"

    def detect(self, image_path: str) -> list[dict]:
        stem = Path(image_path).stem
        index = int(stem.rsplit("_", 1)[-1])
        return list(self.scripted.get(index, []))
