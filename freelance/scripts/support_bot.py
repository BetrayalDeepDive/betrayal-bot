#!/usr/bin/env python3
"""
DeepDive Empire — Support Bot v3.0
====================================
Monitors Gmail inbox every 30 min for client emails.
Auto-replies using Groq AI with professional responses.
Handles: general inquiries, order follow-ups, complaints,
         refund requests, revision requests, pricing questions.

FIXES IN v3.0:
- Rate limit protection with exponential backoff
- Proper App Password authentication (16-char)
- Detailed Telegram error messages with exact fix instructions
- Skips automated senders, bounce messages, no-reply addresses
- HTML + plain text dual email format
- 7 email type classifications
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
GMAIL_USER     = os.environ.get("GMAIL_USER", "mohammedsultan0497@gmail.com")
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASSWORD"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

groq_client = Groq(api_key=GROQ_API_KEY)

# ── CONFIG ────────────────────────────────────────────────────────────────────
IMAP_SERVER   = "imap.gmail.com"
IMAP_PORT     = 993
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SENDER_NAME   = "Mohammed Sultan"
BUSINESS_NAME = "DeepDive Intelligence / NextLayer Media"
MAX_EMAILS    = 10
REPLY_DELAY   = 3

# ── SENDERS TO SKIP ───────────────────────────────────────────────────────────
SKIP_SENDERS = [
    "noreply@", "no-reply@", "notifications@", "mailer-daemon@",
    "fiverr.com", "donotreply@", "bounce@", "unsubscribe@",
    "automated@", "system@", "support@fiverr", "hello@fiverr",
    "replies@", "postmaster@"
]

# ── GROQ WITH RATE LIMIT PROTECTION ──────────────────────────────────────────
def call_groq(prompt, temp=0.7, tokens=600):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=tokens
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 60 * (2 ** attempt)
                print(f"   Groq rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    return None

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except Exception as e:
        print(f"Telegram error: {e}")

# ── EMAIL UTILITIES ───────────────────────────────────────────────────────────
def safe_decode(value):
    if value is None:
        return ""
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
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        except:
            body = str(msg.get_payload())

    # Remove quoted content
    lines = body.split('\n')
    clean = []
    for line in lines:
        if line.startswith('>') or (line.startswith('On ') and 'wrote:' in line):
            break
        clean.append(line)
    return '\n'.join(clean).strip()[:2000]

def classify_email(subject, body):
    text = (subject + " " + body).lower()
    if any(w in text for w in ["refund", "money back", "cancel order", "cancellation"]):
        return "refund_request"
    elif any(w in text for w in ["complaint", "not satisfied", "unhappy", "terrible", "awful", "bad quality", "disappointed"]):
        return "complaint"
    elif any(w in text for w in ["when will", "status", "update", "where is", "delivery", "progress", "eta"]):
        return "order_status"
    elif any(w in text for w in ["revision", "change", "modify", "update my", "edit", "redo"]):
        return "revision_request"
    elif any(w in text for w in ["price", "cost", "how much", "quote", "pricing", "package", "rate"]):
        return "pricing_inquiry"
    elif any(w in text for w in ["order", "purchase", "bought", "payment", "invoice", "receipt"]):
        return "order_inquiry"
    else:
        return "general_inquiry"

# ── REPLY GENERATION ──────────────────────────────────────────────────────────
def generate_reply(sender_name, subject, body, email_type):
    context_map = {
        "refund_request":   "Client is requesting a refund. Be empathetic, acknowledge the concern, explain you will review within 24 hours. Do not promise a refund directly.",
        "complaint":        "Client is unhappy. Be extremely empathetic, apologize genuinely, offer a specific resolution such as revision or escalation.",
        "order_status":     "Client is asking about order status. Confirm you are checking and will provide a full update within 2-4 hours.",
        "revision_request": "Client wants revisions. Confirm receipt, acknowledge requirements, say you will begin within 24 hours.",
        "pricing_inquiry":  "Client is asking about pricing. Mention three packages: Basic $10 / Standard $25 / Premium $55. Direct them to Fiverr for current details.",
        "order_inquiry":    "Client has an order question. Answer professionally and offer to assist.",
        "general_inquiry":  "General client question. Answer helpfully and professionally.",
    }

    prompt = f"""You are a professional customer support representative for {BUSINESS_NAME}.

CLIENT: {sender_name or 'Valued Client'}
SUBJECT: {subject}
MESSAGE: {body[:600]}
CONTEXT: {context_map.get(email_type, 'General inquiry')}

Write a professional, warm, helpful email reply.
Rules:
1. Start with: Dear {sender_name or 'Valued Client'},
2. Maximum 4 short paragraphs
3. Be specific to their actual concern
4. Never make promises you cannot keep
5. End EXACTLY with:
Best regards,
{SENDER_NAME}
{BUSINESS_NAME}
Response time: Within 24 hours

