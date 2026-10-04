# ADR 0006: Taxonomy semantics and case-level splits

## Status

Accepted

## Decision

Each class has a category and an `order_relevant` flag. Categories are `PRODUCT`, `ACCESSORY`, `PACKAGING`, `SHIPPING_MATERIAL`, `DOCUMENT`, `OTHER`, and `UNKNOWN`.

Packaging, shipping material, and documents do not create wrong-item findings.

Dataset splits are at case level across fixtures, development (`train` or `validation` only), and held-out evaluation. Derivatives of one source video stay in that case's tier and split.
