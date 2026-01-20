FROM python:3.14-slim

WORKDIR /app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 1. Set the environment path OUTSIDE /app so the volume mount doesn't hide it
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
# 2. Add that environment to the global PATH
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application into the container.
COPY . /app

# Install dependencies using uv
RUN uv sync --frozen --no-cache

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]