# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the project files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the application code
COPY src/ ./src/
COPY fixtures/ ./fixtures/

# Set environment variables
ENV PYTHONPATH="/app/src:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1

# Command to run the application (assuming main.py is the entry point)
# Adjust if there's a specific CLI command
CMD ["uv", "run", "python", "-m", "nlqe.testing.cli", "--help"]
