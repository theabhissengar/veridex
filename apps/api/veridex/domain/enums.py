from enum import StrEnum


class DisputeType(StrEnum):
    MISSING_ITEM = "missing_item"
    WRONG_ITEM = "wrong_item"
    QUANTITY_MISMATCH = "quantity_mismatch"


class Party(StrEnum):
    SELLER = "seller"
    CUSTOMER = "customer"
    CARRIER = "carrier"
    PLATFORM = "platform"


class EvidenceRole(StrEnum):
    PACKING_VIDEO = "packing_video"
    UNBOXING_VIDEO = "unboxing_video"
    PRODUCT_PHOTO = "product_photo"
    INVOICE = "invoice"
    CUSTOMER_STATEMENT = "customer_statement"
    SELLER_STATEMENT = "seller_statement"
    SHIPPING = "shipping"
    ORDER_FILE = "order_file"


class EvidenceKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    STATEMENT = "statement"
    SHIPPING_FILE = "shipping_file"
    ORDER_FILE = "order_file"


class Category(StrEnum):
    PRODUCT = "PRODUCT"
    ACCESSORY = "ACCESSORY"
    PACKAGING = "PACKAGING"
    SHIPPING_MATERIAL = "SHIPPING_MATERIAL"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class CoverageValue(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    LIMITED = "limited"
    UNASSESSED = "unassessed"


class EvidenceState(StrEnum):
    PROVEN = "proven"
    NOT_OBSERVED = "not_observed"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class Applicability(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"


class QuestionAspect(StrEnum):
    PRESENCE = "presence"
    QUANTITY = "quantity"
    IDENTITY = "identity"


class EvaluationStatus(StrEnum):
    PROVEN = "proven"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class CaseAssessment(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNRESOLVED = "unresolved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ObservationType(StrEnum):
    OBJECT = "object"
    DOCUMENT_TEXT = "document_text"
    STATEMENT = "statement"
    SHIPPING_EVENT = "shipping_event"


class Strength(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


MIME_BY_KIND: dict[EvidenceKind, set[str]] = {
    EvidenceKind.VIDEO: {"video/mp4", "video/webm"},
    EvidenceKind.IMAGE: {"image/jpeg", "image/png"},
    EvidenceKind.DOCUMENT: {"application/pdf", "image/jpeg", "image/png"},
    EvidenceKind.STATEMENT: {"text/plain"},
    EvidenceKind.SHIPPING_FILE: {"application/json"},
    EvidenceKind.ORDER_FILE: {"application/json"},
}

ROLE_KINDS: dict[EvidenceRole, list[EvidenceKind]] = {
    EvidenceRole.PACKING_VIDEO: [EvidenceKind.VIDEO],
    EvidenceRole.UNBOXING_VIDEO: [EvidenceKind.VIDEO],
    EvidenceRole.PRODUCT_PHOTO: [EvidenceKind.IMAGE],
    EvidenceRole.INVOICE: [EvidenceKind.DOCUMENT, EvidenceKind.IMAGE],
    EvidenceRole.CUSTOMER_STATEMENT: [EvidenceKind.STATEMENT],
    EvidenceRole.SELLER_STATEMENT: [EvidenceKind.STATEMENT],
    EvidenceRole.SHIPPING: [EvidenceKind.SHIPPING_FILE],
    EvidenceRole.ORDER_FILE: [EvidenceKind.ORDER_FILE],
}

FORBIDDEN_CLAIM_CATEGORIES = {
    Category.PACKAGING,
    Category.SHIPPING_MATERIAL,
    Category.DOCUMENT,
}

STRENGTH_RANK = {Strength.LOW: 0, Strength.MEDIUM: 1, Strength.HIGH: 2}


def infer_kind(role: EvidenceRole, mime_type: str) -> EvidenceKind:
    allowed = ROLE_KINDS[role]
    for kind in allowed:
        if mime_type in MIME_BY_KIND[kind]:
            return kind
    raise ValueError(mime_type)
