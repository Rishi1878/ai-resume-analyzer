"""
main.py
-------
CLI entry point for the AI Resume Intelligence System.

Usage:
    python main.py --resume path/to/resume.txt
    python main.py --resume path/to/resume.txt --db --db-password secret
    python main.py --analytics --db --db-password secret
    python main.py --demo
"""

import argparse
import json
import sys
from pathlib import Path

from resume_parser import ResumeParser
from embedder import ResumeEmbedder
from job_matcher import JobMatcher
from database import ResumeDatabase

# ── Colours (ANSI) ────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
BLUE   = "\033[94m"
DIM    = "\033[2m"

DEMO_RESUME = """
Jane Doe
jane.doe@email.com  |  +91-9876543210  |  linkedin.com/in/janedoe  |  github.com/janedoe

SUMMARY
Machine learning engineer with 3 years of experience building NLP and computer vision systems.
Passionate about LLMs, RAG pipelines, and deploying models to production.

SKILLS
Python, PyTorch, TensorFlow, scikit-learn, Hugging Face Transformers, spaCy, NLTK
SQL, MySQL, PostgreSQL, MongoDB, Redis
Docker, Kubernetes, AWS (S3, EC2, SageMaker), GitHub Actions, Linux
FastAPI, Flask, REST APIs, Git

EXPERIENCE
Senior ML Engineer | TechCorp AI  (2022 – Present)
- Fine-tuned BERT-based models for text classification, achieving 94% F1 on customer intent dataset.
- Built RAG pipeline using LangChain + Pinecone for internal knowledge base Q&A.
- Deployed models via FastAPI on AWS ECS with CI/CD via GitHub Actions.

ML Engineer | DataWave (2021 – 2022)
- Developed NLP pipeline for resume screening using spaCy and sentence-transformers (MiniLM).
- Implemented cosine-similarity-based job role matching engine.
- Migrated data pipelines to Apache Airflow; reduced ETL latency by 40%.

EDUCATION
B.Tech in Computer Science — Indian Institute of Technology, 2021  |  GPA: 8.9/10

PROJECTS
- AI Resume Intelligence System: End-to-end NLP pipeline with MiniLM embeddings, ATS scoring,
  MySQL analytics, Python · spaCy · Transformers · MySQL
"""


def print_banner():
    print(f"""
{CYAN}{BOLD}
╔═══════════════════════════════════════════════════════╗
║       AI RESUME INTELLIGENCE SYSTEM  v1.0             ║
║       NLP · Transformers · MiniLM · MySQL             ║
╚═══════════════════════════════════════════════════════╝
{RESET}""")


def print_section(title: str):
    print(f"\n{BOLD}{BLUE}{'─'*54}")
    print(f"  {title}")
    print(f"{'─'*54}{RESET}")


def print_parsed_resume(parsed):
    print_section("PARSED RESUME")
    print(f"  {BOLD}Name:{RESET}        {parsed.name or 'N/A'}")
    print(f"  {BOLD}Email:{RESET}       {parsed.email or 'N/A'}")
    print(f"  {BOLD}Phone:{RESET}       {parsed.phone or 'N/A'}")
    print(f"  {BOLD}LinkedIn:{RESET}    {parsed.linkedin or 'N/A'}")
    print(f"  {BOLD}GitHub:{RESET}      {parsed.github or 'N/A'}")
    print(f"  {BOLD}Experience:{RESET}  {parsed.experience_years or '?'} years")
    print(f"  {BOLD}Education:{RESET}   {', '.join(parsed.education) or 'N/A'}")
    print(f"  {BOLD}GPA:{RESET}         {parsed.gpa or 'N/A'}")
    print(f"\n  {BOLD}Skills by category:{RESET}")
    for cat, skills in parsed.skill_categories.items():
        skill_str = ", ".join(skills)
        print(f"    {CYAN}{cat:<16}{RESET} {skill_str}")
    if parsed.companies:
        print(f"\n  {BOLD}Companies:{RESET}   {', '.join(parsed.companies[:5])}")


def print_match_results(results):
    print_section("JOB ROLE PREDICTIONS")
    for r in results:
        bar_len = int(r.final_score * 30)
        bar = f"{GREEN}{'█' * bar_len}{DIM}{'░' * (30 - bar_len)}{RESET}"
        score_str = f"{r.final_score*100:5.1f}%"
        fit_colour = GREEN if r.final_score >= 0.70 else (YELLOW if r.final_score >= 0.50 else RED)
        print(f"\n  {BOLD}#{r.rank}  {fit_colour}{r.title}{RESET}")
        print(f"      Score: {bar} {BOLD}{score_str}{RESET}")
        print(f"      Semantic: {r.semantic_score*100:.1f}%   ATS: {r.ats_score*100:.1f}%   "
              f"Exp OK: {'✓' if r.experience_ok else '✗'}")
        if r.matched_required:
            print(f"      {GREEN}✓ Required:{RESET} {', '.join(r.matched_required)}")
        if r.missing_required:
            print(f"      {RED}✗ Missing: {RESET} {', '.join(r.missing_required)}")
        if r.matched_preferred:
            print(f"      {CYAN}+ Preferred:{RESET} {', '.join(r.matched_preferred[:4])}")
        print(f"      {DIM}{r.recommendation}{RESET}")


