from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_job(filename, action, target, input_path, to_format=None):
    res = supabase.table("jobs").insert({
        "filename": filename,
        "action": action,
        "target": target,
        "status": "queued",
        "progress": 0,
        "input_path": input_path,
        "to_format": to_format
    }).execute()
    return res.data[0]

def update_job(job_id, **fields):
    supabase.table("jobs").update(fields).eq("id", job_id).execute()

def get_job(job_id):
    res = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    return res.data

def cancel_job(job_id):
    update_job(job_id, status="cancelled")

def upload_output(job_id, filepath):
    import os
    ext = os.path.splitext(filepath)[1]
    filename = f"{job_id}{ext}"
    
    with open(filepath, "rb") as f:
        file_content = f.read()
        supabase.storage.from_("mahaconvert-output").upload(
            filename, file_content
        )
    update_job(job_id, output_path=filename)

def get_download_url(job_id):
    import os
    job = get_job(job_id)
    
    # Construct proper filename: original_name (without ext) + new_ext
    original_name = os.path.splitext(job["filename"])[0]
    new_ext = os.path.splitext(job["output_path"])[1]
    final_name = f"{original_name}{new_ext}"

    return supabase.storage.from_("mahaconvert-output").create_signed_url(
        job["output_path"], 
        3600,
        options={'download': final_name}
    )

def upload_file(file_obj, filename):
    """
    Upload input file to 'mahaconvert-uploads' bucket
    """
    file_obj.seek(0)
    file_content = file_obj.read()
    res = supabase.storage.from_("mahaconvert-upload").upload(
        path=filename,
        file=file_content,
        file_options={"content-type": "application/octet-stream", "x-upsert": "true"}
    )
    return res

def download_file(bucket, path, local_path):
    """
    Download file from Supabase to local path
    """
    with open(local_path, 'wb+') as f:
        res = supabase.storage.from_(bucket).download(path)
        f.write(res)

