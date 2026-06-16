#!/usr/bin/env python3
"""
DeepDive Empire — Fiverr Bot v3.0
====================================
Monitors Gmail 'Fiverr Orders' label for new Fiverr notifications.
Auto-generates SEO articles for orders using Gemini + Groq.
Sends Telegram alerts for: new orders, messages, revisions, payments, reviews.

FIXES IN v3.0:
- Rate limit protection on both Groq and Gemini
- Better Fiverr email classification (more trigger words)
- Fallback to INBOX search if Fiverr Orders label missing
- Article generation uses Gemini first (better for long content)
- Detailed Telegram alerts for every order event
- Auth failure sends exact fix instructions to Telegram
"""

import os, sys, json, re, time, imaplib, smtplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
import requests
from groq import Groq

# ── CREDENTIALS ───────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GMAIL_USER     = os.environ.get("GMAIL_USER", "mohammedsultan0497@gmail.com")
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASSWORD"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

groq_client = Groq(api_key=GROQ_API_KEY)
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── CONFIG ────────────────────────────────────────────────────────────────────
IMAP_SERVER     = "imap.gmail.com"
IMAP_PORT       = 993
SMTP_SERVER     = "smtp.gmail.com"
SMTP_PORT       = 587
FIVERR_LABEL    = "Fiverr Orders"
SENDER_NAME     = "Mohammed Sultan | NextLayer Media"
FIVERR_USERNAME = "nextlayermedia"
FIVERR_GIG_URL  = "https://www.fiverr.com/nextlayermedia"

GIG_PACKAGES = {
    "basic":    {"price": 10,  "words": 1200, "revisions": 1, "delivery_days": 3},
    "standard": {"price": 25,  "words": 2000, "revisions": 2, "delivery_days": 2},
    "premium":  {"price": 55,  "words": 3500, "revisions": 3, "delivery_days": 1},
}

# ── AI CALLERS WITH RATE LIMIT PROTECTION ────────────────────────────────────
def call_gemini(prompt, temp=0.7, tokens=4000):
    for attempt in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temp, "maxOutputTokens": tokens}
                },
                timeout=120
            )
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif r.status_code == 429:
                time.sleep(60 * (attempt + 1))
            else:
                time.sleep(10)
        except Exception as e:
            print(f"   Gemini attempt {attempt+1}: {str(e)[:60]}")
            time.sleep(15)
    raise Exception("Gemini failed")

def call_groq(prompt, temp=0.7, tokens=800):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=min(tokens, 2000)
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 60 * (2 ** attempt)
                print(f"   Groq rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Groq rate limited")

def call_ai(prompt, temp=0.7, tokens=4000):
    """Gemini first for long content, Groq fallback"""
    try:
        return call_gemini(prompt, temp, tokens)
    except:
        return call_groq(prompt, temp, min(tokens, 2000))

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except: pass

# ── EMAIL UTILITIES ───────────────────────────────────────────────────────────
def safe_decode(value):
    if value is None: return ""
    result = ""
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="replace")
        else:
            result += str(part)
    return result.strip()

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
                except: continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace")
        except:
            body = str(msg.get_payload())
    return body[:3000]

