import pytest
from backend.tools.role_classifier import get_weights_for_role, classify_role_from_title
from backend.tools.scorer import score_candidate, _skill_overlap, _fuzzy_match
from backend.schemas.candidate import CandidateProfile, WorkExperience, Education, Project
from backend.schemas.job import JobProfile
from backend.core.constants import RoleType


def make_job(role_type=RoleType.ENGINEERING, must_have=None, preferred=None, min_exp=3.0):
    return JobProfile(
        role_title="Test Role",
        role_type=role_type,
        must_have_skills=must_have or ["python", "fastapi", "docker"],
        preferred_skills=preferred or ["kubernetes", "redis"],
        min_experience_years=min_exp,
        raw_text="python fastapi docker kubernetes redis",
    )


def make_candidate(skills=None, exp_years=5.0, certs=None, projects=None, education=None):
    return CandidateProfile(
        candidate_id="test-001",
        file_path="/tmp/test.pdf",
        file_name="test.pdf",
        skills=skills or ["python", "fastapi", "docker", "aws"],
        total_experience_years=exp_years,
        certifications=certs or [],
        projects=projects or [],
        education=education or [],
        raw_text="python fastapi docker aws kubernetes",
        parse_confidence=0.9,
    )


class TestRoleWeights:
    def test_weights_sum_to_100(self):
        for role_type in RoleType:
            weights = get_weights_for_role(role_type)
            assert sum(weights.values()) == 100, f"Weights for {role_type} don't sum to 100"

    def test_engineering_projects_heavier(self):
        eng_weights = get_weights_for_role(RoleType.ENGINEERING)
        gen_weights = get_weights_for_role(RoleType.GENERAL)
        assert eng_weights["relevant_projects"] >= gen_weights["relevant_projects"]

    def test_compliance_certs_heavier(self):
        comp_weights = get_weights_for_role(RoleType.COMPLIANCE)
        gen_weights = get_weights_for_role(RoleType.GENERAL)
        assert comp_weights["certifications"] >= gen_weights["certifications"]

    def test_fresher_education_heavier(self):
        fresh_weights = get_weights_for_role(RoleType.FRESHER)
        gen_weights = get_weights_for_role(RoleType.GENERAL)
        assert fresh_weights["education"] >= gen_weights["education"]

    def test_classify_engineer(self):
        assert classify_role_from_title("Senior Software Engineer") == RoleType.ENGINEERING

    def test_classify_data_scientist(self):
        assert classify_role_from_title("Data Scientist") == RoleType.DATA_SCIENCE

    def test_classify_unknown_returns_general(self):
        assert classify_role_from_title("Wizard of Chaos") == RoleType.GENERAL


class TestScoringMath:
    def test_score_returns_breakdown(self):
        job = make_job()
        candidate = make_candidate()
        breakdown = score_candidate(candidate, job)
        assert breakdown is not None
        assert 0 <= breakdown.total_score <= 100

    def test_perfect_skill_match_scores_high(self):
        job = make_job(must_have=["python", "fastapi", "docker"])
        candidate = make_candidate(skills=["python", "fastapi", "docker"])
        breakdown = score_candidate(candidate, job)
        assert breakdown.role_experience.raw_score > 60

    def test_zero_skill_match_scores_low(self):
        job = make_job(must_have=["cobol", "fortran", "assembly"])
        candidate = make_candidate(skills=["python", "javascript"])
        breakdown = score_candidate(candidate, job)
        assert breakdown.role_experience.raw_score < 40

    def test_skill_overlap_full_match(self):
        score, matched, missing = _skill_overlap(["python", "docker"], ["python", "docker"])
        assert score == 100.0
        assert len(matched) == 2
        assert len(missing) == 0

    def test_skill_overlap_no_match(self):
        score, matched, missing = _skill_overlap(["java"], ["python", "docker"])
        assert score == 0.0
        assert len(missing) == 2

    def test_skill_overlap_partial(self):
        score, matched, missing = _skill_overlap(["python", "java"], ["python", "docker"])
        assert score == 50.0

    def test_fuzzy_match_exact(self):
        assert _fuzzy_match("python", "python") == 1.0

    def test_fuzzy_match_similar(self):
        assert _fuzzy_match("javascript", "javascript") == 1.0

    def test_fuzzy_match_different(self):
        assert _fuzzy_match("python", "cobol") < 0.5

    def test_penalty_reduces_score(self):
        job = make_job(min_exp=5.0)
        # Underqualified candidate
        candidate = make_candidate(exp_years=0.5)
        breakdown = score_candidate(candidate, job)
        assert breakdown.penalty_deductions > 0

    def test_total_score_bounded(self):
        job = make_job()
        candidate = make_candidate()
        breakdown = score_candidate(candidate, job)
        assert 0.0 <= breakdown.total_score <= 100.0

    def test_ranking_order(self):
        job = make_job(must_have=["python", "fastapi", "docker"])
        strong = make_candidate(skills=["python", "fastapi", "docker", "kubernetes"], exp_years=6.0)
        strong.candidate_id = "strong"
        weak = make_candidate(skills=["java", "spring"], exp_years=1.0)
        weak.candidate_id = "weak"

        strong_score = score_candidate(strong, job)
        weak_score = score_candidate(weak, job)
        assert strong_score.total_score > weak_score.total_score
