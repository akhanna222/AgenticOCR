import contextlib
import io
import json
import os
import uuid
from typing import Any, Dict

from flask import Flask, Response, jsonify, request
from werkzeug.utils import secure_filename

from mortgage_core import (
    MORTGAGE_DOC_TYPES,
    classify_document,
    load_document_as_images,
    load_schema_for_doc_type,
    run_full_pipeline,
)

UPLOAD_FOLDER = "uploads"
SCHEMA_DIR = "schemas"
MODELS_FILE = "models.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCHEMA_DIR, exist_ok=True)

app = Flask(__name__)

DOC_STORE: Dict[str, str] = {}


def load_models() -> Dict[str, Any]:
    if not os.path.exists(MODELS_FILE):
        return {}
    with open(MODELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_models(models: Dict[str, Any]) -> None:
    with open(MODELS_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2)


def run_pipeline_with_logs(path: str, override_doc_type_id: str | None = None) -> Dict[str, Any]:
    log_buffer = io.StringIO()
    with contextlib.redirect_stdout(log_buffer):
        result = run_full_pipeline(path, override_doc_type_id=override_doc_type_id)
    logs_text = log_buffer.getvalue()
    logs = logs_text.splitlines()
    result["logs"] = logs
    return result


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Mortgage OCR Template Studio</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a;
      color: #e5e7eb;
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px 16px 64px;
    }
    .card {
      background: #020617;
      border-radius: 18px;
      padding: 20px;
      margin-bottom: 20px;
      border: 1px solid #1e293b;
      box-shadow: 0 18px 45px rgba(15,23,42,0.7);
    }
    h1 {
      font-size: 1.8rem;
      margin-bottom: 0.5rem;
    }
    h2 {
      font-size: 1.2rem;
      margin-top: 0;
      margin-bottom: 0.5rem;
    }
    .subtitle {
      color: #94a3b8;
      font-size: 0.95rem;
      margin-bottom: 1rem;
    }
    label {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 4px;
      color: #cbd5f5;
    }
    input[type="file"],
    input[type="text"],
    select,
    textarea {
      width: 100%;
      box-sizing: border-box;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid #1f2937;
      background: #020617;
      color: #e5e7eb;
      font-size: 0.9rem;
      outline: none;
    }
    input[type="file"] {
      padding: 6px;
      background: #020617;
    }
    textarea {
      min-height: 200px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      resize: vertical;
      white-space: pre;
      overflow-wrap: normal;
      overflow-x: auto;
    }
    .row {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }
    .col {
      flex: 1 1 0;
      min-width: 0;
    }
    .col-40 {
      flex-basis: 40%;
    }
    .col-60 {
      flex-basis: 60%;
    }
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 14px;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      background: linear-gradient(135deg, #22c55e, #0ea5e9);
      color: #0b1120;
      font-weight: 600;
      font-size: 0.9rem;
      margin-right: 8px;
      margin-top: 6px;
    }
    button.secondary {
      background: transparent;
      border: 1px solid #334155;
      color: #e5e7eb;
    }
    button:disabled {
      opacity: 0.5;
      cursor: default;
    }
    .tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #0f172a;
      border: 1px solid #1e293b;
      font-size: 0.75rem;
      color: #9ca3af;
      margin-right: 4px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(34,197,94,0.1);
      color: #bbf7d0;
      font-size: 0.75rem;
    }
    pre {
      background: #020617;
      border-radius: 10px;
      padding: 10px;
      font-size: 0.8rem;
      max-height: 300px;
      overflow: auto;
      border: 1px solid #1e293b;
    }
    .status {
      font-size: 0.85rem;
      color: #a5b4fc;
      margin-top: 4px;
    }
    .small {
      font-size: 0.8rem;
      color: #64748b;
    }
    code.inline {
      background: #020617;
      padding: 2px 6px;
      border-radius: 6px;
      border: 1px solid #1e293b;
      font-size: 0.78rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Mortgage OCR Template Studio</h1>
      <div class="subtitle">
        Upload a document → auto-classify → tweak template → run OCR → save as reusable HTTP model
        (e.g. <code class="inline">/api/bank_model</code>).
      </div>

      <div class="row">
        <div class="col col-40">
          <h2>1. Upload & Classify</h2>
          <label for="fileInput">Document (PDF / image)</label>
          <input id="fileInput" type="file" />
          <button id="uploadBtn">Upload &amp; classify</button>
          <div id="uploadStatus" class="status"></div>

          <div style="margin-top: 12px;">
            <div><span class="tag">doc_id</span> <span id="docId" class="small">–</span></div>
            <div style="margin-top: 4px;">
              <span class="tag">Classifier</span>
              <span id="classifierSummary" class="small">–</span>
            </div>
          </div>

          <div style="margin-top: 16px;">
            <label for="docTypeSelect">Detected template (you can change):</label>
            <select id="docTypeSelect"></select>
          </div>
        </div>

        <div class="col col-60">
          <h2>2. Edit Template</h2>
          <div class="small" style="margin-bottom: 6px;">
            This is the JSON schema that your OCR will fill. Edit &amp; click “Save template” to write
            to <code class="inline">./schemas/&lt;doc_type_id&gt;.json</code>.
          </div>
          <textarea id="schemaEditor" spellcheck="false"></textarea>
          <div>
            <button class="secondary" id="reloadSchemaBtn">Reload schema</button>
            <button id="saveTemplateBtn">Save template</button>
            <span id="templateStatus" class="status"></span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>3. Run OCR</h2>
      <div class="small">
        Uses your selected template + full JSON-mode OCR pipeline (multi-page, evaluation loop).
      </div>
      <button id="runOcrBtn">Run OCR on this document</button>
      <span id="ocrStatus" class="status"></span>

      <div class="row" style="margin-top: 16px;">
        <div class="col col-40">
          <h3 style="font-size: 1rem;">Logs</h3>
          <pre id="logsBox">–</pre>
        </div>
        <div class="col col-60">
          <h3 style="font-size: 1rem;">Final extracted JSON</h3>
          <pre id="outputBox">–</pre>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>4. Save as HTTP Model</h2>
      <div class="small">
        Freeze the selected template into a named model. After saving, you can call:
        <code class="inline">POST /api/&lt;model_name&gt;</code> with a file.
      </div>

      <div class="row" style="margin-top: 8px;">
        <div class="col col-40">
          <label for="modelNameInput">Model name (e.g. <code class="inline">bank_model</code>)</label>
          <input id="modelNameInput" type="text" placeholder="bank_model" />
          <button id="saveModelBtn">Save model</button>
          <span id="modelStatus" class="status"></span>
        </div>
        <div class="col col-60">
          <div class="small">
            Example <code class="inline">curl</code> (replace <code class="inline">localhost:5000</code> with your host):
          </div>
<pre id="curlExample">curl -X POST http://localhost:5000/api/bank_model \\
  -F "file=@/path/to/document.pdf"</pre>
        </div>
      </div>
    </div>
  </div>

  <script>
    const docTypeSelect   = document.getElementById("docTypeSelect");
    const schemaEditor    = document.getElementById("schemaEditor");
    const uploadBtn       = document.getElementById("uploadBtn");
    const runOcrBtn       = document.getElementById("runOcrBtn");
    const reloadSchemaBtn = document.getElementById("reloadSchemaBtn");
    const saveTemplateBtn = document.getElementById("saveTemplateBtn");
    const saveModelBtn    = document.getElementById("saveModelBtn");

    const uploadStatus    = document.getElementById("uploadStatus");
    const templateStatus  = document.getElementById("templateStatus");
    const ocrStatus       = document.getElementById("ocrStatus");
    const modelStatus     = document.getElementById("modelStatus");

    const docIdSpan       = document.getElementById("docId");
    const classifierSummary = document.getElementById("classifierSummary");
    const logsBox         = document.getElementById("logsBox");
    const outputBox       = document.getElementById("outputBox");
    const modelNameInput  = document.getElementById("modelNameInput");
    const curlExample     = document.getElementById("curlExample");

    let currentDocId = null;

    async function fetchDocTypes() {
      const res = await fetch("/api/doc-types");
      const data = await res.json();
      docTypeSelect.innerHTML = "";
      data.doc_types.forEach(dt => {
        const opt = document.createElement("option");
        opt.value = dt.id;
        opt.textContent = dt.id + " — " + dt.label;
        docTypeSelect.appendChild(opt);
      });
    }

    async function loadSchemaForSelected() {
      const docTypeId = docTypeSelect.value;
      if (!docTypeId) return;
      templateStatus.textContent = "Loading schema...";
      const res = await fetch("/api/schema/" + encodeURIComponent(docTypeId));
      if (!res.ok) {
        templateStatus.textContent = "Failed to load schema.";
        return;
      }
      const data = await res.json();
      schemaEditor.value = JSON.stringify(data.schema, null, 2);
      templateStatus.textContent = "Schema loaded.";
    }

    uploadBtn.addEventListener("click", async () => {
      const fileInput = document.getElementById("fileInput");
      const file = fileInput.files[0];
      if (!file) {
        uploadStatus.textContent = "Please choose a file first.";
        return;
      }
      uploadStatus.textContent = "Uploading & classifying...";
      logsBox.textContent = "–";
      outputBox.textContent = "–";

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const text = await res.text();
        uploadStatus.textContent = "Upload failed: " + text;
        return;
      }

      const data = await res.json();
      currentDocId = data.doc_id;
      docIdSpan.textContent = currentDocId;

      const cls = data.classification;
      classifierSummary.textContent = cls.doc_type_id + " (conf " + cls.confidence.toFixed(2) + ")";

      await fetchDocTypes();
      if (cls.doc_type_id) {
        docTypeSelect.value = cls.doc_type_id;
      }
      schemaEditor.value = JSON.stringify(data.schema, null, 2);
      uploadStatus.textContent = "Uploaded & classified.";
      templateStatus.textContent = "Schema loaded for " + cls.doc_type_id + ".";
    });

    reloadSchemaBtn.addEventListener("click", loadSchemaForSelected);

    saveTemplateBtn.addEventListener("click", async () => {
      const docTypeId = docTypeSelect.value;
      if (!docTypeId) {
        templateStatus.textContent = "Select a template first.";
        return;
      }
      let obj;
      try {
        obj = JSON.parse(schemaEditor.value);
      } catch (e) {
        templateStatus.textContent = "Schema is not valid JSON.";
        return;
      }
      templateStatus.textContent = "Saving template...";
      const res = await fetch("/api/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_type_id: docTypeId, schema: obj })
      });
      if (!res.ok) {
        const text = await res.text();
        templateStatus.textContent = "Template save failed: " + text;
        return;
      }
      templateStatus.textContent = "Template saved to ./schemas/" + docTypeId + ".json";
    });

    runOcrBtn.addEventListener("click", async () => {
      if (!currentDocId) {
        ocrStatus.textContent = "Upload a document first.";
        return;
      }
      const docTypeId = docTypeSelect.value;
      ocrStatus.textContent = "Running OCR...";
      logsBox.textContent = "";
      outputBox.textContent = "";

      const res = await fetch("/api/run-ocr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_id: currentDocId,
          doc_type_id: docTypeId || null
        })
      });
      if (!res.ok) {
        const text = await res.text();
        ocrStatus.textContent = "OCR failed: " + text;
        return;
      }
      const data = await res.json();
      ocrStatus.textContent = "OCR complete.";

      logsBox.textContent = (data.logs || []).join("\\n") || "No logs.";
      outputBox.textContent = JSON.stringify(data.extracted_final, null, 2);
    });

    saveModelBtn.addEventListener("click", async () => {
      const name = modelNameInput.value.trim();
      const docTypeId = docTypeSelect.value;
      if (!name) {
        modelStatus.textContent = "Enter a model name first.";
        return;
      }
      if (!docTypeId) {
        modelStatus.textContent = "Select a template first.";
        return;
      }
      modelStatus.textContent = "Saving model...";
      const res = await fetch("/api/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, doc_type_id: docTypeId })
      });
      if (!res.ok) {
        const text = await res.text();
        modelStatus.textContent = "Model save failed: " + text;
        return;
      }
      modelStatus.textContent = "Model saved as /api/" + name;
      curlExample.textContent = "curl -X POST http://localhost:5000/api/" + name + " \\\n  -F \"file=@/path/to/document.pdf\"";
    });

    fetchDocTypes().catch(console.error);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/api/doc-types", methods=["GET"])
