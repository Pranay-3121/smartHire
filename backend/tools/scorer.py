import re
from difflib import SequenceMatcher
from backend.schemas.candidate import CandidateProfile
from backend.schemas.job import JobProfile
from backend.schemas.scoring import ScoreBreakdown, ScoreDimension
from backend.tools.role_classifier import get_weights_for_role
from backend.tools.edge_handler import compute_penalties
from backend.services.embeddings import embedding_service
from backend.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Transferable skill aliases — partial credit for related technologies
# ---------------------------------------------------------------------------
SKILL_ALIASES: dict[str, list[str]] = {
    "python": ["django", "flask", "fastapi", "tornado", "backend"],
    "fastapi": ["flask", "django", "tornado", "python", "backend"],
    "flask": ["fastapi", "django", "tornado", "python", "backend"],
    "django": ["fastapi", "flask", "tornado", "python", "backend"],
    "sql": ["mysql", "postgresql", "sqlite", "database", "mongodb", "nosql"],
    "mysql": ["sql", "postgresql", "sqlite", "database", "nosql"],
    "postgresql": ["sql", "mysql", "sqlite", "database", "nosql"],
    "sqlite": ["sql", "mysql", "postgresql", "database"],
    "database": ["sql", "mysql", "postgresql", "sqlite", "mongodb"],
    "mongodb": ["database", "nosql", "sql"],
    "react": ["javascript", "frontend", "angular", "vue", "js"],
    "angular": ["javascript", "frontend", "react", "vue", "js"],
    "vue": ["javascript", "frontend", "react", "angular", "js"],
    "javascript": ["js", "frontend", "react", "angular", "vue", "typescript"],
    "typescript": ["javascript", "js", "frontend", "react", "angular"],
    "aws": ["cloud", "azure", "gcp", "amazon web services"],
    "azure": ["cloud", "aws", "gcp", "microsoft azure"],
    "gcp": ["cloud", "aws", "azure", "google cloud"],
    "docker": ["container", "containerization", "kubernetes"],
    "kubernetes": ["container", "containerization", "docker", "k8s"],
    "git": ["github", "gitlab", "version control"],
    "github": ["git", "gitlab", "version control"],
    "linux": ["unix", "ubuntu", "debian", "centos", "os"],
    "html": ["frontend", "web", "css"],
    "css": ["frontend", "web", "html", "tailwind"],
    "tailwind": ["css", "frontend", "web"],
    "machine learning": ["ml", "deep learning", "ai", "data science"],
    "deep learning": ["ml", "machine learning", "ai", "neural networks"],
    "ai": ["machine learning", "ml", "deep learning", "data science"],
    "data science": ["machine learning", "ml", "deep learning", "ai"],
    "pytorch": ["tensorflow", "keras", "ml framework"],
    "tensorflow": ["pytorch", "keras", "ml framework"],
    "pandas": ["numpy", "data analysis", "python"],
    "numpy": ["pandas", "data analysis", "python"],
    "spark": ["hadoop", "big data", "data engineering"],
    "hadoop": ["spark", "big data", "data engineering"],
    "kafka": ["rabbitmq", "message queue", "event streaming"],
    "microservices": ["rest api", "api", "backend", "distributed systems"],
    "rest api": ["api", "microservices", "backend", "graphql"],
    "graphql": ["rest api", "api", "backend"],
    "c++": ["c", "cpp", "systems programming"],
    "c#": [".net", "csharp", "microsoft"],
    "java": ["spring", "backend", "jvm"],
    "spring": ["java", "backend", "jvm"],
    "go": ["golang", "backend", "systems"],
    "golang": ["go", "backend", "systems"],
    "rust": ["systems programming", "backend"],
    "node.js": ["nodejs", "node", "backend", "javascript"],
    "nodejs": ["node.js", "node", "backend", "javascript"],
    "express": ["node.js", "nodejs", "backend", "javascript"],
    "php": ["backend", "web", "laravel"],
    "laravel": ["php", "backend", "web"],
    "ruby": ["rails", "backend", "web"],
    "rails": ["ruby", "backend", "web"],
    "scala": ["spark", "big data", "jvm"],
    "kotlin": ["android", "java", "jvm"],
    "swift": ["ios", "mobile", "apple"],
    "flutter": ["dart", "mobile", "cross-platform"],
    "dart": ["flutter", "mobile"],
    "android": ["kotlin", "java", "mobile"],
    "ios": ["swift", "mobile", "apple"],
    "figma": ["design", "ui", "ux"],
    "photoshop": ["design", "ui", "ux", "adobe"],
    "tableau": ["data visualization", "bi", "analytics"],
    "power bi": ["data visualization", "bi", "analytics"],
    "excel": ["data analysis", "spreadsheet", "microsoft"],
    "wordpress": ["cms", "web", "php"],
    "jenkins": ["ci/cd", "devops", "automation"],
    "gitlab ci": ["ci/cd", "devops", "automation"],
    "terraform": ["iac", "infrastructure", "devops"],
    "ansible": ["iac", "infrastructure", "devops", "automation"],
    "prometheus": ["monitoring", "observability", "devops"],
    "grafana": ["monitoring", "observability", "devops"],
    "elasticsearch": ["search", "elastic", "backend"],
    "redis": ["cache", "database", "backend"],
    "nginx": ["web server", "reverse proxy", "backend"],
    "apache": ["web server", "backend"],
}


