FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast, deterministic installs
RUN pip install --no-cache-dir uv

# Install Python dependencies
COPY apps/api/requirements.txt ./requirements.txt
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY apps/api ./apps/api
WORKDIR /app/apps/api

EXPOSE 8000

# Run migrations on boot (free-tier hosts have no shell for one-off commands),
# then serve. $PORT is provided by Render; defaults to 8000 elsewhere.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]