def api_doc_types():
    items = [{"id": k, "label": v} for k, v in MORTGAGE_DOC_TYPES.items()]
    items.append({"id": "unknown", "label": "Unknown / generic template"})
    return jsonify({"doc_types": items})


@app.route("/api/schema/<doc_type_id>", methods=["GET"])
def api_schema(doc_type_id: str):
    schema = load_schema_for_doc_type(doc_type_id)
    return jsonify({"schema": schema})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return "Missing file", 400
    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400

    filename = secure_filename(file.filename)
    doc_id = str(uuid.uuid4())
    save_name = f"{doc_id}_{filename}"
    save_path = os.path.join(UPLOAD_FOLDER, save_name)
    file.save(save_path)

    DOC_STORE[doc_id] = save_path

    pages = load_document_as_images(save_path)
    classification = classify_document(pages)
    doc_type_id = classification.get("doc_type_id", "unknown")
    schema = load_schema_for_doc_type(doc_type_id)

    return jsonify(
        {
            "doc_id": doc_id,
            "classification": classification,
            "schema": schema,
        }
    )


@app.route("/api/run-ocr", methods=["POST"])
def api_run_ocr():
    data = request.get_json(force=True)
    doc_id = data.get("doc_id")
    doc_type_id = data.get("doc_type_id")

    if not doc_id or doc_id not in DOC_STORE:
        return "Unknown or missing doc_id", 400

    path = DOC_STORE[doc_id]
    result = run_pipeline_with_logs(path, override_doc_type_id=doc_type_id)

    return jsonify(result)


