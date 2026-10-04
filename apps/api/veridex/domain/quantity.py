from veridex.domain.enums import STRENGTH_RANK, Strength


def peak_quantity(frame_counts: list[int]) -> int:
    if not frame_counts:
        return 0
    return max(frame_counts)


def quantity_strength(
    frame_counts: list[int],
    *,
    overlap: bool = False,
    partial_visibility: bool = False,
    unstable: bool = False,
    sparse: bool = False,
    brief: bool = False,
    min_stable_frames: int = 3,
    overlap_cap: Strength = Strength.LOW,
) -> Strength:
    """Strength is separate from the peak count. A one-frame peak is low by default."""
    if len(frame_counts) <= 1:
        return Strength.LOW
    stable = len(set(frame_counts)) == 1 and len(frame_counts) >= min_stable_frames and not unstable
    if overlap or partial_visibility:
        return overlap_cap
    if sparse or brief:
        return Strength.LOW
    if stable:
        return Strength.HIGH
    return Strength.MEDIUM


def strength_meets(actual: Strength | str, minimum: Strength | str) -> bool:
    return STRENGTH_RANK[Strength(actual)] >= STRENGTH_RANK[Strength(minimum)]
