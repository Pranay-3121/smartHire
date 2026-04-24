from backend.schemas.scoring import ScoredCandidate, ReasoningOutput
from backend.schemas.job import JobProfile
from backend.services.ollama_client import ollama_client
from backend.core.constants import Recommendation, SHORTLIST_THRESHOLD, HOLD_THRESHOLD
from backend.core.logging import get_logger

logger = get_logger(__name__)

REASONING_SYSTEM_PROMPT = """You are a senior technical recruiter. Analyze a candidate's match against a job and provide structured reasoning.
Return ONLY valid JSON:
{
  "summary": "2-3 sentence overall assessment",
  "strengths": ["strength1", "strength2", "strength3"],
  "gaps": ["gap1", "gap2"],
  "risks": ["risk1"],
  "confidence_level": 0.85,
  "recommendation": "shortlist|hold|reject",
  "recommendation_reason": "one sentence reason"
}
Be honest, specific, and professional."""


def _determine_recommendation(total_score: float) -> Recommendation:
    if total_score >= SHORTLIST_THRESHOLD:
        return Recommendation.SHORTLIST
    elif total_score >= HOLD_THRESHOLD:
        return Recommendation.HOLD
    return Recommendation.REJECT


def _is_clean_matched_item(item: str) -> bool:
    if not item or len(item) > 40:
        return False
    if item.startswith(("#", "*", "-")):
        return False
    if len(item.split()) > 5:
        return False
    return True


def _build_rule_based_reasoning(sc: ScoredCandidate, job: JobProfile) -> ReasoningOutput:
    sb = sc.score_breakdown
    c = sc.candidate
    recommendation = _determine_recommendation(sb.total_score)

    strengths: list[str] = []
    gaps: list[str] = []
    risks: list[str] = []

    # --- Skills ---
    clean_matched = [m for m in sb.role_experience.matched_items if _is_clean_matched_item(m)]
    clean_missing = [m for m in sb.role_experience.missing_items if _is_clean_matched_item(m)]

    if clean_matched:
        strengths.append(f"Matched {len(clean_matched)} required skills: {', '.join(clean_matched[:6])}")
    if clean_missing:
        gaps.append(f"Missing {len(clean_missing)} required skills: {', '.join(clean_missing[:6])}")

    # --- Experience ---
    exp_score = sb.role_experience.raw_score
    if c.total_experience_years >= job.min_experience_years and job.min_experience_years > 0:
        strengths.append(
            f"{c.total_experience_years}y experience satisfies the {job.min_experience_years}y requirement"
            + (f" at {', '.join(c.companies[:2])}" if c.companies else "")
        )
    elif c.total_experience_years > 0 and job.min_experience_years > 0:
        gap_yrs = round(job.min_experience_years - c.total_experience_years, 1)
        gaps.append(
            f"Experience shortfall: {c.total_experience_years}y vs {job.min_experience_years}y required ({gap_yrs}y gap)"
        )
    elif c.total_experience_years > 0:
        strengths.append(f"{c.total_experience_years}y of professional experience")

    # --- Projects ---
    proj_score = sb.relevant_projects.raw_score
    if c.projects:
        proj_techs = list({t for p in c.projects for t in p.technologies})[:5]
        strengths.append(
            f"{len(c.projects)} project(s) demonstrated"
            + (f" using {', '.join(proj_techs)}" if proj_techs else "")
        )
    elif proj_score < 40:
        gaps.append("No projects found; hands-on work cannot be verified")

    # --- Certifications ---
    if c.certifications:
        strengths.append(f"Certified: {', '.join(c.certifications[:3])}")
    elif job.required_certifications:
        gaps.append(f"No certifications found; job requires: {', '.join(job.required_certifications[:3])}")

    # --- Education ---
    edu_score = sb.education.raw_score
    if c.education:
        edu = c.education[0]
        edu_str = f"{edu.degree} — {edu.institution}"
        if edu.graduation_year:
            edu_str += f" ({edu.graduation_year})"
        if edu_score >= 70:
            strengths.append(f"Education matches requirements: {edu_str}")
        else:
            gaps.append(f"Education may not fully meet requirements: {edu_str}")
    elif job.education_requirements:
        gaps.append(f"No education details found; job requires: {job.education_requirements[0]}")

    # --- Soft skills ---
    soft_matched = sb.soft_signals.matched_items
    if soft_matched:
        strengths.append(f"Soft skills present: {', '.join(soft_matched[:4])}")

    # --- Score breakdown insight ---
    dim_scores = {
        "Technical skills": sb.role_experience.raw_score,
        "Projects": sb.relevant_projects.raw_score,
        "Certifications": sb.certifications.raw_score,
        "Education": sb.education.raw_score,
    }
    weakest = min(dim_scores, key=dim_scores.get)
    strongest = max(dim_scores, key=dim_scores.get)
    if dim_scores[weakest] < 40:
        gaps.append(f"Weakest area: {weakest} ({dim_scores[weakest]:.0f}/100)")
    if dim_scores[strongest] >= 80:
        strengths.append(f"Strongest area: {strongest} ({dim_scores[strongest]:.0f}/100)")

    # --- Penalties / risks ---
    for flag in c.warning_flags:
        risks.append(flag)
    if sb.penalty_deductions > 0:
        risks.append(f"Score reduced by {sb.penalty_deductions:.1f} pts due to: {', '.join(c.warning_flags[:2]) or 'profile flags'}")
    if c.parse_confidence < 0.6:
        risks.append(f"Low resume parse confidence ({c.parse_confidence:.0%}) — some data may be missing")

    # --- Summary ---
    skill_coverage = f"{len(clean_matched)}/{len(clean_matched) + len(clean_missing)} required skills matched" if (clean_matched or clean_missing) else "skill coverage unknown"
    if sb.total_score >= 70:
        fit_label = "strong fit"
    elif sb.total_score >= 55:
        fit_label = "good fit"
    elif sb.total_score >= 35:
        fit_label = "partial fit"
    else:
        fit_label = "weak fit"

    summary = (
        f"{c.name or 'Candidate'} is a {fit_label} for the {job.role_title} role with a score of "
        f"{sb.total_score:.1f}/100 ({skill_coverage}, {c.total_experience_years}y experience). "
    )
    if strengths:
        summary += f"Key strengths include {strengths[0].lower()}."
    if gaps:
        summary += f" Primary gap: {gaps[0].lower()}."

    confidence = min(c.parse_confidence * 0.35 + (sb.total_score / 100) * 0.65, 1.0)

    return ReasoningOutput(
        summary=summary,
        strengths=strengths[:6],
        gaps=gaps[:6],
        risks=risks[:4],
        confidence_level=round(confidence, 2),
        recommendation=recommendation,
        recommendation_reason=(
            f"Score {sb.total_score:.1f}/100 — "
            f"{skill_coverage}, {c.total_experience_years}y exp"
            + (f", missing: {', '.join(clean_missing[:3])}" if clean_missing else "")
        ),
    )


