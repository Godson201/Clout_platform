FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ffmpeg is a runtime dependency of app/services/video_processing.py (invoked
# via subprocess, not a Python package) — the slim base image doesn't include
# it, and the ad-upload pipeline silently has nothing to transcode with
# without this.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form (not exec-array) so ${PORT} actually expands — Railway (and most
# PaaS targets) injects PORT at runtime and expects the app to bind to it,
# falling back to 8000 for plain `docker run` / docker-compose.
# Apply migrations before accepting traffic.  This shell-form command is kept
# in the image because Render's Docker Command field does not preserve `&&`.
CMD alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
