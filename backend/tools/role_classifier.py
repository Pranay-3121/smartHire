from backend.core.constants import RoleType, ROLE_WEIGHTS, DEFAULT_WEIGHTS
from backend.core.logging import get_logger

logger = get_logger(__name__)


def get_weights_for_role(role_type: RoleType) -> dict[str, int]:
    weights = ROLE_WEIGHTS.get(role_type, DEFAULT_WEIGHTS)
    total = sum(weights.values())
    if total != 100:
        logger.warning(f"Weights for {role_type} sum to {total}, normalizing to 100")
        factor = 100 / total
        weights = {k: round(v * factor) for k, v in weights.items()}
    logger.debug(f"Weights for role_type={role_type}: {weights}")
    return weights


def classify_role_from_title(title: str) -> RoleType:
    from backend.tools.jd_parser import ROLE_TYPE_KEYWORDS
    title_lower = title.lower()
    for role_type, keywords in ROLE_TYPE_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return RoleType(role_type)
    return RoleType.GENERAL
