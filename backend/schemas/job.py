from pydantic import BaseModel, Field
from typing import Optional
from backend.core.constants import RoleType


class JobProfile(BaseModel):
    role_title: str = Field(..., description="Job title extracted from JD")
    role_type: RoleType = Field(default=RoleType.GENERAL)
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float = Field(default=0.0)
    max_experience_years: Optional[float] = Field(default=None)
    required_certifications: list[str] = Field(default_factory=list)
    preferred_certifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    industry_domain: Optional[str] = None
    location: Optional[str] = None
    raw_text: str = Field(default="")
