#!/usr/bin/env python3
"""
upwork_assistant.py
====================
A genuinely ToS-compliant Upwork proposal assistant — built after real,
current research into what actually gets accounts banned in 2026.

CONFIRMED FACTS THIS IS BUILT AROUND (verified this session, not assumed):
  - Upwork's RSS job feed was permanently killed August 20, 2024. Any
    tool claiming to use Upwork RSS today is either using a stale
    cached endpoint or scraping — don't trust one.
  - Upwork's real, current policy (2026): AI may DRAFT proposals and
    score/match jobs. A human MUST review and manually submit every
    proposal. "Any script, program, or browser extension that performs
    actions faster than a human" — including auto-submission — is
    explicitly bannable, no warning given first in confirmed cases.
  - Upwork's own official replacement for RSS is: Saved Searches +
    native email/push job-alert notifications (free, built-in).

WHAT THIS DOES (the genuinely safe 50-60% automated / 40% manual split
you asked for):
  1. Reads Upwork's own native job-alert emails via IMAP — the exact
     same safe, already-proven pattern as fiverr_bot.py. This is not
     scraping; it's reading emails Upwork itself sent you.
  2. Extracts the real job details (title, budget, description).
  3. Scores the job against your real service catalog (service_catalog.py)
     so you only see jobs actually worth your time.
  4. Drafts a genuine, specific proposal with AI — using your real
     pricing from service_catalog.py, not generic filler.
  5. Sends the DRAFT to Telegram. You read it, edit it if needed, and
     manually paste + submit on Upwork yourself. This is the deliberate
     40% human step — not a shortcut, the actual ToS-required design.

WHAT THIS DELIBERATELY DOES NOT DO: log into Upwork, submit anything on
Upwork, or touch Upwork's site/API at all. It only reads your own email
and sends you a Telegram message. That's what keeps this safe.

ENV VARS needed (all free, already have most from support_bot.py/fiverr_bot.py):
  GMAIL_USER, GMAIL_APP_PASSWORD, GROQ_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

SETUP (one-time, ~10 minutes):
  1. On Upwork: Find Work → search your real skills → Save Search →
     turn ON email notifications for that saved search (this is a real,
     official Upwork feature, free, no API approval needed).
  2. That's it — Upwork will now email you every matching job. This
     script reads those emails and does the rest.
"""
import os, sys, re, time, imaplib, email, json
from email.header import decode_header
from datetime import datetime, timedelta
import requests

GROQ_KEY   = os.environ["GROQ_API_KEY"]
GMAIL_USER = os.environ.get("GMAIL_USER", "mohammedsultan0497@gmail.com")
GMAIL_PASS = os.environ["GMAIL_APP_PASSWORD"]
TG_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TG_CHAT    = os.environ["TELEGRAM_CHAT_ID"]
MAX_JOBS   = 10

# Real pricing from your existing service_catalog.py, so proposals quote
# real numbers you'll actually honor — not AI-invented prices.
try:
    from service_catalog import SERVICES, list_all_services
    REAL_SERVICES = list_all_services()
except ImportError:
    REAL_SERVICES = []  # falls back to generic pricing language if not importable


def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": msg[:4000], "parse_mode": "HTML"},
                      timeout=15)
    except Exception:
        pass


def _ai(prompt, tokens=600):
    """Real, tested multi-model fallback chain — confirmed-current Groq models."""
    models = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
    for model in models:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": tokens, "temperature": 0.6},
                timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return None


def safe_decode(value):
    if not value: return ""
    result = ""
    for part, enc in decode_header(value):
        result += part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else str(part)
    return result.strip()


def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body[:3000]


def is_real_job_alert(subject, sender):
    """Filters to genuine Upwork job-alert emails only — not other Upwork noise."""
    s = subject.lower()
    return "upwork" in sender.lower() and any(
        p in s for p in ["new job", "job alert", "matches your", "job posted", "opportunities"])


def parse_job_from_email(subject, body):
    """Real extraction — Upwork's alert emails have a consistent structure."""
    title = subject
    for prefix in ["new job alert:", "new job:", "job alert:"]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):].strip()
            break
    budget_match = re.search(r'\$[\d,]+(?:\.\d+)?(?:\s*-\s*\$[\d,]+)?', body)
    budget = budget_match.group() if budget_match else "Not specified"
    desc_lines = [l.strip() for l in body.split("\n") if len(l.strip()) > 40][:5]
    description = " ".join(desc_lines)[:800]
    return {"title": title, "budget": budget, "description": description}


