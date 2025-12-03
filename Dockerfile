# Dockerfile optimized for Amazon Bedrock AgentCore Runtime
# Platform: ARM64 (required by AgentCore)
# Port: 8000 (default MCP server port)
# Endpoint: /mcp (required by AgentCore)

FROM --platform=linux/arm64 python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-openapi.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Uncomment if you need OpenAPI support
# RUN pip install --no-cache-dir -r requirements-openapi.txt

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Expose port 8000 (AgentCore requirement)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ping || exit 1

# Run with ADOT instrumentation for observability
# For production without observability, use: CMD ["python", "src/server.py"]
CMD ["opentelemetry-instrument", "python", "src/server.py"]
