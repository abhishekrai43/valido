## PDF Validator — Phased Roadmap

This document breaks the project into clear, incremental phases. Each phase has acceptance criteria, deliverables, recommended starting points, and a suggested branch name.

---

### Phase 0 — Discovery & Local Setup (complete/validation)
- Goal: Confirm architecture, local dev environment, and critical automation.
- Acceptance Criteria:
  - `README.md` reviewed and validated.
  - Repo builds locally (or a clear checklist if code is missing).
  - A short list of missing artifacts (Dockerfile, backend/app structure) produced.
- Deliverables: `PHASES.md`, `AGENT_INSTRUCTIONS.md`, minimal dev checklist.
- Start point: `README.md` (root).
- Branch: `phase/00-discovery`

---

### Phase 1 — MVP: Core Backend & Minimal UI
- Goal: Implement a working, privacy-first pipeline for single-file PDF validation.
- Acceptance Criteria:
  - Backend FastAPI app with: upload endpoint, parser service stub, validator stub.
  - End-to-end flow for one PDF: upload -> parse (text) -> apply deterministic rule -> return JSON report.
  - Unit tests for parser and validator (pytest).
  - Dockerfile + `docker-compose.yml` that runs backend and a placeholder frontend.
- Deliverables:
  - `backend/app/main.py` (FastAPI entrypoint)
  - `backend/app/services/parser.py` (text-extraction interface)
  - `backend/app/services/validator.py` (rules engine interface)
  - `backend/tests/` (unit tests)
  - `docker-compose.yml` and `backend/Dockerfile`
- Start point: `backend/` (create those directories and files if missing).
- Branch: `phase/01-mvp`
- Estimated effort: 3–7 days (small team or 1–2 devs full-time)

---

### Phase 2 — Rules UX, Rule Storage, & Translator (AI optional)
- Goal: Allow users to upload/type rules and persist rulesets; add optional AI translator service (rule-text → JSON).
- Acceptance Criteria:
  - Rules API (create/list/get/validate) with Pydantic schemas.
  - Rules persisted (SQLite for local mode; SQLAlchemy models provided).
  - Simple frontend pages for rule creation and upload.
  - Optional: AI translator endpoint that is disabled by default and can call a configured LLM endpoint.
- Deliverables: `backend/app/routes/rules.py`, `backend/app/models/*`, `frontend/src/pages/rules/*`.
- Branch: `phase/02-rules`

---

### Phase 3 — Batch Processing & Async Workers
- Goal: Scale to batches using Celery + Redis and support lazy OCR fallback.
- Acceptance Criteria:
  - Job queue integration (Celery tasks) for parsing + validation.
  - Worker image and `docker-compose` services for Redis and worker.
  - OCR fallback path using Tesseract for image-only PDFs.
  - End-to-end test that queues and processes a small ZIP of PDFs.
- Deliverables: `backend/celery.py`, `backend/app/tasks/`, `docker-compose.yml` updated.
- Branch: `phase/03-batch`

---

### Phase 4 — Observability, Tracing, and Resilience
- Goal: Add OpenTelemetry tracing, Prometheus metrics, and robust error handling.
- Acceptance Criteria:
  - OpenTelemetry instrumentation on API + tasks.
  - Metrics endpoint for Prometheus scraping.
  - Structured logging with request_id and job_id included.
- Deliverables: `backend/app/utils/logger.py`, `otel/` config snippets, Prometheus scrape config.
- Branch: `phase/04-observability`

---

### Phase 5 — Security, Privacy, & Hardening
- Goal: Ensure privacy-first guarantees and harden the runtime.
- Acceptance Criteria:
  - Air-gap / offline mode available (no outbound network by default).
  - Rate limiting, input sanitization, PDF sandboxing guidance implemented.
  - Secrets handling and TLS for endpoints documented and scripted.
- Deliverables: `config.yaml` security presets, rate-limiter middleware, hardened Docker image.
- Branch: `phase/05-security`

---

### Phase 6 — Integrations, E2E Tests, CI/CD
- Goal: Add integrations (S3, optional cloud LLM), full E2E tests, and GitHub Actions pipeline.
- Acceptance Criteria:
  - E2E tests (Playwright or Cypress) covering core flows.
  - CI pipeline: lint, unit tests, build images, and optional integration tests behind flags.
  - Release notes and deployment templates (Kubernetes manifests or Cloudformation).
- Deliverables: `.github/workflows/ci.yml`, `tests/e2e/`, `deploy/` manifests.
- Branch: `phase/06-ci`

---

### Phase 7 — Production & Ops
- Goal: Production-ready deployment, SLOs, scaling rules, and runbook.
- Acceptance Criteria:
  - Helm chart or Terraform configuration for cluster deployment.
  - Runbook for common incidents and recovery steps.
  - SLOs and alerting rules created.
- Deliverables: `deploy/`, `runbooks/`, SLO documents.
- Branch: `phase/07-prod`

---

## How to pick a phase and start
- The agent or developer should open `PHASES.md`, pick the earliest incomplete phase, create a branch named as suggested, and follow the Deliverables list.
- If the repository lacks the files listed as Deliverables, scaffold them with minimal, testable stubs and unit tests.

## Scaffolding performed (automated agent run)
- The following scaffolds were added to accelerate Phase 1–4 development:
  - `backend/app/main.py` (FastAPI entrypoint)
  - `backend/app/services/parser.py` (parser stub)
  - `backend/app/services/validator.py` (validator stub)
  - `backend/requirements.txt` and `backend/Dockerfile`
  - `docker-compose.yml` to run the backend
  - `backend/app/routes/rules.py` (rules API stub)
  - `backend/celery.py` and `backend/app/tasks/worker_tasks.py` (Celery stubs)
  - `backend/app/utils/logger.py` (logging stub)
  - `frontend/package.json` placeholder

These files are intentionally minimal; they provide the pipeline structure so developers can implement each phase's full functionality.

## Acceptance & Handover
- Each phase ends with a PR that includes:
  - Passing unit tests and linting.
  - A short PR description mapping code changes to the Acceptance Criteria.
  - A demo script or screenshot (for UI work).
