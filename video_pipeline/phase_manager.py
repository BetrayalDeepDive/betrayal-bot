"""
PHASE MANAGER — Two-phase pipeline controller.

Every pipeline imports this and calls:
    phase = get_pipeline_phase()        # returns "generate" or "upload"
    save_pending(data)                  # saves artifact paths for upload phase
    pending = load_pending()            # upload phase reads what generate saved
    clear_pending()                     # upload phase clears after success

How it works:
  GENERATE phase:
    - Pipeline runs fully: script → audio → video → thumbnail
    - Does NOT call upload_yt()
    - Calls save_pending() with all file paths, title, description, tags
    - Commits pending_upload.json to repo
    - Sends Telegram: "Video ready. Uploading at [time]."

  UPLOAD phase:
    - Reads pending_upload.json
    - If no pending file: sends Telegram warning and exits
    - Uploads video, thumbnail, Shorts
    - Posts creator comment, updates channel description
    - Calls growth engine sprint
    - Clears pending_upload.json
    - Commits clean state

Benefits:
  1. Token quotas never compete — 3-4 hour gaps between generations
  2. Upload always happens at the optimal audience window regardless of generation time
  3. If generation fails: upload phase detects missing pending file, alerts via Telegram
  4. If upload fails: pending file remains, can retry upload manually via workflow_dispatch
  5. GitHub Actions timeout (6h) no longer a risk — each phase is 2-3h max
"""

import os, json, datetime
from pathlib import Path


def get_pipeline_phase():
    """
    Returns "generate" or "upload" based on PIPELINE_PHASE env var.
    Defaults to legacy "full" mode if not set (backward compatible).
    """
    return os.environ.get("PIPELINE_PHASE", "full").lower()


def get_pending_file(channel_dir):
    """Returns the path to pending_upload.json for this channel."""
    return Path(channel_dir) / "pending_upload.json"


def save_pending(channel_dir, data: dict):
    """
    Save pending upload data after successful generation.
    data must contain:
      - video_path: absolute path to the generated video file
      - audio_path: path to audio file (for SRT generation)
      - thumbnail_path: path to thumbnail image
      - script_clean: the narration text
      - title: YouTube title
      - description: full YouTube description
      - tags: list of tags
      - niche_name: niche identifier
      - voice_used: edge-tts voice
      - duration: audio duration in seconds
      - score: quality score
      - style_name: animation style (Ch2/Ch3)
      - episode: episode number
      - playlist_id: if already created
      - shorts_clips: list of short clip paths
      - generated_at: ISO timestamp

    FIX: this used to overwrite any existing pending_upload.json completely
    unconditionally — with zero check for whether a PREVIOUS video was
    still sitting there, not yet uploaded. If the Upload phase workflow
    ever failed to run, got delayed, or was paused for any reason, the
    next Generate run would silently clobber that video's data with no
    trace and no alert — that video would simply never upload, and no one
    would know why. Now checks first, and returns a warning in the result
    so the calling pipeline (which has access to its own Telegram
    function) can alert before data is lost, rather than losing it silently.
    """
    pf = get_pending_file(channel_dir)
    overwrite_warning = None
    existing = load_pending(channel_dir)
    if existing and not is_already_uploaded(existing):
        is_fresh, hours_old = check_pending_age(existing, max_hours=30)
        overwrite_warning = (
            f"Overwriting a PREVIOUS pending video that was never uploaded "
            f"({hours_old}h old, title: {existing.get('title', 'unknown')!r}). "
            f"That video will now be lost unless its files are recovered manually."
        )

    data["generated_at"] = datetime.datetime.now().isoformat()
    data["channel_dir"]  = str(channel_dir)
    pf.write_text(json.dumps(data, indent=2))
    return {"path": str(pf), "overwrite_warning": overwrite_warning}


def load_pending(channel_dir):
    """
    Load pending upload data. Returns None if no pending file exists.
    """
    pf = get_pending_file(channel_dir)
    if not pf.exists():
        return None
    try:
        return json.loads(pf.read_text())
    except:
        return None


def clear_pending(channel_dir):
    """Clear pending file after successful upload."""
    pf = get_pending_file(channel_dir)
    if pf.exists():
        # Write empty rather than delete — keeps file in git tree
        pf.write_text(json.dumps({"status": "uploaded",
                                   "cleared_at": datetime.datetime.now().isoformat()}, indent=2))


def check_pending_age(pending_data, max_hours=30):
    """
    Check if pending file is too old (stale generation).
    Returns (is_fresh, hours_old).
    If older than max_hours: generation likely failed or was skipped.
    """
    generated_at = pending_data.get("generated_at", "")
    if not generated_at:
        return False, 999
    try:
        gen_dt    = datetime.datetime.fromisoformat(generated_at)
        hours_old = (datetime.datetime.now() - gen_dt).total_seconds() / 3600
        return hours_old <= max_hours, round(hours_old, 1)
    except:
        return False, 999


def is_already_uploaded(pending_data):
    """Returns True if pending file shows a previous successful upload."""
    return pending_data.get("status") == "uploaded"
