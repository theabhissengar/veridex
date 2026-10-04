# Veridex dataset

Three tiers. A case, and every frame, clip, crop, or other derivative of its videos, belongs to exactly one tier.

- `fixtures/` — about 5 to 10 golden cases for deterministic tests. Not a training set.
- `development/` — the future 50–100+ case set. `splits.json` maps a case id to `train` or `validation` only.
- `evaluation/` — held-out cases. Never used to train, tune thresholds, or edit rules.
- `annotations/` — boxes keyed by case id and video, for development cases only.

Splits are at case level. Do not shuffle frames from one video into another split or tier.

Phase 0 provides the schema and taxonomy. Media is added as it is filmed. The suggester is not expected to mark a video `COMPLETE`.
