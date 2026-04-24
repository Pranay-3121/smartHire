from backend.schemas.candidate import CandidateProfile
from backend.schemas.job import JobProfile
from backend.schemas.scoring import ScoredCandidate
from backend.tools.scorer import score_candidate
from backend.services.embeddings import embedding_service
from backend.core.logging import get_logger

logger = get_logger(__name__)


def _compute_tiebreak(candidate: CandidateProfile, job: JobProfile) -> float:
    score = 0.0
    score += min(candidate.total_experience_years * 0.5, 5.0)
    score += min(len(candidate.certifications) * 0.3, 3.0)
    score += min(len(candidate.projects) * 0.2, 2.0)
    if candidate.parse_confidence:
        score += candidate.parse_confidence * 2.0
    return round(score, 4)


def _index_candidates_in_chroma(candidates: list[CandidateProfile], run_id: str) -> None:
    for candidate in candidates:
        if not candidate.raw_text:
            continue
        try:
            doc_text = f"{' '.join(candidate.skills)} {candidate.raw_text[:800]}"
            embedding_service.upsert_document(
                doc_id=candidate.candidate_id,
                text=doc_text,
                metadata={
                    "name": candidate.name or "Unknown",
                    "file": candidate.file_name,
                    "run_id": run_id,
                },
                collection_name=f"run_{run_id}",
            )
        except Exception as e:
            logger.warning(f"Failed to index candidate {candidate.candidate_id}: {e}")


def run_ranking_agent(
    candidates: list[CandidateProfile],
    job: JobProfile,
    run_id: str,
) -> list[ScoredCandidate]:
    logger.info(f"[RANKING:start] run_id={run_id} job='{job.role_title}' candidates={len(candidates)}")

    _index_candidates_in_chroma(candidates, run_id)

    scored: list[ScoredCandidate] = []
    for candidate in candidates:
        if candidate.is_duplicate:
            logger.info(f"[RANKING:skip] duplicate: {candidate.file_name}")
            continue
        try:
            breakdown = score_candidate(candidate, job)
            tiebreak = _compute_tiebreak(candidate, job)
            scored.append(ScoredCandidate(
                candidate=candidate,
                score_breakdown=breakdown,
                tiebreak_score=tiebreak,
            ))
            logger.info(
                f"[RANKING:scored] candidate={candidate.candidate_id} name={candidate.name or 'Unknown'} "
                f"score={breakdown.total_score:.1f} tiebreak={tiebreak:.2f}"
            )
        except Exception as e:
            logger.error(f"[RANKING:error] candidate={candidate.candidate_id}: {e}")

    # Sort by total_score desc, then tiebreak desc
    scored.sort(
        key=lambda sc: (sc.score_breakdown.total_score, sc.tiebreak_score),
        reverse=True,
    )

    for rank, sc in enumerate(scored, start=1):
        sc.rank = rank

    # Log summary
    if scored:
        top_score = scored[0].score_breakdown.total_score
        bottom_score = scored[-1].score_breakdown.total_score
        shortlisted = sum(1 for sc in scored if sc.score_breakdown.total_score >= 70)
        hold = sum(1 for sc in scored if 50 <= sc.score_breakdown.total_score < 70)
        reject = sum(1 for sc in scored if sc.score_breakdown.total_score < 50)
        logger.info(
            f"[RANKING:done] ranked={len(scored)} top={top_score:.1f} bottom={bottom_score:.1f} "
            f"shortlist={shortlisted} hold={hold} reject={reject}"
        )

    return scored
