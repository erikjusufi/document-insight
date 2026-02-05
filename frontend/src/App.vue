<template>
  <div class="app">
    <div class="container">
      <header class="hero">
        <div class="badge">Document Insight UI</div>
        <h1>Document Insight Service</h1>
        <p>
          Upload documents, extract text, search snippets, and ask questions using the local AI
          pipeline. This UI talks directly to the FastAPI backend.
        </p>
        <div class="meta">
          <span>API Base URL</span>
          <strong>{{ apiBaseUrl }}</strong>
        </div>
      </header>

      <main class="grid">
      <div class="row three">
        <section class="panel one-third">
        <header>
          <h2>Authentication</h2>
          <p>Sign in to access your documents.</p>
        </header>
        <div class="field">
          <label>Email</label>
          <input v-model="auth.email" type="email" placeholder="you@example.com" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="auth.password" type="password" placeholder="********" />
        </div>
        <div class="actions">
          <button @click="handleRegister" :disabled="busy.auth">Register</button>
          <button class="secondary" @click="handleLogin" :disabled="busy.auth">
            Login
          </button>
          <button class="ghost" @click="handleMe" :disabled="busy.auth || !token">
            Fetch Profile
          </button>
          <button class="ghost" @click="clearToken">Logout</button>
        </div>
        <div class="status" v-if="token">Token saved locally.</div>
        <pre class="output compact" v-if="authOutput">{{ authOutput }}</pre>
        </section>

        <section class="panel one-third">
        <header>
          <h2>Upload Documents</h2>
          <p>Upload PDFs or images for analysis.</p>
        </header>
        <div class="field">
          <label>Files (PDF or images)</label>
          <input type="file" multiple @change="onFilesSelected" />
        </div>
        <div class="actions">
          <button @click="handleUpload" :disabled="busy.upload || !token || !files.length">
            Upload
          </button>
        </div>
        <div class="status" v-if="documentLibrary.length">
          {{ documentLibrary.length }} documents in your library.
        </div>
        <pre class="output" v-if="uploadOutput">{{ uploadOutput }}</pre>
        </section>

        <section class="panel one-third">
        <header>
          <h2>Extract Text</h2>
          <p>Run extraction before asking questions.</p>
        </header>
        <div class="field">
          <label>Document</label>
          <select v-model="extract.documentId">
            <option value="">Select a document</option>
            <option v-for="doc in documentLibrary" :key="doc.id" :value="doc.id">
              {{ formatDocumentLabel(doc) }}
            </option>
          </select>
        </div>
        <div class="actions">
          <button
            @click="handleExtract"
            :disabled="busy.extract || !token || !extract.documentId"
          >
            Extract
          </button>
        </div>
        <pre class="output" v-if="extractOutput">{{ extractOutput }}</pre>
        </section>
      </div>

      <section class="panel wide">
        <header>
          <h2>Document Library</h2>
          <p>All sample and uploaded PDFs for this account.</p>
        </header>
        <div class="actions">
          <button class="ghost" @click="handleRefreshDocuments" :disabled="!token || busy.library">
            Refresh List
          </button>
        </div>
        <div class="hint" v-if="libraryError">
          Library refresh failed: {{ libraryError }}
        </div>
        <div class="table-wrap" v-if="documentLibrary.length">
          <table class="doc-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Size</th>
                <th>Type</th>
                <th>Extraction</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in documentLibrary" :key="doc.id">
                <td>#{{ doc.id }}</td>
                <td>{{ doc.filename }}</td>
                <td>{{ formatSize(doc.size_bytes) }}</td>
                <td>{{ doc.content_type }}</td>
                <td>
                  <span class="pill" :class="{ ready: isExtracted(doc) }">
                    {{ doc.extraction_status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="status" v-else-if="token">No documents yet.</div>
      </section>

      <section class="panel wide ask-panel">
        <header>
          <h2>Ask a Question</h2>
          <p>Answer questions using your selected QA model.</p>
        </header>
        <div class="field">
          <label>Document</label>
          <select v-model="ask.documentId">
            <option value="">Select an extracted document</option>
            <option v-for="doc in documentLibrary" :key="doc.id" :value="doc.id">
              {{ formatDocumentLabel(doc) }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>Question</label>
          <textarea v-model="ask.question" placeholder="Ask a question about the document"></textarea>
        </div>
        <div class="field">
          <label>Top K</label>
          <input v-model="ask.topK" type="number" min="1" />
        </div>
        <div class="field">
          <label>QA Model</label>
          <select v-model="ask.modelPreset">
            <option value="best">Best (XLM-R Large)</option>
            <option value="distilbert">DistilBERT (fast)</option>
          </select>
        </div>
        <div class="actions">
          <button
            @click="handleAsk"
            :disabled="busy.ask || !token || !canAsk"
          >
            Ask
          </button>
        </div>
        <div class="hint" v-if="!canAsk && ask.documentId">
          Extract the document before asking questions.
        </div>
        <div class="answer" v-if="askResponse">
          <div class="answer-head">
            <h3>Answer</h3>
            <span class="pill">Confidence {{ askResponse.confidence.toFixed(3) }}</span>
          </div>
          <p>{{ formatText(askResponse.answer) }}</p>
          <div class="sources" v-if="askResponse.sources.length">
            <h4>Sources</h4>
            <details class="source" v-for="(source, idx) in askResponse.sources" :key="idx">
              <summary>
                <span class="pill">Page {{ source.page_number }}</span>
                <span>View snippet</span>
              </summary>
              <p>{{ formatText(source.snippet) }}</p>
            </details>
          </div>
          <div class="entities" v-if="askResponse.entities.length">
            <h4>Entities</h4>
            <div class="entity" v-for="(entity, idx) in askResponse.entities" :key="idx">
              <span class="pill">{{ entity.label }}</span>
              <span>{{ entity.text }}</span>
            </div>
          </div>
        </div>
        <pre class="output compact" v-if="askOutput">{{ askOutput }}</pre>
      </section>

      <section class="panel wide">
        <header>
          <h2>Search Snippets</h2>
          <p>Search is a separate feature focused on snippet retrieval.</p>
        </header>
        <div class="field">
          <label>Document</label>
          <select v-model="search.documentId">
            <option value="">Select a document</option>
            <option v-for="doc in documentLibrary" :key="doc.id" :value="doc.id">
              {{ formatDocumentLabel(doc) }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>Query</label>
          <input v-model="search.query" placeholder="keyword or phrase" />
        </div>
        <div class="field">
          <label>Top K</label>
          <input v-model="search.topK" type="number" min="1" />
        </div>
        <div class="field">
          <label>Min Score</label>
          <input v-model="search.minScore" type="number" step="0.01" />
        </div>
        <div class="field">
          <label>Offset</label>
          <input v-model="search.offset" type="number" min="0" />
        </div>
        <div class="actions">
          <button @click="handleSearch" :disabled="busy.search || !token">Search</button>
        </div>
        <pre class="output" v-if="searchOutput">{{ searchOutput }}</pre>
      </section>
      </main>
    </div>

    <div class="modal" v-if="progress.visible">
      <div class="modal-card">
        <h3>{{ progress.title }}</h3>
        <p>{{ progress.message }}</p>
        <div class="progress">
          <div class="progress-bar" :style="{ width: `${progress.value}%` }"></div>
        </div>
        <div class="progress-meta">
          <span>{{ progress.stage || "working" }}</span>
          <strong>{{ progress.value }}%</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import {
  askQuestionAsync,
  extractDocumentAsync,
  getApiBaseUrl,
  getJobStatus,
  listDocuments,
  login,
  me,
  register,
  searchDocument,
  uploadFiles
} from "./lib/api";

const apiBaseUrl = getApiBaseUrl();
const token = ref(localStorage.getItem("token") || "");

const auth = ref({
  email: "",
  password: ""
});

const extract = ref({
  documentId: ""
});

const search = ref({
  documentId: "",
  query: "",
  topK: 3,
  minScore: 0,
  offset: 0
});

const ask = ref({
  documentId: "",
  question: "",
  topK: 3,
  modelPreset: "best"
});

const files = ref([]);
const documentLibrary = ref([]);
const extractedDocs = ref(new Set());

const authOutput = ref("");
const uploadOutput = ref("");
const extractOutput = ref("");
const searchOutput = ref("");
const askOutput = ref("");
const askResponse = ref(null);
const libraryError = ref("");

const progress = ref({
  visible: false,
  title: "",
  message: "",
  stage: "",
  value: 0
});

const busy = ref({
  auth: false,
  upload: false,
  extract: false,
  search: false,
  ask: false,
  library: false
});

const canAsk = computed(() => {
  if (!ask.value.documentId) return false;
  const selected = documentLibrary.value.find((doc) => doc.id === Number(ask.value.documentId));
  return selected?.extraction_status === "extracted" || extractedDocs.value.has(Number(ask.value.documentId));
});

function setOutput(target, data) {
  target.value = JSON.stringify(data, null, 2);
}

function onFilesSelected(event) {
  files.value = Array.from(event.target.files || []);
}

function clearToken() {
  token.value = "";
  documentLibrary.value = [];
  libraryError.value = "";
  localStorage.removeItem("token");
}

function formatText(text) {
  if (!text) return "";
  return text
    .replace(/[\u0000-\u001F\u007F]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return "";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

function isExtracted(document) {
  return document.extraction_status === "extracted" || extractedDocs.value.has(Number(document.id));
}

function formatDocumentLabel(document) {
  return `#${document.id} ${document.filename} (${formatSize(document.size_bytes)})`;
}

function markExtracted(documentId) {
  const id = Number(documentId);
  const next = new Set(extractedDocs.value);
  next.add(id);
  extractedDocs.value = next;
  documentLibrary.value = documentLibrary.value.map((doc) =>
    doc.id === id ? { ...doc, extraction_status: "extracted" } : doc
  );
}

function syncExtractedFromLibrary() {
  extractedDocs.value = new Set(
    documentLibrary.value
      .filter((doc) => doc.extraction_status === "extracted")
      .map((doc) => Number(doc.id))
  );
}

function mergeDocuments(nextDocs) {
  const byId = new Map(documentLibrary.value.map((doc) => [Number(doc.id), doc]));
  nextDocs.forEach((doc) => byId.set(Number(doc.id), doc));
  documentLibrary.value = Array.from(byId.values()).sort((a, b) => Number(b.id) - Number(a.id));
}

async function refreshDocuments() {
  if (!token.value) {
    documentLibrary.value = [];
    libraryError.value = "";
    return;
  }
  let response;
  try {
    response = await listDocuments(token.value);
  } catch (error) {
    if (error.status === 404) {
      libraryError.value = "Backend does not expose /documents yet. Restart backend to load latest routes.";
      return;
    }
    throw error;
  }
  documentLibrary.value = response;
  syncExtractedFromLibrary();
  libraryError.value = "";
  const ids = new Set(response.map((doc) => String(doc.id)));
  const fallbackId = response.length ? String(response[0].id) : "";

  if (!ids.has(String(extract.value.documentId))) {
    extract.value.documentId = fallbackId;
  }
  if (!ids.has(String(search.value.documentId))) {
    search.value.documentId = fallbackId;
  }
  if (!ids.has(String(ask.value.documentId))) {
    ask.value.documentId = fallbackId;
  }
}

async function pollJob(jobId, onComplete, onError) {
  const pollIntervalMs = 2000;
  let active = true;

  async function tick() {
    if (!active) return;
    try {
      const status = await getJobStatus(token.value, jobId);
      progress.value.stage = status.stage || "working";
      progress.value.value = status.progress || 0;
      if (status.status === "completed") {
        active = false;
        progress.value.visible = false;
        onComplete(status.result);
        return;
      }
      if (status.status === "failed") {
        active = false;
        progress.value.visible = false;
        if (onError) {
          onError(status.error || "Job failed");
        }
        return;
      }
    } catch (error) {
      active = false;
      progress.value.visible = false;
      if (onError) {
        onError(error.message);
      }
      return;
    }
    setTimeout(tick, pollIntervalMs);
  }

  tick();
}

async function handleRegister() {
  busy.value.auth = true;
  try {
    const response = await register({
      email: auth.value.email,
      password: auth.value.password
    });
    setOutput(authOutput, response);
  } catch (error) {
    setOutput(authOutput, { error: error.message });
  } finally {
    busy.value.auth = false;
  }
}

async function handleLogin() {
  busy.value.auth = true;
  try {
    const response = await login({
      email: auth.value.email,
      password: auth.value.password
    });
    token.value = response.access_token;
    localStorage.setItem("token", token.value);
    try {
      await refreshDocuments();
    } catch (error) {
      libraryError.value = error.message;
      setOutput(authOutput, {
        ...response,
        warning: `Login succeeded but document library refresh failed: ${error.message}`
      });
      return;
    }
    setOutput(authOutput, response);
  } catch (error) {
    setOutput(authOutput, { error: error.message });
  } finally {
    busy.value.auth = false;
  }
}

async function handleMe() {
  busy.value.auth = true;
  try {
    const response = await me(token.value);
    setOutput(authOutput, response);
  } catch (error) {
    setOutput(authOutput, { error: error.message });
  } finally {
    busy.value.auth = false;
  }
}

async function handleUpload() {
  busy.value.upload = true;
  try {
    const response = await uploadFiles(token.value, files.value);
    mergeDocuments(
      response.map((doc) => ({
        ...doc,
        pages_count: 0,
        chunks_count: 0,
        extraction_status: "pending"
      }))
    );
    try {
      await refreshDocuments();
      setOutput(uploadOutput, response);
    } catch (error) {
      libraryError.value = error.message;
      setOutput(uploadOutput, {
        uploaded: response,
        warning: `Upload succeeded but document library refresh failed: ${error.message}`
      });
    }
  } catch (error) {
    setOutput(uploadOutput, { error: error.message });
  } finally {
    busy.value.upload = false;
  }
}

async function handleExtract() {
  busy.value.extract = true;
  progress.value = {
    visible: true,
    title: "Extracting text",
    message: "We are extracting and chunking the document.",
    stage: "queued",
    value: 0
  };
  try {
    const response = await extractDocumentAsync(token.value, extract.value.documentId);
    pollJob(
      response.job_id,
      (result) => {
        markExtracted(result.document_id);
        refreshDocuments().catch((error) => {
          libraryError.value = error.message;
        });
        setOutput(extractOutput, result);
      },
      (errorMessage) => setOutput(extractOutput, { error: errorMessage })
    );
  } catch (error) {
    progress.value.visible = false;
    setOutput(extractOutput, { error: error.message });
  } finally {
    busy.value.extract = false;
  }
}

async function handleSearch() {
  busy.value.search = true;
  try {
    const response = await searchDocument(token.value, search.value.documentId, {
      query: search.value.query,
      top_k: Number(search.value.topK),
      min_score: Number(search.value.minScore),
      offset: Number(search.value.offset)
    });
    setOutput(searchOutput, response);
  } catch (error) {
    setOutput(searchOutput, { error: error.message });
  } finally {
    busy.value.search = false;
  }
}

async function handleAsk() {
  busy.value.ask = true;
  progress.value = {
    visible: true,
    title: "Answering question",
    message: "Retrieving context and running the QA model.",
    stage: "queued",
    value: 0
  };
  askResponse.value = null;
  try {
    const response = await askQuestionAsync(token.value, {
      document_id: Number(ask.value.documentId),
      question: ask.value.question,
      top_k: Number(ask.value.topK),
      model_preset: ask.value.modelPreset
    });
    pollJob(
      response.job_id,
      (result) => {
        askResponse.value = result;
        setOutput(askOutput, result);
      },
      (errorMessage) => setOutput(askOutput, { error: errorMessage })
    );
  } catch (error) {
    progress.value.visible = false;
    setOutput(askOutput, { error: error.message });
  } finally {
    busy.value.ask = false;
  }
}

async function handleRefreshDocuments() {
  busy.value.library = true;
  try {
    await refreshDocuments();
  } catch (error) {
    libraryError.value = error.message;
  } finally {
    busy.value.library = false;
  }
}

onMounted(() => {
  if (token.value) {
    refreshDocuments().catch((error) => {
      documentLibrary.value = [];
      libraryError.value = error.message;
    });
  }
});
</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap");

:root {
  color-scheme: dark;
}

body {
  margin: 0;
  font-family: "Space Grotesk", system-ui, -apple-system, sans-serif;
  background: #0e0f12;
  color: #f3f1ee;
}

.app {
  min-height: 100vh;
  background: radial-gradient(circle at top, #1b1c22 0%, #111317 60%, #0b0c0f 100%);
  padding: 40px 20px 80px;
}

.container {
  max-width: 980px;
  margin: 0 auto;
}

.hero {
  width: 100%;
  margin: 0 0 40px;
  padding: 32px 36px;
  background: #191b20;
  color: #f3f1ee;
  border-radius: 24px;
  box-shadow: 0 35px 80px rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.hero h1 {
  font-size: 44px;
  margin: 16px 0 8px;
}

.hero p {
  margin: 0 0 18px;
  opacity: 0.85;
}

.badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f4b15d;
  color: #20150a;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-size: 12px;
}

.meta {
  display: flex;
  gap: 12px;
  align-items: center;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 14px;
}

.grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.row {
  display: grid;
  gap: 24px;
  width: 100%;
}

.row.three {
  grid-template-columns: repeat(3, 1fr);
}

.panel {
  background: #17191e;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  gap: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  width: 100%;
}

.panel:hover {
  transform: translateY(-4px);
  box-shadow: 0 26px 70px rgba(0, 0, 0, 0.6);
  border-color: rgba(244, 177, 93, 0.35);
}

.panel.wide {
  grid-column: 1 / -1;
}

.panel header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #fdf7f0;
}

.panel header p {
  margin: 4px 0 0;
  color: #a7a7ad;
  font-size: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-size: 13px;
  font-weight: 700;
  color: #c5c5cb;
}

input,
textarea,
select {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  background: #0f1115;
  color: #f3f1ee;
}

input::placeholder,
textarea::placeholder {
  color: #8f929b;
}

select {
  color: #f3f1ee;
}

select option {
  color: #14161b;
  background: #f1ede7;
}

textarea {
  min-height: 90px;
  resize: vertical;
}

.ask-panel textarea {
  min-height: 140px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

button {
  border: none;
  background: #f4b15d;
  color: #20150a;
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 10px 24px rgba(244, 177, 93, 0.25);
}

button.secondary {
  background: #2b2f36;
  color: #f4b15d;
  box-shadow: none;
}

button.ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #d1d1d7;
  box-shadow: none;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.status {
  font-size: 13px;
  color: #70d67a;
  font-weight: 600;
}

.output {
  background: #0c0d10;
  color: #e4e1de;
  padding: 12px;
  border-radius: 12px;
  font-size: 12px;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.06);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
}

.output.compact {
  max-height: 120px;
}
.table-wrap {
  overflow-x: auto;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;
  background: #0f1115;
}

.doc-table th,
.doc-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  font-size: 13px;
}

.doc-table th {
  color: #c5c5cb;
  font-weight: 700;
  background: #13161c;
}

.doc-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

.pill {
  background: #f4b15d;
  color: #20150a;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.pill.ghost {
  background: rgba(255, 255, 255, 0.08);
  color: #e3e1dd;
}

.pill.ready {
  background: #2a8b4a;
  color: #f4f4f4;
}

.answer {
  background: #0f1115;
  padding: 18px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.answer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sources,
.entities {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source {
  background: #14161b;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.source summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  list-style: none;
}

.source summary::-webkit-details-marker {
  display: none;
}

.entity {
  display: flex;
  gap: 8px;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: #f4b15d;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(7, 8, 10, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 20;
}

.modal-card {
  background: #17191e;
  border-radius: 20px;
  padding: 24px;
  width: min(420px, 100%);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.progress {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
  height: 10px;
  margin-top: 12px;
}

.progress-bar {
  height: 10px;
  background: linear-gradient(90deg, #f4b15d, #ef7c2c);
  transition: width 0.3s ease;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: #a7a7ad;
}

@media (max-width: 840px) {
  .row.three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .row.three {
    grid-template-columns: 1fr;
  }

  .hero {
    padding: 24px;
  }

  .hero h1 {
    font-size: 30px;
  }
}

</style>
