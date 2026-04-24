import uuid
from pathlib import Path
from backend.schemas.candidate import CandidateProfile, WorkExperience, Education, Project
from backend.tools.resume_parser import parse_resume
from backend.tools.edge_handler import detect_duplicate, detect_multilingual
from backend.services.ollama_client import ollama_client
from backend.core.constants import ParseStatus
from backend.core.logging import get_logger

logger = get_logger(__name__)

RESUME_SYSTEM_PROMPT = """You are an expert resume parser. Extract structured data from resume text.
Return ONLY valid JSON with these exact keys:
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1234567890",
  "summary": "brief professional summary",
  "skills": ["skill1", "skill2"],
  "certifications": ["cert1"],
  "languages": ["English", "Spanish"]
}
Extract only what is present. Use null for missing fields."""


def _build_candidate_profile(parsed: dict, llm_data: dict | None = None) -> CandidateProfile:
    work_exp = [
        WorkExperience(**w) for w in parsed.get("work_experience", [])
        if isinstance(w, dict)
    ]
    education = [
        Education(**e) for e in parsed.get("education", [])
        if isinstance(e, dict)
    ]
    projects = [
        Project(**p) for p in parsed.get("projects", [])
        if isinstance(p, dict)
    ]

    name = parsed.get("name")
    email = parsed.get("email")
    skills = parsed.get("skills", [])
    certifications = parsed.get("certifications", [])

    if llm_data:
        name = name or llm_data.get("name")
        email = email or llm_data.get("email")
        llm_skills = llm_data.get("skills", [])
        if isinstance(llm_skills, list):
            skills = list(dict.fromkeys(skills + llm_skills))[:50]
        llm_certs = llm_data.get("certifications", [])
        if isinstance(llm_certs, list):
            certifications = list(dict.fromkeys(certifications + llm_certs))[:20]

    return CandidateProfile(
        candidate_id=parsed["candidate_id"],
        file_path=parsed["file_path"],
        file_name=parsed["file_name"],
        name=name,
        email=email,
        phone=parsed.get("phone"),
        skills=skills,
        work_experience=work_exp,
        total_experience_years=parsed.get("total_experience_years", 0.0),
        companies=parsed.get("companies", []),
        projects=projects,
        education=education,
        certifications=certifications,
        parse_status=parsed.get("parse_status", ParseStatus.FAILED),
        parse_confidence=parsed.get("parse_confidence", 0.0),
        warning_flags=parsed.get("warning_flags", []),
        raw_text=parsed.get("raw_text", ""),
        content_hash=parsed.get("content_hash"),
    )


def run_resume_parser_agent(file_paths: list[str]) -> list[CandidateProfile]:
    logger.info(f"Resume Parser Agent: processing {len(file_paths)} files")
    profiles: list[CandidateProfile] = []
    seen_hashes: set[str] = set()

    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            continue

        candidate_id = str(uuid.uuid4())
        logger.info(f"Parsing: {path.name} (id={candidate_id})")

        try:
            parsed = parse_resume(file_path, candidate_id)
        except Exception as e:
            logger.error(f"Parse failed for {path.name}: {e}")
            profiles.append(CandidateProfile(
                candidate_id=candidate_id,
                file_path=file_path,
                file_name=path.name,
                parse_status=ParseStatus.FAILED,
                parse_confidence=0.0,
                warning_flags=[f"Parse error: {str(e)}"],
            ))
            continue

        # Duplicate detection
        content_hash = parsed.get("content_hash")
        if content_hash and detect_duplicate(
            CandidateProfile(candidate_id=candidate_id, file_path=file_path,
                             file_name=path.name, content_hash=content_hash),
            seen_hashes
        ):
            parsed["warning_flags"] = parsed.get("warning_flags", []) + ["Duplicate resume"]
            parsed_profile = _build_candidate_profile(parsed)
            parsed_profile.is_duplicate = True
            profiles.append(parsed_profile)
            continue

        if content_hash:
            seen_hashes.add(content_hash)

        # Multilingual detection
        raw_text = parsed.get("raw_text", "")
        if detect_multilingual(raw_text):
            parsed["warning_flags"] = parsed.get("warning_flags", []) + ["Multilingual resume detected"]

        # LLM enhancement for low-confidence parses
        llm_data = None
        if parsed.get("parse_confidence", 1.0) < 0.8 and raw_text:
            try:
                prompt = f"Parse this resume and extract key information:\n\n{raw_text[:2000]}"
                llm_data = ollama_client.generate_json(prompt, system=RESUME_SYSTEM_PROMPT)
                logger.debug(f"LLM enhanced parsing for {path.name}")
            except Exception as e:
                logger.warning(f"LLM enhancement failed for {path.name}: {e}")

        profile = _build_candidate_profile(parsed, llm_data)
        profiles.append(profile)
        logger.info(f"Parsed {path.name}: confidence={profile.parse_confidence:.0%}, skills={len(profile.skills)}")

    logger.info(f"Resume Parser Agent: completed {len(profiles)} profiles")
    return profiles
