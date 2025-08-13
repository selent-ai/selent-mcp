FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv for fast Python package management
RUN pip install uv

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Copy source code first (needed for build)
COPY selent_mcp/ ./selent_mcp/

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ARG SELENT_API_BASE_URL=https://backend.selent.ai
ENV SELENT_API_BASE_URL=${SELENT_API_BASE_URL}

EXPOSE 8000

# Run the MCP server
CMD ["uv", "run", "python", "-m", "selent_mcp.main"] 