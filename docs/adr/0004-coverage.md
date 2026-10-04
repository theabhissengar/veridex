# ADR 0004: Suggested coverage and final coverage

## Status

Accepted

## Decision

Coverage values are `complete`, `partial`, `limited`, and `unassessed`. `unassessed` means coverage has not been determined.

The suggester records duration, frames examined, sampling rate, and simple scene signals. V1 suggestions are `limited` or `unassessed` only. The suggester never emits `complete`.

Investigation rules read final coverage. Final coverage stays `unassessed` until an operator confirms or overrides it. A later classifier may improve suggestions without changing the rules.
