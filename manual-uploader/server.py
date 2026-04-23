#!/usr/bin/env python3
"""
Manual Uploader — Home Assistant add-on.

Serves a web UI via HA ingress where users can:
- Create/edit appliance manual pages
- Upload videos, PDFs, and images from their phone
- Export standalone HTML pages into /homeassistant/www/manuals/
- Generate QR codes that point to the HA-served URL

Files uploaded live in /homeassistant/www/<subfolder>/ and are served
by HA at /local/<subfolder>/<filename>.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, abort
from pathlib import Path
import os
import re
import json

# ============================================================
# CONFIG (from add-on options, injected by run.sh)
# ============================================================
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))
SUBFOLDER = os.environ.get("SUBFOLDER", "manuals").strip("/")

# HA maps the config dir to /homeassistant inside the add-on container
HA_CONFIG = Path("/homeassistant")
WWW_DIR = HA_CONFIG / "www" / SUBFOLDER
MANUALS_DATA_FILE = WWW_DIR / "_manuals.json"   # index of created manuals

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


def load_manuals_index():
    if MANUALS_DATA_FILE.exists():
        try:
            return json.loads(MANUALS_DATA_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_manuals_index(data):
    MANUALS_DATA_FILE.write_text(json.dumps(data, indent=2))


# ============================================================
# ROUTES — UI
# ============================================================
@app.route("/")
def index():
    return send_file(STATIC_DIR / "index.html")


@app.route("/editor")
def editor():
    return send_file(STATIC_DIR / "editor.html")


# ============================================================
# ROUTES — API
# ============================================================
@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "upload_dir": str(WWW_DIR),
        "subfolder": SUBFOLDER,
        "max_upload_mb": MAX_UPLOAD_MB,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
    })


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    safe_name = sanitize_filename(file.filename)
    ext = Path(safe_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"File type {ext} not allowed",
            "allowed": sorted(ALLOWED_EXTENSIONS),
        }), 400

    target = WWW_DIR / safe_name
    counter = 1
    while target.exists():
        stem = Path(safe_name).stem
        target = WWW_DIR / f"{stem}-{counter}{ext}"
        counter += 1

    file.save(target)

    return jsonify({
        "status": "ok",
        "filename": target.name,
        "local_url": f"/local/{SUBFOLDER}/{target.name}",
        "size_bytes": target.stat().st_size,
    })


@app.route("/api/files")
def list_files():
    files = []
    for f in sorted(WWW_DIR.iterdir()):
        if f.is_file() and not f.name.startswith("_"):
            files.append({
                "name": f.name,
                "local_url": f"/local/{SUBFOLDER}/{f.name}",
                "size_bytes": f.stat().st_size,
                "ext": f.suffix.lower(),
            })
    return jsonify({"files": files})


@app.route("/api/files/<name>", methods=["DELETE"])
def delete_file(name):
    safe = sanitize_filename(name)
    target = WWW_DIR / safe
    if not target.exists() or not target.is_file():
        return jsonify({"error": "Not found"}), 404
    target.unlink()
    return jsonify({"status": "ok", "deleted": safe})


@app.route("/api/manuals")
def list_manuals():
    """Return all saved manuals."""
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
    data[manual_id] = body
    save_manuals_index(data)

    # Also write a standalone HTML file for the manual (so it can be viewed via /local/)
    html = render_manual_html(body)
    slug = slugify(body.get("title", manual_id))
    html_path = WWW_DIR / f"{slug}.html"
    html_path.write_text(html, encoding="utf-8")

    body["_html_filename"] = html_path.name
    body["_local_url"] = f"/local/{SUBFOLDER}/{html_path.name}"
    data[manual_id] = body
    save_manuals_index(data)

    return jsonify({
        "status": "ok",
        "manual_id": manual_id,
        "html_filename": html_path.name,
        "local_url": body["_local_url"],
    })


@app.route("/api/manuals/<manual_id>", methods=["DELETE"])
def delete_manual(manual_id):
    data = load_manuals_index()
    if manual_id not in data:
        return jsonify({"error": "Not found"}), 404
    # Remove HTML file too
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
    """Render a self-contained HTML file for a manual."""
    template = (STATIC_DIR / "manual-template.html").read_text()
    payload = json.dumps(data, ensure_ascii=False)
    return template.replace("/*__DATA_INJECTION__*/", f"window.__APPLIANCE_DATA__ = {payload};")


if __name__ == "__main__":
    print(f"📁 Upload dir: {WWW_DIR}")
    print(f"🌐 Ingress port 8099")
    app.run(host="0.0.0.0", port=8099, debug=False)
