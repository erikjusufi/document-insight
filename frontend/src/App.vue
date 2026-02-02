<template>
  <div class="app">
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
      <section class="panel wide ask-panel">
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
        <pre class="output" v-if="authOutput">{{ authOutput }}</pre>
      </section>

      <section class="panel">
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
        <div class="list" v-if="uploadedDocs.length">
          <div class="list-item" v-for="doc in uploadedDocs" :key="doc.id">
            <div>
              <strong>#{{ doc.id }}</strong> — {{ doc.filename }}
              <span class="pill">{{ doc.language || "unknown" }}</span>
            </div>
            <span class="pill" :class="{ ready: isExtracted(doc.id) }">
              {{ isExtracted(doc.id) ? "Extracted" : "Needs extraction" }}
            </span>
          </div>
        </div>
        <pre class="output" v-if="uploadOutput">{{ uploadOutput }}</pre>
      </section>

      <section class="panel">
        <header>
          <h2>Extract Text</h2>
          <p>Run extraction before asking questions.</p>
        </header>
        <div class="field">
          <label>Document ID</label>
          <input v-model="extract.documentId" type="number" min="1" />
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

      <section class="panel">
        <header>
          <h2>Ask a Question</h2>
          <p>Answer questions using your selected QA model.</p>
        </header>
        <div class="field">
          <label>Document ID</label>
          <input v-model="ask.documentId" type="number" min="1" />
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
            <div class="source" v-for="(source, idx) in askResponse.sources" :key="idx">
              <span class="pill">Page {{ source.page_number }}</span>
              <p>{{ formatText(source.snippet) }}</p>
            </div>
          </div>
          <div class="entities" v-if="askResponse.entities.length">
            <h4>Entities</h4>
            <div class="entity" v-for="(entity, idx) in askResponse.entities" :key="idx">
              <span class="pill">{{ entity.label }}</span>
              <span>{{ entity.text }}</span>
            </div>
          </div>
        </div>
        <pre class="output" v-if="askOutput">{{ askOutput }}</pre>
      </section>

      <section class="panel wide">
        <header>
          <h2>Search Snippets</h2>
          <p>Search is a separate feature focused on snippet retrieval.</p>
        </header>
        <div class="field">
          <label>Document ID</label>
          <input v-model="search.documentId" type="number" min="1" />
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
import { computed, ref } from "vue";
import {
  askQuestionAsync,
  extractDocumentAsync,
  getApiBaseUrl,
  getJobStatus,
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
const uploadedDocs = ref([]);
const extractedDocs = ref(new Set());

const authOutput = ref("");
const uploadOutput = ref("");
const extractOutput = ref("");
const searchOutput = ref("");
const askOutput = ref("");
const askResponse = ref(null);

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
  ask: false
});

const canAsk = computed(() => {
  if (!ask.value.documentId) return false;
  return extractedDocs.value.has(Number(ask.value.documentId));
});

function setOutput(target, data) {
  target.value = JSON.stringify(data, null, 2);
}

function onFilesSelected(event) {
  files.value = Array.from(event.target.files || []);
}

function clearToken() {
  token.value = "";
  localStorage.removeItem("token");
}

function formatText(text) {
  if (!text) return "";
  return text
    .replace(/[\u0000-\u001F\u007F]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function markExtracted(documentId) {
  const next = new Set(extractedDocs.value);
  next.add(Number(documentId));
  extractedDocs.value = next;
}

function isExtracted(documentId) {
  return extractedDocs.value.has(Number(documentId));
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
    uploadedDocs.value = response;
    setOutput(uploadOutput, response);
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
</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap");

:root {
  color-scheme: light;
}

body {
  margin: 0;
  font-family: "Space Grotesk", system-ui, -apple-system, sans-serif;
  background: #f5f1ec;
  color: #1f1a15;
}

.app {
  min-height: 100vh;
  background: radial-gradient(circle at top, #f9f6f1 0%, #f2ebe3 60%, #efe6dc 100%);
  padding: 40px 20px 80px;
}

.hero {
  max-width: 980px;
  margin: 0 auto 40px;
  padding: 32px 36px;
  background: #1f1a15;
  color: #f8f3ed;
  border-radius: 24px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.2);
}

.hero h1 {
  font-size: 40px;
  margin: 16px 0 8px;
}

.hero p {
  margin: 0 0 18px;
  opacity: 0.9;
}

.badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f6b76b;
  color: #2c1606;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-size: 12px;
}

.meta {
  display: flex;
  gap: 12px;
  align-items: center;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 14px;
}

.grid {
  max-width: 980px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.panel {
  background: #fffaf4;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 16px 40px rgba(31, 26, 21, 0.12);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel.wide {
  grid-column: 1 / -1;
}

.panel header h2 {
  margin: 0;
  font-size: 22px;
}

.panel header p {
  margin: 4px 0 0;
  color: #6b5b4f;
  font-size: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-size: 13px;
  font-weight: 600;
  color: #5b4a3f;
}

input,
textarea,
select {
  border: 1px solid #e2d7cc;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  background: #fff;
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
  background: #1f1a15;
  color: #fff;
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
}

button.secondary {
  background: #f6b76b;
  color: #2c1606;
}

button.ghost {
  background: transparent;
  border: 1px solid #d8c9bc;
  color: #4d3f34;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status {
  font-size: 13px;
  color: #2e7d32;
  font-weight: 600;
}

.output {
  background: #12100e;
  color: #f8f3ed;
  padding: 12px;
  border-radius: 12px;
  font-size: 12px;
  overflow-x: auto;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: #f3e7da;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
}

.pill {
  background: #f6b76b;
  color: #2c1606;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.pill.ready {
  background: #2e7d32;
  color: #fff;
}

.answer {
  background: #f3e7da;
  padding: 16px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  background: #fff;
  padding: 10px 12px;
  border-radius: 12px;
}

.entity {
  display: flex;
  gap: 8px;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: #b45309;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 12, 10, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 20;
}

.modal-card {
  background: #fffaf4;
  border-radius: 20px;
  padding: 24px;
  width: min(420px, 100%);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
}

.progress {
  background: #eadfd4;
  border-radius: 999px;
  overflow: hidden;
  height: 10px;
  margin-top: 12px;
}

.progress-bar {
  height: 10px;
  background: linear-gradient(90deg, #f6b76b, #ec7c2d);
  transition: width 0.3s ease;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: #6b5b4f;
}

@media (max-width: 720px) {
  .hero {
    padding: 24px;
  }

  .hero h1 {
    font-size: 30px;
  }
}
</style>
