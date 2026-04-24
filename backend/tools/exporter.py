import json
import csv
from pathlib import Path
from backend.schemas.scoring import ScoredCandidate
from backend.schemas.job import JobProfile
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def _flatten_candidate(sc: ScoredCandidate) -> dict:
    c = sc.candidate
    sb = sc.score_breakdown
    r = sc.reasoning

    return {
        "rank": sc.rank,
        "name": c.name or "Unknown",
        "email": c.email or "",
        "phone": c.phone or "",
        "total_score": sb.total_score,
        "experience_years": c.total_experience_years,
        "skills_count": len(c.skills),
        "top_skills": ", ".join(c.skills[:10]),
        "companies": ", ".join(c.companies[:5]),
        "certifications": ", ".join(c.certifications[:5]),
        "education": "; ".join(f"{e.degree} - {e.institution}" for e in c.education[:2]),
        "role_experience_score": sb.role_experience.weighted_score,
        "projects_score": sb.relevant_projects.weighted_score,
        "certifications_score": sb.certifications.weighted_score,
        "education_score": sb.education.weighted_score,
        "soft_signals_score": sb.soft_signals.weighted_score,
        "semantic_similarity": sb.semantic_similarity,
        "penalty_deductions": sb.penalty_deductions,
        "recommendation": r.recommendation.value if r else "N/A",
        "confidence": r.confidence_level if r else 0.0,
        "strengths": "; ".join(r.strengths[:3]) if r else "",
        "gaps": "; ".join(r.gaps[:3]) if r else "",
        "risks": "; ".join(r.risks[:3]) if r else "",
        "warning_flags": "; ".join(c.warning_flags),
        "parse_status": c.parse_status.value if hasattr(c.parse_status, 'value') else c.parse_status,
        "file_name": c.file_name,
    }


def export_to_csv(run_id: str, candidates: list[ScoredCandidate], shortlist_only: bool = False) -> str:
    export_path = Path(settings.export_dir) / f"{run_id}_results.csv"
    data = candidates if not shortlist_only else [
        c for c in candidates
        if c.reasoning and c.reasoning.recommendation.value == "shortlist"
    ]

    if not data:
        logger.warning(f"No data to export for run {run_id}")
        return str(export_path)

    rows = [_flatten_candidate(sc) for sc in data]
    fieldnames = list(rows[0].keys())

    with open(export_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported {len(rows)} candidates to CSV: {export_path}")
    return str(export_path)


def export_to_json(run_id: str, candidates: list[ScoredCandidate], job: JobProfile | None = None) -> str:
    export_path = Path(settings.export_dir) / f"{run_id}_results.json"

    output = {
        "run_id": run_id,
        "job_title": job.role_title if job else "Unknown",
        "total_candidates": len(candidates),
        "candidates": [sc.model_dump() for sc in candidates],
    }

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"Exported {len(candidates)} candidates to JSON: {export_path}")
    return str(export_path)


def export_shortlist_report(run_id: str, candidates: list[ScoredCandidate], job: JobProfile | None = None) -> str:
    report_path = Path(settings.export_dir) / f"{run_id}_shortlist_report.txt"
    shortlisted = [c for c in candidates if c.reasoning and c.reasoning.recommendation.value == "shortlist"]

    lines = [
        f"SHORTLIST REPORT — Run ID: {run_id}",
        f"Job Title: {job.role_title if job else 'Unknown'}",
        f"Total Candidates Evaluated: {len(candidates)}",
        f"Shortlisted: {len(shortlisted)}",
        "=" * 60,
        "",
    ]

    for sc in shortlisted:
        c = sc.candidate
        r = sc.reasoning
        lines += [
            f"Rank #{sc.rank} — {c.name or 'Unknown'} | Score: {sc.score_breakdown.total_score:.1f}/100",
            f"  Email: {c.email or 'N/A'} | Phone: {c.phone or 'N/A'}",
            f"  Experience: {c.total_experience_years}y | Skills: {', '.join(c.skills[:8])}",
            f"  Recommendation: {r.recommendation.value.upper() if r else 'N/A'}",
            f"  Confidence: {r.confidence_level:.0%}" if r else "",
            f"  Strengths: {'; '.join(r.strengths[:3])}" if r and r.strengths else "",
            f"  Gaps: {'; '.join(r.gaps[:3])}" if r and r.gaps else "",
            f"  Summary: {r.summary}" if r else "",
            "-" * 60,
            "",
        ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Shortlist report written: {report_path}")
    return str(report_path)
