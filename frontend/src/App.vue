<template>
  <div class="page">
    <header class="hero">
      <div class="tag">Document Insight UI</div>
      <h1>Document Insight Service</h1>
      <p>
        Upload documents, extract text, search snippets, and ask questions using the
        local AI pipeline. This UI talks directly to the FastAPI backend.
      </p>
      <div class="kv">
        <div>API Base URL</div>
        <div>{{ apiBaseUrl }}</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Authentication</h2>
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
          <button class="secondary" @click="handleMe" :disabled="busy.auth || !token">
            Fetch Profile
          </button>
          <button class="secondary" @click="clearToken">Logout</button>
        </div>
        <div class="status" v-if="token">Token saved locally.</div>
        <div class="output" v-if="authOutput">{{ authOutput }}</div>
      </div>

      <div class="card">
        <h2>Upload Documents</h2>
        <div class="field">
          <label>Files (PDF or images)</label>
          <input type="file" multiple @change="onFilesSelected" />
        </div>
        <div class="actions">
          <button @click="handleUpload" :disabled="busy.upload || !token || !files.length">
            Upload
          </button>
        </div>
        <div class="output" v-if="uploadOutput">{{ uploadOutput }}</div>
      </div>

      <div class="card">
        <h2>Extract Text</h2>
        <div class="field">
          <label>Document ID</label>
          <input v-model="extract.documentId" type="number" min="1" />
        </div>
        <div class="actions">
          <button @click="handleExtract" :disabled="busy.extract || !token || !extract.documentId">
            Extract
          </button>
        </div>
        <div class="output" v-if="extractOutput">{{ extractOutput }}</div>
      </div>

      <div class="card">
        <h2>Search Snippets</h2>
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
        <div class="output" v-if="searchOutput">{{ searchOutput }}</div>
      </div>

      <div class="card">
        <h2>Ask a Question</h2>
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
        <div class="actions">
          <button @click="handleAsk" :disabled="busy.ask || !token">Ask</button>
        </div>
        <div class="output" v-if="askOutput">{{ askOutput }}</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";
import {
  askQuestion,
  extractDocument,
  getApiBaseUrl,
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
  topK: 3
});

const files = ref([]);

const authOutput = ref("");
const uploadOutput = ref("");
const extractOutput = ref("");
const searchOutput = ref("");
const askOutput = ref("");

const busy = ref({
  auth: false,
  upload: false,
  extract: false,
  search: false,
  ask: false
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
    setOutput(uploadOutput, response);
  } catch (error) {
    setOutput(uploadOutput, { error: error.message });
  } finally {
    busy.value.upload = false;
  }
}

async function handleExtract() {
  busy.value.extract = true;
  try {
    const response = await extractDocument(token.value, extract.value.documentId);
    setOutput(extractOutput, response);
  } catch (error) {
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
  try {
    const response = await askQuestion(token.value, {
      document_id: Number(ask.value.documentId),
      question: ask.value.question,
      top_k: Number(ask.value.topK)
    });
    setOutput(askOutput, response);
  } catch (error) {
    setOutput(askOutput, { error: error.message });
  } finally {
    busy.value.ask = false;
  }
}
</script>
