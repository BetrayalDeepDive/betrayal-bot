# support_bot.py
# Betrayal DeepDive - Freelance Support Bot
# Checks Gmail every 30 minutes, auto-replies to client orders

import os
import json
import time
import base64
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BUSINESS_EMAIL = "nextlayermediallc@gmail.com"

SERVICE_PRICES = {
    "seo article": 25, "blog": 25, "blog article": 25,
    "youtube script": 35, "script": 35,
    "social media": 30, "social media pack": 30,
    "product description": 40,
    "email newsletter": 25, "newsletter": 25,
    "script pack": 150, "youtube pack": 150,
    "intelligence report": 199, "report": 199,
    "social media strategy": 175, "content calendar": 175,
    "website content": 250, "website": 250,
    "chatbot": 299, "ai chatbot": 299,
    "youtube channel": 499, "channel setup": 499,
    "content empire": 799,
    "business intelligence": 599,
    "consulting": 999, "automation": 999
}


def send_telegram(message):
    """Send notification to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def generate_reply(email_subject, email_body, sender_name):
    """Generate context-aware reply using Groq"""
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        services_list = "\n".join([f"- {k}: ${v}" for k, v in SERVICE_PRICES.items()])

        prompt = f"""You are a professional freelance content agency assistant for "Betrayal DeepDive Media".

Client name: {sender_name}
Email subject: {email_subject}
Email body: {email_body}

Our services and prices:
{services_list}

Payment methods: PayPal, Wise, UPI (India)
Turnaround: 1-7 days depending on service
Revisions: 2-5 depending on package

Write a professional, friendly email reply that:
1. Thanks them for reaching out
2. Addresses their specific inquiry
3. Provides relevant pricing if they asked about services
4. Asks for any clarification needed
5. Ends with next steps

Keep it concise (150-200 words). Don't use placeholders like [Your Name]."""

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a professional business email writer."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Reply generation error: {e}")

    return f"""Hi {sender_name},

Thank you for reaching out to Betrayal DeepDive Media!

We've received your inquiry and will get back to you within 24 hours with a detailed response.

If you need immediate assistance, please reply to this email with more details about your project.

Best regards,
Betrayal DeepDive Media Team
{BUSINESS_EMAIL}"""


def check_emails_and_reply():
    """Main function to check emails and send replies"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking emails...")

    try:
        import smtplib
        import imaplib
        import email
        from email.header import decode_header

        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(BUSINESS_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unread emails from last 30 minutes
        since_time = (datetime.now() - timedelta(minutes=35)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(UNSEEN SINCE {since_time})')

        if status != "OK" or not messages[0]:
            print("No new emails")
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new emails")

        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Get sender info
                sender = msg.get("From", "")
                sender_name = sender.split("<")[0].strip().strip('"') if "<" in sender else sender
                sender_email = sender.split("<")[1].strip(">") if "<" in sender else sender

                # Skip our own emails
                if BUSINESS_EMAIL in sender_email:
                    continue

                # Get subject
                subject_raw = msg.get("Subject", "No Subject")
                subject_parts = decode_header(subject_raw)
                subject = ""
                for part, encoding in subject_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8")
                    else:
                        subject += part

                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                body = body[:1000]  # Limit body length

                print(f"Processing email from: {sender_email} | Subject: {subject}")

                # Generate reply
                reply_text = generate_reply(subject, body, sender_name)

                # Send reply via SMTP
                smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                smtp.login(BUSINESS_EMAIL, GMAIL_APP_PASSWORD)

                reply_msg = MIMEMultipart()
                reply_msg["From"] = BUSINESS_EMAIL
                reply_msg["To"] = sender_email
                reply_msg["Subject"] = f"Re: {subject}"
                reply_msg.attach(MIMEText(reply_text, "plain"))

                smtp.send_message(reply_msg)
                smtp.quit()

                # Mark as read
                mail.store(email_id, "+FLAGS", "\\Seen")

                # Notify via Telegram
                send_telegram(
                    f"📧 <b>New Client Email!</b>\n\n"
                    f"From: {sender_name} ({sender_email})\n"
                    f"Subject: {subject}\n\n"
                    f"✅ Auto-reply sent!"
                )

                print(f"Reply sent to {sender_email}")
                time.sleep(2)

            except Exception as e:
                print(f"Error processing email {email_id}: {e}")

        mail.logout()

    except Exception as e:
        print(f"Email check error: {e}")
        send_telegram(f"⚠️ Support bot error: {str(e)[:200]}")


def run_weekly_report():
    """Send weekly financial report via Telegram"""
    report = f"""📊 <b>WEEKLY FREELANCE REPORT</b>
    
Date: {datetime.now().strftime('%Y-%m-%d')}

💼 Services Available: 14
📧 Auto-reply: Active
🤖 Bot Status: Running

<b>Service Pricing Summary:</b>
Starter: $25-$40
Professional: $150-$299  
Premium: $499-$999

<b>Next Steps:</b>
- Check Gumroad for new orders
- Review client emails
- Update service catalog if needed

Keep building the empire! 💪"""

    send_telegram(report)


if __name__ == "__main__":
    print("🤖 Betrayal DeepDive Support Bot Starting...")
    send_telegram("🤖 Support Bot is now ACTIVE!\n\nChecking emails every 30 minutes.")

    check_count = 0
    while True:
        check_emails_and_reply()
        check_count += 1

        # Send weekly report every Sunday (every 336 checks at 30min intervals)
        if check_count % 336 == 0:
            run_weekly_report()

        print(f"Sleeping 30 minutes... (Check #{check_count})")
        time.sleep(1800)  # 30 minutes
