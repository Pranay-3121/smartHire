import re
from backend.core.logging import get_logger
from backend.core.constants import RoleType

logger = get_logger(__name__)

ROLE_TYPE_KEYWORDS: dict[str, list[str]] = {
    RoleType.ENGINEERING: ["engineer", "developer", "software", "backend", "frontend", "fullstack", "devops", "sre"],
    RoleType.DATA_SCIENCE: ["data scientist", "machine learning", "ml engineer", "ai engineer", "data analyst", "nlp"],
    RoleType.COMPLIANCE: ["compliance", "audit", "regulatory", "risk", "legal", "governance"],
    RoleType.MANAGEMENT: ["manager", "director", "vp", "head of", "lead", "principal", "cto", "ceo"],
    RoleType.DESIGN: ["designer", "ux", "ui", "product design", "graphic", "figma"],
    RoleType.SALES: ["sales", "account executive", "business development", "revenue", "growth"],
    RoleType.FRESHER: ["fresher", "entry level", "junior", "graduate", "intern", "trainee", "0-1 year", "0-2 year"],
}

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+)\+?\s*[-–]\s*(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE),
    re.compile(r"minimum\s+(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"at\s+least\s+(\d+)\s*years?", re.IGNORECASE),
]

MUST_HAVE_MARKERS = ["required", "must have", "mandatory", "essential", "minimum requirement"]
PREFERRED_MARKERS = ["preferred", "nice to have", "bonus", "plus", "desired", "good to have"]

SOFT_SKILL_KEYWORDS = [
    "communication", "teamwork", "leadership", "problem solving",
    "collaboration", "adaptability", "time management", "critical thinking",
    "attention to detail", "self-motivated", "proactive", "interpersonal",
    "conflict resolution", "mentoring", "stakeholder management",
    "presentation skills", "negotiation", "decision making",
]

# Soft skills must appear in a meaningful context, not just anywhere in the JD
_SOFT_SKILL_CONTEXT_PATTERNS = [
    r"(?:strong|excellent|good|proven|demonstrated)\s+{skill}",
    r"{skill}\s+skills?",
    r"ability\s+to\s+{skill}",
    r"(?:require|need|must have|looking for).*{skill}",
]

# Section headers that terminate a skills/requirements block
SECTION_STOP_HEADERS = [
    "responsibilities", "what you'll do", "key responsibilities", "duties",
    "benefits", "perks", "we offer", "compensation", "salary",
    "about us", "about the company", "who we are",
    "apply now", "how to apply", "contact us",
    "location", "work location", "remote", "onsite", "hybrid",
    "job type", "employment type", "full-time", "part-time", "contract",
    "equal opportunity", "diversity", "disclaimer",
    "role summary", "job summary", "position summary",
    "reporting to", "team structure",
]

# Noise words that should not be treated as skills
SKILL_NOISE_WORDS = {
    "and", "or", "with", "in", "of", "to", "for", "the", "a", "an",
    "proficient", "strong", "expertise", "experience", "skilled", "familiar",
    "knowledge", "good", "excellent", "solid", "understanding", "ability",
    "years", "year", "plus", "including", "such", "as", "like", "etc",
    "required", "preferred", "mandatory", "essential", "desired", "bonus",
    "must", "have", "nice", "good", "well", "working", "using",
}

