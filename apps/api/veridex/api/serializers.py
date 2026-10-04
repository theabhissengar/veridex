from datetime import datetime, timezone


def _started(row) -> datetime:
    stamp = row.started_at or getattr(row, "finished_at", None)
    if isinstance(stamp, datetime):
        return stamp
    return datetime.min.replace(tzinfo=timezone.utc)


def case_dict(case, investigations=None) -> dict:
    latest = None
    items = investigations if investigations is not None else list(case.investigations)
    if items:
        latest = sorted(items, key=_started, reverse=True)[0]
    return {
        "id": str(case.id),
        "title": case.title,
        "status": case.status,
        "claimed_dispute_type": case.claimed_dispute_type,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
        "latest_investigation_id": None if latest is None else str(latest.id),
        "latest_assessment": None if latest is None else latest.assessment,
    }


def evidence_dict(row) -> dict:
    return {
        "id": str(row.id),
        "case_id": str(row.case_id),
        "kind": row.kind,
        "role": row.role,
        "party": row.party,
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "byte_size": row.byte_size,
        "checksum_sha256": row.checksum_sha256,
        "status": row.status,
        "text_body": row.text_body,
        "media_metadata": row.media_metadata,
    }
