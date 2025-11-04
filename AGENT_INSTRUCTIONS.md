# Agent Instructions — How an automated agent should pick up work

Purpose: Give a deterministic, safe checklist so an automated agent (or developer following automation rules) can inspect the repo, select the next phase, scaffold missing artifacts, run validation, and create a PR. These instructions include required constraints (notably: do not place AI icons or long AI-comments into code).

---

## High-level rules (must follow)
- Privacy & safety first: do not send PDFs or extracted content off-host. If network calls are required, only call configured endpoints and respect `config.yaml` air-gap mode.
- Code commenting rule: do not include AI icons, logos, badges, or long AI-generated comment blocks inside source files. Comments must be concise, technical, and actionable (max 3 lines for implementation notes). Example of forbidden content: any ASCII art or icons representing an AI service, or comments like "Powered by AI — see console".
- Keep PRs small and self-contained: one feature or bugfix per branch.

## Preconditions (what the agent should check first)
1. Confirm repo root contains `README.md` and `PHASES.md`.
2. Run a repository scan to list top-level files and common folders (`backend`, `frontend`, `docker-compose.yml`).
3. Confirm local tooling availability (python, pip, node) by inspecting the environment; if missing, create a checklist and report to the user rather than attempting installs.

## Discovery steps (how to decide where to start)
1. Open `PHASES.md`. Locate the earliest phase with missing deliverables by either:
   - Checking for the files listed under Deliverables, or
   - Searching for tests or code that implement that capability.
2. If everything in `PHASES.md` appears completed, consult git history for recent PRs and the issue tracker (if present) and select the next-highest-priority item.

## Minimal actionable workflow the agent should run
1. Create a new branch following the naming convention in `PHASES.md` (e.g., `phase/01-mvp`).
2. Scaffold minimal, testable stubs for missing Deliverables (do not write full implementations in the first commit):
   - Small, well-typed stubs with Pydantic models where applicable.
   - One unit test per stub to prove the shape and API.
   - Keep comments short; do NOT add AI icons or long AI comments.
3. Run lint and tests locally. If tests fail, iterate until the new stubs pass and baseline linting is satisfied.
4. Commit with a clear message: `phase(01-mvp): add parser/validator stubs + unit tests`.
5. Push branch and open a PR with a link to `PHASES.md` and a short description mapping the PR to Acceptance Criteria.

## CI / Local run commands (examples the agent may run)
Note: run these only if the environment provides required runtimes.

Python (run in repo root):
```
python -m pip install -r backend/requirements.txt  # only if file exists
pytest backend/tests -q
flake8 backend || true
```

Docker (optional):
```
docker-compose up --build -d
docker-compose logs --tail=50
```

## Commit & PR rules
- Keep commits atomic.
- Include tests and update `PHASES.md` or `AGENT_INSTRUCTIONS.md` if the scope of a phase changes.
- PR description must map code to acceptance criteria and list manual steps to validate.

## Error handling & reporting
- If any step fails because of missing environment tools or blocked network, the agent must:
  1. Create an issue in the repo (if issue creation is allowed) or add a `DEV_NOTES.md` with clear reproduction steps.
  2. Stop further network activity and notify the human owner.

## Where to resume later
- Each PR must include a short "Next steps" section listing what the next agent or developer should do (exact files, tests, or integration points). This ensures an agent resuming work knows where to pick up.

## Small contract (inputs / outputs / success modes)
- Inputs: repository files, `PHASES.md`, `README.md`, and configured environment variables for local runs.
- Outputs: new branch with commits, unit tests, passing lint & tests for new code, PR opened with mapping to acceptance criteria.
- Success: PR created with green tests for new stubs and clear manual validation steps.
- Error modes: missing runtime, failing CI, air-gap enforced — see Error handling above.

## Edge cases for the agent
- Repo only has docs (no code): scaffold the minimum and create a discovery ticket.
- CI credentials missing: avoid creating/releases; create a ticket.
- AI translator flagged but no credentials: do not call any LLM; create a stub and mark the translator as disabled by default.

## Human-readable checklist the agent leaves in each PR
1. Which phase is addressed.
2. Files added/changed.
3. Tests added and how to run them.
4. Any manual verification steps (e.g., upload a sample PDF via curl).
5. Next steps for the following phase.

---

If you want, I can now run a repository scan, create the first-phase branch scaffold for `phase/01-mvp`, and commit minimal parser/validator stubs and tests. Tell me to proceed and I will follow these instructions strictly (including the "no AI icons / no long AI comments" rule).
