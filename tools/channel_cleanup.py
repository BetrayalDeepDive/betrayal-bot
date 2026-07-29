#!/usr/bin/env python3
"""
Bulk unlist or delete the existing videos on the Ch1 YouTube channel, ahead
of its repurposing to the clinical-case format.

WHY THIS EXISTS
---------------
The Ch1 channel carries dark-documentary episodes that will read as
off-brand once the channel publishes clinical case content. Those videos
can't be cleaned up from the build sandbox (the YouTube credentials are
GitHub secrets, present only on an Actions runner), so this runs there.

SAFETY POSTURE
--------------
Deleting a YouTube video is irreversible on YouTube's side -- there is no
trash can and no undo. Unlisting achieves the same "hidden from the channel"
outcome and IS reversible. Both are offered; nothing destructive happens
without two independent opt-ins:

  1. MODE must be set explicitly ("list" is the default and touches nothing)
  2. For MODE=delete, CONFIRM must equal the exact phrase DELETE_MY_VIDEOS

A wrong click therefore produces an inventory listing, never a deletion.

Every action is logged with the video ID and title before it happens, so the
run log is a usable record of what was removed.

Env:
  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN
  MODE     = list (default) | unlist | delete
  CONFIRM  = DELETE_MY_VIDEOS   (required only for MODE=delete)
  KEEP_IDS = optional comma-separated video IDs to spare
"""
import os
import sys
import time

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"

MODE = os.environ.get("MODE", "list").strip().lower()
CONFIRM = os.environ.get("CONFIRM", "").strip()
KEEP_IDS = {v.strip() for v in os.environ.get("KEEP_IDS", "").split(",") if v.strip()}
REQUIRED_CONFIRM = "DELETE_MY_VIDEOS"


def log(msg):
    print(msg, flush=True)


def get_token():
    cid = os.environ.get("YOUTUBE_CLIENT_ID", "")
    sec = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    ref = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    missing = [n for n, v in (("YOUTUBE_CLIENT_ID", cid),
                              ("YOUTUBE_CLIENT_SECRET", sec),
                              ("YOUTUBE_REFRESH_TOKEN", ref)) if not v]
    if missing:
        log(f"FATAL: missing secret(s): {', '.join(missing)}")
        sys.exit(1)
    r = requests.post(TOKEN_URL, data={
        "client_id": cid, "client_secret": sec,
        "refresh_token": ref, "grant_type": "refresh_token",
    }, timeout=30)
    d = r.json()
    if "access_token" not in d:
        log(f"FATAL: token refresh failed: {d.get('error')} — {d.get('error_description','')}")
        sys.exit(1)
    return d["access_token"]


def uploads_playlist_id(token):
    r = requests.get(f"{API}/channels", params={"part": "contentDetails", "mine": "true"},
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code != 200:
        log(f"FATAL: channels.list failed ({r.status_code}): {r.text[:300]}")
        sys.exit(1)
    items = r.json().get("items", [])
    if not items:
        log("FATAL: no channel returned for these credentials.")
        sys.exit(1)
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_all_videos(token, playlist_id):
    """Every video on the channel, paginated. (id, title, privacy)."""
    out, page = [], None
    while True:
        params = {"part": "snippet,status", "playlistId": playlist_id, "maxResults": 50}
        if page:
            params["pageToken"] = page
        r = requests.get(f"{API}/playlistItems", params=params,
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if r.status_code != 200:
            log(f"WARN: playlistItems failed ({r.status_code}): {r.text[:200]}")
            break
        data = r.json()
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            vid = (sn.get("resourceId") or {}).get("videoId")
            if vid:
                out.append((vid, sn.get("title", "(untitled)"),
                            (it.get("status") or {}).get("privacyStatus", "?")))
        page = data.get("nextPageToken")
        if not page:
            break
    return out


def set_unlisted(token, vid):
    """videos.update requires the full status object, not a partial patch."""
    r = requests.put(f"{API}/videos", params={"part": "status"},
                     headers={"Authorization": f"Bearer {token}",
                              "Content-Type": "application/json"},
                     json={"id": vid, "status": {"privacyStatus": "unlisted"}},
                     timeout=30)
    return r.status_code == 200, r.text[:200]


def delete_video(token, vid):
    r = requests.delete(f"{API}/videos", params={"id": vid},
                        headers={"Authorization": f"Bearer {token}"}, timeout=30)
    # 204 No Content is the documented success response.
    return r.status_code in (200, 204), r.text[:200]


def main():
    if MODE not in ("list", "unlist", "delete"):
        log(f"FATAL: MODE must be list, unlist or delete (got {MODE!r})")
        sys.exit(1)

    if MODE == "delete" and CONFIRM != REQUIRED_CONFIRM:
        log("REFUSING TO DELETE.")
        log(f"  MODE=delete requires CONFIRM={REQUIRED_CONFIRM} (got {CONFIRM!r}).")
        log("  Deleting a YouTube video is permanent — there is no undo.")
        log("  Consider MODE=unlist instead: same result, fully reversible.")
        sys.exit(1)

    token = get_token()
    videos = list_all_videos(token, uploads_playlist_id(token))

    log(f"\nFound {len(videos)} video(s) on the channel:\n")
    for vid, title, priv in videos:
        flag = "  [KEEP]" if vid in KEEP_IDS else ""
        log(f"  {vid}  [{priv:8}]  {title[:70]}{flag}")

    targets = [v for v in videos if v[0] not in KEEP_IDS]

    if MODE == "list":
        log(f"\nMODE=list — inventory only, nothing changed.")
        log(f"  {len(targets)} video(s) would be affected by unlist/delete.")
        log(f"  Re-run with MODE=unlist (reversible) or "
            f"MODE=delete + CONFIRM={REQUIRED_CONFIRM} (permanent).")
        return

    if not targets:
        log("\nNothing to do — no videos outside KEEP_IDS.")
        return

    verb = "Unlisting" if MODE == "unlist" else "DELETING"
    log(f"\n{verb} {len(targets)} video(s)...\n")

    ok_n = fail_n = 0
    for vid, title, _ in targets:
        if MODE == "unlist":
            ok, detail = set_unlisted(token, vid)
        else:
            ok, detail = delete_video(token, vid)
        if ok:
            ok_n += 1
            log(f"  OK    {vid}  {title[:64]}")
        else:
            fail_n += 1
            log(f"  FAIL  {vid}  {title[:64]}  -> {detail}")
        time.sleep(0.4)   # stay well clear of quota/rate limits

    log(f"\nDone. {ok_n} succeeded, {fail_n} failed.")
    if MODE == "delete" and ok_n:
        log("Deleted videos cannot be recovered from YouTube.")
    if fail_n:
        sys.exit(1)


if __name__ == "__main__":
    main()
