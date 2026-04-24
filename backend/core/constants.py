from enum import Enum


class RoleType(str, Enum):
    ENGINEERING = "engineering"
    COMPLIANCE = "compliance"
    FRESHER = "fresher"
    MANAGEMENT = "management"
    DESIGN = "design"
    DATA_SCIENCE = "data_science"
    SALES = "sales"
    GENERAL = "general"


class Recommendation(str, Enum):
    SHORTLIST = "shortlist"
    HOLD = "hold"
    REJECT = "reject"


class ParseStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    OCR_FALLBACK = "ocr_fallback"


# Default scoring weights (must sum to 100)
DEFAULT_WEIGHTS = {
    "role_experience": 40,
    "relevant_projects": 30,
    "certifications": 15,
    "education": 10,
    "soft_signals": 5,
}

# Role-specific weight overrides
ROLE_WEIGHTS: dict[str, dict[str, int]] = {
    RoleType.ENGINEERING: {
        "role_experience": 35,
        "relevant_projects": 40,
        "certifications": 10,
        "education": 10,
        "soft_signals": 5,
    },
    RoleType.COMPLIANCE: {
        "role_experience": 35,
        "relevant_projects": 15,
        "certifications": 35,
        "education": 10,
        "soft_signals": 5,
    },
    RoleType.FRESHER: {
        "role_experience": 10,
        "relevant_projects": 35,
        "certifications": 15,
        "education": 35,
        "soft_signals": 5,
    },
    RoleType.DATA_SCIENCE: {
        "role_experience": 30,
        "relevant_projects": 40,
        "certifications": 15,
        "education": 10,
        "soft_signals": 5,
    },
    RoleType.MANAGEMENT: {
        "role_experience": 45,
        "relevant_projects": 20,
        "certifications": 10,
        "education": 10,
        "soft_signals": 15,
    },
    RoleType.DESIGN: {
        "role_experience": 30,
        "relevant_projects": 45,
        "certifications": 10,
        "education": 10,
        "soft_signals": 5,
    },
    RoleType.SALES: {
        "role_experience": 40,
        "relevant_projects": 20,
        "certifications": 10,
        "education": 10,
        "soft_signals": 20,
    },
    RoleType.GENERAL: DEFAULT_WEIGHTS,
}

# Penalty thresholds
JOB_HOP_THRESHOLD_MONTHS = 12
CAREER_GAP_THRESHOLD_MONTHS = 12
KEYWORD_STUFFING_THRESHOLD = 60  # max unique skills before flagging

# Scoring thresholds
SHORTLIST_THRESHOLD = 55.0
HOLD_THRESHOLD = 35.0

# Confidence levels
HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.65

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
