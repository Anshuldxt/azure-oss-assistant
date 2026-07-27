# Single-container build: FastAPI backend + static frontend served
# from the same process. Build context is the repo root (this file's
# own directory), not backend/ -- so both `backend/` and `frontend/`
# are visible to COPY.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
COPY frontend frontend

WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
