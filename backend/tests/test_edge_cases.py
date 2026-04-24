import pytest
from backend.tools.edge_handler import compute_penalties, detect_duplicate, detect_multilingual, _has_significant_gap
from backend.schemas.candidate import CandidateProfile, WorkExperience
from backend.schemas.job import JobProfile
from backend.core.constants import RoleType


def make_job(min_exp=3.0, max_exp=None):
    return JobProfile(
        role_title="Test Role",
        role_type=RoleType.GENERAL,
        must_have_skills=["python"],
        min_experience_years=min_exp,
        max_experience_years=max_exp,
        raw_text="python developer",
    )


def make_candidate(skills=None, exp_years=3.0, work_exp=None, confidence=0.9, content_hash=None):
    return CandidateProfile(
        candidate_id="test-001",
        file_path="/tmp/test.pdf",
        file_name="test.pdf",
        skills=skills or ["python"],
        total_experience_years=exp_years,
        work_experience=work_exp or [],
        parse_confidence=confidence,
        content_hash=content_hash,
    )


class TestEdgeCases:
    def test_no_penalties_for_clean_candidate(self):
        job = make_job()
        candidate = make_candidate()
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties == 0.0
        assert reasons == []

    def test_keyword_stuffing_penalty(self):
        skills = [f"skill_{i}" for i in range(30)]
        candidate = make_candidate(skills=skills)
        job = make_job()
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties > 0
        assert any("stuffing" in r.lower() for r in reasons)

    def test_keyword_stuffing_no_penalty_low_confidence(self):
        """Parser noise shouldn't trigger stuffing penalty when confidence is low."""
        skills = [f"skill_{i}" for i in range(30)]
        candidate = make_candidate(skills=skills, confidence=0.3)
        job = make_job()
        penalties, reasons = compute_penalties(candidate, job)
        # Should not get stuffing penalty due to low confidence
        assert not any("stuffing" in r.lower() for r in reasons)

    def test_job_hopping_penalty(self):
        short_jobs = [
            WorkExperience(company=f"Co{i}", title="Dev", duration_months=6)
            for i in range(4)
        ]
        candidate = make_candidate(work_exp=short_jobs)
        job = make_job()
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties > 0
        assert any("hopping" in r.lower() for r in reasons)

    def test_overqualified_penalty(self):
        job = make_job(min_exp=2.0, max_exp=4.0)
        candidate = make_candidate(exp_years=10.0)
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties > 0
        assert any("overqualified" in r.lower() for r in reasons)

    def test_underqualified_penalty(self):
        job = make_job(min_exp=5.0)
        candidate = make_candidate(exp_years=1.0)
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties > 0
        assert any("underqualified" in r.lower() for r in reasons)

    def test_no_underqualified_penalty_for_fresher_role(self):
        """Entry-level roles should not penalize lack of experience."""
        job = make_job(min_exp=0.0)
        candidate = make_candidate(exp_years=0.0)
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties == 0.0
        assert not any("underqualified" in r.lower() for r in reasons)

    def test_low_confidence_penalty(self):
        candidate = make_candidate(confidence=0.3)
        job = make_job()
        penalties, reasons = compute_penalties(candidate, job)
        assert penalties > 0
        assert any("confidence" in r.lower() for r in reasons)

    def test_penalties_capped_at_10(self):
        skills = [f"skill_{i}" for i in range(50)]
        short_jobs = [WorkExperience(company=f"Co{i}", title="Dev", duration_months=3) for i in range(6)]
        candidate = make_candidate(skills=skills, exp_years=0.5, work_exp=short_jobs, confidence=0.2)
        job = make_job(min_exp=10.0, max_exp=12.0)
        penalties, _ = compute_penalties(candidate, job)
        assert penalties <= 10.0

    def test_duplicate_detection_true(self):
        candidate = make_candidate(content_hash="abc123")
        assert detect_duplicate(candidate, {"abc123", "def456"}) is True

    def test_duplicate_detection_false(self):
        candidate = make_candidate(content_hash="xyz789")
        assert detect_duplicate(candidate, {"abc123", "def456"}) is False

    def test_duplicate_detection_no_hash(self):
        candidate = make_candidate(content_hash=None)
        assert detect_duplicate(candidate, {"abc123"}) is False

    def test_multilingual_detection_true(self):
        text = "Hello " + "こんにちは世界" * 20
        assert detect_multilingual(text) is True

    def test_multilingual_detection_false(self):
        text = "This is a completely English resume with no foreign characters at all."
        assert detect_multilingual(text) is False

    def test_career_gap_detection(self):
        work_exp = [
            WorkExperience(company="Co1", title="Dev", start_date="Jan 2018", end_date="Dec 2018"),
            WorkExperience(company="Co2", title="Dev", start_date="Sep 2019", end_date="Present"),
        ]
        candidate = make_candidate(work_exp=work_exp)
        assert _has_significant_gap(candidate) is True

    def test_no_career_gap(self):
        work_exp = [
            WorkExperience(company="Co1", title="Dev", start_date="Jan 2018", end_date="Dec 2018"),
            WorkExperience(company="Co2", title="Dev", start_date="Jan 2019", end_date="Present"),
        ]
        candidate = make_candidate(work_exp=work_exp)
        assert _has_significant_gap(candidate) is False
