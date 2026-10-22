# Job Hunter dashboard + search in one image (the search runs as a subprocess of the dashboard).
#   docker compose up --build         ->  http://localhost:8501
# The LLM is optional: without a key in .env every job gets the free heuristic score.
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Non-root; cv/, data/ and users/ are mounted from the host (docker-compose.yml)
RUN useradd --uid 1000 --create-home jobhunter \
    && mkdir -p cv data users \
    && chown -R jobhunter:jobhunter cv data users
USER jobhunter

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "dashboard.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
