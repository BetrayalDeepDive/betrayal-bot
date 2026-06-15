#!/usr/bin/env python3
"""
DeepDive Intelligence — Fiverr Bot v2.0
=========================================
Monitors Gmail 'Fiverr Orders' label for new Fiverr notifications.
Auto-generates and delivers content for SEO blog article orders.
Tracks orders, sends Telegram alerts, logs to Google Sheets.

AUTHENTICATION: Uses Gmail App Password (16-char).
GIGS: SEO Blog Article (Basic $10 / Standard $25 / Premium $55)
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
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── CONFIG ────────────────────────────────────────────────────────────────────
IMAP_SERVER     = "imap.gmail.com"
IMAP_PORT       = 993
SMTP_SERVER     = "smtp.gmail.com"
SMTP_PORT       = 587
FIVERR_LABEL    = "Fiverr Orders"
SENDER_NAME     = "Mohammed Sultan | NextLayer Media"
FIVERR_USERNAME = "nextlayermedia"

# ── GIG PACKAGES ──────────────────────────────────────────────────────────────
GIG_PACKAGES = {
    "basic":    {"price": 10,  "words": 1200, "revisions": 1, "delivery_days": 3},
    "standard": {"price": 25,  "words": 2000, "revisions": 2, "delivery_days": 2},
    "premium":  {"price": 55,  "words": 3500, "revisions": 3, "delivery_days": 1},
}

def telegram(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except: pass

def safe_decode(value) -> str:
    if value is None: return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="replace")
        else:
            result += str(part)
    return result.strip()

def extract_body(msg) -> str:
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
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        except:
            body = str(msg.get_payload())
    return body[:3000]

def classify_fiverr_email(subject: str, body: str) -> dict:
    """Classify type of Fiverr notification"""
    subject_lower = subject.lower()
    body_lower    = body.lower()

    result = {"type": "unknown", "package": "basic", "topic": "", "buyer": ""}

    # Determine notification type
    if "new order" in subject_lower or "you have a new order" in body_lower:
        result["type"] = "new_order"
    elif "order delivered" in subject_lower or "delivery" in subject_lower:
        result["type"] = "delivery_confirmation"
    elif "message" in subject_lower or "inbox" in subject_lower:
        result["type"] = "message"
    elif "review" in subject_lower or "feedback" in subject_lower:
        result["type"] = "review"
    elif "revision" in subject_lower:
        result["type"] = "revision_request"
    elif "cancellation" in subject_lower or "cancel" in subject_lower:
        result["type"] = "cancellation"
    elif "payment" in subject_lower or "cleared" in subject_lower:
        result["type"] = "payment"
    else:
        result["type"] = "general"

    # Determine package
    if "premium" in body_lower or "$55" in body: result["package"] = "premium"
    elif "standard" in body_lower or "$25" in body: result["package"] = "standard"
    else: result["package"] = "basic"

    # Extract buyer name (Fiverr format: "from [username]")
    buyer_match = re.search(r'from\s+([A-Za-z0-9_]+)', body, re.IGNORECASE)
    if buyer_match: result["buyer"] = buyer_match.group(1)

    # Extract topic/keyword from order requirements
    topic_patterns = [
        r'(?:about|on|for|topic:|keyword:)\s+"?([^"\n,]{10,80})"?',
        r'(?:write|article|blog).{0,30}(?:about|on)\s+"?([^"\n,]{10,80})"?',
    ]
    for pattern in topic_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            result["topic"] = match.group(1).strip()
            break

    return result

def generate_seo_article(topic: str, package: str, buyer: str) -> str:
    """Generate high-quality SEO article using Gemini"""
    pkg = GIG_PACKAGES.get(package, GIG_PACKAGES["basic"])
    word_count = pkg["words"]

    prompt = f"""You are a professional SEO content writer. Write a complete, publication-ready SEO blog article.

