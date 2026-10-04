# Models

| Name | Role | Version | License | Source | Commercial use |
| --- | --- | --- | --- | --- | --- |
| yolov8n | detector | unspecified until weights are configured | Not reviewed | https://github.com/ultralytics/ultralytics | Prototyping only until a license review. Do not assume commercial use is allowed. |
| paddleocr | ocr | unspecified until the package is installed | Not reviewed | https://github.com/PaddlePaddle/PaddleOCR | Prototyping only until a license review. Do not assume commercial use is allowed. |

The checked-in registry is `apps/api/veridex/pipeline/config/models.json`. An investigation copies the entries it actually used into `model_manifest`.

Weights live outside git in `weights/`. If weights are missing, detection fails the job with an error. The UI does not invent boxes. Tests inject a stub detector and do not use that stub in the production compose file.