def classify_fiverr_email(subject, body):
    """Classify Fiverr notification type"""
    subject_l = subject.lower()
    body_l    = body.lower()
    result    = {"type": "unknown", "package": "basic", "topic": "", "buyer": ""}

    # Determine type
    if any(x in subject_l for x in ["new order", "you received an order", "order placed"]):
        result["type"] = "new_order"
    elif any(x in body_l for x in ["new order", "you have a new order", "order was placed"]):
        result["type"] = "new_order"
    elif any(x in subject_l for x in ["order delivered", "delivery confirmed", "delivered successfully"]):
        result["type"] = "delivery_confirmation"
    elif any(x in subject_l for x in ["new message", "sent you a message", "inbox"]):
        result["type"] = "message"
    elif any(x in subject_l for x in ["left you a review", "new review", "feedback"]):
        result["type"] = "review"
    elif any(x in subject_l for x in ["revision", "requested a revision", "modification"]):
        result["type"] = "revision_request"
    elif any(x in subject_l for x in ["cancellation", "cancel", "order cancelled"]):
        result["type"] = "cancellation"
    elif any(x in subject_l for x in ["payment cleared", "funds available", "earning"]):
        result["type"] = "payment"
    elif "fiverr" in subject_l or "fiverr" in body_l:
        result["type"] = "general_fiverr"

    # Package detection
    if "premium" in body_l or "$55" in body:
        result["package"] = "premium"
    elif "standard" in body_l or "$25" in body:
        result["package"] = "standard"
    else:
        result["package"] = "basic"

    # Buyer name
    buyer_match = re.search(r'(?:from|buyer|username)[:\s]+([A-Za-z0-9_]{3,20})', body, re.IGNORECASE)
    if buyer_match:
        result["buyer"] = buyer_match.group(1)

    # Topic/keyword extraction
    topic_patterns = [
        r'(?:about|on|topic|keyword|subject)[:\s]+"?([^"\n,]{10,80})"?',
        r'(?:write|article|blog|post).{0,30}(?:about|on)[:\s]+"?([^"\n,]{10,80})"?',
        r'(?:requirements?)[:\s]+([^"\n]{15,100})',
    ]
    for pattern in topic_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            result["topic"] = match.group(1).strip()[:100]
            break

    return result

# ── SEO ARTICLE GENERATION ────────────────────────────────────────────────────
def generate_seo_article(topic, package, buyer):
    pkg = GIG_PACKAGES.get(package, GIG_PACKAGES["basic"])
    word_count = pkg["words"]

    prompt = f"""You are a professional SEO content writer delivering work to a client named {buyer or 'Client'}.

Write a complete, publication-ready SEO blog article on this topic: {topic or 'Digital Marketing Best Practices for 2025'}

TARGET WORD COUNT: Exactly {word_count} words (+-50 words acceptable)

ARTICLE REQUIREMENTS:
1. SEO-optimized title (60-65 characters, includes main keyword)
2. Meta description (150-160 characters)
3. Compelling introduction with a hook
4. 4-6 main sections with H2 headings
5. Sub-sections with H3 headings where relevant
6. Keywords naturally integrated (1.5-2% density)
7. Bullet points and numbered lists for readability
8. Real statistics and specific data points
9. Actionable advice in every section
10. Strong conclusion with a call-to-action
11. FAQ section with 3-5 questions at the end

FORMAT:
META TITLE: [60-65 char title]
META DESCRIPTION: [150-160 char description]
---
[Full article in Markdown]
---
WORD COUNT: [actual count]
PRIMARY KEYWORD: [main keyword]
SECONDARY KEYWORDS: [3-5 related keywords]

Write the complete article now. Make it genuinely valuable and authoritative."""

    return call_ai(prompt, temp=0.72, tokens=4000)