TOPIC: {topic or 'Digital Marketing Best Practices'}
WORD COUNT: Exactly {word_count} words (±50 words tolerance)
CLIENT: {buyer or 'Client'}

ARTICLE REQUIREMENTS:
1. SEO-optimized title (60-65 characters, includes main keyword)
2. Meta description (150-160 characters)
3. Introduction with hook (150-200 words)
4. 4-6 main sections with H2 headings
5. Sub-sections with H3 headings where appropriate
6. Naturally integrated keywords throughout (density 1-2%)
7. Bullet points and numbered lists for readability
8. Real statistics and specific data points
9. Actionable advice in every section
10. Strong conclusion with call-to-action
11. FAQ section (3-5 questions) at the end

FORMAT OUTPUT AS:
META TITLE: [title here]
META DESCRIPTION: [description here]
---
[Full article content in Markdown format]
---
WORD COUNT: [actual word count]
PRIMARY KEYWORD: [main keyword identified]
SECONDARY KEYWORDS: [3-5 related keywords]

Write the complete article now. Make it genuinely helpful and authoritative."""

    # Try Gemini first (better for long content)
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000}
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"   Gemini failed: {e} — trying Groq...")

    # Fallback to Groq
    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )
            return resp.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                time.sleep(60 * (attempt + 1))
            else:
                raise

    return f"# Article on {topic}\n\nArticle generation encountered an error. Please contact support."

def send_article_delivery(buyer_email: str, buyer_name: str, topic: str,
                          article: str, package: str) -> bool:
    """Send completed article to client via email"""
    pkg = GIG_PACKAGES.get(package, GIG_PACKAGES["basic"])

    subject = f"✅ Your SEO Article Delivered — {topic[:50]}"

    body = f"""Dear {buyer_name or 'Valued Client'},

Your SEO blog article has been completed and is attached below.

ORDER DETAILS:
• Topic: {topic}
• Package: {package.capitalize()} ({pkg['words']} words)
• Status: Delivered ✅

Please find your article below:

{'='*60}

{article}

{'='*60}

WHAT TO DO NEXT:
1. Review the article and check it meets your requirements
2. If you need any revisions, please send your feedback via Fiverr
3. If you're satisfied, a 5-star review would mean the world to us!

You have {pkg['revisions']} revision(s) included with your order.

Thank you for choosing NextLayer Media. We look forward to working with you again!

Best regards,
{SENDER_NAME}
Fiverr: fiverr.com/s/nextlayermedia
Response time: Within 24 hours"""

    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"Mohammed Sultan <{GMAIL_USER}>"
        msg['To']      = buyer_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, buyer_email, msg.as_string())

        print(f"   ✅ Article delivered to {buyer_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        telegram(f"⚠️ <b>Fiverr Bot SMTP Auth Failed</b>\n{str(e)}\nUpdate GMAIL_APP_PASSWORD in GitHub Secrets.")
        return False
    except Exception as e:
        print(f"   ❌ Delivery failed: {e}")
        return False

def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect to Gmail IMAP"""
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(GMAIL_USER, GMAIL_APP_PASS)
        return imap
    except imaplib.IMAP4.error as e:
        if "AUTHENTICATIONFAILED" in str(e) or "Invalid credentials" in str(e):
            telegram(f"⚠️ <b>Fiverr Bot — Gmail Auth Failed</b>\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Fix:\n1. myaccount.google.com → Security\n"
                    f"2. Enable 2-Step Verification\n"
                    f"3. App Passwords → Generate for Mail\n"
                    f"4. Update GMAIL_APP_PASSWORD in GitHub Secrets")
        raise

