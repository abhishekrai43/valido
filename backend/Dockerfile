FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (Tesseract for OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
	tesseract-ocr \
	libtesseract-dev \
	poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# Install minimal runtime dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
# Copy the entire backend package into the image at /app/backend so imports like
# `import backend.*` work the same way as in the repository and the worker container.
COPY . /app/backend

# Install the backend package in editable mode so the `app` package (backend/app)
# is available on sys.path for both backend and worker processes. This avoids
# brittle PYTHONPATH hacks and makes imports consistent inside containers.
RUN pip install --no-cache-dir -e /app/backend

# expose new port for app
EXPOSE 9090
# Use the package-qualified import so uvicorn loads the same package layout used by the
# worker (and by imports elsewhere in the codebase).
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "9090"]