TECH_SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "swift",
    "react", "angular", "vue", "node.js", "django", "fastapi", "flask", "spring", "express",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins",
    "machine learning", "deep learning", "nlp", "computer vision", "pytorch", "tensorflow",
    "pandas", "numpy", "scikit-learn", "spark", "hadoop", "kafka", "airflow",
    "git", "linux", "agile", "scrum", "rest api", "graphql", "microservices",
    "html", "css", "tailwind", "figma", "photoshop", "php", "ruby", "perl", "scala",
    "r", "matlab", "opencv", "seaborn", "matplotlib", "plotly", "powerbi", "tableau",
    "next.js", "nuxt", "svelte", "jquery", "bootstrap", "sass", "less",
    "firebase", "supabase", "heroku", "netlify", "vercel", "digitalocean",
    "nginx", "apache", "rabbitmq", "celery", "lodash", "axios", "redux",
    "webpack", "vite", "babel", "eslint", "prettier", "jest", "cypress",
    "mocha", "chai", "pytest", "unittest", "junit", "selenium", "puppeteer",
    "opencv", "keras", "xgboost", "lightgbm", "catboost", "spacy", "nltk",
    "huggingface", "transformers", "bert", "gpt", "llm", "langchain",
    "sqlite", "mariadb", "oracle", "db2", "snowflake", "bigquery", "databricks",
    "prometheus", "grafana", "datadog", "new relic", "splunk", "elk",
    "circleci", "travis", "github actions", "gitlab ci", "bamboo",
    "puppet", "chef", "saltstack", "vagrant", "virtualbox", "vmware",
    "ios", "android", "flutter", "react native", "xamarin", "ionic",
    "unity", "unreal", "blender", "maya", "3ds max", "cad", "autocad",
    "solidity", "ethereum", "web3", "blockchain", "smart contracts",
    "cuda", "opencl", "mpi", "openmp", "fortran", "cobol", "abap",
    "sap", "salesforce", "dynamics", "hubspot", "marketo", "mailchimp",
    "wordpress", "drupal", "joomla", "magento", "shopify", "woocommerce",
    "selenium", "appium", "postman", "swagger", "openapi", "grpc",
    "oauth", "jwt", "ldap", "active directory", "sso", "mfa",
    "pentesting", "burp suite", "metasploit", "nmap", "wireshark",
    "gdpr", "hipaa", "soc2", "iso 27001", "pci dss", "sox",
    "jira", "confluence", "trello", "asana", "monday", "notion",
    "slack", "teams", "zoom", "meet", "webex",
    "excel", "word", "powerpoint", "outlook", "access", "visio",
    "sap", "oracle erp", "netsuite", "workday", "peoplesoft",
    "quickbooks", "xero", "freshbooks", "zoho",
    "google analytics", "google ads", "facebook ads", "seo", "sem",
    "contentful", "prismic", "sanity", "strapi", "directus",
    "figma", "sketch", "adobe xd", "invision", "framer", "proto.io",
    "photoshop", "illustrator", "indesign", "after effects", "premiere",
    "lightroom", "audition", "animate", "dreamweaver",
    "canva", "crello", "picmonkey", "snappa",
    "rstudio", "jupyter", "colab", "kaggle", "databricks",
    "anaconda", "pip", "npm", "yarn", "pnpm", "maven", "gradle",
    "cmake", "make", "ninja", "bazel", "buck", "pants",
    "svn", "mercurial", "perforce", "tfs", "git", "github", "gitlab", "bitbucket",
    "bash", "zsh", "powershell", "cmd", "fish",
    "vim", "emacs", "vscode", "sublime", "atom", "notepad++",
    "intellij", "pycharm", "webstorm", "phpstorm", "rubymine", "goland",
    "eclipse", "netbeans", "visual studio", "xcode", "android studio",
}


def _detect_role_type(text: str) -> RoleType:
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for role_type, keywords in ROLE_TYPE_KEYWORDS.items():
        scores[role_type] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=lambda k: scores[k])
    return RoleType(best) if scores[best] > 0 else RoleType.GENERAL


def _extract_experience_range(text: str) -> tuple[float, float | None]:
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return float(groups[0]), float(groups[1])
            elif len(groups) == 1:
                return float(groups[0]), None
    return 0.0, None


def _is_likely_skill(token: str) -> bool:
    """Heuristic to determine if a token is a real skill."""
    token_lower = token.lower().strip()
    if not token_lower:
        return False
    if token_lower in SKILL_NOISE_WORDS:
        return False
    if len(token) < 2 or len(token) > 40:
        return False
    # Reject full sentences
    if token.count(" ") > 4:
        return False
    # Reject markdown headers
    if token.startswith("#") or token.startswith("* ") or token.startswith("- "):
        return False
    # Reject location-only lines
    location_words = {"mumbai", "pune", "bengaluru", "bangalore", "delhi", "hyderabad", "chennai", "kolkata", "noida", "gurgaon", "remote", "onsite", "hybrid", "india", "usa", "uk", "canada", "australia"}
    if token_lower in location_words:
        return False
    # Reject year-only strings
    if re.match(r"^\d{4}$", token):
        return False
    # Reject email/URL fragments
    if "@" in token or "http" in token_lower:
        return False
    return True


def _clean_skill_token(token: str) -> str | None:
    """Clean and validate a single skill token."""
    token = token.strip().strip("•-*·◦•\t#-–—")
    token = re.sub(r"\s+", " ", token)
    if not _is_likely_skill(token):
        return None
    return token


