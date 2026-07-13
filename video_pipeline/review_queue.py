"""
review_queue.py

RECONSTRUCTION NOTICE: this file was accidentally deleted from the repo.
This is a rebuilt replacement, not a recovered original — I never had a
byte-for-byte copy of the original file. It's built entirely from the
confirmed, exact interface every channel pipeline actually calls: the
same function names, same arguments, and same return-value shapes found
in every real call site across all 5 channels (master_pipeline.py,
evidence_room_pipeline.py, control_files_pipeline.py, archive_pipeline.py,
collapse_index_pipeline.py). If any internal detail beyond that observed
contract differs from the original, the pipelines will still work
correctly against this file, since they only ever depend on the
documented interface below.

Purpose: a simple, file-based state machine ensuring only ONE episode is
ever "in human review" per channel at a time, tracked across the 4 real
checkpoints every channel's pipeline waits on:
  SCRIPT -> AUDIO_VIDEO -> TITLE_THUMB_DESC -> SHORTS -> DONE
plus the terminal "REJECTED" state (reachable only via an explicit
reject decision, and deliberately NOT part of the normal checkpoint
order, since a reject ends the review rather than advancing it).

State lives in a single JSON file per channel: <script_dir>/review_queue.json
"""

import json
import datetime
from pathlib import Path

CHECKPOINT_ORDER = ["SCRIPT", "AUDIO_VIDEO", "TITLE_THUMB_DESC", "SHORTS", "DONE"]

# Real, confirmed 2-day maximum review window (6 check-ins at up to
# 3/day) — matches the check_ins_used / get_schedule_line pattern
# already used throughout human_review_gate.py.
MAX_CHECK_INS = 6


def _queue_path(script_dir):
    return Path(script_dir) / "review_queue.json"


def load_queue_state(script_dir):
    """
    Returns the current queue state dict, or None if no review is
    currently tracked (file doesn't exist, or is empty/corrupt).
    """
    path = _queue_path(script_dir)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data else None
    except Exception:
        return None


def _save_queue_state(script_dir, state):
    path = _queue_path(script_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass  # best-effort persistence — a failed write here shouldn't crash the pipeline
    return state


def is_channel_review_busy(script_dir):
    """
    True if a review is currently in progress for this channel (i.e. the
    last-started episode hasn't reached a terminal checkpoint yet).
    Used at the very start of the generate phase to avoid burning a full
    script-generation run only to discover the queue was already busy.
    """
    state = load_queue_state(script_dir)
    if not state:
        return False
    return state.get("checkpoint") not in ("DONE", "REJECTED")


def start_review(script_dir, episode, title, artifacts=None):
    """
    Begins tracking a new episode's review. Always resets check_ins_used
    to 0 and checkpoint to the first real stage, since this is only ever
    called once the previous review (if any) has already reached a
    terminal state — is_channel_review_busy is the guard for that.
    """
    state = {
        "episode": episode,
        "title": title,
        "artifacts": artifacts or {},
        "checkpoint": CHECKPOINT_ORDER[0],
        "check_ins_used": 0,
        "started_at": datetime.datetime.now().isoformat(),
        "last_updated": datetime.datetime.now().isoformat(),
        "history": [],
    }
    return _save_queue_state(script_dir, state)


def record_check_in(script_dir, decision, feedback=None):
    """
    Records one human decision against the current checkpoint and
    advances the state machine accordingly:

      - "reject"  -> terminal. checkpoint = "REJECTED" (deliberately
                     outside CHECKPOINT_ORDER — a rejected episode never
                     "completes" the normal sequence).
      - "approve" -> advances to the next stage in CHECKPOINT_ORDER.
      - anything else (edit / remake / swap_visuals / any future
        decision type) -> does NOT advance the checkpoint on its own,
        since the pipeline is expected to regenerate and re-submit for
        the SAME checkpoint. The one exception is when check_ins_used
        has hit MAX_CHECK_INS: the decision is force-advanced regardless
        of type, so a review can never stay open past the real 2-day
        window.

    Returns {"state": <updated state dict>, "forced": bool} — "forced"
    is True only when MAX_CHECK_INS was hit and the advance happened
    regardless of the actual decision. Returns None if no active review
    is being tracked at all (defensive — callers already guard for this
    but should not crash if it happens).
    """
    state = load_queue_state(script_dir)
    if not state:
        return None

    state["check_ins_used"] = state.get("check_ins_used", 0) + 1
    state["last_updated"] = datetime.datetime.now().isoformat()
    state.setdefault("history", []).append({
        "decision": decision,
        "feedback": feedback,
        "at": state["last_updated"],
        "checkpoint_at_time": state.get("checkpoint"),
    })

    forced = state["check_ins_used"] >= MAX_CHECK_INS

    if decision == "reject":
        state["checkpoint"] = "REJECTED"
    elif decision == "approve" or forced:
        current = state.get("checkpoint", CHECKPOINT_ORDER[0])
        try:
            idx = CHECKPOINT_ORDER.index(current)
        except ValueError:
            idx = 0
        state["checkpoint"] = CHECKPOINT_ORDER[min(idx + 1, len(CHECKPOINT_ORDER) - 1)]
    # edit / remake / swap_visuals (and not yet forced): checkpoint
    # intentionally stays the same — the pipeline is expected to
    # regenerate and re-submit the same checkpoint for another look.

    _save_queue_state(script_dir, state)
    return {"state": state, "forced": forced}


def clear_queue(script_dir):
    """
    Marks the queue as fully resolved, freeing it for the next episode.
    Deliberately sets checkpoint="DONE" rather than deleting the file —
    load_queue_state's callers check for checkpoint == "DONE" as their
    "safe to start a new review" signal, so keeping a short-lived record
    of the last completed review is harmless and slightly more useful
    for debugging than deleting it outright.
    """
    state = load_queue_state(script_dir) or {}
    state["checkpoint"] = "DONE"
    state["last_updated"] = datetime.datetime.now().isoformat()
    return _save_queue_state(script_dir, state)
