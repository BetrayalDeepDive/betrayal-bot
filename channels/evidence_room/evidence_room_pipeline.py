#!/usr/bin/env python3
"""
THE EVIDENCE ROOM — ANIMATED PIPELINE
Channel 2 of DeepDive Empire

3 ROTATING ANIMATION STYLES (never the same two days in a row):
  Style 1 — DARK MINIMAL: black bg, white/red animated text, timelines, clinical
  Style 2 — CINEMATIC:    dark blue/grey, glowing text, dramatic reveals
  Style 3 — DOCUMENTARY:  case file scans, redacted text, stamps, photos appearing

Stack: Pillow + matplotlib + numpy + FFmpeg
       (zero system deps — pure pip install, runs on GitHub Actions ubuntu-latest)

Pipeline: Script → Animated Scenes → Audio (edge-tts) → Video → Approval → YouTube
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from groq import Groq

# ── CREDENTIALS ─────────────────────────────────────────────
GROQ_KEY      = os.environ["GROQ_API_KEY"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
YT_CLIENT_ID  = os.environ.get("EVIDENCE_YT_CLIENT_ID", os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC = os.environ.get("EVIDENCE_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH    = os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
TG_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TG_CHAT       = os.environ["TELEGRAM_CHAT_ID"]

groq_client = Groq(api_key=GROQ_KEY)
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
WORK_DIR    = Path("/tmp/evidence_room")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE  = WORK_DIR / "state.json"

W, H   = 1920, 1080   # Output resolution
FPS    = 30
FRAME  = (W, H)

# ── ANIMATION STYLES ────────────────────────────────────────
STYLES = {
    "dark_minimal": {
        "bg":        (2, 2, 10),           # Near-black
        "primary":   (255, 255, 255),       # White
        "accent":    (200, 30, 30),         # Blood red
        "secondary": (120, 120, 140),       # Muted grey
        "text_glow": False,
        "desc":      "Clinical dark minimal — white/red on black"
    },
    "cinematic": {
        "bg":        (5, 10, 25),           # Dark blue-black
        "primary":   (220, 235, 255),       # Cool white
        "accent":    (80, 160, 255),        # Electric blue glow
        "secondary": (100, 130, 180),       # Muted blue
        "text_glow": True,
        "desc":      "Cinematic dark blue — glowing dramatic reveals"
    },
    "documentary": {
        "bg":        (18, 15, 12),          # Dark warm black (aged paper feel in dark)
        "primary":   (230, 220, 200),       # Aged paper white
        "accent":    (180, 40, 20),         # Stamp red
        "secondary": (140, 120, 100),       # Aged brown-grey
        "text_glow": False,
        "desc":      "Documentary case file — aged documents, stamps, redacted text"
    }
}

# ── NICHE TOPICS ────────────────────────────────────────────
NICHES = [
    {
        "name": "forensic_finance", "rpm": 16.00,
        "series": "The Evidence Room: Financial Crimes",
        "topics": [
            "The offshore account trail that exposed a 12-year bank fraud hidden inside 40 shell companies",
            "How auditors missed 3.2 billion in concealed losses because they trusted the software the fraudster wrote",
            "The wire transfer pattern that a junior analyst flagged in 2019 that nobody acted on for 3 years",
            "A hedge fund that reported consistent 18% annual returns for 9 years — the investigation that found it was all fabricated",
            "How one accountant embezzled from 60 client accounts simultaneously using a single spreadsheet formula",
        ]
    },
    {
        "name": "criminal_investigation", "rpm": 14.50,
        "series": "The Evidence Room: Cold Cases",
        "topics": [
            "The 1994 cold case where a single unmatched DNA sample sat in an evidence box for 28 years",
            "How investigators reconstructed a complete financial crime timeline from deleted text messages",
            "The surveillance camera timestampsthat proved the suspect was 40 miles away — and who that implicated instead",
            "A witness statement that changed 11 times across 6 interviews — the analysis that exposed the lie",
            "The phone metadata that placed 4 people at a location they each separately denied visiting",
        ]
    },
    {
        "name": "corporate_exposure", "rpm": 15.50,
        "series": "The Evidence Room: Corporate Files",
        "topics": [
            "The internal memo chain proving executives knew about product defects 3 years before the recall",
            "How a startup faked 340 million in funding due diligence with documents that took 8 minutes to produce",
            "The email thread — 847 messages — that dismantled a decade of fraud in one discovery process",
            "A board of directors that approved 23 fraudulent invoices because nobody read past the summary page",
            "The document trail showing a pharmaceutical company buried its own clinical trial data for 6 years",
        ]
    },
    {
        "name": "digital_forensics", "rpm": 17.00,
        "series": "The Evidence Room: Digital Evidence",
        "topics": [
            "How deleted files on a company server reconstructed a 5-year insider trading operation",
            "The IP address that linked 9 separate fraud accounts to a single apartment in 3 countries",
            "Metadata embedded in a document proved it was written 2 years before the date it was supposedly signed",
            "How a data broker built profiles on 300 million people and what investigators found inside those files",
            "The algorithm audit that showed a trading system was front-running client orders — automated proof",
        ]
    },
]

DAY_NICHE = {0:"forensic_finance", 1:"corporate_exposure", 2:"criminal_investigation",
             3:"digital_forensics", 4:"forensic_finance"}
DAY_STYLE = {0:"dark_minimal", 1:"cinematic", 2:"documentary",
             3:"dark_minimal", 4:"cinematic"}


# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════
def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                     json={"chat_id":TG_CHAT,"text":msg,"parse_mode":"HTML"}, timeout=15)
    except: pass

def tg_updates(offset=None):
    try:
        params = {"timeout":30}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                        params=params, timeout=35)
        return r.json().get("result",[])
    except: return []

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_style":"","last_niche":"","last_title":"","last_url":""}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def ai_gemini(prompt, temp=0.85, tokens=6000):
    for attempt in range(3):
        try:
            r = requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192)},
                      "safetySettings":[
                          {"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_NONE"},
                          {"category":"HARM_CATEGORY_DANGEROUS_CONTENT","threshold":"BLOCK_NONE"},
                          {"category":"HARM_CATEGORY_HATE_SPEECH","threshold":"BLOCK_NONE"},
                          {"category":"HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold":"BLOCK_NONE"},
                      ]}, timeout=120)
            if r.status_code == 200:
                c = r.json().get("candidates",[])
                if c: return c[0]["content"]["parts"][0]["text"]
            elif r.status_code == 429: time.sleep(60*(attempt+1))
            else: time.sleep(15)
        except Exception as e:
            print(f"  Gemini {attempt+1}: {e}")
            time.sleep(20)
    raise Exception("Gemini failed")

def ai_groq(prompt, temp=0.7, tokens=2000):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=temp, max_tokens=min(tokens,2000))
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60*(2**attempt))
            else: raise
    raise Exception("Groq failed")

def ai(prompt, temp=0.85, tokens=6000, prefer="gemini"):
    try:
        return ai_gemini(prompt,temp,tokens) if prefer=="gemini" else ai_groq(prompt,temp,min(tokens,2000))
    except:
        return ai_groq(prompt,temp,min(tokens,2000)) if prefer=="gemini" else ai_gemini(prompt,temp,tokens)

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text = re.sub(r'_{1,2}([^_\n]+)_{1,2}',r'\1',text)
        text = re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'`+[^`]*`+','',text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',text)
        text = re.sub(r'https?://\S+','',text)
        text = re.sub(r'<[^>]+>','',text)
        text = re.sub(r'[#@$%^&*{}<>|\\~`]','',text)
        text = re.sub(r'\n{3,}','\n\n',text)
        text = re.sub(r'[ \t]{2,}',' ',text)
    return text.strip()


# ════════════════════════════════════════════════════════════
# STAGE 1: SCRIPT + SCENE BREAKDOWN
# ════════════════════════════════════════════════════════════
def generate_script_and_scenes(niche, topic, style_name, episode):
    style = STYLES[style_name]
    prompt = f"""You are the writer for "The Evidence Room" — an animated forensic investigation YouTube channel.
