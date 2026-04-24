import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from backend.schemas.job import JobProfile
from backend.schemas.candidate import CandidateProfile
from backend.schemas.scoring import ScoredCandidate, ScoreBreakdown, ScoreDimension
from backend.core.constants import RoleType, Recommendation
from backend.agents.ranking_agent import run_ranking_agent
from backend.agents.reasoning_agent import run_reasoning_agent, _determine_recommendation, _build_rule_based_reasoning


SAMPLE_JD_TEXT = """
Senior Python Developer

We are looking for a Senior Python Developer with 4+ years of experience.

Required:
- Python
- FastAPI
- PostgreSQL
- Docker

Preferred:
- Kubernetes
- AWS

Bachelor's degree in Computer Science required.
"""

SAMPLE_RESUME_TEXT = """
Jane Smith
jane.smith@example.com
+1-555-987-6543

Skills: Python, FastAPI, PostgreSQL, Docker, AWS, Git

Experience:
Senior Developer
TechCorp
Jan 2019 - Present
Built APIs with FastAPI and Python.

Education:
Bachelor of Science in Computer Science
MIT
2019

Certifications:
AWS Certified Developer
"""


def make_job():
    return JobProfile(
        role_title="Senior Python Developer",
        role_type=RoleType.ENGINEERING,
        must_have_skills=["python", "fastapi", "postgresql", "docker"],
        preferred_skills=["kubernetes", "aws"],
        min_experience_years=4.0,
        education_requirements=["Bachelor's in Computer Science"],
        raw_text=SAMPLE_JD_TEXT,
    )


def make_candidate(candidate_id="c001", skills=None, exp=5.0):
    return CandidateProfile(
        candidate_id=candidate_id,
        file_path=f"/tmp/{candidate_id}.pdf",
        file_name=f"{candidate_id}.pdf",
        name="Jane Smith",
        email="jane@example.com",
        skills=skills or ["python", "fastapi", "postgresql", "docker", "aws"],
        total_experience_years=exp,
        certifications=["AWS Certified Developer"],
        raw_text=SAMPLE_RESUME_TEXT,
        parse_confidence=0.9,
    )


class TestRankingAgent:
    def test_ranking_returns_scored_candidates(self):
        job = make_job()
        candidates = [make_candidate("c001"), make_candidate("c002", skills=["java"], exp=1.0)]
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
                scored = run_ranking_agent(candidates, job, "test-run-001")
        assert len(scored) == 2

    def test_ranking_order_correct(self):
        job = make_job()
        strong = make_candidate("strong", skills=["python", "fastapi", "postgresql", "docker"], exp=6.0)
        weak = make_candidate("weak", skills=["cobol", "fortran"], exp=0.5)
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.3):
                scored = run_ranking_agent([strong, weak], job, "test-run-002")
        assert scored[0].candidate.candidate_id == "strong"
        assert scored[1].candidate.candidate_id == "weak"

    def test_ranks_assigned_sequentially(self):
        job = make_job()
        candidates = [make_candidate(f"c{i}") for i in range(5)]
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
                scored = run_ranking_agent(candidates, job, "test-run-003")
        ranks = [sc.rank for sc in scored]
        assert ranks == list(range(1, len(scored) + 1))

    def test_duplicate_skipped(self):
        job = make_job()
        c1 = make_candidate("c001")
        c2 = make_candidate("c002")
        c2.is_duplicate = True
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
                scored = run_ranking_agent([c1, c2], job, "test-run-004")
        assert len(scored) == 1
        assert scored[0].candidate.candidate_id == "c001"

    def test_fresher_not_zeroed_for_missing_experience(self):
        """Fresher with no experience but skills should not score 0 on experience."""
        job = JobProfile(
            role_title="Junior Developer",
            role_type=RoleType.FRESHER,
            must_have_skills=["python", "html", "css"],
            preferred_skills=[],
            min_experience_years=0.0,
            raw_text="entry level",
        )
        fresher = CandidateProfile(
            candidate_id="f001",
            file_path="/tmp/f001.pdf",
            file_name="f001.pdf",
            name="Fresh Grad",
            skills=["python", "html", "css", "javascript"],
            total_experience_years=0.0,
            projects=[{"name": "Portfolio", "description": "Personal site", "technologies": ["html", "css", "javascript"]}],
            education=[{"institution": "State Univ", "degree": "B.Sc CS"}],
            parse_confidence=0.9,
        )
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.3):
                scored = run_ranking_agent([fresher], job, "test-run-fresher")
        # Should be a moderate score, not near-zero
        assert scored[0].score_breakdown.total_score >= 35.0

    def test_transferable_skills_give_partial_credit(self):
        """Flask should give partial credit when FastAPI is required."""
        job = JobProfile(
            role_title="Python Dev",
            role_type=RoleType.ENGINEERING,
            must_have_skills=["fastapi"],
            preferred_skills=[],
            min_experience_years=1.0,
            raw_text="need fastapi",
        )
        candidate = CandidateProfile(
            candidate_id="t001",
            file_path="/tmp/t001.pdf",
            file_name="t001.pdf",
            name="Transferable",
            skills=["flask", "python", "postgresql"],
            total_experience_years=2.0,
            parse_confidence=0.9,
        )
        with patch("backend.agents.ranking_agent._index_candidates_in_chroma"):
            with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.3):
                scored = run_ranking_agent([candidate], job, "test-run-transfer")
        # Flask → FastAPI alias should give partial credit, so score > 0
        assert scored[0].score_breakdown.total_score > 15.0


