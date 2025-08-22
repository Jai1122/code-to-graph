FROM python:3.10-slim

LABEL maintainer="CodeToGraph Team"
LABEL description="Scalable repository analysis and graph database system"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Java (required for Joern)
RUN apt-get update && apt-get install -y default-jdk && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

# Copy requirements files
COPY requirements.txt requirements-core.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and setup files
COPY src/ ./src/
COPY config/ ./config/
COPY setup.py ./
COPY README.md ./

# Install the package
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data /app/cache /app/logs /app/tmp /app/repos

# NOTE: Joern is NOT installed in the image anymore.
# Instead, mount it from the host at runtime:
#   docker run -v ~/joern:/opt/joern my-image

ENV PATH=$PATH:/opt/joern/bin
ENV PYTHONPATH=/app/src

# Create non-root user
RUN useradd --create-home --shell /bin/bash code-to-graph
RUN chown -R code-to-graph:code-to-graph /app
USER code-to-graph

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["code-to-graph", "--help"]