def _build_llm_reasoning(sc: ScoredCandidate, job: JobProfile) -> ReasoningOutput | None:
    c = sc.candidate
    sb = sc.score_breakdown

    clean_matched = [m for m in sb.role_experience.matched_items if _is_clean_matched_item(m)]
    clean_missing = [m for m in sb.role_experience.missing_items if _is_clean_matched_item(m)]
    proj_techs = list({t for p in c.projects for t in p.technologies})[:8]

    prompt = f"""Job Title: {job.role_title} ({job.role_type})
Min Experience Required: {job.min_experience_years} years
Must-Have Skills: {', '.join(job.must_have_skills[:12])}
Preferred Skills: {', '.join(job.preferred_skills[:8])}
Required Certifications: {', '.join(job.required_certifications[:5]) or 'None'}
Education Requirements: {', '.join(job.education_requirements[:3]) or 'None'}

Candidate: {c.name or 'Unknown'}
Total Experience: {c.total_experience_years} years
Companies: {', '.join(c.companies[:4]) or 'None listed'}
Skills ({len(c.skills)} total): {', '.join(c.skills[:20])}
Projects ({len(c.projects)}): {', '.join(p.name for p in c.projects[:4])}
Project Technologies: {', '.join(proj_techs) or 'None'}
Certifications: {', '.join(c.certifications[:5]) or 'None'}
Education: {'; '.join(f"{e.degree} at {e.institution}" for e in c.education[:2]) or 'Not specified'}

Scoring Summary:
  Total Score: {sb.total_score:.1f}/100
  Technical Skills: {sb.role_experience.raw_score:.1f}/100 (weight {sb.role_experience.weight}%)
  Projects: {sb.relevant_projects.raw_score:.1f}/100 (weight {sb.relevant_projects.weight}%)
  Certifications: {sb.certifications.raw_score:.1f}/100 (weight {sb.certifications.weight}%)
  Education: {sb.education.raw_score:.1f}/100 (weight {sb.education.weight}%)
  Soft Skills: {sb.soft_signals.raw_score:.1f}/100 (weight {sb.soft_signals.weight}%)
  Semantic Similarity: {sb.semantic_similarity:.2f}
  Penalty Deductions: {sb.penalty_deductions:.1f} pts

Matched Skills ({len(clean_matched)}): {', '.join(clean_matched[:10])}
Missing Skills ({len(clean_missing)}): {', '.join(clean_missing[:10])}
Warning Flags: {', '.join(c.warning_flags) or 'None'}

Provide a detailed recruiter assessment with specific, actionable insights."""

    try:
        data = ollama_client.generate_json(prompt, system=REASONING_SYSTEM_PROMPT)
        recommendation_str = data.get("recommendation", "hold").lower()
        try:
            recommendation = Recommendation(recommendation_str)
        except ValueError:
            recommendation = _determine_recommendation(sb.total_score)

        return ReasoningOutput(
            summary=data.get("summary", ""),
            strengths=data.get("strengths", [])[:5],
            gaps=data.get("gaps", [])[:5],
            risks=data.get("risks", [])[:5],
            confidence_level=float(data.get("confidence_level", 0.7)),
            recommendation=recommendation,
            recommendation_reason=data.get("recommendation_reason", ""),
        )
    except Exception as e:
        logger.warning(f"LLM reasoning failed for {c.file_name}: {e}")
        return None


def run_reasoning_agent(
    scored_candidates: list[ScoredCandidate],
    job: JobProfile,
    use_llm: bool = False,
) -> list[ScoredCandidate]:
    logger.info(f"[REASONING:start] candidates={len(scored_candidates)} llm={use_llm}")

    for sc in scored_candidates:
        llm_reasoning = _build_llm_reasoning(sc, job) if use_llm else None
        sc.reasoning = llm_reasoning or _build_rule_based_reasoning(sc, job)
        logger.info(
            f"[REASONING:done] candidate={sc.candidate.candidate_id} "
            f"score={sc.score_breakdown.total_score:.1f} "
            f"rec={sc.reasoning.recommendation.value} "
            f"conf={sc.reasoning.confidence_level:.0%}"
        )

    logger.info("[REASONING:complete]")
    return scored_candidates
