# NeoMigrations - Enterprise Migration Service with Flyway
# Production-ready migration orchestration

# Use official Flyway image as base
FROM flyway/flyway:10.21.0-alpine AS flyway-base

# Build Python application layer
FROM python:3.12-slim

# Copy Flyway from official image
COPY --from=flyway-base /flyway /flyway

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for flyway command
RUN ln -s /flyway/flyway /usr/local/bin/flyway \
    && chmod +x /usr/local/bin/flyway

# Flyway configuration is now generated dynamically by the migration engine

# Create app directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY flyway/ ./flyway/
COPY orchestrator/ ./orchestrator/
COPY scripts/ ./scripts/

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user for security
RUN groupadd -r neo && useradd -r -g neo neo \
    && chown -R neo:neo /app
USER neo

# Default command
CMD ["python", "orchestrator/migration_manager.py"]