from veridex.domain.enums import CoverageValue


def suggest_coverage(
    *,
    media_present: bool,
    duration_ms: int | None,
    frames_examined: int | None,
    sampling_fps: float | None,
    scene_notes: list[str] | None = None,
    short_duration_ms: int = 15_000,
    min_sampling_fps: float = 0.5,
) -> tuple[str, str, dict]:
    """V1 never suggests COMPLETE. Signals are recorded either way."""
    signals = {
        "media_present": media_present,
        "duration_ms": duration_ms,
        "frames_examined": frames_examined,
        "sampling_fps": sampling_fps,
        "scene_notes": list(scene_notes or []),
    }
    if not media_present:
        return CoverageValue.UNASSESSED.value, "No media for this role.", signals
    if duration_ms is not None and duration_ms < short_duration_ms:
        return (
            CoverageValue.LIMITED.value,
            f"Duration {duration_ms} ms is below the configured floor of {short_duration_ms} ms.",
            signals,
        )
    if sampling_fps is not None and sampling_fps < min_sampling_fps:
        return (
            CoverageValue.LIMITED.value,
            f"Sampling rate {sampling_fps} fps is below the configured floor of {min_sampling_fps} fps.",
            signals,
        )
    return (
        CoverageValue.UNASSESSED.value,
        "V1 does not auto-classify whether this media covers the real-world event. Signals are recorded for the operator.",
        signals,
    )
