# Backend

## Auth

- Passwords must be 8–72 characters (bcrypt limit).

## Runtime Configuration

- `DATABASE_URL` (default: `sqlite:///./app.db`)
- `SECRET_KEY` (default: `dev-secret`)
- `JWT_ALGORITHM` (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: `60`)
- `STORAGE_DIR` (default: `./storage`)
- `OCR_LANGUAGES` (default: `["en", "hr"]`)
- `OCR_MIN_TEXT_LENGTH` (default: `100`)
- `QA_MODEL_PRESET` (default: `best`, options: `best`, `distilbert`)
- `QA_MODEL_NAME` (default: `deepset/xlm-roberta-large-squad2`)
- `QA_DISTILBERT_MODEL_NAME` (default: `distilbert-base-cased-distilled-squad`)
- `QA_LOAD_ON_STARTUP` (default: `true`)
- `QA_TOP_K` (default: `10`)
- `QA_MAX_CONTEXT_CHARS` (default: `4000`)
- `EMBEDDING_MODEL_NAME` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `FAISS_INDEX_DIR` (default: `./storage/faiss`)
- `REDIS_URL` (default: `redis://localhost:6379/0`)
- `NER_DEFAULT_MODEL` (default: `en_core_web_sm`)
- `NER_MODEL_MAP` (default: `{"en": "en_core_web_sm", "hr": "hr_core_news_sm"}`)

## Schema Notes

- If `document_chunks` gains new columns, defaults are added and offsets are backfilled
  from `document_pages` when possible.
- Re-run `/documents/{document_id}/extract` to rebuild precise chunk offsets.

## NER Models

- English: `uv run python -m spacy download en_core_web_sm`
- Croatian: `uv run python -m spacy download hr_core_news_sm`

## Async Jobs

- `POST /documents/{id}/extract/async` returns a job id.
- `POST /ask/async` returns a job id (supports `model_preset`).
- `GET /jobs/{job_id}` returns job status + result.

## Developer Notes

- Install dev tooling (pytest, etc.): `uv sync --extra dev`
