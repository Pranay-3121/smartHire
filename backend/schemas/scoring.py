from pydantic import BaseModel, Field
from typing import Optional
from backend.schemas.candidate import CandidateProfile
from backend.core.constants import Recommendation


class ScoreDimension(BaseModel):
    raw_score: float = Field(ge=0.0, le=100.0)
    weighted_score: float = Field(ge=0.0, le=100.0)
    weight: float
    matched_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    notes: str = ""


class ScoreBreakdown(BaseModel):
    role_experience: ScoreDimension
    relevant_projects: ScoreDimension
    certifications: ScoreDimension
    education: ScoreDimension
    soft_signals: ScoreDimension
    semantic_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    penalty_deductions: float = Field(default=0.0, ge=0.0)
    total_score: float = Field(ge=0.0, le=100.0)


class ReasoningOutput(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0)
    recommendation: Recommendation
    recommendation_reason: str = ""


class ScoredCandidate(BaseModel):
    candidate: CandidateProfile
    score_breakdown: ScoreBreakdown
    reasoning: Optional[ReasoningOutput] = None
    rank: Optional[int] = None
    tiebreak_score: float = 0.0
