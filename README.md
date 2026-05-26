# AI Resume Intelligence System

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end NLP system that analyzes resumes and predicts the best-matching job roles using **semantic embeddings** (MiniLM-L6-v2) and **ATS-style feature matching**. Perfect for recruiters, HR platforms, and AI-driven talent matching systems.

## Features

✨ **Resume Parsing**
- Extract structured data from resume text using spaCy NER
- Entity recognition: name, email, phone, LinkedIn, GitHub
- Skill extraction from a comprehensive taxonomy
- Education & experience years estimation
- GPA extraction

🧠 **Semantic Matching**
- State-of-the-art sentence embeddings (MiniLM-L6-v2 from HuggingFace)
- Cosine similarity scoring for resume-to-job matching
- Pre-embedded job catalogue (8 roles) for fast inference

📊 **Hybrid Scoring**
- **60% semantic similarity** (deep understanding)
- **40% ATS scoring** (keyword matching, education, experience)
- Combined final score for robust predictions

💾 **MySQL Persistence**
- Store candidates, skills, and match results
- Recruiter analytics: top skills, role demand, experience distribution
- Daily snapshots for trend analysis

📄 **PDF Support**
- Extract text from PDF resumes (via pdfplumber)
- Seamless pipeline with txt or PDF input

🎯 **Pre-built Job Catalogue**
1. Machine Learning Engineer
2. NLP / LLM Engineer
3. Data Scientist
4. Data Engineer
5. AI Research Scientist
6. Backend Software Engineer
7. Full-Stack Developer
8. DevOps / MLOps Engineer

---

## Installation

### Prerequisites
- Python 3.8+
- (Optional) MySQL 5.7+
- (Optional) pdfplumber (for PDF support)

### Step 1: Clone the repository
```bash
git clone https://github.com/Rishi1878/ai-resume-analyzer.git
cd ai-resume-analyzer
```

### Step 2: Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Download spaCy model
```bash
python -m spacy download en_core_web_sm
```

### Step 5 (Optional): Set up MySQL
If you want to enable database persistence:
```bash
# Make sure MySQL server is running
mysql -u root -p
# No need to create database manually — the app does it automatically
```

---

## Usage

### Quick Start: Demo Resume
```bash
python main.py --demo
```

### Parse a Text Resume
```bash
python main.py --resume path/to/resume.txt
```

### Parse a PDF Resume
```bash
python main.py --resume path/to/resume.pdf
```

### Save Results as JSON
```bash
python main.py --resume resume.txt --json-out results.json
```

### Enable MySQL Persistence
```bash
python main.py --demo --db --db-password your_mysql_password
```

### View Recruiter Analytics
```bash
python main.py --analytics --db --db-password your_mysql_password
```

### Advanced Options
```bash
python main.py --help

Options:
  --resume PATH              Path to resume .txt or .pdf file
  --demo                     Run with built-in demo resume
  --top-k N                  Number of role matches to return (default: 5)
  --json-out PATH            Save results as JSON
  --db                       Enable MySQL persistence
  --db-host HOST             MySQL host (default: localhost)
  --db-port PORT             MySQL port (default: 3306)
  --db-user USER             MySQL user (default: root)
  --db-password PASSWORD     MySQL password
  --db-name DATABASE         Database name (default: resume_intelligence)
  --analytics                Print analytics from DB (requires --db)
```

---

## Architecture

### Module Structure

```
ai-resume-analyzer/
├── resume_parser.py      # Extracts entities from resume text (spaCy NER + regex)
├── embedder.py           # Generates semantic embeddings (sentence-transformers)
├── job_matcher.py        # Hybrid scoring: semantic + ATS
├── database.py           # MySQL persistence layer
├── pdf_reader.py         # PDF text extraction utility
├── main.py              # CLI entry point
├── requirements.txt      # Dependencies
└── README.md            # This file
```

### Data Flow

```
Resume (TXT/PDF)
    ↓
[resume_parser.py]  → Extract entities (name, skills, experience, etc.)
    ↓
ParsedResume object
    ↓
[embedder.py]       → Generate semantic embedding (384-dim vector)
                    → Load pre-embedded job descriptions
    ↓
[job_matcher.py]    → Compute semantic similarity
                    → Compute ATS score (skills, education, experience)
                    → Combine scores (0.6*semantic + 0.4*ATS)
                    → Rank and generate recommendations
    ↓
Top-K MatchResults
    ↓
[database.py]       → (Optional) Store in MySQL
    ↓
Output: Formatted results + JSON
```

### Scoring Formula

**Final Score = 0.6 × Semantic_Similarity + 0.4 × ATS_Score**

**ATS Score Breakdown:**
- Required Skills Match: 50 pts
- Preferred Skills Match: 30 pts
- Education Level: 20 pts

**Experience Penalty:**
- If candidate's experience < role's min_experience: 10% penalty

---

## Example Output

