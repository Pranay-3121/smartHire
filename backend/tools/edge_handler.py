from backend.schemas.candidate import CandidateProfile
from backend.schemas.job import JobProfile
from backend.core.constants import (
    JOB_HOP_THRESHOLD_MONTHS,
    CAREER_GAP_THRESHOLD_MONTHS,
    KEYWORD_STUFFING_THRESHOLD,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


def compute_penalties(candidate: CandidateProfile, job: JobProfile) -> tuple[float, list[str]]:
    penalties = 0.0
    reasons: list[str] = []

    # Job hopping
    short_stints = [
        w for w in candidate.work_experience
        if (w.duration_months or 0) < JOB_HOP_THRESHOLD_MONTHS
    ]
    if len(short_stints) >= 3:
        penalties += 3.0
        reasons.append(f"Job hopping: {len(short_stints)} positions under 12 months")

    # Career gaps
    if _has_significant_gap(candidate):
        penalties += 2.0
        reasons.append("Career gap detected (>6 months)")

    # Keyword stuffing — only apply if parse confidence is decent (avoid false positives from parser noise)
    if len(candidate.skills) > KEYWORD_STUFFING_THRESHOLD and candidate.parse_confidence >= 0.7:
        penalties += 2.0
        reasons.append(f"Keyword stuffing: {len(candidate.skills)} skills listed")

    # Overqualified
    if job.max_experience_years and candidate.total_experience_years > job.max_experience_years * 1.5:
        penalties += 1.5
        reasons.append(f"Potentially overqualified: {candidate.total_experience_years}y vs max {job.max_experience_years}y")

    # Underqualified — SKIP for entry-level / fresher roles
    if job.min_experience_years > 1:
        if candidate.total_experience_years < job.min_experience_years * 0.3 and job.min_experience_years > 0:
            penalties += 2.0
            reasons.append(f"Significantly underqualified: {candidate.total_experience_years}y vs required {job.min_experience_years}y")

    # Low parse confidence
    if candidate.parse_confidence < 0.3:
        penalties += 1.0
        reasons.append(f"Low parse confidence: {candidate.parse_confidence:.0%}")

    total_penalties = min(penalties, 10.0)
    logger.debug(
        f"[PENALTIES] candidate={candidate.candidate_id} "
        f"raw_penalties={penalties:.1f} capped={total_penalties:.1f} reasons={reasons}"
    )
    return total_penalties, reasons


def _has_significant_gap(candidate: CandidateProfile) -> bool:
    import datetime
    experiences = sorted(
        [w for w in candidate.work_experience if w.start_date],
        key=lambda w: w.start_date or "",
    )
    if len(experiences) < 2:
        return False

    for i in range(1, len(experiences)):
        prev = experiences[i - 1]
        curr = experiences[i]
        if prev.end_date and curr.start_date:
            gap = _months_between(prev.end_date, curr.start_date)
            if gap > CAREER_GAP_THRESHOLD_MONTHS:
                return True
    return False


def _months_between(date_str1: str, date_str2: str) -> int:
    import re
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

    def parse(s: str):
        import datetime
        s = s.lower().strip()
        if s in ("present", "current", "now"):
            return datetime.date.today()
        for abbr, num in month_map.items():
            if abbr in s:
                year_match = re.search(r"\d{4}", s)
                year = int(year_match.group()) if year_match else datetime.date.today().year
                return datetime.date(year, num, 1)
        year_match = re.search(r"\d{4}", s)
        if year_match:
            return datetime.date(int(year_match.group()), 1, 1)
        return None

    d1 = parse(date_str1)
    d2 = parse(date_str2)
    if d1 and d2 and d2 > d1:
        return (d2.year - d1.year) * 12 + (d2.month - d1.month)
    return 0


def detect_duplicate(candidate: CandidateProfile, existing_hashes: set[str]) -> bool:
    if candidate.content_hash and candidate.content_hash in existing_hashes:
        logger.warning(f"Duplicate resume detected: {candidate.file_name}")
        return True
    return False


def detect_multilingual(text: str) -> bool:
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return (non_ascii / max(len(text), 1)) > 0.15
