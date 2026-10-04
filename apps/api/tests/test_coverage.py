from veridex.domain.coverage import suggest_coverage


def test_suggester_never_emits_complete() -> None:
    for kwargs in (
        {"media_present": False, "duration_ms": None, "frames_examined": None, "sampling_fps": None},
        {"media_present": True, "duration_ms": 5_000, "frames_examined": 5, "sampling_fps": 1},
        {"media_present": True, "duration_ms": 120_000, "frames_examined": 120, "sampling_fps": 1, "scene_notes": ["closed package detected"]},
    ):
        suggested, _basis, _signals = suggest_coverage(**kwargs)
        assert suggested != "complete"


def test_short_media_is_limited_and_long_media_stays_unassessed() -> None:
    limited, _, _ = suggest_coverage(media_present=True, duration_ms=1000, frames_examined=1, sampling_fps=1)
    open_case, basis, signals = suggest_coverage(media_present=True, duration_ms=120_000, frames_examined=120, sampling_fps=1)
    assert limited == "limited"
    assert open_case == "unassessed"
    assert "does not auto-classify" in basis
    assert signals["frames_examined"] == 120