class TestReasoningAgent:
    def test_recommendation_shortlist(self):
        assert _determine_recommendation(75.0) == Recommendation.SHORTLIST

    def test_recommendation_hold(self):
        assert _determine_recommendation(55.0) == Recommendation.HOLD

    def test_recommendation_reject(self):
        assert _determine_recommendation(30.0) == Recommendation.REJECT

    def test_recommendation_boundary_shortlist(self):
        assert _determine_recommendation(70.0) == Recommendation.SHORTLIST

    def test_recommendation_boundary_hold(self):
        assert _determine_recommendation(50.0) == Recommendation.HOLD

    def test_rule_based_reasoning_has_summary(self):
        job = make_job()
        candidate = make_candidate()
        from backend.tools.scorer import score_candidate
        with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
            breakdown = score_candidate(candidate, job)
        sc = ScoredCandidate(candidate=candidate, score_breakdown=breakdown)
        reasoning = _build_rule_based_reasoning(sc, job)
        assert reasoning.summary != ""
        assert reasoning.recommendation in list(Recommendation)

    def test_reasoning_filters_garbage_matched_items(self):
        """Reasoning should not include markdown headers or long sentences as matched skills."""
        job = make_job()
        candidate = make_candidate()
        from backend.tools.scorer import score_candidate
        with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
            breakdown = score_candidate(candidate, job)
        # Inject garbage matched item
        breakdown.role_experience.matched_items.append("# Key Responsibilities")
        sc = ScoredCandidate(candidate=candidate, score_breakdown=breakdown)
        reasoning = _build_rule_based_reasoning(sc, job)
        assert "# Key Responsibilities" not in reasoning.summary
        for s in reasoning.strengths:
            assert "# Key Responsibilities" not in s

    def test_reasoning_agent_populates_all(self):
        job = make_job()
        candidate = make_candidate()
        from backend.tools.scorer import score_candidate
        with patch("backend.tools.scorer._compute_semantic_similarity", return_value=0.5):
            breakdown = score_candidate(candidate, job)
        sc = ScoredCandidate(candidate=candidate, score_breakdown=breakdown, rank=1)

        with patch("backend.agents.reasoning_agent._build_llm_reasoning", return_value=None):
            result = run_reasoning_agent([sc], job)

        assert result[0].reasoning is not None
        assert result[0].reasoning.recommendation in list(Recommendation)


class TestAPIEndpoints:
    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from backend.api.main import app
        client = TestClient(app)
        with patch("backend.api.main.ollama_client.is_available", return_value=True):
            with patch("backend.api.main.embedding_service.is_available", return_value=True):
                response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_analyze_job_endpoint(self):
        from fastapi.testclient import TestClient
        from backend.api.main import app
        client = TestClient(app)
        with patch("backend.api.main.run_jd_reader_agent") as mock_agent:
            mock_agent.return_value = make_job()
            response = client.post("/analyze-job", json={"jd_text": SAMPLE_JD_TEXT})
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "job_profile" in data

    def test_analyze_job_short_text_rejected(self):
        from fastapi.testclient import TestClient
        from backend.api.main import app
        client = TestClient(app)
        response = client.post("/analyze-job", json={"jd_text": "too short"})
        assert response.status_code == 422

    def test_results_not_found(self):
        from fastapi.testclient import TestClient
        from backend.api.main import app
        client = TestClient(app)
        response = client.get("/results/nonexistent-run-id-xyz")
        assert response.status_code == 404
