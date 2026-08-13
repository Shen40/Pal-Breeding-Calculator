FROM python:3.11-slim

# Prevent Python from writing .pyc files & enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for PostgreSQL and builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application files and static data
COPY ./src /app/src
COPY ./data /app/data
COPY ./static /app/static
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

EXPOSE 8000

# Apply migrations, then run with Gunicorn managing Uvicorn worker processes
CMD ["sh", "-c", "alembic upgrade head && gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"]