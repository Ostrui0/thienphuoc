FROM python:3.14-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY pyproject.toml ./
# COPY README.md ./  # Uncomment if you want to include it

# Install deps
RUN pip install --no-cache-dir --upgrade pip uv \
    && uv pip install --system .

FROM python:3.14-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libfreetype6 \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY . .

EXPOSE 1234
CMD ["python", "main.py"]