def _fuzzy_match(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _is_direct_match(candidate_skill: str, jd_skill: str) -> bool:
    """Check direct, substring, or high fuzzy match."""
    c = candidate_skill.lower().strip()
    j = jd_skill.lower().strip()
    if c == j:
        return True
    if c in j or j in c:
        return True
    if _fuzzy_match(c, j) > 0.82:
        return True
    return False


def _find_alias_match(candidate_skills: list[str], jd_skill: str) -> bool:
    """Check if any candidate skill is an alias of the JD skill."""
    j = jd_skill.lower().strip()
    aliases = SKILL_ALIASES.get(j, [])
    for cs in candidate_skills:
        c = cs.lower().strip()
        if c in aliases or any(_fuzzy_match(c, a) > 0.82 for a in aliases):
            return True
    return False


def _skill_overlap(candidate_skills: list[str], jd_skills: list[str]) -> tuple[float, list[str], list[str]]:
    if not jd_skills:
        return 100.0, [], []

    matched = []
    alias_matched = []
    missing = []

    for jd_skill in jd_skills:
        # Direct match
        found_direct = any(_is_direct_match(cs, jd_skill) for cs in candidate_skills)
        if found_direct:
            matched.append(jd_skill)
            continue

        # Alias / transferable match
        found_alias = _find_alias_match(candidate_skills, jd_skill)
        if found_alias:
            alias_matched.append(jd_skill)
            continue

        missing.append(jd_skill)

    # Score: direct = 1.0, alias = 0.6
    score = (len(matched) + 0.6 * len(alias_matched)) / len(jd_skills) * 100
    return min(score, 100.0), matched + alias_matched, missing


def _score_role_experience(candidate: CandidateProfile, job: JobProfile, weight: int) -> ScoreDimension:
    must_score, must_matched, must_missing = _skill_overlap(candidate.skills, job.must_have_skills)
    pref_score, pref_matched, _ = _skill_overlap(candidate.skills, job.preferred_skills)

    # If must-have is tiny or empty, weight preferred more heavily
    if len(job.must_have_skills) < 3 and job.preferred_skills:
        combined_score = (must_score * 0.3 + pref_score * 0.7)
    else:
        combined_score = (must_score * 0.7 + pref_score * 0.3) if job.preferred_skills else must_score

    # Experience years scoring — be generous for entry-level roles
    if job.min_experience_years > 0:
        if candidate.total_experience_years >= job.min_experience_years:
            exp_score = 100.0
        else:
            # Partial credit: don't punish too hard
            ratio = candidate.total_experience_years / max(job.min_experience_years, 1.0)
            exp_score = max(ratio * 80.0, 20.0)  # floor at 20 so not zero
    else:
        # No experience required — freshers get full credit if they have projects/skills
        if candidate.total_experience_years > 0:
            exp_score = 90.0
        elif candidate.projects or len(candidate.skills) >= 5:
            exp_score = 80.0
        else:
            exp_score = 50.0

    raw = combined_score * 0.6 + exp_score * 0.4
    weighted = raw * weight / 100

    logger.debug(
        f"[SCORE:role_experience] candidate={candidate.candidate_id} "
        f"must_score={must_score:.1f} pref_score={pref_score:.1f} exp_score={exp_score:.1f} "
        f"raw={raw:.1f} weighted={weighted:.1f}"
    )

    return ScoreDimension(
        raw_score=round(raw, 2),
        weighted_score=round(weighted, 2),
        weight=weight,
        matched_items=must_matched + pref_matched,
        missing_items=must_missing,
        notes=f"Experience: {candidate.total_experience_years}y, Required: {job.min_experience_years}y",
    )


def _score_projects(candidate: CandidateProfile, job: JobProfile, weight: int) -> ScoreDimension:
    all_jd_skills = set(s.lower() for s in job.must_have_skills + job.preferred_skills)

    if not candidate.projects:
        # No projects — don't zero out. Use skills + experience as proxy.
        if candidate.work_experience and len(candidate.work_experience) > 0:
            raw = 55.0  # professional experience compensates
        elif len(candidate.skills) >= 5:
            raw = 45.0  # strong skill set suggests capability
        elif candidate.education:
            raw = 35.0  # at least has education
        else:
            raw = 15.0
        weighted = raw * weight / 100
        logger.debug(
            f"[SCORE:projects] candidate={candidate.candidate_id} no_projects "
            f"fallback_raw={raw:.1f} weighted={weighted:.1f}"
        )
        return ScoreDimension(
            raw_score=round(raw, 2),
            weighted_score=round(weighted, 2),
            weight=weight,
            matched_items=[],
            missing_items=[],
            notes="No explicit projects; fallback based on experience/skills",
        )

    matched_techs = []
    for project in candidate.projects:
        for tech in project.technologies:
            if tech.lower() in all_jd_skills:
                matched_techs.append(tech)
            else:
                # Also check aliases
                for jd_skill in all_jd_skills:
                    if _is_direct_match(tech, jd_skill) or _find_alias_match([tech], jd_skill):
                        matched_techs.append(tech)
                        break

    project_count_score = min(len(candidate.projects) / 3 * 100, 100)
    tech_relevance_score = (len(set(matched_techs)) / max(len(all_jd_skills), 1)) * 100 if all_jd_skills else 60.0

    raw = project_count_score * 0.4 + tech_relevance_score * 0.6
    weighted = raw * weight / 100

    logger.debug(
        f"[SCORE:projects] candidate={candidate.candidate_id} "
        f"proj_count={len(candidate.projects)} matched_techs={len(set(matched_techs))} "
        f"raw={raw:.1f} weighted={weighted:.1f}"
    )

    return ScoreDimension(
        raw_score=round(raw, 2),
        weighted_score=round(weighted, 2),
        weight=weight,
        matched_items=list(set(matched_techs)),
        notes=f"{len(candidate.projects)} projects found",
    )


def _score_certifications(candidate: CandidateProfile, job: JobProfile, weight: int) -> ScoreDimension:
    # If no certs required by job, be neutral — don't punish
    if not job.required_certifications and not job.preferred_certifications:
        raw = 70.0  # neutral baseline
        weighted = raw * weight / 100
        logger.debug(
            f"[SCORE:certifications] candidate={candidate.candidate_id} no_req_certs "
            f"neutral_raw={raw:.1f} weighted={weighted:.1f}"
        )
        return ScoreDimension(
            raw_score=raw,
            weighted_score=round(weighted, 2),
            weight=weight,
            matched_items=[],
            missing_items=[],
            notes="No certifications required by job",
        )

    all_required = job.required_certifications + job.preferred_certifications
    matched, missing = [], []
    for req_cert in all_required:
        found = any(_fuzzy_match(req_cert, c) > 0.7 for c in candidate.certifications)
        if found:
            matched.append(req_cert)
        else:
            missing.append(req_cert)

    raw = (len(matched) / len(all_required)) * 100
    weighted = raw * weight / 100

    logger.debug(
        f"[SCORE:certifications] candidate={candidate.candidate_id} "
        f"matched={len(matched)} total_req={len(all_required)} raw={raw:.1f} weighted={weighted:.1f}"
    )

    return ScoreDimension(
        raw_score=round(raw, 2),
        weighted_score=round(weighted, 2),
        weight=weight,
        matched_items=matched,
        missing_items=missing,
    )


def _score_education(candidate: CandidateProfile, job: JobProfile, weight: int) -> ScoreDimension:
    if not job.education_requirements:
        raw = 70.0 if candidate.education else 40.0
        weighted = raw * weight / 100
        logger.debug(
            f"[SCORE:education] candidate={candidate.candidate_id} no_req_edu "
            f"has_edu={bool(candidate.education)} raw={raw:.1f} weighted={weighted:.1f}"
        )
        return ScoreDimension(
            raw_score=raw,
            weighted_score=round(weighted, 2),
            weight=weight,
            matched_items=[],
            missing_items=[],
            notes="No education requirements specified" if not job.education_requirements else "",
        )

    edu_text = " ".join(
        f"{e.degree} {e.institution} {e.field_of_study or ''}"
        for e in candidate.education
    ).lower()

    # Degree equivalence map for common abbreviations
    DEGREE_ALIASES = {
        "bca": ["bachelor of computer applications", "computer applications"],
        "bsc": ["bachelor of science", "b.sc", "bs"],
        "btec": ["b.tech", "bachelor of technology", "btech"],
        "b.tech": ["bachelor of technology", "btech", "btec"],
        "mca": ["master of computer applications"],
        "msc": ["master of science", "m.sc"],
        "m.tech": ["master of technology", "mtech"],
        "mba": ["master of business administration"],
        "bachelor": ["b.tech", "btech", "bca", "bsc", "b.sc", "be", "b.e"],
        "degree": ["bachelor", "b.tech", "bca", "bsc", "diploma"],
    }

    def _edu_matches(req: str, edu_text: str) -> bool:
        # Split slash-separated alternatives like "BCA / BSc CS / BTech"
        alternatives = [a.strip().lower() for a in re.split(r"[/|,]", req)]
        for alt in alternatives:
            alt_words = set(alt.split())
            edu_words = set(edu_text.split())
            # Direct word overlap
            if alt_words & edu_words:
                return True
            # Substring check
            if any(word in edu_text for word in alt_words if len(word) > 2):
                return True
            # Alias check
            for word in alt_words:
                for alias in DEGREE_ALIASES.get(word, []):
                    if alias in edu_text:
                        return True
        return False

    matched = [req for req in job.education_requirements if _edu_matches(req, edu_text)]
    missing = [req for req in job.education_requirements if not _edu_matches(req, edu_text)]

    raw = (len(matched) / len(job.education_requirements)) * 100
    weighted = raw * weight / 100

    logger.debug(
        f"[SCORE:education] candidate={candidate.candidate_id} "
        f"matched={len(matched)} total_req={len(job.education_requirements)} raw={raw:.1f} weighted={weighted:.1f}"
    )

    return ScoreDimension(
        raw_score=round(raw, 2),
        weighted_score=round(weighted, 2),
        weight=weight,
        matched_items=matched,
        missing_items=missing,
    )


def _score_soft_signals(candidate: CandidateProfile, job: JobProfile, weight: int) -> ScoreDimension:
    if not job.soft_skills:
        raw = 70.0
        weighted = raw * weight / 100
        logger.debug(
            f"[SCORE:soft_signals] candidate={candidate.candidate_id} no_soft_skills_req "
            f"neutral_raw={raw:.1f} weighted={weighted:.1f}"
        )
        return ScoreDimension(
            raw_score=raw,
            weighted_score=round(weighted, 2),
            weight=weight,
            matched_items=[],
            missing_items=[],
            notes="No soft skills required",
        )

    candidate_text = (candidate.raw_text + " " + (candidate.summary or "")).lower()
    matched = [s for s in job.soft_skills if s.lower() in candidate_text]
    missing = [s for s in job.soft_skills if s.lower() not in candidate_text]

    raw = (len(matched) / len(job.soft_skills)) * 100
    weighted = raw * weight / 100

    logger.debug(
        f"[SCORE:soft_signals] candidate={candidate.candidate_id} "
        f"matched={len(matched)} total={len(job.soft_skills)} raw={raw:.1f} weighted={weighted:.1f}"
    )

    return ScoreDimension(
        raw_score=round(raw, 2),
        weighted_score=round(weighted, 2),
        weight=weight,
        matched_items=matched,
        missing_items=missing,
    )


def _compute_semantic_similarity(candidate: CandidateProfile, job: JobProfile) -> float:
    try:
        candidate_text = f"{' '.join(candidate.skills)} {candidate.raw_text[:1000]}"
        jd_text = f"{' '.join(job.must_have_skills)} {job.raw_text[:1000]}"
        similarity = embedding_service.compute_similarity(candidate_text, jd_text)
        sim = round(float(similarity), 4)
        logger.debug(f"[SCORE:semantic] candidate={candidate.candidate_id} similarity={sim:.4f}")
        return sim
    except Exception as e:
        logger.warning(f"Semantic similarity failed for {candidate.candidate_id}: {e}")
        return 0.0


def score_candidate(candidate: CandidateProfile, job: JobProfile) -> ScoreBreakdown:
    weights = get_weights_for_role(job.role_type)

    logger.info(
        f"[SCORE:start] candidate={candidate.candidate_id} name={candidate.name or 'Unknown'} "
        f"job={job.role_title} type={job.role_type} "
        f"must_skills={len(job.must_have_skills)} pref_skills={len(job.preferred_skills)} "
        f"min_exp={job.min_experience_years}"
    )

    exp_dim = _score_role_experience(candidate, job, weights["role_experience"])
    proj_dim = _score_projects(candidate, job, weights["relevant_projects"])
    cert_dim = _score_certifications(candidate, job, weights["certifications"])
    edu_dim = _score_education(candidate, job, weights["education"])
    soft_dim = _score_soft_signals(candidate, job, weights["soft_signals"])

    semantic_sim = _compute_semantic_similarity(candidate, job)

    base_score = (
        exp_dim.weighted_score
        + proj_dim.weighted_score
        + cert_dim.weighted_score
        + edu_dim.weighted_score
        + soft_dim.weighted_score
    )

    # Semantic similarity bonus (up to 5 points)
    semantic_bonus = semantic_sim * 5.0

    penalties, penalty_reasons = compute_penalties(candidate, job)

    if penalty_reasons:
        logger.info(f"[SCORE:penalties] candidate={candidate.candidate_id} penalties={penalties:.1f} reasons={penalty_reasons}")

    total = round(min(max(base_score + semantic_bonus - penalties, 0.0), 100.0), 2)

    logger.info(
        f"[SCORE:total] candidate={candidate.candidate_id} "
        f"base={base_score:.1f} semantic_bonus={semantic_bonus:.1f} penalties={penalties:.1f} "
        f"total={total:.1f}"
    )

    return ScoreBreakdown(
        role_experience=exp_dim,
        relevant_projects=proj_dim,
        certifications=cert_dim,
        education=edu_dim,
        soft_signals=soft_dim,
        semantic_similarity=semantic_sim,
        penalty_deductions=round(penalties, 2),
        total_score=total,
    )

