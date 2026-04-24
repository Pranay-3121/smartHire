import re
import hashlib
from pathlib import Path
from typing import Optional
from backend.core.logging import get_logger
from backend.core.constants import ParseStatus, KEYWORD_STUFFING_THRESHOLD
from backend.tools.ocr_fallback import extract_text_via_ocr, is_scanned_pdf

logger = get_logger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
URL_RE = re.compile(r"https?://[^\s]+")

SKILL_KEYWORDS = {
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
    "keras", "xgboost", "lightgbm", "catboost", "spacy", "nltk",
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
    "oracle erp", "netsuite", "workday", "peoplesoft",
    "quickbooks", "xero", "freshbooks", "zoho",
    "google analytics", "google ads", "facebook ads", "seo", "sem",
    "contentful", "prismic", "sanity", "strapi", "directus",
    "sketch", "adobe xd", "invision", "framer", "proto.io",
    "illustrator", "indesign", "after effects", "premiere",
    "lightroom", "audition", "animate", "dreamweaver",
    "canva", "crello", "picmonkey", "snappa",
    "rstudio", "jupyter", "colab", "kaggle",
    "anaconda", "pip", "npm", "yarn", "pnpm", "maven", "gradle",
    "cmake", "make", "ninja", "bazel", "buck", "pants",
    "svn", "mercurial", "perforce", "tfs", "github", "gitlab", "bitbucket",
    "bash", "zsh", "powershell", "cmd", "fish",
    "vim", "emacs", "vscode", "sublime", "atom", "notepad++",
    "intellij", "pycharm", "webstorm", "phpstorm", "rubymine", "goland",
    "eclipse", "netbeans", "visual studio", "xcode", "android studio",
}

EDUCATION_KEYWORDS = ["bachelor", "master", "phd", "b.tech", "m.tech", "b.e", "m.e", "mba",
                      "b.sc", "m.sc", "associate", "diploma", "degree", "university", "college", "institute",
                      "bca", "mca", "be", "me", "b.voc", "m.voc", "hsc", "ssc", "secondary", "higher secondary"]

CERT_KEYWORDS = ["certified", "certification", "certificate", "aws certified", "pmp", "cissp",
                 "cpa", "cfa", "google certified", "microsoft certified", "comptia", "ccna", "ccnp",
                 "udemy", "coursera", "edx", "linkedin learning", "pluralsight"]

SECTION_HEADERS = {
    "experience": ["experience", "work history", "employment", "professional experience", "career", "work experience"],
    "education": ["education", "academic", "qualification", "degree", "educational background"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "expertise", "proficiencies"],
    "projects": ["projects", "personal projects", "key projects", "portfolio", "project experience"],
    "certifications": ["certifications", "certificates", "credentials", "licenses", "accreditations"],
    "summary": ["summary", "profile", "objective", "about me", "overview", "professional summary"],
    "languages": ["languages", "language proficiency", "linguistic skills"],
    "activities": ["activities", "extracurricular", "achievements", "awards", "honors", "publications"],
    "interests": ["interests", "hobbies", "personal interests"],
}

NOISE_WORDS = {
    "proficient", "strong", "expertise", "experience", "skilled", "familiar",
    "knowledge", "good", "excellent", "solid", "understanding", "ability",
    "and", "or", "with", "in", "of", "to", "for", "the", "a", "an",
    "years", "year", "plus", "including", "such", "as", "like", "etc",
    "working", "using", "known", "languages", "technical", "tools",
}


def _extract_raw_text_pdf(file_path: str) -> tuple[str, ParseStatus]:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        text = "\n".join(text_parts).strip()
        if len(text) > 100:
            return text, ParseStatus.SUCCESS
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    try:
        import fitz
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc).strip()
        doc.close()
        if len(text) > 100:
            return text, ParseStatus.SUCCESS
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}")

    if is_scanned_pdf(file_path):
        logger.info(f"Falling back to OCR for {file_path}")
        try:
            text = extract_text_via_ocr(file_path)
            return text, ParseStatus.OCR_FALLBACK
        except Exception as e:
            logger.error(f"OCR failed: {e}")

    return "", ParseStatus.FAILED