# ── IMAP CONNECTION ───────────────────────────────────────────────────────────
def connect_imap():
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(GMAIL_USER, GMAIL_APP_PASS)
        return imap
    except imaplib.IMAP4.error as e:
        if "AUTHENTICATIONFAILED" in str(e) or "Invalid credentials" in str(e):
            telegram(f"<b>Fiverr Bot — Gmail Auth Failed</b>\n\n"
                    f"Error: {str(e)}\n\n"
                    f"<b>Fix:</b>\n"
                    f"1. myaccount.google.com → Security\n"
                    f"2. Enable 2-Step Verification\n"
                    f"3. App Passwords → Generate for Mail\n"
                    f"4. Update GMAIL_APP_PASSWORD in GitHub Secrets")
        raise

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\nFiverr Bot v3.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    processed = errors = 0

    try:
        imap = connect_imap()
        print("Gmail connected")

        # Try Fiverr Orders label first, fall back to inbox search
        label_used = "INBOX"
        try:
            status, _ = imap.select(f'"{FIVERR_LABEL}"')
            if status == "OK":
                label_used = FIVERR_LABEL
                print(f"Using label: {FIVERR_LABEL}")
            else:
                imap.select("INBOX")
                print("Label not found — searching INBOX for Fiverr emails")
        except:
            imap.select("INBOX")

        since = (datetime.now() - timedelta(hours=48)).strftime("%d-%b-%Y")

        if label_used == FIVERR_LABEL:
            status, messages = imap.search(None, f'UNSEEN SINCE {since}')
        else:
            # Search inbox for Fiverr emails specifically
            status, messages = imap.search(None, f'UNSEEN SINCE {since} FROM "fiverr.com"')

        if status != "OK" or not messages[0]:
            print(f"No new Fiverr emails found")
            imap.logout()
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} Fiverr email(s)")

        for msg_id in reversed(email_ids[-5:]):
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK": continue

                msg     = email.message_from_bytes(msg_data[0][1])
                subject = safe_decode(msg.get("Subject", ""))
                body    = extract_body(msg)

                print(f"\n  Email: {subject[:60]}")

                info = classify_fiverr_email(subject, body)
                print(f"  Type: {info['type']} | Package: {info['package']}")

                if info["type"] == "new_order":
                    topic   = info["topic"] or "Digital Marketing Best Practices 2025"
                    buyer   = info["buyer"] or "Client"
                    package = info["package"]
                    pkg     = GIG_PACKAGES[package]

                    telegram(f"<b>New Fiverr Order!</b>\n\n"
                            f"Package: {package.capitalize()} (${pkg['price']})\n"
                            f"Words: {pkg['words']}\n"
                            f"Topic: {topic}\n"
                            f"Buyer: {buyer}\n"
                            f"Delivery: {pkg['delivery_days']} day(s)\n\n"
                            f"Generating article now...")

                    print(f"  Generating {pkg['words']}w article on: {topic}")
                    article = generate_seo_article(topic, package, buyer)

                    # Preview first 300 chars
                    preview = article[:300].replace('\n', ' ')
                    telegram(f"<b>Article Generated!</b>\n\n"
                            f"Topic: {topic}\n"
                            f"Package: {package.capitalize()} | {pkg['words']}w\n\n"
                            f"Preview: {preview}...\n\n"
                            f"Deliver via Fiverr dashboard. "
                            f"Copy the full article from the Actions log.")

                    print(f"\n{'='*60}")
                    print("GENERATED ARTICLE (copy from here for delivery):")
                    print('='*60)
                    print(article)
                    print('='*60)
                    processed += 1

                elif info["type"] == "message":
                    telegram(f"<b>New Fiverr Message</b>\n\n"
                            f"From: {info['buyer'] or 'Buyer'}\n"
                            f"Subject: {subject}\n\n"
                            f"Check Fiverr inbox to reply promptly.")

                elif info["type"] == "revision_request":
                    telegram(f"<b>Revision Request</b>\n\n"
                            f"Buyer: {info['buyer']}\n"
                            f"Subject: {subject}\n\n"
                            f"Review the request and deliver revision within 24 hours.")

                elif info["type"] == "payment":
                    telegram(f"<b>Payment Cleared!</b>\n\n{subject}\n\nCheck Fiverr earnings.")

                elif info["type"] == "review":
                    telegram(f"<b>New Review!</b>\n\n{subject}\nCheck Fiverr for the full review.")

                elif info["type"] == "cancellation":
                    telegram(f"<b>Order Cancellation</b>\n\n{subject}\nCheck Fiverr for details.")

                imap.store(msg_id, '+FLAGS', '\\Seen')

            except Exception as e:
                print(f"  Error: {e}")
                errors += 1
                continue

        imap.logout()

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if "AUTHENTICATIONFAILED" not in str(e):
            telegram(f"<b>Fiverr Bot Error</b>\n{str(e)[:250]}")
        sys.exit(1)

    print(f"\nDone: {processed} orders processed | {errors} errors")

if __name__ == "__main__":
    main()
