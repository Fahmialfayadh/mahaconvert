import time
import os
from database import supabase, update_job, upload_output, download_file
from compressor import MahaCompressor

compressor = MahaCompressor("output")


def run_worker():
    print("Worker started…")

    while True:
        # ambil job queued
        jobs = (
            supabase.table("jobs")
            .select("*")
            .eq("status", "queued")
            .order("created_at")
            .execute()
        )

        for job in jobs.data:
            job_id = job["id"]
            action = job["action"]
            input_path = job["input_path"]
            target = job.get("target", 70)
            to_format = job.get("to_format")

            try:
                # =========================
                # START JOB
                # =========================
                update_job(job_id, status="Starting", progress=5)

                # cek cancel awal
                cur = supabase.table("jobs").select("status").eq("id", job_id).single().execute()
                if cur.data["status"] == "cancelled":
                    update_job(job_id, status="cancelled")
                    continue
                
                # DOWNLOAD FROM SUPABASE IF NEEDED
                # Assume input_path is now the filename in Supabase
                local_input = os.path.join("uploads", input_path)
                if not os.path.exists(local_input):
                    update_job(job_id, status="Downloading file...", progress=10)
                    download_file("mahaconvert-upload", input_path, local_input)

                # =========================
                # COMPRESS
                # =========================
                if action == "compress":
                    update_job(job_id, status="Compressing file", progress=20)

                    output = compressor.compress(
                        local_input,
                        target_percent=target
                    )

                # =========================
                # CONVERT
                # =========================
                elif action == "convert":
                    update_job(job_id, status="Converting file", progress=20)

                    # auto-detect convert with optional target format
                    output = compressor.mc.detect_and_convert(local_input, request_format=to_format)

                else:
                    update_job(job_id, status="error")
                    continue
                    
                # CLEANUP INPUT
                if os.path.exists(local_input):
                    os.remove(local_input)

                # =========================
                # UPLOAD OUTPUT
                # =========================
                update_job(job_id, status="Uploading result", progress=85)
                upload_output(job_id, output)
                
                # CLEANUP OUTPUT
                if os.path.exists(output):
                    os.remove(output)

                update_job(job_id, status="done", progress=100)

            except Exception as e:
                update_job(
                    job_id,
                    status="error",
                    progress=0
                )
                print(f"[ERROR] Job {job_id}: {e}")

        time.sleep(1)


if __name__ == "__main__":
    run_worker()
