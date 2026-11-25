"""
Flask backend — Object-Specific Movement Detection & Tracking
"""

import os
import sys
import uuid
import json
import threading
from pathlib import Path
import tempfile

# ── Fix matplotlib / ultralytics cache dirs before importing them ─────────────
_tmp = tempfile.gettempdir()
os.environ.setdefault("MPLCONFIGDIR",   str(Path(_tmp) / "matplotlib_cfg"))
os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(_tmp) / "ultralytics_cfg"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(exist_ok=True)
Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(exist_ok=True)

from flask import (
    Flask, request, jsonify, send_file,
    send_from_directory, abort, Response,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename

from tracker import ObjectTracker
from graphs_gen import save_all_graphs


# ── ffmpeg re-encode helper (makes video browser-playable) ───────────────────
def _try_ffmpeg_reencode(video_path: Path) -> None:
    """
    Re-encode the output video to H.264 using ffmpeg if it is available.
    Falls back silently if ffmpeg is not installed.
    """
    import subprocess, shutil
    if not shutil.which("ffmpeg"):
        return
    tmp = video_path.with_suffix(".h264.mp4")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vcodec", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-movflags", "+faststart",   # enables streaming
                "-acodec", "copy",
                str(tmp),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )
        if tmp.exists() and tmp.stat().st_size > 0:
            video_path.unlink()
            tmp.rename(video_path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

# ─────────────────────────── App setup ───────────────────────────────────────
BASE_DIR    = Path(__file__).parent
UPLOAD_DIR  = BASE_DIR / "uploads"
OUTPUT_DIR  = BASE_DIR / "outputs"
GRAPHS_DIR  = BASE_DIR / "graphs"
FRONTEND    = BASE_DIR.parent / "frontend"

ALLOWED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

app = Flask(
    __name__,
    static_folder=str(FRONTEND / "static"),
    template_folder=str(FRONTEND / "templates"),
)
CORS(app)

# Global in-memory session store   session_id → {tracker, summary, video_path}
sessions: dict[str, dict] = {}
jobs:     dict[str, dict] = {}     # session_id → job status for async rendering


# ─────────────────────────── Static frontend ─────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(FRONTEND / "templates"), "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(str(FRONTEND / "static"), path)


# ─────────────────────────── Upload & analyse ────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    f = request.files["video"]
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    session_id = str(uuid.uuid4())
    fname      = secure_filename(f"{session_id}{ext}")
    video_path = UPLOAD_DIR / fname
    f.save(video_path)

    return jsonify({"session_id": session_id, "filename": fname})


@app.route("/api/analyse", methods=["POST"])
def analyse_video():
    data       = request.get_json(force=True)
    session_id = data.get("session_id")
    conf       = float(data.get("conf", 0.35))

    # find uploaded file
    video_path = None
    for ext in ALLOWED_EXT:
        p = UPLOAD_DIR / f"{session_id}{ext}"
        if p.exists():
            video_path = p
            break

    if video_path is None:
        return jsonify({"error": "Session not found — please upload first"}), 404

    tracker  = ObjectTracker(conf=conf)
    summary  = tracker.process_video(str(video_path))

    sessions[session_id] = {
        "tracker":    tracker,
        "summary":    summary,
        "video_path": str(video_path),
    }

    return jsonify({"session_id": session_id, "summary": summary})


# ─────────────────────────── Track selected object ───────────────────────────
@app.route("/api/track", methods=["POST"])
def track_object():
    data       = request.get_json(force=True)
    session_id = data.get("session_id")
    track_id   = int(data.get("track_id", -1))

    if session_id not in sessions:
        return jsonify({"error": "Session expired — re-upload video"}), 404

    sess       = sessions[session_id]
    tracker    = sess["tracker"]
    video_path = sess["video_path"]

    out_vid  = OUTPUT_DIR / f"{session_id}_{track_id}.mp4"
    out_dir  = GRAPHS_DIR / session_id

    # run render
    analysis = tracker.render_tracked_video(
        video_path, track_id, str(out_vid)
    )

    # generate graphs
    graph_files = save_all_graphs(analysis, str(out_dir))

    # ── Re-encode to H.264 with ffmpeg if available (browser-compatible) ──
    _try_ffmpeg_reencode(out_vid)

    # build URLs
    base_url = f"/api/graphs/{session_id}"
    graph_urls = {k: f"{base_url}/{v}" for k, v in graph_files.items() if v}

    sess["analysis"]   = analysis
    sess["graph_urls"] = graph_urls
    sess["out_vid"]    = str(out_vid)

    return jsonify({
        "analysis":   analysis,
        "graph_urls": graph_urls,
        "video_url":  f"/api/video/{session_id}/{track_id}",
    })


# ─────────────────────────── File serving ────────────────────────────────────
@app.route("/api/video/<session_id>/<int:track_id>")
def serve_video(session_id, track_id):
    path = OUTPUT_DIR / f"{session_id}_{track_id}.mp4"
    if not path.exists():
        abort(404)

    file_size = path.stat().st_size
    range_header = request.headers.get("Range", None)

    if not range_header:
        # No range requested — send whole file with headers browsers need
        resp = Response(
            _stream_file(path, 0, file_size - 1),
            200,
            mimetype="video/mp4",
            direct_passthrough=True,
        )
        resp.headers["Content-Length"] = file_size
        resp.headers["Accept-Ranges"]  = "bytes"
        return resp

    # Parse Range: bytes=start-end
    byte_range = range_header.replace("bytes=", "").strip()
    parts = byte_range.split("-")
    start = int(parts[0]) if parts[0] else 0
    end   = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
    end   = min(end, file_size - 1)
    length = end - start + 1

    resp = Response(
        _stream_file(path, start, end),
        206,
        mimetype="video/mp4",
        direct_passthrough=True,
    )
    resp.headers["Content-Range"]  = f"bytes {start}-{end}/{file_size}"
    resp.headers["Accept-Ranges"]  = "bytes"
    resp.headers["Content-Length"] = length
    return resp


def _stream_file(path, start, end, chunk=65536):
    """Generator that yields file chunks between byte positions start…end."""
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


@app.route("/api/graphs/<session_id>/<filename>")
def serve_graph(session_id, filename):
    graph_dir = GRAPHS_DIR / session_id
    path = graph_dir / filename
    if not path.exists():
        abort(404)
    return send_file(str(path), mimetype="image/png")


# ─────────────────────────── Health check ────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    GRAPHS_DIR.mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
