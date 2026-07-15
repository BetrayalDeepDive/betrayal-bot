#!/usr/bin/env python3
"""
DeepDive Empire — Support Bot v4.0
Fixed: IMAP connection, auth error handling, Groq rate limits, skip logic
"""
import os,sys,json,re,time,imaplib,smtplib,email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime,timedelta
import requests
from groq import Groq

GROQ_KEY      = os.environ["GROQ_API_KEY"]
GMAIL_USER    = os.environ.get("GMAIL_USER","mohammedsultan0497@gmail.com")
GMAIL_PASS    = os.environ["GMAIL_APP_PASSWORD"]
TG_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TG_CHAT       = os.environ["TELEGRAM_CHAT_ID"]
groq_client   = Groq(api_key=GROQ_KEY)
SENDER_NAME   = "Mohammed Sultan"
BUSINESS_NAME = "DeepDive Intelligence / NextLayer Media"
MAX_EMAILS    = 10
SKIP_SENDERS  = ["noreply@","no-reply@","notifications@","mailer-daemon@","fiverr.com",
                 "donotreply@","bounce@","automated@","postmaster@","replies@","support@fiverr"]

def tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id":TG_CHAT,"text":msg[:4000],"parse_mode":"HTML"},timeout=15)
    except: pass

def call_groq(prompt):
    """
    FIX: this only ever tried "llama-3.3-70b-versatile" — a model Groq
    announced deprecated on June 17, 2026 — with retries only on rate
    limiting, never falling back to a different model. Now tries a real
    chain of genuinely current models before giving up.
    """
    models = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
    for model in models:
        for attempt in range(3):
            try:
                r = groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role":"user","content":prompt}],
                    temperature=0.7, max_tokens=500)
                return r.choices[0].message.content
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    time.sleep(60); continue
                break  # try next model
    return None

def safe_decode(value):
    if not value: return ""
    result = ""
    for part,enc in decode_header(value):
        if isinstance(part,bytes):
            result += part.decode(enc or "utf-8",errors="replace")
        else: result += str(part)
    return result.strip()

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type()=="text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(part.get_content_charset() or "utf-8",errors="replace")
                    break
                except: continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8",errors="replace")
        except: body = str(msg.get_payload())
    lines = [l for l in body.split('\n') if not l.startswith('>')]
    return '\n'.join(lines).strip()[:2000]

def classify_email(subject,body):
    text=(subject+" "+body).lower()
    if any(w in text for w in ["refund","money back","cancel order"]): return "refund_request"
    if any(w in text for w in ["complaint","not satisfied","unhappy","disappointed","terrible"]): return "complaint"
    if any(w in text for w in ["when will","status","update","progress","where is"]): return "order_status"
    if any(w in text for w in ["revision","change","modify","edit","redo"]): return "revision_request"
    if any(w in text for w in ["price","cost","how much","quote","pricing"]): return "pricing_inquiry"
    return "general_inquiry"

def generate_reply(sender_name,subject,body,email_type):
    context = {
        "refund_request":   "Empathetically acknowledge, say you will review within 24hrs, do not promise refund.",
        "complaint":        "Apologize sincerely, offer revision or escalation, be specific.",
        "order_status":     "Confirm checking, will update within 2-4 hours.",
        "revision_request": "Confirm receipt, begin within 24 hours.",
        "pricing_inquiry":  "Basic $10 / Standard $25 / Premium $55. Direct to Fiverr.",
        "general_inquiry":  "Answer helpfully and professionally.",
    }
    prompt = f"""You are professional support for {BUSINESS_NAME}.
Client: {sender_name or 'Client'} | Subject: {subject} | Message: {body[:600]}
Context: {context.get(email_type,'')}
Write a professional warm reply. 3-4 short paragraphs.
Start: Dear {sender_name or 'Valued Client'},
End exactly with:
Best regards,
{SENDER_NAME}
{BUSINESS_NAME}
Return only the email body."""
    result = call_groq(prompt)
    if result: return result.strip()
    return f"""Dear {sender_name or 'Valued Client'},

Thank you for contacting {BUSINESS_NAME}. We have received your message and will respond within 24 hours.

Best regards,
{SENDER_NAME}
{BUSINESS_NAME}"""

