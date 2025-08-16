# NeoMultiTenant Deployment API
FROM flyway/flyway:10.21.0-alpine AS flyway-base

FROM python:3.12-slim

WORKDIR /app

# Copy Flyway from the official image
COPY --from=flyway-base /flyway /flyway

# Install system dependencies including Java for Flyway
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Make Flyway accessible
RUN ln -s /flyway/flyway /usr/local/bin/flyway && \
    chmod +x /usr/local/bin/flyway

# Copy requirements
COPY migrations/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional API dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    httpx==0.26.0 \
    requests==2.31.0 \
    aiohttp==3.9.1

# Copy application code
COPY migrations/api /app/api
COPY migrations/orchestrator /app/orchestrator
COPY migrations/flyway /app/flyway
COPY scripts /app/scripts

# Make scripts executable
RUN find /app/scripts -name "*.sh" -type f -exec chmod +x {} \;

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "api.deployment_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]