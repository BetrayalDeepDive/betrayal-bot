#!/usr/bin/env python3
"""
DeepDive Empire — Fiverr Bot v4.0
Fixed: Gemini 400 handling, Groq rate limits, better email classification
"""
import os,sys,json,re,time,imaplib,smtplib,email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime,timedelta
import requests
from groq import Groq

GROQ_KEY       = os.environ["GROQ_API_KEY"]
GEMINI_KEY     = os.environ["GEMINI_API_KEY"]
GMAIL_USER     = os.environ.get("GMAIL_USER","mohammedsultan0497@gmail.com")
GMAIL_PASS     = os.environ["GMAIL_APP_PASSWORD"]
TG_TOKEN       = os.environ["TELEGRAM_TOKEN"]
TG_CHAT        = os.environ["TELEGRAM_CHAT_ID"]
groq_client    = Groq(api_key=GROQ_KEY)
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
SENDER_NAME    = "Mohammed Sultan | NextLayer Media"
FIVERR_USER    = "nextlayermedia"
GIG_PACKAGES   = {
    "basic":    {"price":10, "words":1200,"revisions":1,"days":3},
    "standard": {"price":25, "words":2000,"revisions":2,"days":2},
    "premium":  {"price":55, "words":3500,"revisions":3,"days":1},
}

def tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id":TG_CHAT,"text":msg[:4000],"parse_mode":"HTML"},timeout=15)
    except: pass

def call_gemini(prompt,tokens=3000):
    for attempt in range(3):
        try:
            r=requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":0.7,"maxOutputTokens":tokens}},
                timeout=120)
            if r.status_code==200:
                c=r.json().get("candidates",[])
                if c: return c[0]["content"]["parts"][0]["text"]
            elif r.status_code==429: time.sleep(60*(attempt+1))
            elif r.status_code==400:
                err=r.json().get("error",{}).get("message","")
                if "API key" in err:
                    tg("Fiverr Bot: Invalid Gemini API key. Update GEMINI_API_KEY in GitHub Secrets.")
                    return None
                time.sleep(10)
            else: time.sleep(10)
        except Exception as e:
            print(f"  Gemini err: {str(e)[:60]}"); time.sleep(15)
    return None

def call_groq(prompt,tokens=800):
    for attempt in range(3):
        try:
            r=groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.7,max_tokens=min(tokens,2000))
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60); continue
            break
    return None

def call_ai(prompt,tokens=3000):
    result=call_gemini(prompt,tokens)
    if result: return result
    return call_groq(prompt,min(tokens,1500))

def safe_decode(value):
    if not value: return ""
    result=""
    for part,enc in decode_header(value):
        if isinstance(part,bytes): result+=part.decode(enc or "utf-8",errors="replace")
        else: result+=str(part)
    return result.strip()

def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type()=="text/plain":
                try: return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8",errors="replace")[:3000]
                except: continue
    try: return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8",errors="replace")[:3000]
    except: return str(msg.get_payload())[:3000]

def classify_fiverr_email(subject,body):
    sl,bl=subject.lower(),body.lower()
    result={"type":"unknown","package":"basic","buyer":"","topic":""}
    if any(x in sl for x in ["new order","you received an order","order placed"]): result["type"]="new_order"
    elif any(x in bl for x in ["new order","you have a new order","order was placed"]): result["type"]="new_order"
    elif any(x in sl for x in ["new message","sent you a message","inbox"]): result["type"]="message"
    elif any(x in sl for x in ["left you a review","new review","feedback"]): result["type"]="review"
    elif any(x in sl for x in ["revision","requested a revision"]): result["type"]="revision_request"
    elif any(x in sl for x in ["cancellation","cancel","order cancelled"]): result["type"]="cancellation"
    elif any(x in sl for x in ["payment cleared","funds available","earning"]): result["type"]="payment"
    elif "fiverr" in sl or "fiverr" in bl: result["type"]="general_fiverr"
    if "premium" in bl or "$55" in body: result["package"]="premium"
    elif "standard" in bl or "$25" in body: result["package"]="standard"
    bm=re.search(r'(?:from|buyer|username)[:\s]+([A-Za-z0-9_]{3,20})',body,re.IGNORECASE)
    if bm: result["buyer"]=bm.group(1)
    for pat in [r'(?:about|topic|keyword)[:\s]+"?([^"\n,]{10,80})"?',
                r'(?:write|article|blog).{0,30}(?:about|on)[:\s]+"?([^"\n,]{10,80})"?']:
        m=re.search(pat,body,re.IGNORECASE)
        if m: result["topic"]=m.group(1).strip()[:100]; break
    return result