def _extract_skills_from_markdown(text: str) -> list[str]:
    """Extract skills from markdown bullet lists anywhere in the JD."""
    skills = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(("-", "*", "•", "·", "◦")):
            content = line.lstrip("- *•·◦\t").strip()
            # Split by common delimiters
            parts = re.split(r"[,|/\t;]", content)
            for part in parts:
                cleaned = _clean_skill_token(part)
                if cleaned and cleaned.lower() not in {s.lower() for s in skills}:
                    skills.append(cleaned)
    return skills


def _extract_skills_from_section(text: str, markers: list[str]) -> list[str]:
    """Extract skills from a dedicated section, stopping at the next major section."""
    lines = text.split("\n")
    in_section = False
    skills = []

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Detect section start
        if not in_section:
            if any(m in line_lower for m in markers):
                in_section = True
            continue

        # Stop at next major section header
        if any(stop in line_lower for stop in SECTION_STOP_HEADERS):
            # But make sure it's actually a header (short line)
            if len(line_stripped) < 80:
                in_section = False
                continue

        # Stop at another must-have/preferred marker that isn't ours
        if any(m in line_lower for m in MUST_HAVE_MARKERS + PREFERRED_MARKERS):
            if not any(m in line_lower for m in markers):
                if len(line_stripped) < 80:
                    in_section = False
                    continue

        # Extract tokens from this line
        tokens = re.split(r"[,•·\-\t|/;]", line_stripped)
        for token in tokens:
            cleaned = _clean_skill_token(token)
            if cleaned and cleaned.lower() not in {s.lower() for s in skills}:
                skills.append(cleaned)

    return skills[:30]


def _extract_bullet_skills(text: str) -> list[str]:
    """Extract all bullet items that look like skills."""
    skills = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(("•", "-", "*", "·", "◦")):
            content = line.lstrip("•-*·◦ ").strip()
            # If it's a single short item, keep it
            if 2 <= len(content) <= 40 and " " in content:
                # Check if it contains at least one known tech word or is short enough
                words = content.lower().split()
                if any(w in TECH_SKILL_KEYWORDS for w in words) or len(words) <= 3:
                    cleaned = _clean_skill_token(content)
                    if cleaned and cleaned.lower() not in {s.lower() for s in skills}:
                        skills.append(cleaned)
            else:
                # Split by delimiters
                parts = re.split(r"[,|/\t;]", content)
                for part in parts:
                    cleaned = _clean_skill_token(part)
                    if cleaned and cleaned.lower() not in {s.lower() for s in skills}:
                        skills.append(cleaned)
    return skills[:40]


def _extract_education_requirements(text: str) -> list[str]:
    # Use word-boundary safe keywords to avoid matching "be" inside other words
    edu_patterns = [
        r"\bbachelor", r"\bmaster", r"\bphd", r"\bb\.tech", r"\bm\.tech", r"\bmba",
        r"\bdegree", r"\bb\.sc", r"\bm\.sc", r"\bdiploma", r"\bbca\b", r"\bmca\b",
        r"\bb\.e\b", r"\bm\.e\b", r"\bbsc\b", r"\bbtec",
    ]
    compiled = [re.compile(p, re.IGNORECASE) for p in edu_patterns]
    results = []
    for line in text.split("\n"):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        if not line_lower:
            continue
        if not any(p.search(line_lower) for p in compiled):
            continue
        if len(line_stripped) > 100:
            continue
        if any(loc in line_lower for loc in ["mumbai", "pune", "bengaluru", "bangalore", "delhi", "hyderabad", "chennai", "remote", "onsite"]):
            continue
        if re.match(r"^\d{4}$", line_stripped):
            continue
        # Skip lines that are clearly skills/experience, not education
        if any(skip in line_lower for skip in ["experience", "framework", "api", "development", "years", "internship"]):
            continue
        results.append(line_stripped)
    return list(dict.fromkeys(results))[:5]


def _extract_certifications(text: str) -> list[str]:
    cert_keywords = ["certified", "certification", "aws", "pmp", "cissp", "cpa", "cfa", "comptia", "ccna", "ccnp", "google certified", "microsoft certified"]
    vendor_keywords = ["udemy", "coursera", "edx", "linkedin learning", "pluralsight", "google", "microsoft", "amazon", "oracle", "ibm", "salesforce"]
    results = []
    for line in text.split("\n"):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        if not line_stripped:
            continue
        if any(kw in line_lower for kw in cert_keywords + vendor_keywords):
            # Reject headers and very long lines
            if len(line_stripped) > 120:
                continue
            if line_stripped.lower() in ["certifications", "certificates", "credentials", "licenses"]:
                continue
            results.append(line_stripped)
    return list(dict.fromkeys(results))[:10]


