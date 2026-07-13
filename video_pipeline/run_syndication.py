#!/usr/bin/env python3
"""
run_syndication.py
====================
Standalone trigger for blog_syndication.py — deliberately built this way
so none of the 5 existing channel pipeline files need to be touched or
risk being broken by a mid-file edit.

How it works: each channel's own pipeline already writes last_title,
last_url, and last_niche into its own state.json every time a real
episode publishes (confirmed directly in the pipeline code). This
script reads those 5 state files, checks a small tracking file to see
which episodes have already been syndicated, and calls
syndicate_episode() for anything genuinely new.

Run this on a schedule shortly after your upload workflows run each day
(e.g., 1-2 hours later, to be safe) — it's a no-op with nothing to do on
days a channel didn't actually publish.
"""
import os, sys, json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from blog_syndication import syndicate_episode, tg

CHANNELS = [
    ("channels/betrayal_deepdive/state.json", "betrayal_deepdive"),
    ("channels/evidence_room/state.json",     "evidence_room"),
    ("channels/control_files/state.json",     "control_files"),
    ("channels/archive/state.json",           "archive"),
    ("channels/collapse_index/state.json",    "collapse_index"),
]
TRACKING_FILE = "video_pipeline/syndicated_episodes.json"


def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_tracking(data):
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    tracking = load_tracking()
    synced_this_run = 0

    for state_path, channel_id in CHANNELS:
        if not os.path.exists(state_path):
            print(f"No state.json yet for {channel_id} — skipping")
            continue
        try:
            with open(state_path) as f:
                state = json.load(f)
        except Exception as e:
            print(f"Could not read {state_path}: {e}")
            continue

        last_title = state.get("last_title", "")
        last_url = state.get("last_url", "")
        last_niche = state.get("last_niche", "")

        if not last_title or not last_url:
            print(f"{channel_id}: no published episode recorded yet")
            continue

        # Use the URL as the unique key — a new episode always gets a new URL
        if tracking.get(channel_id) == last_url:
            print(f"{channel_id}: '{last_title[:50]}' already syndicated — skipping")
            continue

        print(f"{channel_id}: new episode found — '{last_title[:60]}'")
        result = syndicate_episode(
            episode_title=last_title,
            topic_summary=f"A real, documented episode from {channel_id.replace('_', ' ').title()}.",
            channel_id=channel_id,
            niche_name=last_niche or "general",
        )
        tracking[channel_id] = last_url
        synced_this_run += 1

    save_tracking(tracking)
    print(f"\nDone. {synced_this_run} new episode(s) syndicated this run.")


if __name__ == "__main__":
    main()
