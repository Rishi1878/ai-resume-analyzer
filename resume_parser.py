"""
resume_parser.py
----------------
Extracts structured entities from raw resume text using spaCy NER
and regex-based pattern matching.
"""

import re
import spacy
from dataclasses import dataclass, field
from typing import List, Optional

# Load spaCy model (en_core_web_sm must be installed)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load("en_core_web_sm")


# ── Skill taxonomy ──────────────────────────────────────────────────────────
SKILL_TAXONOMY = {
    "programming": [
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust",
        "kotlin", "swift", "r", "scala", "matlab", "bash", "shell", "perl",
    ],
    "ml_ai": [
        "machine learning", "deep learning", "nlp", "computer vision", "llm",
        "transformers", "bert", "gpt", "reinforcement learning", "neural network",
        "genai", "generative ai", "rag", "fine-tuning", "prompt engineering",
    ],
    "frameworks": [
        "tensorflow", "pytorch", "keras", "scikit-learn", "hugging face",
        "spacy", "nltk", "opencv", "fastapi", "flask", "django", "spring",
        "react", "angular", "vue", "node.js", "express",
    ],
    "data": [
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "spark", "hadoop", "kafka", "airflow", "dbt", "pandas", "numpy",
        "tableau", "power bi", "looker",
    ],
    "cloud_devops": [
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
        "jenkins", "github actions", "linux", "git",
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "project management", "agile", "scrum",
    ],
}

FLAT_SKILLS = {skill: category for cat, skills in SKILL_TAXONOMY.items() for skill in skills}

DEGREE_PATTERNS = [
    r"\b(b\.?tech|b\.?e\.?|bachelor[s]? of (technology|engineering|science|arts|commerce))\b",
    r"\b(m\.?tech|m\.?e\.?|master[s]? of (technology|engineering|science|arts|business administration))\b",
    r"\b(ph\.?d|doctor of philosophy)\b",
    r"\b(mba|bba|bca|mca|b\.?sc\.?|m\.?sc\.?)\b",
]

EMAIL_RE   = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE   = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)
GITHUB_RE  = re.compile(r"github\.com/[\w\-]+", re.IGNORECASE)
YEAR_RE    = re.compile(r"\b(19|20)\d{2}\b")
GPA_RE     = re.compile(r"\b(\d\.\d{1,2})\s*/?\.\s*(4\.0|10(\.0)?|100)?\b")


@dataclass
class ParsedResume:
    raw_text: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    skill_categories: dict = field(default_factory=dict)
    education: List[str] = field(default_factory=list)
    experience_years: Optional[int] = None
    companies: List[str] = field(default_factory=list)
    job_titles: List[str] = field(default_factory=list)
    gpa: Optional[str] = None
    years_mentioned: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "linkedin": self.linkedin,
            "github": self.github,
            "skills": self.skills,
            "skill_categories": self.skill_categories,
            "education": self.education,
            "experience_years": self.experience_years,
            "companies": self.companies,
            "job_titles": self.job_titles,
            "gpa": self.gpa,
        }


class ResumeParser:
    """Parses resume text into a structured ParsedResume object."""

    def parse(self, text: str) -> ParsedResume:
        result = ParsedResume(raw_text=text)
        text_lower = text.lower()
        doc = nlp(text)

        result.email    = self._extract_email(text)
        result.phone    = self._extract_phone(text)
        result.linkedin = self._extract_pattern(text, LINKEDIN_RE)
        result.github   = self._extract_pattern(text, GITHUB_RE)
        result.name     = self._extract_name(doc)
        result.skills, result.skill_categories = self._extract_skills(text_lower)
        result.education = self._extract_education(text)
        result.companies, result.job_titles = self._extract_work_experience(doc)
        result.experience_years = self._estimate_experience(text)
        result.gpa = self._extract_gpa(text)
        result.years_mentioned = YEAR_RE.findall(text)

        return result

    # ── private helpers ──────────────────────────────────────────────────────

    def _extract_email(self, text: str) -> Optional[str]:
        m = EMAIL_RE.search(text)
        return m.group(0) if m else None

    def _extract_phone(self, text: str) -> Optional[str]:
        m = PHONE_RE.search(text)
        return m.group(0).strip() if m else None

    def _extract_pattern(self, text: str, pattern) -> Optional[str]:
        m = pattern.search(text)
        return m.group(0) if m else None

    def _extract_name(self, doc) -> Optional[str]:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        # Fallback: first non-empty line often is the name
        for line in doc.text.splitlines():
            line = line.strip()
            if line and len(line.split()) <= 4 and not EMAIL_RE.search(line):
                return line
        return None

    def _extract_skills(self, text_lower: str):
        found_skills = []
        found_categories = {}
        for skill, category in FLAT_SKILLS.items():
            if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
                found_skills.append(skill)
                found_categories.setdefault(category, []).append(skill)
        return found_skills, found_categories

    def _extract_education(self, text: str) -> List[str]:
        results = []
        for pattern in DEGREE_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                results.append(m.group(0).strip())
        return list(set(results))

    def _extract_work_experience(self, doc):
        companies, titles = [], []
        for ent in doc.ents:
            if ent.label_ == "ORG":
                companies.append(ent.text)
        # Simple title heuristics
        title_keywords = [
            "engineer", "developer", "scientist", "analyst", "manager",
            "intern", "lead", "architect", "consultant", "researcher",
        ]
        for sent in doc.sents:
            s = sent.text.lower()
            if any(kw in s for kw in title_keywords):
                titles.append(sent.text.strip()[:80])
        return list(set(companies)), titles[:5]

    def _estimate_experience(self, text: str) -> Optional[int]:
        # Try explicit "X years of experience"
        m = re.search(r"(\d+)\+?\s+years?\s+of\s+(professional\s+)?experience", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        # Estimate from year range mentions
        years = sorted(set(int(y) for y in YEAR_RE.findall(text)))
        if len(years) >= 2:
            return years[-1] - years[0]
        return None

    def _extract_gpa(self, text: str) -> Optional[str]:
        m = GPA_RE.search(text)
        return m.group(0) if m else None