@app.route("/api/templates", methods=["POST"])
def api_templates():
    data = request.get_json(force=True)
    doc_type_id = data.get("doc_type_id")
    schema = data.get("schema")
    if not doc_type_id or not isinstance(schema, dict):
        return "doc_type_id and schema dict required", 400

    dest_path = os.path.join(SCHEMA_DIR, f"{doc_type_id}.json")
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    return jsonify({"ok": True, "path": dest_path})


@app.route("/api/models", methods=["POST"])
def api_save_model():
    data = request.get_json(force=True)
    name = data.get("name")
    doc_type_id = data.get("doc_type_id")
    if not name or not doc_type_id:
        return "name and doc_type_id required", 400

    models = load_models()
    models[name] = {
        "doc_type_id": doc_type_id,
        "description": data.get("description", ""),
    }
    save_models(models)
    return jsonify({"ok": True, "models": models})


@app.route("/api/models", methods=["GET"])
def api_list_models():
    return jsonify({"models": load_models()})


@app.route("/api/<model_name>", methods=["POST"])
def api_run_model(model_name: str):
    models = load_models()
    if model_name not in models:
        return f"Unknown model '{model_name}'", 404

    cfg = models[model_name]
    doc_type_id = cfg.get("doc_type_id")

    if "file" not in request.files:
        return "Missing file", 400
    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400

    filename = secure_filename(file.filename)
    tmp_id = str(uuid.uuid4())
    save_name = f"{tmp_id}_{filename}"
    save_path = os.path.join(UPLOAD_FOLDER, save_name)
    file.save(save_path)

    result = run_pipeline_with_logs(save_path, override_doc_type_id=doc_type_id)

    return jsonify(
        {
            "model": model_name,
            "doc_type_id": doc_type_id,
            "result": result,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
