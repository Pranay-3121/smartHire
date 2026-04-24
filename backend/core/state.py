from typing import TypedDict, Optional
from backend.schemas.job import JobProfile
from backend.schemas.candidate import CandidateProfile
from backend.schemas.scoring import ScoredCandidate


class PipelineState(TypedDict, total=False):
    run_id: str
    raw_jd: str
    job_profile: Optional[JobProfile]
    raw_resume_paths: list[str]
    candidate_profiles: list[CandidateProfile]
    scored_candidates: list[ScoredCandidate]
    ranked_candidates: list[ScoredCandidate]
    errors: list[str]
    warnings: list[str]
    status: str
