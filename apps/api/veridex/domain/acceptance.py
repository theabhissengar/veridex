from dataclasses import dataclass

from veridex.domain.enums import Strength
from veridex.domain.quantity import peak_quantity, quantity_strength


@dataclass(frozen=True)
class DetectionBox:
    frame_index: int
    timestamp_ms: int
    detector_confidence: float
    bbox: dict | None = None
    canonical_class: str = ""
    source_index: int = 0


@dataclass(frozen=True)
class AcceptanceConfig:
    version: str = "1"
    min_detector_confidence: float = 0.5
    min_supporting_frames: int = 3
    min_persistence_ms: int = 200
    max_confidence_spread: float = 0.2
    max_bbox_center_drift: float = 0.25
    min_stable_frames: int = 3
    max_gap_ms: int = 1500


@dataclass(frozen=True)
class AcceptedGroup:
    canonical_class: str
    start_timestamp_ms: int
    end_timestamp_ms: int
    supporting: list[DetectionBox]
    observation_strength: Strength
    observed_quantity_estimate: int
    quantity_strength: Strength


def _center(bbox: dict) -> tuple[float, float]:
    return (float(bbox["x"]) + float(bbox["w"]) / 2, float(bbox["y"]) + float(bbox["h"]) / 2)


def _overlap(boxes: list[DetectionBox]) -> bool:
    by_frame: dict[int, list[DetectionBox]] = {}
    for box in boxes:
        by_frame.setdefault(box.frame_index, []).append(box)
    for group in by_frame.values():
        if len(group) < 2:
            continue
        for index, left in enumerate(group):
            if not left.bbox:
                continue
            for right in group[index + 1 :]:
                if not right.bbox:
                    continue
                ax, ay = _center(left.bbox)
                bx, by = _center(right.bbox)
                if abs(ax - bx) < 0.15 and abs(ay - by) < 0.15:
                    return True
    return False


def _partial(boxes: list[DetectionBox]) -> bool:
    for box in boxes:
        if not box.bbox:
            continue
        x = float(box.bbox["x"])
        y = float(box.bbox["y"])
        w = float(box.bbox["w"])
        h = float(box.bbox["h"])
        if x < 0.02 or y < 0.02 or x + w > 0.98 or y + h > 0.98:
            return True
    return False


def _drift(boxes: list[DetectionBox], limit: float) -> bool:
    centers = [_center(box.bbox) for box in boxes if box.bbox]
    if len(centers) < 2:
        return False
    xs = [item[0] for item in centers]
    ys = [item[1] for item in centers]
    return max(xs) - min(xs) > limit or max(ys) - min(ys) > limit


def group_detections(boxes: list[DetectionBox], config: AcceptanceConfig) -> list[list[DetectionBox]]:
    ordered = sorted(boxes, key=lambda box: (box.timestamp_ms, box.frame_index))
    groups: list[list[DetectionBox]] = []
    current: list[DetectionBox] = []
    for box in ordered:
        if not current or box.timestamp_ms - current[-1].timestamp_ms <= config.max_gap_ms:
            current.append(box)
        else:
            groups.append(current)
            current = [box]
    if current:
        groups.append(current)
    return groups


def accept_group(canonical_class: str, boxes: list[DetectionBox], config: AcceptanceConfig) -> AcceptedGroup | None:
    supporting = [box for box in boxes if box.detector_confidence >= config.min_detector_confidence]
    frames = {box.frame_index for box in supporting}
    if len(frames) < config.min_supporting_frames:
        return None
    start = min(box.timestamp_ms for box in supporting)
    end = max(box.timestamp_ms for box in supporting)
    if end - start < config.min_persistence_ms and len(frames) > 1:
        return None
    scores = [box.detector_confidence for box in supporting]
    if max(scores) - min(scores) > config.max_confidence_spread:
        return None
    if _drift(supporting, config.max_bbox_center_drift):
        return None
    counts: dict[int, int] = {}
    for box in supporting:
        counts[box.frame_index] = counts.get(box.frame_index, 0) + 1
    frame_counts = [counts[index] for index in sorted(counts)]
    observation = Strength.MEDIUM
    if len(frames) >= config.min_supporting_frames * 2 and max(scores) - min(scores) <= config.max_confidence_spread / 2:
        observation = Strength.HIGH
    return AcceptedGroup(
        canonical_class=canonical_class,
        start_timestamp_ms=start,
        end_timestamp_ms=end,
        supporting=supporting,
        observation_strength=observation,
        observed_quantity_estimate=peak_quantity(frame_counts),
        quantity_strength=quantity_strength(
            frame_counts,
            overlap=_overlap(supporting),
            partial_visibility=_partial(supporting),
            min_stable_frames=config.min_stable_frames,
        ),
    )
