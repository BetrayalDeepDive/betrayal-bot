#!/usr/bin/env python3
"""
Answer, with evidence, the one question code inspection cannot: does YouTube
apply the "Made with AI" label even when we declare containsSyntheticMedia
as false?

WHY A REAL UPLOAD IS THE ONLY WAY
---------------------------------
The pipeline now sends `containsSyntheticMedia: false` — that part is proven
by reading the payload. What is NOT provable from here is YouTube's own
behaviour: it can apply the label from its own detection, independently of
what an uploader declares. Reasoning about that is guessing. Uploading one
video and reading the answer back is not.

WHAT IT DOES
------------
  1. Renders a ~6 second clip with ffmpeg in the same shape a real episode
     has -- 1920x1080, h264, an AAC track -- because a probe that does not
     resemble the thing being tested proves nothing about it.
  2. Uploads it PRIVATE, with containsSyntheticMedia explicitly false.
  3. Reads the video's status straight back from the API.
  4. Prints what YouTube stored, and the verdict.
  5. Deletes it again unless --keep is passed.

Private means only the channel owner can see it. It never appears on the
channel, in search, or in subscriber feeds.

Usage:
    python tools/ai_label_probe.py           # upload, check, delete
    python tools/ai_label_probe.py --keep    # leave it up so you can look in Studio

Needs: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"


def token():
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
        print(f"Token refresh failed: {d.get('error')} "
              f"— {d.get('error_description','')}")
        return None
    return d["access_token"]


def render_probe(path):
    """A clip shaped like a real episode: 1080p h264 + AAC, ~6s."""
    cmd = ["ffmpeg", "-y",
           "-f", "lavfi", "-i", "color=c=0x101418:s=1920x1080:d=6",
           "-f", "lavfi", "-i", "sine=frequency=220:duration=6",
           "-vf", "drawtext=text='label probe':fontcolor=white:fontsize=64:"
                  "x=(w-text_w)/2:y=(h-text_h)/2",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-shortest", path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not os.path.exists(path):
        print("ffmpeg failed:\n" + r.stderr[-800:])
        return False
    return True


def main():
    keep = "--keep" in sys.argv[1:]
    tok = token()
    if not tok:
        return 1

    with tempfile.TemporaryDirectory() as td:
        vid_path = os.path.join(td, "probe.mp4")
        if not render_probe(vid_path):
            return 1
        size = os.path.getsize(vid_path)
        print(f"probe rendered: {size} bytes, 1920x1080 h264+aac\n")

        body = {
            "snippet": {
                "title": f"internal label probe {int(time.time())}",
                "description": "Private technical probe. Delete on sight.",
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
                "madeForKids": False,
                # THE WHOLE POINT OF THIS PROBE:
                "containsSyntheticMedia": False,
            },
        }
        print("declaring: containsSyntheticMedia = False\n")

        init = requests.post(
            f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status",
            headers={"Authorization": f"Bearer {tok}",
                     "Content-Type": "application/json",
                     "X-Upload-Content-Length": str(size),
                     "X-Upload-Content-Type": "video/mp4"},
            data=json.dumps(body), timeout=30)
        loc = init.headers.get("Location")
        if not loc:
            print(f"Upload init failed {init.status_code}: {init.text[:400]}")
            return 1
        with open(vid_path, "rb") as f:
            up = requests.put(loc, headers={"Content-Type": "video/mp4",
                                            "Content-Length": str(size)},
                              data=f, timeout=300)
        if up.status_code not in (200, 201):
            print(f"Upload failed {up.status_code}: {up.text[:400]}")
            return 1
        vid = up.json().get("id")
        print(f"uploaded (private): {vid}\n")

    # YouTube can take a moment to settle processing/labelling.
    verdict = None
    read_it = False
    last_status = {}
    for wait in (5, 15, 30, 60):
        time.sleep(wait)
        got = requests.get(f"{API}/videos",
                           params={"part": "status", "id": vid},
                           headers={"Authorization": f"Bearer {tok}"},
                           timeout=30).json()
        items = got.get("items", [])
        if not items:
            continue
        st = items[0].get("status", {}) or {}
        flag = st.get("containsSyntheticMedia")
        print(f"  +{wait}s  containsSyntheticMedia = {flag!r}  "
              f"(upload status: {st.get('uploadStatus')})")
        verdict = flag
        read_it = True
        last_status = st

    print()
    if read_it:
        print("full status object YouTube stored:")
        print(json.dumps(last_status, indent=2, sort_keys=True))
        print()
    if not read_it:
        # Never say "it held" on the strength of a read that never happened.
        print("RESULT: INCONCLUSIVE — the API never returned the video's")
        print("        status, so nothing was actually observed. Re-run, or")
        print(f"        check {vid} in Studio by hand.")
    elif verdict:
        print("RESULT: YouTube SET the flag despite us declaring false.")
        print("        The label will still appear. Our declaration is not")
        print("        the only input — their own detection overrode it.")
    else:
        # Observed 2026-08-02: YouTube does not echo the field back at all
        # when it is false — it only appears in the status object when it is
        # true. Absent and false are the same state here: nothing declared,
        # and nothing added by their own detection.
        print("RESULT: YouTube did not set containsSyntheticMedia.")
        print("        Our declaration held — the field comes back absent,")
        print("        which is how the API represents 'not declared'. No")
        print("        'Made with AI' label from the disclosure field.")
        print()
        print("        Caveat worth knowing: this probe is a plain colour")
        print("        card with a sine tone. It does not contain synthetic")
        print("        SPEECH. If YouTube's detection reacts to TTS narration")
        print("        specifically, a real episode could still differ — the")
        print("        only way to close that gap completely is one real")
        print("        episode uploaded private.")

    if keep:
        print(f"\nLeft up as PRIVATE for you to inspect: "
              f"https://studio.youtube.com/video/{vid}/edit")
    else:
        d = requests.delete(f"{API}/videos", params={"id": vid},
                            headers={"Authorization": f"Bearer {tok}"},
                            timeout=30)
        print(f"\ndeleted the probe: "
              f"{'yes' if d.status_code in (204, 200) else f'FAILED {d.status_code} — delete {vid} by hand'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
