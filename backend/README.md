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
- `QA_MODEL_NAME` (default: `deepset/xlm-roberta-large-squad2`)
- `QA_LOAD_ON_STARTUP` (default: `true`)
- `QA_TOP_K` (default: `10`)
- `QA_MAX_CONTEXT_CHARS` (default: `4000`)
- `EMBEDDING_MODEL_NAME` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `FAISS_INDEX_DIR` (default: `./storage/faiss`)
- `REDIS_URL` (default: `redis://localhost:6379/0`)

## Schema Notes

- If `document_chunks` schema changes, existing chunk rows may be dropped on startup.
- Re-run `/documents/{document_id}/extract` to rebuild chunks.