def _extract_raw_text_docx(file_path: str) -> tuple[str, ParseStatus]:
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text, ParseStatus.SUCCESS
    except Exception as e:
        logger.error(f"DOCX parsing failed: {e}")
        return "", ParseStatus.FAILED


def _extract_raw_text_txt(file_path: str) -> tuple[str, ParseStatus]:
    try:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                text = Path(file_path).read_text(encoding=encoding)
                return text, ParseStatus.SUCCESS
            except UnicodeDecodeError:
                continue
        return "", ParseStatus.FAILED
    except Exception as e:
        logger.error(f"TXT parsing failed: {e}")
        return "", ParseStatus.FAILED


def extract_raw_text(file_path: str) -> tuple[str, ParseStatus]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _extract_raw_text_pdf(file_path)
    elif suffix == ".docx":
        return _extract_raw_text_docx(file_path)
    elif suffix == ".txt":
        return _extract_raw_text_txt(file_path)
    else:
        return "", ParseStatus.FAILED


def _extract_name(lines: list[str]) -> Optional[str]:
    for line in lines[:5]:
        line = line.strip()
        if 2 <= len(line.split()) <= 5 and not any(c in line for c in ["@", ":", "/", "|", "\\", "http"]):
            if re.match(r"^[A-Za-z\s.\-']+$", line):
                return line
    return None


def _extract_email(text: str) -> Optional[str]:
    matches = EMAIL_RE.findall(text)
    return matches[0] if matches else None


def _extract_phone(text: str) -> Optional[str]:
    matches = PHONE_RE.findall(text)
    for m in matches:
        digits = re.sub(r"\D", "", m)
        if 7 <= len(digits) <= 15:
            return m.strip()
    return None


def _is_noise_token(token: str) -> bool:
    t = token.lower().strip()
    if t in NOISE_WORDS:
        return True
    if len(t) > 40:
        return True
    if len(t) < 2:
        return True
    words = t.split()
    # Allow known multi-word skills (e.g. "machine learning", "rest api")
    if len(words) > 4:
        return True
    if re.search(r"[;:!?\"]", t):
        return True
    return False


def _clean_skill(token: str) -> Optional[str]:
    token = token.strip().strip("•-*·◦–—\t ").strip()
    if _is_noise_token(token):
        return None
    # Remove trailing punctuation artifacts
    token = re.sub(r"[.,;]+$", "", token)
    if not token:
        return None
    return token


def _extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)

    # Also extract from explicit skills section
    skills_section = _extract_section(text, "skills")
    if skills_section:
        for line in skills_section.split("\n"):
            for token in re.split(r"[,|•·\t/]+", line):
                cleaned = _clean_skill(token)
                if cleaned and cleaned not in found:
                    found.append(cleaned)

    return list(dict.fromkeys(found))


def _extract_section(text: str, section_type: str) -> str:
    headers = SECTION_HEADERS.get(section_type, [])
    lines = text.split("\n")
    start_idx = -1
    end_idx = len(lines)

    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if start_idx == -1:
            for header in headers:
                if header in line_lower and len(line_lower) < 60:
                    start_idx = i + 1
                    break
        else:
            found_end = False
            for other_type, other_headers in SECTION_HEADERS.items():
                if other_type == section_type:
                    continue
                for header in other_headers:
                    if header in line_lower and len(line_lower) < 60:
                        end_idx = i
                        found_end = True
                        break
                if found_end:
                    break
            if found_end:
                break

    if start_idx == -1:
        return ""
    return "\n".join(lines[start_idx:end_idx]).strip()


def _extract_experience_years(text: str, work_exp: list) -> float:
    if work_exp:
        total = sum(w.get("duration_months", 0) or 0 for w in work_exp)
        if total > 0:
            return round(total / 12, 1)

    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+experience",
        r"(\d+)\+?\s*years?\s+experience",
        r"experience\s+of\s+(\d+)\+?\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1))
    return 0.0