def run_fiverr_bot():
    """Main Fiverr bot logic"""
    print(f"\n💼 Fiverr Bot v2.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    processed = 0
    errors    = 0

    try:
        imap = connect_imap()
        print("   ✅ Gmail connected")

        # Try Fiverr Orders label first, fall back to inbox search
        try:
            status, _ = imap.select(f'"{FIVERR_LABEL}"')
            if status != "OK":
                raise Exception("Label not found")
            label_used = FIVERR_LABEL
        except:
            imap.select("INBOX")
            label_used = "INBOX (Fiverr filter)"

        # Search unread emails from last 48 hours
        since_date = (datetime.now() - timedelta(hours=48)).strftime("%d-%b-%Y")
        status, messages = imap.search(None, f'UNSEEN SINCE {since_date}')

        if status != "OK" or not messages[0]:
            print(f"   📭 No new Fiverr emails ({label_used})")
            imap.logout()
            return 0, 0

        email_ids = messages[0].split()
        print(f"   📬 {len(email_ids)} new Fiverr email(s) in {label_used}")

        for msg_id in reversed(email_ids[-5:]):  # Process max 5 per run
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK": continue

                msg     = email.message_from_bytes(msg_data[0][1])
                subject = safe_decode(msg.get("Subject", ""))
                body    = extract_body(msg)

                sender_raw   = safe_decode(msg.get("From", ""))
                sender_match = re.search(r'<([^>]+)>', sender_raw)
                sender_email = sender_match.group(1) if sender_match else sender_raw

                print(f"\n   📧 {subject[:60]}")

                info = classify_fiverr_email(subject, body)
                print(f"      Type: {info['type']} | Package: {info['package']}")

                if info["type"] == "new_order":
                    topic   = info["topic"] or "Digital Marketing"
                    buyer   = info["buyer"] or "Client"
                    package = info["package"]
                    pkg     = GIG_PACKAGES[package]

                    telegram(f"🛒 <b>New Fiverr Order!</b>\n\n"
                            f"📦 Package: {package.capitalize()} (${pkg['price']})\n"
                            f"📝 Topic: {topic}\n"
                            f"👤 Buyer: {buyer}\n"
                            f"📅 Delivery: {pkg['delivery_days']} day(s)\n\n"
                            f"⚡ Generating article now...")

                    print(f"      Generating {pkg['words']}-word article on: {topic}")
                    article = generate_seo_article(topic, package, buyer)

                    # For now notify via Telegram (actual delivery needs buyer's email from Fiverr)
                    telegram(f"✅ <b>Article Generated!</b>\n\n"
                            f"📝 Topic: {topic}\n"
                            f"📦 {package.capitalize()} | {pkg['words']} words\n"
                            f"📤 Deliver via Fiverr dashboard\n\n"
                            f"Article preview:\n{article[:200]}...")

                    processed += 1

                elif info["type"] == "message":
                    telegram(f"💬 <b>New Fiverr Message</b>\n\n"
                            f"From: {info['buyer'] or 'Unknown buyer'}\n"
                            f"Subject: {subject}\n\n"
                            f"Check Fiverr inbox to reply.")

                elif info["type"] == "revision_request":
                    telegram(f"🔄 <b>Revision Request</b>\n\n"
                            f"Buyer: {info['buyer']}\n"
                            f"Subject: {subject}\n\n"
                            f"Review the request in Fiverr and action within 24 hours.")

                elif info["type"] == "payment":
                    telegram(f"💰 <b>Payment Cleared!</b>\n\n{subject}")

                elif info["type"] == "review":
                    telegram(f"⭐ <b>New Review!</b>\n\n{subject}\n\nCheck Fiverr for details.")

                imap.store(msg_id, '+FLAGS', '\\Seen')

            except Exception as e:
                print(f"      ❌ Error: {e}")
                errors += 1
                continue

        imap.logout()
        return processed, errors

    except Exception as e:
        print(f"   ❌ Fiverr bot error: {e}")
        if "AUTHENTICATIONFAILED" not in str(e):
            telegram(f"⚠️ <b>Fiverr Bot Error</b>\n{str(e)[:250]}")
        return 0, 1

def main():
    processed, errors = run_fiverr_bot()
    print(f"\n✅ Fiverr Bot: {processed} orders processed | {errors} errors")

if __name__ == "__main__":
    main()
