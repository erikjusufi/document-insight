# AI-driven Document Insight Service

This repository contains a local, end‑to‑end document insight system:
- Upload PDFs or images
- Extract text (PyMuPDF + OCR fallback)
- Retrieve relevant context (FAISS + embeddings)
- Answer questions with local QA models
- Extract named entities
- JWT‑protected API + Vue UI

---

## 1) Setup Instructions (Manual)

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`
Backend default URL: `http://127.0.0.1:8000`

---

## 2) Docker (coming next)

Docker is available for the whole app (backend + frontend).

```bash
docker compose up --build
```

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- Redis: `localhost:6379` (container name `redis`)
- spaCy models are baked into the backend image (`en_core_web_sm`, `hr_core_news_sm`).
- Frontend container is built with `VITE_API_BASE_URL=http://localhost:8000`.

---

## 3) Example API Requests

### Register
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"secret123"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"secret123"}'
```

### Upload
```bash
curl -X POST http://127.0.0.1:8000/upload \
  -H 'Authorization: Bearer <TOKEN>' \
  -F 'files=@/path/to/sample.pdf'
```

### Extract
```bash
curl -X POST http://127.0.0.1:8000/documents/1/extract \
  -H 'Authorization: Bearer <TOKEN>'
```

### Search
```bash
curl -X POST http://127.0.0.1:8000/documents/1/search \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"query":"invoice total","top_k":3,"min_score":0,"offset":0}'
```

### Ask
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"document_id":1,"question":"What is the total?","top_k":3}'
```

### Entities
```bash
curl -X GET http://127.0.0.1:8000/documents/1/entities \
  -H 'Authorization: Bearer <TOKEN>'
```

---

## 4) Approach Summary

**Text extraction**
- PyMuPDF for PDFs, OCR fallback for scanned pages/images.

**Retrieval**
- Chunk text deterministically, embed chunks with SentenceTransformers.
- FAISS for semantic retrieval.
- Redis cache for embeddings.

**QA**
- Local extractive QA with `deepset/xlm-roberta-large-squad2` (best) or DistilBERT QA.
  - Set `QA_MODEL_PRESET=distilbert` to switch to `distilbert-base-cased-distilled-squad`.
  - Override with `QA_MODEL_NAME` for a custom model.

**NER**
- spaCy models by language, chosen from detected doc language.

---

## 5) Sample Documents

Sample PDFs are stored under:
```
backend/storage/
```

---

## 6) Notes

- spaCy models must be installed manually (per language).
- Redis should be running to enable embedding cache.

---

## 7) Frontend

See `frontend/README.md` for Vue setup and usage.
