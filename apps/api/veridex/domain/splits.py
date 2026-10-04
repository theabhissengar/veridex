from veridex.domain.errors import ContractError


def validate_case_assignment(records: list[dict]) -> None:
    """Reject a source video whose derivatives land in different tiers or splits.

    Each record has case_id, tier, split (or None), source_video_id, and derivative_id.
    """
    by_video: dict[str, set[tuple[str, str | None]]] = {}
    case_tier: dict[str, str] = {}
    for record in records:
        tier = record["tier"]
        split = record.get("split")
        case_id = record["case_id"]
        if tier == "development" and split not in {"train", "validation"}:
            raise ContractError("invalid_split", "Development cases use train or validation only")
        if tier in {"fixture", "evaluation"} and split not in {None, ""}:
            raise ContractError("invalid_split", "Fixture and evaluation cases are not train or validation splits")
        previous = case_tier.get(case_id)
        if previous is not None and previous != tier:
            raise ContractError("tier_leak", f"{case_id} appears in more than one tier")
        case_tier[case_id] = tier
        key = (tier, split)
        video = record["source_video_id"]
        by_video.setdefault(video, set()).add(key)
        if len(by_video[video]) > 1:
            raise ContractError("frame_leak", f"Derivatives of {video} are in different splits or tiers")