def send_reply(to_email,to_name,subject,body):
    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"{SENDER_NAME} <{GMAIL_USER}>"
        msg['To']      = f"{to_name} <{to_email}>" if to_name else to_email
        msg['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        msg.attach(MIMEText(body,'plain','utf-8'))
        msg.attach(MIMEText(f"<html><body>{body.replace(chr(10),'<br>')}</body></html>",'html','utf-8'))
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as smtp:
            smtp.login(GMAIL_USER,GMAIL_PASS)
            smtp.sendmail(GMAIL_USER,to_email,msg.as_string())
        print(f"   Replied: {to_email}"); return True
    except smtplib.SMTPAuthenticationError as e:
        tg(f"Support Bot AUTH FAILED\n{str(e)}\nFix: myaccount.google.com → Security → App Passwords → update GMAIL_APP_PASSWORD secret")
        return False
    except Exception as e:
        print(f"   Send err: {e}"); return False

def main():
    print(f"\nSupport Bot v4.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    replied=skipped=errors=0
    try:
        imap=imaplib.IMAP4_SSL("imap.gmail.com",993)
        imap.login(GMAIL_USER,GMAIL_PASS)
        imap.select("INBOX")
        since=(datetime.now()-timedelta(hours=24)).strftime("%d-%b-%Y")
        status,messages=imap.search(None,f'UNSEEN SINCE {since}')
        if status!="OK" or not messages[0]:
            print("No unread emails"); imap.logout(); return
        email_ids=messages[0].split()
        print(f"Found {len(email_ids)} email(s)")
        for msg_id in reversed(email_ids[-MAX_EMAILS:]):
            try:
                status,msg_data=imap.fetch(msg_id,"(RFC822)")
                if status!="OK": continue
                msg=email.message_from_bytes(msg_data[0][1])
                sender_raw=safe_decode(msg.get("From",""))
                subject   =safe_decode(msg.get("Subject","(No Subject)"))
                sm=re.search(r'<([^>]+)>',sender_raw)
                sender_email=sm.group(1).lower() if sm else sender_raw.lower()
                sender_name =re.sub(r'<[^>]+>','',sender_raw).strip().strip('"')
                print(f"\n  From: {sender_email}\n  Subject: {subject[:60]}")
                if any(s in sender_email for s in SKIP_SENDERS) or sender_email==GMAIL_USER.lower():
                    imap.store(msg_id,'+FLAGS','\\Seen'); skipped+=1; continue
                body=extract_body(msg)
                if not body: imap.store(msg_id,'+FLAGS','\\Seen'); skipped+=1; continue
                email_type=classify_email(subject,body)
                print(f"  Type: {email_type}")
                reply=generate_reply(sender_name,subject,body,email_type)
                if send_reply(sender_email,sender_name,subject,reply):
                    imap.store(msg_id,'+FLAGS','\\Seen'); replied+=1; time.sleep(3)
                else: errors+=1
            except Exception as e:
                print(f"  Email err: {e}"); errors+=1
        imap.logout()
    except imaplib.IMAP4.error as e:
        print(f"IMAP err: {e}")
        if "AUTHENTICATIONFAILED" in str(e) or "Invalid credentials" in str(e):
            tg(f"Support Bot IMAP AUTH FAILED\nFix: Enable 2-Step Verification on Gmail then generate App Password\nUpdate GMAIL_APP_PASSWORD in GitHub Secrets")
        sys.exit(1)
    except Exception as e:
        print(f"Err: {e}"); tg(f"Support Bot Error\n{str(e)[:200]}"); sys.exit(1)
    print(f"\nDone: {replied} replied | {skipped} skipped | {errors} errors")
    if replied>0 or errors>0:
        tg(f"Support Bot Complete\nReplied: {replied}\nSkipped: {skipped}\nErrors: {errors}")

if __name__=="__main__":
    main()