def _parse_duration_months(start: Optional[str], end: Optional[str]) -> int:
    if not start:
        return 0
    import datetime
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

    def parse_date(s: str):
        import datetime
        s = s.lower().strip()
        if s in ("present", "current", "now", "till date"):
            return datetime.date.today()
        for abbr, num in month_map.items():
            if abbr in s:
                year_match = re.search(r"\d{4}", s)
                year = int(year_match.group()) if year_match else datetime.date.today().year
                return datetime.date(year, num, 1)
        year_match = re.search(r"\d{4}", s)
        if year_match:
            return datetime.date(int(year_match.group()), 1, 1)
        return None

    start_date = parse_date(start)
    end_date = parse_date(end or "present")
    if start_date and end_date and end_date >= start_date:
        delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        return max(0, delta)
    return 0


def _is_likely_education_block(block: str) -> bool:
    bl = block.lower()
    return any(kw in bl for kw in EDUCATION_KEYWORDS)


def _is_likely_cert_block(block: str) -> bool:
    bl = block.lower()
    return any(kw in bl for kw in CERT_KEYWORDS + ["udemy", "coursera", "edx", "course", "training"])


def _extract_work_experience(text: str) -> list[dict]:
    exp_section = _extract_section(text, "experience")
    if not exp_section:
        return []

    experiences = []
    date_pattern = re.compile(
        r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{4})"
        r"\s*[-–—to]+\s*"
        r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{4}|present|current|now)",
        re.IGNORECASE,
    )

    blocks = re.split(r"\n{2,}", exp_section)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue

        # Skip blocks that are clearly education or certifications
        if _is_likely_education_block(block):
            continue
        if _is_likely_cert_block(block):
            continue

        date_match = date_pattern.search(block)
        start_date = date_match.group(1) if date_match else None
        end_date = date_match.group(2) if date_match else None
        duration = _parse_duration_months(start_date, end_date)

        # Require a date match; otherwise skip (reduces false positives)
        if not date_match:
            continue

        lines = [l.strip() for l in block.split("\n") if l.strip()]
        title = lines[0] if lines else "Unknown"
        company = lines[1] if len(lines) > 1 else "Unknown"
        description = " ".join(lines[2:]) if len(lines) > 2 else ""

        experiences.append({
            "company": company[:100],
            "title": title[:100],
            "start_date": start_date,
            "end_date": end_date,
            "duration_months": duration,
            "description": description[:500],
            "is_current": end_date.lower() in ("present", "current", "now") if end_date else False,
        })

    return experiences


def _extract_education(text: str) -> list[dict]:
    edu_section = _extract_section(text, "education")
    if not edu_section:
        return []

    results = []
    blocks = re.split(r"\n{2,}", edu_section) or [edu_section]
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        block_lower = block.lower()
        if not any(kw in block_lower for kw in EDUCATION_KEYWORDS):
            continue

        # Skip blocks that look like certifications or projects
        if _is_likely_cert_block(block) and not any(kw in block_lower for kw in ["bachelor", "master", "b.tech", "b.e", "b.sc", "bca", "be"]):
            continue

        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        year_match = re.search(r"\b(19|20)\d{2}\b", block)
        gpa_match = re.search(r"(?:gpa|cgpa|grade|sgpa)[:\s]+(\d+\.?\d*)", block_lower)

        # Heuristic: if first line contains degree keyword, it's likely the degree
        first_has_degree = any(kw in lines[0].lower() for kw in EDUCATION_KEYWORDS)
        if first_has_degree:
            degree = lines[0]
            institution = lines[1] if len(lines) > 1 else "Unknown"
        else:
            degree = lines[0]
            institution = lines[1] if len(lines) > 1 else "Unknown"
            # Try to swap if second line looks more like a degree
            if len(lines) > 1 and any(kw in lines[1].lower() for kw in EDUCATION_KEYWORDS):
                degree, institution = institution, degree

        results.append({
            "institution": institution[:100],
            "degree": degree[:100],
            "field_of_study": None,
            "graduation_year": int(year_match.group()) if year_match else None,
            "gpa": float(gpa_match.group(1)) if gpa_match else None,
        })
    return results


