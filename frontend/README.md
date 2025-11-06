Purpose: instruct the co-pilot to convert the current Valido repository into a Windows-native single-machine distributable (no Docker). Be concise, actionable and strict on code style and quality.

Goals (brief)

Add a single-process mode replacing Celery/Redis for single-machine installs.

Bundle app into a Windows EXE with PyInstaller.

Install app as a Windows Service (prefer NSSM; provide pywin32 alternative).

Produce an Inno Setup installer that registers the service, creates folders, shortcuts, uninstall.

Add a first-run wizard in the web UI and a diagnostics page.

Add a simple trial license file check and UI banner.

Produce build artifacts and a QA checklist

Deliverables (ordered)

local_worker.py + minimal changes to switch via SINGLE_PROCESS_MODE=true.

launcher.py that starts FastAPI + local worker in one process.

pyinstaller.spec and build script build_windows.bat.

nssm_install.bat and service_pywin32.py (alternative).

installer.iss (Inno Setup script).

First-run wizard UI snippets and endpoints.

QA_CHECKLIST.md.

package_build_instructions.md — commands to build and test locally.

Keep it short and readable. Small functions, single responsibility.

Use explicit type hints everywhere (mypy compatible).

Avoid long comments in code. Use clear names; comments only when necessary (1–2 lines).

No AI emojis or marketing fluff anywhere in code or docs.

Follow PEP8. Use black, isort, and ruff/flake8. Add pre-commit hooks.

Write unit tests for every new module (pytest). Aim ≥ 80% coverage for changed code.

Add docstrings (one-line summary + brief args/returns) only for public functions.

Log at appropriate levels. No verbose prints in production code.

Keep secrets and keys out of repository.