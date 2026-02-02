# Document Insight Frontend (Vue)

This frontend connects to the FastAPI backend and exposes the full workflow:
register → login → upload → extract → search → ask.

## 1) Prerequisites

- Node.js 18+ (recommended)
- Running backend at `http://127.0.0.1:8000`

## 2) Install

From the repo root:

```bash
cd frontend
npm install
```

## 3) Configure API base URL

By default, the UI points to `http://127.0.0.1:8000`.
To override it, create a `.env` file in `frontend/`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 4) Run the app

```bash
npm run dev
```

Then open the URL shown by Vite (usually `http://localhost:5173`).

## 5) Workflow in the UI

1) **Authentication**
   - Register and login.
   - A JWT token is saved in local storage and used automatically.

2) **Upload**
   - Select one or more files and upload.
   - The response returns document IDs you will use in the next steps.

3) **Extract (required before Ask)**
   - Provide the `document_id` and run extraction.
   - Extraction runs asynchronously with a progress modal.

4) **Search**
   - Search within a document for top-k chunks/snippets.

5) **Ask**
   - Choose a QA model (Best / DistilBERT).
   - Ask a question and receive the answer, confidence, sources, and entities.
   - Ask runs asynchronously with a progress modal.

## 6) Files and structure

- `src/App.vue`: main UI and API calls
- `src/lib/api.js`: fetch wrapper and endpoints
- Styling is embedded in `src/App.vue`.

## 7) Troubleshooting

- If you see CORS errors, ensure the backend is running on the same host or
  configure CORS on the backend.
- If `/ask` returns empty answers, ensure extraction has been run.

## 8) Production build

```bash
npm run build
npm run preview
```
