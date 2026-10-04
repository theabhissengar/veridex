import pytest

from veridex.domain.errors import ContractError
from veridex.domain.splits import validate_case_assignment


def test_frames_from_one_video_cannot_change_split() -> None:
    with pytest.raises(ContractError):
        validate_case_assignment(
            [
                {"case_id": "c1", "tier": "development", "split": "train", "source_video_id": "v1", "derivative_id": "f1"},
                {"case_id": "c1", "tier": "development", "split": "validation", "source_video_id": "v1", "derivative_id": "f2"},
            ]
        )


def test_crop_cannot_move_to_another_tier() -> None:
    with pytest.raises(ContractError):
        validate_case_assignment(
            [
                {"case_id": "c1", "tier": "development", "split": "train", "source_video_id": "v1", "derivative_id": "v1"},
                {"case_id": "c1", "tier": "evaluation", "split": None, "source_video_id": "v1", "derivative_id": "crop"},
            ]
        )
