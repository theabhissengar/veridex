from veridex.domain.acceptance import AcceptanceConfig, DetectionBox, accept_group


def _box(index: int, confidence: float = 0.9) -> DetectionBox:
    return DetectionBox(index, index * 1000, confidence, {"x": 0.2, "y": 0.2, "w": 0.2, "h": 0.2}, "usb_c_cable")


def test_one_frame_does_not_become_an_observation() -> None:
    assert accept_group("usb_c_cable", [_box(0)], AcceptanceConfig()) is None


def test_repeated_frames_become_one_observation() -> None:
    group = accept_group("usb_c_cable", [_box(0), _box(1), _box(2), _box(3)], AcceptanceConfig())
    assert group is not None
    assert group.observed_quantity_estimate == 1
    assert group.observation_strength.value in {"medium", "high"}
