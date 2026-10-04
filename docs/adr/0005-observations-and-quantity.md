# ADR 0005: Observations and quantity estimates

## Status

Accepted

## Decision

Raw model rows are an audit log. The investigation engine reads typed evidence observations: `object`, `document_text`, `statement`, and `shipping_event`.

`observed_quantity_estimate` is the peak simultaneous count of a class in one frame of the observation interval, including a one-frame peak. `quantity_strength` says whether that estimate is reliable enough to reason on. A one-frame peak is `low` strength under the default config. Reports say "Estimated observed quantity".

Question generation does not read detector confidence.
