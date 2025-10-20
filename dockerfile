# Stage 1: Builder
FROM python:3.14-slim AS builder
WORKDIR /app

# Install system build tools and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    pkg-config \
 && pip install --no-cache-dir --upgrade uv \
 && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv pip install (simpler approach)
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Runtime
FROM python:3.14-slim
WORKDIR /app

# Install only runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
 && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY main.py ./

# Create a non-root user for safety
RUN useradd -m appuser
USER appuser

# Expose internal port only (nginx will handle external exposure)
EXPOSE 8000

# Healthcheck using urllib (no extra deps)
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Start the app
CMD ["python", "main.py"]