Write Episode {episode} for: "{niche['series']}"
Topic: {topic}
Animation style this episode: {style['desc']}

SCRIPT RULES:
1. 1800-2200 words of pure spoken narration (12-15 minute video)
2. ZERO markdown — pure spoken English only
3. MAX 12 words per sentence — short sentences = tension
4. Written as if showing evidence on screen as you narrate
5. Reference what's being shown: "This document", "These records show", "The highlighted section", "Frame 47"

ALSO provide a JSON scene breakdown at the end (after a line of 10 dashes):
{{
  "title": "YouTube title 55-65 chars",
  "thumbnail_text": "3 WORDS ALL CAPS shocking",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],
  "scenes": [
    {{"type": "timeline", "duration": 8, "title": "THE FRAUD BEGINS", "items": ["2017: First transaction", "2018: Pattern established", "2019: Scale increases"], "label": "CHRONOLOGICAL EVIDENCE"}},
    {{"type": "document", "duration": 6, "title": "EXHIBIT A", "lines": ["CONFIDENTIAL", "Internal memo dated March 4 2019", "RE: Risk Assessment Override", "Signed: [REDACTED]"], "stamp": "CLASSIFIED"}},
    {{"type": "data_reveal", "duration": 7, "title": "THE NUMBERS", "items": ["$4.7M", "$12.3M", "$28.9M", "$47.2M"], "label": "FUNDS MOVED ANNUALLY"}},
    {{"type": "connection_map", "duration": 8, "title": "THE NETWORK", "nodes": ["SHELL CO A", "OFFSHORE B", "ACCOUNT C", "FINAL DEST"], "label": "MONEY TRAIL RECONSTRUCTED"}},
    {{"type": "evidence_board", "duration": 10, "title": "EVIDENCE COMPILED", "items": ["Wire transfers: 847", "Shell companies: 40", "Countries: 6", "Years active: 12"], "label": "CASE SUMMARY"}}
  ]
}}

