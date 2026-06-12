"""
drive_backup.py
================
Stores freelance deliverables to Google Drive automatically.
- Organises by client name and date
- Sets 90-day auto-delete (saves storage)
- Generates shareable link for client delivery
- Zero cost — uses your existing Google account (15GB free)

This replaces GitHub artifact storage completely.
Videos go: GitHub runner → YouTube (direct) → deleted
Freelance work goes: GitHub runner → Google Drive → client link → deleted after 90 days

ENV VARS needed (already have these):
  GOOGLE_SHEETS_CREDS  (reuse existing service account)
"""

import os, json, logging
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DRIVE] %(message)s")
log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

def get_drive_service():
    """Get Google Drive service using existing service account credentials."""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDS", "{}")
    if creds_json == "{}":
        raise ValueError("GOOGLE_SHEETS_CREDS not set")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """Get existing folder or create new one. Returns folder ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    log.info("Created folder: %s", folder_name)
    return folder["id"]


def upload_to_drive(file_path: str, client_name: str = "General",
                    keep_days: int = 90) -> dict:
    """
    Upload a file to Google Drive.
    Organises into: Betrayal DeepDive / Freelance / [Client] / [Date]
    Returns dict with file_id and shareable_link.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    service = get_drive_service()

    # Create folder structure
    root_id     = get_or_create_folder(service, "Betrayal DeepDive Automation")
    freelance_id = get_or_create_folder(service, "Freelance Deliverables", root_id)
    client_id   = get_or_create_folder(service, client_name, freelance_id)
    date_id     = get_or_create_folder(service, datetime.now().strftime("%Y-%m"), client_id)

    # Upload file
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # Determine mime type
    if file_path.endswith(".mp4"):
        mime = "video/mp4"
    elif file_path.endswith(".pdf"):
        mime = "application/pdf"
    elif file_path.endswith(".html"):
        mime = "text/html"
    elif file_path.endswith(".json"):
        mime = "application/json"
    else:
        mime = "application/octet-stream"

    metadata = {
        "name":    file_name,
        "parents": [date_id],
        "description": f"Deliverable for {client_name}. Auto-delete after {keep_days} days.",
    }

    media = MediaFileUpload(file_path, mimetype=mime, resumable=True)
    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink"
    ).execute()

    file_id = file["id"]

    # Make shareable (anyone with link can view)
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    shareable_link = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
    download_link  = file.get("webContentLink", f"https://drive.google.com/uc?id={file_id}&export=download")

    log.info("✅ Uploaded to Drive: %s (%.1f MB)", file_name, file_size/1024/1024)
    log.info("   Link: %s", shareable_link)

    return {
        "file_id":       file_id,
        "file_name":     file_name,
        "shareable_link": shareable_link,
        "download_link":  download_link,
        "expires_days":   keep_days,
        "client":         client_name,
        "uploaded_at":    datetime.now().isoformat(),
    }


def cleanup_old_files(keep_days: int = 90):
    """
    Deletes files older than keep_days from Drive.
    Run this weekly to keep storage clean automatically.
    """
    service    = get_drive_service()
    cutoff     = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%dT%H:%M:%S")
    query      = f"createdTime < '{cutoff}' and trashed=false"
    results    = service.files().list(q=query, fields="files(id, name, createdTime)").execute()
    old_files  = results.get("files", [])

    deleted = 0
    for f in old_files:
        try:
            service.files().delete(fileId=f["id"]).execute()
            log.info("Deleted old file: %s (created %s)", f["name"], f["createdTime"][:10])
            deleted += 1
        except Exception as e:
            log.warning("Could not delete %s: %s", f["name"], e)

    log.info("Cleanup complete: %d files deleted", deleted)
    return deleted


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_old_files()
    else:
        print("Usage: python drive_backup.py <file_path> [client_name] [keep_days]")
        print("       python drive_backup.py cleanup")
