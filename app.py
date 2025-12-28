from flask import (
    Flask,
    request,
    jsonify,
    redirect,
    render_template
)
from werkzeug.utils import secure_filename
import os
import threading

from database import (
    create_job,
    cancel_job,
    get_download_url,
    upload_file
)
from database import supabase
from worker import run_worker


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_ACTIONS = {"compress", "convert"}

app = Flask(__name__)

# Start worker in background thread
worker_thread = threading.Thread(target=run_worker, daemon=True)
worker_thread.start()


# =========================
# UI ROUTE
# =========================
@app.get("/")
def index():
    """
    Serve main UI
    """
    return render_template("index.html")


# =========================
# API: CREATE JOB
# =========================
@app.get("/job/<job_id>")
def job_status(job_id):
    job = (
        supabase.table("jobs")
        .select("status, progress")
        .eq("id", job_id)
        .single()
        .execute()
    )
    return jsonify(job.data)

@app.post("/upload")
def upload():
    # --- file validation ---
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # --- action validation ---
    action = request.form.get("action")
    if action not in ALLOWED_ACTIONS:
        return jsonify({"error": "Invalid action"}), 400

    # --- target validation ---
    try:
        target = int(request.form.get("target", 70))
    except ValueError:
        target = 70

    target = max(0, min(target, 90))

    # --- save upload ---
    filename = secure_filename(f.filename)

    # UPLOAD TO SUPABASE
    # UPLOAD & CREATE JOB
    try:
        # --- to_format (optional) ---
        to_format = request.form.get("to_format")

        upload_file(f, filename)
        
        job = create_job(
            filename=filename,
            action=action,
            target=target,
            input_path=filename, # Key in bucket
            to_format=to_format
        )
        
        return jsonify({
            "job_id": job["id"],
            "status": job["status"],
            "progress": job["progress"]
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc() # Print to server logs
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


# =========================
# API: CANCEL JOB
# =========================
@app.post("/cancel/<job_id>")
def cancel(job_id):
    cancel_job(job_id)
    return jsonify({"status": "cancelled"}), 200


# =========================
# API: DOWNLOAD RESULT
# =========================
@app.get("/download/<job_id>")
def download(job_id):
    url = get_download_url(job_id)

    if not url or "signedURL" not in url:
        return jsonify({"error": "File not ready or job not finished"}), 404

    return redirect(url["signedURL"])


# =========================
# API: HEALTH CHECK
# =========================
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ========================= 
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
