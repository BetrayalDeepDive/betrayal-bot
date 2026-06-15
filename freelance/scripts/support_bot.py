#!/usr/bin/env python3
"""
DeepDive Intelligence — Support Bot v2.0
=========================================
Monitors Gmail every 30 minutes for client emails.
Auto-replies using Groq AI with professional responses.
Handles: general inquiries, order follow-ups, complaints, refund requests.

AUTHENTICATION: Uses Gmail App Password (16-char) — NOT regular Gmail password.
ERROR HANDLING: Never crashes — logs all errors to Telegram.
"""

import os, sys, json, re, time, imaplib, smtplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
import requests
from groq import Groq

# ── CREDENTIALS ───────────────────────────────────────────────────────────────
GROQ_API_KEY      = os.environ["GROQ_API_KEY"]
GMAIL_USER        = os.environ.get("GMAIL_USER", "mohammedsultan0497@gmail.com")
GMAIL_APP_PASS    = os.environ["GMAIL_APP_PASSWORD"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT     = os.environ["TELEGRAM_CHAT_ID"]

groq_client = Groq(api_key=GROQ_API_KEY)

# ── CONFIG ────────────────────────────────────────────────────────────────────
IMAP_SERVER   = "imap.gmail.com"
IMAP_PORT     = 993
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
BUSINESS_NAME = "DeepDive Intelligence / NextLayer Media"
SENDER_NAME   = "Mohammed Sultan"
MAX_EMAILS    = 10   # Process max 10 emails per run to avoid timeouts
REPLY_DELAY   = 2    # Seconds between replies to avoid spam flags

# ── EMAIL CATEGORIES ──────────────────────────────────────────────────────────
SKIP_SENDERS = [
    "noreply@", "no-reply@", "notifications@", "mailer-daemon@",
    "fiverr.com", "donotreply@", "bounce@", "unsubscribe@"
]

def telegram(msg: str):
    """Send Telegram notification"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def safe_decode(value) -> str:
    """Safely decode email header values"""
    if value is None:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(encoding or "utf-8", errors="replace")
            except:
                result += part.decode("utf-8", errors="replace")
        else:
            result += str(part)
    return result.strip()

def extract_email_body(msg) -> str:
    """Extract plain text body from email"""
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

    # Clean up quoted content and signatures
    lines = body.split('\n')
    clean_lines = []
    for line in lines:
        if line.startswith('>') or line.startswith('On ') and 'wrote:' in line:
            break
        clean_lines.append(line)

    return '\n'.join(clean_lines).strip()[:2000]

def classify_email(subject: str, body: str) -> str:
    """Classify email type for appropriate response"""
    text = (subject + " " + body).lower()

    if any(w in text for w in ["refund", "money back", "cancel order", "cancellation"]):
        return "refund_request"
    elif any(w in text for w in ["complaint", "not satisfied", "unhappy", "terrible", "awful", "bad quality"]):
        return "complaint"
    elif any(w in text for w in ["when will", "status", "update", "where is", "delivery", "progress"]):
        return "order_status"
    elif any(w in text for w in ["order", "purchase", "bought", "payment", "invoice"]):
        return "order_inquiry"
    elif any(w in text for w in ["price", "cost", "how much", "quote", "pricing", "package"]):
        return "pricing_inquiry"
    elif any(w in text for w in ["revision", "change", "modify", "update", "edit"]):
        return "revision_request"
    else:
        return "general_inquiry"

def generate_reply(sender_name: str, subject: str, body: str, email_type: str) -> str:
    """Generate AI-powered professional reply using Groq"""

    type_context = {
        "refund_request": "The client is requesting a refund. Be empathetic, acknowledge their concern, explain the refund policy professionally, and offer to resolve the issue. Do not promise a refund directly — say you will review their case within 24 hours.",
        "complaint": "The client is unhappy with the service. Be extremely empathetic and professional. Apologize genuinely, take responsibility, and offer a specific resolution (revision, priority support, or escalation to senior team).",
        "order_status": "The client is asking about their order status. Acknowledge the inquiry, confirm you are checking on their order, and say you will provide a full update within 2-4 hours.",
        "order_inquiry": "The client has an order-related question. Answer professionally and offer to assist with any specific requirements they have.",
        "pricing_inquiry": "The client is asking about pricing. Direct them to the Fiverr gig page for current pricing, mention the three packages (Basic $10, Standard $25, Premium $55), and highlight the value offered.",
        "revision_request": "The client wants revisions. Confirm you have received their revision request, acknowledge their specific requirements, and say you will begin within 24 hours.",
        "general_inquiry": "The client has a general question. Answer helpfully and professionally, and offer to assist further.",
    }

    context = type_context.get(email_type, type_context["general_inquiry"])

    prompt = f"""You are a professional customer support representative for {BUSINESS_NAME}.

CLIENT NAME: {sender_name or 'Valued Client'}
EMAIL SUBJECT: {subject}
CLIENT MESSAGE: {body[:800]}
SITUATION: {context}

Write a professional, warm, and helpful email reply.

RULES:
1. Start with "Dear {sender_name or 'Valued Client'},"
2. Maximum 4-5 short paragraphs
3. Be specific to their actual question or concern
4. Never make promises you cannot keep
5. Always end with: "Best regards,\\n{SENDER_NAME}\\n{BUSINESS_NAME}\\nResponse time: Within 24 hours"
6. Do NOT include a subject line — just the body
7. Sound like a real human — not a robot or template

Write the reply now:"""

    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60 * (attempt + 1))
            else:
                raise

    # Fallback reply if AI fails
    return f"""Dear {sender_name or 'Valued Client'},

Thank you for reaching out to {BUSINESS_NAME}. We have received your message regarding "{subject}" and will review it promptly.

A member of our team will respond with a detailed reply within 24 hours. We appreciate your patience.

If this is urgent, please reply to this email with "URGENT" in the subject line and we will prioritize your request.

Best regards,
{SENDER_NAME}
{BUSINESS_NAME}
Response time: Within 24 hours"""

def send_reply(to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Send email reply via Gmail SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"{SENDER_NAME} <{GMAIL_USER}>"
        msg['To']      = f"{to_name} <{to_email}>" if to_name else to_email
        msg['Subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
        msg['Reply-To'] = GMAIL_USER

        # Plain text version
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # HTML version for better formatting
        html_body = body.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
        html = f"""<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<div style="padding: 20px;">
{html_body}
</div>
</body></html>"""
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"   ✅ Reply sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"   ❌ SMTP Auth failed: {e}")
        telegram(f"⚠️ <b>Support Bot — SMTP Auth Failed</b>\n\nError: {str(e)}\n\n"
                f"Fix: Go to Google Account → Security → App Passwords → Generate new password → Update GMAIL_APP_PASSWORD secret in GitHub.")
        return False
    except Exception as e:
        print(f"   ❌ Send failed: {e}")
        return False

def mark_as_read(imap, msg_id: bytes):
    """Mark email as read"""
    try:
        imap.store(msg_id, '+FLAGS', '\\Seen')
    except:
        pass

def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect to Gmail IMAP with proper error handling"""
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(GMAIL_USER, GMAIL_APP_PASS)
        return imap
    except imaplib.IMAP4.error as e:
        err = str(e)
        if "AUTHENTICATIONFAILED" in err or "Invalid credentials" in err:
            telegram(f"⚠️ <b>Support Bot — Gmail Auth Failed</b>\n\n"
                    f"Error: {err}\n\n"
                    f"<b>Fix required:</b>\n"
                    f"1. Go to myaccount.google.com → Security\n"
                    f"2. Enable 2-Step Verification\n"
                    f"3. Go to App Passwords → Generate for 'Mail'\n"
                    f"4. Update GMAIL_APP_PASSWORD in GitHub Secrets\n\n"
                    f"<b>Current secret appears to be wrong or expired.</b>")
            raise
        raise

def run_support_bot():
    """Main support bot logic"""
    print(f"\n🤖 Support Bot v2.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Account: {GMAIL_USER}")

    replied_count = 0
    skipped_count = 0
    error_count   = 0

    try:
        print("   Connecting to Gmail IMAP...")
        imap = connect_imap()
        print("   ✅ Connected")

        # Select inbox
        imap.select("INBOX")

        # Search for unread emails from last 24 hours
        since_date = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        status, messages = imap.search(None, f'UNSEEN SINCE {since_date}')

        if status != "OK" or not messages[0]:
            print("   📭 No unread emails in last 24 hours")
            imap.logout()
            return 0, 0, 0

        email_ids = messages[0].split()
        total = len(email_ids)
        print(f"   📬 {total} unread email(s) found")

        # Process most recent first, up to MAX_EMAILS
        for msg_id in reversed(email_ids[-MAX_EMAILS:]):
            try:
                # Fetch email
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract headers
                sender_raw  = safe_decode(msg.get("From", ""))
                subject     = safe_decode(msg.get("Subject", "(No Subject)"))
                date        = msg.get("Date", "")

                # Extract sender email and name
                sender_match = re.search(r'<([^>]+)>', sender_raw)
                sender_email = sender_match.group(1).lower() if sender_match else sender_raw.lower()
                sender_name  = re.sub(r'<[^>]+>', '', sender_raw).strip().strip('"')

                print(f"\n   📧 From: {sender_email}")
                print(f"      Subject: {subject[:60]}")

                # Skip automated emails
                if any(skip in sender_email for skip in SKIP_SENDERS):
                    print(f"      ⏭️ Skipped (automated sender)")
                    mark_as_read(imap, msg_id)
                    skipped_count += 1
                    continue

                # Skip our own emails
                if sender_email == GMAIL_USER.lower():
                    mark_as_read(imap, msg_id)
                    skipped_count += 1
                    continue

                # Extract body
                body = extract_email_body(msg)
                if not body:
                    print(f"      ⏭️ Skipped (empty body)")
                    mark_as_read(imap, msg_id)
                    skipped_count += 1
                    continue

                # Classify and generate reply
                email_type = classify_email(subject, body)
                print(f"      📌 Type: {email_type}")

                reply_body = generate_reply(sender_name, subject, body, email_type)

                # Send reply
                success = send_reply(sender_email, sender_name, subject, reply_body)

                if success:
                    mark_as_read(imap, msg_id)
                    replied_count += 1
                    time.sleep(REPLY_DELAY)
                else:
                    error_count += 1

            except Exception as e:
                print(f"      ❌ Error processing email: {e}")
                error_count += 1
                continue

        imap.logout()
        print(f"\n   ✅ Done: {replied_count} replied | {skipped_count} skipped | {error_count} errors")
        return replied_count, skipped_count, error_count

    except imaplib.IMAP4.error as e:
        print(f"   ❌ IMAP Error: {e}")
        raise
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        telegram(f"⚠️ <b>Support Bot Error</b>\n{str(e)[:300]}")
        return 0, 0, 1

def main():
    try:
        replied, skipped, errors = run_support_bot()

        if replied > 0:
            telegram(f"✅ <b>Support Bot Complete</b>\n"
                    f"📧 Replied: {replied}\n"
                    f"⏭️ Skipped: {skipped}\n"
                    f"❌ Errors: {errors}")

    except imaplib.IMAP4.error as e:
        # Auth error already handled in connect_imap()
        sys.exit(1)
    except Exception as e:
        telegram(f"⚠️ <b>Support Bot Fatal Error</b>\n{str(e)[:300]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
