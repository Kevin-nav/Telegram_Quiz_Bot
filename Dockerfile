# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PYTHONPATH=/app

# Set work directory
WORKDIR $APP_HOME

# Install system dependencies (needed for compiling some python packages like asyncpg, arq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create an unprivileged runtime user
RUN useradd --create-home --shell /usr/sbin/nologin appuser

# Copy project
COPY . .
RUN chown -R appuser:appuser $APP_HOME

# Drop root privileges for runtime
USER appuser

# Expose port (Uvicorn will run on 8000)
EXPOSE 8000

# Start Uvicorn for FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
