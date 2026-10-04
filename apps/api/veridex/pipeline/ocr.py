from typing import Protocol

from veridex.domain.errors import DomainError


class OcrEngine(Protocol):
    name: str
    version: str

    def recognize(self, image_path: str) -> list[dict]: ...


class PaddleOcrEngine:
    def __init__(self, *, allow_unreviewed: bool, license_text: str) -> None:
        if not license_text and not allow_unreviewed:
            raise DomainError(
                "license_unreviewed",
                "The OCR license has not been reviewed. Set VERIDEX_ALLOW_UNREVIEWED_MODEL only for a local prototype.",
            )
        self.name = "paddleocr"
        self.version = "unspecified"
        self._engine = None

    def recognize(self, image_path: str) -> list[dict]:
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise DomainError("ocr_unavailable", "PaddleOCR is not installed. No text was invented.") from exc
            self._engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        result = self._engine.ocr(image_path, cls=True) or []
        rows = []
        for page in result:
            for item in page or []:
                box, (text, score) = item
                rows.append({"text": text, "score": float(score), "region": {"points": box}})
        return rows


class StubOcr:
    def __init__(self, lines: list[dict] | None = None) -> None:
        self.lines = lines or []
        self.name = "stub-ocr"
        self.version = "test"

    def recognize(self, image_path: str) -> list[dict]:
        return list(self.lines)


class UnavailableOcr:
    name = "unavailable"
    version = "none"

    def recognize(self, image_path: str) -> list[dict]:
        raise DomainError("ocr_unavailable", "PaddleOCR is not installed. No text was invented.")
