from backend.schemas.job import JobProfile
from backend.tools.jd_parser import parse_jd_rules
from backend.services.ollama_client import ollama_client
from backend.core.logging import get_logger

logger = get_logger(__name__)

JD_SYSTEM_PROMPT = """You are an expert HR analyst. Extract structured information from job descriptions.
Return ONLY valid JSON with these exact keys:
{
  "role_title": "string",
  "role_type": "engineering|compliance|fresher|management|design|data_science|sales|general",
  "must_have_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "min_experience_years": 0,
  "max_experience_years": null,
  "required_certifications": ["cert1"],
  "preferred_certifications": ["cert1"],
  "education_requirements": ["Bachelor's in CS"],
  "soft_skills": ["communication", "teamwork"],
  "responsibilities": ["responsibility1"]
}
Be precise. Extract only what is explicitly stated."""


def _clean_skill_list(skills: list[str]) -> list[str]:
    """Remove markdown artifacts, headers, locations, and sentences from skill lists."""
    cleaned = []
    for s in skills:
        s = s.strip()
        if not s:
            continue
        sl = s.lower()
        # Skip markdown headers
        if s.startswith("#") or s.startswith("##") or s.startswith("###"):
            continue
        # Skip locations and long sentences
        if len(s) > 40:
            continue
        # Skip common non-skill artifacts
        if any(artifact in sl for artifact in [
            "location", "remote", "hybrid", "onsite", "mumbai", "pune", "bengaluru", "delhi",
            "chennai", "hyderabad", "kolkata", "ahmedabad", "noida", "gurugram", "bangalore",
            "0 to", "1 to", "2 to", "3 to", "4 to", "5 to", "years", "year experience",
            "salary", "compensation", "benefits", "perks", "apply now", "about us",
            "job description", "role summary", "key responsibilities", "requirements",
        ]):
            continue
        # Skip if it contains too many words (likely a sentence)
        if len(s.split()) > 5:
            continue
        cleaned.append(s)
    return list(dict.fromkeys(cleaned))


def _clean_education_requirements(reqs: list[str]) -> list[str]:
    cleaned = []
    for r in reqs:
        r = r.strip()
        if not r:
            continue
        rl = r.lower()
        if any(artifact in rl for artifact in ["location", "remote", "hybrid", "mumbai", "pune", "bengaluru"]):
            continue
        if any(kw in rl for kw in ["bachelor", "master", "phd", "b.tech", "m.tech", "bca", "mca", "b.sc", "m.sc", "diploma", "degree"]):
            cleaned.append(r)
    return cleaned


def _clean_certifications(certs: list[str]) -> list[str]:
    cleaned = []
    for c in certs:
        c = c.strip()
        if not c:
            continue
        cl = c.lower()
        if any(kw in cl for kw in ["certified", "certification", "certificate", "aws", "azure", "google", "microsoft", "pmp", "cissp", "ccna", "comptia"]):
            cleaned.append(c)
    return cleaned


def run_jd_reader_agent(jd_text: str) -> JobProfile:
    logger.info("JD Reader Agent: starting extraction")

    rule_based = parse_jd_rules(jd_text)

    # Clean rule-based output immediately
    rule_based["must_have_skills"] = _clean_skill_list(rule_based.get("must_have_skills", []))
    rule_based["preferred_skills"] = _clean_skill_list(rule_based.get("preferred_skills", []))
    rule_based["education_requirements"] = _clean_education_requirements(rule_based.get("education_requirements", []))
    rule_based["required_certifications"] = _clean_certifications(rule_based.get("required_certifications", []))
    rule_based["preferred_certifications"] = _clean_certifications(rule_based.get("preferred_certifications", []))

    try:
        prompt = f"Extract structured hiring requirements from this job description:\n\n{jd_text[:3000]}"
        llm_data = ollama_client.generate_json(prompt, system=JD_SYSTEM_PROMPT)

        merged = _merge_jd_data(rule_based, llm_data)
        # Clean again after merge
        merged["must_have_skills"] = _clean_skill_list(merged.get("must_have_skills", []))
        merged["preferred_skills"] = _clean_skill_list(merged.get("preferred_skills", []))
        merged["education_requirements"] = _clean_education_requirements(merged.get("education_requirements", []))
        merged["required_certifications"] = _clean_certifications(merged.get("required_certifications", []))
        merged["preferred_certifications"] = _clean_certifications(merged.get("preferred_certifications", []))

        profile = JobProfile(**merged)
        logger.info(
            f"[JD:parsed] role='{profile.role_title}' type={profile.role_type} "
            f"must_have={len(profile.must_have_skills)} preferred={len(profile.preferred_skills)} "
            f"min_exp={profile.min_experience_years} max_exp={profile.max_experience_years} "
            f"edu_req={len(profile.education_requirements)} certs={len(profile.required_certifications)}"
        )
        return profile

    except Exception as e:
        logger.warning(f"LLM JD extraction failed, using rule-based only: {e}")
        profile = JobProfile(**rule_based)
        logger.info(
            f"[JD:parsed] role='{profile.role_title}' type={profile.role_type} "
            f"must_have={len(profile.must_have_skills)} preferred={len(profile.preferred_skills)} "
            f"min_exp={profile.min_experience_years} (rule-based fallback)"
        )
        return profile


def _merge_jd_data(rule_based: dict, llm_data: dict) -> dict:
    merged = dict(rule_based)

    for key in ["must_have_skills", "preferred_skills", "required_certifications",
                "preferred_certifications", "education_requirements", "soft_skills", "responsibilities"]:
        llm_list = llm_data.get(key, [])
        rule_list = rule_based.get(key, [])
        if isinstance(llm_list, list) and isinstance(rule_list, list):
            combined = list(dict.fromkeys(rule_list + llm_list))
            merged[key] = combined[:30]

    if llm_data.get("role_title") and llm_data["role_title"] != "Unknown Role":
        merged["role_title"] = llm_data["role_title"]

    if llm_data.get("role_type"):
        raw_rt = str(llm_data["role_type"]).split("|")[0].strip().lower()
        valid_types = {"engineering", "compliance", "fresher", "management", "design", "data_science", "sales", "general"}
        if raw_rt in valid_types:
            merged["role_type"] = raw_rt

    if llm_data.get("min_experience_years") is not None:
        merged["min_experience_years"] = float(llm_data["min_experience_years"] or 0)

    if llm_data.get("max_experience_years") is not None:
        merged["max_experience_years"] = float(llm_data["max_experience_years"])

    return merged
