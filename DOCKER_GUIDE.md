# Docker Setup Guide

Run the AI Resume Intelligence System using Docker! 🐳

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed (optional, but recommended)

---

## Option 1: Run with Docker (Without MySQL)

### Step 1: Build the image
```bash
git clone https://github.com/Rishi1878/ai-resume-analyzer.git
cd ai-resume-analyzer

docker build -t ai-resume-analyzer .
```

### Step 2: Run the container

#### Run Demo Resume
```bash
docker run ai-resume-analyzer python main.py --demo
```

#### Parse Your Resume (from local file)
```bash
docker run -v $(pwd)/resumes:/app/resumes ai-resume-analyzer python main.py --resume /app/resumes/your_resume.txt
```

#### Save Results as JSON
```bash
docker run -v $(pwd)/results:/app/results ai-resume-analyzer python main.py --demo --json-out /app/results/output.json
```

#### Interactive Mode (stdin)
```bash
docker run -it ai-resume-analyzer python main.py
# Paste resume text and press Ctrl+D
```

---

## Option 2: Run with Docker Compose (With MySQL)

This setup includes both the analyzer and a MySQL database.

### Step 1: Start services
```bash
git clone https://github.com/Rishi1878/ai-resume-analyzer.git
cd ai-resume-analyzer

docker-compose up --build
```

### Step 2: In another terminal, run commands

#### Parse with DB persistence
```bash
docker-compose exec resume-analyzer python main.py --demo --db --db-host mysql --db-user root --db-password resume_password
```

#### View analytics
```bash
docker-compose exec resume-analyzer python main.py --analytics --db --db-host mysql --db-user root --db-password resume_password
```

### Step 3: Stop services
```bash
docker-compose down
```

---

## Quick Start Examples

### 1. Run Demo (Fastest)
```bash
docker run ai-resume-analyzer
```

### 2. Process local resume files
```bash
# Create directories
mkdir resumes results
cp your_resume.txt resumes/

# Run analyzer
docker run -v $(pwd)/resumes:/app/resumes -v $(pwd)/results:/app/results ai-resume-analyzer \
  python main.py --resume /app/resumes/your_resume.txt --json-out /app/results/output.json

# Check results
cat results/output.json
```

### 3. Batch process multiple resumes
```bash
#!/bin/bash
for resume in resumes/*.txt; do
  filename=$(basename "$resume")
  echo "Processing $filename..."
  docker run -v $(pwd)/resumes:/app/resumes -v $(pwd)/results:/app/results ai-resume-analyzer \
    python main.py --resume /app/resumes/$filename --json-out /app/results/${filename%.txt}_output.json
done
```

---

## Docker Commands Reference

### Build image
```bash
docker build -t ai-resume-analyzer .
```

### List images
```bash
docker images | grep ai-resume
```

### Run container
```bash
docker run [OPTIONS] ai-resume-analyzer [COMMAND]
```

### Common options
- `-v HOST_PATH:CONTAINER_PATH` - Mount volume
- `-e VAR=VALUE` - Set environment variable
- `-it` - Interactive terminal
- `-d` - Detached mode (background)
- `--name` - Container name

### View logs
```bash
docker logs container_name
```

### Execute command in running container
```bash
docker exec -it container_name bash
```

### Clean up
```bash
docker stop container_name
docker rm container_name
docker rmi ai-resume-analyzer
```

---

## Docker Compose Commands

### Start services
```bash
docker-compose up
```

### Build and start
```bash
docker-compose up --build
```

### Run in background
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f resume-analyzer
```

### Execute command
```bash
docker-compose exec resume-analyzer bash
```

---

## Volumes & Mounts

The docker-compose.yml includes:

```yaml
volumes:
  - ./resumes:/app/resumes      # Put input resumes here
  - ./results:/app/results      # Results saved here
```

Create these directories:
```bash
mkdir resumes results
```

---

## Environment Variables

You can customize behavior with env vars:

```bash
docker run -e MYSQL_ROOT_PASSWORD=mypass ai-resume-analyzer python main.py --demo
```

Common variables:
- `PYTHONUNBUFFERED=1` - Real-time output
- `DB_HOST` - Database host
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

---

## Troubleshooting

### Issue: "Cannot find Python module"
**Solution**: Rebuild the image
```bash
docker build --no-cache -t ai-resume-analyzer .
```

### Issue: "Permission denied" on volumes
**Solution**: Check directory permissions
```bash
chmod 755 resumes results
```

### Issue: MySQL connection timeout
**Solution**: Wait for MySQL to start
```bash
# Check if MySQL is ready
docker-compose exec mysql mysqladmin ping

# Or wait in docker-compose
docker-compose up mysql  # Start only MySQL first
```

### Issue: Out of disk space
**Solution**: Clean up Docker
```bash
docker system prune -a
```

---

## Performance Tips

1. **Use `.dockerignore`** to exclude large files:
   ```
   __pycache__/
   *.pyc
   .git/
   venv/
   .env
   ```

2. **Use Alpine image for smaller size**:
   ```dockerfile
   FROM python:3.9-alpine
   ```

3. **Cache layers** - Order dependencies strategically in Dockerfile

4. **Use GPU acceleration** (if available):
   ```bash
   docker run --gpus all ai-resume-analyzer python main.py --demo
   ```

---

## Next Steps

- Read [README.md](README.md) for full feature documentation
- Customize `docker-compose.yml` for your needs
- Add custom job roles in `job_matcher.py`
- Extend skill taxonomy in `resume_parser.py`

---

## Questions?

Open an issue on [GitHub](https://github.com/Rishi1878/ai-resume-analyzer/issues) 💬