Return only the email body — no subject line."""

    result = call_groq(prompt, temp=0.7, tokens=500)
    if result:
        return result.strip()

    # Fallback reply
    return f"""Dear {sender_name or 'Valued Client'},

Thank you for reaching out to {BUSINESS_NAME}. We have received your message regarding "{subject}" and will review it promptly.

A member of our team will respond with a detailed reply within 24 hours. We appreciate your patience.

Best regards,
{SENDER_NAME}
{BUSINESS_NAME}
Response time: Within 24 hours"""

# ── SEND REPLY ────────────────────────────────────────────────────────────────
def send_reply(to_email, to_name, subject, body):
    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"{SENDER_NAME} <{GMAIL_USER}>"
        msg['To']      = f"{to_name} <{to_email}>" if to_name else to_email
        msg['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        msg['Reply-To'] = GMAIL_USER

        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;padding:20px">
{body.replace(chr(10), '<br>')}
</body></html>"""
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"   Replied to: {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        msg = (f"<b>Support Bot — SMTP Auth Failed</b>\n\n"
               f"Error: {str(e)}\n\n"
               f"<b>Fix:</b>\n"
               f"1. Go to myaccount.google.com\n"
               f"2. Security → App Passwords\n"
               f"3. Generate new password for 'Mail'\n"
               f"4. Update GMAIL_APP_PASSWORD in GitHub Secrets")
        telegram(msg)
        print(f"   SMTP auth failed: {e}")
        return False
    except Exception as e:
        print(f"   Send failed: {e}")
        return False

# ── IMAP CONNECTION ───────────────────────────────────────────────────────────
def connect_imap():
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(GMAIL_USER, GMAIL_APP_PASS)
        return imap
    except imaplib.IMAP4.error as e:
        if "AUTHENTICATIONFAILED" in str(e) or "Invalid credentials" in str(e):
            telegram(f"<b>Support Bot — Gmail Auth Failed</b>\n\n"
                    f"Error: {str(e)}\n\n"
                    f"<b>Fix required:</b>\n"
                    f"1. myaccount.google.com → Security\n"
                    f"2. Enable 2-Step Verification (must be ON)\n"
                    f"3. App Passwords → Generate for Mail → DeepDive Bot\n"
                    f"4. Update GMAIL_APP_PASSWORD in GitHub Secrets\n\n"
                    f"Current password appears wrong or expired.")
        raise

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\nSupport Bot v3.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Account: {GMAIL_USER}")

    replied = skipped = errors = 0

    try:
        print("Connecting to Gmail...")
        imap = connect_imap()
        print("Connected")

        imap.select("INBOX")
        since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        status, messages = imap.search(None, f'UNSEEN SINCE {since}')

        if status != "OK" or not messages[0]:
            print("No unread emails in last 24 hours")
            imap.logout()
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} unread email(s)")

        for msg_id in reversed(email_ids[-MAX_EMAILS:]):
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                sender_raw  = safe_decode(msg.get("From", ""))
                subject     = safe_decode(msg.get("Subject", "(No Subject)"))

                sender_match = re.search(r'<([^>]+)>', sender_raw)
                sender_email = sender_match.group(1).lower() if sender_match else sender_raw.lower()
                sender_name  = re.sub(r'<[^>]+>', '', sender_raw).strip().strip('"')

                print(f"\n  From: {sender_email}")
                print(f"  Subject: {subject[:60]}")

                # Skip automated senders
                if any(skip in sender_email for skip in SKIP_SENDERS):
                    print(f"  Skipped (automated sender)")
                    imap.store(msg_id, '+FLAGS', '\\Seen')
                    skipped += 1
                    continue

                if sender_email == GMAIL_USER.lower():
                    imap.store(msg_id, '+FLAGS', '\\Seen')
                    skipped += 1
                    continue

                body = extract_body(msg)
                if not body:
                    print(f"  Skipped (empty body)")
                    imap.store(msg_id, '+FLAGS', '\\Seen')
                    skipped += 1
                    continue

                email_type = classify_email(subject, body)
                print(f"  Type: {email_type}")

                reply = generate_reply(sender_name, subject, body, email_type)
                success = send_reply(sender_email, sender_name, subject, reply)

                if success:
                    imap.store(msg_id, '+FLAGS', '\\Seen')
                    replied += 1
                    time.sleep(REPLY_DELAY)
                else:
                    errors += 1

            except Exception as e:
                print(f"  Error processing email: {e}")
                errors += 1
                continue

        imap.logout()

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        telegram(f"<b>Support Bot Error</b>\n{str(e)[:250]}")
        sys.exit(1)

    print(f"\nDone: {replied} replied | {skipped} skipped | {errors} errors")

    if replied > 0 or errors > 0:
        telegram(f"<b>Support Bot Complete</b>\n"
                f"Replied: {replied}\n"
                f"Skipped: {skipped}\n"
                f"Errors: {errors}")

if __name__ == "__main__":
    main()
