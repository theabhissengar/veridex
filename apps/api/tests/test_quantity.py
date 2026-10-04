from veridex.domain.enums import Strength
from veridex.domain.quantity import peak_quantity, quantity_strength


def test_one_frame_peak_is_an_estimate_with_low_strength() -> None:
    counts = [2]
    assert peak_quantity(counts) == 2
    assert quantity_strength(counts) is Strength.LOW


def test_stable_multi_frame_peak_is_high_strength() -> None:
    counts = [2, 2, 2]
    assert peak_quantity(counts) == 2
    assert quantity_strength(counts) is Strength.HIGH


def test_overlap_lowers_strength() -> None:
    assert quantity_strength([2, 2, 2], overlap=True) is Strength.LOW
