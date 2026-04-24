from pydantic import BaseModel, Field
from typing import Optional
from backend.schemas.scoring import ScoredCandidate
from backend.schemas.job import JobProfile


class AnalyzeJobRequest(BaseModel):
    jd_text: str = Field(..., min_length=50, description="Raw job description text")
    run_id: Optional[str] = None


class AnalyzeJobResponse(BaseModel):
    run_id: str
    job_profile: JobProfile
    message: str = "Job description analyzed successfully"


class UploadResumesResponse(BaseModel):
    run_id: str
    uploaded_count: int
    failed_files: list[str] = Field(default_factory=list)
    message: str


class RankRequest(BaseModel):
    run_id: str


class RankResponse(BaseModel):
    run_id: str
    total_candidates: int
    shortlisted: int
    on_hold: int
    rejected: int
    message: str = "Ranking completed"


class ResultsResponse(BaseModel):
    run_id: str
    job_profile: Optional[JobProfile] = None
    ranked_candidates: list[ScoredCandidate] = Field(default_factory=list)
    total: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: str


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    chroma_connected: bool
    version: str
