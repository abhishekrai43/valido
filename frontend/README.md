Valido frontend
===============

This is a minimal static frontend that lets users upload PDFs or a ZIP and optional rules JSON.

How to use
----------

1. Open `frontend/index.html` in a browser.

2. Or serve it locally with a small static server (recommended so fetch calls work without file:// restrictions):

```powershell
# from repo root
cd frontend
python -m http.server 3000
# then open http://localhost:3000 in your browser
```

3. Ensure the backend API is running at `http://localhost:8000` (the frontend posts to `/api/v1/submit` relative path).

Notes
-----
- This is intentionally tiny and dependency-free. If you want a React/Vue UI or packaging into the Docker Compose flow, I can scaffold that next.
- For production / larger uploads, consider uploading to shared storage and sending references to the worker to avoid large broker messages.
