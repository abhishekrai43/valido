RUNNING.md
===========

This document shows quick ways to run the project locally on Windows (PowerShell) and with Docker Compose.

Windows (PowerShell) - local dev
--------------------------------
Prereqs:
- Python 3.10+ installed and on PATH
- Recommended: create a venv

Steps:

1. From the repository root open PowerShell and create/activate a venv

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend/requirements.txt
```

2. Start the FastAPI backend (development)

```powershell
# from repository root
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Running a Celery worker locally (PowerShell)

Set broker/result backends to a Redis server running locally (or use Docker-based Redis). Example uses local Redis at default port.

```powershell
$env:CELERY_BROKER_URL = 'redis://localhost:6379/0'
$env:CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
$env:CELERY_WORKER_CONCURRENCY = '2'
# Run worker from backend folder
cd backend
celery -A backend.celery.celery_app worker --loglevel=info --concurrency=$env:CELERY_WORKER_CONCURRENCY
```

Docker Compose - local with resource caps
----------------------------------------
This project includes a `docker-compose.yml` with service examples for `backend`, `redis`, and `worker`.

Notes about resource limits:
- `mem_limit` is respected by docker-compose in most local setups.
- `deploy.resources` is only honored in swarm mode; it's included as a recommendation and for platforms that honor it.

Examples

1) Start with Docker Compose (builds the backend image and starts Redis and worker):

```powershell
# From repository root
docker-compose up --build
```

2) Override worker concurrency and resource caps at runtime via environment variables

```powershell
# Example: set worker concurrency to 4 and start
$env:CELERY_WORKER_CONCURRENCY = '4'
docker-compose up --build
```

3) If you only want the API server (no worker), run:

```powershell
docker-compose up --build backend
```

Windows-specific tips
---------------------
- If you use Windows containers (not typical for Python apps) resource syntax may differ. These instructions assume Linux containers under Docker Desktop.
- When running PowerShell commands in CI or scripts, ensure execution policy permits activation of virtual environments (or use the `Activate.ps1` script explicitly).

Verifying the worker
--------------------
- Visit http://localhost:8000/healthz to confirm the API is up.
- Submit a task to the worker (call the endpoint or trigger the Celery task directly) and poll the task result via Celery backend (Redis) or look at worker logs.

If anything fails or your environment is different (macOS, WSL, non-standard Docker), tell me which OS and I can add tailored instructions.