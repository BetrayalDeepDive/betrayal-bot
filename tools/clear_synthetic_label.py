#!/usr/bin/env python3
"""
Clear the "Made with AI / Altered or synthetic content" label from videos
this channel ALREADY published.

WHY THIS IS SEPARATE FROM THE PIPELINE FIX
------------------------------------------
The pipeline change (DECLARE_SYNTHETIC_MEDIA, default off) only affects
uploads made from now on. Videos already on the channel keep whatever was
declared at the moment they were uploaded — which was `True`, on every one,
because that value was hardcoded into the upload payload with a comment
calling it mandatory. It is not mandatory for this format: the disclosure
requirement is for REALISTIC content a viewer could mistake for a real
person, place, scene or event, and AI narration over rendered charts and
diagrams is on the exempt list, alongside AI-written scripts.

So the back catalogue is carrying a label it does not owe, and on a health
channel that label is the prominent on-player kind rather than a line in the
expanded description.

WHAT THIS DOES
--------------
Reads every video on the channel, reports which ones currently declare
synthetic media, and — with --apply — sends videos.update to clear the flag.
Without --apply it changes nothing and just shows you the list.

THE API IS BLIND HERE — PROVEN, NOT ASSUMED
-------------------------------------------
videos.list does not return containsSyntheticMedia. Measured on 2026-08-02:
all 7 videos on this channel came back with the field absent, even though
every one was uploaded with it hardcoded True and at least one visibly
carries the label in Studio right now.

That has two consequences this tool is built around:
  * It cannot list which videos are flagged. So it does not try to filter —
    every video gets the clear attempt. (An earlier version filtered on the
    read, found 0, and cheerfully reported "nothing to do" on a channel
    where the label was on screen.)
  * A 200 from the update means ACCEPTED, not VERIFIED. Nothing in the
    response can confirm the label is gone.

The only real read is the Studio UI, which is also the manual route if the
API refuses:

    YouTube Studio -> Content -> select the video -> Edit -> "Altered content"
    -> answer No -> Save

Usage:
    python tools/clear_synthetic_label.py            # report only
    python tools/clear_synthetic_label.py --apply    # actually clear it

Needs the same secrets the pipeline uses: YOUTUBE_CLIENT_ID,
YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.
"""
import json
import os
import sys

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"


def get_token():
    cid = os.environ.get("YOUTUBE_CLIENT_ID", "")
    sec = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    ref = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    missing = [n for n, v in (("YOUTUBE_CLIENT_ID", cid),
                              ("YOUTUBE_CLIENT_SECRET", sec),
                              ("YOUTUBE_REFRESH_TOKEN", ref)) if not v]
    if missing:
        print(f"Missing secret(s): {', '.join(missing)}")
        print("Run this inside the workflow, or export them locally.")
        return None
    r = requests.post(TOKEN_URL, data={
        "client_id": cid, "client_secret": sec,
        "refresh_token": ref, "grant_type": "refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        print(f"Token refresh failed: {d.get('error')} — "
              f"{d.get('error_description', '')}")
        return None
    return d["access_token"]


def uploads_playlist(token):
    r = requests.get(f"{API}/channels", params={"part": "contentDetails",
                                                "mine": "true"},
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    items = r.json().get("items", [])
    if not items:
        print(f"Could not read the channel: {r.status_code} {r.text[:200]}")
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def all_video_ids(token, playlist):
    ids, page = [], None
    while True:
        r = requests.get(f"{API}/playlistItems",
                         params={"part": "contentDetails", "playlistId": playlist,
                                 "maxResults": 50, "pageToken": page or ""},
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        d = r.json()
        for it in d.get("items", []):
            vid = it.get("contentDetails", {}).get("videoId")
            if vid:
                ids.append(vid)
        page = d.get("nextPageToken")
        if not page:
            return ids


def main():
    apply = "--apply" in sys.argv[1:]
    token = get_token()
    if not token:
        return 1
    pl = uploads_playlist(token)
    if not pl:
        return 1
    vids = all_video_ids(token, pl)
    print(f"{len(vids)} video(s) on the channel.\n")

    # PROVEN 2026-08-02: videos.list does NOT return containsSyntheticMedia.
    # All 7 videos on this channel read back with the field absent, despite
    # every one having been uploaded with it hardcoded True and at least one
    # visibly carrying the label in Studio. So there is no way to ask the API
    # "which videos are flagged?" -- an earlier version of this tool did
    # exactly that, found 0, and reported "nothing to do" on a channel where
    # the label was on screen.
    #
    # So we do not filter. Every video gets the clear attempt.
    flagged, cleared, refused = [], [], []
    for i in range(0, len(vids), 50):
        batch = vids[i:i + 50]
        r = requests.get(f"{API}/videos",
                         params={"part": "snippet", "id": ",".join(batch)},
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        for v in r.json().get("items", []):
            flagged.append((v["id"], (v.get("snippet", {}).get("title") or "")[:60]))

    print("NOTE: the API does not report containsSyntheticMedia on read, so")
    print("      which videos currently carry the label cannot be listed.")
    print("      Every video is treated as a candidate.\n")
    print(f"videos that would be cleared: {len(flagged)}")
    for vid, title in flagged:
        print(f"   {vid}  {title}")
    print()

    if not flagged:
        print("Nothing to do.")
        return 0
    if not apply:
        print("Report only. Re-run with --apply to send the clear.")
        return 0

    for vid, title in flagged:
        # part=status means the whole status object is replaced, so every
        # field being preserved has to be sent back explicitly. Dropping
        # privacyStatus here would silently republish a private video.
        cur = requests.get(f"{API}/videos", params={"part": "status", "id": vid},
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=30).json().get("items", [{}])[0].get("status", {})
        body = {"id": vid, "status": {
            "privacyStatus": cur.get("privacyStatus", "private"),
            "license": cur.get("license", "youtube"),
            "embeddable": cur.get("embeddable", True),
            "publicStatsViewable": cur.get("publicStatsViewable", True),
            "selfDeclaredMadeForKids": cur.get("selfDeclaredMadeForKids", False),
            "containsSyntheticMedia": False,
        }}
        r = requests.put(f"{API}/videos", params={"part": "status"},
                         headers={"Authorization": f"Bearer {token}",
                                  "Content-Type": "application/json"},
                         data=json.dumps(body), timeout=30)
        if r.status_code == 200:
            # 200 means the update was ACCEPTED, not that the label is gone.
            # The response echoes status without containsSyntheticMedia (see
            # the note above), so there is nothing here to check it against.
            # Verification is the Studio UI, not this exit code.
            cleared.append((vid, title))
        else:
            refused.append((vid, title, f"{r.status_code}: {r.text[:160]}"))

    print(f"\nupdate accepted (200) — NOT the same as verified: {len(cleared)}")
    for vid, title in cleared:
        print(f"   {vid}  {title}")
    if refused:
        print(f"\nNOT cleared: {len(refused)}")
        for vid, title, why in refused:
            print(f"   {vid}  {title}\n      {why}")
        print("\nThe API would not clear these. Do it by hand — this route works:")
        print("  YouTube Studio -> Content -> the video -> Edit ->")
        print("  'Altered content' -> answer No -> Save")
    print("\nNow go and LOOK. A 200 above only says YouTube accepted the")
    print("request; the API will not tell us whether the label is gone,")
    print("because it never reports this field back. Open one video in")
    print("Studio -> Edit -> 'Altered content' and confirm with your eyes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