def generate_seo_article(topic,package,buyer):
    pkg=GIG_PACKAGES.get(package,GIG_PACKAGES["basic"])
    prompt=f"""Write a complete SEO article for client {buyer or 'Client'}.
Topic: {topic}
Length: exactly {pkg['words']} words
Format: H1 title, introduction, 5 H2 sections with 2-3 paragraphs each, conclusion with CTA.
Style: Professional, engaging, SEO-optimized, no fluff.
Return only the article."""
    return call_ai(prompt,tokens=min(pkg['words']*2,4000))

def handle_new_order(info,body):
    topic=info.get("topic","")
    package=info.get("package","basic")
    buyer=info.get("buyer","")
    pkg=GIG_PACKAGES.get(package,GIG_PACKAGES["basic"])
    tg(f"NEW FIVERR ORDER\n\nBuyer: {buyer or 'Unknown'}\nPackage: {package.upper()} (${pkg['price']})\nTopic: {topic[:100]}\nDelivery: {pkg['days']} day(s)")
    if topic:
        print(f"  Generating article: {topic[:60]}")
        article=generate_seo_article(topic,package,buyer)
        if article:
            tg(f"Article Generated\n\nTopic: {topic[:80]}\nWords: ~{len(article.split())}\n\nFirst 300 chars:\n{article[:300]}...")
            return True
    return False

def handle_message(info,subject,body):
    buyer=info.get("buyer","")
    tg(f"FIVERR MESSAGE\n\nFrom: {buyer or 'Buyer'}\nSubject: {subject[:80]}\nMessage: {body[:300]}")

def handle_review(info,body):
    stars=5
    for i in ["1 star","2 star","3 star","4 star"]:
        if i in body.lower(): stars=int(i[0]); break
    tg(f"FIVERR REVIEW — {stars} stars\n\n{body[:300]}")

def handle_payment(body):
    amount_m=re.search(r'\$[\d.]+',body)
    amount=amount_m.group() if amount_m else "amount unknown"
    tg(f"FIVERR PAYMENT CLEARED\n\nAmount: {amount}\n\nBalance available for withdrawal.")

def handle_revision(info,body):
    buyer=info.get("buyer","")
    tg(f"REVISION REQUEST\n\nBuyer: {buyer or 'Buyer'}\nRequest: {body[:300]}\n\nBegin within 24 hours.")

def main():
    print(f"\nFiverr Bot v4.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    processed=errors=0
    try:
        imap=imaplib.IMAP4_SSL("imap.gmail.com",993)
        imap.login(GMAIL_USER,GMAIL_PASS)
        # Try Fiverr label first, fall back to INBOX search
        try:
            imap.select('"Fiverr Orders"')
            status,messages=imap.search(None,'UNSEEN')
        except:
            imap.select("INBOX")
            since=(datetime.now()-timedelta(hours=24)).strftime("%d-%b-%Y")
            status,messages=imap.search(None,f'UNSEEN FROM "fiverr" SINCE {since}')
        if status!="OK" or not messages[0]:
            print("No Fiverr emails"); imap.logout(); return
        email_ids=messages[0].split()
        print(f"Found {len(email_ids)} Fiverr email(s)")
        for msg_id in reversed(email_ids[-15:]):
            try:
                status,msg_data=imap.fetch(msg_id,"(RFC822)")
                if status!="OK": continue
                msg    =email.message_from_bytes(msg_data[0][1])
                subject=safe_decode(msg.get("Subject",""))
                body   =extract_body(msg)
                print(f"\n  Subject: {subject[:70]}")
                info   =classify_fiverr_email(subject,body)
                print(f"  Type: {info['type']}")
                if   info["type"]=="new_order":       handle_new_order(info,body)
                elif info["type"]=="message":         handle_message(info,subject,body)
                elif info["type"]=="review":          handle_review(info,body)
                elif info["type"]=="payment":         handle_payment(body)
                elif info["type"]=="revision_request":handle_revision(info,body)
                elif info["type"]=="cancellation":    tg(f"ORDER CANCELLED\n\n{subject}\n{body[:200]}")
                elif info["type"]=="general_fiverr":  tg(f"Fiverr Notification\n{subject[:80]}\n{body[:200]}")
                imap.store(msg_id,'+FLAGS','\\Seen')
                processed+=1; time.sleep(2)
            except Exception as e:
                print(f"  Email err: {e}"); errors+=1
        imap.logout()
    except imaplib.IMAP4.error as e:
        print(f"IMAP err: {e}")
        if "AUTHENTICATIONFAILED" in str(e) or "Invalid credentials" in str(e):
            tg(f"Fiverr Bot AUTH FAILED\nFix: Enable 2-Step Verification → App Passwords → update GMAIL_APP_PASSWORD")
        sys.exit(1)
    except Exception as e:
        print(f"Err: {e}"); tg(f"Fiverr Bot Error\n{str(e)[:200]}")
    print(f"\nDone: {processed} processed | {errors} errors")
    if processed>0: tg(f"Fiverr Bot Complete\nProcessed: {processed}\nErrors: {errors}")

if __name__=="__main__":
    main()
