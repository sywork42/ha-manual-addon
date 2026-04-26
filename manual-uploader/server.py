#!/usr/bin/env python3
"""
Manual Uploader — Home Assistant add-on (v1.1.0).

Features:
- Create/edit appliance manual pages via web UI
- Upload videos, PDFs, images directly from phone
- QR codes downloadable as PNG named after the appliance
- Optional obfuscated filenames so URLs aren't easily guessable
- Rate limiting on upload endpoint
"""

from flask import Flask, request, jsonify, send_file, abort
from pathlib import Path
import os
import re
import json
import secrets
import time
from collections import defaultdict, deque

# ============================================================
# CONFIG
# ============================================================
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))
SUBFOLDER = os.environ.get("SUBFOLDER", "manuals").strip("/")
OBFUSCATE_URLS = os.environ.get("OBFUSCATE_URLS", "true").lower() in ("true", "1", "yes")

HA_CONFIG = Path("/homeassistant")
WWW_DIR = HA_CONFIG / "www" / SUBFOLDER
MANUALS_DATA_FILE = WWW_DIR / "_manuals.json"

WWW_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv",
    ".pdf",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".html",
}

APP_DIR = Path("/app")
STATIC_DIR = APP_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


# ============================================================
# RATE LIMITING (simple in-memory)
# ============================================================
_rate_buckets = defaultdict(lambda: deque(maxlen=60))


def check_rate_limit(client_id: str, max_per_minute: int = 30) -> bool:
    """Returns True if under limit, False if rate-limited."""
    now = time.time()
    bucket = _rate_buckets[client_id]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= max_per_minute:
        return False
    bucket.append(now)
    return True


def client_id_from_request():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")


# ============================================================
# HELPERS
# ============================================================
def sanitize_filename(name: str) -> str:
    name = os.path.basename(name or "")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:120] or "file"


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9\s-]", "", name).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s[:80] or "appliance"


def make_obfuscated_name(stem: str, ext: str) -> str:
    """Append a random short suffix to make URLs hard to guess."""
    suffix = secrets.token_hex(4)  # 8 hex chars
    return f"{stem}-{suffix}{ext}"


def load_manuals_index() -> dict:
    if MANUALS_DATA_FILE.exists():
        try:
            return json.loads(MANUALS_DATA_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_manuals_index(data: dict):
    MANUALS_DATA_FILE.write_text(json.dumps(data, indent=2))


# ============================================================
# UI ROUTES
# ============================================================
@app.route("/")
def index():
    return send_file(STATIC_DIR / "index.html")


@app.route("/editor")
def editor():
    return send_file(STATIC_DIR / "editor.html")


# ============================================================
# STATUS
# ============================================================
@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "upload_dir": str(WWW_DIR),
        "subfolder": SUBFOLDER,
        "max_upload_mb": MAX_UPLOAD_MB,
        "obfuscate_urls": OBFUSCATE_URLS,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
    })


# ============================================================
# UPLOAD
# ============================================================
@app.route("/api/upload", methods=["POST"])
def upload():
    if not check_rate_limit("upload_" + client_id_from_request(), max_per_minute=30):
        return jsonify({"error": "Upload rate limit exceeded — wait a minute"}), 429

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    safe_name = sanitize_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"File type {ext} not allowed",
            "allowed": sorted(ALLOWED_EXTENSIONS),
        }), 400

    if OBFUSCATE_URLS:
        final_name = make_obfuscated_name(stem, ext)
        while (WWW_DIR / final_name).exists():
            final_name = make_obfuscated_name(stem, ext)
    else:
        final_name = safe_name
        counter = 1
        while (WWW_DIR / final_name).exists():
            final_name = f"{stem}-{counter}{ext}"
            counter += 1

    target = WWW_DIR / final_name
    file.save(target)

    return jsonify({
        "status": "ok",
        "filename": target.name,
        "local_url": f"/local/{SUBFOLDER}/{target.name}",
        "size_bytes": target.stat().st_size,
    })


# ============================================================
# MANUAL CRUD
# ============================================================
@app.route("/api/manuals")
def list_manuals():
    return jsonify(load_manuals_index())


@app.route("/api/manuals/<manual_id>", methods=["GET"])
def get_manual(manual_id):
    data = load_manuals_index()
    if manual_id not in data:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data[manual_id])


@app.route("/api/manuals/<manual_id>", methods=["PUT", "POST"])
def save_manual(manual_id):
    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "No data"}), 400

    data = load_manuals_index()
    existing = data.get(manual_id, {})

    # Stable filename per manual: keep existing or generate once
    if OBFUSCATE_URLS:
        html_name = existing.get("_html_filename")
        if not html_name:
            slug = slugify(body.get("title", manual_id))
            html_name = f"{slug}-{secrets.token_hex(4)}.html"
    else:
        slug = slugify(body.get("title", manual_id))
        html_name = f"{slug}.html"
        # Remove old file if title changed
        old_html = existing.get("_html_filename")
        if old_html and old_html != html_name:
            old_path = WWW_DIR / sanitize_filename(old_html)
            if old_path.exists():
                old_path.unlink()

    body["_html_filename"] = html_name
    body["_local_url"] = f"/local/{SUBFOLDER}/{html_name}"
    body["_slug"] = slugify(body.get("title", manual_id))
    data[manual_id] = body
    save_manuals_index(data)

    html = render_manual_html(body)
    (WWW_DIR / html_name).write_text(html, encoding="utf-8")

    return jsonify({
        "status": "ok",
        "manual_id": manual_id,
        "html_filename": html_name,
        "local_url": body["_local_url"],
        "slug": body["_slug"],
    })


@app.route("/api/manuals/<manual_id>", methods=["DELETE"])
def delete_manual(manual_id):
    data = load_manuals_index()
    if manual_id not in data:
        return jsonify({"error": "Not found"}), 404
    manual = data[manual_id]
    html_name = manual.get("_html_filename")
    if html_name:
        html_path = WWW_DIR / sanitize_filename(html_name)
        if html_path.exists():
            html_path.unlink()
    del data[manual_id]
    save_manuals_index(data)
    return jsonify({"status": "ok"})


# ============================================================
# STANDALONE HTML RENDERER
# ============================================================
def render_manual_html(data: dict) -> str:
    template = (STATIC_DIR / "manual-template.html").read_text()
    payload = json.dumps(data, ensure_ascii=False)
    return template.replace("/*__DATA_INJECTION__*/", f"window.__APPLIANCE_DATA__ = {payload};")


if __name__ == "__main__":
    print(f"📁 Upload dir: {WWW_DIR}")
    print(f"🔒 URL obfuscation: {OBFUSCATE_URLS}")
    print(f"🌐 Ingress port 8099")
    app.run(host="0.0.0.0", port=8099, debug=False)
