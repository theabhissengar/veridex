# ADR 0007: Neutral reports and model licensing

## Status

Accepted

## Decision

The default report is a deterministic twelve-section template. An optional narrator may only rephrase existing structured results and is unwired in V1. Generated conclusions do not state that a party is lying, and do not conclude fraud, theft, guilt, or responsibility. Those words may appear only inside a marked quotation of an uploaded statement.

Ultralytics YOLO and PaddleOCR may be used for local prototyping. This project does not assert that their licenses allow commercial deployment. Every model used for inference is recorded with name, version, license, source, and commercial-use notes. Empty license fields require `VERIDEX_ALLOW_UNREVIEWED_MODEL` for a local prototype, and the report limitations say the license has not been reviewed. The detector and OCR engines stay behind ports.
