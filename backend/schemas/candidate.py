from pydantic import BaseModel, Field
from typing import Optional
from backend.core.constants import ParseStatus


class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None
    description: str = ""
    is_current: bool = False


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class CandidateProfile(BaseModel):
    candidate_id: str
    file_path: str
    file_name: str

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    skills: list[str] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    total_experience_years: float = 0.0
    companies: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    summary: Optional[str] = None

    parse_status: ParseStatus = ParseStatus.SUCCESS
    parse_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warning_flags: list[str] = Field(default_factory=list)
    raw_text: str = ""
    is_duplicate: bool = False
    content_hash: Optional[str] = None
