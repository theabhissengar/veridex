import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from veridex.config import config_dir, get_settings
from veridex.db.models import Investigation, ProcessingJob
from veridex.db.session import make_session_factory
from veridex.domain.taxonomy import default_taxonomy
from veridex.logging import configure_logging
from veridex.pipeline.detector import YoloDetector
from veridex.pipeline.ocr import PaddleOcrEngine, UnavailableOcr
from veridex.pipeline.run import run_investigation
from veridex.storage.local import LocalFilesystemStorage

logger = logging.getLogger(__name__)


def build_detector(settings, models: dict):
    detector_entry = next(item for item in models["models"] if item["role"] == "detector")
    if settings.detector == "stub":
        from veridex.pipeline.detector import StubDetector

        logger.warning("VERIDEX_DETECTOR=stub is a test double and must not be used as product inference")
        return StubDetector(), False
    return (
        YoloDetector(
            settings.weights_path,
            allow_unreviewed=settings.allow_unreviewed_model,
            license_text=detector_entry.get("license") or "",
        ),
        not detector_entry.get("license"),
    )


def build_ocr(settings, models: dict):
    entry = next(item for item in models["models"] if item["role"] == "ocr")
    if settings.ocr == "stub":
        from veridex.pipeline.ocr import StubOcr

        return StubOcr()
    if settings.ocr == "unavailable":
        return UnavailableOcr()
    return PaddleOcrEngine(allow_unreviewed=settings.allow_unreviewed_model, license_text=entry.get("license") or "")


def main() -> None:
    configure_logging()
    settings = get_settings()
    factory = make_session_factory(settings)
    storage = LocalFilesystemStorage(settings.storage_root)
    taxonomy = default_taxonomy()
    acceptance = config_dir() / "acceptance.json"
    import json

    models = json.loads((config_dir() / "models.json").read_text(encoding="utf-8"))
    while True:
        session = factory()
        try:
            job = session.scalar(
                select(ProcessingJob).where(ProcessingJob.status == "queued").order_by(ProcessingJob.created_at).with_for_update(skip_locked=True)
            )
            if job is None or job.investigation_id is None:
                session.commit()
                time.sleep(1)
                continue
            investigation_id = job.investigation_id
            try:
                detector, license_unreviewed = build_detector(settings, models)
            except Exception as exc:
                message = getattr(exc, "message", str(exc))
                job.status = "failed"
                job.error = message
                job.finished_at = datetime.now(timezone.utc)
                investigation = session.get(Investigation, investigation_id)
                if investigation is not None:
                    investigation.status = "failed"
                    investigation.finished_at = job.finished_at
                    investigation.case.status = "failed"
                session.commit()
                continue
            session.commit()
            run_investigation(
                session,
                investigation_id,
                detector=detector,
                ocr=build_ocr(settings, models),
                storage=storage,
                taxonomy=taxonomy,
                acceptance_path=acceptance,
                max_duration_ms=settings.max_duration_ms,
                license_unreviewed=license_unreviewed,
            )
        except Exception:
            logger.exception("worker iteration failed")
            session.rollback()
            time.sleep(1)
        finally:
            session.close()


if __name__ == "__main__":
    main()