def print_analytics(db: ResumeDatabase):
    print_section("RECRUITER ANALYTICS")

    candidates = db.get_all_candidates()
    print(f"\n  {BOLD}Total resumes stored:{RESET} {len(candidates)}")

    top_skills = db.get_top_skills(10)
    if top_skills:
        print(f"\n  {BOLD}Top Skills:{RESET}")
        for s in top_skills:
            bar = "█" * min(s["count"], 20)
            print(f"    {CYAN}{s['skill']:<25}{RESET} {bar} {s['count']}")

    role_demand = db.get_role_demand()
    if role_demand:
        print(f"\n  {BOLD}Most Matched Roles:{RESET}")
        for r in role_demand:
            print(f"    {YELLOW}{r['job_title']:<35}{RESET} "
                  f"{r['candidate_count']} candidates  "
                  f"avg score {r['avg_score']*100:.1f}%")

    exp_dist = db.get_experience_distribution()
    if exp_dist:
        print(f"\n  {BOLD}Experience Distribution:{RESET}")
        for row in exp_dist:
            bar = "█" * min(row["count"], 20)
            print(f"    {row['experience_years']:>3} yrs  {bar} {row['count']}")


def run_pipeline(
    resume_text: str,
    use_db: bool = False,
    db_config: dict = None,
    top_k: int = 5,
) -> dict:
    """
    Full pipeline: parse → embed → match → (optionally) persist.
    Returns a dict with parsed + results.
    """
    # 1. Parse
    print(f"\n{DIM}[1/3] Parsing resume...{RESET}")
    parser = ResumeParser()
    parsed = parser.parse(resume_text)
    print_parsed_resume(parsed)

    # 2. Embed & match
    print(f"\n{DIM}[2/3] Computing embeddings and matching roles...{RESET}")
    embedder = ResumeEmbedder()
    matcher  = JobMatcher(embedder=embedder)
    results  = matcher.match(parsed, top_k=top_k)
    print_match_results(results)

    # 3. Persist
    if use_db and db_config:
        print(f"\n{DIM}[3/3] Saving to MySQL...{RESET}")
        db = ResumeDatabase(**db_config)
        if db.connect():
            cid = db.save_resume(parsed)
            if cid:
                db.save_match_results(cid, results)
                print(f"  {GREEN}✓ Saved. Candidate ID: {cid}{RESET}")
            db.disconnect()
        else:
            print(f"  {RED}✗ DB connection failed. Data not persisted.{RESET}")
    else:
        print(f"\n{DIM}[3/3] DB not configured — skipping persistence.{RESET}")
        print(f"  {DIM}(Add --db and --db-password to enable MySQL storage){RESET}")

    return {
        "parsed": parsed.to_dict(),
        "matches": [r.to_dict() for r in results],
    }


def main():
    print_banner()
    parser = argparse.ArgumentParser(
        description="AI Resume Intelligence System",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--resume",      type=str, help="Path to resume .txt file")
    parser.add_argument("--demo",        action="store_true", help="Run with a built-in demo resume")
    parser.add_argument("--top-k",       type=int, default=5, help="Number of role matches to return")
    parser.add_argument("--json-out",    type=str, help="Save results as JSON to this path")
    parser.add_argument("--db",          action="store_true", help="Enable MySQL persistence")
    parser.add_argument("--db-host",     default="localhost")
    parser.add_argument("--db-port",     type=int, default=3306)
    parser.add_argument("--db-user",     default="root")
    parser.add_argument("--db-password", default="")
    parser.add_argument("--db-name",     default="resume_intelligence")
    parser.add_argument("--analytics",   action="store_true", help="Print recruiter analytics from DB")
    args = parser.parse_args()

    db_config = {
        "host": args.db_host, "port": args.db_port,
        "user": args.db_user, "password": args.db_password,
        "database": args.db_name,
    } if args.db else None

    # Analytics-only mode
    if args.analytics:
        if not args.db:
            print(f"{RED}--analytics requires --db to be set.{RESET}")
            sys.exit(1)
        db = ResumeDatabase(**db_config)
        if db.connect():
            print_analytics(db)
            db.disconnect()
        else:
            print(f"{RED}Could not connect to database.{RESET}")
        return

    # Determine resume text
    if args.demo:
        resume_text = DEMO_RESUME
        print(f"{YELLOW}[Demo mode] Using built-in sample resume.{RESET}")
    elif args.resume:
        p = Path(args.resume)
        if not p.exists():
            print(f"{RED}File not found: {args.resume}{RESET}")
            sys.exit(1)
        resume_text = p.read_text(encoding="utf-8")
    else:
        print(f"{YELLOW}No input specified. Reading from stdin (Ctrl+D to finish):{RESET}")
        resume_text = sys.stdin.read()

    output = run_pipeline(
        resume_text=resume_text,
        use_db=args.db,
        db_config=db_config,
        top_k=args.top_k,
    )

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(output, indent=2))
        print(f"\n{GREEN}Results saved → {args.json_out}{RESET}")

    print(f"\n{GREEN}{BOLD}Done.{RESET}\n")


if __name__ == "__main__":
    main()
