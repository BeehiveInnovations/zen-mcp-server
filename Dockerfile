# Multi-stage build for Zen MCP Server
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash mcp

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/mcp/.local

# Copy application code
COPY --chown=mcp:mcp . .

# Create logs directory
RUN mkdir -p logs && chown -R mcp:mcp logs

# Switch to non-root user
USER mcp

# Add .local/bin to PATH
ENV PATH=/home/mcp/.local/bin:$PATH

# Set Python to run in unbuffered mode for real-time logging
ENV PYTHONUNBUFFERED=1

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the MCP server
CMD ["python", "server.py"]