def _extract_soft_skills(text: str) -> list[str]:
    import re
    text_lower = text.lower()
    found = []
    for skill in SOFT_SKILL_KEYWORDS:
        skill_lower = skill.lower()
        # Must appear with meaningful context, not just anywhere
        patterns = [
            rf"(?:strong|excellent|good|proven|demonstrated)\s+{re.escape(skill_lower)}",
            rf"{re.escape(skill_lower)}\s+skills?",
            rf"ability\s+to\s+{re.escape(skill_lower)}",
            rf"(?:require[sd]?|need[sd]?|must have|looking for)[^.\n]{{0,40}}{re.escape(skill_lower)}",
            rf"^[\s\-•*]*{re.escape(skill_lower)}[\s,]*$",
        ]
        if any(re.search(p, text_lower, re.MULTILINE) for p in patterns):
            found.append(skill)
    return found


def _extract_role_title(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title_patterns = [
        re.compile(r"(?:job title|position|role)[:\s]+(.+)", re.IGNORECASE),
        re.compile(r"(?:we are hiring|looking for|seeking)[:\s]+(?:a\s+)?(.+)", re.IGNORECASE),
        re.compile(r"(?:hiring|opening)[:\s]+(.+)", re.IGNORECASE),
    ]
    for pattern in title_patterns:
        for line in lines[:10]:
            match = pattern.search(line)
            if match:
                return match.group(1).strip()[:100]
    # Try first non-header line
    for line in lines[:3]:
        if 2 <= len(line.split()) <= 8 and len(line) < 80 and not line.startswith("#"):
            return line
    return "Unknown Role"


def parse_jd_rules(jd_text: str) -> dict:
    logger.info("Parsing JD with rule-based parser")

    must_have = _extract_skills_from_section(jd_text, MUST_HAVE_MARKERS)
    preferred = _extract_skills_from_section(jd_text, PREFERRED_MARKERS)
    bullet_skills = _extract_bullet_skills(jd_text)

    # Fallback: if no explicit must-have/preferred sections, use bullet skills
    if not must_have and not preferred:
        # Split: first half as must-have, second half as preferred
        split_point = max(1, len(bullet_skills) // 2)
        must_have = bullet_skills[:split_point]
        preferred = bullet_skills[split_point:]

    # If we have must-have but no preferred, put some bullets in preferred
    if must_have and not preferred and bullet_skills:
        preferred = [s for s in bullet_skills if s.lower() not in {m.lower() for m in must_have}][:15]

    # If we have preferred but no must-have, use bullets as must-have
    if preferred and not must_have and bullet_skills:
        must_have = [s for s in bullet_skills if s.lower() not in {p.lower() for p in preferred}][:15]

    # Final fallback: if still empty, extract any tech keywords found in the text
    if not must_have and not preferred:
        text_lower = jd_text.lower()
        found_tech = [t for t in TECH_SKILL_KEYWORDS if t in text_lower]
        must_have = found_tech[:10]
        preferred = found_tech[10:20]

    min_exp, max_exp = _extract_experience_range(jd_text)

    parsed = {
        "role_title": _extract_role_title(jd_text),
        "role_type": _detect_role_type(jd_text),
        "must_have_skills": list(dict.fromkeys(must_have)),
        "preferred_skills": list(dict.fromkeys(preferred)),
        "min_experience_years": min_exp,
        "max_experience_years": max_exp,
        "required_certifications": _extract_certifications(jd_text),
        "preferred_certifications": [],
        "education_requirements": _extract_education_requirements(jd_text),
        "soft_skills": _extract_soft_skills(jd_text),
        "responsibilities": [],
        "raw_text": jd_text,
    }

    logger.info(
        f"JD parsed: role='{parsed['role_title']}' type={parsed['role_type']} "
        f"must_have={len(parsed['must_have_skills'])} preferred={len(parsed['preferred_skills'])} "
        f"min_exp={min_exp} max_exp={max_exp}"
    )
    logger.debug(f"Must-have skills: {parsed['must_have_skills']}")
    logger.debug(f"Preferred skills: {parsed['preferred_skills']}")
    logger.debug(f"Education reqs: {parsed['education_requirements']}")
    logger.debug(f"Certifications: {parsed['required_certifications']}")

    return parsed