def _extract_certifications(text: str) -> list[str]:
    cert_section = _extract_section(text, "certifications")
    certs = []
    search_text = cert_section if cert_section else text
    for line in search_text.split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in CERT_KEYWORDS) and 5 < len(line) < 150:
            # Skip lines that are section headers or activities
            line_lower = line.lower()
            if any(hdr in line_lower for hdr in ["activities", "achievements", "projects", "education", "experience"]):
                continue
            certs.append(line)
    return list(dict.fromkeys(certs))[:20]


def _extract_projects(text: str) -> list[dict]:
    proj_section = _extract_section(text, "projects")
    if not proj_section:
        return []

    projects = []
    blocks = re.split(r"\n{2,}", proj_section)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue

        lines = [l.strip() for l in block.split("\n") if l.strip()]
        techs = [s for s in SKILL_KEYWORDS if s in block.lower()]
        url_match = URL_RE.search(block)

        # Require at least some tech keywords or a URL to consider it a project
        if not techs and not url_match and not any(kw in block.lower() for kw in ["system", "application", "app", "platform", "website", "tool", "framework"]):
            continue

        projects.append({
            "name": lines[0][:100] if lines else "Unnamed Project",
            "description": " ".join(lines[1:])[:500] if len(lines) > 1 else block[:500],
            "technologies": techs[:10],
            "url": url_match.group() if url_match else None,
        })
    return projects[:15]


def _detect_warnings(text: str, skills: list[str], work_exp: list[dict]) -> list[str]:
    warnings = []

    if len(skills) > KEYWORD_STUFFING_THRESHOLD:
        warnings.append(f"Possible keyword stuffing: {len(skills)} skills listed")

    if len(work_exp) >= 4:
        short_stints = [w for w in work_exp if (w.get("duration_months") or 0) < 12]
        if len(short_stints) >= 3:
            warnings.append("Job hopping detected: multiple short-tenure positions")

    if not _extract_email(text):
        warnings.append("No email address found")

    if not any(kw in text.lower() for kw in EDUCATION_KEYWORDS):
        warnings.append("No education section detected")

    return warnings


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_resume(file_path: str, candidate_id: str) -> dict:
    path = Path(file_path)
    logger.info(f"Parsing resume: {path.name}")

    raw_text, status = extract_raw_text(file_path)

    if not raw_text or status == ParseStatus.FAILED:
        return {
            "candidate_id": candidate_id,
            "file_path": file_path,
            "file_name": path.name,
            "parse_status": ParseStatus.FAILED,
            "parse_confidence": 0.0,
            "warning_flags": ["Failed to extract text from file"],
            "raw_text": "",
        }

    lines = [l for l in raw_text.split("\n") if l.strip()]
    work_exp = _extract_work_experience(raw_text)
    skills = _extract_skills(raw_text)
    education = _extract_education(raw_text)
    certifications = _extract_certifications(raw_text)
    projects = _extract_projects(raw_text)
    warnings = _detect_warnings(raw_text, skills, work_exp)

    filled_fields = sum([
        bool(_extract_name(lines)),
        bool(_extract_email(raw_text)),
        bool(skills),
        bool(work_exp),
        bool(education),
    ])
    confidence = round(filled_fields / 5.0, 2)

    if confidence < 0.6:
        status = ParseStatus.PARTIAL

    result = {
        "candidate_id": candidate_id,
        "file_path": file_path,
        "file_name": path.name,
        "name": _extract_name(lines),
        "email": _extract_email(raw_text),
        "phone": _extract_phone(raw_text),
        "skills": skills,
        "work_experience": work_exp,
        "total_experience_years": _extract_experience_years(raw_text, work_exp),
        "companies": list({w["company"] for w in work_exp if w.get("company")}),
        "projects": projects,
        "education": education,
        "certifications": certifications,
        "parse_status": status,
        "parse_confidence": confidence,
        "warning_flags": warnings,
        "raw_text": raw_text[:5000],
        "content_hash": compute_content_hash(raw_text),
    }

    logger.info(
        f"[PARSE:resume] id={candidate_id} name={result['name']} "
        f"skills={len(skills)} exp_years={result['total_experience_years']} "
        f"projects={len(projects)} edu={len(education)} certs={len(certifications)} "
        f"confidence={confidence} status={status}"
    )

    return result