```
╔═══════════════════════════════════════════════════════╗
║       AI RESUME INTELLIGENCE SYSTEM  v1.0             ║
║       NLP · Transformers · MiniLM · MySQL             ║
╚═══════════════════════════════════════════════════════╝

──────────────────────────────────────────────────────
  PARSED RESUME
──────────────────────────────────────────────────────
  Name:        Jane Doe
  Email:       jane.doe@email.com
  Phone:       +91-9876543210
  LinkedIn:    linkedin.com/in/janedoe
  GitHub:      github.com/janedoe
  Experience:  3 years
  Education:   B.Tech
  GPA:         8.9/10

  Skills by category:
    programming      python, java, javascript
    ml_ai            machine learning, nlp, transformers
    frameworks       pytorch, tensorflow, spacy
    data             sql, pandas, kafka
    cloud_devops     docker, kubernetes, aws

──────────────────────────────────────────────────────
  JOB ROLE PREDICTIONS
──────────────────────────────────────────────────────

  #1  NLP / LLM Engineer
      Score: ███████████████████████░░░░░░░░░░░░░░░░░░ 82.5%
      Semantic: 85.2%   ATS: 78.9%   Exp OK: ✓
      ✓ Required: python, nlp, transformers
      + Preferred: pytorch, rag, fine-tuning
      Strong fit (82% match). Strengths: python, nlp, transformers.

  #2  Machine Learning Engineer
      Score: ███████████████░░░░░░░░░░░░░░░░░░░░░░░░░ 76.3%
      Semantic: 79.1%   ATS: 71.8%   Exp OK: ✓
      ✓ Required: python, machine learning, pytorch
      Missing key skills: tensorflow.
      Good fit (76% match). Strengths: python, pytorch, tensorflow.

  ...

──────────────────────────────────────────────────────
  ✓ Saved. Candidate ID: 42
──────────────────────────────────────────────────────
Done.
```

---

## Database Schema

### candidates
```sql
id (PK), name, email (UNIQUE), phone, linkedin, github,
experience_years, education (JSON), gpa, raw_text,
created_at, updated_at
```

### candidate_skills
```sql
id (PK), candidate_id (FK), skill, category
```

### match_results
```sql
id (PK), candidate_id (FK), job_title, rank_position,
final_score, semantic_score, ats_score,
matched_required (JSON), matched_preferred (JSON),
missing_required (JSON), experience_ok, recommendation,
created_at
```

### analytics_snapshots
```sql
id (PK), snapshot_date, total_resumes, avg_experience,
top_skills (JSON), top_roles (JSON), created_at
```

---

## Performance

- **Resume Parsing**: ~50-100ms per resume
- **Embedding Generation**: ~200-400ms per resume (first load includes model init)
- **Job Matching**: ~50-100ms (8 jobs × cosine similarity)
- **Total Pipeline**: ~500-1000ms for first resume; ~300-500ms for subsequent resumes

*Benchmarks on CPU (Intel i7, 16GB RAM). GPU acceleration available with `sentence-transformers` GPU support.*

---

## Customization

### Add Custom Job Descriptions

```python
from job_matcher import JobMatcher, load_custom_jd

matcher = JobMatcher()

# Add a custom job
custom_job = load_custom_jd(
    jd_text="Expert in cloud infrastructure and DevOps automation...",
    title="Senior DevOps Engineer"
)

# Extend job catalogue
from job_matcher import JOB_CATALOGUE
JOB_CATALOGUE.append(custom_job)
```

### Adjust Scoring Weights

```python
# In job_matcher.py, modify:
class JobMatcher:
    SEMANTIC_WEIGHT = 0.70  # Increase semantic weight
    ATS_WEIGHT = 0.30       # Decrease ATS weight
```

### Extend Skill Taxonomy

```python
# In resume_parser.py, add to SKILL_TAXONOMY:
SKILL_TAXONOMY = {
    "blockchain": ["solidity", "ethereum", "web3", "truffle"],
    ...
}
```

---

## Testing

Run the demo with sample data:
```bash
python main.py --demo
```

Parse a custom resume:
```bash
echo "Jane Doe\njane@example.com\nPython, Machine Learning, AWS" | python main.py
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'spacy'`
**Solution:**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Issue: `mysql-connector-python not installed. DB features disabled.`
**Solution:**
```bash
pip install mysql-connector-python
```

### Issue: MySQL connection failed
**Solution:**
1. Ensure MySQL server is running: `mysql -u root -p`
2. Verify credentials: `--db-user`, `--db-password`
3. Check connectivity: `mysql -h localhost -u root`

### Issue: PDF extraction returns empty text
**Solution:**
```bash
# Install pdfplumber
pip install pdfplumber
# Try with a text-based PDF (not image-based scans)
```

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Citation

If you use this system in research or production, please cite:

```bibtex
@software{ai-resume-analyzer,
  author = {Rishi1878},
  title = {AI Resume Intelligence System},
  year = {2024},
  url = {https://github.com/Rishi1878/ai-resume-analyzer}
}
```

---

## Acknowledgments

- **spaCy**: For NER and linguistic features
- **Hugging Face**: For sentence-transformers and MiniLM-L6-v2
- **pdfplumber**: For PDF text extraction
- **MySQL**: For robust data persistence

---

## Contact

For questions or feedback, reach out via:
- GitHub Issues: [Report a bug](https://github.com/Rishi1878/ai-resume-analyzer/issues)
- Email: [Your email]

---

**Happy matching! 🚀**
