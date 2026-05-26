"""
job_matcher.py
--------------
Predicts the best-matching job roles for a parsed resume using:
  1. Cosine similarity over MiniLM embeddings
  2. Feature-weighted ATS-style scoring (skills, experience, education)

Final score = 0.6 * semantic_similarity + 0.4 * ats_score
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np

from resume_parser import ParsedResume
from embedder import ResumeEmbedder


# ── Job role catalogue ───────────────────────────────────────────────────────
# Each role has: title, description (used for embedding), required_skills,
# preferred_skills, min_experience (years).
JOB_CATALOGUE: List[Dict] = [
    {
        "title": "Machine Learning Engineer",
        "description": (
            "Design and deploy ML models into production. "
            "Work with Python, PyTorch/TensorFlow, MLOps pipelines, "
            "feature engineering, model monitoring, and REST APIs."
        ),
        "required_skills": ["python", "machine learning", "pytorch", "tensorflow", "scikit-learn"],
        "preferred_skills": ["docker", "kubernetes", "mlflow", "aws", "spark"],
        "min_experience": 2,
    },
    {
        "title": "NLP / LLM Engineer",
        "description": (
            "Build NLP pipelines and LLM-powered applications. "
            "Fine-tune transformers, work with Hugging Face, implement RAG, "
            "prompt engineering, semantic search, and vector databases."
        ),
        "required_skills": ["python", "nlp", "transformers", "hugging face", "spacy"],
        "preferred_skills": ["llm", "rag", "fine-tuning", "prompt engineering", "pytorch"],
        "min_experience": 1,
    },
    {
        "title": "Data Scientist",
        "description": (
            "Analyse large datasets, build predictive models, create dashboards. "
            "Strong in statistics, pandas, SQL, matplotlib, scikit-learn, "
            "A/B testing, and storytelling with data."
        ),
        "required_skills": ["python", "sql", "pandas", "scikit-learn", "machine learning"],
        "preferred_skills": ["tableau", "power bi", "r", "spark", "deep learning"],
        "min_experience": 1,
    },
    {
        "title": "Data Engineer",
        "description": (
            "Build and maintain scalable data pipelines, ETL processes, "
            "data warehouses. Work with Spark, Kafka, Airflow, SQL, "
            "cloud data platforms (AWS/GCP/Azure), and dbt."
        ),
        "required_skills": ["sql", "python", "spark", "kafka", "airflow"],
        "preferred_skills": ["dbt", "aws", "gcp", "docker", "scala"],
        "min_experience": 2,
    },
    {
        "title": "AI Research Scientist",
        "description": (
            "Conduct research on novel ML/AI methods. Publish papers, "
            "implement state-of-the-art models, work with transformers, "
            "reinforcement learning, computer vision, and NLP."
        ),
        "required_skills": ["python", "pytorch", "deep learning", "machine learning", "nlp"],
        "preferred_skills": ["reinforcement learning", "computer vision", "transformers", "r"],
        "min_experience": 3,
    },
    {
        "title": "Backend Software Engineer",
        "description": (
            "Design and build scalable REST/gRPC services. "
            "Strong in Python/Java/Go, databases (SQL + NoSQL), "
            "microservices, Docker, Kubernetes, and cloud deployment."
        ),
        "required_skills": ["python", "sql", "docker", "git", "linux"],
        "preferred_skills": ["kubernetes", "aws", "java", "go", "redis"],
        "min_experience": 2,
    },
    {
        "title": "Full-Stack Developer",
        "description": (
            "Build end-to-end web applications with React/Angular frontend "
            "and Python/Node.js backend. Work with REST APIs, databases, "
            "CI/CD pipelines, and cloud infrastructure."
        ),
        "required_skills": ["javascript", "python", "sql", "react", "git"],
        "preferred_skills": ["typescript", "node.js", "docker", "aws", "postgresql"],
        "min_experience": 1,
    },
    {
        "title": "DevOps / MLOps Engineer",
        "description": (
            "Automate infrastructure, manage CI/CD pipelines, orchestrate containers. "
            "Expert in Docker, Kubernetes, Terraform, AWS/GCP, and Jenkins."
        ),
        "required_skills": ["docker", "kubernetes", "linux", "git", "aws"],
        "preferred_skills": ["terraform", "ci/cd", "python", "ansible", "gcp"],
        "min_experience": 2,
    },
]

EDUCATION_WEIGHTS = {
    "ph.d": 1.0, "phd": 1.0,
    "m.tech": 0.85, "mtech": 0.85, "master": 0.85, "mba": 0.80,
    "b.tech": 0.70, "btech": 0.70, "bachelor": 0.70,
    "bca": 0.60, "mca": 0.70, "b.sc": 0.60,
}


@dataclass
class MatchResult:
    rank: int
    title: str
    final_score: float
    semantic_score: float
    ats_score: float
    matched_required: List[str]
    matched_preferred: List[str]
    missing_required: List[str]
    experience_ok: bool
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "title": self.title,
            "final_score": round(self.final_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "ats_score": round(self.ats_score, 4),
            "matched_required": self.matched_required,
            "matched_preferred": self.matched_preferred,
            "missing_required": self.missing_required,
            "experience_ok": self.experience_ok,
            "recommendation": self.recommendation,
        }


class JobMatcher:
    """
    Matches a parsed resume to job roles using hybrid scoring.
    """

    SEMANTIC_WEIGHT = 0.60
    ATS_WEIGHT      = 0.40

    def __init__(self, embedder: Optional[ResumeEmbedder] = None):
        self.embedder = embedder or ResumeEmbedder()
        # Pre-embed all job descriptions once
        print("[JobMatcher] Pre-embedding job catalogue...")
        self._job_embeddings: Dict[str, np.ndarray] = {
            job["title"]: self.embedder.embed_job_description(job["description"])
            for job in JOB_CATALOGUE
        }
        print(f"[JobMatcher] {len(JOB_CATALOGUE)} roles ready.")

    # ── public API ────────────────────────────────────────────────────────────

    def match(self, resume: ParsedResume, top_k: int = 5) -> List[MatchResult]:
        """Return top_k best-matching roles for a given resume."""
        resume_vec = self.embedder.embed_resume(resume)
        results = []

        for job in JOB_CATALOGUE:
            semantic = float(np.dot(resume_vec, self._job_embeddings[job["title"]]))
            ats, m_req, m_pref, miss_req = self._ats_score(resume, job)
            exp_ok = self._check_experience(resume, job)

            final = (self.SEMANTIC_WEIGHT * semantic) + (self.ATS_WEIGHT * ats)

            # Slight penalty if experience requirement not met
            if not exp_ok:
                final *= 0.90

            results.append(MatchResult(
                rank=0,
                title=job["title"],
                final_score=final,
                semantic_score=semantic,
                ats_score=ats,
                matched_required=m_req,
                matched_preferred=m_pref,
                missing_required=miss_req,
                experience_ok=exp_ok,
            ))

        # Sort & rank
        results.sort(key=lambda r: r.final_score, reverse=True)
        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1
            r.recommendation = self._generate_recommendation(r)

        return results[:top_k]

    # ── private helpers ───────────────────────────────────────────────────────

    def _ats_score(self, resume: ParsedResume, job: Dict):
        """
        ATS-style scoring:
          - Required skills: 0–50 pts
          - Preferred skills: 0–30 pts
          - Education: 0–20 pts
        Returns normalised score [0, 1].
        """
        skills_lower = [s.lower() for s in resume.skills]

        req  = job["required_skills"]
        pref = job["preferred_skills"]

        matched_req  = [s for s in req  if s in skills_lower]
        matched_pref = [s for s in pref if s in skills_lower]
        missing_req  = [s for s in req  if s not in skills_lower]

        req_score  = (len(matched_req)  / max(len(req),  1)) * 50
        pref_score = (len(matched_pref) / max(len(pref), 1)) * 30
        edu_score  = self._education_score(resume) * 20

        total = (req_score + pref_score + edu_score) / 100
        return total, matched_req, matched_pref, missing_req

    def _education_score(self, resume: ParsedResume) -> float:
        best = 0.0
        for edu_str in resume.education:
            edu_lower = edu_str.lower()
            for kw, weight in EDUCATION_WEIGHTS.items():
                if kw in edu_lower:
                    best = max(best, weight)
        return best if best > 0 else 0.4  # default: assume some edu

    def _check_experience(self, resume: ParsedResume, job: Dict) -> bool:
        exp = resume.experience_years
        if exp is None:
            return True  # can't determine — give benefit of doubt
        return exp >= job["min_experience"]

    def _generate_recommendation(self, result: MatchResult) -> str:
        score_pct = int(result.final_score * 100)
        if score_pct >= 70:
            fit = "Strong fit"
        elif score_pct >= 50:
            fit = "Good fit"
        elif score_pct >= 35:
            fit = "Partial fit"
        else:
            fit = "Weak fit"

        parts = [f"{fit} ({score_pct}% match)."]
        if result.missing_required:
            parts.append(f"Missing key skills: {', '.join(result.missing_required[:3])}.")
        if not result.experience_ok:
            parts.append("May lack required experience.")
        if result.matched_required:
            parts.append(f"Strengths: {', '.join(result.matched_required[:3])}.")
        return " ".join(parts)


def load_custom_jd(jd_text: str, title: str = "Custom Role") -> Dict:
    """Helper to add a one-off job description to a match session."""
    return {
        "title": title,
        "description": jd_text,
        "required_skills": [],
        "preferred_skills": [],
        "min_experience": 0,
    }
