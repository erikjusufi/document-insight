# Development Plan & Rules

This document defines the development strategy, milestones, and rules for the
AI-driven Document Insight Service project.

The goal is to build the system incrementally using best practices:
small changes, strong tests, clear architecture, and production-oriented decisions.

---

## How to Work on This Project (Strict)

- Work on **one milestone at a time**
- Do **not** implement parts of future milestones early
- Prefer the **simplest possible implementation** that satisfies requirements
- Avoid refactoring unrelated code
- If unsure, implement the minimal version and leave TODO comments
- Heavy operations (OCR, models, embeddings) must be mockable in tests

---

## 1. Project Goals

### Functional Goals
- Upload PDF and image documents
- Extract text using:
  - PyMuPDF (primary)
  - OCR fallback (EasyOCR)
- Ask natural language questions over uploaded documents
- Return:
  - answers
  - confidence
  - document insight (sources, page numbers, snippets)
- Fully local AI stack (no external APIs)
- JWT-based user authentication
- Dockerized backend + frontend
- CI with GitHub Actions

### Non-Goals (Explicitly Out of Scope)
- No paid LLM APIs
- No GPU requirements
- No full-text search engine (Elasticsearch, etc.)
- No multi-tenant enterprise permissions
- No frontend E2E testing (initially)

---

## 2. Development Rules (Must-Follow)

### General Rules
- Implement features in **small, modular increments**
- Every increment must:
  - be testable
  - include pytest tests that fail before the change and pass after
  - keep CI green
- Prefer clarity over cleverness
- Avoid premature optimization

### Code Structure Rules
- FastAPI routers must be thin
- Business logic goes into `services/`
- Persistence logic goes into `db/repos/`
- Heavy components (OCR, QA, retrieval) must be behind interfaces
- No model loading inside request handlers

### Testing Rules
- Pytest is mandatory for every feature
- Unit tests first
- Heavy components MUST be mocked in tests:
  - OCR
  - QA models
  - embeddings
- Tests must be fast and deterministic
- Integration tests may be added later

---

## 3. Milestone-Based Development Plan

Each milestone must be fully completed, tested, and committed
before moving to the next milestone.

---

### Milestone 0 — Baseline Infrastructure
**Goal:** runnable app + CI

- App boots
- `/health` endpoint
- Settings via env
- Logging configured
- CI runs pytest

Tests:
- health endpoint returns OK

---

### Milestone 1 — User Management (JWT)
**Goal:** authentication & authorization

Features:
- User registration
- Login (JWT)
- Protected endpoints
- Password hashing

Endpoints:
- POST /auth/register
- POST /auth/login
- GET /auth/me

Tests:
- register/login success
- login failure cases
- protected route requires token

---

### Milestone 2 — Document Upload & Persistence
**Goal:** reliable document ingestion

Features:
- Upload multiple PDFs/images
- JWT-protected
- Store files on disk
- Store metadata in DB

Endpoints:
- POST /upload

Tests:
- auth required
- files saved
- metadata persisted

---

### Milestone 3 — Text Extraction (PyMuPDF)
**Goal:** extract structured text

Features:
- Extract per-page text from PDFs
- Chunk text deterministically
- Store page-to-text mapping

Tests:
- extraction returns known text from sample PDF
- chunking is stable and deterministic

---

### Milestone 4 — OCR Engine
**Goal:** handle scanned documents & images

Features:
- OCR standalone images
- OCR scanned PDF pages
- Fallback policy:
  - PyMuPDF first
  - OCR if text is empty or too short

Tests:
- image OCR path
- OCR fallback triggered on empty page

---

### Milestone 5 — Retrieval Engine (Baseline)
**Goal:** find relevant text chunks

Features:
- Chunk-level retrieval
- TF-IDF or similar local scoring
- Top-k selection

Tests:
- retrieval returns chunk containing expected keywords

---

### Milestone 6 — QA Engine (Local, Extractive)
**Goal:** answer questions with insight

Features:
- Local QA model (DistilBERT or similar)
- Model loaded once at startup
- `/ask` endpoint
- Return:
  - answer
  - confidence
  - sources (doc, page, snippet)

Tests:
- QA pipeline works on known fixture text
- sources map to correct page

---

## 4. Enhancements (Implemented Sequentially)

### Enhancement A — RAG with FAISS
- Embedding-based retrieval
- FAISS index per user or document
- Replace baseline retrieval

Tests:
- embeddings created
- FAISS returns correct chunk

---

### Enhancement B — Redis Embedding Cache
- Cache embeddings by content hash
- Skip recomputation on repeated uploads

Tests:
- cache hit vs miss behavior

---

### Enhancement C — Named Entity Recognition (NER)
- spaCy-based NER
- Extract entities from text
- Return entities in API responses

Tests:
- entities extracted from known text

---

## 5. PR Size & Workflow Rules

Each PR must:
- Implement **one logical step only**
- Be reviewable in under 15 minutes
- Contain:
  - code
  - tests
  - passing CI

---

## 6. TechAssignment Delivery Checklist

Remaining delivery requirements from the TechAssignment PDF must be completed
after Enhancements A–C:

- Dockerize the application (backend + frontend).
- Add sample/dummy documents to the repo for testing.
- Create a root README that includes:
  - setup instructions
  - manual installation + Docker instructions
  - example API requests/responses
  - brief approach and model/tool choices
  - optional screenshots or demo notes

Work on these items in small, reviewable increments.

---

## 7. Deployment + UI Improvements (Planned)

Deployment additions:
- Production Docker setup (multi-stage builds, environment config).
- Optional reverse proxy (e.g., Nginx) and HTTPS termination.
- Optional process manager (systemd) for non-container deployment.

UI improvements (choose one or more):
- Gradio or Streamlit prototype (as suggested by the TechAssignment).
- Vue frontend enhancements for production (routing, state management, API error UX).
- Add static hosting guidance (Vite build + Nginx/Cloud storage).

Avoid:
- massive refactors
- unrelated cleanup
- mixing features

PR completion checklist:
- [ ] Feature implemented
- [ ] Tests added or updated
- [ ] `uv run pytest` passes
- [ ] CI passes
- [ ] Visual artifact included

---

## 6. Visual Checkpoints

Each PR must include **at least one visual artifact**, such as:
- Screenshot of Swagger UI endpoint
- Terminal output showing tests passing
- Diagram (ASCII or image) explaining flow
- Screenshot of Vue UI change

Images should be placed under:
docs/pr-assets/<milestone-name>/


Purpose:
- Easier discussion
- Faster debugging
- Better self-review
- Easier to ask questions when something feels off

---

## 7. When to Ask for Review or Explanation

Ask for review when:
- A test feels fragile
- A service boundary feels unclear
- Performance suddenly degrades
- An architectural decision is blocking progress
- You are unsure if complexity is justified

This document is the source of truth for development direction.
