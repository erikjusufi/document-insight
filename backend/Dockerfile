FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libxcb1 \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./

ENV PYTHONUNBUFFERED=1

FROM base AS prod

RUN uv sync --frozen --no-dev

COPY backend/ ./

RUN uv run python -m ensurepip --upgrade \
  && uv run python -m pip install --upgrade pip \
  && uv run python -m spacy download en_core_web_sm \
  && uv run python -m spacy download hr_core_news_sm

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dev

RUN uv sync --frozen --dev

COPY backend/ ./

RUN uv run python -m ensurepip --upgrade \
  && uv run python -m pip install --upgrade pip \
  && uv run python -m spacy download en_core_web_sm \
  && uv run python -m spacy download hr_core_news_sm

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
