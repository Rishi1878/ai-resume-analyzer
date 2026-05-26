"""
database.py
-----------
MySQL persistence layer for resume analytics.
Schema: candidates, skills, match_results
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Dict

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("[DB] mysql-connector-python not installed. DB features disabled.")

logger = logging.getLogger(__name__)

# ── DDL ──────────────────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS candidates (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120),
    email           VARCHAR(180) UNIQUE,
    phone           VARCHAR(30),
    linkedin        VARCHAR(255),
    github          VARCHAR(255),
    experience_years INT,
    education       JSON,
    gpa             VARCHAR(20),
    raw_text        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id    INT NOT NULL,
    skill           VARCHAR(80),
    category        VARCHAR(60),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS match_results (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id    INT NOT NULL,
    job_title       VARCHAR(120),
    rank_position   INT,
    final_score     FLOAT,
    semantic_score  FLOAT,
    ats_score       FLOAT,
    matched_required JSON,
    matched_preferred JSON,
    missing_required  JSON,
    experience_ok   TINYINT(1),
    recommendation  TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date   DATE,
    total_resumes   INT,
    avg_experience  FLOAT,
    top_skills      JSON,
    top_roles       JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


class ResumeDatabase:
    """
    Handles all MySQL operations for the Resume Intelligence System.

    Usage
    -----
    db = ResumeDatabase(host="localhost", user="root", password="...", database="resume_ai")
    db.connect()
    candidate_id = db.save_resume(parsed_resume)
    db.save_match_results(candidate_id, match_results)
    db.disconnect()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "resume_intelligence",
    ):
        self.config = dict(host=host, port=port, user=user,
                          password=password, database=database)
        self.conn = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not MYSQL_AVAILABLE:
            logger.warning("MySQL not available. Skipping connection.")
            return False
        try:
            # First connect without specifying DB to create it if needed
            init_cfg = {k: v for k, v in self.config.items() if k != "database"}
            tmp = mysql.connector.connect(**init_cfg)
            cur = tmp.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.config['database']}`")
            cur.close()
            tmp.close()

            self.conn = mysql.connector.connect(**self.config)
            self._run_ddl()
            logger.info(f"[DB] Connected to {self.config['database']}.")
            return True
        except MySQLError as e:
            logger.error(f"[DB] Connection failed: {e}")
            return False

    def disconnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()
            logger.info("[DB] Disconnected.")

    @contextmanager
    def _cursor(self, commit: bool = False):
        cur = self.conn.cursor(dictionary=True)
        try:
            yield cur
            if commit:
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def _run_ddl(self):
        with self._cursor(commit=True) as cur:
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)

    # ── Writes ────────────────────────────────────────────────────────────────

    def save_resume(self, parsed_resume) -> Optional[int]:
        """
        Upserts a candidate record + their skills.
        Returns the candidate's DB id.
        """
        if not self._is_connected():
            return None

        with self._cursor(commit=True) as cur:
            # Upsert candidate
            cur.execute("""
                INSERT INTO candidates
                    (name, email, phone, linkedin, github,
                     experience_years, education, gpa, raw_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name=VALUES(name), phone=VALUES(phone),
                    experience_years=VALUES(experience_years),
                    education=VALUES(education), gpa=VALUES(gpa),
                    raw_text=VALUES(raw_text), updated_at=NOW()
            """, (
                parsed_resume.name,
                parsed_resume.email or f"unknown_{datetime.now().timestamp()}",
                parsed_resume.phone,
                parsed_resume.linkedin,
                parsed_resume.github,
                parsed_resume.experience_years,
                json.dumps(parsed_resume.education),
                parsed_resume.gpa,
                parsed_resume.raw_text[:5000],
            ))

            # Get id
            cur.execute(
                "SELECT id FROM candidates WHERE email=%s",
                (parsed_resume.email or f"unknown",)
            )
            row = cur.fetchone()
            if not row:
                return None
            cid = row["id"]

            # Delete old skills and reinsert
            cur.execute("DELETE FROM candidate_skills WHERE candidate_id=%s", (cid,))
            for skill in parsed_resume.skills:
                category = parsed_resume.skill_categories.get(skill, "other")
                # skill_categories stores cat->list, reverse lookup
                skill_cat = "other"
                for cat, skills_list in parsed_resume.skill_categories.items():
                    if skill in skills_list:
                        skill_cat = cat
                        break
                cur.execute(
                    "INSERT INTO candidate_skills (candidate_id, skill, category) VALUES (%s,%s,%s)",
                    (cid, skill, skill_cat),
                )
        return cid

    def save_match_results(self, candidate_id: int, match_results: list):
        """Persist a list of MatchResult objects for a candidate."""
        if not self._is_connected():
            return

        with self._cursor(commit=True) as cur:
            # Remove previous results for this candidate
            cur.execute("DELETE FROM match_results WHERE candidate_id=%s", (candidate_id,))
            for r in match_results:
                cur.execute("""
                    INSERT INTO match_results
                        (candidate_id, job_title, rank_position, final_score,
                         semantic_score, ats_score, matched_required,
                         matched_preferred, missing_required,
                         experience_ok, recommendation)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    candidate_id,
                    r.title,
                    r.rank,
                    r.final_score,
                    r.semantic_score,
                    r.ats_score,
                    json.dumps(r.matched_required),
                    json.dumps(r.matched_preferred),
                    json.dumps(r.missing_required),
                    int(r.experience_ok),
                    r.recommendation,
                ))

    # ── Reads / Analytics ─────────────────────────────────────────────────────

    def get_all_candidates(self) -> List[Dict]:
        if not self._is_connected():
            return []
        with self._cursor() as cur:
            cur.execute("SELECT * FROM candidates ORDER BY created_at DESC")
            return cur.fetchall()

    def get_top_skills(self, limit: int = 20) -> List[Dict]:
        """Most common skills across all resumes."""
        if not self._is_connected():
            return []
        with self._cursor() as cur:
            cur.execute("""
                SELECT skill, category, COUNT(*) as count
                FROM candidate_skills
                GROUP BY skill, category
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def get_role_demand(self) -> List[Dict]:
        """Which roles candidates are most frequently matching."""
        if not self._is_connected():
            return []
        with self._cursor() as cur:
            cur.execute("""
                SELECT job_title,
                       COUNT(*) as candidate_count,
                       AVG(final_score) as avg_score
                FROM match_results
                WHERE rank_position = 1
                GROUP BY job_title
                ORDER BY candidate_count DESC
            """)
            return cur.fetchall()

    def get_experience_distribution(self) -> List[Dict]:
        if not self._is_connected():
            return []
        with self._cursor() as cur:
            cur.execute("""
                SELECT experience_years, COUNT(*) as count
                FROM candidates
                WHERE experience_years IS NOT NULL
                GROUP BY experience_years
                ORDER BY experience_years
            """)
            return cur.fetchall()

    def get_candidate_by_email(self, email: str) -> Optional[Dict]:
        if not self._is_connected():
            return None
        with self._cursor() as cur:
            cur.execute("SELECT * FROM candidates WHERE email=%s", (email,))
            return cur.fetchone()

    def save_analytics_snapshot(self):
        """Capture a daily analytics snapshot."""
        if not self._is_connected():
            return
        top_skills = self.get_top_skills(10)
        top_roles  = self.get_role_demand()
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) as n, AVG(experience_years) as avg_exp FROM candidates")
            stats = cur.fetchone()
        with self._cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO analytics_snapshots
                    (snapshot_date, total_resumes, avg_experience, top_skills, top_roles)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                datetime.now().date(),
                stats["n"],
                stats["avg_exp"],
                json.dumps(top_skills),
                json.dumps(top_roles),
            ))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_connected(self) -> bool:
        return self.conn is not None and self.conn.is_connected()