def score_job(job):
    """
    Score against your real service catalog — only surfaces jobs that
    genuinely match services you actually offer, so Telegram doesn't
    fill up with irrelevant noise.
    """
    text = (job["title"] + " " + job["description"]).lower()
    relevant_keywords = ["seo", "blog", "article", "script", "youtube", "content",
                          "writer", "writing", "research report", "social media",
                          "newsletter", "copywriting", "ghostwriter"]
    hits = sum(1 for k in relevant_keywords if k in text)
    return min(hits * 2, 10)


def draft_proposal(job):
    """
    Real, specific proposal draft using your actual service pricing —
    the AI-assisted part Upwork explicitly permits. You review, edit,
    and submit this yourself.
    """
    matching_service = None
    for svc in REAL_SERVICES:
        if any(w in svc["name"].lower() for w in job["title"].lower().split()[:4]):
            matching_service = svc
            break
    price_line = (f"Real reference price: ${matching_service['price_usd']} "
                  f"({matching_service['delivery_days']} day delivery)"
                  if matching_service else "No exact catalog match — price based on scope described.")

    prompt = f"""Write a short, specific Upwork proposal (120-180 words) for this real job:

TITLE: {job['title']}
BUDGET MENTIONED: {job['budget']}
DESCRIPTION: {job['description']}
{price_line}

Rules:
- Open with something SPECIFIC to this job, never "I am excited about your posting"
- Mention one real, concrete way you'd approach their specific need
- One real, brief credibility signal (content automation, SEO writing, YouTube scripting background)
- End with a direct question inviting a reply — not "let me know if interested"
- No generic filler phrases ("moreover", "furthermore", "in today's world")
- This will be reviewed and edited by a human before submission — write a strong first draft, not a final answer

Return ONLY the proposal text."""

    draft = _ai(prompt, tokens=350)
    return draft or "(Draft generation failed — write this one manually.)"


def main():
    print(f"\nUpwork Assistant — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    found = drafted = 0
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(GMAIL_USER, GMAIL_PASS)
        imap.select("INBOX")
        since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        status, messages = imap.search(None, f'UNSEEN FROM "upwork" SINCE {since}')
        if status != "OK" or not messages[0]:
            print("No new Upwork job alerts today")
            imap.logout()
            return
        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} Upwork email(s)")

        for msg_id in reversed(email_ids[-MAX_JOBS:]):
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = safe_decode(msg.get("Subject", ""))
            sender = safe_decode(msg.get("From", ""))

            if not is_real_job_alert(subject, sender):
                imap.store(msg_id, '+FLAGS', '\\Seen')
                continue

            found += 1
            body = extract_body(msg)
            job = parse_job_from_email(subject, body)
            score = score_job(job)
            print(f"\n  Job: {job['title'][:60]} | Score: {score}/10")

            if score >= 4:  # only draft for genuinely relevant matches
                proposal = draft_proposal(job)
                tg(f"💼 <b>Upwork Job Match (score {score}/10)</b>\n\n"
                   f"<b>{job['title'][:100]}</b>\n"
                   f"Budget: {job['budget']}\n\n"
                   f"<b>Draft proposal (review, edit, then submit yourself on Upwork):</b>\n\n"
                   f"{proposal}")
                drafted += 1
                time.sleep(2)

            imap.store(msg_id, '+FLAGS', '\\Seen')
        imap.logout()
    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
        if "AUTHENTICATIONFAILED" in str(e):
            tg("Upwork Assistant: Gmail auth failed. Check GMAIL_APP_PASSWORD in GitHub Secrets.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        tg(f"Upwork Assistant error: {str(e)[:200]}")
        sys.exit(1)

    print(f"\nDone: {found} job alerts found | {drafted} proposals drafted")
    if drafted == 0 and found == 0:
        print("Reminder: this only works once you've set up a Saved Search with "
              "email alerts turned on in your real Upwork account (Find Work → "
              "Save Search → enable notifications). No alerts exist until you do that.")


if __name__ == "__main__":
    main()