Write the complete narration first, then the 10 dashes, then the JSON."""

    raw = ai(prompt, temp=0.85, tokens=7000, prefer="gemini")

    # Split script from JSON
    parts = raw.split("----------")
    script_raw = parts[0].strip()
    script_clean = strip_md(strip_md(script_raw))

    scenes = []
    title = f"The Evidence Room: {topic[:45]}"
    thumbnail_text = "EVIDENCE FOUND"
    tags = [niche["name"],"investigation","forensics","evidence","crime","documentary","animated","deepdive","exposed","shocking"]

    if len(parts) > 1:
        try:
            json_text = re.sub(r'```json|```','',parts[1]).strip()
            m = re.search(r'\{[\s\S]*\}', json_text)
            if m:
                data = json.loads(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',m.group()))
                scenes       = data.get("scenes", [])
                title        = data.get("title", title)
                thumbnail_text = data.get("thumbnail_text", thumbnail_text)
                tags         = data.get("tags", tags)
        except Exception as e:
            print(f"  Scene JSON parse error: {e}")

    # Fallback scenes if none parsed
    if not scenes:
        scenes = [
            {"type":"timeline","duration":8,"title":"THE INVESTIGATION BEGINS",
             "items":["Phase 1: Discovery","Phase 2: Analysis","Phase 3: Evidence","Phase 4: Exposure"],
             "label":"CASE TIMELINE"},
            {"type":"data_reveal","duration":7,"title":"THE EVIDENCE",
             "items":["$47M","12 Years","40 Accounts","847 Transactions"],
             "label":"KEY FINDINGS"},
            {"type":"document","duration":6,"title":"EXHIBIT A",
             "lines":["INTERNAL DOCUMENT","DATE: REDACTED","CLASSIFICATION: CONFIDENTIAL","STATUS: EVIDENCE"],
             "stamp":"CLASSIFIED"},
            {"type":"evidence_board","duration":10,"title":"CASE SUMMARY",
             "items":["Shell companies: 40","Countries: 6","Transactions: 847","Duration: 12 years"],
             "label":"COMPILED EVIDENCE"},
        ]

    wc = len(script_clean.split())
    print(f"  Script: {wc}w | Scenes: {len(scenes)} | Title: {title[:50]}")
    return script_clean, scenes, title, thumbnail_text, tags


# ════════════════════════════════════════════════════════════
# STAGE 2: AUDIO
# ════════════════════════════════════════════════════════════
async def _tts(text, voice_id, path):
    import edge_tts
    c = edge_tts.Communicate(text, voice_id, rate="-10%", pitch="-6Hz", volume="+10%")
    await c.save(path)

def generate_audio(script_clean, niche_name):
    # Evidence Room uses more measured, analytical voices
    voices = {
        "forensic_finance":    "en-GB-ThomasNeural",   # Cold measured authority
        "criminal_investigation": "en-GB-RyanNeural",  # BBC documentary gravitas
        "corporate_exposure":  "en-US-GuyNeural",      # Commanding US male
        "digital_forensics":   "en-GB-RyanNeural",     # Precise British
    }
    voice = voices.get(niche_name, "en-GB-RyanNeural")
    print(f"  Voice: {voice}")
    mp3 = str(WORK_DIR/"audio.mp3")
    asyncio.run(_tts(script_clean, voice, mp3))
    sz = Path(mp3).stat().st_size
    if sz < 30000: raise Exception(f"Audio too small: {sz}b")
    wc  = len(script_clean.split())
    dur = (wc / 130.0) * 60.0
    print(f"  Audio: {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
    return mp3, dur, voice


# ════════════════════════════════════════════════════════════
# STAGE 3: ANIMATION ENGINE
# 3 styles: dark_minimal, cinematic, documentary
# Each scene type: timeline, document, data_reveal,
#                  connection_map, evidence_board
# ════════════════════════════════════════════════════════════

def hex_to_rgb_float(rgb_tuple):
    return tuple(c/255.0 for c in rgb_tuple)

def render_frame_pil(style_name, scene, frame_idx, total_frames, scene_idx, total_scenes):
    """Render a single frame using Pillow. Returns PIL Image."""
    style = STYLES[style_name]
    bg = style["bg"]
    primary = style["primary"]
    accent = style["accent"]
    secondary = style["secondary"]

    img = Image.new("RGB", FRAME, bg)
    draw = ImageDraw.Draw(img)

    # Progress through this scene (0.0 → 1.0)
    progress = frame_idx / max(total_frames - 1, 1)

    # Try to load fonts — fall back to default
    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    except:
        font_lg = font_md = font_sm = font_xs = font_mono = ImageFont.load_default()

    stype = scene.get("type", "evidence_board")

    # ── Style-specific background ──────────────────────────
    if style_name == "cinematic":
        # Dark blue gradient scan lines
        for y in range(0, H, 4):
            alpha = int(8 * abs(0.5 - y/H))
            draw.line([(0,y),(W,y)], fill=(20,40,80), width=1)
    elif style_name == "documentary":
        # Subtle paper texture lines
        for y in range(0, H, 8):
            if random.random() < 0.15:
                draw.line([(0,y),(W,y)], fill=(30,25,20), width=1)

    # ── Red corner accent lines ────────────────────────────
    if style_name in ["dark_minimal", "cinematic"]:
        lw = 2
        draw.line([(0,0),(60,0)], fill=accent, width=lw)
        draw.line([(0,0),(0,60)], fill=accent, width=lw)
        draw.line([(W-60,H-1),(W,H-1)], fill=accent, width=lw)
        draw.line([(W-1,H-60),(W-1,H)], fill=accent, width=lw)

    # ── Episode watermark ─────────────────────────────────
    draw.text((30, H-40), "THE EVIDENCE ROOM", font=font_xs, fill=secondary)
    draw.text((W-250, H-40), f"SCENE {scene_idx+1}/{total_scenes}", font=font_xs, fill=secondary)

    # ── Scene title bar ───────────────────────────────────
    title = scene.get("title", "EVIDENCE")
    if progress > 0.05:
        title_alpha = min(1.0, (progress - 0.05) * 5)
        title_x = int(80 + (1.0 - title_alpha) * 40)
        draw.text((title_x, 40), title, font=font_lg, fill=accent if style_name != "cinematic" else (80,160,255))
        draw.line([(80,110),(min(80+int(700*progress),780),110)], fill=accent, width=2)

    # ── Scene type rendering ──────────────────────────────
    if stype == "timeline":
        _render_timeline(draw, scene, progress, style, font_md, font_sm, font_xs)
    elif stype == "document":
        _render_document(draw, scene, progress, style, style_name, font_md, font_sm, font_mono)
    elif stype == "data_reveal":
        _render_data_reveal(draw, scene, progress, style, font_lg, font_md, font_sm)
    elif stype == "connection_map":
        _render_connection_map(draw, scene, progress, style, font_md, font_sm)
    elif stype == "evidence_board":
        _render_evidence_board(draw, scene, progress, style, font_md, font_sm, font_xs)
    else:
        _render_evidence_board(draw, scene, progress, style, font_md, font_sm, font_xs)

    # ── Cinematic glow overlay ─────────────────────────────
    if style_name == "cinematic":
        # Subtle vignette
        for r_i, alpha in [(300, 20), (500, 12), (700, 6)]:
            for _ in range(20):
                x = random.randint(0, W)
                y = random.randint(0, H)
                dist = ((x - W//2)**2 + (y - H//2)**2)**0.5
                if dist > r_i:
                    draw.point((x,y), fill=(0,0,10))

    return img

def _render_timeline(draw, scene, progress, style, font_md, font_sm, font_xs):
    items = scene.get("items", [])
    label = scene.get("label", "TIMELINE")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    # Vertical timeline line
    line_x = 200
    top_y, bot_y = 160, H - 150
    draw.line([(line_x, top_y), (line_x, bot_y)], fill=secondary, width=2)

    # Label
    draw.text((80, H-120), label, font=font_xs, fill=secondary)

    # Items appear one by one
    n = len(items)
    spacing = (bot_y - top_y) // max(n, 1)

    for i, item in enumerate(items):
        item_progress = (progress * n) - i
        if item_progress <= 0: continue
        alpha = min(1.0, item_progress)
        y = top_y + i * spacing

        # Dot on timeline
        dot_color = accent if alpha > 0.5 else secondary
        draw.ellipse([(line_x-8, y-8), (line_x+8, y+8)], fill=dot_color)

        # Horizontal connector
        x_end = int(line_x + 60 + alpha * 40)
        draw.line([(line_x+8, y), (x_end, y)], fill=dot_color, width=2)

        # Item text
        if alpha > 0.3:
            text_alpha = min(1.0, (alpha - 0.3) * 3)
            text_x = line_x + 80
            draw.text((text_x, y-15), item, font=font_sm, fill=primary)

def _render_document(draw, scene, style_name, progress, style, font_md, font_sm, font_mono):
    lines = scene.get("lines", ["CONFIDENTIAL DOCUMENT"])
    stamp = scene.get("stamp", "")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    # Document background panel
    pad_x, pad_y = 200, 160
    doc_w, doc_h = W - 400, H - 280
    panel_color = (12, 12, 18) if style_name != "documentary" else (20, 16, 12)
    draw.rectangle([(pad_x, pad_y), (pad_x+doc_w, pad_y+doc_h)], fill=panel_color, outline=secondary, width=1)

    # Document header line
    draw.line([(pad_x+20, pad_y+60), (pad_x+doc_w-20, pad_y+60)], fill=secondary, width=1)

    # Lines reveal
    n = len(lines)
    for i, line in enumerate(lines):
        line_progress = (progress * (n + 1)) - i
        if line_progress <= 0: continue
        alpha = min(1.0, line_progress)
        y = pad_y + 80 + i * 55
        if alpha > 0:
            color = primary if not line.startswith("[") else secondary
            draw.text((pad_x + 40, y), line, font=font_mono, fill=color)

    # Stamp appears at 70%
    if stamp and progress > 0.7 and style_name in ["documentary", "dark_minimal"]:
        stamp_alpha = min(1.0, (progress - 0.7) * 3.3)
        sx, sy = pad_x + doc_w - 280, pad_y + doc_h - 200
        draw.rectangle([(sx,sy),(sx+240,sy+100)], outline=accent, width=3)
        draw.text((sx+15, sy+15), stamp, font=font_md, fill=accent)

def _render_data_reveal(draw, scene, progress, style, font_lg, font_md, font_sm):
    items = scene.get("items", [])
    label = scene.get("label", "DATA")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    draw.text((80, H-120), label, font=font_sm, fill=secondary)
    draw.line([(80, H-90), (W-80, H-90)], fill=secondary, width=1)

    n = len(items)
    col_w = (W - 200) // max(n, 1)

    for i, item in enumerate(items):
        item_progress = (progress * (n + 0.5)) - i
        if item_progress <= 0: continue
        alpha = min(1.0, item_progress)

        cx = 100 + i * col_w + col_w // 2
        bar_h = int(alpha * 350)
        bar_top = H - 150 - bar_h
        bar_color = accent if i == n-1 else primary

        # Bar
        draw.rectangle([(cx-40, bar_top), (cx+40, H-150)], fill=bar_color, outline=secondary, width=1)

        # Value label
        if alpha > 0.4:
            bbox = font_lg.getbbox(item) if hasattr(font_lg, 'getbbox') else (0,0,100,40)
            text_w = bbox[2] - bbox[0]
            draw.text((cx - text_w//2, bar_top - 60), item, font=font_lg, fill=primary)

def _render_connection_map(draw, scene, progress, style, font_md, font_sm):
    nodes = scene.get("nodes", [])
    label = scene.get("label", "CONNECTION MAP")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    draw.text((80, H-120), label, font=font_sm, fill=secondary)
    n = len(nodes)
    if n == 0: return

    # Node positions in a line with connecting arrows
    spacing = (W - 300) // max(n-1, 1)
    node_y = H // 2
    positions = [(150 + i * spacing, node_y) for i in range(n)]

    for i, (nx, ny) in enumerate(positions):
        node_progress = (progress * (n + 0.5)) - i
        if node_progress <= 0: continue
        alpha = min(1.0, node_progress)

        # Draw connector line to next node
        if i < n-1 and node_progress > 0.8:
            next_x, next_y = positions[i+1]
            line_end_x = int(nx + 40 + alpha * (next_x - nx - 80))
            draw.line([(nx+40, ny), (line_end_x, ny)], fill=accent, width=2)
            # Arrow head
            if line_end_x > nx + 100:
                draw.polygon([(line_end_x, ny), (line_end_x-12, ny-8), (line_end_x-12, ny+8)], fill=accent)

        # Node box
        box_color = accent if i == 0 or i == n-1 else secondary
        draw.rectangle([(nx-60, ny-25), (nx+60, ny+25)], fill=(5,5,15), outline=box_color, width=2)
        draw.text((nx-50, ny-12), nodes[i], font=font_sm, fill=primary)

def _render_evidence_board(draw, scene, progress, style, font_md, font_sm, font_xs):
    items = scene.get("items", [])
    label = scene.get("label", "EVIDENCE")
    primary, accent, secondary = style["primary"], style["accent"], style["secondary"]

    draw.text((80, H-120), label, font=font_xs, fill=secondary)

    # Grid layout
    n = len(items)
    cols = 2
    rows = (n + 1) // 2
    cell_w = (W - 200) // cols
    cell_h = (H - 320) // max(rows, 1)

    for i, item in enumerate(items):
        item_progress = (progress * (n + 0.5)) - i
        if item_progress <= 0: continue
        alpha = min(1.0, item_progress)

        col = i % cols
        row = i // cols
        cx = 100 + col * cell_w
        cy = 160 + row * cell_h

        # Card
        draw.rectangle([(cx, cy), (cx+cell_w-20, cy+cell_h-20)],
                       fill=(8,8,18), outline=accent if alpha > 0.8 else secondary, width=1)

        # Text
        if alpha > 0.2:
            parts_text = item.split(":")
            if len(parts_text) == 2:
                draw.text((cx+15, cy+15), parts_text[0]+":", font=font_xs, fill=secondary)
                draw.text((cx+15, cy+45), parts_text[1].strip(), font=font_md, fill=primary)
            else:
                draw.text((cx+15, cy+25), item, font=font_sm, fill=primary)

def render_scene_to_frames(style_name, scene, scene_idx, total_scenes, output_dir):
    """Render all frames for one scene, save as PNG sequence."""
    duration_sec = scene.get("duration", 8)
    total_frames = duration_sec * FPS
    frames_dir = output_dir / f"scene_{scene_idx:03d}"
    frames_dir.mkdir(exist_ok=True)

    print(f"  Scene {scene_idx+1}: {scene.get('type','?')} — {total_frames} frames")

    for fi in range(total_frames):
        img = render_frame_pil(style_name, scene, fi, total_frames, scene_idx, total_scenes)
        img.save(str(frames_dir / f"frame_{fi:05d}.png"))

    return str(frames_dir), total_frames

def build_video_from_scenes(style_name, scenes, audio_path, output_path, total_duration):
    """
    Render all scene frames, concatenate via FFmpeg.
    """
    frames_base = WORK_DIR / "frames"
    frames_base.mkdir(exist_ok=True)
    all_frame_dirs = []

    for i, scene in enumerate(scenes):
        fd, nf = render_scene_to_frames(style_name, scene, i, len(scenes), frames_base)
        all_frame_dirs.append((fd, nf, scene.get("duration",8)))

    # Write concat list for FFmpeg
    concat_parts = []
    for fd, nf, dur in all_frame_dirs:
        # Build mini-video per scene
        scene_mp4 = fd + "_scene.mp4"
        subprocess.run([
            "ffmpeg","-y","-framerate",str(FPS),
            "-i",f"{fd}/frame_%05d.png",
            "-c:v","libx264","-preset","fast","-crf","23",
            "-pix_fmt","yuv420p","-r",str(FPS),scene_mp4
        ], capture_output=True, timeout=300)
        concat_parts.append(f"file '{scene_mp4}'")

    # Loop scenes to match audio duration
    concat_file = str(WORK_DIR/"concat.txt")
    with open(concat_file,"w") as f:
        # Repeat scene list enough times to cover audio
        total_scene_dur = sum(s.get("duration",8) for s in scenes)
        repeats = max(1, int(total_duration / total_scene_dur) + 2)
        for _ in range(repeats):
            f.write("\n".join(concat_parts) + "\n")

    # Concatenate all scenes
    raw_video = str(WORK_DIR/"raw_video.mp4")
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0",
        "-i",concat_file,
        "-c:v","libx264","-preset","fast","-crf","23",
        "-pix_fmt","yuv420p","-r",str(FPS),raw_video
    ], capture_output=True, timeout=600)

    # Mux with audio, trim to audio length
    subprocess.run([
        "ffmpeg","-y",
        "-i",raw_video,"-i",audio_path,
        "-c:v","libx264","-preset","medium","-crf","19",
        "-c:a","aac","-b:a","192k",
        "-t",str(total_duration),
        "-pix_fmt","yuv420p","-movflags","+faststart",
        "-shortest",output_path
    ], capture_output=True, timeout=2400)

    sz = Path(output_path).stat().st_size
    print(f"  Final video: {sz/1024/1024:.0f}MB | 1080p")
    return output_path


# ════════════════════════════════════════════════════════════
# STAGE 4: SUBTITLES
# ════════════════════════════════════════════════════════════
def generate_subtitles(script_clean, duration):
    words = script_clean.split()
    wps   = len(words) / duration
    def fmt(t):
        h,r = divmod(int(t),3600); m,s = divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d},{int((t%1)*1000):03d}"
    entries, idx, t = [], 1, 0.0
    for i in range(0,len(words),5):
        g = words[i:i+5]
        if not g: continue
        d = len(g)/wps
        entries.append(f"{idx}\n{fmt(t)} --> {fmt(t+d)}\n{' '.join(g)}\n")
        idx+=1; t+=d
    srt = WORK_DIR/"subtitles.srt"
    srt.write_text("\n".join(entries),encoding="utf-8")
    return str(srt), len(entries)

def burn_subtitles(video_path, srt_path, output_path):
    sub_style = ("FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,"
                 "OutlineColour=&H00000000,BackColour=&HAA000000,"
                 "Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=50,BorderStyle=3")
    subprocess.run([
        "ffmpeg","-y","-i",video_path,
        "-vf",f"subtitles={srt_path}:force_style='{sub_style}'",
        "-c:v","libx264","-preset","fast","-crf","21",
        "-c:a","copy",output_path
    ], capture_output=True, timeout=2400)
    return output_path


# ════════════════════════════════════════════════════════════
# STAGE 5: UPLOAD + APPROVAL
# ════════════════════════════════════════════════════════════
def get_yt_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SEC,
        "refresh_token":YT_REFRESH,"grant_type":"refresh_token"})
    d = r.json()
    if "access_token" not in d: raise Exception(f"Token failed: {d}")
    return d["access_token"]

def upload_yt(path, title, description, tags):
    token = get_yt_token()
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"snippet":{"title":title,"description":description,"tags":tags,"categoryId":"22"},
              "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}})
    url = init.headers.get("Location")
    if not url: raise Exception(f"No upload URL: {init.text[:200]}")
    sz = Path(path).stat().st_size
    with open(path,"rb") as f:
        up = requests.put(url, headers={"Content-Length":str(sz),"Content-Type":"video/mp4"},
                         data=f, timeout=2400)
    if up.status_code in [200,201]:
        return f"https://www.youtube.com/watch?v={up.json().get('id')}"
    raise Exception(f"Upload failed {up.status_code}")

def wait_approval(title, style_name, niche, duration, sub_count):
    deadline = datetime.datetime.now() + datetime.timedelta(hours=2)
    style_desc = STYLES[style_name]["desc"]
    tg(f"<b>EVIDENCE ROOM — APPROVAL NEEDED</b>\n\n"
       f"<b>{title}</b>\n\n"
       f"Style: {style_desc}\n"
       f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
       f"Duration: {duration/60:.1f} min | Subtitles: {sub_count} lines\n\n"
       f"Auto-uploads at {deadline.strftime('%I:%M %p')} if no response\n\n"
       f"Reply <b>APPROVE</b> or <b>REJECT</b>")
    updates = tg_updates()
    offset = (max(u["update_id"] for u in updates)+1) if updates else 0
    reminded = set()
    while datetime.datetime.now() < deadline:
        time.sleep(60)
        for u in tg_updates(offset):
            offset = u["update_id"]+1
            txt = u.get("message",{}).get("text","").upper().strip()
            cid = str(u.get("message",{}).get("chat",{}).get("id",""))
            if cid == str(TG_CHAT):
                if any(w in txt for w in ["APPROVE","YES","GO","UPLOAD","OK"]):
                    tg("Approved! Uploading Evidence Room now..."); return "approved"
                if any(w in txt for w in ["REJECT","NO","SKIP"]):
                    tg("Rejected. Skipping today."); return "rejected"
        mins = int((deadline-datetime.datetime.now()).total_seconds()/60)
        for rem in [90,60,30,10]:
            if rem-2 <= mins <= rem+2 and rem not in reminded:
                tg(f"<b>REMINDER: {mins} min until auto-upload</b>\nReply APPROVE or REJECT")
                reminded.add(rem); break
    tg("Auto-uploading Evidence Room now.")
    return "auto_approved"

def cleanup():
    for f in ["audio.mp3","audio.wav","raw_video.mp4","final.mp4","final_with_subs.mp4",
              "subtitles.srt","concat.txt"]:
        p = WORK_DIR/f
        if p.exists(): p.unlink()
    # Clean frames
    frames_dir = WORK_DIR/"frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    print("  Cleanup complete")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    print("\n" + "="*65)
    print("  THE EVIDENCE ROOM — ANIMATED FORENSIC PIPELINE")
    print("  3 Rotating Styles | Pillow + FFmpeg | No system deps")
    print("="*65 + "\n")

    state = load_state()

    # Select niche and style
    day = datetime.datetime.now().weekday()
    niche_name = DAY_NICHE.get(day, "forensic_finance")
    style_name = DAY_STYLE.get(day, "dark_minimal")
    # Never repeat yesterday's style
    if style_name == state.get("last_style",""):
        style_options = [s for s in STYLES if s != style_name]
        style_name = style_options[day % len(style_options)]

    niche   = next(n for n in NICHES if n["name"] == niche_name)
    topic   = random.choice(niche["topics"])
    episode = (datetime.datetime.now().timetuple().tm_yday // 3) + 1

    print(f"Niche: {niche_name} | ${niche['rpm']} RPM | Ep{episode}")
    print(f"Style: {style_name} — {STYLES[style_name]['desc']}")
    print(f"Topic: {topic}\n")

    # Stage 1: Script + Scenes
    print("Stage 1: Generating script and scene breakdown...")
    script_clean, scenes, title, thumbnail_text, tags = generate_script_and_scenes(
        niche, topic, style_name, episode)
    tg(f"<b>Evidence Room Stage 1 Complete</b>\n{niche_name} | {len(scenes)} scenes\n{title[:60]}\nStage 2: Audio...")

    # Stage 2: Audio
    print("\nStage 2: Generating audio...")
    audio_path, duration, voice = generate_audio(script_clean, niche_name)
    tg(f"<b>Stage 2 Complete</b>\nVoice: {voice} | {duration/60:.1f}min\nStage 3: Animation rendering...")

    # Stage 3: Animation
    print("\nStage 3: Rendering animation frames...")
    video_raw = str(WORK_DIR/"final.mp4")
    build_video_from_scenes(style_name, scenes, audio_path, video_raw, duration)
    tg(f"<b>Stage 3 Complete</b>\n1080p animated | Style: {style_name}\nAdding subtitles...")

    # Stage 4: Subtitles
    print("\nStage 4: Generating subtitles...")
    srt_path, sub_count = generate_subtitles(script_clean, duration)
    final_video = str(WORK_DIR/"final_with_subs.mp4")
    burn_subtitles(video_raw, srt_path, final_video)
    print(f"  Subtitles: {sub_count} lines burned in")

    # Stage 5: Approval
    print("\nStage 5: Sending approval request...")
    description = (f"Episode {episode} of The Evidence Room. {topic}\n\n"
                   f"Subscribe to The Evidence Room for forensic investigation breakdowns.\n\n"
                   f"Every case. Every document. Every piece of evidence — animated.")
    decision = wait_approval(title, style_name, niche, duration, sub_count)
    if decision == "rejected":
        cleanup(); sys.exit(0)

    # Upload
    print("Uploading to YouTube...")
    try:
        yt_url = upload_yt(final_video, title, description, tags)
        print(f"Published: {yt_url}")
    except Exception as e:
        tg(f"<b>Evidence Room Upload Failed</b>\n{str(e)[:200]}")
        sys.exit(1)

    # Update state
    state["last_style"] = style_name
    state["last_niche"]  = niche_name
    state["last_title"]  = title
    state["last_url"]    = yt_url
    save_state(state)
    cleanup()

    est_rev = round((duration/60/1000)*niche["rpm"]*7000/1000,2)
    tg(f"<b>THE EVIDENCE ROOM PUBLISHED</b>\n\n"
       f"<b>{title}</b>\n"
       f"Style: {style_name}\nNiche: {niche_name} | ${niche['rpm']} RPM\n"
       f"Duration: {duration/60:.1f}min | Subtitles: {sub_count} lines\n\n"
       f"{yt_url}\n\nAll artifacts deleted.")
    print(f"\nPIPELINE COMPLETE: {yt_url}")

if __name__ == "__main__":
    main()
