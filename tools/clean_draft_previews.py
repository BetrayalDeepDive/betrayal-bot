#!/usr/bin/env python3
"""
Delete review previews stranded on the channel by generate runs that were
never followed by an upload run.

WHAT THESE ARE
--------------
The generate phase uploads the finished episode UNLISTED so the audio+video
review has a real, full-quality link — Telegram cannot carry a 100MB+ file.
That upload necessarily carries placeholder metadata, because the description
and tags are not generated until a later stage:

    "Draft — under review, description finalized before publish."

The Upload phase then pushes the real metadata onto that same video and flips
it public. Nothing is ever published with the placeholder.

WHY THEY GOT STRANDED
---------------------
The preview's id lived in exactly one place: pending_upload.json. A fresh
generate run overwrote it. So a generate run that was never followed by an
upload run left its preview on the channel with nothing anywhere pointing at
it — invisible to every cleanup path, permanent, and visible in Studio as a
draft that never went anywhere.

That leak is fixed at the source (save_pending now deletes the previous
preview at the moment it overwrites the record). This tool is for the ones
already stranded before that fix existed.

WHAT IT WILL NOT TOUCH
----------------------
  * anything not UNLISTED
  * anything whose description is not the exact placeholder
  * the id currently in pending_upload.json — that preview is legitimately
    waiting for its upload run, and deleting it would throw away a finished
    episode

Usage:
    python tools/clean_draft_previews.py            # report only
    python tools/clean_draft_previews.py --apply    # delete them
"""
import json
import os
import sys
from pathlib import Path

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
PLACEHOLDER = "Draft — under review, description finalized before publish."
PENDING = Path(__file__).resolve().parents[1] / \
    "channels/betrayal_deepdive/pending_upload.json"


def get_token():
    cid = os.environ.get("YOUTUBE_CLIENT_ID", "")
    sec = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    ref = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if not (cid and sec and ref):
        print("Missing YOUTUBE_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN.")
        return None
    d = requests.post(TOKEN_URL, data={
        "client_id": cid, "client_secret": sec,
        "refresh_token": ref, "grant_type": "refresh_token"}, timeout=30).json()
    if "access_token" not in d:
        print(f"Token refresh failed: {d.get('error')} — "
              f"{d.get('error_description', '')}")
        return None
    return d["access_token"]


def protected_id():
    """The preview the Upload phase is still going to use, if there is one."""
    try:
        d = json.loads(PENDING.read_text())
        if d.get("status") == "uploaded":
            return None
        return d.get("prerendered_yt_video_id")
    except Exception:
        return None


def main():
    apply = "--apply" in sys.argv[1:]
    token = get_token()
    if not token:
        return 1
    keep = protected_id()
    if keep:
        print(f"protecting the pending episode's preview: {keep}\n")

    hdr = {"Authorization": f"Bearer {token}"}
    ch = requests.get(f"{API}/channels",
                      params={"part": "contentDetails", "mine": "true"},
                      headers=hdr, timeout=30).json().get("items", [])
    if not ch:
        print("Could not read the channel.")
        return 1
    playlist = ch[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, page = [], None
    while True:
        d = requests.get(f"{API}/playlistItems",
                         params={"part": "contentDetails", "playlistId": playlist,
                                 "maxResults": 50, "pageToken": page or ""},
                         headers=hdr, timeout=30).json()
        ids += [i["contentDetails"]["videoId"] for i in d.get("items", [])
                if i.get("contentDetails", {}).get("videoId")]
        page = d.get("nextPageToken")
        if not page:
            break

    stranded = []
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos",
                         params={"part": "snippet,status", "id": ",".join(ids[i:i + 50])},
                         headers=hdr, timeout=30).json()
        for v in r.get("items", []):
            sn, st = v.get("snippet", {}) or {}, v.get("status", {}) or {}
            if v["id"] == keep:
                continue
            if st.get("privacyStatus") != "unlisted":
                continue
            # Exact match only. A partial match could catch a real episode
            # whose description merely mentions the phrase.
            if (sn.get("description") or "").strip() != PLACEHOLDER:
                continue
            stranded.append((v["id"], (sn.get("title") or "")[:60]))

    print(f"{len(ids)} video(s) on the channel.")
    print(f"stranded review previews: {len(stranded)}")
    for vid, title in stranded:
        print(f"   {vid}  {title}")
    if not stranded:
        print("\nNothing to clean up.")
        return 0
    if not apply:
        print("\nReport only. Re-run with --apply to delete these.")
        return 0

    print()
    for vid, title in stranded:
        d = requests.delete(f"{API}/videos", params={"id": vid},
                            headers=hdr, timeout=30)
        ok = d.status_code in (200, 204)
        print(f"{'deleted' if ok else f'FAILED {d.status_code}'}  {vid}  {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
