import pytest
from backend.tools.jd_parser import parse_jd_rules, _detect_role_type, _extract_experience_range
from backend.tools.resume_parser import (
    _extract_email, _extract_phone, _extract_name, _extract_skills,
    _extract_certifications, compute_content_hash, _clean_skill, _is_noise_token,
)
from backend.core.constants import RoleType


SAMPLE_JD = """
Senior Python Engineer

We are looking for a Senior Python Engineer with 5+ years of experience.

Required Skills:
- Python
- FastAPI
- PostgreSQL
- Docker
- AWS

Preferred Skills:
- Kubernetes
- Redis
- Machine Learning

Requirements:
- Bachelor's degree in Computer Science or related field
- AWS Certified Solutions Architect preferred
- Strong communication and teamwork skills
"""

SAMPLE_RESUME_TEXT = """
John Doe
john.doe@example.com
+1-555-123-4567

Summary:
Senior software engineer with 6 years of experience in Python and cloud technologies.

Skills:
Python, FastAPI, Django, PostgreSQL, Docker, AWS, Kubernetes, Redis, Git

Experience:
Senior Engineer
TechCorp Inc
Jan 2020 - Present
Built microservices using FastAPI and deployed on AWS EKS.

Software Engineer
StartupXYZ
Mar 2018 - Dec 2019
Developed REST APIs using Django and PostgreSQL.

Education:
Bachelor of Technology in Computer Science
State University
2018

Certifications:
AWS Certified Solutions Architect - Associate
"""


class TestJDParser:
    def test_parse_jd_returns_dict(self):
        result = parse_jd_rules(SAMPLE_JD)
        assert isinstance(result, dict)

    def test_role_title_extracted(self):
        result = parse_jd_rules(SAMPLE_JD)
        assert result["role_title"] != ""

    def test_role_type_engineering(self):
        role_type = _detect_role_type(SAMPLE_JD)
        assert role_type == RoleType.ENGINEERING

    def test_role_type_compliance(self):
        jd = "We need a Compliance Officer with audit and regulatory experience."
        assert _detect_role_type(jd) == RoleType.COMPLIANCE

    def test_role_type_fresher(self):
        jd = "Looking for a fresher or entry level developer to join our team."
        assert _detect_role_type(jd) == RoleType.FRESHER

    def test_experience_range_extracted(self):
        min_exp, max_exp = _extract_experience_range(SAMPLE_JD)
        assert min_exp == 5.0

    def test_experience_range_no_match(self):
        min_exp, max_exp = _extract_experience_range("No experience mentioned here.")
        assert min_exp == 0.0
        assert max_exp is None

    def test_must_have_skills_not_empty(self):
        result = parse_jd_rules(SAMPLE_JD)
        assert isinstance(result["must_have_skills"], list)
        # Should not contain markdown headers or locations
        for skill in result["must_have_skills"]:
            assert not skill.startswith("#")
            assert "location" not in skill.lower()

    def test_education_requirements_extracted(self):
        result = parse_jd_rules(SAMPLE_JD)
        assert isinstance(result["education_requirements"], list)

    def test_soft_skills_extracted(self):
        result = parse_jd_rules(SAMPLE_JD)
        assert "communication" in result["soft_skills"] or "teamwork" in result["soft_skills"]

    def test_no_location_in_skills(self):
        """Ensure section bleed doesn't put locations into skills."""
        jd_with_location = """
        # Location
        Mumbai, Pune

        Required Skills:
        - Python
        - Flask
        """
        result = parse_jd_rules(jd_with_location)
        for skill in result["must_have_skills"]:
            assert "mumbai" not in skill.lower()
            assert "pune" not in skill.lower()


class TestResumeParser:
    def test_extract_email(self):
        assert _extract_email(SAMPLE_RESUME_TEXT) == "john.doe@example.com"

    def test_extract_email_none(self):
        assert _extract_email("No email here just text") is None

    def test_extract_phone(self):
        phone = _extract_phone(SAMPLE_RESUME_TEXT)
        assert phone is not None
        assert "555" in phone

    def test_extract_name(self):
        lines = SAMPLE_RESUME_TEXT.strip().split("\n")
        name = _extract_name(lines)
        assert name == "John Doe"

    def test_extract_skills(self):
        skills = _extract_skills(SAMPLE_RESUME_TEXT)
        assert "python" in skills
        assert "docker" in skills

    def test_extract_certifications(self):
        certs = _extract_certifications(SAMPLE_RESUME_TEXT)
        assert len(certs) > 0
        assert any("aws" in c.lower() for c in certs)

    def test_content_hash_deterministic(self):
        h1 = compute_content_hash("same text")
        h2 = compute_content_hash("same text")
        assert h1 == h2

    def test_content_hash_different(self):
        h1 = compute_content_hash("text one")
        h2 = compute_content_hash("text two")
        assert h1 != h2

    def test_noise_token_rejected(self):
        assert _is_noise_token("proficient") is True
        assert _is_noise_token("and") is True
        assert _is_noise_token("strong grasp of python") is True

    def test_clean_skill_filters_noise(self):
        assert _clean_skill("proficient") is None
        assert _clean_skill("Python") == "Python"
        assert _clean_skill("and mysql. strong grasp of") is None
