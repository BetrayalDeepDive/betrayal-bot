#!/usr/bin/env python3
"""
telegram_job_drafter.py
=========================
THE REAL, GENUINELY FREE FIX — no Upwork paid plan involved anywhere in
this file. This exists because Upwork's own free alert paths are both
gated behind requirements a new account doesn't have yet: instant
alerts need Freelancer Plus (paid) + a prior proposal, and the job
digest email needs Rising Talent/Top Rated status (earned reputation).
Confirmed directly against Upwork's own help documentation, not assumed.

How this actually works, honestly, start to finish:
  1. You browse Upwork's "Find Work" page yourself, using your saved
     search, for a few minutes whenever it suits you. This part is
     manual — there's no way around that until Upwork's own free
     alert paths unlock for your account naturally over time.
  2. When you see a real job worth pursuing, you copy the job title
     and description.
  3. You paste that text as a message to your own Telegram bot.
  4. This script (running on a schedule) picks up that message, scores
     it against your real service catalog, drafts a proposal with AI,
     and replies to you on Telegram with the score and the draft.
  5. You read it, edit if you want, and paste it into Upwork yourself
     to submit. Nothing here ever touches Upwork's site directly —
     it only reads Telegram messages you send it and replies.

This reuses the exact same scoring and drafting logic already built
and tested in upwork_assistant.py — nothing duplicated, nothing new
invented, just a different, genuinely free trigger instead of an email
that doesn't exist yet for your account.

ENV VARS needed (all already set up): GROQ_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import os, sys, time, requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from upwork_assistant import score_job, draft_proposal, tg, REAL_SERVICES

TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
OFFSET_FILE = "telegram_offset.txt"


def _load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE) as f:
                return int(f.read().strip())
        except Exception:
            return None
    return None


def _save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def get_new_messages():
    """
    Real Telegram getUpdates call — reads any new messages sent to your
    bot since the last check. Uses a saved offset so the same message
    never gets processed twice across separate runs.
    """
    offset = _load_offset()
    params = {"timeout": 5}
    if offset:
        params["offset"] = offset + 1
    try:
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                          params=params, timeout=15)
        if r.status_code != 200:
            return []
        return r.json().get("result", [])
    except Exception as e:
        print(f"getUpdates failed: {e}")
        return []


def parse_pasted_job(text):
    """
    Splits a pasted job posting into a title (first line) and
    description (everything else) — matches however someone naturally
    copy-pastes a job listing: title on top, details below.
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return None
    title = lines[0][:150]
    description = " ".join(lines[1:])[:1500] if len(lines) > 1 else lines[0][:1500]
    return {"title": title, "budget": "Not specified", "description": description}


def main():
    updates = get_new_messages()
    if not updates:
        print("No new Telegram messages.")
        return

    last_offset = None
    processed = 0

    for update in updates:
        last_offset = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))

        # Only process messages from your own configured chat, and
        # ignore anything too short to plausibly be a real job posting
        if chat_id != str(TG_CHAT) or len(text) < 40:
            continue
        if text.startswith("/"):
            continue  # skip bot commands, not job pastes

        job = parse_pasted_job(text)
        if not job:
            continue

        score = score_job(job)
        print(f"Processing pasted job: {job['title'][:60]} | Score: {score}/10")

        if score >= 3:  # lower bar than the email version, since you already manually chose to paste this
            proposal = draft_proposal(job)
            tg(f"📋 <b>Job Draft Ready (relevance {score}/10)</b>\n\n"
               f"<b>{job['title'][:100]}</b>\n\n"
               f"<b>Draft proposal (review, edit, then submit yourself on Upwork):</b>\n\n"
               f"{proposal}")
        else:
            tg(f"⚠️ Low relevance match ({score}/10) for '{job['title'][:60]}' — "
               f"drafted anyway in case you still want it:\n\n{draft_proposal(job)}")
        processed += 1

    if last_offset is not None:
        _save_offset(last_offset)

    print(f"Done. {processed} pasted job(s) processed.")


if __name__ == "__main__":
    main()
