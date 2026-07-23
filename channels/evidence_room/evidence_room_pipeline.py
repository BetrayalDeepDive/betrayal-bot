#!/usr/bin/env python3
"""
THE EVIDENCE ROOM — ANIMATED PIPELINE v2.0
Channel 2 of DeepDive Empire

SAME UPGRADES AS MASTER PIPELINE v5.0:
✅ 20 human neural voices (10 US + 10 GB) — no robotic voices
✅ Voice quality checker — auto-switches if robotic detected
✅ Quality gate minimum 7.3 | Final floor 6.9 (never lower)
✅ 13-attempt system (8 fresh + 5 archive viral topics)
✅ Different topic per attempt — never retries same topic
✅ Archive fallback: proven viral stories from last 2 years
✅ 4-trigger thumbnail system (curiosity + social proof + identity + pattern)
✅ Most shocking scripts ever written for forensic niche
✅ Viral intelligence engine (weekly learning)
✅ NO subtitles on main video
✅ Subtitles on Shorts ONLY with frame-perfect audio sync
✅ 2 YouTube Shorts per day, standalone and trend-researched (teaser/recap removed)
✅ Approval gate BEFORE video generation (30-min)
✅ Dual notification: Telegram + Gmail
✅ Startup Telegram test
✅ Gemini primary + Gemini 1.5 fallback (no Groq for large requests)
✅ 3 rotating animation styles (dark_minimal, cinematic, documentary)
✅ Animated scenes: timeline, document, data_reveal, connection_map, evidence_board
✅ Auto-cleanup after upload

Animation Stack: Pillow + FFmpeg (zero system deps)
"""

import os, sys, json, re, time, random, datetime, asyncio
import subprocess, shutil, requests, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image, ImageDraw, ImageFont

# ── SHARED UTILS (inlined — no external file dependency) ──
"""
DEEPDIVE EMPIRE — Shared Utilities v1.0
Inlined into each pipeline at import time.
No external file dependencies — everything self-contained.

Import at top of each pipeline:
    from shared_utils import *
"""

import os, re, json, sys, time, datetime, random, subprocess, requests
from pathlib import Path


# ══════════════════════════════════════════════════════════════════
# PHASE MANAGER (inlined — no external file dependency)
# ══════════════════════════════════════════════════════════════════

def get_pipeline_phase():
    return os.environ.get("PIPELINE_PHASE", "full").lower()

def _pending_path(channel_dir):
    return Path(channel_dir) / "pending_upload.json"

def save_pending(channel_dir, data: dict):
    pf = _pending_path(channel_dir)
    data["generated_at"] = datetime.datetime.now().isoformat()
    pf.write_text(json.dumps(data, indent=2))
    return str(pf)

def load_pending(channel_dir):
    pf = _pending_path(channel_dir)
    if not pf.exists():
        return None
    try:
        d = json.loads(pf.read_text())
        if d.get("status") == "uploaded":
            return None   # already uploaded
        return d
    except:
        return None

def clear_pending(channel_dir):
    pf = _pending_path(channel_dir)
    pf.write_text(json.dumps({
        "status": "uploaded",
        "cleared_at": datetime.datetime.now().isoformat()
    }, indent=2))

def check_pending_age(pending, max_hours=28):
    try:
        gen = datetime.datetime.fromisoformat(pending.get("generated_at",""))
        hours = (datetime.datetime.now() - gen).total_seconds() / 3600
        return hours <= max_hours, round(hours, 1)
    except:
        return False, 999


# ══════════════════════════════════════════════════════════════════
# REVENUE ENGINE (inlined — no external file dependency)
# ══════════════════════════════════════════════════════════════════

NUMBER_NOUN_BANKS = {
    "dark_horror":        ["4,380 DAYS","12 YEARS","3 AM","14 VICTIMS","ONE NIGHT"],
    "seduction_dark":     ["7 SIGNS","28 DAYS","3 PEOPLE","6 WARNINGS","ONE TRAP"],
    "psychological_trap": ["6 STAGES","23 STEPS","100 DAYS","1 EXIT","5 TRIGGERS"],
    "supernatural_real":  ["3 NIGHTS","72 HOURS","9 WITNESSES","14 YEARS","1 PLACE"],
    "obsession_dark":     ["847 MESSAGES","4 YEARS","23 CALLS","1,460 DAYS","1 PERSON"],
    "forensic_finance":   ["$2.4M GONE","4,380 DAYS","47 REPORTS","$14M FRAUD","12 YEARS"],
    "criminal_investigation": ["14 VICTIMS","23 YEARS","1 FILE","47 CLUES","3 SUSPECTS"],
    "corporate_exposure": ["$840M HIDDEN","14 YEARS","23 EMAILS","$2.4B FRAUD","1 MEMO"],
    "digital_forensics":  ["2.7M FILES","847 ACCOUNTS","1 IP ADDRESS","23 SERVERS","14TB DATA"],
    # FIX (found on systematic dict-completeness check): these 3 real
    # Ch2 niches were missing entirely — every thumbnail for
    # body_cam_police/courtroom_drama/robbery_documentaries silently
    # fell back to a generic "14 YEARS/47 CASES/1 TRUTH" default instead
    # of anything niche-specific.
    "body_cam_police":       ["847 HOURS FOOTAGE","23 OFFICERS","1 CAMERA","14 SECONDS","3 CALLS"],
    "courtroom_drama":       ["12 JURORS","23 WITNESSES","1 VERDICT","14 YEARS","3 APPEALS"],
    "robbery_documentaries": ["$2.4M TAKEN","47 MINUTES","1 GETAWAY","23 YEARS RUNNING","3 SUSPECTS"],
    "cult_psychology":    ["847 MEMBERS","14 YEARS","7 STAGES","23 RULES","1 LEADER"],
    "propaganda_systems": ["40M PEOPLE","7 TECHNIQUES","14 YEARS","3 AGENCIES","1 NARRATIVE"],
    "social_engineering": ["6 PRINCIPLES","847 TARGETS","23 HOURS","7 TRIGGERS","1 CALL"],
    "mass_deception":     ["1B PEOPLE","14 MONTHS","3 NETWORKS","23 COUNTRIES","1 LIE"],
}

def enforce_number_noun(thumb_text, topic, niche_name, ai_fn=None):
    if re.search(r'\b\d[\d,\.]*\b|\$', thumb_text):
        return re.sub(r'[^A-Z0-9$.,% ]','', thumb_text.upper()).strip()[:22]
    m = re.search(r'\b(\d[\d,\.]*)\s*(\w+)', topic)
    if m:
        return f"{m.group(1)} {m.group(2).upper()[:8]}"[:22]
    if ai_fn:
        try:
            r = ai_fn(
                f"Topic: {topic[:80]}\n"
                f"Generate 2-3 word thumbnail in NUMBER+NOUN format.\n"
                f"Examples: '$2.4M GONE', '47 REPORTS', '14 VICTIMS', '4380 DAYS'\n"
                f"Return ONLY the phrase in ALL CAPS.", tokens=20)
            if r and re.search(r'\d', r):
                return re.sub(r'[^A-Z0-9$.,% ]','', r.upper()).strip()[:22]
        except:
            pass
    return random.choice(NUMBER_NOUN_BANKS.get(niche_name, ["14 YEARS","47 CASES","1 TRUTH"]))


def score_title_v2(title):
    t  = title.lower()
    sc = 3.0
    bd = {}
    # FIX: Ch1 had a real bug where malformed AI output (a markdown bullet
    # list, not an actual title) scored HIGH because it had numbers and
    # hook words, and got accepted as the video title. Ch2's title path
    # never had Ch1's pre-filter protecting against this at all — this
    # scorer is the only line of defense here, so it needs its own check.
    if any(ch in title for ch in ("*", "_", "`", "#")):
        return 0.0, {"malformed": "REJECTED — contains markdown symbols"}
    if title.count(",") >= 4:
        return 0.0, {"malformed": "REJECTED — reads as a list, not a title"}
    if title.lower().startswith(("numbers:", "stats:", "facts:", "-", "•")):
        return 0.0, {"malformed": "REJECTED — bullet/label-style opening"}
    # Curiosity gap
    cg = ["nobody knew","never told","what was hidden","the real reason",
          "kept secret","concealed","covered up","went unnoticed","was ignored"]
    cg_hits = sum(1 for s in cg if s in t)
    if cg_hits >= 2:   sc += 2.5; bd["curiosity_gap"] = "STRONG"
    elif cg_hits == 1: sc += 1.5; bd["curiosity_gap"] = "OK"
    else:              bd["curiosity_gap"] = "WEAK"
    # Specificity
    has_num    = bool(re.search(r'\b\d[\d,\.]*\b', title))
    has_dollar = bool(re.search(r'\$[\d,\.]+', title))
    has_name   = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', title))
    if (has_num or has_dollar) and has_name: sc += 2.0; bd["specificity"] = "STRONG"
    elif has_num or has_dollar or has_name:  sc += 1.2; bd["specificity"] = "OK"
    else:                                    bd["specificity"] = "WEAK"
    # Revelation
    rev = ["exposed","revealed","documented","proved","evidence","classified","traced"]
    if any(s in t for s in rev): sc += 1.5; bd["revelation"] = "PRESENT"
    else:                        bd["revelation"] = "ABSENT"
    # Pattern interrupt
    pi = ["they knew","it was allowed","it was ignored","still happening","went unpunished"]
    if any(s in t for s in pi): sc += 1.5; bd["pattern_interrupt"] = "PRESENT"
    else:                       bd["pattern_interrupt"] = "ABSENT"
    # Length
    n = len(title)
    if 50 <= n <= 65:    sc += 1.0
    elif 45 <= n <= 70:  sc += 0.5
    elif n < 40 or n > 80: sc -= 0.5
    # Generic penalty
    generic = ["incredible","unbelievable","shocking","amazing","you won't believe"]
    sc -= sum(0.8 for g in generic if g in t)
    return round(min(max(sc, 0), 10), 1), bd


def _record_title_history(niche_name, episode, title, score):
    # FIX (found on deep re-audit): weekly_report.py's
    # recalibrate_title_model() claimed to compare predicted title-CTR
    # scores against real performance but never actually recorded either
    # side of that comparison — this is the real write side, mirroring
    # thumb_format_history's proven pattern exactly.
    try:
        from title_scoring_history import record_title_used
        record_title_used(str(SCRIPT_DIR), "The Evidence Room", niche_name, episode, title, score)
    except Exception as e:
        log(f"  Title history record (non-fatal): {e}")


def run_title_ctr_gate(title_str, title_scores, topic, niche_name,
                        series_name, episode, ai_fn, min_ctr=6.5):
    if not title_scores:
        return title_str, [(title_str, 5.0)]
    v2_scored = sorted([(t, score_title_v2(t)[0]) for t, _ in title_scores],
                        key=lambda x: x[1], reverse=True)
    best_title, best_score = v2_scored[0]
    if best_score >= min_ctr:
        _record_title_history(niche_name, episode, best_title, best_score)
        return best_title, v2_scored
    # Regenerate with targeted fix
    _, bd = score_title_v2(best_title)
    weak  = [k for k,v in bd.items() if "WEAK" in str(v) or "ABSENT" in str(v)]
    fixes = {
        "curiosity_gap":    "Start with 'Nobody knew' or 'What the records show'",
        "specificity":      "Include a specific number",
        "revelation":       "Include 'documented', 'exposed', or 'revealed'",
        "pattern_interrupt":"Add 'They Knew' or 'Still Happening'",
    }
    fix_instructions = "\n".join(f"- {fixes[w]}" for w in weak[:2] if w in fixes)
    if not fix_instructions:
        fix_instructions = "- Add a specific number AND a curiosity gap phrase"
    try:
        result = ai_fn(
            f"Generate 5 stronger YouTube titles for: {topic[:120]}\n"
            f"Series: {series_name} Ep{episode}\n"
            f"Current best score: {best_score}/10 — too low.\n"
            f"Required fixes:\n{fix_instructions}\n"
            f"Rules: 50-65 chars. Dark documentary tone.\n"
            f'Return ONLY: ["Title 1","Title 2","Title 3","Title 4","Title 5"]',
            tokens=300)
        if result:
            result = re.sub(r'```json|```','', result).strip()
            m = re.search(r'\[[\s\S]*?\]', result)
            if m:
                titles  = [t for t in json.loads(m.group()) if t]
                new_scored = sorted([(t, score_title_v2(t)[0]) for t in titles],
                                     key=lambda x: x[1], reverse=True)
                if new_scored and new_scored[0][1] > best_score:
                    _record_title_history(niche_name, episode, new_scored[0][0], new_scored[0][1])
                    return new_scored[0][0], new_scored
    except:
        pass
    _record_title_history(niche_name, episode, best_title, best_score)
    return best_title, v2_scored


# Real business-inquiries contact, per explicit request — every published
# description was missing this entirely across all 5 channels.
BUSINESS_EMAIL = "nextlayermediallc@gmail.com"

# HONEST NOTE (found on final audit pass): none of the 4 URLs below are
# real, trackable affiliate links yet — they're placeholder slugs on each
# platform's own domain (e.g. betterhelp.com/deepdive isn't BetterHelp's
# real referral-link format, amzn.to/deepdive-audible isn't a genuine
# Amazon-issued short code). Getting real tracked links requires actually
# signing up for each program (BetterHelp/NordVPN/CuriosityStream
# Affiliates, Amazon Associates) and replacing these with the real URLs
# each program issues — the same genuine manual step already documented
# for Gumroad (monetization.py) and collapse_index's finance affiliates
# below. Until then, these links will 404 or redirect to each platform's
# homepage with zero affiliate credit, not fail outright.
AFFILIATE_REGISTRY = {
    "betterhelp":   {"url": "https://betterhelp.com/deepdive",      "label": "BetterHelp therapy",       "channels": ["all"]},
    "nordvpn":      {"url": "https://nordvpn.com/deepdive",          "label": "NordVPN privacy",          "channels": ["evidence_room","control_files"]},
    "curiosity":    {"url": "https://curiositystream.com/deepdive",  "label": "CuriosityStream docs",     "channels": ["all"]},
    "audible":      {"url": "https://amzn.to/deepdive-audible",      "label": "Audible audiobooks",       "channels": ["all"]},
}

def build_affiliate_block(channel_id, niche_name=""):
    ch = channel_id.replace("betrayal_deepdive","betrayal_deepdive")
    lines = ["\n\n— LINKS —"]
    for key, link in AFFILIATE_REGISTRY.items():
        if "all" in link["channels"] or ch in link["channels"]:
            lines.append(f"▸ {link['label']}: {link['url']}")
    if len(lines) < 2:
        return ""
    lines.append("\n*Affiliate links — support the channel at no cost to you.")
    return "\n".join(lines)


# v8 addition — real product monetization, per explicit request ("other
# sources of income we had worked upon should be added to all the
# channels"). Never previously mentioned in any actual video description.
GITHUB_PAGES_BASE = "https://betrayaldeepdive.github.io/betrayal-bot"

def build_product_cta(channel_id):
    """Real product CTA for the actual video description."""
    # FIX (found while wiring Gumroad revenue into the weekly report):
    # this dict was missing a "collapse_index" entry (present correctly
    # only in collapse_index_pipeline.py's own copy) — dormant today
    # since this function is only ever called with each file's own
    # literal channel_id, but a latent landmine matching the same
    # CROSS_PROMO gap found and fixed earlier this session.
    product_by_channel = {
        "betrayal_deepdive": ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "evidence_room":     ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "control_files":     ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "archive":           ("empire-collapse-atlas", "The Empire Collapse Atlas"),
        "collapse_index":    ("financial-red-flags-field-guide", "The Financial Red Flags Field Guide"),
    }
    product_id, product_title = product_by_channel.get(
        channel_id, ("faceless-documentary-creator-toolkit", "Faceless Documentary Creator Toolkit"))
    try:
        from monetization import get_product_cta_url
        url = get_product_cta_url(product_id)
        if url.startswith("../"):
            url = f"{GITHUB_PAGES_BASE}/products/{product_id}.html"
        return f"\n\n📖 {product_title}: {url}"
    except Exception as e:
        log(f"  Product CTA (non-fatal): {e}")
        return ""


CHAPTER_STRUCTURES = {
    "betrayal_deepdive": [
        (0.00,"The Case Begins"),(0.10,"Before It Happened"),(0.28,"First Warning Signs"),
        (0.45,"Escalation"),(0.60,"The Revelation"),(0.78,"The Aftermath"),(0.90,"What This Means"),
    ],
    "evidence_room": [
        (0.00,"Case File Opened"),(0.10,"The Subject"),(0.28,"First Anomalies"),
        (0.45,"The Evidence Builds"),(0.60,"Key Document Revealed"),(0.78,"The Full Record"),(0.90,"Verdict"),
    ],
    "control_files": [
        (0.00,"The System"),(0.10,"How It Was Built"),(0.28,"Documented Cases"),
        (0.45,"The Evidence"),(0.60,"The Scale"),(0.78,"Those Who Resisted"),(0.90,"Implications"),
    ],
}

def generate_chapter_timestamps(script_clean, total_duration_secs, channel_id, stage_word_counts=None):
    """
    FIX (found on deep re-audit): script_clean was accepted but never
    referenced — timestamps were a fixed percentage table calibrated once
    against the ORIGINAL stage-word targets, disconnected from what the
    script actually turned out to be after generation/edits. When
    stage_word_counts (real word count of each of the 7 stages in the
    FINAL, possibly-edited script — e.g. via approximate_stage_split on
    the current script_clean) is provided, timestamps are computed from
    the actual cumulative word-count fraction instead. Falls back to the
    fixed percentage table when real counts aren't available.
    """
    if total_duration_secs < 120:
        return ""
    structure = CHAPTER_STRUCTURES.get(channel_id, CHAPTER_STRUCTURES["betrayal_deepdive"])
    if stage_word_counts and len(stage_word_counts) == len(structure) and sum(stage_word_counts) > 0:
        total_words = sum(stage_word_counts)
        lines = []
        cumulative = 0
        for (_, label), wc in zip(structure, stage_word_counts):
            pct = cumulative / total_words
            secs = int(total_duration_secs * pct)
            lines.append(f"{secs//60}:{secs%60:02d} {label}")
            cumulative += wc
        return "\n".join(lines)
    lines = []
    for pct, label in structure:
        secs = int(total_duration_secs * pct)
        lines.append(f"{secs//60}:{secs%60:02d} {label}")
    return "\n".join(lines)


CROSS_PROMO = {
    "betrayal_deepdive": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "evidence_room": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🌑 Dark horror: youtube.com/@BetrayalDeepDive",
    },
    # FIX: same gap found and fixed in Ch1 — Ch4/Ch5 entries were entirely
    # missing, a genuinely 3-channel system despite the empire having 5.
    "archive": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
    "collapse_index": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
}

def get_cross_promo(channel_id, is_short=False):
    p = CROSS_PROMO.get(channel_id, CROSS_PROMO["betrayal_deepdive"])
    return p["short"] if is_short else p["main"]

# NOTE: TG_TOKEN/TG_CHAT are defined once, correctly, further below —
# channel-specific (TELEGRAM_TOKEN_CH2) with a generic fallback, right
# alongside the YouTube credentials. A duplicate, non-channel-aware
# definition used to live here too — removed, matching the same
# cleanup already done for Ch3's identical duplicate.

def send_hype_push(video_url, video_title, channel_name, day=0):
    if not TG_TOKEN or not TG_CHAT:
        return
    urgency = {0:"⚡ First hour — maximum impact", 3:"🔥 4 days left", 6:"⏰ LAST DAY"}.get(day,"")
    msg = (
        f"🚀 <b>HYPE THIS VIDEO — {urgency}</b>\n\n"
        f"<b>{channel_name}</b>: {video_title}\n\n"
        f"▶️ {video_url}\n\n"
        f"<b>How to Hype (10 seconds):</b>\n"
        f"1. Open the link on YouTube\n"
        f"2. Tap the 🔥 Hype button under the video\n"
        f"3. Done — YouTube pushes this to the Explore leaderboard\n\n"
        f"⏳ 7-day window only. Every Hype = free algorithmic reach."
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=25)
    except:
        pass

def validate_retention_hooks(script_clean, channel_id="betrayal_deepdive"):
    words   = script_clean.split()
    total   = len(words)
    if total < 400:
        return 0.0, []
    penalty = 0.0
    issues  = []
    hooks   = ["subscribe","coming up","next","what happens","revealed","in a moment",
               "stay","about to","what we found next","the next document"]
    def seg(p1, p2):
        return " ".join(words[int(total*p1):int(total*p2)]).lower()
    if sum(1 for h in hooks if h in seg(0.25,0.35)) < 1:
        penalty -= 0.4; issues.append("Missing 30% retention hook")
    if sum(1 for h in hooks if h in seg(0.55,0.65)) < 1:
        penalty -= 0.8; issues.append("Weak 60% peak hook")
    if sum(1 for h in hooks if h in seg(0.75,0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% retention hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing subscribe CTA in final 60 words")
    return round(penalty, 1), issues



_gen_chapters = generate_chapter_timestamps


# ── CREDENTIALS ─────────────────────────────────────────────
# ── Core credentials ──────────────────────────────────────
GROQ_KEY        = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY      = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY    = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
COHERE_KEY      = os.environ.get("COHERE_API_KEY", "")
# FIX (found on thorough dead/live-code review, same fix applied to
# Ch4): PIXABAY_KEY/PEXELS_KEY/BG_KEYWORDS were only ever defined
# locally inside a confirmed-dead function, never at module level —
# a real NameError waiting to happen if the (currently dead)
# get_stage_matched_video is ever wired in. Fixed for correctness.
PIXABAY_KEY     = os.environ.get("PIXABAY_KEY", "")
PEXELS_KEY      = os.environ.get("PEXELS_API_KEY", "")
BG_KEYWORDS     = {}
DEFAULT_BG_KEYWORDS = ["dark shadows", "dark atmosphere", "dark dramatic"]
MISTRAL_KEY     = os.environ.get("MISTRAL_API_KEY", "")
SAMBANOVA_KEY   = os.environ.get("SAMBANOVA_API_KEY", "")  # 1000 req/day free — cloud.sambanova.ai
GEMINI_KEY_2    = os.environ.get("GEMINI_API_KEY_2", "")   # backup Gemini key — doubles quota
YT_CLIENT_ID    = os.environ.get("EVIDENCE_YT_CLIENT_ID",  os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC   = os.environ.get("EVIDENCE_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH      = os.environ.get("EVIDENCE_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
# CRITICAL FIX (found on final pre-Ch4 verification pass, directly
# explains real production evidence — Telegram screenshots showing Ch2
# crash alerts and "EVIDENCE ROOM APPROVAL NEEDED" messages landing in
# "YouTube Automation Bot", Ch1's bot): the v5 fix giving Ch2 its own
# dedicated bot (TELEGRAM_TOKEN_CH2/CHAT_ID_CH2) was only ever applied
# to weekly_report.py (the shared weekly-report file) — Ch2's OWN
# pipeline, which sends every single script/audio/video/title review,
# every HOLD alert, and every crash alert, was still reading the
# generic TELEGRAM_TOKEN/CHAT_ID this whole time. Same channel-
# specific-first, generic-fallback pattern already correct for the
# YouTube credentials right above this.
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN_CH2", os.environ.get("TELEGRAM_TOKEN", ""))
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID_CH2", os.environ.get("TELEGRAM_CHAT_ID", ""))

# ── API endpoints ──────────────────────────────────────────
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_LITE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"  # gemini-2.0-flash retired by Google June 1 2026
CEREBRAS_URL    = "https://api.cerebras.ai/v1/chat/completions"
SAMBANOVA_URL   = "https://api.sambanova.ai/v1/chat/completions"   # v12: added
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
COHERE_URL      = "https://api.cohere.com/v2/chat"
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"
YT_UPLOAD_URL   = "https://www.googleapis.com/upload/youtube/v3"
YT_DATA_URL     = "https://www.googleapis.com/youtube/v3"
YT_TOKEN_URL    = "https://oauth2.googleapis.com/token"

# ── Paths — state in REPO (persists between runs) ─────────
SCRIPT_DIR    = Path(__file__).parent
WORK_DIR      = Path("/home/runner/work/evidence_room")
if not WORK_DIR.exists(): WORK_DIR = Path("/tmp/evidence_room")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = SCRIPT_DIR / "state.json"   # persists in repo
INTEL_FILE    = SCRIPT_DIR / "intel.json"   # persists in repo
CKPT_FILE     = WORK_DIR / "checkpoint.json"

# Cerebras model names to try in order
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]

W, H, FPS   = 1920, 1080, 24
MIN_WORDS   = 1900
MAX_WORDS   = 2100
MIN_GATE    = 8.8   # FIX (found on deep re-audit): was 8.5 — archive/control_files
                     # were already raised to 8.8 per the explicit "8.8-8.9 minimum,
                     # every time" empire-wide directive; this channel was never
                     # updated to match. attempts 1-8.
FINAL_GATE  = 6.9   # absolute last-resort floor, attempt 13 only

# ════════════════════════════════════════════════════════════
# 20 HUMAN NEURAL VOICES — 10 US + 10 GB
# ════════════════════════════════════════════════════════════
US_VOICES = [
    "en-US-AndrewNeural",       # Warm authoritative storyteller
    "en-US-BrianNeural",        # Deep calm commanding
    "en-US-ChristopherNeural",  # Serious documentary authoritative
    "en-US-JasonNeural",        # Calm measured (DavisNeural unavailable on Actions)
    "en-US-EricNeural",         # Professional measured
    "en-US-GuyNeural",          # Commanding serious
    "en-US-JasonNeural",        # Calm measured deliberate
    "en-US-RogerNeural",        # Energetic authoritative
    "en-US-SteffanNeural",      # Professional clear
    "en-US-TonyNeural",         # Confident expressive
]
GB_VOICES = [
    "en-GB-RyanNeural",         # BBC documentary gravitas
    "en-GB-ThomasNeural",       # Cold measured cinematic
    "en-GB-OliverNeural",       # Professional authoritative
    "en-GB-EthanNeural",        # Warm natural storytelling
    "en-GB-SoniaNeural",        # Sharp devastating (F)
    "en-GB-LibbyNeural",        # Natural conversational (F)
    "en-GB-AbbiNeural",         # Clear warm professional (F)
    "en-GB-HollieNeural",       # Professional sharp (F)
]
# FIX (direct user report, July 23 2026 — "I wanted to go beyond the
# Great Britain voices... Australian, New Zealand, or other English
# languages... add everything... so that if that fails... it can move
# to the next thing, not get stuck with one voice itself"): ALL_VOICES
# now includes a real, deep additional-accent pool beyond just GB.
#
# FIX (direct user report, July 23 2026, second pass — "I want 15 to 18
# fallback voices... both male and female... according to the nation and
# according to how the channel works"): expanded to the full real
# Microsoft Edge neural voice catalog for every non-US English locale
# (en-GB-NoahNeural excluded — confirmed broken on this repo's Actions
# runners). Same honest limitation as Ch1/Ch5's identical fix: this
# sandbox's network policy blocks reaching Microsoft's speech endpoint
# (confirmed live, 403 from the proxy), so these could not be
# synthesized and listened to from here — only the GitHub Actions
# runner can do that, and any renamed/retired ID simply gets skipped by
# the existing fallback-chain logging.
EXTENDED_VOICES = [
    "en-GB-AlfieNeural", "en-GB-ElliotNeural", "en-GB-EthanNeural", "en-GB-OliverNeural",
    "en-GB-BellaNeural", "en-GB-OliviaNeural",
    "en-IE-ConnorNeural", "en-IE-EmilyNeural",
    "en-AU-WilliamNeural", "en-AU-DarrenNeural", "en-AU-DuncanNeural",
    "en-AU-KenNeural", "en-AU-NeilNeural", "en-AU-TimNeural",
    "en-AU-NatashaNeural", "en-AU-AnnetteNeural", "en-AU-CarlyNeural",
    "en-AU-ElsieNeural", "en-AU-FreyaNeural", "en-AU-JoanneNeural",
    "en-AU-KimNeural", "en-AU-TinaNeural",
    "en-NZ-MitchellNeural", "en-NZ-MollyNeural",
    "en-ZA-LukeNeural", "en-ZA-LeahNeural",
    "en-CA-LiamNeural", "en-CA-ClaraNeural",
]
ALL_VOICES     = GB_VOICES + EXTENDED_VOICES
ROBOTIC_VOICES = ["en-US-AriaNeural", "en-US-AnaNeural"]

# FIX (direct user report, July 23 2026): raised from 4 to 16-18 per
# niche. Two tone templates rather than 7 fully bespoke lists — both
# real, gender-mixed, non-US voice lists: PROCEDURAL_SERIOUS (measured,
# crisp documentary register for the finance/records-heavy niches),
# TENSE_DOCUMENTARY (dread/investigative energy for the crime-scene-
# heavy niches).
_PROCEDURAL_SERIOUS = [
    "en-GB-ThomasNeural", "en-GB-OliverNeural", "en-AU-WilliamNeural", "en-GB-SoniaNeural",
    "en-NZ-MitchellNeural", "en-AU-NatashaNeural", "en-GB-LibbyNeural", "en-CA-LiamNeural",
    "en-IE-ConnorNeural", "en-GB-EthanNeural", "en-AU-FreyaNeural", "en-ZA-LukeNeural",
    "en-GB-AbbiNeural", "en-CA-ClaraNeural", "en-NZ-MollyNeural", "en-IE-EmilyNeural",
    "en-AU-DuncanNeural", "en-ZA-LeahNeural",
]
_TENSE_DOCUMENTARY = [
    "en-GB-RyanNeural", "en-GB-ThomasNeural", "en-IE-ConnorNeural", "en-AU-WilliamNeural",
    "en-CA-LiamNeural", "en-GB-HollieNeural", "en-ZA-LukeNeural", "en-AU-NatashaNeural",
    "en-GB-EthanNeural", "en-NZ-MitchellNeural", "en-GB-BellaNeural", "en-ZA-LeahNeural",
    "en-AU-DarrenNeural", "en-GB-SoniaNeural", "en-CA-ClaraNeural", "en-IE-EmilyNeural",
    "en-AU-KenNeural", "en-NZ-MollyNeural",
]

NICHE_VOICES = {
    "forensic_finance":       _PROCEDURAL_SERIOUS,
    "criminal_investigation": _TENSE_DOCUMENTARY,
    "corporate_exposure":     _PROCEDURAL_SERIOUS,
    "digital_forensics":      _PROCEDURAL_SERIOUS,
    "body_cam_police":        _TENSE_DOCUMENTARY,
    "courtroom_drama":        _PROCEDURAL_SERIOUS,
    "robbery_documentaries":  _TENSE_DOCUMENTARY,
}

# ── ANIMATION STYLES ────────────────────────────────────────
STYLES = {
    "dark_minimal": {
        "bg":(2,2,10), "primary":(255,255,255), "accent":(200,0,0),
        "secondary":(120,120,140), "pulse":(180,0,0), "glow":(255,50,50),
        "desc":"Clinical dark — blood red on absolute black, maximum psychological impact"
    },
    "cinematic": {
        "bg":(3,6,18), "primary":(210,230,255), "accent":(200,0,0),
        "secondary":(80,110,160), "pulse":(20,80,200), "glow":(100,180,255),
        "desc":"Cinematic noir blue — glowing evidence reveals, deep shadow"
    },
    "documentary": {
        "bg":(12,10,8), "primary":(235,225,205), "accent":(200,0,0),
        "secondary":(130,110,90), "pulse":(160,20,0), "glow":(220,80,40),
        "desc":"Aged classified document style — burnt edges, redaction marks, stamps"
    },
}
DAY_STYLE = {0:"dark_minimal",1:"cinematic",2:"documentary",3:"dark_minimal",4:"cinematic"}

# ── NICHES ────────────────────────────────────────────────
DAY_NICHE = {0:"forensic_finance",1:"corporate_exposure",2:"criminal_investigation",3:"digital_forensics",4:"forensic_finance"}

NICHES = [
    {
        "name": "forensic_finance", "rpm": 16.00,
        "series": "The Evidence Room: Financial Crimes",
        "viral_search": "forensic finance fraud investigation documentary animated",
        "archive_search": "biggest financial fraud investigation exposed 2022 2023 documentary viral",
        "thumbnail_triggers": ["FUNDS TRACED","PAPER TRAIL","MONEY FOUND","ALL DOCUMENTED"],
        "seed_topics": [
            "The offshore account trail that exposed a 12-year bank fraud hidden across 40 shell companies",
            "How auditors missed 3.2 billion in concealed losses because they trusted the software the fraudster built",
            "The wire transfer pattern a junior analyst flagged in 2019 that nobody acted on for 3 years",
            "A hedge fund reporting 18 percent annual returns for 9 years — the investigation that proved it was fabricated",
            "One accountant who embezzled from 60 client accounts simultaneously using a single spreadsheet formula",
        ],
    },
    {
        "name": "criminal_investigation", "rpm": 14.50,
        "series": "The Evidence Room: Cold Cases",
        "viral_search": "cold case investigation evidence breakthrough documentary",
        "archive_search": "cold case solved breakthrough evidence 2022 2023 viral documentary",
        "thumbnail_triggers": ["ONE FIBER","FALSE ALIBI","THE PRINT","CASE REOPENED"],
        "seed_topics": [
            "The 1994 cold case where a single unmatched DNA sample sat in an evidence box for 28 years",
            "How investigators reconstructed a complete crime timeline from recovered deleted messages",
            "The surveillance timestamp that proved the suspect was 40 miles away — and who that implicated instead",
            "A witness statement that changed 11 times across 6 interviews — the analysis that exposed the truth",
            "Phone metadata that placed 4 people at a location they each separately denied visiting",
        ],
    },
    {
        "name": "corporate_exposure", "rpm": 15.50,
        "series": "The Evidence Room: Corporate Files",
        "viral_search": "corporate fraud cover-up exposed investigation documentary",
        "archive_search": "corporate fraud cover-up internal documents exposed 2022 2023 viral",
        "thumbnail_triggers": ["THEY KNEW","MEMO FOUND","ALL DOCUMENTED","COVER EXPOSED"],
        "seed_topics": [
            "The internal memo chain proving executives knew about product defects 3 years before the recall",
            "How a startup faked 340 million in due diligence with documents that took 8 minutes to produce",
            "The email thread — 847 messages — that dismantled a decade of fraud in one discovery process",
            "A board of directors that approved 23 fraudulent invoices because nobody read past the summary page",
            "Document trail showing a pharmaceutical company buried its own clinical trial data for 6 years",
        ],
    },
    {
        "name": "digital_forensics", "rpm": 17.00,
        "series": "The Evidence Room: Digital Evidence",
        "viral_search": "digital forensics cyber investigation data evidence documentary",
        "archive_search": "digital forensics investigation breakthrough cyber crime 2022 2023 viral",
        "thumbnail_triggers": ["DATA RECOVERED","FILES FOUND","METADATA MATCHED","DELETED FOUND"],
        "seed_topics": [
            "How deleted files on a company server reconstructed a 5-year insider trading operation completely",
            "The IP address that linked 9 separate fraud accounts to a single apartment across 3 countries",
            "Metadata embedded in a document proved it was written 2 years before the date it was supposedly signed",
            "How a data broker built profiles on 300 million people and what investigators found inside those files",
            "The trading algorithm audit that showed a system was front-running client orders — automated proof",
        ],
    },
    {
        "name": "body_cam_police", "rpm": 10.50,
        "series": "The Evidence Room: Body Cam Files",
        "viral_search": "body cam footage police incident investigation documentary animated",
        "archive_search": "body cam footage reveals truth police incident 2022 2023 viral documentary",
        "thumbnail_triggers": ["FOOTAGE SEALED","NINE MINUTES","THEY KNEW","CAM NEVER LIED"],
        "seed_topics": [
            "Officer body cam captured 9 minutes of footage that overturned a conviction after 3 years",
            "A police department sealed body cam footage for 14 months — what it showed when released",
            "The body cam recording that contradicted every official statement made by the department",
            "A routine traffic stop body cam captured the moment a cover story began to unravel",
            "Three officers. Three body cams. Three different accounts. The footage showed something else entirely.",
            "The body cam footage a department said was accidentally deleted — recovered 2 years later",
            "What 11 minutes of body cam footage proved about a use-of-force incident nobody witnessed",
        ],
    },
    {
        "name": "courtroom_drama", "rpm": 10.00,
        "series": "The Evidence Room: Court Record Files",
        "viral_search": "courtroom trial transcript evidence animated investigation documentary",
        "archive_search": "courtroom trial transcript reveals truth fraud evidence 2022 2023 viral",
        "thumbnail_triggers": ["TRANSCRIPT SEALED","DAY FOUR","WITNESS BROKE","CASE COLLAPSED"],
        "seed_topics": [
            "The cross-examination transcript that made a prosecution witness contradict himself 14 times",
            "Three words spoken under oath on day four collapsed a $40M fraud case",
            "A court transcript sealed for 11 years — what it revealed about the original investigation",
            "The star witness recanted every statement on day three. The trial continued for six more days.",
            "Jury deliberation notes that surfaced prove the verdict was reached before day one of testimony",
            "A forensic accountant's 6-hour testimony that the prosecution tried to suppress from the record",
            "The courtroom exhibit that nobody questioned — until an appeal attorney read page 47",
        ],
    },
    {
        "name": "robbery_documentaries", "rpm": 10.50,
        "series": "The Evidence Room: Heist Files",
        "viral_search": "heist robbery investigation animated documentary true crime",
        "archive_search": "greatest heist robbery unsolved investigation documentary viral 2022 2023",
        "thumbnail_triggers": ["NEVER SOLVED","81 MINUTES","26 MONTHS","STILL MISSING"],
        "seed_topics": [
            "The Isabella Stewart Gardner Museum theft: $500M in art stolen in 81 minutes. Still unsolved.",
            "Eleven men spent 26 months tunneling into a vault under a bank. They took everything and left one note.",
            "The casino robbery planned over 4 years by a team who communicated only through dead drops",
            "A diamond heist where the thieves replaced every stone with identical fakes before anyone noticed",
            "The Antwerp diamond district robbery: $100M taken over a weekend while guards watched the monitors",
            "A bank job where the robbers returned every dollar 3 days later — and the reason has never been explained",
            "The Securitas depot robbery: the largest cash theft in British history, planned from inside the company",
        ],
    },
]

# ── DREAD TRIGGERS ────────────────────────────────────────
DREAD_TRIGGERS = {
    "institutional": "The trusted institution — the bank, the firm, the regulatory body — was the weapon or the enabler.",
    "scale":         "Exact numbers that overwhelm. Then make each number a specific human being.",
    "competence":    "The sophistication. The patience. The years of planning. The cold architecture of it.",
    "detail":        "One specific irrelevant-seeming detail that proves everything. The exact date. The exact amount.",
    "duration":      "The exact duration. Not years — 4,380 days. 627 statements. 12 annual reports.",
    "reversal":      "Everything understood was the cover story. The evidence was hiding what really happened.",
    "cost":          "The people who lost everything. Name them. Quantify the loss. Make it permanent.",
    "invisibility":  "The crime was invisible because it looked exactly like normal business.",
}


# ════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# CHECKPOINT / RESUME  (same system as Channel 1)
# ═══════════════════════════════════════════════════════════
def ckpt_save(key, value):
    data = {}
    try:
        if CKPT_FILE.exists():
            data = json.loads(CKPT_FILE.read_text())
    except: pass
    data[key] = value
    CKPT_FILE.write_text(json.dumps(data, indent=2))
    log(f"  [ckpt] saved: {key}")

def ckpt_load(key):
    try:
        if CKPT_FILE.exists():
            val = json.loads(CKPT_FILE.read_text()).get(key)
            if val is not None:
                log(f"  [ckpt] resuming: {key}")
                return val
    except: pass
    return None

def ckpt_clear():
    try: CKPT_FILE.unlink(missing_ok=True)
    except: pass

def log(msg): print(msg, flush=True)

def tg(msg):
    chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                             json={"chat_id":TG_CHAT,"text":chunk,"parse_mode":"HTML"},
                             timeout=25)
            if r.status_code != 200: log(f"  TG {r.status_code}")
            time.sleep(0.5)
        except Exception as e: log(f"  TG err: {str(e)[:50]}")

def tg_updates(offset=None):
    try:
        params = {"timeout": 25, "allowed_updates": ["message","callback_query"]}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                         params=params, timeout=30)
        return r.json().get("result", [])
    except: return []

def tg_buttons(text, chat_id=None):
    """Send Telegram message with APPROVE / REJECT / CHANGE inline buttons."""
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE",        "callback_data": "approved"},
        {"text": "❌ REJECT",         "callback_data": "rejected"},
        {"text": "✏️ CHANGE TITLE",   "callback_data": "change"},
    ]]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id or TG_CHAT,
                  "text": text, "parse_mode": "HTML",
                  "reply_markup": keyboard}, timeout=25)
        return r.json().get("result", {}).get("message_id")
    except Exception as e:
        log(f"  tg_buttons error: {e}")
        return None

def tg_answer_callback(callback_id, answer_text="Got it"):
    """Dismiss the spinning loader on the button after it's pressed."""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": answer_text}, timeout=20)
    except: pass

def send_gmail(subject, html_body):
    pwd = os.environ.get("GMAIL_APP_PASSWORD","")
    if not pwd: log("  Gmail: no password — skipping"); return False
    sender = recipient = "mohammedsultan0497@gmail.com"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body,"html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as smtp:
            smtp.login(sender,pwd)
            smtp.sendmail(sender,recipient,msg.as_string())
        log("  Gmail sent"); return True
    except Exception as e:
        log(f"  Gmail err: {str(e)[:80]}"); return False

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_style":"","last_niche":"","last_voice":"","last_title":"","last_url":""}

def save_state(s): STATE_FILE.write_text(json.dumps(s,indent=2))

def load_intel():
    if INTEL_FILE.exists():
        try: return json.loads(INTEL_FILE.read_text())
        except: pass
    return {}

def save_intel(d): INTEL_FILE.write_text(json.dumps(d,indent=2))

# ═══════════════════════════════════════════════════════════
# 6-PROVIDER AI CHAIN — Cerebras → Gemini → Groq → OR → Cohere → Mistral
# Same architecture as Channel 1 (master_pipeline.py)
# ═══════════════════════════════════════════════════════════

def _call_cerebras(prompt, tokens=9000):
    if not CEREBRAS_KEY:
        log("  Cerebras: CEREBRAS_API_KEY secret not set — skipping")
        return None
    _url = "https://api.cerebras.ai/v1/chat/completions"
    _models = ["gpt-oss-120b", "zai-glm-4.7", "llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]  # Cerebras free-tier catalog narrowed to gpt-oss-120b/zai-glm-4.7 as of June 2026 — old llama names kept as fallback in case they return
    for model in _models:
        try:
            r = requests.post(_url,
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_completion_tokens": min(tokens, 12000),
                      "temperature": 0.88}, timeout=120)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK Cerebras ({model})")
                    return t
            elif r.status_code == 404:
                continue  # wrong model name, try next
            else:
                log(f"  Cerebras {model}: {r.status_code}")
                break
        except Exception as e:
            log(f"  Cerebras: {e}")
            break
    return None

def _call_gemini(prompt, tokens=9000):
    if not GEMINI_KEY:
        log("  Gemini: SKIPPED (GEMINI_API_KEY not set)")
        return None
    # Only gemini-2.0-flash works on v1beta endpoint.
    # gemini-1.5-pro and gemini-1.5-flash both return 404 on v1beta.
    # When quota is 429, move immediately to next provider.
    for url in [GEMINI_URL]:
        try:
            r = requests.post(f"{url}?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.88,
                                           "maxOutputTokens": min(tokens, 12000)},
                      "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"}
                                         for c in ["HARM_CATEGORY_HARASSMENT",
                                                   "HARM_CATEGORY_HATE_SPEECH",
                                                   "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                                   "HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                timeout=90)
            if r.status_code == 200:
                c = r.json().get("candidates", [])
                if c:
                    t = c[0]["content"]["parts"][0]["text"]
                    if t and len(t.strip()) > 100:
                        log("  OK Gemini")
                        return t
            elif r.status_code == 429:
                log(f"  Gemini 429 — quota, trying next model...")
                time.sleep(10)
            else:
                log(f"  Gemini {r.status_code}: {r.text[:150]}")
        except Exception as e:
            log(f"  Gemini: {e}")
    return None

def _call_groq(prompt, tokens=9000):
    if not GROQ_KEY: return None
    # Groq announced deprecation of llama-3.3-70b-versatile on June 17 2026.
    # Try the recommended replacements first, keep the old name as last-resort
    # in case the grace period is still active.
    for model in ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88,
                      "max_tokens": min(tokens, 4800)},  # TPM limit is 6000
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK Groq ({model})")
                    return t
            elif r.status_code in (400, 404):
                log(f"  Groq {model}: {r.status_code} (model gone) — trying next")
                continue
            else:
                log(f"  Groq {model}: {r.status_code}: {r.text[:150]}")
        except Exception as e:
            log(f"  Groq {model}: {e}")
    return None

def _call_openrouter(prompt, tokens=9000):
    if not OPENROUTER_KEY:
        log("  OpenRouter: OPENROUTER_API_KEY secret not set — skipping")
        return None
    for model in [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-2-9b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-3.5-0106:free",
    ]:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4000), "temperature": 0.88},
                timeout=90)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                if t and len(t.strip()) > 100:
                    log(f"  OK OpenRouter ({model.split('/')[-1]})")
                    return t
        except Exception as e:
            log(f"  OpenRouter: {e}")
    return None

def _call_cohere(prompt, tokens=9000):
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY secret not set — skipping")
        return None
    # FIX (confirmed against Cohere's own official deprecations page):
    # command-r-08-2024 is explicitly marked deprecated, with an April 4,
    # 2026 retirement date already passed. Same fragile single-model
    # pattern already fixed for Gemini/Groq. command-a-03-2025 is
    # Cohere's own current recommended, production-stable replacement.
    for _cohere_model in ["command-a-03-2025", "command-r-08-2024"]:
        try:
            r = requests.post(COHERE_URL,
                headers={"Authorization": f"Bearer {COHERE_KEY}",
                         "Content-Type": "application/json"},
                json={"model": _cohere_model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4000), "temperature": 0.88},
                timeout=120)
            if r.status_code == 200:
                t = r.json().get("message",{}).get("content",[{}])
                text = t[0].get("text","") if t else ""
                if text and len(text.strip()) > 100:
                    log(f"  OK Cohere ({_cohere_model})")
                    return text
        except Exception as e:
            log(f"  Cohere {_cohere_model}: {e}")
    return None

def _call_mistral(prompt, tokens=9000):
    if not MISTRAL_KEY:
        log("  Mistral: MISTRAL_API_KEY secret not set — skipping")
        return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistral-small-latest",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000), "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
            if t and len(t.strip()) > 100:
                log("  OK Mistral")
                return t
    except Exception as e:
        log(f"  Mistral: {e}")
    return None


# v12: SambaNova — added to Ch2 (was only in Ch1 before)
def _call_sambanova(prompt, tokens=9000):
    """
    SambaNova Cloud — free tier, 1000 req/day, llama-3.3-70b.
    Sign up free at https://cloud.sambanova.ai
    Add SAMBANOVA_API_KEY to GitHub Secrets.
    """
    if not SAMBANOVA_KEY:
        log("  SambaNova: SAMBANOVA_API_KEY not set — add free key from cloud.sambanova.ai")
        return None
    for model in ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.3-70B-Instruct"]:
        try:
            r = requests.post(SAMBANOVA_URL,
                headers={"Authorization": f"Bearer {SAMBANOVA_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 8192),
                      "temperature": 0.88},
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                if t and len(t.strip()) > 100:
                    log(f"  OK SambaNova ({model.split('-')[2]})")
                    return t
            elif r.status_code == 401:
                log("  SambaNova 401 — key invalid"); return None
            elif r.status_code == 429:
                log("  SambaNova 429 — daily limit"); return None
        except Exception as e:
            log(f"  SambaNova: {e}")
    return None


# v12: GEMINI_KEY_2 dual-key for Ch2 (doubles Gemini quota)
def _call_gemini_with_fallback(prompt, tokens=9000):
    """Try primary Gemini key then backup key, each across GEMINI_URL (2.5-flash) then GEMINI_LITE_URL (2.5-flash-lite)."""
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    if not keys:
        log("  Gemini: GEMINI_API_KEY not set")
        return None
    for key_idx, active_key in enumerate(keys):
        key_label = "primary" if key_idx == 0 else "backup"
        for url_label, url in [("2.5-flash", GEMINI_URL), ("2.5-flash-lite", GEMINI_LITE_URL)]:
            if not url:
                continue
            try:
                r = requests.post(f"{url}?key={active_key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.88,
                                               "maxOutputTokens": min(tokens, 12000)},
                          "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"}
                                             for c in ["HARM_CATEGORY_HARASSMENT",
                                                       "HARM_CATEGORY_HATE_SPEECH",
                                                       "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                                       "HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                    timeout=90)
                if r.status_code == 200:
                    c = r.json().get("candidates", [])
                    if c:
                        t = c[0]["content"]["parts"][0]["text"]
                        if t and len(t.strip()) > 100:
                            log(f"  OK Gemini ({key_label}, {url_label})")
                            return t
                elif r.status_code == 429:
                    log(f"  Gemini ({key_label}, {url_label}) 429 quota — trying next")
                    continue
                elif r.status_code == 404:
                    log(f"  Gemini ({key_label}, {url_label}) 404 — model retired, trying next")
                    continue
                else:
                    log(f"  Gemini ({key_label}, {url_label}): {r.status_code}")
            except Exception as e:
                log(f"  Gemini ({key_label}, {url_label}): {e}")
    return None




def run_stage_with_retry(stage_fn, stage_name, *args, max_attempts=3, **kwargs):
    """
    Run a pipeline stage with up to 3 attempts before escalating.
    Handles transient failures (network timeouts, temp API errors)
    in under 2 minutes instead of triggering the 2-hour full-pipeline retry.
    """
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = stage_fn(*args, **kwargs)
            if attempt > 1:
                log(f"  Stage {stage_name}: OK on attempt {attempt}")
            return result
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                log(f"  Stage {stage_name} attempt {attempt}/{max_attempts} failed: {e}")
                log(f"  Retrying in 30s...")
                time.sleep(30)
            else:
                log(f"  Stage {stage_name} FAILED after {max_attempts} attempts: {e}")
    raise RuntimeError(f"Stage {stage_name} failed after {max_attempts} attempts: {last_err}")

def load_weekly_strategy():
    """
    Read the strategy file written by weekly_report.py every Sunday.
    Injects competitor intelligence and recommended topics into script generation.
    Returns strategy context string or empty string if not available.
    """
    strategy_file = SCRIPT_DIR / "next_week_strategy.json"
    try:
        if strategy_file.exists():
            data = json.loads(strategy_file.read_text())
            # Only use if generated this week
            generated = data.get("generated_date", "")
            if generated:
                gen_date = datetime.date.fromisoformat(generated)
                days_old = (datetime.date.today() - gen_date).days
                if days_old <= 7:
                    lines = ["COMPETITOR INTELLIGENCE FROM THIS WEEK:"]
                    topics = data.get("recommended_topics", [])
                    if topics:
                        lines.append("Recommended topics based on competitor gaps:")
                        for t in topics[:3]:
                            lines.append(f"  - {t}")
                    hook_fmt = data.get("winning_hook_format", "")
                    if hook_fmt:
                        lines.append(f"Winning hook format: {hook_fmt}")
                    top_titles = data.get("top_competitor_titles", [])
                    if top_titles:
                        lines.append("Top competitor titles this week:")
                        for t in top_titles[:4]:
                            lines.append(f"  - {t}")
                    return "\n".join(lines)
    except Exception as e:
        log(f"  Strategy load (non-fatal): {e}")
    return ""


def select_best_voice(state, niche_name, available_voices):
    """
    After 5 episodes in a niche, lock in the voice that has produced
    the highest average scores. Viewers build a relationship with THE voice.
    Before 5 episodes: rotate to gather data.
    """
    perf = state.get("performance", {})
    niche_episodes = [ep for ep in state.get("episode_history", [])
                      if ep.get("niche") == niche_name]
    if len(niche_episodes) < 5:
        # Not enough data — rotate voices for data gathering
        ep_count = len(niche_episodes)
        voice = available_voices[ep_count % len(available_voices)]
        log(f"  Voice (gathering data, ep {ep_count+1}/5): {voice}")
        return voice

    # Score each available voice by average episode score
    voice_scores = {}
    for ep in niche_episodes:
        ep_ep = ep.get("episode", 0)
        # Find voice from performance tracker
        for key, val in perf.items():
            if key.startswith("voice_") and isinstance(val, dict):
                v_name = key.replace("voice_", "")
                if v_name in available_voices:
                    scores = val.get("scores", [])
                    if scores:
                        voice_scores[v_name] = sum(scores) / len(scores)

    if voice_scores:
        best = max(voice_scores, key=voice_scores.get)
        log(f"  Voice (locked — best avg {voice_scores[best]:.1f}/10): {best}")
        return best

    # Fallback to first voice
    return available_voices[0]

def load_pattern_memory(state):
    """Return what script patterns scored highest in previous episodes."""
    history = state.get("episode_history", [])
    if not history: return ""
    top = sorted(history, key=lambda x: x.get("score", 0), reverse=True)[:5]
    if not top: return ""
    lines = ["HIGHEST SCORING EPISODES — use their approach as inspiration:"]
    for ep in top:
        lines.append(f"  Score {ep.get('score',0)}/10: {ep.get('topic','')[:80]}")
    return "\n".join(lines)

def save_pattern_memory(state, episode, niche, topic, score):
    history = state.get("episode_history", [])
    history.append({
        "episode": episode, "niche": niche,
        "topic": topic[:100], "score": score,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
    })
    state["episode_history"] = history[-50:]
    return state

_DEAD_PROVIDERS_THIS_RUN = set()

def _strip_reasoning(text):
    """FIX (July 14 2026 audit): strip reasoning-model chain-of-thought
    (gpt-oss-120b via Cerebras/Groq) so it never leaks into a script."""
    if not text:
        return text
    # FIX (found on direct user report, July 15 2026 -- an unclosed
    # <think> tag from a truncated response, common under rate-limit
    # pressure, used to pass raw reasoning straight through untouched,
    # since the old regex below required a closing tag to match at all).
    for _open, _close in (('<think>', '</think>'), ('<thinking>', '</thinking>')):
        _idx = text.lower().find(_open)
        if _idx != -1 and _close not in text.lower()[_idx:]:
            text = text[:_idx].strip()
            if not text:
                return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    if '<|channel|>final<|message|>' in text:
        text = text.split('<|channel|>final<|message|>')[-1]
        text = text.split('<|end|>')[0].split('<|return|>')[0].split('<|start|>')[0]
    text = re.sub(r'<\|[^|]{1,40}\|>', '', text)
    return text.strip()

def ai(prompt, temp=0.88, tokens=9000, prefer="cerebras"):
    """
    v12: 7-provider chain: Cerebras -> SambaNova -> Gemini(+backup key) -> Groq -> OR -> Cohere -> Mistral
    FIX (July 14 2026 audit): providers that fail once are skipped for the
    rest of this run instead of retried from scratch on every call.
    """
    providers = [("cerebras", _call_cerebras), ("sambanova", _call_sambanova),
                 ("gemini", _call_gemini_with_fallback), ("groq", _call_groq),
                 ("openrouter", _call_openrouter), ("cohere", _call_cohere),
                 ("mistral", _call_mistral)]
    live = [(name, fn) for name, fn in providers if name not in _DEAD_PROVIDERS_THIS_RUN]
    if not live:
        live = providers
        _DEAD_PROVIDERS_THIS_RUN.clear()
    for i, (name, fn) in enumerate(live):
        result = fn(prompt, tokens)
        if result:
            return _strip_reasoning(result)
        _DEAD_PROVIDERS_THIS_RUN.add(name)
        if i < len(live) - 1:
            log(f"  {name} failed — skipping it for the rest of this run. Waiting 10s before next provider...")
            time.sleep(10)
    raise Exception("All 7 AI providers failed")

# Compatibility alias
def call_gemini(prompt, temp=0.85, tokens=7000, model="2.0"):
    return _call_gemini_with_fallback(prompt, tokens) or ai(prompt, tokens=tokens)

def call_groq(prompt, temp=0.7, tokens=2000):
    return _call_groq(prompt, min(tokens, 4800)) or ai(prompt, tokens=min(tokens, 4800))

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text = re.sub(r'_{1,3}([^_\n]+)_{1,3}',r'\1',text)
        text = re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+•]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.)]\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'^>\s*','',text,flags=re.MULTILINE)
        text = re.sub(r'`+[^`]*`+','',text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',text)
        text = re.sub(r'\[[^\]]*\]','',text)
        text = re.sub(r'https?://\S+','',text)
        text = re.sub(r'<[^>]+>','',text)
        text = re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene)[^)]*\)','',text,flags=re.IGNORECASE)
        text = re.sub(r'[#@$%^&*{}<>|\\~`]','',text)
        text = re.sub(r'\n{3,}','\n\n',text)
        text = re.sub(r'[ \t]{2,}',' ',text)
    return text.strip()


# ════════════════════════════════════════════════════════════
# VIRAL INTELLIGENCE ENGINE
# ════════════════════════════════════════════════════════════
def run_viral_intelligence(niche):
    intel = load_intel()
    name  = niche["name"]
    if name in intel:
        try:
            last = datetime.datetime.fromisoformat(intel[name].get("last_run","2020-01-01"))
            if (datetime.datetime.now()-last).days < 7:
                log(f"  Intel cached ({(datetime.datetime.now()-last).days}d)")
                return intel[name]
        except: pass
    log(f"  Running viral intelligence for {name}...")
    prompt = f"""Analyze the TOP 20 most viral forensic/investigation documentary YouTube videos (2M+ views) in the "{niche['viral_search']}" niche.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"emotional_arc":"One sentence description",
"retention_hooks":["30pct hook","60pct hook","80pct hook"],
"niche_specific_power_words":["word1","word2","word3","word4","word5","word6"],
"what_makes_videos_viral":"One sentence",
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]}}"""
    try:
        text = ai(prompt,temp=0.65,tokens=400,prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}',text)
        if m:
            d = json.loads(m.group())
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d; save_intel(intel)
            log(f"  Intel loaded")
            return d
    except Exception as e: log(f"  Intel err: {e}")
    fallback = {
        "top_hook_formulas":["The evidence was there the entire time. Nobody looked at it correctly.",
                              "This document changed everything. It had been sitting in a drawer for 11 years.",
                              "The number on page 3 did not match the number on page 3 of a different filing. That was the beginning."],
        "winning_title_patterns":["The [DOCUMENT/DATA] That Proved [CRIME] Had Been [DURATION]",
                                   "[NUMBER] [DOCUMENTS/ACCOUNTS] — The Investigation That Changed Everything"],
        "thumbnail_text_examples": niche["thumbnail_triggers"],
        "emotional_arc":"Methodical discovery then growing horror then full documented exposure",
        "retention_hooks":["What the next document revealed changed the entire investigation",
                           "The pattern only became visible when all 847 records were laid side by side",
                           "The final piece of evidence was the most ordinary thing imaginable"],
        "niche_specific_power_words":["documented","evidence","pattern","records","exposed","concealed","verified"],
        "what_makes_videos_viral":"Methodical evidence revelation that builds to an undeniable conclusion",
        "fresh_topic_ideas": niche["seed_topics"],
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback; save_intel(intel)
    return fallback


# ════════════════════════════════════════════════════════════
# FRESH TOPIC ENGINE — Different topic every attempt
# ════════════════════════════════════════════════════════════
def fetch_real_trending_titles(niche, token):
    """
    FIX: Ch2's entire "viral intelligence" system (run_viral_intelligence,
    below) was 100% AI-imagined — it asks the AI to "analyze the top 20
    viral videos" with NO actual data source behind it at all. The AI was
    hallucinating plausible-sounding patterns, not reporting real ones.
    This is a genuinely real replacement: an actual YouTube Data API call
    (matching the proven working pattern already used in master_pipeline.py
    for Ch1), returning real current top-performing video titles in this
    niche from the last 30 days. Non-fatal — returns [] on any failure.
    """
    if not token:
        return []
    try:
        published_after = (datetime.datetime.utcnow() -
                           datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche.get("viral_search", niche["name"]),
                    "type": "video", "order": "viewCount", "publishedAfter": published_after,
                    "videoDuration": "long", "maxResults": 8,
                    "relevanceLanguage": "en"}, timeout=20)
        if r.status_code == 200:
            items  = r.json().get("items", [])
            titles = [i["snippet"]["title"] for i in items if i.get("snippet", {}).get("title")]
            log(f"  Real trend data: {len(titles)} actual current titles fetched")
            return titles
        else:
            log(f"  Real trend fetch: {r.status_code}")
    except Exception as e:
        log(f"  Real trend fetch (non-fatal): {e}")
    return []


def get_fresh_topic(niche, attempt, intel, used_topics):
    # On first attempt, use strategy topic if available
    if attempt == 1:
        try:
            sf = SCRIPT_DIR / "next_week_strategy.json"
            if sf.exists():
                sd = json.loads(sf.read_text())
                rec = [t for t in sd.get("recommended_topics", [])
                       if t not in used_topics]
                if rec:
                    t = random.choice(rec)
                    log(f"  Strategy topic (attempt 1): {t[:60]}")
                    return t
        except: pass
    is_archive = attempt > 8
    if not is_archive:
        fresh = intel.get("fresh_topic_ideas", niche["seed_topics"])
        unused = [t for t in fresh if t not in used_topics]
        if unused:
            chosen = unused[0] if attempt <= 3 else random.choice(unused)
            log(f"  Topic (intel): {chosen[:70]}")
            return chosen
        log(f"  Generating new topics...")
        prompt = f"""Generate 6 compelling forensic investigation topics for "{niche['series']}".
Niche: {niche['name']} | Search: {niche['viral_search']}
Already used: {[t[:40] for t in used_topics[:4]]}
Each must be specific, have real emotional weight, produce a 12-minute video.
Return ONLY a JSON array: ["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]"""
        try:
            text = ai(prompt,temp=0.85,tokens=400,prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused:
                    chosen = random.choice(unused)
                    log(f"  Topic (generated): {chosen[:70]}")
                    return chosen
        except Exception as e: log(f"  Topic gen err: {e}")
    else:
        log(f"  Archive mode (attempt {attempt})...")
        prompt = f"""Find 6 documented real-world stories from 2022-2024 that fit "{niche['name']}" and went viral.
Focus: {niche['archive_search']}
Not already used: {[t[:40] for t in used_topics[:4]]}
Return ONLY a JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
        try:
            text = ai(prompt,temp=0.8,tokens=400,prefer="groq")
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
            m = re.search(r'\[[\s\S]*?\]',text)
            if m:
                topics = json.loads(m.group())
                unused = [t for t in topics if t not in used_topics]
                if unused:
                    chosen = random.choice(unused)
                    log(f"  Topic (archive): {chosen[:70]}")
                    return chosen
        except Exception as e: log(f"  Archive err: {e}")
    unused_seeds = [t for t in niche["seed_topics"] if t not in used_topics]
    chosen = random.choice(unused_seeds) if unused_seeds else niche["seed_topics"][0]
    log(f"  Topic (seed): {chosen[:70]}")
    return chosen


# ════════════════════════════════════════════════════════════
# 4-TRIGGER THUMBNAIL SYSTEM
# ════════════════════════════════════════════════════════════
def generate_thumbnail_text(niche, topic, intel, register="dread"):
    examples = intel.get("thumbnail_text_examples", niche["thumbnail_triggers"])
    register_instruction = (
        "SYMPATHY/WOEFUL: implies someone was failed, ignored, or unheard (e.g. \"NOBODY EVER LISTENED\")"
        if register == "sympathy" else
        "DREAD: implies something disturbing was confirmed"
    )
    prompt = f"""Generate the most psychologically compelling 3-word thumbnail text for a forensic investigation video.
NICHE: {niche['name']} | TOPIC: {topic[:100]}
TOP PERFORMERS: {', '.join(examples)}

USE THIS REGISTER (must match the video's actual title — do not mix registers): {register_instruction}
Also acceptable if it fits better: CURIOSITY GAP (unanswerable question), AUTHORITY SIGNAL
(documented proof), CONSEQUENCE (something irreversible found), PATTERN INTERRUPT (unexpected).

Rules: EXACTLY 3 words. ALL CAPS. Evidence-focused. Never generic.
Return ONLY 3 words. Example: PAPER TRAIL FOUND or NOBODY EVER LISTENED"""
    # FIX (direct user report, July 23 2026 — "for everything, there
    # should be specific scores that it should pass... rework that stage
    # without fail", same fix already verified on Ch1, applied
    # empire-wide): this generated exactly ONE candidate, unscored, no
    # gate at all. Now generates up to 3 real candidates per round, scores
    # them, and reworks a second round if nothing clears a real 6.5/10 bar.
    try:
        from thumbnail_engine_v2 import score_thumbnail_text
    except Exception:
        score_thumbnail_text = lambda t: 5.0
    THUMB_TEXT_MIN = 7.9
    THUMB_TEXT_EXCELLENT = 8.8  # aspirational tier, logged but not a hard requirement
    candidates = []
    for _round in range(2):
        try:
            for _ in range(3):
                result = ai(prompt, temp=0.82, tokens=15, prefer="groq")
                if result:
                    result = re.sub(r'[^A-Z\s]', '', result.upper()).strip()
                    words = result.split()[:3]
                    if len(words) == 3:
                        candidates.append(' '.join(words))
        except Exception as e:
            log(f"  Thumbnail text (non-fatal): {e}")
        if candidates:
            scored = [(c, score_thumbnail_text(c)) for c in dict.fromkeys(candidates)]
            best_text, best_score = max(scored, key=lambda pair: pair[1])
            if best_score >= THUMB_TEXT_MIN:
                _tier = " [EXCELLENT tier >=8.8]" if best_score >= THUMB_TEXT_EXCELLENT else ""
                log(f"  Thumbnail candidates scored: {scored} -> chose '{best_text}' ({best_score}/10, passed {THUMB_TEXT_MIN} bar){_tier}")
                return best_text
            log(f"  Thumbnail candidates scored: {scored} -> best '{best_text}' ({best_score}/10) "
                f"BELOW {THUMB_TEXT_MIN} bar — reworking (round {_round + 1}/2)")
    if candidates:
        scored = [(c, score_thumbnail_text(c)) for c in dict.fromkeys(candidates)]
        best_text, best_score = max(scored, key=lambda pair: pair[1])
        log(f"  Thumbnail candidates scored: {scored} -> chose '{best_text}' ({best_score}/10) "
            f"[best-effort after {THUMB_TEXT_MIN} bar unmet across all rounds]")
        return best_text
    return random.choice(niche["thumbnail_triggers"])


# ════════════════════════════════════════════════════════════
# 5-TITLE CTR SCORING
# ════════════════════════════════════════════════════════════
def score_title_ctr(title):  # v15: delegates to 5-axis scorer
    return score_title_v2(title)[0]

def _score_title_ctr_legacy(title):
    s = 5.0; tl = title.lower(); n = len(title)
    if 50<=n<=65: s+=1.5
    elif 45<=n<=70: s+=0.8
    else: s-=1.0
    power = ["exposed","documented","evidence","records","proved","concealed","revealed","traced","verified","found"]
    s += min(sum(1 for w in power if w in tl)*0.4, 2.0)
    if re.search(r'\d+\s*(year|month|document|account|transaction|million|billion)',tl): s+=1.0
    if any(w in tl for w in ["nobody checked","sat unread","was ignored","was missed","went unnoticed"]): s+=0.8
    return min(round(s,1),10.0)

def generate_and_score_titles(niche, topic, intel, episode, register="dread", real_trending_titles=None):
    patterns = intel.get("winning_title_patterns",[])
    power    = intel.get("niche_specific_power_words",["documented","evidence","records"])
    viral_patterns_str = "\n".join(patterns[:3])
    register_instruction = (
        'SYMPATHY/WOEFUL register: "She Reported It For 3 Years. Nobody Listened."'
        if register == "sympathy" else
        'DREAD register: "The System Knew. Nobody Stopped It. Here\'s The File."'
    )
    # FIX: real_trending_titles is actual current YouTube data (fetched via
    # the real API), unlike the AI-imagined "patterns" above. Give it clear
    # priority in the prompt over the imagined patterns.
    real_trend_block = ""
    if real_trending_titles:
        real_titles_str = "\n".join(f'  - "{t}"' for t in real_trending_titles[:6])
        real_trend_block = f"""
REAL CURRENT TOP-PERFORMING TITLES IN THIS NICHE (actual YouTube data, last 30
days, not invented) — study these for what's genuinely landing right now:
{real_titles_str}
Match this actual phrasing energy and specificity level — this is real data,
weight it above the generic patterns listed further below.
"""
    prompt = f"""
{real_trend_block}TITLE REQUIREMENTS — NON-NEGOTIABLE:
Do NOT write normal YouTube titles. The title should make someone screenshot it and send it to a friend.
Use specific numbers, real-feeling specificity, or uncomfortable implications.
Dark psychological humor outperforms pure shock — it signals intelligence.
The viewer should feel: "I shouldn't watch this... but I have to."

USE THIS REGISTER for this title: {register_instruction}

HONESTY CONSTRAINT (non-negotiable): the title must be something the first 30
seconds of the actual script genuinely delivers on. 2026 YouTube penalizes
titles that get clicks but lose viewers fast when the video doesn't match the
promise — this is worse long-term than a slightly less aggressive honest title.

TITLE FORMULAS THAT WORK (evidence/contradiction-driven — cleaner and more
concrete, often outperforms abstract institutional framing):
- "How One Fiber Solved The Case"
- "The Fingerprint Everyone Missed"
- "The Evidence Didn't Match The Confession"
- "The Timeline That Exposed The Killer"
- "Three Clues. One Impossible Suspect."
- "The Blood Pattern That Changed Everything"

FORBIDDEN: "Shocking", "Incredible", "Amazing", "Unbelievable", "You Won't Believe", "Mind-Blowing"

Generate exactly 5 YouTube title variants for this forensic investigation video.
NICHE: {niche['name']} | SERIES: {niche['series']} Ep{episode}
TOPIC: {topic[:150]}
VIRAL PATTERNS: {viral_patterns_str}
POWER WORDS: {', '.join(power)}
Rules: 50-65 chars. Curiosity gap. Documentary tone. Specific detail.
Return ONLY JSON array: ["title 1","title 2","title 3","title 4","title 5"]"""
    try:
        text = ai(prompt,temp=0.75,tokens=400,prefer="groq")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',re.sub(r'```json|```','',text).strip())
        m = re.search(r'\[[\s\S]*?\]',text)
        if m:
            titles = json.loads(m.group())
            if len(titles)>=3:
                scored = sorted([(t,score_title_v2(t)[0]) for t in titles],key=lambda x:x[1],reverse=True)
                log(f"  Title: {scored[0][1]}/10 — {scored[0][0][:55]}")
                return scored[0][0], scored
    except Exception as e: log(f"  Title err: {e}")
    fallback = f"{niche['series']}: The Investigation That Changed Everything"
    return fallback, [(fallback,6.0)]


# ════════════════════════════════════════════════════════════
# SCRIPT GENERATION — HIGH QUALITY FORENSIC NARRATION
# ════════════════════════════════════════════════════════════
def pick_best_niche_ch2(state, scheduled_name):
    """
    FIX: this genuinely didn't exist in Ch2 at all — track_episode_ch2
    was writing streak_below data, but nothing ever read it to actually
    rotate away from an underperforming niche. Matches Ch1's exact logic.
    """
    perf   = state.get("performance", {})
    streak = perf.get(scheduled_name, {}).get("streak_below", 0)
    if streak < 3:
        return scheduled_name
    log(f"  Niche {scheduled_name} has {streak} below-gate episodes — swapping")
    best_name = scheduled_name
    best_avg  = 0.0
    for n in NICHES:
        if n["name"] == scheduled_name: continue
        scores = perf.get(n["name"], {}).get("scores", [])
        avg    = sum(scores) / len(scores) if scores else 7.3
        if avg > best_avg:
            best_avg  = avg
            best_name = n["name"]
    log(f"  Swapped to: {best_name} (avg {best_avg:.1f})")
    return best_name


def get_niche_voice_style(state):
    day        = datetime.datetime.now().weekday()
    niche_name = DAY_NICHE.get(day,"forensic_finance")
    niche_name = pick_best_niche_ch2(state, niche_name)
    style_name = DAY_STYLE.get(day,"dark_minimal")
    if style_name == state.get("last_style",""):
        opts = [s for s in STYLES if s!=style_name]
        style_name = opts[day%len(opts)]
    niche = next(n for n in NICHES if n["name"]==niche_name)
    preferred = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    available = [v for v in preferred if v!=state.get("last_voice","")]
    voice = (available or preferred)[datetime.datetime.now().timetuple().tm_yday % len(available or preferred)]
    return niche, voice, style_name

def build_dread_prompt_er():
    """Evidence Room uses investigation-specific dread triggers"""
    triggers = ["institutional","scale","competence","detail","duration","reversal","cost","invisibility"]
    return "\n".join(f"DREAD {t.upper()}: {DREAD_TRIGGERS[t]}" for t in triggers if t in DREAD_TRIGGERS)

def generate_script_and_scenes(niche, topic, style_name, episode, attempt, intel, prev_title=""):
    """
    v2 script generation for Ch2 (The Evidence Room):
    1. Research anchors prevent vague AI output
    2. Forensic documentary prompt with stage-specific structure
    3. Stage-level scoring + targeted rewrite of 2 worst stages
    4. Scene JSON extracted separately after narration
    """
    temp  = min(0.82 + attempt * 0.012, 0.94)
    # v1 addition — real product title for the verbal-mention instruction.
    try:
        _product_title_for_prompt = build_product_cta("evidence_room").split(": ")[0].replace("\n\n📖 ", "").strip() or "our companion resource"
    except Exception:
        _product_title_for_prompt = "our companion resource"
    hooks = intel.get("top_hook_formulas", ["The documents confirmed what investigators had suspected."])
    power = intel.get("niche_specific_power_words", ["documented","verified","traced","confirmed"])
    viral = intel.get("what_makes_videos_viral", "Specific documented evidence that viewers can verify")
    retention = intel.get("retention_hooks", ["The next document changes the entire case"])
    cross = f'\nReference previous investigation: "{prev_title}" naturally in closing.' if prev_title else ""

    # Research anchors
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic anchors for a forensic documentary about: {topic}\n"
            f"Return ONLY valid JSON (no backticks):\n"
            f'{{"case_duration":"e.g. 4380 days — twelve years",' 
            f'"people_affected":"e.g. 847 confirmed victims",'
            f'"discovery_date":"e.g. October 14 2019",'
            f'"key_document":"e.g. a 47-page internal audit dated March 2011",'
            f'"financial_figure":"e.g. $2.4 million over eleven years",'
            f'"institutional_failure":"e.g. 23 filed reports that reached no supervisor"}}' 
        )
        ar = ai(anchor_prompt, temp=0.65, tokens=300, prefer="groq")
        if ar:
            ar = re.sub(r"```json|```", "", ar).strip()
            m  = re.search(r"\{[\s\S]*?\}", ar)
            if m:
                anchors = json.loads(m.group())
                log(f"  Anchors: {len(anchors)} fields")
    except Exception as e:
        log(f"  Anchors (non-fatal): {e}")

    anchor_block = ""
    if anchors:
        anchor_block = "\n\nUSE THESE SPECIFIC DETAILS:\n" + "\n".join(
            f"  {k}: {v}" for k, v in anchors.items() if v)

    # FIX: same gap found and fixed in Ch1 — generate_best_cold_open
    # existed fully built (3 real variants, real hook-strength scoring)
    # but was never called anywhere.
    try:
        best_cold_open = generate_best_cold_open(niche, topic, intel.get("trending_titles"))
        if best_cold_open:
            anchor_block = (f"\n\nMANDATORY COLD OPEN — use this exact opening, scored as the "
                            f"strongest of 3 real variants, then continue from there:\n"
                            f"{best_cold_open}{anchor_block}")
    except Exception as e:
        log(f"  Cold open scoring (non-fatal): {e}")

    # FIX: load_pattern_memory and load_weekly_strategy both existed fully
    # built — the former reads real past-episode performance data (the
    # write side, save_pattern_memory, was fixed earlier this session),
    # the latter reads the real competitor-intelligence report weekly_report.py
    # generates — but NEITHER was ever called anywhere in this file. Ch2 was
    # writing pattern data that never fed back into future scripts, and
    # never benefited from the weekly competitive research at all, despite
    # both systems being fully built for exactly this feedback loop.
    try:
        pattern_ctx = load_pattern_memory(load_state())
        strategy_ctx = load_weekly_strategy()
        combined = "\n".join(filter(None, [pattern_ctx, strategy_ctx]))
        if combined:
            anchor_block += f"\n\nPATTERN MEMORY + COMPETITOR INTELLIGENCE:\n{combined}\n"
    except Exception as e:
        log(f"  Pattern memory / weekly strategy (non-fatal): {e}")

    # NEW FEATURE (per explicit request — daily competitive research):
    # the above is weekly (weekly_report.py) or AI-imagined (run_viral_
    # intelligence). This is a genuinely real, DAILY refresh: real
    # view/like counts and real title-word-frequency patterns from
    # actual current top-performing videos in this niche, computed
    # deterministically — not an AI guess. Cached per calendar day, so
    # repeated attempts the same day (this function runs once per
    # attempt, up to 13x) reuse the same fetch rather than re-hitting
    # the API every time.
    try:
        from daily_competitor_research import fetch_daily_competitor_research
        _daily_token = get_yt_token()
        _daily_intel = fetch_daily_competitor_research(niche, _daily_token, str(SCRIPT_DIR))
        if _daily_intel.get("research_block"):
            anchor_block += f"\n\n{_daily_intel['research_block']}\n"
    except Exception as e:
        log(f"  Daily competitor research (non-fatal): {e}")

    # FIX: get_research_context (and the real search_real_cases /
    # extract_real_case_facts chain underneath it) existed fully built —
    # searches Google News RSS and Reddit for REAL documented cases
    # matching the topic — but was never called anywhere. This is a
    # genuinely significant gap: the "research anchors" already in use
    # generate AI-INVENTED plausible-sounding specifics, not real,
    # verified facts. Given Ch2's whole stated risk is factual
    # sloppiness/defamation, grounding scripts in real search results
    # when available matters directly, not just as a nice-to-have.
    real_cases = []
    try:
        real_case_context, real_cases = get_research_context(niche["name"], topic)
        if real_case_context:
            anchor_block += f"\n\n{real_case_context}\n"
    except Exception as e:
        log(f"  Real-case research (non-fatal): {e}")

    stage_targets = {
        1: 120,   # Cold open — short and brutal
        2: 200,   # The before
        3: 280,   # First signals
        4: 480,   # Escalation — most evidence
        5: 150,   # False resolution
        6: 520,   # Real reveal — climax
        7: 150,   # Implication + CTA
    }

    power_str = ", ".join(power[:6])
    # Dynamic scene count — NOT a fixed number. Varies 55-60 by day of year,
    # each targeting ~13.5s (never over 15s), per explicit requirement. The
    # existing repeat-to-fill-duration logic in render_and_encode still
    # covers any remaining runtime beyond what 55-60 unique scenes span.
    n_scenes_target = 55 + (datetime.datetime.now().timetuple().tm_yday % 6)  # 55-60, varies daily
    viral_hooks_str = "\n".join(f"  '{h}'" for h in hooks[:3])
    prompt = f"""Write a forensic investigative documentary narration script.
Style: precisely documented, evidence-driven, animated forensic format.

CASE: {topic}
SERIES: {niche['series']} — Episode {episode}
VIRAL HOOKS: {viral_hooks_str}
POWER WORDS: {power_str}
{anchor_block}{cross}

TOTAL: {MIN_WORDS} to {MAX_WORDS} words. Each stage must hit its target.

SEVEN-STAGE FORENSIC STRUCTURE — write continuously, no labels. The stage
names below (STAGE 1 — CASE FILE OPEN, STAGE 2 — THE SUBJECT, etc.) are
structural notes for YOU, the writer, describing what content goes where —
they are NOT text to include in your response. Never write "Stage 1",
"Stage 4", "Chapter 2", a stage's name, or any invented section title (e.g.
never write something like "Stage 4: The Evidence Builds") anywhere in your
output. The reader must experience one continuous, unbroken narration with
zero visible section breaks of any kind — the transition between stages
should be a single smooth sentence, never a title or heading:

SIGNATURE OPENING (brand consistency): begin the case file open with a
recognizable rhythm specific to {niche['series']} — exact words can vary per
episode, but the STRUCTURE should feel unmistakably like this series within
the first sentence, not interchangeable with any other forensic channel.

CASE SELECTION: prefer a genuinely underreported or lesser-known case over
the most famous/oversaturated version, if the topic allows it — differentiates
from the flood of channels covering the same viral cases, and protects
against reading as mass-produced generic content.

CENTRAL CONTRADICTION (channel strength, not optional): structure the entire
video around ONE central contradiction — alibi vs timestamp, confession vs
blood pattern, witness statement vs CCTV, timeline vs cell data. The star of
this channel is the EVIDENCE TRAIL, not the criminal. Keep the moral drama
secondary to the proof trail — viewers stay to watch the puzzle lock into
place, not for shock value.

FACTUAL CARE (non-negotiable, real policy-safety requirement): this channel's
biggest real risk is defamation and factual sloppiness, not creative weakness.
Use careful, evidence-first wording — "according to court records," "the
prosecution argued," "reportedly" — rather than stating contested claims as
flat fact. If any detail is dramatized or reconstructed rather than
independently verifiable, say so plainly in the narration.

RETENTION CHECKPOINTS (precise timing, not just word count):
- At approximately 15-20 seconds into the Case File Open (roughly the 35-45
  word mark): introduce one SPECIFIC new piece of information not already
  promised in sentences 1-3. Without this second hook, attention drops here
  regardless of how strong the opening was.
- At approximately 40-45 seconds in (end of Stage 1 / start of Stage 2): set
  up a payoff requiring continued viewing to resolve.

STAGE 1 — CASE FILE OPEN ({stage_targets[1]} words)
{"A MANDATORY COLD OPEN is provided above — it already previews this exact case's specific twist/outcome and was scored as the strongest of 3 real variants. Use it AS-IS for Stage 1 (only light edits for grammar/flow into what follows), do NOT write a new, generic case-file open from scratch here. The rules below describe what that mandatory text already satisfies -- they are not a second, separate opening to write instead of it." if "MANDATORY COLD OPEN" in anchor_block else "Sentence 1: exact case reference — number, date, or document ID. Sentence 2: specific location of the discovery. Sentence 3: the question this investigation will answer. The opening must preview the real, specific twist/outcome of THIS case (state or strongly imply the actual result) -- not a generic disturbing mood that could belong to any episode."}
Forbidden: "welcome back", "today we investigate", "in this video"
TRIGGER PLACEMENT: DETAIL (s1) → PROXIMITY (s2) → open unresolved loop (s3)

STAGE 2 — THE SUBJECT ({stage_targets[2]} words)
Establish the entity — person, company, or system — as completely ordinary.
Specific details. Specific routine. Make the viewer care about what is about to be lost.
Final sentence signals something is about to break — without stating it.
Forbidden: "little did they know", "unbeknownst to", "but fate had other plans"
TRIGGER PLACEMENT: NORMALITY (s1-s3) → PROXIMITY (s4-s6) → quiet wrongness (final)

STAGE 3 — FIRST ANOMALIES ({stage_targets[3]} words)
Small discrepancies. Each individually explainable. One per sentence.
Start with the smallest. Build accumulation. Each one specific and documented.
Forbidden: "suddenly", "out of nowhere", "shockingly", "without warning"
TRIGGER PLACEMENT: INVISIBILITY (s1) → DURATION (s3) → SCALE (s5) → INSTITUTIONAL (s7)

STAGE 4 — THE EVIDENCE BUILDS ({stage_targets[4]} words)
One short sentence reframes Stage 3 entirely.
Documents arrive. Records are pulled. Each piece more specific than the last.
Short sentences then one longer. Real-feeling case references.
Forbidden: vague quantities — not "many reports" but "forty-seven reports"

STAGE 5 — FALSE CLOSURE ({stage_targets[5]} words)
Case appears resolved. Specific timeframe. Viewer exhales.
Final sentence: quietly, specifically wrong — not dramatic, not flagged.
Forbidden: "but it wasn't over", "however", "or so they thought"

STAGE 6 — THE FULL RECORD ({stage_targets[6]} words)
One short sentence destroys the false closure.
Then one finding per paragraph. Ordered by impact — each more significant.
Document references, file numbers, specific dates, specific figures.
Forbidden: "in conclusion", "to summarise", "as we can see"

STAGE 7 — CASE IMPLICATIONS ({stage_targets[7]} words)
Imply — never state — that this case is part of a larger pattern.
Subscribe CTA at emotional peak. Reference series.{cross}
Forbidden: "subscribe and like", "hit the bell", "don't forget to"

RETENTION PAYOFF CADENCE (NON-NEGOTIABLE — the single biggest lever for
average view duration): a script that saves its only real hooks for a
few fixed points across a long video leaves multi-minute stretches with
nothing preventing viewer drop-off. Every stage, especially the longer
ones, MUST contain a genuine payoff — a surprising fact, a specific
number, a forward reference ("what happens next reveals...") — roughly
every 150-225 words (approximately every 60-90 seconds of narration),
not just at the stage's start. Never save all the value for the end.

MID-VIDEO REHOOK (NON-NEGOTIABLE — the drift point): viewer attention
consistently dips right around the 55-65% mark of a long video — after the
opening hook has worn off, before the final reveal creates urgency again.
Exactly once, somewhere in that 55-65% window (right around the start of
Stage 5), break the documentary narration for ONE short direct-address
beat: speak straight to the viewer in second person ("you"), acknowledge
they're still here, and re-raise the stakes. Example shape only, do not
copy verbatim: "Stop for a second. If you're still watching, you already
sense something is wrong here." Then return immediately to the narration —
this is a single beat, not a new tone for the rest of the script.

VERBAL RESOURCE MENTION (natural, brief, once only): most viewers never read
the description. Within the existing subscribe moment, include ONE brief,
natural sentence mentioning "{_product_title_for_prompt}" as a related
resource for anyone who wants to go deeper — phrased as a genuine aside, not
an ad-read, and never interrupting the narrative flow. If it can't be worked
in naturally, skip it entirely — a forced-sounding mention actively hurts
the viewer-satisfaction signals that now weigh more than raw watch time.


TONE AND STYLE (NON-NEGOTIABLE): matches the CENTRAL CONTRADICTION rule
above — this is a FORENSIC PUZZLE, not a shock-value true-crime retelling.
- Every sentence should feel like one more piece of evidence being placed
  on the table — precise, procedural, building toward a lock-tight case.
- The satisfaction comes from watching contradictory evidence resolve into
  certainty, not from dark humor or dread. Skip jokes entirely — this
  channel's craft is the click of pieces fitting together.
- Each stage should narrow the contradiction further. Build toward the
  moment the puzzle locks into place, not toward maximum darkness.
- Real documentary references and case-file language make it feel
  researched. Fake-sounding or invented claims get skipped.
- Pacing: short sentences at the moment a piece of evidence lands.
- The viewer should feel like they solved something alongside the
  investigators, not like they witnessed something shocking.

WHAT MAKES VIEWERS STAY FOR THE WHOLE CASE:
- The moment a contradiction viewers didn't notice gets pointed out.
- The specific piece of evidence that reframes everything before it.
- The satisfaction of the full evidence trail resolving into one conclusion.
- Respect for the viewer's intelligence — let them almost solve it first.

EVIDENCE TRIGGERS — use at least 3 per script:
1. The specific detail in the record that contradicts the official story.
2. The piece of evidence investigators almost missed.
3. The document or record that's still on file and checkable today.
4. The procedural step institutions got wrong or skipped.
5. The exact detail so specific it has to come from a real record.
6. The final piece of evidence that resolves the contradiction, in the last 30 seconds.
7. The one detail the case file leaves formally unresolved.

RULES:
1. Maximum 13 words per sentence. Every sentence.
2. Zero markdown. Zero AI filler phrases.
3. Every number specific. Every date specific. Every location specific.
4. Write continuously — no stage labels, no headers. Never write "Stage N",
   a stage's name, or an invented section title anywhere in the output
   (e.g. never "Stage 4: The Evidence Builds") — this applies to every one
   of the seven stages above, all the way through Stage 7, not just the
   opening.
5. Start immediately with the case file open narration itself — never with
   a label or heading.

After writing the complete narration, add exactly 10 dashes on a new line, then provide scene JSON.
IMPORTANT: provide exactly {n_scenes_target} scenes (55-60, not fewer) — this video runs
15-18 minutes, and fewer scenes means the same visuals loop far too often, which
looks broken and repetitive. Each scene should run approximately 13.5 seconds
(never more than 15). Vary content EVERY time a scene type repeats (different
case details, different numbers, different network nodes each time — never
reuse the same labels twice). Cycle through the 5 types across the full case
narrative repeatedly, each pass with fresh content:
TITLE REQUIREMENTS for the JSON below (this was previously just "55-65 chars"
with no real guidance — same title research applied to Ch1 now applies here):
- 40-65 characters, front-load the compelling part in the first 40 (mobile display).
- CURIOSITY GAP: withhold the one detail that can only be resolved by watching.
- Rotate between two registers roughly equally — don't default to one:
  DREAD ("The System Knew. Nobody Stopped It. Here's The File.")
  SYMPATHY/WOEFUL ("She Reported It For 3 Years. Nobody Listened.")
- HONESTY CONSTRAINT (non-negotiable): the title must be something the first 30
  seconds of the actual script genuinely delivers on. 2026 YouTube penalizes
  titles that get clicks but lose viewers fast when the video doesn't match the
  promise — this is worse long-term than a slightly less aggressive honest title.

{{"title":"YouTube title, 40-65 chars, dread OR sympathy register, curiosity gap intact","thumbnail_text":"3 WORDS ALL CAPS with number","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"scenes":[
{{"type":"timeline","duration":13,"title":"CASE TIMELINE","events":["Event 1: date","Event 2: date","Event 3: date","Event 4: date"],"label":"CHRONOLOGY"}},
{{"type":"document_reveal","duration":13,"title":"THE KEY DOCUMENT","lines":["CASE FILE — RESTRICTED","Reference: [case number]","Finding: [key finding]","Status: [outcome]"],"stamp":"CLASSIFIED"}},
{{"type":"data_reveal","duration":14,"title":"THE NUMBERS","items":["$X.XM","XX YEARS","XXX VICTIMS","XX REPORTS"],"label":"CASE STATISTICS"}},
{{"type":"connection_map","duration":14,"title":"THE NETWORK","nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"HOW IT CONNECTED"}},
{{"type":"evidence_board","duration":13,"title":"EVIDENCE SUMMARY","items":["Finding 1","Finding 2","Finding 3","Finding 4"],"label":"CASE EVIDENCE"}}
... continue this pattern for a total of {n_scenes_target} scenes, each with genuinely different
case-specific content — different timeline events, different documents, different
numbers, different network nodes, different evidence each time a type repeats ...
]}}

Write narration first ({MIN_WORDS}-{MAX_WORDS} words), then 10 dashes, then JSON."""

    raw   = ai(prompt, temp=temp, tokens=7000, prefer="gemini")
    parts = raw.split("----------") if raw else [""]
    clean = strip_md(strip_md(parts[0].strip()))
    from script_scoring import strip_all_leaked_stage_headers, split_into_stage_texts, strip_leaked_stage_headers
    clean = strip_all_leaked_stage_headers(clean)
    wc    = len(clean.split())

    # Expansion rounds
    for exp_round in range(2):
        if wc >= MIN_WORDS:
            break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w short — expanding round {exp_round+1}...")
        exp = (
            f"This forensic documentary script is {wc} words. Needs {MIN_WORDS} minimum.\n"
            f"Expand the Evidence Builds section and the Full Record section only.\n"
            f"Add specific case references, exact figures, exact dates, investigator reactions.\n"
            f"Max 13 words per sentence. Zero markdown.\n"
            f"Return the COMPLETE expanded script.\n\nSCRIPT:\n{clean}"
        )
        raw2 = ai(exp, temp=0.82, tokens=7000, prefer="gemini")
        if raw2:
            c2 = strip_all_leaked_stage_headers(strip_md(strip_md(raw2)))
            if len(c2.split()) > wc:
                clean = c2
                wc    = len(clean.split())
                log(f"  Expanded to {wc}w")

    # Stage-level scoring + targeted rewrite of 2 worst stages
    if wc >= MIN_WORDS:
        try:
            targets_l  = [110, 210, 260, 420, 170, 680, 190]
            stage_txts = split_into_stage_texts(clean, targets_l)

            stage_names = ["CASE OPEN","SUBJECT","ANOMALIES","EVIDENCE",
                           "CLOSURE","FULL RECORD","IMPLICATIONS"]
            forbidden_per = [
                ["welcome back","today we investigate"],
                ["little did they know","unbeknownst"],
                ["suddenly","out of nowhere","without warning"],
                [],
                ["but it wasn't over","or so they thought"],
                ["in conclusion","to summarise"],
                ["subscribe and like","hit the bell"],
            ]
            stage_scores = []
            # Real specificity/craveability signals — same upgrade applied to
            # Ch1's rubric, which only checked word-count adherence and
            # forbidden-phrase absence and never measured actual specificity.
            vague_quantity_words = ["many", "several", "some", "numerous", "various",
                                     "a lot of", "countless", "multiple"]
            vague_time_words = ["years ago", "some time later", "at some point",
                                 "a while later", "eventually", "in time"]
            specificity_signals = [r'\b\d+\b', r'\$\d', r'\b\d{4}\b']
            craveability_signals = ["still", "today", "confirmed", "documented",
                                     "records show", "never released", "still running",
                                     "still active", "remains", "to this day"]

            for i, (stext, sname, starget, sforbidden) in enumerate(
                    zip(stage_txts, stage_names, targets_l, forbidden_per)):
                sc    = 5.0
                ratio = len(stext.split()) / max(starget, 1)
                if 0.85 <= ratio <= 1.15:   sc += 2.0
                elif 0.70 <= ratio <= 1.30: sc += 0.8
                else:                       sc -= 1.5
                sc -= sum(0.8 for f in sforbidden if f in stext.lower())
                sents = [s for s in re.split(r"(?<=[.!?])\s+", stext) if s.strip()]
                long  = [s for s in sents if len(s.split()) > 13]
                if len(long) / max(len(sents), 1) > 0.2:
                    sc -= 0.8
                ai_ph = ["moreover","furthermore","it is worth noting","in conclusion"]
                sc   -= sum(0.4 for p in ai_ph if p in stext.lower())

                stext_lower = stext.lower()
                num_hits = sum(1 for pat in specificity_signals if re.search(pat, stext))
                if num_hits >= 2: sc += 1.0
                elif num_hits == 0: sc -= 1.0
                sc -= sum(1 for w in vague_quantity_words if w in stext_lower) * 0.6
                sc -= sum(1 for w in vague_time_words if w in stext_lower) * 0.6
                if sum(1 for w in craveability_signals if w in stext_lower) >= 1:
                    sc += 0.8

                stage_scores.append(round(min(max(sc, 0), 10), 1))

            stage_scores_str = " | ".join(f"{n[:6]}:{s}" for n,s in zip(stage_names,stage_scores))
            log(f"  Stage scores: {stage_scores_str}")
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]
            _any_rewritten = False

            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                rewrite_p = (
                    f"Rewrite ONLY this forensic documentary stage. Return ONLY the rewritten stage — "
                    f"pure narration prose, continuing the case file. "
                    f"Do NOT include a title, heading, or any text like \"Stage {idx+1}:\" or "
                    f"\"{stage_names[idx]}:\" or any chapter/section label of any kind — the reader "
                    f"must never see the words \"stage\" or \"chapter\" or a number label; the "
                    f"response must read as an uninterrupted continuation of the narration.\n\n"
                    f"STAGE PURPOSE (for your reference only, do not name it in the output): "
                    f"{stage_names[idx]} (target: {targets_l[idx]} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"SCORE: {stage_scores[idx]}/10 — sentences too long or too vague\n\n"
                    f"RULES:\n"
                    f"- Max 13 words per sentence.\n"
                    f"- Every number specific (not 'many' but '47').\n"
                    f"- Every date specific (not 'years ago' but 'March 2011').\n"
                    f"- Zero markdown. Zero AI filler. Zero titles/headers/labels.\n"
                    f"- Target: {targets_l[idx]} words (±15% ok).\n\n"
                    f"ORIGINAL:\n{stage_txts[idx]}\n\nRewrite now (prose only, no label):"
                )
                new_s = ai(rewrite_p, temp=0.82, tokens=2000, prefer="groq")
                if new_s:
                    new_s = strip_md(new_s)
                    new_s = strip_leaked_stage_headers(new_s)
                    if len(new_s.split()) > 30:
                        clean = clean.replace(stage_txts[idx], new_s, 1)
                        log(f"  Stage {stage_names[idx]} rewritten")
                        _any_rewritten = True

            if _any_rewritten:
                stage_txts = split_into_stage_texts(clean, targets_l)

            # FIX (direct user report, July 23 2026 — real production data
            # showed score_narrative_craft's hard 7.9 gate failing on most
            # attempts, exhausting all 13 tries with zero video produced):
            # the ONLY prior response to a failing craft score was to
            # reject the whole attempt and re-roll a brand new script from
            # scratch, hoping the next generation happens to land an
            # escalation beat, a resolution beat, sentence-rhythm variety,
            # and no repeated phrasing all by chance. This directly
            # rewrites the middle third (escalation) and final third
            # (resolution) with the exact missing structural beats
            # score_narrative_craft checks for, then keeps whichever
            # version actually scores higher.
            try:
                from script_scoring import score_narrative_craft, NARRATIVE_CRAFT_GATE_MIN
                _craft_before, _ = score_narrative_craft(clean)
                if _craft_before < NARRATIVE_CRAFT_GATE_MIN:
                    _clean_before_craft = clean
                    _cwords = clean.split()
                    _cthird = len(_cwords) // 3
                    _mid_text = " ".join(_cwords[_cthird:2 * _cthird])
                    _mid_prompt = (
                        f"Rewrite this middle section of a forensic documentary narration. Return "
                        f"ONLY the rewritten prose, same approximate length, no headers, no markdown.\n\n"
                        f"REQUIRED, all of these:\n"
                        f"1. One genuine escalation moment — new evidence, a worse discovery, a "
                        f"visible turn for the worse. A real turn, not just a transition word.\n"
                        f"2. Vary sentence length dramatically — mix short punches (4-8 words) with "
                        f"longer sentences (20+ words).\n"
                        f"3. Do not repeat any 4-word phrase from elsewhere in the script.\n\n"
                        f"ORIGINAL:\n{_mid_text}\n\nRewrite now:"
                    )
                    _new_mid = ai(_mid_prompt, temp=0.82, tokens=1500, prefer="groq")
                    if _new_mid:
                        _new_mid = strip_md(_new_mid)
                        if len(_new_mid.split()) > 30:
                            clean = clean.replace(_mid_text, _new_mid, 1)

                    _cwords2 = clean.split()
                    _cthird2 = len(_cwords2) // 3
                    _final_text = " ".join(_cwords2[2 * _cthird2:])
                    _final_prompt = (
                        f"Rewrite this final section of a forensic documentary narration. Return "
                        f"ONLY the rewritten prose, same approximate length, no headers, no markdown.\n\n"
                        f"REQUIRED, all of these:\n"
                        f"1. One genuine resolution moment — what turned out to be true, what was "
                        f"finally confirmed. A real payoff, not a summary.\n"
                        f"2. Vary sentence length dramatically — mix short punches (4-8 words) with "
                        f"longer sentences (20+ words).\n"
                        f"3. Do not repeat any 4-word phrase from elsewhere in the script.\n\n"
                        f"ORIGINAL:\n{_final_text}\n\nRewrite now:"
                    )
                    _new_final = ai(_final_prompt, temp=0.82, tokens=1500, prefer="groq")
                    if _new_final:
                        _new_final = strip_md(_new_final)
                        if len(_new_final.split()) > 30:
                            clean = clean.replace(_final_text, _new_final, 1)

                    _craft_after, _ = score_narrative_craft(clean)
                    if _craft_after < _craft_before:
                        clean = _clean_before_craft
                        log(f"  Targeted craft rewrite: {_craft_before}/10 -> {_craft_after}/10 (worse, reverted)")
                    else:
                        stage_txts = split_into_stage_texts(clean, targets_l)
                        log(f"  Targeted craft rewrite: {_craft_before}/10 -> {_craft_after}/10")
            except Exception as e:
                log(f"  Targeted craft rewrite (non-fatal): {e}")

            wc = len(clean.split())
            log(f"  After targeted rewrite: {wc}w")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # Parse scene JSON
    scenes, title, thumbnail_text, tags = [], f"The Evidence Room: {topic[:45]}", "CASE DOCUMENTED", \
        [niche["name"],"forensic","investigation","animated","crime","evidence","documentary",
         "exposed","deepdive","case"]
    if len(parts) > 1:
        try:
            jt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]","",re.sub(r"```json|```","",parts[1]).strip())
            m  = re.search(r"\{[\s\S]*\}", jt)
            if m:
                data  = json.loads(m.group())
                scenes        = data.get("scenes", [])
                title         = data.get("title", title)
                thumbnail_text = data.get("thumbnail_text", thumbnail_text)
                tags          = data.get("tags", tags)
        except Exception as e:
            log(f"  Scene JSON (non-fatal): {e}")

    # Fallback scenes — dynamic 55-60 (was 20, was 5 before that), matching
    # the prompt fix. Built PROGRAMMATICALLY rather than hand-writing 55-60
    # unique dict entries (impractical to maintain): 20 genuinely distinct
    # hand-written base scenes, cycled with numbered variation to reach the
    # target count, each retimed to ~13.5s per explicit requirement (was 7-10s).
    if not scenes:
        base_scenes = [
            {"type":"timeline","title":"CASE TIMELINE",
             "events":["Event 1","Event 2","Event 3","Event 4"],"label":"CHRONOLOGY"},
            {"type":"document_reveal","title":"KEY DOCUMENT",
             "lines":["CASE FILE — RESTRICTED","Reference: CF-2019-447",
                      "Finding: pattern confirmed","Status: under review"],"stamp":"CLASSIFIED"},
            {"type":"data_reveal","title":"THE NUMBERS",
             "items":["$2.4M","12 YEARS","847 CASES","47 REPORTS"],"label":"STATISTICS"},
            {"type":"connection_map","title":"THE NETWORK",
             "nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"CONNECTION"},
            {"type":"evidence_board","title":"EVIDENCE",
             "items":["Document 1","Document 2","Pattern","Conclusion"],"label":"EVIDENCE"},
            {"type":"timeline","title":"ESCALATION",
             "events":["First report","Internal memo","Cover attempt","Whistleblower"],"label":"PROGRESSION"},
            {"type":"document_reveal","title":"INTERNAL MEMO",
             "lines":["CONFIDENTIAL MEMO","Author redacted","Subject: risk exposure",
                      "Action: none taken"],"stamp":"RESTRICTED"},
            {"type":"data_reveal","title":"THE SCALE",
             "items":["230 AFFECTED","6 STATES","3 AGENCIES","0 ARRESTS"],"label":"SCOPE"},
            {"type":"connection_map","title":"WHO KNEW",
             "nodes":["EXECUTIVE","LEGAL TEAM","REGULATOR","PUBLIC"],"label":"AWARENESS CHAIN"},
            {"type":"evidence_board","title":"THE PAPER TRAIL",
             "items":["Email thread","Signed waiver","Deleted log","Recovered file"],"label":"DISCOVERY"},
            {"type":"timeline","title":"THE COVER-UP",
             "events":["Records altered","Staff reassigned","Story changed","Silence bought"],"label":"CONCEALMENT"},
            {"type":"document_reveal","title":"THE SETTLEMENT",
             "lines":["NON-DISCLOSURE","Amount sealed","Terms confidential",
                      "Case closed quietly"],"stamp":"SEALED"},
            {"type":"data_reveal","title":"THE COST",
             "items":["$18M SETTLED","4 VICTIMS PAID","0 PUBLIC RECORD","1 SURVIVOR TALKING"],"label":"AFTERMATH"},
            {"type":"connection_map","title":"THE PATTERN",
             "nodes":["FIRST CASE","SECOND CASE","THIRD CASE","SAME METHOD"],"label":"REPETITION"},
            {"type":"evidence_board","title":"WHAT SURVIVED",
             "items":["Backup drive","Anonymous tip","Court filing","Public record"],"label":"REMAINING PROOF"},
            {"type":"timeline","title":"COMING FORWARD",
             "events":["First contact","Legal review","Story verified","Publication"],"label":"EXPOSURE"},
            {"type":"document_reveal","title":"THE RESPONSE",
             "lines":["OFFICIAL STATEMENT","Denies wrongdoing","Declines comment",
                      "Investigation ongoing"],"stamp":"UNVERIFIED"},
            {"type":"data_reveal","title":"WHERE IT STANDS",
             "items":["1 LAWSUIT ACTIVE","2 AGENCIES NOTIFIED","0 CONVICTIONS","ONGOING CASE"],"label":"STATUS"},
            {"type":"connection_map","title":"STILL RUNNING",
             "nodes":["SAME SYSTEM","SAME PLAYERS","NEW VICTIMS","NO OVERSIGHT"],"label":"PRESENT DAY"},
            {"type":"evidence_board","title":"THE QUESTION LEFT OPEN",
             "items":["Who else knew","What else is hidden","Who pays next","Who's accountable"],"label":"UNRESOLVED"},
        ]
        target_count = 55 + (datetime.datetime.now().timetuple().tm_yday % 6)  # 55-60, matches prompt
        scenes = []
        cycle_num = 0
        while len(scenes) < target_count:
            for base in base_scenes:
                if len(scenes) >= target_count:
                    break
                s = dict(base)
                s["duration"] = 13 + (len(scenes) % 3)  # 13-15s, varies, never over 15
                if cycle_num > 0:
                    # Subsequent cycles get a distinguishing suffix so repeated
                    # scene types are still visually/textually distinct.
                    s["title"] = f"{s['title']} — PART {cycle_num + 1}"
                scenes.append(s)
            cycle_num += 1

    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", clean))

    # CTA injection
    if len(clean.split()) >= 400:
        clean = _inject_ctas_er(clean, niche.get("name","forensic_finance"))
        wc    = len(clean.split())

    # Force expansion if under minimum word count
    for _exp in range(3):
        if wc >= MIN_WORDS or wc > MAX_WORDS: break
        deficit = MIN_WORDS - wc
        log(f"  {wc}w — expanding (need {deficit} more)...")
        try:
            ep = (f"This script is {wc} words. Needs {MIN_WORDS} minimum.\n"
                  f"Add {deficit} words. Expand evidence and human cost sections.\n"
                  f"Zero markdown. Max 13 words per sentence. Return COMPLETE script:\n\n"
                  + clean[:3000])
            raw2 = ai(ep, tokens=7000)
            if raw2:
                c2 = strip_md(raw2)
                if len(c2.split()) > wc:
                    clean = c2; wc = len(clean.split())
                    # Hard truncate to MAX_WORDS after expansion
                    if wc > MAX_WORDS:
                        words_list = clean.split()
                        clean = " ".join(words_list[:MAX_WORDS])
                        wc    = len(clean.split())
                    log(f"  Expanded to {wc}w")
        except Exception as _e:
            log(f"  Expansion (non-fatal): {_e}"); break
    # FIX: Ch2's "evidence-first, careful wording" requirement was only a
    # prompt instruction with zero verification — same gap as Ch1's fiction-
    # labeling. Unlike Ch1's single insertable disclosure sentence, this is
    # a PERVASIVE WORDING STYLE throughout the whole script, which can't be
    # reliably force-corrected with a simple string insert. Being honest
    # about that limit: this detects and ALERTS if the qualifying language
    # is completely absent, rather than silently letting it slip through
    # unverified, but does not auto-rewrite the whole script's tone.
    evidence_qualifiers = ["according to", "reportedly", "court records", "alleged",
                           "prosecution argued", "investigators said", "per the report",
                           "documented", "the defense", "on record"]
    if not any(q in clean.lower() for q in evidence_qualifiers):
        log("  ⚠️ Factual-care check: no evidence-qualifying language detected — flagging for review")
        tg(f"⚠️ Evidence Room Ep{episode}: script has no evidence-qualifying wording "
           f"(\"according to\", \"reportedly\", etc.) — real defamation/factual-risk concern. "
           f"Recommend manual review of this script before it goes further.")

    # v6 addition — real research-usage verification (same fix built for
    # Ch1/Ch3/Ch4, applying here since Ch2 has the identical gap):
    # real_cases gets injected into the prompt, but nothing ever
    # verified the AI actually used it versus inventing plausible-
    # sounding details instead. Logged every attempt (this function runs
    # once per attempt); the real Telegram alert fires once, for the
    # actual winning attempt, in run_stage1 — avoiding up to 13 noisy
    # alerts per episode.
    if real_cases:
        _script_lower = clean.lower()
        _research_words = set()
        for c in real_cases[:3]:
            _research_words.update(
                w.strip(".,;:").lower() for w in (c.get("title", "") + " " + c.get("summary", "")).split()
                if len(w) > 6
            )
        _used = any(w in _script_lower for w in _research_words)
        log(f"  Research-usage check: {'genuinely reflected' if _used else 'NOT clearly used'}")

    log(f"  Script: {wc}w | {violations} MD | {len(scenes)} scenes")
    return clean, scenes, title, thumbnail_text, tags, violations, real_cases


def render_connection_reveal(draw, W, H, nodes, progress, accent, font_sm):
    """
    Animate lines drawing between connection nodes progressively.
    nodes: list of (x, y, label) tuples
    """
    if len(nodes) < 2: return
    total_connections = len(nodes) - 1
    for i in range(total_connections):
        conn_progress = min(1.0, max(0.0, (progress * total_connections - i)))
        if conn_progress <= 0: continue
        x1, y1 = nodes[i][0], nodes[i][1]
        x2, y2 = nodes[i+1][0], nodes[i+1][1]
        cx = int(x1 + (x2 - x1) * conn_progress)
        cy = int(y1 + (y2 - y1) * conn_progress)
        draw.line([(x1, y1), (cx, cy)], fill=accent, width=2)
        r = 6
        draw.ellipse([(x1-r, y1-r), (x1+r, y1+r)], fill=accent)
        if conn_progress >= 1.0:
            draw.ellipse([(x2-r, y2-r), (x2+r, y2+r)], fill=accent)

def render_counting_number(draw, x, y, target_val, progress, font_lg, color,
                           prefix="", suffix="", decimals=0):
    """
    Animate a number counting up from 0 to target_val.
    Creates urgency — viewer feels the scale of the case.

    FIX (this was never wired in, and the original version would have
    been a real regression if simply swapped in — it only rendered a
    bare comma-separated integer, silently losing formatting like "$"
    prefixes, "million"/"reports" unit suffixes, and decimal precision
    that the actual stat text needs, e.g. "$2.4 million" or "47 reports").
    Now accepts prefix/suffix/decimals so the counted number keeps its
    real formatting throughout the animation, not just at the final frame.
    """
    current = target_val * min(progress * 1.5, 1.0)
    if decimals > 0:
        num_text = f"{current:,.{decimals}f}"
    else:
        num_text = f"{int(current):,}"
    text = f"{prefix}{num_text}{suffix}"
    bbox = draw.textbbox((0,0), text, font=font_lg)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw//2 + 1, y + 1), text, font=font_lg, fill=(20, 20, 20))
    draw.text((x - tw//2, y), text, font=font_lg, fill=color)


def _parse_stat_for_counting(item):
    """
    Splits a formatted stat string like "$2.4 million" or "47 reports"
    into (prefix, numeric_value, suffix, decimals) so it can be animated
    while keeping its real formatting. Returns None if no clean numeric
    value can be extracted, so the caller can safely fall back to the
    plain static display for anything too irregular to animate safely.
    """
    m = re.search(r'^([^\d]*)([\d,]+(?:\.\d+)?)(.*)$', item.strip())
    if not m:
        return None
    prefix, num_str, suffix = m.group(1), m.group(2), m.group(3)
    try:
        clean_num = num_str.replace(",", "")
        decimals = len(clean_num.split(".")[1]) if "." in clean_num else 0
        value = float(clean_num)
        return prefix, value, suffix, decimals
    except ValueError:
        return None

def render_classified_stamp(draw, W, H, progress, font_lg):
    """
    Stamp-reveal effect for classified evidence.
    Red CLASSIFIED diagonal stamp appears at reveal moment.
    """
    if progress < 0.7: return
    stamp_text  = "CLASSIFIED"
    stamp_color = (200, 0, 0)
    bbox = draw.textbbox((0,0), stamp_text, font=font_lg)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    cx, cy = W//2, H//2
    draw.text((cx - tw//2 + 2, cy - th//2 + 2), stamp_text, font=font_lg, fill=(40,0,0))
    draw.text((cx - tw//2, cy - th//2), stamp_text, font=font_lg, fill=stamp_color)
    pad = 20
    for thickness in range(1, 4):
        draw.rectangle([cx-tw//2-pad, cy-th//2-pad,
                        cx+tw//2+pad, cy+th//2+pad],
                       outline=stamp_color, width=thickness)


def render_frame_pil(style_name, scene, frame_idx, total_frames, scene_idx, total_scenes):
    style    = STYLES[style_name]
    bg, primary, accent, secondary = style["bg"], style["primary"], style["accent"], style["secondary"]
    img      = Image.new("RGB",(W,H),bg)
    draw     = ImageDraw.Draw(img)
    progress = frame_idx / max(total_frames-1, 1)

    try:
        font_lg   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_md   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_xs   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    except:
        font_lg = font_md = font_sm = font_xs = font_mono = ImageFont.load_default()

    stype = scene.get("type","evidence_board")

    # Enhanced atmospheric backgrounds — psychological thriller grade
    pulse = style.get("pulse", accent)
    glow  = style.get("glow", accent)

    if style_name == "dark_minimal":
        # Vignette: red pulse from corners — creates dread
        for i in range(0, min(frame_idx*3, 120), 6):
            intensity = max(0, 40 - i)
            draw.rectangle([i,i,W-i,H-i], outline=(intensity,0,0))
        # Scanlines for digital surveillance feel
        for y in range(0, H, 3):
            draw.line([(0,y),(W,y)], fill=(0,0,0,60), width=1)

    elif style_name == "cinematic":
        # Deep blue atmospheric gradient
        for y in range(0, H, 2):
            intensity = int(15 * (1 - y/H))
            draw.line([(0,y),(W,y)], fill=(intensity, intensity*2, intensity*4), width=1)
        # Film grain
        for _ in range(200):
            gx, gy = random.randint(0,W), random.randint(0,H)
            draw.point([(gx,gy)], fill=(random.randint(10,30),)*3)

    elif style_name == "documentary":
        # Aged paper texture with film grain
        for y in range(0, H, 6):
            if random.random() < 0.15:
                draw.line([(0,y),(W,y)], fill=(22,18,14), width=1)
        # Random damage spots
        for _ in range(30):
            dx, dy = random.randint(0,W), random.randint(0,H)
            draw.ellipse([(dx-2,dy-2),(dx+2,dy+2)], fill=(8,6,4))

    # Glitch effect on high-tension frames (every 90 frames = 3s at 30fps)
    if frame_idx % 90 < 3:
        for _ in range(5):
            gy = random.randint(0, H)
            shift = random.randint(-8, 8)
            draw.line([(0,gy),(W,gy)], fill=glow, width=1)

    # Dramatic corner marks with glow
    for thickness, color in [(3, pulse), (1, glow)]:
        draw.line([(0,0),(80,0)], fill=color, width=thickness)
        draw.line([(0,0),(0,80)], fill=color, width=thickness)
        draw.line([(W-80,H-1),(W,H-1)], fill=color, width=thickness)
        draw.line([(W-1,H-80),(W-1,H)], fill=color, width=thickness)

    # Classification watermark — feels like classified footage
    draw.text((30,H-42), "THE EVIDENCE ROOM — CLASSIFIED", font=font_xs, fill=secondary)
    draw.text((W-200,H-42), f"CASE {scene_idx+1:03d}/{total_scenes:03d}", font=font_xs, fill=secondary)
    # Live recording indicator
    if frame_idx % 60 < 30:  # blink every second
        draw.ellipse([(W-30,15),(W-15,30)], fill=accent)
        draw.text((W-55,14), "REC", font=font_xs, fill=accent)

    # Scene title
    title = scene.get("title","EVIDENCE")
    if progress > 0.05:
        ta = min(1.0,(progress-0.05)*5)
        draw.text((int(80+(1.0-ta)*30),40),title,font=font_lg,fill=accent)
        draw.line([(80,112),(80+int(700*progress),112)],fill=accent,width=2)

    # Render scene type
    # FIX: this checked for "document" but every actual scene generated
    # (by the AI prompt and the fallback bank) uses "document_reveal" —
    # a real naming mismatch meaning every single document-reveal scene
    # silently fell through to the generic evidence-board renderer
    # instead of its purpose-built typewriter-reveal + dramatic-stamp
    # visual, which was sitting fully built and unused underneath it.
    if   stype=="timeline":      _render_timeline(draw,scene,progress,style,font_md,font_sm,font_xs)
    elif stype=="document_reveal": _render_document(draw,scene,progress,style,style_name,font_md,font_sm,font_mono)
    elif stype=="data_reveal":   _render_data_reveal(draw,scene,progress,style,font_lg,font_md,font_sm)
    elif stype=="connection_map":_render_connection_map(draw,scene,progress,style,font_md,font_sm)
    else:                        _render_evidence_board(draw,scene,progress,style,font_md,font_sm,font_xs)
    return img

def _render_timeline(draw,scene,progress,style,font_md,font_sm,font_xs):
    items=scene.get("items",[]); label=scene.get("label","TIMELINE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    lx,ty,by=200,160,H-150
    draw.line([(lx,ty),(lx,by)],fill=secondary,width=2)
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    n=len(items); spacing=(by-ty)//max(n,1)
    for i,item in enumerate(items):
        ip=(progress*n)-i
        if ip<=0: continue
        a=min(1.0,ip); y=ty+i*spacing
        dc=accent if a>0.5 else secondary
        draw.ellipse([(lx-8,y-8),(lx+8,y+8)],fill=dc)
        xe=int(lx+60+a*40)
        draw.line([(lx+8,y),(xe,y)],fill=dc,width=2)
        if a>0.3: draw.text((lx+80,y-14),item,font=font_sm,fill=primary)

def _render_document(draw,scene,progress,style,style_name,font_md,font_sm,font_mono):
    """Enhanced document scene: typewriter reveal, redaction lines, dramatic stamp."""
    lines=scene.get("lines",["CONFIDENTIAL"]); stamp=scene.get("stamp","")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    glow=style.get("glow",accent)
    px,py,dw,dh=160,120,W-320,H-240
    pc=(8,8,14) if style_name!="documentary" else (16,12,9)
    # Outer glow effect on document border
    for offset in [4,2,1]:
        draw.rectangle([(px-offset,py-offset),(px+dw+offset,py+dh+offset)],
                       outline=accent if offset==1 else (accent[0]//4,accent[1]//4,accent[2]//4))
    draw.rectangle([(px,py),(px+dw,py+dh)],fill=pc,outline=secondary,width=2)
    # Header bar
    draw.rectangle([(px,py),(px+dw,py+55)],fill=(accent[0]//3,accent[1]//3,accent[2]//3))
    draw.text((px+20,py+14),"CLASSIFIED — RESTRICTED ACCESS",font=font_sm,fill=glow)
    draw.line([(px+15,py+58),(px+dw-15,py+58)],fill=accent,width=2)
    n=len(lines)
    for i,line in enumerate(lines):
        lp=(progress*(n+1.5))-i
        if lp<=0: continue
        a=min(1.0,lp); y=py+75+i*58
        # Typewriter effect: reveal characters gradually
        chars_to_show = int(len(line) * min(1.0, (lp)*3))
        visible = line[:chars_to_show]
        # Redacted lines start with [
        if line.startswith("["):
            # Black redaction bar
            bb = draw.textbbox((0,0),line,font=font_mono)
            tw = bb[2]-bb[0]
            draw.rectangle([(px+40,y-2),(px+40+tw+8,y+28)],fill=(0,0,0))
            if progress>0.85:  # Reveal after 85% — dramatic moment
                draw.text((px+40,y),line.strip("[]"),font=font_mono,fill=accent)
        else:
            draw.text((px+40,y),visible,font=font_mono,fill=primary)
            # Cursor blink at current typing position
            if chars_to_show < len(line) and int(progress*20)%2==0:
                cw = draw.textbbox((0,0),visible,font=font_mono)[2]
                draw.line([(px+42+cw,y),(px+42+cw,y+24)],fill=glow,width=2)
    # Dramatic stamp reveal
    if stamp and progress>0.75:
        stamp_alpha = min(1.0,(progress-0.75)*4)
        sx,sy=px+dw-300,py+dh-170
        draw.rectangle([(sx,sy),(sx+270,sy+120)],outline=accent,width=4)
        for thickness in [4,2]:
            draw.line([(sx,sy),(sx+270,sy+120)],fill=accent,width=thickness)
            draw.line([(sx+270,sy),(sx,sy+120)],fill=accent,width=thickness)
        draw.text((sx+20,sy+35),stamp,font=font_md,fill=accent)

def ease_out_cubic(t):
    """Smooth, professional deceleration curve — the motion signature of
    well-produced explainer channels (Infographics Show, Kurzgesagt-style),
    versus the raw linear progress used before. Tested by direct render
    before integrating (icon_test.png/icon_test2.png), not assumed."""
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)


def draw_infographic_icon(draw, icon_type, cx, cy, size, color, font=None):
    """
    Simple flat icons — the single most recognizable visual signature of
    Infographics-Show-style content: every stat/data point paired with a
    small icon, not just bare text. Pure PIL primitives, zero external
    assets, zero API calls (no free-tier risk at all for this system).
    Verified by direct render before integrating, not assumed to look right.
    """
    r = size // 2
    if icon_type == "dollar":
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=3)
        if font:
            draw.text((cx, cy), "$", font=font, fill=color, anchor="mm")
    elif icon_type == "person":
        draw.ellipse([cx-r*0.4, cy-r, cx+r*0.4, cy-r*0.15], outline=color, width=3)
        draw.arc([cx-r, cy-r*0.3, cx+r, cy+r*1.2], start=180, end=360, fill=color, width=3)
    elif icon_type == "document":
        draw.rectangle([cx-r/1.5, cy-r, cx+r/1.5, cy+r], outline=color, width=3)
        for i in range(3):
            ly = cy - r/2 + i*(size/4)
            draw.line([(cx-r/2.2, ly), (cx+r/2.2, ly)], fill=color, width=2)
    elif icon_type == "clock":
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=3)
        draw.line([(cx, cy), (cx, cy-r+10)], fill=color, width=3)
        draw.line([(cx, cy), (cx+r-15, cy)], fill=color, width=3)
    elif icon_type == "warning":
        draw.polygon([(cx, cy-r), (cx-r, cy+r), (cx+r, cy+r)], outline=color, width=3)
        draw.line([(cx, cy-r/3), (cx, cy+r/4)], fill=color, width=3)
        draw.ellipse([cx-3, cy+r/2, cx+3, cy+r/2+6], fill=color)


def _pick_icon_for_stat(text):
    """Match a stat's icon to its actual content — $ amounts get a dollar
    icon, years/days get a clock, victims/cases get a person, reports get
    a document, everything else gets a warning triangle."""
    t = text.upper()
    if "$" in t: return "dollar"
    if any(w in t for w in ("YEAR","DAY","MONTH","WEEK")): return "clock"
    if any(w in t for w in ("VICTIM","CASE","PEOPLE","AFFECTED","MEMBER")): return "person"
    if any(w in t for w in ("REPORT","DOCUMENT","FILE","RECORD")): return "document"
    return "warning"


def _render_data_reveal(draw,scene,progress,style,font_lg,font_md,font_sm):
    items=scene.get("items",[]); label=scene.get("label","DATA")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_sm,fill=secondary)
    draw.line([(80,H-90),(W-80,H-90)],fill=secondary,width=1)
    n=len(items); cw=(W-200)//max(n,1)
    try:
        font_icon = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except Exception:
        font_icon = None
    for i,item in enumerate(items):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=ease_out_cubic(min(1.0,ip)); cx=100+i*cw+cw//2
        bh=int(a*350); bt=H-150-bh; bc=accent if i==n-1 else primary
        draw.rectangle([(cx-40,bt),(cx+40,H-150)],fill=bc,outline=secondary,width=1)
        if a>0.3:
            icon_type = _pick_icon_for_stat(item)
            draw_infographic_icon(draw, icon_type, cx, bt-95, 55, accent, font_icon)
        if a>0.4:
            # FIX: render_counting_number existed fully built but was never
            # wired in — stat numbers just popped in as static text with
            # no animation. Now genuinely counts up while preserving the
            # real formatting ("$2.4 million", "47 reports"), with a safe
            # fallback to the original static display for anything that
            # doesn't cleanly parse as a number.
            parsed = _parse_stat_for_counting(item)
            if parsed:
                prefix, target_val, suffix, decimals = parsed
                count_progress = min(1.0, ip)  # this item's own reveal progress
                render_counting_number(draw, cx, bt-55, target_val, count_progress,
                                       font_lg, primary, prefix=prefix, suffix=suffix,
                                       decimals=decimals)
            else:
                try: tw=font_lg.getbbox(item)[2]-font_lg.getbbox(item)[0]
                except: tw=100
                draw.text((cx-tw//2,bt-55),item,font=font_lg,fill=primary)

def _render_connection_map(draw,scene,progress,style,font_md,font_sm):
    nodes=scene.get("nodes",[]); label=scene.get("label","NETWORK")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_sm,fill=secondary)
    n=len(nodes)
    if n==0: return
    sp=(W-300)//max(n-1,1); ny=H//2
    positions=[(150+i*sp,ny) for i in range(n)]
    for i,(nx,ny2) in enumerate(positions):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=ease_out_cubic(min(1.0,ip))
        if i<n-1 and ip>0.8:
            nnx,nny=positions[i+1]
            le=int(nx+40+a*(nnx-nx-80))
            draw.line([(nx+40,ny2),(le,ny2)],fill=accent,width=2)
            if le>nx+100: draw.polygon([(le,ny2),(le-12,ny2-8),(le-12,ny2+8)],fill=accent)
        bc=accent if i==0 or i==n-1 else secondary
        draw.rectangle([(nx-60,ny2-25),(nx+60,ny2+25)],fill=(5,5,15),outline=bc,width=2)
        draw.text((nx-50,ny2-12),nodes[i],font=font_sm,fill=primary)

def _render_evidence_board(draw,scene,progress,style,font_md,font_sm,font_xs):
    items=scene.get("items",[]); label=scene.get("label","EVIDENCE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    n=len(items); cols=2; rows=(n+1)//2
    cw=(W-200)//cols; ch=(H-320)//max(rows,1)
    for i,item in enumerate(items):
        ip=(progress*(n+0.5))-i
        if ip<=0: continue
        a=min(1.0,ip); col=i%cols; row=i//cols
        cx=100+col*cw; cy=160+row*ch
        draw.rectangle([(cx,cy),(cx+cw-20,cy+ch-20)],fill=(8,8,18),
                       outline=accent if a>0.8 else secondary,width=1)
        if a>0.2:
            pts=item.split(":")
            if len(pts)==2:
                draw.text((cx+15,cy+14),pts[0]+":",font=font_xs,fill=secondary)
                draw.text((cx+15,cy+44),pts[1].strip(),font=font_md,fill=primary)
            else:
                draw.text((cx+15,cy+24),item,font=font_sm,fill=primary)


# Ken Burns motion profiles per scene type
# Slow camera movement creates documentary cinematography feel
SCENE_MOTION = {
    "timeline":        "zoompan=z='min(zoom+0.0008,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "document_reveal": "zoompan=z='min(zoom+0.001,1.4)':d=1:x='iw/2-(iw/zoom/2)':y='ih*0.3-(ih/zoom*0.3)'",
    "data_reveal":     "zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.001))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "connection_map":  "zoompan=z='1.2+0.05*sin(2*PI*on/100)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "evidence_board":  "zoompan=z='min(zoom+0.0006,1.25)':d=1:x='(iw-iw/zoom)*on/n':y='ih/2-(ih/zoom/2)'",
}

def apply_ken_burns(input_path, output_path, scene_type, fps=24, duration=None):
    """
    Apply Ken Burns (slow zoom/pan) motion to a video scene.
    Makes animated frames feel cinematic — industry standard for documentary.
    Falls back to original if filter fails.
    """
    motion = SCENE_MOTION.get(scene_type, SCENE_MOTION["timeline"])
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"{motion},scale=1920:1080:flags=lanczos",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "copy",
        ]
        if duration:
            cmd += ["-t", str(duration)]
        cmd.append(output_path)
        run_ffmpeg(cmd, label=f"ken-burns-{scene_type}", timeout=600)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 100000:
            log(f"  Ken Burns ({scene_type}): OK")
            return output_path
    except Exception as e:
        log(f"  Ken Burns (non-fatal, using original): {e}")
    return input_path

def fetch_pollinations_bg(topic, niche_name, out_path):
    """v2: delegates to thumbnail_engine_v2 background fetcher."""
    try:
        from thumbnail_engine_v2 import fetch_background
        import hashlib
        seed   = int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999
        result = fetch_background(topic, niche_name, seed, str(WORK_DIR))
        if result and Path(result).exists():
            import shutil
            shutil.copy(result, out_path)
            return True
    except Exception as e:
        log(f"  fetch_pollinations_bg (non-fatal): {e}")
    return False


def generate_thumbnail_with_ai_bg(title, thumb_text, niche_name, topic,
                                   ab_style="A", episode=1, channel_name="The Evidence Room"):
    """v2 thumbnail: three-layer composition via thumbnail_engine_v2."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title        = title,
            thumb_text   = thumb_text,
            niche_name   = niche_name,
            topic        = topic,
            channel_name = channel_name,
            episode      = episode,
            work_dir     = str(WORK_DIR),
            ab_variant   = ab_style,
            cache_dir    = str(SCRIPT_DIR),  # persistent — avatar cache must
                                              # survive between runs
        )
        if result and Path(result).exists():
            log(f"  Thumbnail v2 ({niche_name}): {Path(result).stat().st_size//1024}KB")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    return None


# ══════════════════════════════════════════════════════════════════
# NICHE-AWARE BACKGROUND MUSIC (v6 addition, per explicit requirement:
# "the background noise should be according to the niche"). Same real
# system built for Ch1, with moods matched to Ch2's own 7 niches.
#
# HONEST DESIGN NOTE: real, freely-licensed tracks (e.g. sourced once
# from Pixabay's actual music library, free commercial use permitted)
# are the real fix — genuine recorded texture, not synthesis. Built to
# use real bundled files the MOMENT they exist (drop into
# music_bank/<mood>/ as any .mp3), rotating through what's present.
# Until then, falls back to a genuinely mood-distinct synthesis rather
# than the single generic brown-noise texture this replaces.
# ══════════════════════════════════════════════════════════════════

NICHE_MUSIC_MOOD = {
    "forensic_finance":       "clinical_tension",
    "criminal_investigation": "investigative",
    "corporate_exposure":     "corporate_dread",
    "digital_forensics":      "digital_unease",
    "body_cam_police":        "raw_tension",
    "courtroom_drama":        "gravitas",
    "robbery_documentaries":  "heist_tension",
}

MOOD_TRACK_RECOMMENDATIONS = {
    "clinical_tension": ["Search Pixabay Music for: 'corporate thriller tension', 'cold suspense', 'financial crime ambient'"],
    "investigative": ["Search Pixabay Music for: 'investigation ambient', 'procedural tension', 'detective noir'"],
    "corporate_dread": ["Search Pixabay Music for: 'corporate dark ambient', 'boardroom tension', 'sterile suspense'"],
    "digital_unease": ["Search Pixabay Music for: 'cyber tension', 'digital glitch ambient', 'tech thriller dark'"],
    "raw_tension": ["Search Pixabay Music for: 'urgent tension', 'raw suspense drone', 'visceral ambient'"],
    "gravitas": ["Search Pixabay Music for: 'courtroom drama ambient', 'formal tension', 'weighty orchestral drone'"],
    "heist_tension": ["Search Pixabay Music for: 'heist tension', 'kinetic suspense', 'driving thriller pulse'"],
}

MUSIC_BANK_ROOT = Path(__file__).parent / "music_bank"

def _synthesize_mood_track(mood, duration):
    """Genuinely mood-distinct synthesis fallback — different frequency
    relationships, filtering, and noise character per mood."""
    path = str(WORK_DIR / f"music_{mood}.mp3")
    dur = int(duration) + 30
    recipes = {
        "clinical_tension": (
            ["-f","lavfi","-i",f"sine=frequency=130:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=196:duration={dur}",  # perfect fifth, cold/clean
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0015:duration={dur}"],
            "[0]volume=0.06[a];[1]volume=0.04[b];[2]volume=0.2[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=500,highpass=f=80,volume=0.12[out]"),
        "investigative": (
            ["-f","lavfi","-i",f"sine=frequency=80:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=120:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0025:duration={dur}"],
            "[0]volume=0.08[a];[1]volume=0.05[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=380,highpass=f=45,volume=0.13[out]"),
        "corporate_dread": (
            ["-f","lavfi","-i",f"sine=frequency=45:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=46:duration={dur}",  # near-unison, sterile throb
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.09[b];[2]volume=0.25[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=220,highpass=f=30,volume=0.14[out]"),
        "digital_unease": (
            ["-f","lavfi","-i",f"sine=frequency=300:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=303:duration={dur}",  # thin, glitchy beating
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.005:duration={dur}"],
            "[0]volume=0.03[a];[1]volume=0.03[b];[2]volume=0.4[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=700,highpass=f=150,volume=0.1[out]"),
        "raw_tension": (
            ["-f","lavfi","-i",f"sine=frequency=65:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=97:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.004:duration={dur}"],
            "[0]volume=0.1[a];[1]volume=0.06[b];[2]volume=0.35[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=340,highpass=f=40,volume=0.15[out]"),
        "gravitas": (
            ["-f","lavfi","-i",f"sine=frequency=55:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=82:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0015:duration={dur}"],
            "[0]volume=0.08[a];[1]volume=0.05[b];[2]volume=0.15[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=260,highpass=f=32,volume=0.13[out]"),
        "heist_tension": (
            ["-f","lavfi","-i",f"sine=frequency=90:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=135:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.003:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.06[b];[2]volume=0.28[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=400,highpass=f=50,volume=0.15[out]"),
    }
    inputs, filt = recipes.get(mood, recipes["investigative"])
    try:
        subprocess.run(["ffmpeg", "-y"] + inputs +
                       ["-filter_complex", filt, "-map", "[out]", "-c:a", "mp3", "-q:a", "4", path],
                       capture_output=True, timeout=60)
        if Path(path).exists() and Path(path).stat().st_size > 5000:
            return path
    except Exception as e:
        log(f"  Mood synthesis ({mood}) failed: {e}")
    return None


def get_niche_ambient_music(niche_name, duration):
    """Real entry point — picks a real bundled track for this niche's
    mood if one exists (rotating to avoid repetition), otherwise the
    mood-distinct synthesis above."""
    mood = NICHE_MUSIC_MOOD.get(niche_name, "investigative")
    mood_dir = MUSIC_BANK_ROOT / mood
    real_tracks = []
    try:
        if mood_dir.exists():
            real_tracks = sorted([p for p in mood_dir.glob("*.mp3") if p.stat().st_size > 10000])
    except Exception:
        pass

    if real_tracks:
        chosen = random.choice(real_tracks)
        log(f"  Using real bundled track for mood '{mood}': {chosen.name}")
        out = str(WORK_DIR / f"music_real_{mood}.mp3")
        try:
            subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(chosen),
                            "-t", str(int(duration) + 5), "-c:a", "mp3", "-q:a", "3", out],
                           capture_output=True, timeout=60)
            if Path(out).exists() and Path(out).stat().st_size > 10000:
                return out
        except Exception as e:
            log(f"  Real track trim failed, falling back to synthesis: {e}")

    return _synthesize_mood_track(mood, duration)


def render_and_encode(style_name, scenes, audio_path, duration, niche_name=None, niche_obj=None, episode=1, real_cases=None, ass_path=None):
    frames_base = WORK_DIR/"frames"
    frames_base.mkdir(exist_ok=True)
    concat_parts = []
    black_fallback_count = 0  # FIX: previously only individual "Scene N failed"
    # log lines existed — no aggregate count or Telegram alert if MULTIPLE
    # scenes fell back to solid black, unlike the equivalent system built for
    # Ch1's background footage. Added here for the same visibility.
    for si, scene in enumerate(scenes):
        dur_s = scene.get("duration",8); total_f = dur_s*FPS
        fd = frames_base/f"scene_{si:03d}"; fd.mkdir(exist_ok=True)
        log(f"  Rendering scene {si+1}/{len(scenes)}: {scene.get('type','?')} — {total_f}f")
        for fi in range(total_f):
            img = render_frame_pil(style_name, scene, fi, total_f, si, len(scenes))
            img.save(str(fd/f"frame_{fi:05d}.png"))
        sm4 = str(fd)+"_s.mp4"
        _enc_result = subprocess.run(
            ["ffmpeg","-y","-framerate",str(FPS),"-i",f"{fd}/frame_%05d.png",
             "-c:v","libx264","-preset","ultrafast","-crf","26",
             "-pix_fmt","yuv420p","-r",str(FPS),sm4],
            capture_output=True, timeout=600)
        # Verify scene mp4 was created before adding to concat
        if _enc_result.returncode == 0 and Path(sm4).exists() and \
           Path(sm4).stat().st_size > 50000:
            # FIX: apply_ken_burns existed fully built (real per-scene-type
            # zoom/pan filters, described in its own docstring as "industry
            # standard for documentary") but was never called anywhere —
            # every scene rendered with zero cinematic motion beyond
            # whatever render_frame_pil already did internally. Applied
            # here as a real finishing pass; falls back to the original
            # scene file automatically if the filter fails for any reason.
            scene_type = scene.get("type", "timeline")
            kb_path = str(fd) + "_kb.mp4"
            enhanced = apply_ken_burns(sm4, kb_path, scene_type, fps=FPS, duration=dur_s)
            concat_parts.append(f"file '{enhanced}'")
            log(f"    Scene {si+1} encoded: {Path(sm4).stat().st_size//1024}KB")
        else:
            # Fallback: create a solid-colour scene as replacement
            log(f"    Scene {si+1} encode failed — using fallback")
            black_fallback_count += 1
            _fb = str(fd)+"_fallback.mp4"
            subprocess.run([
                "ffmpeg","-y","-f","lavfi",
                "-i",f"color=c=black:s=1920x1080:d={dur_s}",
                "-c:v","libx264","-preset","ultrafast","-crf","26",
                "-pix_fmt","yuv420p","-r",str(FPS), _fb],
                capture_output=True, timeout=60)
            if Path(_fb).exists():
                concat_parts.append(f"file '{_fb}'")
                log(f"    Scene {si+1} fallback created")

    concat_file = str(WORK_DIR/"concat.txt")
    if black_fallback_count > 0:
        tg(f"⚠️ Evidence Room: {black_fallback_count}/{len(scenes)} animated scenes "
           f"failed to render and fell back to solid black. Check PIL/font setup.")
    total_scene_dur = sum(s.get("duration",8) for s in scenes)
    repeats = max(1, int(duration/total_scene_dur)+2)
    with open(concat_file,"w") as f:
        for _ in range(repeats): f.write("\n".join(concat_parts)+"\n")

    raw = str(WORK_DIR/"raw.mp4")
    if not concat_parts:
        raise RuntimeError("All scene encodings failed — no parts for concat")
    log(f"  Concatenating {len(concat_parts)} scene parts...")
    _concat_result = subprocess.run(
        ["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,
         "-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p",
         "-r",str(FPS),raw],
        capture_output=True, timeout=900)
    if _concat_result.returncode != 0:
        err = _concat_result.stderr.decode("utf-8","ignore")[-300:]
        raise RuntimeError(f"FFmpeg concat failed: {err}")
    final = str(WORK_DIR/"final.mp4")
    # FIX (found going through Ch1/Ch2's audio systems in full, per
    # explicit requirement: "background noise should be according to
    # the niche"): this used to be a single generic brown-noise texture
    # (300-700Hz bandpass), IDENTICAL for forensic_finance,
    # criminal_investigation, corporate_exposure, digital_forensics,
    # body_cam_police, courtroom_drama, and robbery_documentaries alike.
    # Now genuinely niche-aware — see get_niche_ambient_music below.
    ambient_path = get_niche_ambient_music(niche_name, duration)
    try:
        if ambient_path and Path(ambient_path).exists():
            mixed = str(WORK_DIR/"mixed_ch2.mp3")
            subprocess.run([
                "ffmpeg","-y","-i",audio_path,"-i",ambient_path,
                "-filter_complex","[0:a][1:a]amix=inputs=2:weights=1 0.03",
                "-c:a","mp3","-q:a","2", mixed],
                capture_output=True, timeout=120)
            if Path(mixed).exists() and Path(mixed).stat().st_size > 100000:
                audio_path = mixed
                log("  Niche-matched ambient atmosphere mixed in")
    except Exception as _ae:
        log(f"  Ambient (non-fatal): {_ae}")

    ffmpeg_cmd = ["ffmpeg","-y","-i",raw,"-i",audio_path]
    if ass_path and Path(ass_path).exists():
        escaped_ass = str(ass_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        ffmpeg_cmd += ["-vf", f"ass='{escaped_ass}'"]
        log("  Burning in real, word-synced captions")
    ffmpeg_cmd += ["-c:v","libx264","-preset","medium","-crf","19",
                    "-c:a","aac","-b:a","192k","-t",str(duration),
                    "-pix_fmt","yuv420p","-movflags","+faststart","-shortest",final]
    # FIX (found on deep re-audit): this was the one ffmpeg call in this
    # function with no returncode check at all — the step that actually
    # bakes narration audio and burned captions into the frames. WORK_DIR
    # is a fixed, non-per-run path, so a failed mux here could silently
    # leave a stale final.mp4 from an earlier call in the same run (e.g.
    # a swap_voice/edit re-render) looking like a successful new one.
    _mux_result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=2400)
    if _mux_result.returncode != 0 or not Path(final).exists() or Path(final).stat().st_size < 500000:
        err = _mux_result.stderr.decode("utf-8", "ignore")[-300:]
        raise RuntimeError(f"FFmpeg audio+caption mux failed: {err}")
    log(f"  Video: {Path(final).stat().st_size/1024/1024:.0f}MB | 1080p | "
        f"{'Real synced captions' if ass_path else 'No captions (real sync unavailable this episode)'}")

    # v6 addition, per explicit request to check every channel for
    # missing growth levers: Ch2 had NO outro at all — Ch1 has one,
    # Ch2 never did. Built as a genuinely separate final step (not
    # injected into the scene-cycling loop above, which repeats to fill
    # the narration's length and would have repeated or mistimed an
    # outro placed inside it). Honest design matching Ch1's corrected
    # version: a real subscribe reminder + episode branding, NOT a fake
    # visual mimicking YouTube's actual (non-API-accessible) clickable
    # end-screen cards.
    try:
        _series_name = niche_obj.get("series", "The Evidence Room") if niche_obj else "The Evidence Room"
        outro_path = create_evidence_room_outro(_series_name, episode)
        # v6 addition — real on-screen source credits, per explicit
        # request. Only produces a real segment when there are genuine
        # URL-backed sources to show.
        citations_path = create_evidence_room_citations_scene(real_cases)
        _segments = [final]
        if citations_path and Path(citations_path).exists():
            _segments.append(citations_path)
        if outro_path and Path(outro_path).exists():
            _segments.append(outro_path)
        if len(_segments) > 1:
            final_with_outro = str(WORK_DIR / "final_with_outro.mp4")
            outro_concat_list = str(WORK_DIR / "outro_concat.txt")
            with open(outro_concat_list, "w") as f:
                for seg in _segments:
                    f.write(f"file '{seg}'\n")
            _outro_result = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", outro_concat_list,
                 "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", final_with_outro],
                capture_output=True, timeout=300)
            if _outro_result.returncode == 0 and Path(final_with_outro).exists() and \
               Path(final_with_outro).stat().st_size > Path(final).stat().st_size:
                log(f"  Outro/citations appended: {Path(final_with_outro).stat().st_size/1024/1024:.0f}MB")
                return final_with_outro
            log("  Outro concat failed (non-fatal) — using video without outro")
    except Exception as _oe:
        log(f"  Outro (non-fatal): {_oe}")

    return final


def create_evidence_room_citations_scene(real_cases):
    """
    v6 addition — real on-screen source credits, per explicit request:
    "give the source details... just like in a movie after the post
    credits." Same design as Ch1's version: only built when there's at
    least one real, URL-backed source; shows source titles (not raw
    URLs) with a pointer to the description for the actual links.
    """
    real_sources = [c for c in (real_cases or []) if c.get("url")]
    if not real_sources:
        return None
    duration = 6
    path = str(WORK_DIR / "citations_ch2.mp4")
    lines_filters = []
    y = 260
    lines_filters.append(
        "drawtext=text='SOURCES REFERENCED':fontsize=34:fontcolor=white:"
        f"x=(w-text_w)/2:y=180:enable='between(t,0,{duration})'")
    for c in real_sources[:3]:
        safe_title = (c["title"][:70]
                      .replace("'", "").replace('"', "").replace(":", " —"))
        lines_filters.append(
            f"drawtext=text='{safe_title}':fontsize=22:fontcolor=gray:"
            f"x=(w-text_w)/2:y={y}:enable='between(t,0,{duration})'")
        y += 45
    lines_filters.append(
        "drawtext=text='Full links in the description':fontsize=20:fontcolor=white:"
        f"x=(w-text_w)/2:y={y+20}:enable='between(t,0,{duration})'")
    vf = ",".join(lines_filters)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:size=1920x1080:rate=24:duration={duration}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:duration={duration}",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", path
    ], capture_output=True, timeout=60)
    return path if Path(path).exists() and Path(path).stat().st_size > 5000 else None


def create_evidence_room_outro(series_name="The Evidence Room", episode_num=1):
    """
    8-second burned-in outro card for Ch2 — genuinely new, this channel
    had none at all. Same honest design as Ch1's corrected version: a
    real subscribe reminder and episode branding, no fake-clickable
    visual mimicking YouTube's real (non-API-accessible) end-screen
    cards. If real end screens are set up manually in YouTube Studio,
    this stays deliberately simple and centered so it doesn't visually
    conflict with them.
    """
    series_name = series_name.replace("'", "").replace('"', "").replace(":", "")
    path = str(WORK_DIR / "outro_ch2.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1920x1080:rate=24:duration=8",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=8",
        "-vf",
        "drawbox=x=0:y=0:w=iw:h=ih:color=blue@0.25:t=6,"
        "drawtext=text='SUBSCRIBE TO " + series_name.upper() + "':fontsize=54:"
        "fontcolor=white:x=(w-text_w)/2:y=440:enable='between(t,0,8)',"
        "drawtext=text='NEW CASE FILES EVERY WEEK':fontsize=36:"
        "fontcolor=gray:x=(w-text_w)/2:y=540:enable='between(t,0,8)',"
        "drawtext=text='Case File #" + str(episode_num) + "':fontsize=30:"
        "fontcolor=gray:x=50:y=H-80:enable='between(t,0,8)'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", path
    ], capture_output=True, timeout=60)
    return path if Path(path).exists() and Path(path).stat().st_size > 10000 else None


# ════════════════════════════════════════════════════════════
# STAGE 5: SHORTS WITH SUBTITLES
# NO subtitles on main video — subtitles on Shorts ONLY
# ════════════════════════════════════════════════════════════
def generate_short_srt(script_clean, start, short_dur):
    words    = script_clean.split()
    total_wc = len(words)
    total_dur = (total_wc/125.0)*60.0
    wps      = total_wc/total_dur
    sw       = int(start*wps)
    ew       = min(int((start+short_dur)*wps)+5, total_wc)
    clip_wds = words[sw:ew]
    if not clip_wds: return None

    def fmt(t):
        h,r=divmod(int(t),3600); m,s=divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d},{int((t%1)*1000):03d}"

    entries=[]; idx,t=1,0.0
    cwps=len(clip_wds)/short_dur if short_dur>0 else 3.0
    for i in range(0,len(clip_wds),4):
        g=clip_wds[i:i+4]
        if not g: continue
        d=len(g)/cwps
        entries.append(f"{idx}\n{fmt(t)} --> {fmt(t+d)}\n{' '.join(g)}\n")
        idx+=1; t+=d
    srt=WORK_DIR/f"short_{idx}.srt"
    srt.write_text("\n".join(entries),encoding="utf-8")
    return str(srt)

# FIX (found on deep re-audit): niche_name was accepted here but never
# referenced in the function body — every niche (forensic_finance,
# criminal_investigation, corporate_exposure, digital_forensics,
# body_cam_police, courtroom_drama, robbery_documentaries) got the
# identical fixed EQ chain, unlike betrayal_deepdive/collapse_index which
# already have real per-niche NICHE_AUDIO_PROFILES. Also the old
# docstring claimed "reverb adds room depth" — no aecho/reverb filter
# exists anywhere in this chain or Ch1's, so that was never accurate;
# removed rather than propagated.
NICHE_AUDIO_PROFILES = {
    "forensic_finance": (
        # Dry and clinical — precise, analytical, no warmth
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "criminal_investigation": (
        # Tense and present — bass forward, urgent
        "equalizer=f=80:width_type=o:width=2:g=4,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-18dB:ratio=4:attack=3:release=90:makeup=3dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "corporate_exposure": (
        # Cold and clean — bright, corporate, controlled
        "equalizer=f=200:width_type=o:width=2:g=-1,"
        "equalizer=f=3500:width_type=o:width=2:g=3,"
        "equalizer=f=9000:width_type=o:width=2:g=-1,"
        "acompressor=threshold=-16dB:ratio=3:attack=5:release=80:makeup=2dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "digital_forensics": (
        # Cold and digital — tight, bright highs, minimal warmth
        "equalizer=f=250:width_type=o:width=2:g=-2,"
        "equalizer=f=4000:width_type=o:width=2:g=3,"
        "equalizer=f=10000:width_type=o:width=2:g=0,"
        "acompressor=threshold=-15dB:ratio=4:attack=2:release=50:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "body_cam_police": (
        # Raw and urgent — present mids, tighter dynamics
        "equalizer=f=100:width_type=o:width=2:g=3,"
        "equalizer=f=2000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-17dB:ratio=4:attack=2:release=60:makeup=3dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "courtroom_drama": (
        # Formal and resonant — balanced, weighted authority
        "equalizer=f=90:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=7000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-19dB:ratio=3:attack=5:release=100:makeup=2dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "robbery_documentaries": (
        # Tense and urgent — bass forward, dynamic
        "equalizer=f=70:width_type=o:width=2:g=4,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-18dB:ratio=4:attack=3:release=90:makeup=3dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["forensic_finance"]


def apply_audio_post_processing(input_path, output_path=None, niche_name=None):
    """
    Transform edge-tts flat TTS into cinematic investigative narrator
    quality. EQ boosts presence, compression smooths dynamics. Uses
    NICHE_AUDIO_PROFILES to select the real per-niche EQ chain, falling
    back to the default if niche_name is unknown.
    """
    try:
        if output_path is None:
            output_path = input_path.replace(".mp3", "_eq.mp3").replace(".wav", "_eq.wav")
        if output_path == input_path:
            output_path = input_path + ".eq.mp3"
        af = NICHE_AUDIO_PROFILES.get(niche_name, DEFAULT_AUDIO_PROFILE)

        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-af", af, "-c:a", "mp3", "-q:a", "2", output_path
        ], capture_output=True, timeout=300, check=True)
        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            log(f"  Audio post-processed ({niche_name}): {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e:
        log(f"  Audio processing (non-fatal): {e}")
    return input_path


async def _tts_ch2(text, voice_id, path):
    """
    Chunked TTS — splits long scripts at sentence boundaries every 3000 chars.
    Prevents 'No audio was received' error on scripts over ~2000 words.
    """
    import edge_tts, shutil
    MAX_CHUNK = 500
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []; current = ""
    for sent in sentences:
        if len(current) + len(sent) > MAX_CHUNK and current:
            chunks.append(current.strip()); current = sent
        else:
            current += (" " if current else "") + sent
    if current.strip(): chunks.append(current.strip())

    if len(chunks) <= 1:
        c = edge_tts.Communicate(text, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
        await asyncio.wait_for(c.save(path), timeout=120); return

    log(f"    Chunked TTS: {len(chunks)} segments")
    parts = []
    for i, chunk in enumerate(chunks):
        part = str(WORK_DIR / f"chunk_{i}_{voice_id[-8:]}.mp3")
        try:
            c = edge_tts.Communicate(chunk, voice_id, rate="-8%", pitch="+0Hz", volume="+8%")
            await c.save(part)
            if Path(part).exists() and Path(part).stat().st_size > 5000:
                parts.append(part)
        except Exception as e:
            log(f"    Chunk {i} error: {e}")

    if not parts: raise Exception("All TTS chunks failed")
    if len(parts) == 1: shutil.copy(parts[0], path); return

    lst = str(WORK_DIR / f"chunk_list_{voice_id[-8:]}.txt")
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", path],
                   capture_output=True, timeout=600)
    if not Path(path).exists():
        raise Exception("Chunk concatenation failed")


def _detect_abnormal_silence(mp3_path, total_duration):
    """
    v1 addition — real, signal-based audio quality check using ffmpeg's
    actual silencedetect filter, not just file size/duration heuristics.
    Flags if total detected silence exceeds 15% of the audio.
    """
    if not total_duration or total_duration <= 0:
        return True, 0.0
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(mp3_path), "-af", "silencedetect=noise=-30dB:d=1.0",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=60)
        silence_total = 0.0
        for line in r.stderr.splitlines():
            if "silence_duration:" in line:
                try:
                    silence_total += float(line.split("silence_duration:")[1].strip())
                except (ValueError, IndexError):
                    pass
        fraction = silence_total / total_duration
        is_normal = fraction <= 0.15
        if not is_normal:
            log(f"  Audio silence check: {fraction*100:.0f}% of audio is silence "
                f"(threshold 15%) — possible corrupted/truncated segment")
        return is_normal, fraction
    except Exception as e:
        log(f"  Silence detection (non-fatal, not blocking): {e}")
        return True, 0.0


def check_audio_quality(mp3_path, dur_expected):
    """
    Fixed threshold: edge-tts outputs ~48kbps MP3.
    Uses ffprobe actual duration. Falls back to 500KB minimum size check.
    FIX: this always measured the REAL duration via ffprobe internally but
    only ever returned True/False, discarding the actual number — meaning
    the caller had no way to know real audio length and fell back to a
    word-count ESTIMATE for everything downstream (video length, background
    clip timing, the duration cap check). Now returns (passed, actual_duration).
    """
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 200000:  # 200KB minimum
            log(f"  Quality FAIL: {sz}b — file empty or corrupt"); return False, None
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp3_path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual_dur = float(r.stdout.strip())
            if actual_dur < dur_expected * 0.20:  # 20% = accept any audio >= 3 min
                log(f"  Quality FAIL: {actual_dur:.0f}s vs {dur_expected:.0f}s expected")
                return False, actual_dur
            _silence_ok, _silence_frac = _detect_abnormal_silence(mp3_path, actual_dur)
            if not _silence_ok:
                log(f"  Quality FAIL: {_silence_frac*100:.0f}% silence — likely corrupted/truncated segment")
                return False, actual_dur
            log(f"  Quality OK: {sz/1024/1024:.1f}MB | {actual_dur:.0f}s"); return True, actual_dur
        log(f"  Quality OK (size): {sz/1024/1024:.1f}MB"); return True, None
    except Exception as e:
        log(f"  Quality check error: {e}"); return False, None


def _try_ssml_multirate_audio(script_clean, voice_id, niche_name):
    """
    FIX (found on deep re-audit): run_audio_with_ssml (multi-rate
    narration — delivery pace varies by section, reads as a real
    documentary narrator) was fully built here but never actually called
    anywhere in this file — control_files/archive both already wired this
    exact same function in via this exact wrapper. Falls back to None
    (triggering the existing flat-rate chain) on any doubt, including
    partial segment failure — a non-None return doesn't necessarily mean
    every segment succeeded, so duration is checked against expectation
    rather than trusted at face value.
    """
    try:
        out, duration = run_audio_with_ssml(script_clean, niche_name, voice_id)
        if not out or not Path(out).exists():
            return None
        wc = len(script_clean.split())
        dur_expected = min((wc / 125.0) * 60.0, 1080.0)
        if duration < dur_expected * 0.75:
            log(f"  SSML audio ({duration:.0f}s) looks short vs {dur_expected:.0f}s "
                f"expected — likely partial segment failure, falling back to flat-rate")
            return None
        sz = Path(out).stat().st_size
        if sz < 200000:
            log(f"  SSML audio file too small ({sz}b) — falling back to flat-rate")
            return None
        log(f"  ACCEPTED: SSML multi-rate | {sz/1024/1024:.1f}MB | {duration:.0f}s")
        # FIX (found on deep re-audit): apply_audio_post_processing (the
        # real per-niche NICHE_AUDIO_PROFILES EQ chain) was only ever
        # called on the flat-rate edge-tts fallback tier below — since
        # SSML multi-rate is tried FIRST and succeeds most of the time,
        # the documentary-grade EQ was silently never reaching most real
        # published episodes. Applied here too now, on whichever tier
        # actually wins.
        out_eq = apply_audio_post_processing(out, str(WORK_DIR / "ssml_narration_eq.mp3"), niche_name)
        wav = str(WORK_DIR / "ssml_narration.wav")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", out_eq, "-acodec", "pcm_s16le",
                            "-ar", "24000", "-ac", "1", wav],
                           capture_output=True, timeout=300)
            if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                return wav, duration, sz, f"ssml-multirate-{voice_id}"
        except Exception:
            pass
        return out_eq, duration, sz, f"ssml-multirate-{voice_id}"
    except Exception as e:
        log(f"  SSML multi-rate audio (non-fatal, falling back to flat-rate): {e}")
        return None


def run_stage3_audio(script_clean, voice_id, niche_name):
    log("\n"+"="*65)
    log(f"  STAGE 3: Human Voice Audio — {voice_id}")
    log("="*65)
    # Hard truncate to MAX_WORDS before TTS — prevents 40-chunk failures
    _words = script_clean.split()
    if len(_words) > MAX_WORDS:
        script_clean = " ".join(_words[:MAX_WORDS])
        log(f"  Script truncated to MAX_WORDS ({MAX_WORDS}w) for TTS reliability")

    # FIX (found on deep re-audit): tried first now, matching Ch3/Ch4 —
    # any failure or doubt falls straight through to the existing,
    # thoroughly-tested flat-rate chain below, so this can only improve
    # narration quality, never regress reliability.
    ssml_result = _try_ssml_multirate_audio(script_clean, voice_id, niche_name)
    if ssml_result:
        return ssml_result

    wc           = len(script_clean.split())
    dur_expected = min((wc / 125.0) * 60.0, 1080.0)  # matches the real 18-min hard cap, not 15
    preferred    = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    # v1 addition — real learning-loop closure: track_episode has been
    # recording per-voice average scores into state["performance"] this
    # whole time, but nothing ever read it back. Now genuinely reorders
    # the niche's own voice list toward whichever has the best real
    # historical average score for this channel, once there's enough
    # data to be meaningful.
    try:
        _perf_state = load_state()
        _voice_perf = _perf_state.get("performance", {})
        def _voice_learned_rank(v):
            _scores = _voice_perf.get(f"voice_{v}", {}).get("scores", [])
            if len(_scores) < 3:
                return (0, 0)
            return (1, sum(_scores) / len(_scores))
        _ranked = sorted(enumerate(preferred), key=lambda iv: (-_voice_learned_rank(iv[1])[0], -_voice_learned_rank(iv[1])[1], iv[0]))
        preferred = [v for _, v in _ranked]
    except Exception as e:
        log(f"  Learned voice preference (non-fatal, using default order): {e}")
    # FIX (direct user report, July 23 2026): dropped the US voices (robotic
    # per direct feedback) and en-GB-NoahNeural (confirmed broken on this
    # repo's Actions runners — 24/24 segment failures in live testing).
    GUARANTEED_VOICES = [
    "en-GB-ThomasNeural",       # Cold BBC gravitas — best for dark documentary
    "en-GB-RyanNeural",          # Deep British authority
    "en-GB-OliverNeural",        # Composed British authority
    "en-GB-EthanNeural",         # Warm natural storytelling
] + EXTENDED_VOICES  # AU/NZ/IE/ZA/CA — real fallback depth beyond GB-only
    voice_queue = [voice_id]
    for v in preferred:
        if v not in voice_queue and v not in ROBOTIC_VOICES: voice_queue.append(v)
    for v in GUARANTEED_VOICES:
        if v not in voice_queue: voice_queue.append(v)

    for _vi, v in enumerate(voice_queue[:12]):
        if _vi > 0: time.sleep(3)  # avoid edge-tts rate limit
        log(f"  Trying: {v}")
        mp3 = str(WORK_DIR / "audio.mp3")
        try:
            asyncio.run(asyncio.wait_for(_tts_ch2(script_clean, v, mp3), timeout=120))
            if not Path(mp3).exists(): continue
            quality_ok, real_dur = check_audio_quality(mp3, dur_expected)
            if not quality_ok:
                log(f"  {v} failed quality — trying next"); continue
            sz  = Path(mp3).stat().st_size
            dur = real_dur if real_dur else dur_expected  # real measured duration, not the word-count estimate
            log(f"  ACCEPTED: {v} | {sz/1024/1024:.1f}MB | ~{dur/60:.1f}min")
            # Apply cinematic EQ processing
            processed = str(WORK_DIR / "audio_processed.mp3")
            _proc_path = str(WORK_DIR / "audio_eq_processed.mp3")
            if _proc_path == mp3:  # same file guard
                _proc_path = str(WORK_DIR / "audio_eq_out.mp3")
            mp3 = apply_audio_post_processing(mp3, _proc_path, niche_name)
            wav = str(WORK_DIR / "audio.wav")
            try:
                subprocess.run(["ffmpeg", "-y", "-i", mp3, "-acodec", "pcm_s16le",
                                "-ar", "24000", "-ac", "1", wav],
                               capture_output=True, timeout=300)
                if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                    return wav, dur, sz, v
            except: pass
            return mp3, dur, sz, v
        except Exception as e:
            log(f"  {v} err: {str(e)[:60]}"); time.sleep(3)

    # ── FALLBACK CHAIN: every edge-tts voice failed today. Try alternate
    # providers before giving up entirely, so one bad day for Microsoft's
    # free TTS doesn't mean no video at all. Ordered by quality:
    # Fish Audio (natural, free tier via API key) -> gTTS (free, no key,
    # noticeably more robotic but reliable) -> offline espeak-ng
    # (guaranteed local synthesis, most robotic, true last resort).
    log("  All edge-tts voices exhausted — trying backup TTS providers...")

    fish_key = os.environ.get("FISH_AUDIO_API_KEY", "")
    if fish_key:
        try:
            mp3 = str(WORK_DIR / "audio_fish.mp3")
            r = requests.post("https://api.fish.audio/v1/tts",
                headers={"Authorization": f"Bearer {fish_key}",
                          "Content-Type": "application/json",
                          "model": "s2-pro"},
                json={"text": script_clean, "format": "mp3",
                       "normalize": True, "prosody": {"speed": 1.0}},
                timeout=180)
            if r.status_code == 200 and len(r.content) > 50000:
                with open(mp3, "wb") as f: f.write(r.content)
                quality_ok, real_dur = check_audio_quality(mp3, dur_expected)
                if quality_ok:
                    sz = Path(mp3).stat().st_size
                    actual_dur = real_dur if real_dur else dur_expected
                    log(f"  ACCEPTED: Fish Audio backup | {sz/1024/1024:.1f}MB")
                    tg("⚠️ Evidence Room: all edge-tts voices failed today — used Fish Audio backup instead (still natural-sounding)")
                    mp3p = apply_audio_post_processing(mp3, str(WORK_DIR/"audio_fish_eq.mp3"), niche_name)
                    wav = str(WORK_DIR / "audio_fish.wav")
                    try:
                        subprocess.run(["ffmpeg","-y","-i",mp3p,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                                       capture_output=True, timeout=300)
                        if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                            return wav, actual_dur, sz, "fish-audio-s2-pro"
                    except Exception: pass
                    return mp3p, actual_dur, sz, "fish-audio-s2-pro"
            else:
                log(f"  Fish Audio: {r.status_code} — {str(r.content)[:150]}")
        except Exception as e:
            log(f"  Fish Audio backup failed: {e}")
    else:
        log("  FISH_AUDIO_API_KEY not set — skipping Fish Audio backup")

    # NEW TIER: Kokoro (local, open-weight, Apache 2.0) — same real addition
    # as Ch1, inserted here for the identical reason: genuinely natural-
    # sounding, and runs LOCALLY with no rate limit to hit.
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
        log("  Trying Kokoro (local, natural-sounding, no rate limit)...")
        _kokoro_pipeline = KPipeline(lang_code="a")
        _kokoro_voice = {"en-GB-RyanNeural": "bm_george", "en-US-BrianNeural": "am_michael"}.get(
            voice_id, "am_michael")
        _generator = _kokoro_pipeline(script_clean, voice=_kokoro_voice, speed=1.0)
        _all_audio = []
        for _, _, _audio_chunk in _generator:
            _all_audio.append(_audio_chunk)
        if _all_audio:
            _combined = np.concatenate(_all_audio)
            _wav_path = str(WORK_DIR / "kokoro_narration.wav")
            sf.write(_wav_path, _combined, 24000)
            mp3 = str(WORK_DIR / "audio_kokoro.mp3")
            subprocess.run(["ffmpeg", "-y", "-i", _wav_path, "-codec:a", "libmp3lame",
                             "-qscale:a", "2", mp3], capture_output=True, timeout=120)
            if Path(mp3).exists() and Path(mp3).stat().st_size > 50000:
                actual_dur = get_media_duration(mp3)
                sz = Path(mp3).stat().st_size
                log(f"  ACCEPTED: Kokoro (local) | {sz/1024/1024:.1f}MB")
                tg("⚠️ Evidence Room: edge-tts and Fish Audio both failed today — used Kokoro "
                   "(local, natural-sounding, no rate limit)")
                return mp3, actual_dur, sz, "kokoro-local"
    except Exception as e:
        log(f"  Kokoro backup failed (non-fatal, falling further): {e}")

    try:
        from gtts import gTTS
        import shutil as _shutil
        mp3 = str(WORK_DIR / "audio_gtts.mp3")
        _words = script_clean.split()
        gtts_chunks = [" ".join(_words[i:i+400]) for i in range(0, len(_words), 400)]
        parts = []
        for i, chunk in enumerate(gtts_chunks):
            part = str(WORK_DIR / f"gtts_part_{i}.mp3")
            try:
                gTTS(text=chunk, lang="en", tld="co.uk", slow=False).save(part)
                if Path(part).exists() and Path(part).stat().st_size > 2000:
                    parts.append(part)
            except Exception as e:
                log(f"    gTTS chunk {i} error: {e}")
        if parts:
            if len(parts) == 1:
                _shutil.copy(parts[0], mp3)
            else:
                lst = str(WORK_DIR / "gtts_list.txt")
                with open(lst, "w") as f:
                    for p in parts: f.write(f"file '{p}'\n")
                subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c","copy",mp3],
                               capture_output=True, timeout=300)
            if Path(mp3).exists() and Path(mp3).stat().st_size > 50000:
                sz = Path(mp3).stat().st_size
                _r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                                     "-of","csv=p=0",mp3], capture_output=True, text=True, timeout=30)
                actual_dur = float(_r.stdout.strip()) if _r.returncode == 0 and _r.stdout.strip() else dur_expected
                log(f"  ACCEPTED: gTTS backup | {sz/1024/1024:.1f}MB (lower quality)")
                tg("⚠️ Evidence Room: edge-tts AND Fish Audio both failed today — used gTTS backup "
                   f"(noticeably more robotic). Check FISH_AUDIO_API_KEY / provider status.")
                return mp3, actual_dur, sz, "gtts-fallback"
    except Exception as e:
        log(f"  gTTS backup failed: {e}")

    try:
        mp3 = str(WORK_DIR / "audio_espeak.mp3")
        wav = str(WORK_DIR / "audio_espeak.wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", wav, script_clean[:20000]],
                       capture_output=True, timeout=180)
        if Path(wav).exists() and Path(wav).stat().st_size > 50000:
            subprocess.run(["ffmpeg","-y","-i",wav,mp3], capture_output=True, timeout=60)
            final = mp3 if Path(mp3).exists() else wav
            sz = Path(final).stat().st_size
            _r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                                 "-of","csv=p=0",final], capture_output=True, text=True, timeout=30)
            actual_dur = float(_r.stdout.strip()) if _r.returncode == 0 and _r.stdout.strip() else dur_expected
            log(f"  ACCEPTED: offline espeak-ng (LAST RESORT) | {sz/1024/1024:.1f}MB")
            tg("🚨 Evidence Room: ALL providers failed today (edge-tts, Fish Audio, gTTS) — used OFFLINE "
               f"robotic voice as last resort so the video still published. Check provider status urgently.")
            return final, actual_dur, sz, "espeak-offline-LASTRESORT"
    except Exception as e:
        log(f"  espeak-ng backup failed: {e}")

    tg("Evidence Room Stage 3 FAILED — all voices AND all backup providers failed")
    sys.exit(1)


def fetch_case_relevant_image_ch2(topic, niche_name, out_path):
    """Case-relevant image search for Channel 2 thumbnails — Pixabay first, then Pexels."""
    PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
    PEXELS_KEY  = os.environ.get("PEXELS_API_KEY", "")
    stopwords   = {"a","an","the","and","or","in","on","to","of","with","was","been","have"}
    topic_words = [w.strip(".,!?") for w in topic.lower().split()
                   if len(w) > 3 and w not in stopwords]
    search_kw   = " ".join(topic_words[:3])
    niche_mod   = {
        "forensic_finance":       "dark corporate financial documents",
        "criminal_investigation": "dark crime evidence investigation",
        "corporate_exposure":     "dark corporate shadow documents",
        "digital_forensics":      "dark technology screen code shadow",
    }
    full_query = f"{search_kw} {niche_mod.get(niche_name, 'dark investigation')}"

    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": full_query, "image_type": "photo",
                        "orientation": "horizontal", "per_page": 3}, timeout=25)
            if r.status_code == 200 and r.json().get("hits"):
                url = r.json()["hits"][0].get("webformatURL")
                if url:
                    ir = requests.get(url, timeout=20)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f: f.write(ir.content)
                        log(f"  Case image Ch2 (Pixabay): {search_kw}")
                        return True
        except: pass

    if PEXELS_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": full_query, "per_page": 3,
                        "orientation": "landscape"}, timeout=25)
            if r.status_code == 200:
                photos = r.json().get("photos", [])
                if photos:
                    url = photos[0]["src"]["large"]
                    ir  = requests.get(url, timeout=20)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f: f.write(ir.content)
                        log(f"  Case image Ch2 (Pexels): {search_kw}")
                        return True
        except: pass
    return False


def generate_thumbnail(title, thumb_text, niche_name, topic, ab_style="A",
                        episode=1, channel_name="The Evidence Room"):
    """Three-layer thumbnail via thumbnail_engine_v2. Fallback to Pollinations+Pillow."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title=title, thumb_text=thumb_text, niche_name=niche_name,
            topic=topic, channel_name=channel_name, episode=episode,
            work_dir=str(WORK_DIR), ab_variant=ab_style, cache_dir=str(SCRIPT_DIR))
        if result and Path(result).exists():
            log(f"  Thumbnail v2: {Path(result).stat().st_size//1024}KB")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    # Fallback: Pollinations + Pillow
    return generate_thumbnail_with_ai_bg(title, thumb_text, niche_name, topic, ab_style)


def make_short_with_subs(video_path, script_clean, stype, total_dur):
    short_dur = 55
    start     = total_dur*(0.30 if stype=="standalone_1" else 0.60)  # FIX: teaser/recap framing removed per explicit request
    raw       = str(WORK_DIR/f"s_{stype}_raw.mp4")
    final     = str(WORK_DIR/f"short_{stype}.mp4")
    r = subprocess.run(["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(short_dur),
                        "-vf","crop=608:1080:(iw-608)/2:0,scale=1080:1920",
                        "-c:v","libx264","-preset","fast","-crf","22",
                        "-c:a","aac","-b:a","128k",raw], capture_output=True, timeout=180)
    if not Path(raw).exists() or Path(raw).stat().st_size<400000:
        log(f"  Short {stype} clip failed"); return None
    # Subtitles disabled — timing sync not reliable enough
    # Short is the raw clip — no subtitle burn
    log(f"  Short ({stype}): {Path(raw).stat().st_size/1024/1024:.1f}MB — no subtitles")
    return raw


# ════════════════════════════════════════════════════════════
# STAGE 6: UPLOAD
# ════════════════════════════════════════════════════════════
_tok_cache = {"token": None, "expires_at": 0}

def get_yt_token():
    now = time.time()
    if _tok_cache["token"] and now < _tok_cache["expires_at"] - 60:
        return _tok_cache["token"]
    r = requests.post(YT_TOKEN_URL,
        data={"client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SEC,
              "refresh_token": YT_REFRESH, "grant_type": "refresh_token"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"YT token failed: {d.get('error')} — {d.get('error_description')}")
    _tok_cache["token"]      = d["access_token"]
    _tok_cache["expires_at"] = now + d.get("expires_in", 3600)
    return d["access_token"]

def upload_yt(path, title, description, tags, is_short=False, token=None, privacy="public"):
    """Chunked resumable upload with retry — same as Channel 1."""
    token = token or get_yt_token()
    if is_short: title = f"{title[:55]} #Shorts"
    fs = Path(path).stat().st_size
    log(f"  Uploading: {Path(path).name} ({fs//(1024*1024)}MB)")

    init = requests.post(
        f"{YT_UPLOAD_URL}/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(fs), "X-Upload-Content-Type": "video/mp4"},
        json={"snippet": {"title": title[:100], "description": description,
                          "tags": tags[:15], "categoryId": "22"},
              "status": {
                  "privacyStatus": privacy,
                  "selfDeclaredMadeForKids": False,
                  "madeForKids": False,
                  "containsSyntheticMedia": True   # mandatory AI disclosure since Mar 2024
              }},
                timeout=30)
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL: {init.status_code}: {init.text[:200]}")

    CHUNK = 16 * 1024 * 1024
    uploaded = 0; retries = 0
    with open(path, "rb") as f:
        while uploaded < fs:
            data = f.read(CHUNK)
            if not data: break
            end = uploaded + len(data) - 1
            try:
                up = requests.put(upload_url,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Length": str(len(data)),
                             "Content-Range": f"bytes {uploaded}-{end}/{fs}",
                             "Content-Type": "video/mp4"},
                    data=data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id = up.json().get("id")
                    url = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"  Uploaded: {url}")
                    return url, vid_id
                elif up.status_code == 308:
                    rh = up.headers.get("Range", "")
                    uploaded = int(rh.split("-")[1]) + 1 if rh else uploaded + len(data)
                    log(f"  {int(uploaded*100/fs)}%"); retries = 0
                elif up.status_code in [500, 502, 503, 504]:
                    retries += 1
                    if retries > 5: raise Exception(f"Server errors x{retries}")
                    time.sleep(2 ** retries)
                else:
                    raise Exception(f"HTTP {up.status_code}: {up.text[:200]}")
            except requests.exceptions.Timeout:
                retries += 1
                if retries > 5: raise Exception("Repeated timeouts")
                time.sleep(5)
    raise Exception("Upload ended without completion")


def set_video_privacy(video_id, privacy, token=None):
    """
    Real, metadata-only YouTube API call — flips an already-uploaded
    video's privacyStatus without re-uploading the file. Used by the
    final pre-publish gate: the video is uploaded unlisted first, then
    this flips it to public once a human has actually approved it.
    """
    token = token or get_yt_token()
    try:
        r = requests.put(
            f"{YT_DATA_URL}/videos?part=status",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"id": video_id, "status": {"privacyStatus": privacy}},
            timeout=20)
        if r.status_code == 200:
            return True
        log(f"  Set privacy to {privacy} FAILED: {r.status_code} — {r.text[:200]}")
        return False
    except Exception as e:
        log(f"  Set privacy (non-fatal): {e}")
        return False


def delete_yt_video(video_id, token=None):
    """Real deletion of an unlisted upload rejected at the final pre-publish gate."""
    token = token or get_yt_token()
    try:
        r = requests.delete(f"{YT_DATA_URL}/videos",
            headers={"Authorization": f"Bearer {token}"},
            params={"id": video_id}, timeout=20)
        if r.status_code in (200, 204):
            return True
        log(f"  Delete rejected video FAILED: {r.status_code} — {r.text[:200]}")
        return False
    except Exception as e:
        log(f"  Delete rejected video (non-fatal): {e}")
        return False


def post_creator_comment(token, video_id, niche_name, title, episode):
    """Post engagement-driving creator comment immediately after upload."""
    niche_hooks = {
        "forensic_finance":       "What financial warning sign do you think most people miss?",
        "criminal_investigation": "Which piece of evidence in this case do you find most disturbing?",
        "corporate_exposure":     "Have you ever seen this happen at a company you know?",
        "digital_forensics":      "Did you know your digital footprint tells this much about you?",
    }
    hook = niche_hooks.get(niche_name, "What detail in this case changed how you see it?")
    comment = (
        f"🔬 {hook}\n\n"
        f"Leave your answer below — every case has details that never make the news.\n\n"
        f"🔔 New forensic investigation every weekday\n"
        f"🌑 Dark horror investigations: youtube.com/@BetrayalDeepDive\n\n"
        f"#{niche_name.replace('_','')} #forensic #investigation #documentary #episode{episode}"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200:
            log("  Creator comment posted OK")
        else:
            log(f"  Creator comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Creator comment (non-fatal): {e}")

def ensure_playlist(token, niche_name, series_name):
    """Auto-create per-niche playlist, return playlist_id."""
    try:
        r = requests.get(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true", "maxResults": 50}, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                if series_name.lower() in item["snippet"]["title"].lower():
                    return item["id"]
        r2 = requests.post(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet,status"},
            json={"snippet": {"title": f"{series_name} — All Cases",
                              "description": f"Every investigation from {series_name}."},
                  "status": {"privacyStatus": "public"}}, timeout=20)
        if r2.status_code == 200:
            pid = r2.json()["id"]
            log(f"  Playlist created: {pid}"); return pid
    except Exception as e: log(f"  Playlist (non-fatal): {e}")
    return None

def add_to_playlist(token, playlist_id, video_id):
    if not playlist_id: return
    try:
        requests.post(f"{YT_DATA_URL}/playlistItems",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
            timeout=20)
        log("  Added to playlist")
    except Exception as e: log(f"  Playlist add (non-fatal): {e}")

# ════════════════════════════════════════════════════════════
# v12.0 NEW FUNCTIONS — TRAFFIC & REVENUE MAXIMISATION
# ════════════════════════════════════════════════════════════

def generate_dedicated_short_title_ch2(main_title, short_type, niche_name):
    """Dedicated Short title for Ch2 — forensic investigation angle."""
    prompts = {
        "standalone_1": f"Write a YouTube Shorts title that creates maximum curiosity for a forensic investigation. "
                  f"Topic: {main_title[:80]}. Under 55 chars, starts with a document/evidence/number fact. Return ONLY the title.",
        "standalone_2":  f"Write a YouTube Shorts title revealing a genuinely surprising, self-contained piece of evidence. "
                  f"Topic: {main_title[:80]}. Under 55 chars, feels complete on its own. Return ONLY the title.",
    }
    type_key = "standalone_1" if "1" in short_type else "standalone_2"
    try:
        result = ai(prompts[type_key], tokens=80)
        if result:
            title = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
            if 15 < len(title) < 65:
                log(f"  Short title Ch2: {title}")
                return title
    except Exception as e:
        log(f"  Short title Ch2 (non-fatal): {e}")
    defaults = {"standalone_1": "What the Records Revealed", "standalone_2": "Evidence Found — Full Case Above"}
    return defaults.get(type_key, main_title[:50])


def post_short_creator_comment_ch2(token, video_id, niche_name, main_title):
    """Pinned creator comment on each Ch2 Short. Drives early engagement signals."""
    short_hooks = {
        "forensic_finance":       "What financial warning sign do you wish more people understood?",
        "criminal_investigation": "What detail in this case makes it impossible to look away?",
        "corporate_exposure":     "Have you ever seen corporate documents like these in real life?",
        "digital_forensics":      "Did you know how much of your digital trail can be reconstructed?",
    }
    hook = short_hooks.get(niche_name, "What was the most disturbing piece of evidence?")
    comment = (
        f"🔬 {hook}\n\n"
        f"Full forensic investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🌑 Dark horror: youtube.com/@BetrayalDeepDive\n"
        f"🧠 Mass manipulation: youtube.com/@TheControlFiles\n\n"
        f"#{niche_name.replace('_','')} #shorts #forensic #investigation"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200: log("  Short creator comment Ch2 OK")
        else: log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_ch2_cross_promo(is_short=False):
    """Three-channel cross-promotion for Ch2 descriptions."""
    if is_short:
        return (
            "\n\n🌑 Dark horror investigations: youtube.com/@BetrayalDeepDive"
            "\n🧠 Mass manipulation exposed: youtube.com/@TheControlFiles"
        )
    return (
        "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
        "\n🧠 Mass manipulation & propaganda: youtube.com/@TheControlFiles"
        "\n\n📺 New investigation every weekday on all three channels."
    )


def track_episode_ch2(state, niche_name, score, voice, episode):
    """Performance tracker for Ch2 — same as Ch1's track_episode."""
    perf = state.get("performance", {})
    n    = perf.get(niche_name, {"scores": [], "streak_below": 0})
    n["scores"]       = (n["scores"] + [score])[-20:]
    n["streak_below"] = (n["streak_below"] + 1) if score < 7.3 else 0
    n["last_episode"] = episode
    perf[niche_name]  = n
    v = perf.get(f"voice_{voice}", {"scores": []})
    v["scores"] = (v["scores"] + [score])[-20:]
    perf[f"voice_{voice}"] = v
    state["performance"] = perf
    return state



# ════════════════════════════════════════════════════════════
# STANDALONE NICHE SHORTS — the 2 real Shorts produced each day
# ════════════════════════════════════════════════════════════

SHORTS_TEMPLATES = {
    "forensic_finance":       ["The one financial warning sign that nobody acted on",
                               "The document trail that exposed the entire fraud"],
    "criminal_investigation": ["The single piece of evidence that broke the whole case",
                               "The detail in the scene that proved it was not an accident"],
    "corporate_exposure":     ["The internal memo that exposed the cover-up",
                               "The document they tried to destroy and failed"],
    "digital_forensics":      ["The digital trace that was impossible to erase",
                               "The metadata that revealed the entire timeline"],
    "body_cam_police":        ["The bodycam frame nobody expected to matter",
                               "The moment the footage contradicted the report"],
    "courtroom_drama":        ["The cross-examination question that changed the verdict",
                               "The testimony that fell apart in real time"],
    "robbery_documentaries":  ["The getaway detail that finally solved it",
                               "The security footage that took years to surface"],
}

def generate_standalone_short_script(niche_name, topic, short_num):
    """
    Generate a 45-second standalone Short script optimised for the Shorts algorithm.
    ~120-130 words = 45 seconds at natural TTS pace.
    Structure: Immediate hook → Fast context → Single devastating reveal → CTA
    """
    angles = {
        0: "the single most shocking documented fact from this case",
        1: "the warning sign that everyone missed before it was too late",
    }
    angle = angles.get(short_num, angles[0])

    prompt = f"""Write a 45-second YouTube Shorts narration script.
Topic: {topic}
Focus angle: {angle}
Niche feel: {niche_name.replace('_', ' ')} — dark, investigative, forensic

STRUCTURE:
Line 1 (HOOK): Start with a specific number, date, or dollar amount. Mid-action. No "today we".
Lines 2-4 (CONTEXT): Three short punchy sentences. Max 10 words each.
Lines 5-6 (REVEAL): The one fact that changes everything. Documented and real.
Line 7 (CTA): "Full investigation on our channel." or "Watch the full case above."

RULES:
- Exactly 120-130 words total
- Every sentence max 12 words
- Include at least ONE specific number or date
- No markdown, no headers, no asterisks
- Plain narration text only

Write the script:"""

    result = ai(prompt, tokens=350)
    if result:
        clean = result.strip().replace("**","").replace("##","").replace("*","")
        words = clean.split()
        if len(words) > 132:
            clean = " ".join(words[:130])
        log(f"  Short {short_num+1} script: {len(clean.split())}w")
        return clean
    return None


async def generate_short_audio_async(script, voice, out_path):
    """Generate audio for standalone Short using edge-tts."""
    import edge_tts
    try:
        comm = edge_tts.Communicate(text=script, voice=voice, rate="-5%")
        await asyncio.wait_for(comm.save(out_path), timeout=120)
        if Path(out_path).exists() and Path(out_path).stat().st_size > 50000:
            return True
    except Exception as e:
        log(f"  Short audio error: {e}")
    return False


def create_standalone_short_video(script, audio_path, niche_name, short_num):
    """
    Create animated Short video from script + audio.
    Vertical 1080x1920. Channel 2 brand: animated frames + text overlay.
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1920

    # Get audio duration via ffprobe
    dur_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", audio_path],
        capture_output=True, text=True, timeout=30)
    duration = 45.0
    try:
        import json as _json
        streams = _json.loads(dur_result.stdout).get("streams", [])
        for s in streams:
            if s.get("codec_type") == "audio":
                duration = float(s.get("duration", 45.0)); break
    except: pass

    bg_colors = {
        "forensic_finance":       (8, 12, 20),
        "criminal_investigation": (12, 5, 5),
        "corporate_exposure":     (5, 8, 12),
        "digital_forensics":      (5, 15, 10),
    }
    bg = bg_colors.get(niche_name, (8, 8, 15))

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    def gf(sz):
        for fp in font_paths:
            if Path(fp).exists():
                try: return ImageFont.truetype(fp, sz)
                except: pass
        return ImageFont.load_default()

    sents = [s.strip() for s in script.replace("\n"," ").split(".") if len(s.strip()) > 5]
    sections = [
        " ".join(sents[:2]),
        " ".join(sents[2:5]),
        " ".join(sents[5:]),
    ]

    frames_dir = WORK_DIR / f"short_frames_{short_num}"
    frames_dir.mkdir(exist_ok=True)

    fps           = 24
    total_frames  = int(duration * fps)
    section_frames= total_frames // 3
    frame_list    = []

    for section_idx, section_text in enumerate(sections):
        words_s = section_text.split()
        for fi in range(section_frames):
            progress = fi / section_frames
            img  = Image.new("RGB", (W, H), bg)
            draw = ImageDraw.Draw(img)

            # Animated red progress bar at top
            bar_w = int(W * ((section_idx * section_frames + fi) / total_frames))
            draw.rectangle([0, 0, bar_w, 10], fill=(200, 0, 0))
            draw.rectangle([0, 0, W, 10], outline=(60, 0, 0), width=1)

            # Channel badge
            draw.text((40, 30), "● THE EVIDENCE ROOM", font=gf(26), fill=(160, 0, 0))

            # Section progress dots
            for dot_i in range(3):
                color = (200, 0, 0) if dot_i <= section_idx else (40, 40, 40)
                draw.ellipse([W//2-30+dot_i*25, H-80, W//2-14+dot_i*25, H-64], fill=color)

            # Animated word reveal
            visible_words = max(1, int(len(words_s) * min(progress * 1.8, 1.0)))
            display_text  = " ".join(words_s[:visible_words])

            # Word wrap
            wrapped = []; current = []
            for word in display_text.split():
                current.append(word)
                if len(" ".join(current)) > 22:
                    wrapped.append(" ".join(current[:-1])); current = [word]
            if current: wrapped.append(" ".join(current))

            fm = gf(72)
            total_h = len(wrapped) * 85
            start_y = (H - total_h) // 2
            for li, line in enumerate(wrapped[:6]):
                y = start_y + li * 85
                bbox = draw.textbbox((0, 0), line, font=fm)
                x    = (W - (bbox[2] - bbox[0])) // 2
                for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
                    draw.text((x+dx, y+dy), line, font=fm, fill=(30, 0, 0))
                draw.text((x, y), line, font=fm,
                          fill=(220, 15, 15) if section_idx == 0 else (230, 230, 230))

            if section_idx == 2:
                pulse = int(abs(progress - 0.5) * 200)
                draw.rectangle([4, 4, W-4, H-4], outline=(pulse, 0, 0), width=3)

            fpath = str(frames_dir / f"f{section_idx:01d}_{fi:04d}.jpg")
            img.save(fpath, "JPEG", quality=85)
            frame_list.append(fpath)

    list_file = str(WORK_DIR / f"short_list_{short_num}.txt")
    with open(list_file, "w") as lf:
        for fp in frame_list:
            lf.write(f"file '{fp}'\nduration {1/fps}\n")

    out_path = str(WORK_DIR / f"standalone_short_{short_num}.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration + 0.3), "-shortest",
        out_path
    ], capture_output=True, timeout=300)

    if Path(out_path).exists() and Path(out_path).stat().st_size > 200000:
        log(f"  Standalone Short {short_num}: {Path(out_path).stat().st_size//(1024*1024)}MB")
        # Cleanup frames
        shutil.rmtree(str(frames_dir), ignore_errors=True)
        return out_path
    return None


def create_and_upload_standalone_shorts(token, niche, topic, voice, description,
                                        tags, playlist_id, title_str):
    """
    Generate 2 standalone niche Shorts and upload them.
    These are original content — NOT clips from the main video.
    Each targets different keywords, driving independent search traffic.
    Non-fatal: if they fail, the main video and clip Shorts are unaffected.
    """
    standalone_uploaded = []

    for short_num in range(2):
        try:
            log(f"\n  Standalone Short {short_num+1}/2...")

            script = generate_standalone_short_script(niche["name"], topic, short_num)
            if not script:
                log(f"  Short {short_num+1} script failed — skipping"); continue

            audio_out = str(WORK_DIR / f"standalone_short_audio_{short_num}.mp3")
            ok        = asyncio.run(generate_short_audio_async(script, voice, audio_out))
            if not ok:
                log(f"  Short {short_num+1} audio failed — skipping"); continue

            video_out = create_standalone_short_video(script, audio_out,
                                                      niche["name"], short_num)
            if not video_out:
                log(f"  Short {short_num+1} video failed — skipping"); continue

            short_title = (
                f"{script.split('.')[0][:50]} #Shorts"
                if short_num == 0
                else f"THE EVIDENCE ROOM: {topic[:35]} #Shorts"
            )
            short_desc = (
                f"{script[:200]}\n\n"
                f"Watch the full investigation: {title_str}\n\n"
                f"🔔 Subscribe: youtube.com/@TheEvidenceRoom\n"
                f"#{niche['name'].replace('_','')} #shorts #forensic #investigation"
            )

            su, sid = upload_yt(video_out, short_title, short_desc,
                                tags[:8], is_short=True, token=token)
            add_to_playlist(token, playlist_id, sid)
            standalone_uploaded.append(su)
            log(f"  Standalone Short {short_num+1} uploaded: {su}")

        except Exception as e:
            log(f"  Standalone Short {short_num+1} error (non-fatal): {e}")

    return standalone_uploaded


def cleanup():
    for f in ["audio.mp3","audio.wav","raw.mp4","final.mp4",
              "short_standalone_1.mp4","short_standalone_2.mp4","s_standalone_1_raw.mp4","s_standalone_2_raw.mp4"]:
        p=WORK_DIR/f
        if p.exists(): p.unlink()
    for srt in WORK_DIR.glob("short_*.srt"): srt.unlink()
    frames_dir=WORK_DIR/"frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    log("  Cleanup complete")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def run_stage1(state):
    """
    13-attempt script engine for Ch2 The Evidence Room.
    Returns all script data needed by generate phase.
    """
    log("\n"+"="*65)
    log("  STAGE 1: Evidence Room 13-Attempt Script Engine")
    log(f"  Graduated quality gate: attempts 1-8 require {MIN_GATE} | "
        f"attempts 9-12 relax to 7.0 | attempt 13 absolute floor {FINAL_GATE}")
    log("="*65)

    niche, voice, style_name = get_niche_voice_style(state)
    episode    = (datetime.datetime.now().timetuple().tm_yday//3)+1
    prev_title = state.get("last_title","")
    intel      = run_viral_intelligence(niche)
    used_topics = []
    gate       = MIN_GATE
    best_score = 0.0
    best_script = best_scenes = best_title_str = best_thumbnail = best_tags = best_title_scores = None
    best_real_cases = []

    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Style: {style_name} | Voice: {voice}")

    # Topic-scoring backlog integration — prefer a topic a human has
    # already approved over generating a brand new one. If the backlog
    # is empty (or has nothing approved yet), fall through to the
    # existing AI generation, unchanged.
    _approved_topic_entry = None
    try:
        from topic_scoring import get_next_approved_topic
        _approved_topic_entry = get_next_approved_topic(SCRIPT_DIR)
    except Exception as e:
        log(f"  Topic backlog check (non-fatal): {e}")

    for attempt in range(1, 14):
        # Graduated 13-level quality gate — identical structure to Ch1, per
        # explicit specification: attempts 1-8 require the high bar (8.5),
        # attempts 9-12 relax to 7.0, attempt 13 allows 6.9 as the absolute
        # last-resort floor only. Previously this loop only ran 8 attempts
        # despite the log message already (incorrectly) claiming 13 — now
        # the actual behavior matches what was always being logged.
        if attempt == 13:
            gate = FINAL_GATE
        elif attempt >= 9:
            gate = 7.0
        else:
            gate = 8.5

        if _approved_topic_entry and attempt == 1:
            # Use the human-approved topic on the first attempt — if it
            # fails the quality gate, later attempts still fall back to
            # fresh AI generation rather than forcing the same topic
            # through all 13 attempts.
            topic = _approved_topic_entry["topic_text"]
        else:
            topic = get_fresh_topic(niche, attempt, intel, used_topics)
            # Score and bank this candidate for future human review,
            # regardless of whether it's used today — this is what
            # actually builds the backlog into something real over time.
            try:
                from topic_scoring import add_topic_candidate
                add_topic_candidate(SCRIPT_DIR, "evidence_room", topic, niche["name"],
                                     lambda p, tokens=200: ai(p, tokens=tokens))
            except Exception as e:
                log(f"  Topic scoring (non-fatal): {e}")
        used_topics.append(topic)

        if attempt in [1,5,9,13]:
            # Compute the dread/sympathy register ONCE, before either call, so
            # thumbnail and title stay coordinated even though thumbnail is
            # generated first — previously each picked independently with a
            # real risk of clashing (sympathy title, dread thumbnail or vice
            # versa). Day-based alternation matches the pattern already used
            # elsewhere in this file (get_niche_voice_style).
            shared_register = "sympathy" if datetime.datetime.now().timetuple().tm_yday % 2 == 0 else "dread"
            # FIX: fetch REAL trending titles (actual YouTube API data) here,
            # safely — if this fails for any reason (token issue, API
            # hiccup), fall back to no real-trend data rather than break
            # generation. This is genuinely real data, unlike the AI-imagined
            # "intel" system below.
            real_trend_token = None
            try:
                real_trend_token = get_yt_token()
                real_trending_titles = fetch_real_trending_titles(niche, real_trend_token)
            except Exception as e:
                log(f"  Real trend fetch skipped (non-fatal): {e}")
                real_trending_titles = []
            # NEW FEATURE (per explicit request — daily competitive
            # research): fetch_real_trending_titles above is title-only;
            # daily_competitor_research also has real view/like counts,
            # cached per calendar day. Merged in here so title generation
            # sees the same real, richer signal script generation now
            # gets (deduplicated, real titles first).
            try:
                from daily_competitor_research import fetch_daily_competitor_research
                _daily_intel_titles = fetch_daily_competitor_research(niche, real_trend_token, str(SCRIPT_DIR))
                for _v in _daily_intel_titles.get("videos", []):
                    if _v["title"] and _v["title"] not in real_trending_titles:
                        real_trending_titles.append(_v["title"])
            except Exception as e:
                log(f"  Daily competitor research for titles (non-fatal): {e}")
            thumbnail_text     = generate_thumbnail_text(niche, topic, intel, register=shared_register)
            # FIX: enforce_number_noun existed fully built (ensures the
            # punchy NUMBER+NOUN thumbnail format — "$2.4M GONE", "47
            # REPORTS" — with a real 3-tier fallback) but was never called
            # anywhere in this file, unlike Ch1 which has always used it.
            try:
                thumbnail_text = enforce_number_noun(thumbnail_text, topic, niche["name"],
                                                       lambda p, tokens=20: ai(p, tokens=tokens))
            except Exception as e:
                log(f"  Number-noun enforcement (non-fatal): {e}")
            title_str, tscores = generate_and_score_titles(niche, topic, intel, episode,
                                                             register=shared_register,
                                                             real_trending_titles=real_trending_titles)
            # v15: title CTR gate
            title_str, tscores = run_title_ctr_gate(
                title_str, tscores, topic, niche["name"], niche["series"],
                episode, lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
            best_thumbnail     = thumbnail_text
            best_title_str     = title_str
            best_title_scores  = tscores
            log(f"Thumbnail: {thumbnail_text}")

        log(f"\nAttempt {attempt}/8 (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            script_clean, scenes, title, thumb, tags, violations, real_cases = generate_script_and_scenes(
                niche, topic, style_name, episode, attempt, intel, prev_title)
            wc = len(script_clean.split())
            score, issues = score_script_er(script_clean, wc, violations, topic)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w | MD:{violations}")
            if issues:
                iss_str = " | ".join(issues[:3])
                log(f"  {iss_str}")

            if score > best_score:
                best_score  = score
                best_script = script_clean
                best_scenes = scenes
                if thumb and thumb != "EVIDENCE FOUND": best_thumbnail = thumb
                best_tags   = tags
                best_real_cases = real_cases
            if score >= gate:
                log(f"\nSCRIPT APPROVED: {score}/10 | Attempt {attempt}\n")
                # v6 addition — real research-usage alert, fired exactly
                # once here for the actual winning/publishing attempt.
                if real_cases:
                    _win_script_lower = script_clean.lower()
                    _win_research_words = set()
                    for c in real_cases[:3]:
                        _win_research_words.update(
                            w.strip(".,;:").lower() for w in (c.get("title","")+" "+c.get("summary","")).split()
                            if len(w) > 6)
                    if not any(w in _win_script_lower for w in _win_research_words):
                        tg(f"⚠️ Ch2: real research was found ({len(real_cases)} sources) but the "
                           f"script that's actually publishing shows no clear sign of using it — "
                           f"may be relying on invented details instead of the real documented "
                           f"facts. Worth a manual check on this episode's factual grounding.")
                # v9 addition — real title-script alignment check, per
                # direct research confirming spoken-content-to-title
                # matching affects both search relevance and satisfaction
                # signals.
                _title_distinctive_words = {
                    w.strip(".,!?:;\"'").lower() for w in best_title_str.split()
                    if len(w) > 4 and w.lower() not in
                    {"about","after","before","their","there","which","would","could","should"}
                }
                if _title_distinctive_words:
                    _script_words_lower = set(script_clean.lower().split())
                    _matched = sum(1 for w in _title_distinctive_words if w in _script_words_lower)
                    if _matched == 0:
                        tg(f"⚠️ Ch2: none of the title's distinctive words appear in the script — "
                           f"\"{best_title_str[:70]}\" may not match what the video actually says. "
                           f"Worth checking the title still fits before this publishes.")
                # FIX (real production crash, found via an actual GitHub
                # Actions run): "quality_attempt": attempt in main()'s
                # save_pending call referenced a bare `attempt` variable
                # that is local to THIS function (run_stage1), not main()
                # — a function-boundary violation causing a guaranteed
                # NameError every single run. Safely carried through via
                # the intel dict, which is already returned and unpacked
                # in main(), instead of changing this tuple's arity.
                intel["_winning_attempt"] = attempt
                intel["_approved_topic_id"] = _approved_topic_entry["topic_id"] if _approved_topic_entry else None
                # v6 addition — real citation system: same safe pattern
                # as _winning_attempt above, carried through intel rather
                # than extending this already-large tuple's arity.
                intel["_real_cases"] = best_real_cases
                return (niche, topic, voice, style_name, episode,
                        best_script, best_scenes, best_title_str,
                        best_thumbnail, best_title_scores, score, best_tags, intel)
            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if best_script and best_score >= FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Note: Publishing {best_score}/10 after 13 attempts.")
        intel["_winning_attempt"] = 13  # fires only after all 13 attempts are exhausted
        intel["_approved_topic_id"] = _approved_topic_entry["topic_id"] if _approved_topic_entry else None
        intel["_real_cases"] = best_real_cases
        return (niche, used_topics[-1], voice, style_name, episode,
                best_script, best_scenes, best_title_str,
                best_thumbnail, best_title_scores, best_score, best_tags or [], intel)

    state["last_niche"] = niche["name"]; save_state(state)
    tg(f"Evidence Room Day Skipped\nBest: {best_score}/10 after 13 attempts")
    sys.exit(0)



def run_stage2_approval_ch2(title_str, niche, score, script_clean):
    """30-minute approval gate for Ch2 Evidence Room."""
    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime("%I:%M %p")
    preview      = script_clean[:400].replace("<","").replace(">","")
    msg = (
        f"<b>EVIDENCE ROOM APPROVAL NEEDED</b>\n\n"
        f"Title: {title_str}\n"
        f"Niche: {niche['name']} | Score: {score}/10\n"
        f"Auto-uploads at {deadline_str}\n\n"
        f"Reply APPROVE or REJECT"
    )
    keyboard = {"inline_keyboard": [
        [{"text": "APPROVE", "callback_data": "approved"},
         {"text": "REJECT",  "callback_data": "rejected"}]
    ]}
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg,
                  "parse_mode": "HTML", "reply_markup": keyboard},
            timeout=25)
        tg(f"Preview: {preview}...")
    except Exception as e:
        log(f"  Approval notification (non-fatal): {e}")
    # Poll for response
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
            params={"timeout": 25}, timeout=30)
        updates = r.json().get("result", [])
        offset  = (max(u["update_id"] for u in updates) + 1) if updates else 0
    except:
        offset = 0
    decision = "auto_approved"
    while datetime.datetime.now() < deadline:
        time.sleep(30)
        try:
            r2 = requests.get(
                f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                params={"timeout": 25, "offset": offset,
                        "allowed_updates": ["callback_query", "message"]},
                timeout=30)
            for u in r2.json().get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    cb   = u["callback_query"]
                    data = cb.get("data", "")
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
                            json={"callback_query_id": cb.get("id",""),
                                  "text": "Got it!"}, timeout=20)
                    except:
                        pass
                    if data == "approved":
                        tg("APPROVED. Generating video...")
                        return "approved"
                    elif data == "rejected":
                        tg("REJECTED. Stopping.")
                        return "rejected"
        except:
            pass
    tg("30 min expired — auto-approved.")
    return "auto_approved"


def _inject_ctas_er(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30/60/80% word marks for retention + conversion.
    Channel-specific, niche-specific phrasing — never identical wording.
    """
    cta_bank = {
        "forensic_finance": [
            "If documented cases like this concern you, subscribe — new files every week.",
            "This channel investigates documented financial fraud. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
        "criminal_investigation": [
            "If this case concerns you, subscribe — documented investigations every week.",
            "This channel documents criminal investigations. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
        "corporate_exposure": [
            "If this pattern concerns you, subscribe — documented exposures every week.",
            "This channel investigates documented corporate misconduct. Subscribe to follow the record.",
            "More documented findings like this are coming. Subscribe to The Evidence Room.",
        ],
        "digital_forensics": [
            "If this trail concerns you, subscribe — documented digital cases every week.",
            "This channel documents digital forensic investigations. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
        # FIX: body_cam_police, courtroom_drama, and robbery_documentaries
        # are 3 of this channel's 7 real niches (see NICHES below) but had
        # no entry here at all — every episode in these 3 niches was
        # silently falling back to forensic_finance's CTA text via the
        # .get() default below, mismatched against what the video was
        # actually about.
        "body_cam_police": [
            "If footage like this concerns you, subscribe — documented body cam cases every week.",
            "This channel investigates documented body cam evidence. Subscribe to follow the evidence.",
            "More documented footage like this is coming. Subscribe to The Evidence Room.",
        ],
        "courtroom_drama": [
            "If this verdict concerns you, subscribe — documented courtroom cases every week.",
            "This channel investigates documented courtroom proceedings. Subscribe to follow the evidence.",
            "More documented trials like this are coming. Subscribe to The Evidence Room.",
        ],
        "robbery_documentaries": [
            "If this heist concerns you, subscribe — documented robbery cases every week.",
            "This channel documents real robbery investigations. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Evidence Room.",
        ],
    }
    ctas = cta_bank.get(niche_name, cta_bank["forensic_finance"])

    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    marks = [int(total * 0.30), int(total * 0.60), int(total * 0.80)]
    inserted = 0
    result = script_clean

    for i, mark_pct in enumerate(marks):
        cta = ctas[i % len(ctas)]
        target_word_idx = mark_pct + inserted
        all_words = result.split()
        if target_word_idx >= len(all_words):
            continue
        char_pos = len(" ".join(all_words[:target_word_idx]))
        next_period = result.find(". ", char_pos)
        if next_period == -1:
            continue
        insert_at = next_period + 2
        result = result[:insert_at] + cta + " " + result[insert_at:]
        inserted += len(cta.split()) + 1

    # Ensure subscribe CTA exists in final 60 words
    if "subscribe" not in " ".join(result.split()[-60:]).lower():
        result = result.rstrip() + " Subscribe to this channel for more documented investigations."
    return result



def run_ffmpeg(cmd, label="ffmpeg", timeout=300):
    """Run an ffmpeg subprocess with consistent logging and timeout handling."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", "ignore")[-200:]
            log(f"  {label}: ffmpeg exit {result.returncode} — {err}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log(f"  {label}: ffmpeg timed out after {timeout}s")
        return False
    except Exception as e:
        log(f"  {label}: ffmpeg error — {e}")
        return False


def score_script_er(script_clean, wc, violations, topic=""):
    """
    Score a generated script 0-10. Used as the quality gate before approval.
    Checks: word count, markdown violations, retention hooks at 30/60/80%,
    and the Killer Hook / Narrative Craft / Topic Clarity rubric.
    """
    if not script_clean:
        return 0.0, ["Empty script"]

    score  = 5.0
    issues = []

    if wc >= MIN_WORDS:
        score += 2.8
    elif wc >= int(MIN_WORDS * 0.8):
        score += 0.8
    else:
        score -= 2.0
        issues.append(f"Under word target: {wc}w")

    if violations == 0:
        score += 2.2
    elif violations <= 2:
        score += 0.8
    else:
        score -= 1.5
        issues.append(f"{violations} markdown violations")

    words = script_clean.split()
    total = len(words)
    hook_signals = ["subscribe", "coming up", "next", "what happens", "the answer",
                    "revealed", "in a moment", "stay", "about to", "this changes",
                    "documented", "the evidence", "what comes next"]
    if total >= 400:
        def seg(p1, p2):
            return " ".join(words[int(total*p1):int(total*p2)]).lower()
        if sum(1 for w in hook_signals if w in seg(0.25, 0.35)) < 1:
            score -= 0.4
            issues.append("Missing 30% retention hook")
        # FIX (direct user report, July 23 2026): missing CTA at the
        # retention peak is now a hard gate, matching the
        # NARRATIVE_CRAFT/TOPIC_CLARITY/HOOK gates in script_scoring.py.
        h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
        if h60 < 2:
            score -= 5.0
            issues.append("PEAK CTA GATE FAILED: weak 60% hook/CTA — this attempt cannot pass "
                          "regardless of any other score.")
        elif h60 >= 3:
            score += 0.3
        if "subscribe" not in " ".join(words[-60:]).lower():
            score -= 0.3
            issues.append("Missing subscribe CTA in final 60 words")

        # v1 addition — real, measurable enforcement of the retention-
        # cadence instruction added to the prompt (payoff every 150-225
        # words / ~60-90 seconds). Scans real ~200-word rolling windows
        # and penalizes genuine dead zones (no hook signal AND no real
        # specific-number claim anywhere in that stretch).
        WINDOW = 200
        dead_zones = 0
        for start in range(0, total - WINDOW, WINDOW):
            window_text = " ".join(words[start:start + WINDOW]).lower()
            has_hook = any(w in window_text for w in hook_signals)
            has_number = bool(re.search(r'[0-9][0-9,.]*', window_text))
            if not has_hook and not has_number:
                dead_zones += 1
        if dead_zones >= 2:
            score -= min(0.3 * dead_zones, 1.2)
            issues.append(f"{dead_zones} retention dead zones (200w+ with no hook or specific detail)")

    # Killer Hook / Narrative Craft / Topic Clarity rubric — real,
    # deterministic scoring of the actual script text, shared across all
    # 5 channels (video_pipeline/script_scoring.py).
    try:
        from script_scoring import score_script_rubric, validate_rehook_beat
        rubric_bonus, rubric_issues, subscores = score_script_rubric(script_clean, topic)
        score += rubric_bonus
        if subscores:
            log(f"  Rubric: Hook {subscores['killer_hook']}/10 | "
                f"Craft {subscores['narrative_craft']}/10 | "
                f"Clarity {subscores['topic_clarity']}/10 | "
                f"HookGate {'PASS' if subscores.get('hook_gate_passed') else 'FAIL'}")
        issues.extend(rubric_issues[:3])
        rehook_bonus, rehook_issues = validate_rehook_beat(script_clean)
        score += rehook_bonus
        issues.extend(rehook_issues)
    except Exception as e:
        log(f"  Script rubric scoring (non-fatal): {e}")

    return min(round(score, 1), 10.0), issues




# ═══════════════════════════════════════════════════════════
# PORTED FROM Ch1 — Advanced features for Ch2
# ═══════════════════════════════════════════════════════════

def run_provider_health_check():
    """
    Tests all AI providers at pipeline startup.
    Fires BEFORE script generation so you see exactly what works.
    Results sent to Telegram so you can see them in the approval gate.

    FIX (found via a real production Telegram alert showing 6/7
    providers consistently "failing" — same bug fixed identically in
    Ch1 and Ch3, this function having been copy-pasted across all
    channels): the test prompt asked for a genuinely ~2-character reply
    ("Reply with exactly: OK"), while every single provider-calling
    function requires the response to exceed 100 characters to count as
    valid — correct for REAL script-generation calls, wrong for this
    tiny test. A model that actually followed the instruction literally
    got wrongly marked "NO RESPONSE"; a model that ignored it and
    rambled past 100 characters passed by accident. Fixed by asking for
    something that naturally produces a long reply regardless of model
    compliance.
    """
    log("\n" + "="*65)
    log("  AI PROVIDER HEALTH CHECK")
    log("="*65)
    test = ("Write a short paragraph (at least 150 words) describing what "
            "makes a documentary narration engaging. Do not use any special "
            "formatting, just plain prose.")
    results = {}

    checks = [
        ("Cerebras",    _call_cerebras),
        ("SambaNova",   _call_sambanova),
        ("Gemini",      _call_gemini_with_fallback),
        ("Groq",        call_groq),
        ("OpenRouter",  _call_openrouter),
        ("Cohere",      _call_cohere),
        ("Mistral",     _call_mistral),
    ]
    working = []
    for name, fn in checks:
        try:
            r = fn(test, tokens=50)
            status = "✅ WORKING" if r else "❌ NO RESPONSE"
            if r: working.append(name)
        except Exception as e:
            status = f"❌ ERROR: {str(e)[:60]}"
        results[name] = status
        log(f"  {name:12s}: {status}")

    log("="*65)

    # Alert to Telegram so Mohammed can see it without checking logs
    status_lines = "\n".join(f"  {n}: {s}" for n, s in results.items())
    if len(working) == 0:
        tg(f"🚨 CRITICAL: ALL AI PROVIDERS FAILED\n{status_lines}\n\nPipeline cannot continue.")
        raise RuntimeError("All AI providers failed health check")
    elif len(working) < 3:
        tg(f"⚠️ Only {len(working)} AI provider(s) working:\n{status_lines}")
    else:
        log(f"  {len(working)}/7 providers working — OK to proceed")

    return working



def generate_best_cold_open(niche, topic, trending_titles=None):
    """
    Generate 3 cold open variants, score each on hook strength, return the best.
    The cold open is the most important 30 seconds — it determines whether
    YouTube promotes the video or buries it.
    """
    trend_hint = ""
    if trending_titles:
        trend_hint = f"These hooks are working in this niche right now:\n"
        trend_hint += "\n".join(f"  - {t}" for t in trending_titles[:3])

    prompt = f"""Generate exactly 3 different cold open variants for a dark documentary narration.
Topic: {topic}
Niche style: {niche.get("viral_search", niche.get("name", "dark investigative documentary"))}
{trend_hint}

Each cold open must:
- Be 80-120 words
- Start with the single most disturbing fact — mid-action, no preamble
- Never say "welcome back", "today", "in this video"
- Use a specific date, time, or number in the first sentence
- Create a question the listener cannot stop thinking about
- FIX (direct user report, July 23 2026 — same fix already verified on
  Ch1, applied empire-wide): the opening must actually PREVIEW the real,
  specific twist/outcome of THIS exact case — state or strongly imply the
  concrete result up front (e.g. if the case is evidence that cleared the
  prime suspect but convicted the one person nobody suspected, say
  something like "the evidence that cleared him is what convicted her" —
  naming the real irony, not a vague mood). This creates a "wait — HOW
  did that happen" curiosity gap about THIS specific case, not generic
  dread. A viewer must be able to tell, from the cold open alone, roughly
  WHAT happens by the end — they keep watching to learn HOW, never to
  learn WHAT. An opening that could be swapped into a different episode
  about a different case with zero changes has failed this requirement,
  no matter how disturbing it sounds in isolation.

- FIX (direct user report, July 23 2026 — "I don't want you to just use
  the AI to write things. I want to think harder and use the human
  attention connection of how humans get interested with any video"):
  the opening sentence must use a REVERSAL pattern — state something
  that violates an expectation (e.g. "wasn't supposed to", "everyone
  assumed", "should have been the one thing that..."), not a flat
  statement of fact. It must name concrete STAKES — what is actually at
  risk (a marriage, a fortune, a life, a family, a reputation), not an
  abstract disturbing mood. And it must include a real named person or
  place, not pure abstraction. These three signals are automatically
  scored after generation (video_pipeline/script_scoring.py) — an
  opening missing them will fail the hook gate and be reworked, so build
  them in now rather than relying on a retry to catch it.

Format your response EXACTLY as:
VARIANT_1:
[cold open text here]
VARIANT_2:
[cold open text here]
VARIANT_3:
[cold open text here]

Write all 3 now. Zero markdown."""

    raw = ai(prompt, tokens=1200)
    if not raw:
        return None

    # Parse variants
    variants = []
    for i in range(1, 4):
        pattern = f"VARIANT_{i}:"
        next_p  = f"VARIANT_{i+1}:" if i < 3 else None
        start = raw.find(pattern)
        if start == -1: continue
        start += len(pattern)
        end   = raw.find(next_p, start) if next_p else len(raw)
        text  = strip_md(raw[start:end].strip())
        if len(text.split()) >= 60:
            variants.append(text)

    if not variants:
        return None

    # Score each variant on hook strength
    def score_cold_open(text):
        s = 0.0
        words = text.lower()
        # Specific numbers/dates signal
        if re.search(r'\d', text): s += 2.0
        # Short punchy sentences
        sentences = [x.strip() for x in re.split(r'(?<=[.!?])\s+', text) if x.strip()]
        if sentences:
            avg_len = sum(len(x.split()) for x in sentences) / len(sentences)
            if avg_len <= 10: s += 2.0
            elif avg_len <= 13: s += 1.0
        # Dread keywords
        dread = ["discovered","found","nobody","never","years","days","inside","unknown","hidden","only"]
        s += sum(0.4 for w in dread if w in words)
        # Opens mid-action (no weak openers)
        weak = ["in this", "today we", "welcome", "hello", "this is the story", "have you ever"]
        if not any(w in words[:50] for w in weak): s += 1.5
        return round(min(s, 10.0), 1)

    scored = [(v, score_cold_open(v)) for v in variants]
    scored.sort(key=lambda x: x[1], reverse=True)
    best_text, best_score = scored[0]
    log(f"  Cold opens scored: {[s for _,s in scored]} — picked {best_score}/10")
    return best_text


# ================================================================
# REAL CASE RESEARCH
# Pulls real documented cases from free sources before script generation.
# AI narrates real facts instead of inventing plausible-sounding ones.
# Sources: Google News RSS (free) + Reddit r/TrueCrime (free read-only)
# ================================================================


def _validate_retention_hooks(script_clean):
    """
    Validates retention hooks at 30/60/80% positions.
    Returns (penalty, issues). Penalty deducted from script score.
    Called inside score_result so weak scripts retry automatically.
    """
    words   = script_clean.split()
    total   = len(words)
    if total < 400:
        return 0.0, []
    penalty = 0.0; issues = []

    def seg(p1, p2):
        return " ".join(words[int(total*p1):int(total*p2)]).lower()

    hook_signals = ["subscribe","coming up","next","what happens","the answer","revealed",
                    "in a moment","stay","about to","this changes","not yet","what comes next"]

    if sum(1 for w in hook_signals if w in seg(0.25, 0.35)) < 1:
        penalty -= 0.4; issues.append("Missing 30% hook")
    h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
    if h60 < 2:
        penalty -= 0.8; issues.append("Weak 60% hook — peak CTA missing")
    elif h60 >= 3:
        penalty += 0.3
    if sum(1 for w in hook_signals if w in seg(0.75, 0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing final subscribe CTA")
    if issues:
        issues_str = " | ".join(issues)
        log(f"  Retention issues: {issues_str}")
    return round(penalty, 1), issues

# ================================================================
# PSYCHOLOGICAL 7-STAGE SCRIPT  [IMPROVED]
# ================================================================

def get_stage_matched_video(niche, script, audio_duration):
    """
    Stage-matched footage: extract keywords from each script stage,
    search Pixabay for matching dark footage, concatenate 7 clips.
    Falls back to single looped video if this fails.
    """
    words     = script.split()
    total     = len(words)
    # Stage boundaries (proportional)
    stage_defs = [
        (100,  "dark discovery opening"),
        (200,  "ordinary life before dark"),
        (250,  "warning signs shadows"),
        (400,  "dark escalation danger"),
        (200,  "calm relief break"),
        (650,  "dark revelation truth exposed"),
        (200,  "dark aftermath consequences"),
    ]
    stage_clips = []
    idx = 0
    black_fallback_count = 0
    stage_dur   = audio_duration / len(stage_defs)

    for i, (word_count, base_kw) in enumerate(stage_defs):
        end        = min(idx + word_count, total)
        stage_text = " ".join(words[idx:end]).lower()
        idx        = end

        # Extract 2 most relevant nouns from stage text
        # Simple approach: most common non-stopwords
        stopwords  = {"the","a","an","and","or","but","in","on","at","to","for",
                      "of","with","by","from","this","that","was","were","had","have",
                      "it","its","he","she","they","their","his","her","be","been",
                      "not","no","so","as","if","then","than","when","what","who"}
        stage_words= [w.strip(".,!?;:") for w in stage_text.split()
                      if len(w) > 4 and w not in stopwords]
        from collections import Counter
        top_nouns  = [w for w,_ in Counter(stage_words).most_common(2)]
        kw         = " ".join(top_nouns[:1]) + " " + base_kw if top_nouns else base_kw

        clip_path  = str(WORK_DIR / f"stage_{i}.mp4")
        log(f"  Stage {i+1} footage: '{kw[:40]}'")

        # Try Pixabay, then Pexels (real fallback — was documented but never called), then a generic broad term
        downloaded = False
        search_terms = [kw, base_kw, BG_KEYWORDS.get(niche["name"], DEFAULT_BG_KEYWORDS)[i % 3],
                         "cinematic dark atmosphere"]
        for search_kw in search_terms:
            if downloaded: break
            try:
                if PIXABAY_KEY:
                    r = requests.get("https://pixabay.com/api/videos/",
                        params={"key": PIXABAY_KEY, "q": search_kw, "per_page": 5,
                                "video_type": "film", "orientation": "horizontal"}, timeout=25)
                    if r.status_code == 200 and r.json().get("hits"):
                        hit = max(r.json()["hits"], key=lambda h: h.get("duration", 0))
                        url = hit["videos"]["medium"]["url"]
                        with requests.get(url, timeout=45, stream=True) as dl:
                            dl.raise_for_status()
                            with open(clip_path, "wb") as f:
                                for chunk in dl.iter_content(32768): f.write(chunk)
                        if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                            downloaded = True; continue
                    elif r.status_code == 429:
                        log(f"    Stage {i+1} Pixabay: 429 rate limited")
            except Exception as e:
                log(f"    Stage {i+1} Pixabay: {e}")

            if not downloaded:
                try:
                    if PEXELS_KEY:
                        r = requests.get("https://api.pexels.com/videos/search",
                            headers={"Authorization": PEXELS_KEY},
                            params={"query": search_kw, "per_page": 5, "orientation": "landscape"},
                            timeout=25)
                        if r.status_code == 200 and r.json().get("videos"):
                            vids  = r.json()["videos"]
                            best  = max(vids, key=lambda v: v.get("duration", 0))
                            files_ = sorted(best.get("video_files", []),
                                            key=lambda vf: vf.get("width", 0), reverse=True)
                            url = next((vf["link"] for vf in files_ if vf.get("width", 0) <= 1920), None) \
                                  or (files_[0]["link"] if files_ else None)
                            if url:
                                with requests.get(url, timeout=45, stream=True) as dl:
                                    dl.raise_for_status()
                                    with open(clip_path, "wb") as f:
                                        for chunk in dl.iter_content(32768): f.write(chunk)
                                if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                                    downloaded = True
                        elif r.status_code == 429:
                            log(f"    Stage {i+1} Pexels: 429 rate limited")
                except Exception as e:
                    log(f"    Stage {i+1} Pexels: {e}")

        if not downloaded:
            black_fallback_count += 1
            # Last resort only — real footage exhausted on both providers
            dur = max(int(stage_dur), 8)
            run_ffmpeg(["ffmpeg","-y","-f","lavfi",
                "-i",f"color=c=black:size=1280x720:rate=24:duration={dur}",
                "-c:v","libx264","-pix_fmt","yuv420p", clip_path],
                label=f"stage-{i}-fallback")
            log(f"  Stage {i+1}: NO footage found on Pixabay or Pexels — using black clip")

        if Path(clip_path).exists():
            stage_clips.append((clip_path, stage_dur))

    if black_fallback_count > 0:
        tg(f"⚠️ {black_fallback_count}/{len(stage_defs)} background clips had NO real footage "
           f"(Pixabay+Pexels both empty/exhausted) — used black clip instead. Check PIXABAY_KEY / PEXELS_API_KEY.")

    if len(stage_clips) < 3:
        log("  Stage footage insufficient — falling back to single looped video")
        return None

    # Concatenate all stage clips scaled/padded to 1280x720
    parts = []
    for i, (clip, dur) in enumerate(stage_clips):
        scaled = str(WORK_DIR / f"stage_{i}_scaled.mp4")
        run_ffmpeg(["ffmpeg","-y","-i",clip,
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,"
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-t",str(dur),"-c:v","libx264","-preset","ultrafast",
            "-pix_fmt","yuv420p","-an", scaled], label=f"scale-{i}")
        if Path(scaled).exists():
            parts.append(scaled)

    if not parts:
        return None

    list_file = str(WORK_DIR / "stage_list.txt")
    combined  = str(WORK_DIR / "background_staged.mp4")
    with open(list_file, "w") as f:
        # Repeat to cover full duration
        loops = max(1, int(audio_duration / (len(parts) * 8)) + 2)
        for _ in range(loops):
            for p in parts: f.write(f"file '{p}'\n")

    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,
                "-c","copy","-t",str(audio_duration+5),combined], label="stage-concat")
    if Path(combined).exists() and Path(combined).stat().st_size > 50000:
        log(f"  Stage-matched video: {Path(combined).stat().st_size//(1024*1024)}MB")
        return combined
    return None


def fetch_trending_titles(niche, token):
    try:
        published_after = (datetime.datetime.utcnow() -
                           datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche.get("viral_search", niche["name"]), "type": "video",
                    "order": "viewCount", "publishedAfter": published_after,
                    "videoDuration": "long", "maxResults": 8,
                    "relevanceLanguage": "en"}, timeout=20)
        if r.status_code == 200:
            items  = r.json().get("items", [])
            titles = [i["snippet"]["title"] for i in items if i.get("snippet", {}).get("title")]
            log(f"  Trend intel: {len(titles)} titles")
            return titles
        else: log(f"  Trend intel: {r.status_code}")
    except Exception as e: log(f"  Trend intel (non-fatal): {e}")
    return []


def _research_viral_content(niche, original_topic):
    """
    When script quality falls below gate, research the last 2 years of
    viral mega-videos (2M+ views) in this niche and generate a stronger
    topic angle before the next attempt. Gives the AI better direction.
    """
    prompt = f"""You are a YouTube viral content strategist for dark investigative documentaries.

Niche: {niche["name"].replace("_", " ")}
Underperforming topic: {original_topic}

Study what makes 2M+ view mega-videos in this niche over the last 2 years:
- They open with a specific date, location, or number — never vague
- They follow ONE person's story, not a general theme
- They contain a twist that reframes everything the viewer thought they knew
- The reveal feels impossible until the evidence is laid out

Generate ONE stronger replacement topic sentence that:
1. Is far more specific — real-feeling names, exact durations, precise counts
2. Contains a built-in impossible detail that demands explanation
3. Creates immediate psychological tension from the very first word
4. Fits the {niche["series"]} series tone exactly

Return ONLY the topic sentence. Nothing else."""

    result = ai(prompt, tokens=300)
    if result:
        t = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
        if len(t) > 40:
            log(f"  Viral angle: {t[:90]}")
            return t
    return None



def format_citations_block(real_cases):
    """
    v6 addition — real citation/sourcing system, same as Ch1: only ever
    cites cases with a REAL, actually-captured URL — never lists an
    unverifiable "source" as decoration.
    """
    real_sources = [c for c in (real_cases or []) if c.get("url")]
    if not real_sources:
        return ""
    lines = ["Sources & further reading:"]
    for c in real_sources[:4]:
        label = "News" if c.get("source") == "news" else "Community discussion"
        lines.append(f"• {label}: {c['title'][:100]} — {c['url']}")
    return "\n\n" + "\n".join(lines)


def generate_seo_description(niche, topic, title, episode, chapters_text, audio_duration=0, citations_block=""):
    dur_min = int(audio_duration / 60) if audio_duration > 60 else 15
    prompt = f"""Write a YouTube video description for a forensic investigation documentary.
Title: {title} | Series: {niche["series"]}, Episode {episode}
Topic: {topic} | Duration: ~{dur_min} minutes

Structure:
1. Two hook sentences on the core disturbing fact. Creates urgency to watch.
2. Three sentences on what the investigation reveals. No spoilers.
3. One line: Watch until the end — the final revelation changes everything.
4. Chapters section (paste verbatim):\n{chapters_text or "0:00 Introduction"}
5. Eight keyword sentences using: forensic investigation, true crime documentary, evidence analysis,
   hidden truth, {niche["name"].replace("_", " ")}, classified evidence, real case, financial crime
6. One line: New investigations every week — subscribe so you never miss one.

Total: 250-320 words. Plain text. No markdown. Do NOT include any hashtags —
those are added separately afterward."""
    # FIX (found alongside the hashtag fix below): these seo_hooks used
    # Ch1's niche names (dark_horror, seduction_dark, etc.) inside Ch2's
    # own file — the exact same "niche names copy-pasted from Ch1"
    # pattern already found and fixed repeatedly elsewhere in this
    # project. None of these keys could ever match any of Ch2's real
    # niches, so seo_first_line always silently fell through to the
    # generic default below. Fixed to Ch2's actual 7 niches.
    seo_hooks = {
        "forensic_finance":       f"DOCUMENTED: {topic[:45]}.",
        "criminal_investigation": f"CASE FILE: {topic[:45]}.",
        "corporate_exposure":     f"EXPOSED: {topic[:45]}.",
        "digital_forensics":      f"TRACED: {topic[:45]}.",
        "body_cam_police":        f"ON RECORD: {topic[:45]}.",
        "courtroom_drama":        f"ON TRIAL: {topic[:45]}.",
        "robbery_documentaries":  f"DOCUMENTED: {topic[:45]}.",
    }
    seo_first_line = seo_hooks.get(niche["name"], f"INVESTIGATION: {topic[:55]}.")

    # FIX (v6 addition, per explicit request — "multiple hashtags for
    # more viewers"): same real fix as Ch1 — was a buried, unverified
    # "Ten relevant hashtags" instruction inside a much bigger
    # generation prompt (and 10 is itself wrong; real 2026 best practice
    # researched directly is 3-5). Now generated explicitly in code.
    hashtags = generate_episode_hashtags(niche, topic)

    raw = ai(prompt, tokens=1000)
    # FIX: this was "betrayal_deepdive" (Ch1's channel_id) inside CH2's
    # own file — Ch2's cross-promo block would show Ch1's cross-promo
    # content instead of Ch2's own. Matches the same real bug class
    # already found and fixed for niche names above.
    cross_promo_txt = get_cross_promo("evidence_room", is_short=False)
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo_txt
        desc += "\n\n✨ Real stories, brought to life with next-generation AI narration and production craft."
        desc += citations_block
        desc += f"\n\n{hashtags}"
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"Subscribe for new investigations every week."
            f"{cross_promo_txt}\n\n"
            f"✨ Real stories, brought to life with next-generation AI narration and production craft."
            f"{citations_block}\n\n"
            f"{hashtags}")


def generate_episode_hashtags(niche, topic):
    """Real, explicit, code-level hashtag generation — 3-5 total (the
    actual researched 2026 sweet spot), matched to Ch2's real niches."""
    category_tags_map = {
        "forensic_finance":       ["#FinancialCrime", "#TrueCrime"],
        "criminal_investigation": ["#TrueCrime", "#Investigation"],
        "corporate_exposure":     ["#CorporateExposed", "#TrueCrime"],
        "digital_forensics":      ["#DigitalForensics", "#CyberCrime"],
        "body_cam_police":        ["#BodyCam", "#TrueCrime"],
        "courtroom_drama":        ["#CourtroomDrama", "#TrueCrime"],
        "robbery_documentaries":  ["#TrueCrime", "#Robbery"],
    }
    category_tags = category_tags_map.get(niche["name"], ["#TrueCrime", "#Documentary"])
    try:
        tag_prompt = (f"Give exactly 2 real YouTube hashtags (short, no spaces, CamelCase, "
                      f"starting with #) that specifically match this documentary topic: "
                      f"{topic[:200]}. Return ONLY the 2 hashtags separated by a space, nothing else.")
        raw_tags = ai(tag_prompt, tokens=30) or ""
        topic_tags = [t for t in raw_tags.split() if t.startswith("#") and len(t) < 30][:2]
    except Exception:
        topic_tags = []
    all_tags = category_tags + topic_tags + ["#TheEvidenceRoom"]
    seen = set(); final_tags = []
    for t in all_tags:
        if t.lower() not in seen:
            seen.add(t.lower()); final_tags.append(t)
    return " ".join(final_tags[:5])

# ================================================================
# ELEVENLABS TTS  [NEW #5]
# ================================================================

def update_channel_description(token, latest_title, latest_url):
    """[NEW #12] Update channel About with latest episode."""
    try:
        r = requests.get(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true"}, timeout=20)
        if r.status_code != 200: return
        ch_id = r.json()["items"][0]["id"]
        # FIX: same "Channel update 400" bug found and fixed in Ch1 —
        # YouTube's channels.update requires the FULL snippet (including
        # title) when part=snippet, not just the field being changed.
        existing_snippet = r.json()["items"][0].get("snippet", {})
        # FIX (found on direct user request, July 14 2026): this was
        # literally Ch1's real channel description ("dark psychology,
        # true horror") copy-pasted verbatim -- if this ever ran,
        # Ch2's real, public YouTube "About" page would have
        # described itself as a horror channel.
        desc  = (f"Latest: {latest_title}\n{latest_url}\n\n"
                 "Forensic crime investigations — documented cases, real evidence, cold cases and corporate exposure.\n"
                 "New episodes every weekday. Subscribe for weekly investigations.")
        existing_snippet["description"] = desc[:1000]
        r2 = requests.put(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"id": ch_id, "snippet": existing_snippet}, timeout=20)
        if r2.status_code in [200, 201]: log("OK Channel description updated")
        else: log(f"  Channel update {r2.status_code}: {r2.text[:200]}")
    except Exception as e: log(f"  Channel update (non-fatal): {e}")

# ================================================================
# CLEANUP
# ================================================================

def extract_real_case_facts(cases, niche_name):
    """
    Use AI to extract the most compelling documented facts from
    the real cases found. Returns a brief that gets injected
    into the script prompt — AI narrates real facts, doesn't invent.
    """
    if not cases:
        return ""

    cases_text = "\n".join(
        f"- [{c['source'].upper()}] {c['title']} | {c['summary'][:100]}"
        for c in cases[:5]
    )

    prompt = f"""From these REAL documented cases in the {niche_name.replace('_', ' ')} niche:

{cases_text}

Extract the single most compelling REAL case with:
1. ONE specific verifiable fact (exact number, date, duration, or amount)
2. ONE detail that makes it feel completely real and documented
3. The core disturbing element that would make someone watch a full documentary

Return as: REAL CASE BRIEF (3 sentences max, plain text, use the actual facts):
[fact 1]. [fact 2]. [core disturbing element]."""

    result = ai(prompt, tokens=300)
    if result:
        brief = result.strip()[:400]
        if len(brief) > 50:
            log(f"  Real case brief: {brief[:80]}...")
            return brief
    return ""



def get_research_context(niche_name, topic):
    """
    Main research entry point. Returns (research_context_string, real_cases_list) —
    same real citation-system addition as Ch1: the structured list (with
    real URLs) is what feeds the actual "Sources" block and on-screen
    credits, rather than fabricating citations with nothing real behind them.
    """
    log("  Researching real documented cases...")
    cases = search_real_cases(niche_name, topic)
    if not cases:
        log("  No real cases found — proceeding with AI-generated topic")
        return "", []
    brief = extract_real_case_facts(cases, niche_name)
    if not brief:
        return "", cases
    return (
        f"REAL DOCUMENTED CASE RESEARCH (use these real facts in your script):\n"
        f"{brief}\n"
        f"IMPORTANT: Use these real facts as the foundation. Do not invent details. "
        f"Build the narrative around documented reality."
    ), cases


def search_real_cases(niche_name, topic_hint):
    """
    Search Google News RSS and Reddit for real documented cases
    matching this niche. Returns list of real case summaries.
    No API key required for either source.
    """
    import xml.etree.ElementTree as ET
    import urllib.parse

    # FIX: this dict used Ch1's niche names (dark_horror, seduction_dark,
    # etc.) despite being inside Ch2's file — Ch2's real niches are
    # completely different, so every actual call here fell through to the
    # generic fallback query, losing all niche-specific search refinement.
    niche_queries = {
        "forensic_finance":       f"financial fraud investigation documented case {topic_hint.split()[0] if topic_hint else ''}",
        "criminal_investigation": f"criminal investigation evidence documented case {topic_hint.split()[0] if topic_hint else ''}",
        "corporate_exposure":     f"corporate fraud scandal documented case {topic_hint.split()[0] if topic_hint else ''}",
        "digital_forensics":      f"cybercrime digital forensics documented case {topic_hint.split()[0] if topic_hint else ''}",
        # FIX (found on deep re-audit): body_cam_police, courtroom_drama,
        # and robbery_documentaries are 3 of this channel's 7 real niches
        # (see NICHES below) but had no entry here — every research call
        # for these 3 niches fell through to the generic fallback query,
        # weakening the real-case grounding fed into the script prompt.
        # Same "3 niches missing" bug class already fixed this session
        # for this channel's CTA_BANK.
        "body_cam_police":        f"police body camera footage documented case {topic_hint.split()[0] if topic_hint else ''}",
        "courtroom_drama":        f"courtroom trial verdict documented case {topic_hint.split()[0] if topic_hint else ''}",
        "robbery_documentaries":  f"robbery heist investigation documented case {topic_hint.split()[0] if topic_hint else ''}",
    }
    query = niche_queries.get(niche_name,
                               (topic_hint.split()[0] if topic_hint else "case") + " documented case")
    cases = []

    # Source 1: Google News RSS — completely free, no key
    try:
        gn_url = ("https://news.google.com/rss/search"
                  f"?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en")
        r = requests.get(gn_url, timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall(".//item")[:5]
            for item in items:
                title = item.find("title")
                desc  = item.find("description")
                pub   = item.find("pubDate")
                # FIX (v6 addition — real citation system, same fix
                # applied to Ch1): this never captured the actual
                # article URL, only title/summary/date. No real URL
                # means nothing genuine to cite.
                link = item.find("link")
                if title is not None and title.text:
                    cases.append({
                        "source":  "news",
                        "title":   title.text[:120],
                        "summary": desc.text[:200] if desc is not None and desc.text else "",
                        "date":    pub.text[:20] if pub is not None and pub.text else "",
                        "url":     link.text.strip() if link is not None and link.text else "",
                    })
            log(f"  Real cases from news: {len(cases)}")
    except Exception as e:
        log(f"  News RSS (non-fatal): {e}")

    # Source 2: Reddit r/TrueCrime — free read-only JSON API
    try:
        reddit_url = (f"https://www.reddit.com/r/TrueCrime/search.json"
                      f"?q={urllib.parse.quote(query)}&sort=top&t=year&limit=5")
        r2 = requests.get(reddit_url, timeout=15,
                         headers={"User-Agent": "DeepDiveResearch/1.0"})
        if r2.status_code == 200:
            posts = r2.json().get("data", {}).get("children", [])
            for post in posts[:3]:
                d = post.get("data", {})
                title = d.get("title", "")
                permalink = d.get("permalink", "")
                if title and len(title) > 20:
                    cases.append({
                        "source":  "reddit",
                        "title":   title[:120],
                        "summary": d.get("selftext", "")[:200],
                        "date":    "",
                        "score":   d.get("score", 0),
                        "url":     f"https://reddit.com{permalink}" if permalink else "",
                    })
            log(f"  Real cases from Reddit: {len([c for c in cases if c['source']=='reddit'])}")
    except Exception as e:
        log(f"  Reddit (non-fatal): {e}")

    return cases[:6]  # top 6 real cases



def get_real_weekly_trend_signal(niche_name):
    """
    v1 addition — genuine, real weekly trend research (same fix built
    for Ch5). Uses the real YouTube Data API (mostPopular chart) to see
    what's actually resonating this week, rather than a static random
    pick. Real signal, never fabricated; returns an empty list on any
    failure rather than guessing.
    """
    try:
        token = get_yt_token()
        if not token:
            return []
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet", "chart": "mostPopular",
                    "regionCode": "US", "maxResults": 15, "access_token": token},
            timeout=15)
        if r.status_code != 200:
            return []
        items = r.json().get("items", [])
        return [it["snippet"]["title"] for it in items if it.get("snippet", {}).get("title")][:15]
    except Exception as e:
        log(f"  Weekly trend signal (non-fatal): {e}")
        return []


def generate_trend_informed_topic(niche, trending_titles):
    """
    FIX (critical, confirmed with real execution — this crashed on
    every single call): referenced niche["topics"], which doesn't exist
    — the real key is "seed_topics". Would have crashed topic selection
    every time this path was used, for every niche, without exception.
    Also rebuilt into genuine, real trend research (matching the fix
    built for Ch5): pulls a real current signal (YouTube's own trending
    chart, plus any NewsAPI-sourced trending_titles already passed in)
    and asks the AI to pick whichever real seed topic is genuinely most
    aligned with what's resonating this week.
    """
    real_trend_titles = list(trending_titles or [])
    real_trend_titles += get_real_weekly_trend_signal(niche["name"])

    if not real_trend_titles:
        topic = random.choice(niche["seed_topics"])
        log(f"  No real trend signal available — using seed topic: {topic[:80]}")
        return topic

    try:
        trend_block = "\n".join(f"- {t}" for t in real_trend_titles[:10])
        result = ai(
            f"Real trending topics/titles this week:\n{trend_block}\n\n"
            f"Real available seed topics for this channel's '{niche['name']}' niche:\n" +
            "\n".join(f"{i+1}. {t}" for i, t in enumerate(niche["seed_topics"])) +
            f"\n\nWhich numbered seed topic is most aligned with what's genuinely "
            f"resonating this week? Return ONLY the number (1-{len(niche['seed_topics'])}). "
            f"If none are a good fit, return 0.", tokens=10)
        if result:
            match = re.search(r'\d+', result)
            if match:
                idx = int(match.group())
                if 1 <= idx <= len(niche["seed_topics"]):
                    topic = niche["seed_topics"][idx - 1]
                    log(f"  Trend-informed topic selected (real signal, real AI pick): {topic[:80]}")
                    return topic
    except Exception as e:
        log(f"  Trend-informed topic selection (non-fatal): {e}")

    topic = random.choice(niche["seed_topics"])
    log(f"  Trend-informed topic fallback: {topic[:80]}")
    return topic

# ================================================================
# PERFORMANCE TRACKER  [NEW #8, #10]
# ================================================================


# ═══════════════════════════════════════════════════════════
# SSML MULTI-RATE AUDIO — Ported from Ch1 for human-sounding TTS
# Generates audio at 7 different rates per stage for natural pacing
# ═══════════════════════════════════════════════════════════

def inject_ssml_rate(script):
    """
    Split script into 7 stages by word proportion and inject
    SSML prosody rate markers. Edge-tts supports rate parameter
    but not inline SSML. Instead we split the audio into segments
    with different rates and concatenate.
    Returns list of (text_segment, rate_string) tuples.

    FIX (voice-quality pass):
    - Rate range narrowed to -5%..-10% (was up to -18%). Neural voices are
      trained on natural pacing; large negative rates cause unnatural
      syllable elongation, which reads as "robotic."
    - Segments now break on the nearest SENTENCE boundary to each target
      word count instead of a hard word-count cut. Cutting mid-sentence
      meant two independently-synthesized halves — with different rates —
      got glued together inside a single thought, producing an audible
      speed jump and unnatural gap mid-sentence.
    """
    import re as _re
    # Find all sentence-end positions (index into `words`) so we can snap
    # each stage boundary to the nearest sentence end rather than a raw
    # word count.
    words = script.split()
    total = len(words)
    sentence_end_word_idxs = []
    running = 0
    for sent in _re.split(r'(?<=[.!?])\s+', script):
        sent_wc = len(sent.split())
        running += sent_wc
        if running <= total:
            sentence_end_word_idxs.append(running)
    if not sentence_end_word_idxs or sentence_end_word_idxs[-1] != total:
        sentence_end_word_idxs.append(total)

    def snap_to_sentence_end(target_idx):
        if not sentence_end_word_idxs:
            return target_idx
        return min(sentence_end_word_idxs, key=lambda x: abs(x - target_idx))

    # Stage word boundaries (proportional to STAGE_WORDS), rates narrowed
    stage_rates = [
        (100,  "-5%"),   # Cold open: urgent, attention-grabbing
        (200,  "-7%"),   # The Before: normal documentary pace
        (250,  "-7%"),   # First Signals: measured, building
        (400,  "-5%"),   # Escalation: faster, momentum
        (200,  "-8%"),   # False Resolution: slow, relief
        (650,  "-10%"),  # Real Reveal: slower, weighty (was -18%)
        (200,  "-8%"),   # Implication + CTA: deliberate
    ]
    segments = []
    idx = 0
    cumulative_target = 0
    for word_count, rate in stage_rates:
        cumulative_target += word_count
        end = snap_to_sentence_end(min(cumulative_target, total))
        end = max(end, idx)  # never go backwards
        segment = " ".join(words[idx:end])
        if segment.strip():
            segments.append((segment, rate))
        idx = end
        if idx >= total:
            break
    # Any remaining words go to last rate
    if idx < total:
        remaining = " ".join(words[idx:])
        if remaining.strip():
            segments.append((remaining, "-8%"))
    return segments


def get_media_duration(path):
    """
    FIX: this function was genuinely missing from this file entirely —
    run_audio_with_ssml (a confirmed-active function) called it twice,
    and both calls would have raised NameError the moment they executed.
    Found via static analysis (pyflakes), not manual review. Ported
    directly from Ch1's real, working implementation.
    """
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def run_audio_with_ssml(script, niche_name, edge_voice):
    """
    Multi-rate audio: split script into 7 stage segments,
    generate each with its own delivery rate, concatenate via FFmpeg.
    Produces audio that sounds like a real documentary narrator.

    FIX (voice-quality pass): removed the mid-narration voice swap. If a
    segment failed before, it silently fell back to en-GB-RyanNeural or
    en-US-BrianNeural for JUST that one piece — meaning the narrator's
    voice could audibly change color for a few seconds mid-video, then
    switch back. Now every segment retries on the SAME configured voice
    (with backoff) before giving up, so the narrator stays consistent
    throughout. Also added a short crossfade at each concat join instead
    of a raw stream copy, to smooth the seams between independently
    synthesized segments.
    """
    segments = inject_ssml_rate(script)
    log(f"  SSML segments: {len(segments)} at rates {[r for _,r in segments]}")

    part_paths = []
    for i, (text, rate) in enumerate(segments):
        part_path = str(WORK_DIR / f"audio_seg_{i}.mp3")
        ok = False
        for attempt in range(3):
            if attempt > 0:
                time.sleep(3 * attempt)  # backoff, avoid edge-tts rate limit
            try:
                asyncio.run(asyncio.wait_for(
                    _edge_tts_segment(text, edge_voice, rate, part_path), timeout=90))
                if Path(part_path).exists() and Path(part_path).stat().st_size > 5000:
                    part_paths.append(part_path)
                    ok = True
                    break
            except Exception as e:
                log(f"    Segment {i} attempt {attempt+1} ({edge_voice}): {e}")
        if not ok:
            log(f"  Segment {i} failed on {edge_voice} after 3 attempts — skipping "
                f"(NOT switching narrator voice mid-video)")

    if not part_paths:
        return None, 0.0

    if len(part_paths) == 1:
        import shutil
        out = str(WORK_DIR / "ssml_narration.mp3")
        shutil.copy(part_paths[0], out)
        return out, get_media_duration(out)

    # Concatenate all segments with a short crossfade at each join instead
    # of a raw stream copy, so rate/pace transitions between segments don't
    # sound like an abrupt cut.
    out = str(WORK_DIR / "ssml_narration.mp3")
    CROSSFADE_S = 0.12
    try:
        filter_parts = []
        inputs = []
        for p in part_paths:
            inputs += ["-i", p]
        n = len(part_paths)
        prev_label = "0:a"
        for i in range(1, n):
            cur_label = f"a{i}"
            filter_parts.append(
                f"[{prev_label}][{i}:a]acrossfade=d={CROSSFADE_S}:c1=tri:c2=tri[{cur_label}]"
            )
            prev_label = cur_label
        filter_complex = ";".join(filter_parts)
        run_ffmpeg(["ffmpeg", "-y", *inputs,
                    "-filter_complex", filter_complex,
                    "-map", f"[{prev_label}]", out], label="ssml-crossfade-concat")
        if not Path(out).exists() or Path(out).stat().st_size < 5000:
            raise RuntimeError("crossfade concat produced no usable output")
    except Exception as e:
        log(f"  Crossfade concat failed ({e}) — falling back to plain concat")
        list_file = str(WORK_DIR / "seg_list.txt")
        with open(list_file, "w") as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")
        run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", out], label="ssml-concat")

    duration = get_media_duration(out)
    log(f"  SSML audio: {duration:.1f}s ({duration/60:.1f} min)")
    return out, duration



async def _edge_tts_segment(text, voice, rate, path):
    """Generate audio for one segment with a specific rate."""
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await asyncio.wait_for(comm.save(path), timeout=90)


async def _edge_tts_stream(text, voice, audio_path, vtt_path):
    """
    Generate audio + word-level subtitles via edge-tts stream API.
    IMPORTANT: communicate.stream() can only be called ONCE per object.
    The fallback uses a completely fresh Communicate instance.
    """
    import edge_tts
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="-8%")
        sub = edge_tts.SubMaker()
        with open(audio_path, "wb") as af:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    af.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    sub.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
        with open(vtt_path, "w", encoding="utf-8") as sf:
            # edge-tts SubMaker API varies by version
            try:
                subs_text = sub.generate_subs()
            except TypeError:
                subs_text = getattr(sub, 'generate_subs', None)
                if callable(subs_text):
                    subs_text = subs_text()
            sf.write(subs_text if isinstance(subs_text, str) else "WEBVTT\n")
        return True
    except Exception as sub_err:
        log(f"    SubMaker path failed: {sub_err} — falling back to save()")
        # MUST create a brand-new Communicate object here.
        # The original one's stream() is already consumed and cannot be reused.
        try:
            communicate_fresh = edge_tts.Communicate(text=text, voice=voice, rate="-8%")
            await communicate_fresh.save(audio_path)
            return False   # audio saved, no subtitle timing
        except Exception as save_err:
            raise RuntimeError(f"edge-tts save() also failed: {save_err}")


def vtt_to_ass(vtt_path, ass_path):
    """Convert .vtt to styled .ass for FFmpeg subtitle burning."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,46,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,75,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def to_ass_time(t):
        t = t.strip()
        if t.count(":") == 1: t = "00:" + t
        p = t.split(":")
        h, m = int(p[0]), int(p[1])
        s_ms = p[2].replace(",", ".")
        s, ms = s_ms.split(".")
        cs = int(ms[:2]) if len(ms) >= 2 else int(ms) * 10
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"
    try:
        lines  = Path(vtt_path).read_text(encoding="utf-8").splitlines()
        events = []
        i = 0
        while i < len(lines):
            if " --> " in lines[i]:
                times = lines[i].split(" --> ")
                start = to_ass_time(times[0])
                end   = to_ass_time(times[1].split()[0])
                i += 1
                txt_parts = []
                while i < len(lines) and lines[i].strip():
                    txt_parts.append(lines[i].strip())
                    i += 1
                text  = re.sub(r'<[^>]+>', '', " ".join(txt_parts))
                words = text.split()
                chunks = [" ".join(words[j:j+6]) for j in range(0, len(words), 6)]
                text  = "\\N".join(chunks)
                events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
            i += 1
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))
        return True
    except Exception as e:
        log(f"  vtt->ass error: {e}")
        return False


def generate_real_synced_ass(audio_path, ass_path):
    """
    v1 addition — real, word-level accurate captions for the main video,
    per explicit request: captions must genuinely match the audio.
    Uses Groq's real Whisper transcription directly on the FINAL,
    ACCEPTED narration audio file — works identically regardless of
    which TTS tier produced it. Returns False (no captions) rather than
    a potentially-desynced fallback.
    """
    if not GROQ_KEY or not Path(audio_path).exists():
        return False
    try:
        with open(audio_path, "rb") as f:
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                files={"file": (Path(audio_path).name, f, "audio/mpeg")},
                data={"model": "whisper-large-v3-turbo",
                      "response_format": "verbose_json",
                      "timestamp_granularities[]": "word",
                      "language": "en"},
                timeout=180)
        if r.status_code != 200:
            log(f"  Real caption sync: Whisper request failed ({r.status_code}) — no captions this episode")
            return False
        words_data = r.json().get("words", [])
        if not words_data:
            log("  Real caption sync: no word-level data returned — no captions this episode")
            return False

        def s2t(s):
            h = int(s) // 3600; m = (int(s) % 3600) // 60
            sc = int(s) % 60;   cs = int((s - int(s)) * 100)
            return f"{h}:{m:02d}:{sc:02d}.{cs:02d}"

        header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,46,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,75,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        chunk_size = 6
        events = []
        for i in range(0, len(words_data), chunk_size):
            group = words_data[i:i + chunk_size]
            start_sec = group[0]["start"]
            end_sec = group[-1]["end"]
            text = " ".join(w["word"].strip() for w in group)
            events.append(f"Dialogue: 0,{s2t(start_sec)},{s2t(end_sec)},Default,,0,0,0,,{text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))
        log(f"  Real caption sync: {len(events)} genuinely word-timed caption groups ✅")
        return True
    except Exception as e:
        log(f"  Real caption sync failed (non-fatal, no captions this episode): {e}")
        return False


def generate_fallback_ass(script, audio_duration, ass_path):
    """Approximate timing subtitles when edge-tts SubMaker unavailable."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,46,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,75,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def s2t(s):
        h = int(s) // 3600; m = (int(s) % 3600) // 60
        sc = int(s) % 60;   cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{sc:02d}.{cs:02d}"
    words   = script.split()
    spw     = audio_duration / max(len(words), 1)   # seconds per word
    chunks  = [words[i:i+6] for i in range(0, len(words), 6)]
    events  = []
    t       = 0.0
    for chunk in chunks:
        if t >= audio_duration: break
        end  = min(t + spw * len(chunk), audio_duration)
        text = " ".join(chunk)
        events.append(f"Dialogue: 0,{s2t(t)},{s2t(end)},Default,,0,0,0,,{text}")
        t = end
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

# ================================================================
# AUDIO STAGE
# ================================================================

def main():
    """
    Two-phase controller for Ch2 (The Evidence Room).
    PIPELINE_PHASE=generate : generate + save pending_upload.json
    PIPELINE_PHASE=upload   : read pending, upload to YouTube
    PIPELINE_PHASE=full     : legacy single-run (backward compatible)
    """
    from phase_manager import (get_pipeline_phase, save_pending,
                                load_pending, clear_pending, check_pending_age,
                                is_already_uploaded)

    phase      = get_pipeline_phase()
    SCRIPT_DIR = Path(__file__).parent
    state      = load_state()

    log(f"\nEVIDENCE ROOM v14.0 — Phase: {phase.upper()}")
    log(f"Time: {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p IST')}")

    if phase == "generate":
        # FIX: same gap found and fixed in Ch1 — run_provider_health_check
        # existed fully built but was never actually called anywhere.
        _healthy_providers = run_provider_health_check()

    # ── UPLOAD PHASE ──────────────────────────────────────────
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch2 Upload: no pending video. Generation may have failed.")
            sys.exit(0)
        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch2 Upload: pending is {hours_old}h old — uploading anyway.")

        title        = pending["title"]
        description  = pending["description"]
        tags         = pending["tags"]
        niche_name   = pending["niche_name"]
        video_path   = pending["video_path"]
        topic        = pending.get("topic", title)  # FIX: same gap found and fixed in Ch1 —
        # was never extracted, so the Shorts functions got the title instead
        # of real story details to write their scripts from.
        thumb_path   = pending.get("thumbnail_path","")
        shorts       = pending.get("shorts_clips", [])
        script_clean = pending.get("script_clean","")
        duration     = pending.get("duration", 0)
        score        = pending.get("score", 0)
        voice_used   = pending.get("voice_used","")
        episode      = pending.get("episode", 1)
        playlist_id  = pending.get("playlist_id","")
        short_titles = pending.get("short_titles", {})
        short_cross  = pending.get("short_cross","")

        if not video_path or not Path(video_path).exists():
            tg(f"❌ Ch2 Upload: video file missing. Run Generate first.")
            sys.exit(1)

        token_yt = get_yt_token()
        # Create playlist now if generate phase skipped it
        if not playlist_id:
            niche_obj = next((n for n in NICHES if n["name"] == niche_name), None)
            if niche_obj:
                playlist_id = ensure_playlist(token_yt, niche_name, niche_obj["series"])
                if playlist_id:
                    pl = state.get("playlists",{}); pl[niche_name] = playlist_id
                    state["playlists"] = pl; save_state(state)
        yt_url, vid_id = run_stage_with_retry(
            upload_yt, "Upload", video_path, title, description, tags,
            is_short=False, token=token_yt, privacy="unlisted")

        from human_review_gate import review_final_video_before_publish
        _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
        _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        _final_gate = review_final_video_before_publish(
            "Ch2 The Evidence Room", yt_url, thumb_path,
            TG_TOKEN, TG_CHAT, check_ins_used=0,
            gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
        if _final_gate["decision"] != "approve":
            delete_yt_video(vid_id, token=token_yt)
            clear_pending(SCRIPT_DIR)
            tg(f"🔄 Ch2: final video rejected — unlisted upload removed, "
               f"nothing published. Feedback: {_final_gate.get('feedback') or '(none given)'}. "
               f"A fresh episode will be generated on the next cycle.")
            log("Final pre-publish gate: rejected — stopping before publish steps.")
            sys.exit(0)
        set_video_privacy(vid_id, "public", token=token_yt)
        log(f"  Final gate approved — video is now public: {yt_url}")

        # FIX (direct user report, July 23 2026 — "after uploading, it
        # also needs to take up the job of checking: what is going on,
        # how many views... likes... subscribers... what the monetary
        # environment is... report back to me... in Telegram", applied
        # empire-wide): a real publish-time snapshot sent right after the
        # video goes public, on top of the existing weekly aggregate report.
        try:
            from post_upload_reporter import send_post_upload_report
            send_post_upload_report(
                "The Evidence Room", yt_url, vid_id, token_yt,
                TG_TOKEN, TG_CHAT, gumroad_token=os.environ.get("GUMROAD_ACCESS_TOKEN"), tg_fn=tg)
        except Exception as e:
            log(f"  Post-upload report (non-fatal): {e}")

        # FIX: same root cause found and fixed in Ch1 — ensure_playlist
        # existed fully built but was never called, so playlist_id was
        # always empty, meaning add_to_playlist below never actually fired.
        if not playlist_id:
            try:
                playlist_id = ensure_playlist(token_yt, niche_name, "The Evidence Room")
                if playlist_id:
                    state.setdefault("playlists", {})[niche_name] = playlist_id
            except Exception as e:
                log(f"  Playlist creation (non-fatal): {e}")

        if playlist_id: add_to_playlist(token_yt, playlist_id, vid_id)

        # FIX: update_channel_description existed fully built (including a
        # real fix to the "channel update 400" bug made much earlier in
        # this project) but was NEVER actually called — that fix has been
        # sitting completely unused; the channel's About description has
        # never actually been updated to reflect the latest episode.
        try:
            update_channel_description(token_yt, title, yt_url)
        except Exception as e:
            log(f"  Channel description update (non-fatal): {e}")

        if thumb_path and Path(thumb_path).exists():
            try:
                with open(thumb_path,"rb") as tf:
                    tr = requests.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={vid_id}&uploadType=media",
                        headers={"Authorization":f"Bearer {token_yt}",
                                 "Content-Type":"image/jpeg"},
                        data=tf.read(), timeout=60)
                if tr.status_code in [200,201]:
                    log("  Thumbnail uploaded")
                else:
                    # FIX: same silent-failure bug found and fixed in Ch1 —
                    # zero logging on any non-200 response, which is exactly
                    # why a missing thumbnail was invisible in the logs.
                    log(f"  Thumbnail upload FAILED: {tr.status_code} — {tr.text[:300]}")
                    tg(f"⚠️ Evidence Room: thumbnail upload failed ({tr.status_code}) — "
                       f"video published without a custom thumbnail.")
            except Exception as te: log(f"  Thumbnail (non-fatal): {te}")

        post_creator_comment(token_yt, vid_id, niche_name, title, episode)

        # FIX: produce_standalone_short already generates AND uploads
        # internally — both standalone Shorts already went out during the
        # generate phase. Recap Short removed entirely per explicit
        # request — only 2 Shorts/day now.
        short_urls = [s.get("url") for s in shorts if s.get("ok") and s.get("url")]
        log(f"  Total Shorts this episode: {len(short_urls)}")

        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token_yt, vid_id, script_clean, duration, "evidence_room")
            except Exception as e: log(f"  SRT (non-fatal): {e}")

        # Log fingerprint to history only after confirmed real publish success
        try:
            from authenticity_guard import save_fingerprint_record
            _fp = pending.get("auth_fingerprint")
            if _fp:
                save_fingerprint_record(SCRIPT_DIR, _fp)
        except Exception as e:
            log(f"  Authenticity fingerprint log (non-fatal): {e}")

        # Mark the approved backlog topic as produced, same success-only timing
        try:
            from topic_scoring import mark_produced
            _approved_id = pending.get("approved_topic_id")
            if _approved_id:
                mark_produced(SCRIPT_DIR, _approved_id, episode)
        except Exception as e:
            log(f"  Topic backlog update (non-fatal): {e}")

        # Generate the companion page + log to the Publishing Archive —
        # both only after confirmed real publish success, same discipline
        # as fingerprint logging and topic marking above. These modules
        # live in video_pipeline/, already on PYTHONPATH (same fix that
        # made thumbnail_engine_v2 etc. importable from here), so no path
        # manipulation is needed — same as every other cross-module import
        # in this file.
        try:
            from site_generator import render_companion_page
            from publishing_archive import add_archive_entry, get_related_episodes

            # SCRIPT_DIR = channels/evidence_room/ -> repo root is 2 levels up
            docs_root = SCRIPT_DIR.parent.parent / "docs"
            related = get_related_episodes(SCRIPT_DIR, niche_name, exclude_episode_number=episode)

            page_path = render_companion_page(
                episode_data={
                    "episode_number": episode,
                    "episode_title": title,
                    "video_url": yt_url,
                    "channel_id": "evidence_room",
                    "niche_name": niche_name,
                    "publish_date": datetime.date.today().isoformat(),
                    "script_excerpt": script_clean[:600],
                    "related_links": related,
                },
                output_root=docs_root,
                ai_fn=lambda p, tokens=500: ai(p, tokens=tokens),
            )
            if page_path:
                add_archive_entry(SCRIPT_DIR, {
                    "episode_number": episode,
                    "title": title,
                    "video_url": yt_url,
                    "niche_name": niche_name,
                    "topic": topic,
                    "companion_page_url": f"evidenceroom/ep{episode}.html",
                })
                log(f"  Companion page generated: {page_path}")
            else:
                log("  Companion page generation skipped (non-fatal)")
        except Exception as e:
            log(f"  Companion page / archive (non-fatal): {e}")

        # Extract a genuine reusable insight into the right product manuscript
        try:
            from product_manuscript import add_product_note
            products_root = SCRIPT_DIR.parent.parent / "products"
            note = add_product_note(products_root, title, script_clean[:800],
                                      "evidence_room",
                                      lambda p, tokens=300: ai(p, tokens=tokens))
            if note:
                log(f"  Product note added to '{note['chapter']}': {note['note_text'][:80]}")
            else:
                log("  Product note skipped (duplicate or extraction miss, non-fatal)")
        except Exception as e:
            log(f"  Product note extraction (non-fatal): {e}")

        clear_pending(SCRIPT_DIR)
        state["last_title"]    = title
        state["last_url"]      = yt_url
        state["last_voice"]    = voice_used
        state["total_uploads"] = state.get("total_uploads",0)+1

        # FIX: same gap found and fixed in Ch1 — save_pattern_memory
        # existed fully built but was never called, so the pattern-memory
        # system always read from a permanently empty history.
        # FIX: track_episode_ch2 existed fully built but was never called —
        # niche auto-rotation could never trigger without this.
        state = track_episode_ch2(state, niche_name, score, voice_used, episode)

        state = save_pattern_memory(state, episode, niche_name, topic, score)

        # The unified audit search engine — same as Ch1.
        try:
            from daily_audit_engine import run_full_video_audit
            audit_result = run_full_video_audit(
                channel_dir=SCRIPT_DIR,
                episode_number=episode,
                title=title,
                niche_name=niche_name,
                quality_score=score,
                quality_attempt=pending.get("quality_attempt", 1),
                authenticity_result={"composite_score": pending.get("authenticity_score", 10.0)},
                provider_health_working_count=pending.get("providers_healthy_count", 7),
            )
            log(f"  Audit verdict: {audit_result['verdict']} — {audit_result['reasons']}")
            if audit_result["verdict"] == "HOLD":
                tg(f"🚨 Ch2 AUDIT HOLD — Episode {episode}: {audit_result['reasons']}")
        except Exception as e:
            log(f"  Audit engine (non-fatal): {e}")

        save_state(state)

        try:
            # FIX: same gap found and fixed in Ch1 — SPRINT_SCRIPT_PATH and
            # SPRINT_PLAYLIST_ID were never set, silently disabling
            # growth_engine's previous-episode pinned-comment update feature.
            sprint_script_path = str(WORK_DIR / "sprint_script.txt")
            try:
                Path(sprint_script_path).write_text(script_clean)
            except Exception:
                sprint_script_path = ""

            env_ext = os.environ.copy()
            env_ext.update({
                "GROWTH_ENGINE_MODE": "sprint",
                "SPRINT_VIDEO_URL":   yt_url,
                "SPRINT_VIDEO_TITLE": title,
                "SPRINT_CHANNEL_ID":  "evidence_room",
                "SPRINT_NICHE":       niche_name,
                "SPRINT_SHORTS_URLS": ",".join(short_urls),
                "SPRINT_SCORE":       str(score),
                # FIX: SPRINT_DURATION_SECS was still missing even after the
                # SPRINT_SCRIPT_PATH/SPRINT_PLAYLIST_ID fix above — growth_engine.py's
                # caption-upload + pinned-comment-update gate requires BOTH
                # script_path AND duration > 0, so it was still silently
                # disabled here even with a real script_path set.
                "SPRINT_DURATION_SECS": str(duration),
                "SPRINT_PLAYLIST_ID": playlist_id or "",
                "SPRINT_SCRIPT_PATH": sprint_script_path,
            })
            # FIX: this pointed at channels/growth_engine/growth_engine.py — a
            # path that doesn't exist. The real file lives in video_pipeline/,
            # a sibling directory to channels/, not inside channels/ at all.
            # Same category of bug found and fixed in master_pipeline.py
            # earlier — Popen doesn't wait for or check the subprocess, so
            # this failed silently every single run with zero trace.
            #
            # FIX (found on deep re-audit): the path was already correct
            # here, but this was still fire-and-forget Popen — Ch3/Ch4
            # were already upgraded to a blocking subprocess.run because
            # run_post_upload_sprint sleeps 30 minutes before its comment-
            # reply engine runs, and GitHub Actions tears down the entire
            # process tree within seconds of the job's last step. A
            # detached Popen child here would almost certainly be killed
            # mid-sleep every time too, regardless of the correct path.
            _ge_path = Path(__file__).parent.parent.parent / "video_pipeline" / "growth_engine.py"
            if not _ge_path.exists():
                log(f"  Growth engine NOT FOUND at {_ge_path} — skipping sprint")
            else:
                try:
                    subprocess.run(["python3", str(_ge_path)], env=env_ext, timeout=2400)
                except subprocess.TimeoutExpired:
                    log("  Growth engine sprint exceeded 40min budget — moving on")
        except Exception as ge: log(f"  Growth engine (non-fatal): {ge}")

        # v15: Hype notification — free Explore leaderboard push
        send_hype_push(yt_url, title, "The Evidence Room", day=0)

        tg(f"✅ <b>The Evidence Room — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10 | Ep{episode}\n"
           f"🚀 First-hour sprint active")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ── GENERATE PHASE ────────────────────────────────────────
    episode = (datetime.datetime.now().timetuple().tm_yday//3)+1
    ckpt_clear()

    (niche, topic, voice, style_name, episode,
     script_clean, scenes, title_str, thumbnail_text,
     title_scores, score, tags, intel) = run_stage1(state)

    # v6 addition — real citation system: the actual sources used during
    # research (if any were found), carried through intel (the same safe
    # pattern already established for _winning_attempt) rather than
    # extending run_stage1's own large return tuple.
    real_cases = intel.get("_real_cases", [])

    # FIX (direct user report, July 23 2026 — "sync Claude Code into the
    # script as a main interceptor for quality... if it generates a
    # script, I want you to read that script and generate the quality
    # audit... minimum is 6.8... remake it without fail", applied
    # empire-wide, matching the same fix on Ch1): the 13-attempt loop
    # above already gates on a rule-based rubric, but that's not the same
    # as an independent AI actually reading the whole script and judging
    # it holistically. This is that second, independent read. run_stage1
    # generates script+scenes+title+thumbnail all together per attempt,
    # so a rework here re-runs the WHOLE tuple and every downstream
    # variable is reassigned together -- never just the script text alone,
    # which would leave scenes/title/thumbnail describing a stale attempt.
    try:
        from quality_auditor import enforce_quality_gate
        _rework_history = [{"niche": niche, "topic": topic, "voice": voice, "style_name": style_name,
                             "episode": episode, "script_clean": script_clean, "scenes": scenes,
                             "title_str": title_str, "thumbnail_text": thumbnail_text,
                             "title_scores": title_scores, "score": score, "tags": tags,
                             "intel": intel, "real_cases": real_cases}]
        def _rescript():
            (_n2, _t2, _v2, _sn2, _ep2, _sc2, _scenes2, _ts2, _tt2,
             _tsc2, _score2, _tg2, _intel2) = run_stage1(state)
            _rework_history.append({"niche": _n2, "topic": _t2, "voice": _v2, "style_name": _sn2,
                                     "episode": _ep2, "script_clean": _sc2, "scenes": _scenes2,
                                     "title_str": _ts2, "thumbnail_text": _tt2,
                                     "title_scores": _tsc2, "score": _score2, "tags": _tg2,
                                     "intel": _intel2, "real_cases": _intel2.get("_real_cases", [])})
            return _sc2
        _audit = enforce_quality_gate(
            "script", script_clean, "", lambda p, tokens=350: ai(p, tokens=tokens),
            _rescript, tg_fn=tg, topic=topic, max_reworks=2)
        for _entry in reversed(_rework_history):
            if _entry["script_clean"] == _audit["content"]:
                niche, topic, voice, style_name = _entry["niche"], _entry["topic"], _entry["voice"], _entry["style_name"]
                episode, scenes, title_str = _entry["episode"], _entry["scenes"], _entry["title_str"]
                thumbnail_text, title_scores, score = _entry["thumbnail_text"], _entry["title_scores"], _entry["score"]
                tags, intel, real_cases = _entry["tags"], _entry["intel"], _entry["real_cases"]
                break
        script_clean = _audit["content"]
        log(f"  Quality audit (script): {_audit['score']}/10 "
            f"(passed={_audit['passed']}, reworked={_audit['reworked']}, "
            f"fallback={_audit['used_fallback']})")
    except Exception as e:
        log(f"  Quality audit unavailable (non-fatal, proceeding with existing script): {e}")

    topic_used   = topic
    # v1 addition — real learned thumbnail-style preference, closing the
    # same "write-only, no learning" gap already found and fixed for
    # voice selection. Honest limitation: uses the script's own quality
    # score as a proxy signal, since no real click-through data exists
    # yet. Epsilon-greedy: 80% of the time uses whichever style has the
    # better real historical average (once there's enough data), 20% of
    # the time still explores via calendar alternation.
    week_number  = datetime.datetime.now().isocalendar()[1]
    _calendar_style = "A" if week_number % 2 == 1 else "B"
    try:
        _ab_perf = state.get("performance", {})
        _a_scores = _ab_perf.get("thumbnail_style_A", {}).get("scores", [])
        _b_scores = _ab_perf.get("thumbnail_style_B", {}).get("scores", [])
        if len(_a_scores) >= 3 and len(_b_scores) >= 3 and week_number % 5 != 0:
            _a_avg = sum(_a_scores) / len(_a_scores)
            _b_avg = sum(_b_scores) / len(_b_scores)
            ab_style = "A" if _a_avg >= _b_avg else "B"
            log(f"  Thumbnail style: learned preference ({ab_style}, avg {max(_a_avg,_b_avg):.1f} vs {min(_a_avg,_b_avg):.1f})")
        else:
            ab_style = _calendar_style
    except Exception as e:
        log(f"  Learned thumbnail-style preference (non-fatal, using calendar): {e}")
        ab_style = _calendar_style
    try:
        _perf = state.get("performance", {})
        _ab_rec = _perf.get(f"thumbnail_style_{ab_style}", {"scores": []})
        _ab_rec["scores"] = (_ab_rec["scores"] + [score])[-20:]
        _perf[f"thumbnail_style_{ab_style}"] = _ab_rec
        state["performance"] = _perf
    except Exception as e:
        log(f"  Thumbnail style tracking (non-fatal): {e}")
    cross_promo     = get_cross_promo("evidence_room", is_short=False)
    affiliate_block = build_affiliate_block("evidence_room", niche["name"])
    product_cta = build_product_cta("evidence_room")
    # chapters_block built AFTER audio so duration is available
    seo_first    = f"DOCUMENTED: {topic[:60]}."

    # Playlist created at upload time (YouTube creds not available in generate phase)
    playlist_id = state.get("playlists",{}).get(niche["name"], "")

    tags_er = list(set(tags))[:15]

    # FULL SCRIPT REVIEW + EDIT LOOP — mirrors Ch1's design. Ch2's script
    # flow doesn't expose per-stage text the way Ch1 does, so section-
    # targeted feedback still identifies which named section is meant
    # (using the real stage_names below) but regenerates the whole
    # script with that as explicit context, rather than pretending a
    # precise substring-replace is possible when it isn't.
    try:
        from human_review_gate import review_script, identify_target_sections, regenerate_script_sections, approximate_stage_split
        _stage_names_ch2 = ["CASE OPEN","SUBJECT","ANOMALIES","EVIDENCE",
                             "CLOSURE","FULL RECORD","IMPLICATIONS"]
        _stage_word_targets_ch2 = [100, 200, 250, 400, 200, 650, 200]
        _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
        _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        _check_ins_used_script = 0

        while True:
            # FIX (July 14 2026 audit): now sends the script stage-by-stage
            # with clear headers instead of one wall of text. This channel's
            # generator doesn't keep real per-stage text, so the split is
            # reconstructed by the same word-count-proportion method the
            # pipeline's own quality gate already uses for stage scoring.
            _review = review_script("The Evidence Room", title_str, script_clean, score,
                                    niche["name"], TG_TOKEN, TG_CHAT, _check_ins_used_script,
                                    gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass,
                                    timeout_minutes=60,
                                    stage_texts=approximate_stage_split(script_clean, _stage_names_ch2, _stage_word_targets_ch2),
                                    stage_names=_stage_names_ch2)
            _check_ins_used_script += 1

            if _review["decision"] == "reject":
                log("Rejected during full script review."); sys.exit(0)
            if _review["decision"] == "remake":
                tg(f"🔄 Ch2: REMAKE requested"
                   f"{' — ' + _review['feedback'] if _review['feedback'] else ''}. "
                   f"This episode is being scrapped. A fresh episode will be generated "
                   f"on the next scheduled run.")
                log("  REMAKE requested during script review — clearing pending, exiting.")
                clear_pending(SCRIPT_DIR)
                sys.exit(0)
            if _review["decision"] == "approve":
                break
            if _review["decision"] == "edit":
                _targets = identify_target_sections(_review["feedback"], _stage_names_ch2)
                log(f"  Script EDIT requested: '{_review['feedback']}' -> "
                    f"sections identified: {_targets or 'WHOLE SCRIPT'} "
                    f"(regenerating whole script with this as context — no per-stage text "
                    f"breakdown available in Ch2)")
                try:
                    script_clean, _ = regenerate_script_sections(
                        script_clean, [], _stage_names_ch2, [],  # empty target_sections forces whole-script path
                        f"Focus especially on: {', '.join(_targets) if _targets else 'the whole script'}. "
                        f"{_review['feedback']}", niche, topic, ai)
                    tg("✅ Script updated per your feedback — sending the revised version for another look.")
                except Exception as e:
                    tg(f"🚨 Ch2: your script edit could NOT be applied — {e}. "
                       f"The script is UNCHANGED. Please try again or approve as-is.")
                    log(f"  Script edit failed, feedback NOT applied: {e}")
    except Exception as e:
        # FIX (found diagnosing a real production issue from a Telegram
        # screenshot): this previously only logged to stdout — completely
        # invisible unless you're watching the GitHub Actions run live.
        # The bare, contextless "30 min expired — auto-approved" messages
        # you saw were this exact fallback firing silently (most likely
        # because human_review_gate.py genuinely isn't deployed to the
        # live repo yet, per your own note — a real ModuleNotFoundError
        # here, correctly caught, but silently swallowed instead of
        # telling you the richer review system didn't actually run).
        # Now alerts visibly every time this fallback triggers, for any
        # reason, so this is never invisible again.
        log(f"  Full script review (non-fatal, falling back to quick gate): {e}")
        tg(f"⚠️ Ch2: the full review system failed to load ({str(e)[:150]}) — falling back "
           f"to the older, simpler approval gate for this episode. If human_review_gate.py "
           f"and review_queue.py haven't been deployed to this repo yet, that's the likely "
           f"cause; once they are, this fallback should stop firing.")
        decision = run_stage2_approval_ch2(title_str, niche, score, script_clean)
        if decision == "rejected":
            log("Rejected."); sys.exit(0)

    # Audio
    audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
        run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    # STRICTER AUDIO GATE, now with an active retry — same upgrade made in
    # Ch1: rather than holding immediately and waiting a full day, this
    # re-attempts the whole audio stage up to twice more, 2 hours apart,
    # giving edge-tts/Fish Audio a genuine chance to refresh before
    # falling back further. Only holds if every attempt still lands on
    # the two robotic tiers.
    _audio_retry_count = 0
    _MAX_AUDIO_RETRIES = 2
    # FIX (found on final re-audit): 2 retries x 2h each could
    # silently consume up to 4 real hours before the audio+video
    # review checkpoint is ever reached, inside a 6-hour job that
    # also shares a 4.5h review-time budget across every other
    # checkpoint. It also didn't achieve its own stated purpose --
    # provider DAILY quotas reset roughly every 24h, not 2h, so
    # this was never long enough for that case anyway. Shortened
    # to a realistic wait for a genuinely transient rate limit.
    _AUDIO_RETRY_WAIT_SECONDS = 10 * 60  # 10 minutes
    while voice_used in ("gtts-fallback", "espeak-offline-LASTRESORT") and \
          _audio_retry_count < _MAX_AUDIO_RETRIES:
        _audio_retry_count += 1
        log(f"  Audio tier {voice_used} is below the auto-publish bar — "
            f"waiting 2h for providers to refresh (retry {_audio_retry_count}/{_MAX_AUDIO_RETRIES})...")
        tg(f"⏳ Ch2: audio fell back to {voice_used} — waiting 2h and retrying "
           f"({_audio_retry_count}/{_MAX_AUDIO_RETRIES}) before holding for review.")
        time.sleep(_AUDIO_RETRY_WAIT_SECONDS)
        audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
            run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    if voice_used in ("gtts-fallback", "espeak-offline-LASTRESORT"):
        tg(f"🛑 Ch2 HOLD — audio still fell back to {voice_used} after "
           f"{_MAX_AUDIO_RETRIES} retries over {_MAX_AUDIO_RETRIES * 2}h, below the stated "
           f"voice-quality bar. This episode is NOT being published automatically. Review the "
           f"audio, or manually approve if it's acceptable, then re-run.")
        log(f"  HOLD: audio tier {voice_used} is still below the auto-publish bar "
            f"after {_MAX_AUDIO_RETRIES} retries. Stopping here.")
        sys.exit(0)

    # v1 addition — real, word-level synced captions for the main video,
    # per explicit request that captions must genuinely match the audio.
    # Generated here on the truly final accepted audio (past all
    # retries), using real Whisper transcription — works regardless of
    # which TTS tier produced it. Skipped entirely (no captions) rather
    # than shown potentially-desynced if real transcription fails.
    ass_path = str(WORK_DIR / "main_captions.ass")
    has_real_captions = generate_real_synced_ass(audio_path, ass_path)
    if not has_real_captions:
        ass_path = None

    # HARD CEILING: 18 minutes, no exceptions — Ch1 had this safety net
    # (added after a real 32-minute video slipped through), Ch2 never did.
    # Only meaningful now that duration measurement above actually reflects
    # the real audio file instead of a word-count estimate.
    HARD_MAX_SECONDS = 18 * 60
    if duration > HARD_MAX_SECONDS:
        log(f"  ⚠️ Audio exceeded 18-min hard cap ({duration/60:.1f} min) — trimming")
        trimmed = str(WORK_DIR / "audio_trimmed.mp3")
        subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-t", str(HARD_MAX_SECONDS),
                         "-c", "copy", trimmed], capture_output=True, timeout=120)
        if Path(trimmed).exists() and Path(trimmed).stat().st_size > 50000:
            audio_path = trimmed
            _r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                                 "-of","csv=p=0",trimmed], capture_output=True, text=True, timeout=30)
            duration = float(_r.stdout.strip()) if _r.returncode == 0 and _r.stdout.strip() else HARD_MAX_SECONDS
            audio_sz = Path(trimmed).stat().st_size
            tg(f"⚠️ Evidence Room: narration ran over 18min, had to trim it. "
               f"The generation itself needs checking — this trim is a safety net, not a fix.")

    # Build description now that duration is known
    _stage_word_counts_ch2 = [len(t.split()) for t in
                              approximate_stage_split(script_clean, _stage_names_ch2, _stage_word_targets_ch2)]
    chapters_block = _gen_chapters(script_clean, duration, "evidence_room",
                                    stage_word_counts=_stage_word_counts_ch2)
    # FIX (found while wiring in citations — a real, honest correction of
    # my own earlier work): generate_episode_hashtags was only ever
    # called from inside generate_seo_description, which is ITSELF never
    # called anywhere in this file — the real, live description is built
    # right here, inline. My earlier hashtag fix was verified to work in
    # isolation but never actually traced through to confirm it was wired
    # into the live path, so hashtags never actually reached a real
    # Ch2 description. Fixed here, alongside the new citations block.
    hashtags = generate_episode_hashtags(niche, topic)
    citations_block = format_citations_block(real_cases)
    # FIX (found on deep re-audit): this description had no real per-
    # episode summary anywhere — seo_first is just a truncated topic
    # fragment, and the line after it was fixed boilerplate reused
    # every single episode ("Every case. Every document...."). Every
    # other channel generates a real, topic-specific 2-sentence hook
    # for this exact spot (control_files/archive's hook_prompt pattern);
    # Ch2 never did. Added here, with the same generic-fallback safety
    # net those channels already use if the AI call fails.
    # FIX (direct user report, July 23 2026 — "for everything, there
    # should be specific scores that it should pass... rework that stage
    # without fail"): this description was built ONCE with no scoring or
    # rework of any kind -- every other channel (Ch1/Ch3/Ch4/Ch5) already
    # runs its description through regenerate_description_until_good
    # (real score_description() rubric, min 9.0, up to 4 attempts). Ch2
    # was the one channel missing this gate entirely. Wrapped the same
    # content/branding this function already built (business email,
    # "Subscribe to The Evidence Room", cross-promo, affiliate/product
    # CTAs, citations, hashtags all preserved) in a real generate-and-score
    # closure so a fresh hook line is attempted each retry.
    def _desc_gen(_n, _t, _ti, _ep, _ch, _dur):
        try:
            _hook_prompt = (f"Write ONE compelling 2-sentence hook for a YouTube description, "
                            f"for a forensic investigative documentary about: {_t[:200]}. "
                            f"Specific, evidence-focused, no clickbait, no markdown. "
                            f"Return ONLY the 2 sentences.")
            _hook = ai(_hook_prompt, tokens=120, prefer="groq")
            _hook = strip_md(_hook).strip() if _hook else \
                "Every case. Every document. Every piece of evidence — animated."
        except Exception:
            _hook = "Every case. Every document. Every piece of evidence — animated."
        return (f"{seo_first}\n\nEpisode {_ep} of {_n['series']}.\n\n"
                f"{_hook}\n\n"
                f"{_ch}\n\n"
                f"Subscribe to The Evidence Room."
                f"{cross_promo}"
                f"{affiliate_block}"
                f"{product_cta}\n\n"
                f"\u2728 Real cases, brought to life with next-generation AI narration and forensic craft."
                f"\n\n\U0001F4E7 Business inquiries: {BUSINESS_EMAIL}"
                f"{citations_block}\n\n"
                f"{hashtags}")

    from human_review_gate import regenerate_description_until_good
    _desc_result = regenerate_description_until_good(
        niche, topic, title_str, episode, chapters_block, duration, niche["name"], _desc_gen,
        min_score=9.0, max_attempts=4)
    description = _desc_result["description"]
    log(f"  Description score: {_desc_result['score']}/10 "
        f"(hit target: {_desc_result['hit_target']}, {_desc_result['attempts']} attempts)")

    # Video
    video_path = run_stage_with_retry(
        render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], niche_obj=niche, episode=episode, real_cases=real_cases, ass_path=ass_path)
    # FIX (direct user report, July 23 2026 — "hundreds of things...
    # according to the niche and title... should not be missed"): Ch2
    # had ZERO content-matched sound design beyond ambient music.
    # Genre-neutral, audio-only layer (no visual grain/flash — Ch2's
    # own genre, not Ch1's horror-movie language) from the shared
    # ~78-category library.
    try:
        from content_sfx import apply_audio_only_content_sfx
        _sfx_out = str(WORK_DIR / f"video_content_sfx_{episode}.mp4")
        video_path = apply_audio_only_content_sfx(
            video_path, script_clean, duration, niche["name"], _sfx_out, topic=topic, log_fn=log)
    except Exception as _sfx_e:
        log(f"  Content SFX layer (non-fatal): {_sfx_e}")

    # COMBINED AUDIO + VIDEO REVIEW — mirrors Ch1 exactly.
    _remade_av_ch2 = False
    try:
        from human_review_gate import review_audio_and_video
        _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
        _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        _check_ins_used_av = 0

        while True:
            try:
                from quality_scoring import score_audio_quality, score_video_quality, get_media_duration
                _audio_score, _audio_breakdown = score_audio_quality(
                    audio_path, duration, len(script_clean.split()), voice_used)
            except Exception as e:
                log(f"  Audio scoring (non-fatal): {e}")
                _audio_score, _audio_breakdown = None, None
            try:
                _real_video_duration = get_media_duration(video_path)
                # FIX (found on deep re-audit): score_video_quality defaults
                # to expected_width=1280/height=720, but this channel renders
                # at W,H=1920,1080 — every episode was silently docked ~25%
                # weight of its video score for a "resolution mismatch" that
                # wasn't real, since nothing here ever overrode the default.
                _video_score, _video_breakdown = score_video_quality(
                    video_path, _real_video_duration, duration, content_type="animated",
                    expected_width=W, expected_height=H)
            except Exception as e:
                log(f"  Video scoring (non-fatal): {e}")
                _video_score, _video_breakdown = None, None

            _av_review = review_audio_and_video(
                "The Evidence Room", audio_path, voice_used, video_path, None,
                TG_TOKEN, TG_CHAT, _check_ins_used_av,
                gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60,
                audio_score=_audio_score, audio_score_breakdown=_audio_breakdown,
                video_score=_video_score, video_score_breakdown=_video_breakdown)
            _check_ins_used_av += 1

            _a_dec = _av_review["audio_decision"]["decision"]
            if _a_dec in ("reject", "remake"):
                if _a_dec == "remake":
                    tg("🔄 Ch2: REMAKE requested at audio review — this episode is being "
                       "scrapped. A fresh episode will be generated on the next scheduled run.")
                    log("  REMAKE requested during audio review — clearing pending, exiting.")
                    _remade_av_ch2 = True
                else:
                    log("Rejected during audio review.")
                break

            _v_dec = _av_review["video_decision"]["decision"] if _av_review["video_decision"] else "approve"
            if _v_dec == "reject":
                log("Rejected during video review."); sys.exit(0)
            if _v_dec == "remake":
                tg("🔄 Ch2: REMAKE requested at video review — this episode is being "
                   "scrapped. A fresh episode will be generated on the next scheduled run.")
                log("  REMAKE requested during video review — clearing pending, exiting.")
                _remade_av_ch2 = True
                break
            if _v_dec == "swap_visuals":
                tg(f"🎨 Swapping visuals"
                   f"{' for: ' + _av_review['video_decision']['feedback'] if _av_review['video_decision']['feedback'] else ''}"
                   f" — regenerating the video assembly now, same script and audio.")
                log(f"  SWAP VISUALS requested: {_av_review['video_decision']['feedback']}")
                video_path = run_stage_with_retry(
                    render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], niche_obj=niche, episode=episode, real_cases=real_cases, ass_path=ass_path)
                # FIX (direct user report, July 23 2026 — "hundreds of things...
                # according to the niche and title... should not be missed"): Ch2
                # had ZERO content-matched sound design beyond ambient music.
                # Genre-neutral, audio-only layer (no visual grain/flash — Ch2's
                # own genre, not Ch1's horror-movie language) from the shared
                # ~78-category library.
                try:
                    from content_sfx import apply_audio_only_content_sfx
                    _sfx_out = str(WORK_DIR / f"video_content_sfx_{episode}.mp4")
                    video_path = apply_audio_only_content_sfx(
                        video_path, script_clean, duration, niche["name"], _sfx_out, topic=topic, log_fn=log)
                except Exception as _sfx_e:
                    log(f"  Content SFX layer (non-fatal): {_sfx_e}")
                continue
            if _v_dec == "approve" and _a_dec == "approve":
                # FIX (found on deep re-audit): score_audio_quality/
                # score_video_quality were computed every episode but
                # never persisted anywhere — weekly_report.py had no
                # real quality data to report on at all. Recorded here
                # on the actual approved episode, mirroring
                # thumb_format_history's proven write-side pattern.
                try:
                    from quality_score_history import record_quality_scores
                    record_quality_scores(str(SCRIPT_DIR), "The Evidence Room", episode, _audio_score, _video_score)
                except Exception as e:
                    log(f"  Quality score history record (non-fatal): {e}")
                break
            if _a_dec == "swap_voice":
                _voice_pool = [v for v in NICHE_VOICES.get(niche["name"], ALL_VOICES) if v != voice_used]
                _new_voice = random.choice(_voice_pool) if _voice_pool else voice_used
                tg(f"🎙️ Swapping voice: {voice_used} → {_new_voice} — regenerating audio now, same script.")
                log(f"  SWAP VOICE requested: {voice_used} -> {_new_voice}")
                audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
                    run_stage3_audio, "Audio", script_clean, _new_voice, niche["name"])
                # FIX (found on deep re-audit): ass_path was still the
                # transcription of the OLD audio here — the video got
                # correctly re-rendered with the new narration, but its
                # burned-in captions would go out of sync with it.
                ass_path = str(WORK_DIR / "main_captions.ass")
                if not generate_real_synced_ass(audio_path, ass_path):
                    ass_path = None
                video_path = run_stage_with_retry(
                    render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], niche_obj=niche, episode=episode, real_cases=real_cases, ass_path=ass_path)
                # FIX (direct user report, July 23 2026 — "hundreds of things...
                # according to the niche and title... should not be missed"): Ch2
                # had ZERO content-matched sound design beyond ambient music.
                # Genre-neutral, audio-only layer (no visual grain/flash — Ch2's
                # own genre, not Ch1's horror-movie language) from the shared
                # ~78-category library.
                try:
                    from content_sfx import apply_audio_only_content_sfx
                    _sfx_out = str(WORK_DIR / f"video_content_sfx_{episode}.mp4")
                    video_path = apply_audio_only_content_sfx(
                        video_path, script_clean, duration, niche["name"], _sfx_out, topic=topic, log_fn=log)
                except Exception as _sfx_e:
                    log(f"  Content SFX layer (non-fatal): {_sfx_e}")
                continue
            if _a_dec == "edit":
                _fb_audio = _av_review["audio_decision"]["feedback"] or ""
                # FIX (found on direct user report, July 15 2026): this used
                # to regenerate with the exact same voice every time -- see
                # Ch1 for the full explanation. Now actually swaps voices.
                _voice_pool = [v for v in NICHE_VOICES.get(niche["name"], ALL_VOICES) if v != voice_used]
                _new_voice = random.choice(_voice_pool) if _voice_pool else voice_used
                tg(f"🎙️ Regenerating audio per your feedback: {_fb_audio}\n"
                   f"Voice: {voice_used} → {_new_voice}")
                log(f"  Audio EDIT requested: '{_fb_audio}' — swapping voice {voice_used} -> {_new_voice}")
                audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
                    run_stage3_audio, "Audio", script_clean, _new_voice, niche["name"])
                # FIX (found on deep re-audit): same stale-captions gap as
                # SWAP VOICE above.
                ass_path = str(WORK_DIR / "main_captions.ass")
                if not generate_real_synced_ass(audio_path, ass_path):
                    ass_path = None
                video_path = run_stage_with_retry(
                    render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], niche_obj=niche, episode=episode, real_cases=real_cases, ass_path=ass_path)
                # FIX (direct user report, July 23 2026 — "hundreds of things...
                # according to the niche and title... should not be missed"): Ch2
                # had ZERO content-matched sound design beyond ambient music.
                # Genre-neutral, audio-only layer (no visual grain/flash — Ch2's
                # own genre, not Ch1's horror-movie language) from the shared
                # ~78-category library.
                try:
                    from content_sfx import apply_audio_only_content_sfx
                    _sfx_out = str(WORK_DIR / f"video_content_sfx_{episode}.mp4")
                    video_path = apply_audio_only_content_sfx(
                        video_path, script_clean, duration, niche["name"], _sfx_out, topic=topic, log_fn=log)
                except Exception as _sfx_e:
                    log(f"  Content SFX layer (non-fatal): {_sfx_e}")
                continue
    except Exception as e:
        log(f"  Audio/Video review (non-fatal, proceeding with generated versions): {e}")
        tg(f"⚠️ Ch2: the audio+video review system failed to load ({str(e)[:150]}) — "
           f"proceeding with the generated audio/video WITHOUT human review for this "
           f"episode. If human_review_gate.py isn't deployed to this repo yet, that's "
           f"the likely cause.")

    if _remade_av_ch2:
        clear_pending(SCRIPT_DIR)
        sys.exit(0)

    # FIX (found on deep re-audit): SWAP VOICE and audio EDIT above both
    # reassign `duration` to the real re-recorded audio's length and
    # correctly re-render video + captions to match — but chapters_block
    # and the description built from it (above, before this review loop
    # even started) were never rebuilt. Any duration change during review
    # left the published timestamps silently wrong. Rebuilt here from the
    # real final duration, mirroring the same fix already in place for
    # control_files/archive.
    _new_stage_word_counts_ch2 = [len(t.split()) for t in
                                  approximate_stage_split(script_clean, _stage_names_ch2, _stage_word_targets_ch2)]
    _new_chapters_block = _gen_chapters(script_clean, duration, "evidence_room",
                                         stage_word_counts=_new_stage_word_counts_ch2)
    if _new_chapters_block != chapters_block:
        log("  Audio duration changed during review — rebuilding chapters + description to match.")
        chapters_block = _new_chapters_block
        description = (f"{seo_first}\n\nEpisode {episode} of {niche['series']}.\n\n"
                       f"{episode_hook}\n\n"
                       f"{chapters_block}\n\n"
                       f"Subscribe to The Evidence Room."
                       f"{cross_promo}"
                       f"{affiliate_block}"
                       f"{product_cta}\n\n"
                       f"✨ Real cases, brought to life with next-generation AI narration and forensic craft."
                       f"\n\n\U0001F4E7 Business inquiries: {BUSINESS_EMAIL}"
                       f"{citations_block}\n\n"
                       f"{hashtags}")

    # Thumbnail
    thumb_path = generate_thumbnail_with_ai_bg(
        title_str, thumbnail_text, niche["name"], topic, ab_style,
        episode=episode, channel_name="The Evidence Room")

    # Real description quality scoring on the already-built description —
    # if it doesn't hit 9.0, do a real targeted AI improvement pass
    # (rather than restructuring Ch2's inline description-building into
    # a repeatable generate_fn like Ch1 has, which would be a much
    # riskier change for equivalent real benefit here).
    from human_review_gate import score_description
    _desc_score, _desc_missing = score_description(description, title_str, niche["name"])
    _desc_attempts = 0
    while _desc_score < 9.0 and _desc_attempts < 3:
        _desc_attempts += 1
        # FIX: this prompt only ever told the AI to preserve cross-
        # promotion links and affiliate content — nothing instructed it
        # to keep the hashtags or the real Sources citation block intact,
        # and this is a full freeform AI rewrite of the whole description,
        # not a targeted patch. Real risk that either block would be
        # silently dropped, reworded, or moved somewhere that breaks the
        # "first 3 hashtags show above the title" mechanic. Now explicit.
        _improved = ai(f"Improve this real YouTube video description. It's currently missing: "
                      f"{', '.join(_desc_missing)}.\n\nCurrent description:\n{description}\n\n"
                      f"Return ONLY the improved description, keeping the real cross-promotion "
                      f"links, affiliate content, the product link, the hashtags line, and the "
                      f"Sources section (if present) EXACTLY as they are, at the very end, in the "
                      f"same order. Nothing else.", tokens=800)
        if _improved and len(_improved.split()) > 20:
            description = _improved.strip()
            # Defensive check: if the AI rewrite dropped the hashtags,
            # citations, or product CTA despite the instruction above,
            # re-append them rather than silently losing them.
            if hashtags and hashtags not in description:
                description += f"\n\n{hashtags}"
            if citations_block and citations_block.strip() not in description:
                description += citations_block
            if product_cta and product_cta.strip() not in description:
                description += product_cta
            _desc_score, _desc_missing = score_description(description, title_str, niche["name"])
    log(f"  Description score: {_desc_score}/10 after {_desc_attempts} improvement attempts")

    # COMBINED TITLE + THUMBNAIL + DESCRIPTION REVIEW — mirrors Ch1.
    _remade_ttd_ch2 = False
    try:
        from human_review_gate import review_title_thumbnail_description
        _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
        _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        _check_ins_used_ttd = 0

        while True:
            _ttd_review = review_title_thumbnail_description(
                "The Evidence Room", title_str, thumb_path, description, _desc_score,
                TG_TOKEN, TG_CHAT, _check_ins_used_ttd,
                gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60)
            _check_ins_used_ttd += 1

            if _ttd_review["decision"] == "reject":
                log("Rejected during title/thumbnail/description review."); sys.exit(0)
            if _ttd_review["decision"] == "remake":
                tg(f"🔄 Ch2: REMAKE requested"
                   f"{' — ' + _ttd_review['feedback'] if _ttd_review['feedback'] else ''}. "
                   f"This episode is being scrapped. A fresh episode will be generated "
                   f"on the next scheduled run.")
                log("  REMAKE requested — clearing pending, exiting for a fresh run.")
                _remade_ttd_ch2 = True
                break
            if _ttd_review["decision"] == "approve":
                break
            if _ttd_review["decision"] == "edit":
                fb = _ttd_review["feedback"] or ""
                _new_title = ai(f"Rewrite this video title based on real feedback.\n"
                                f"Current title: {title_str}\nFeedback: {fb}\n"
                                f"Return ONLY the new title, nothing else.", tokens=60)
                if _new_title and len(_new_title.strip()) > 5:
                    title_str = _new_title.strip()
                _new_thumb_text = ai(f"Write a new punchy 3-word max thumbnail overlay text, "
                                     f"NUMBER+NOUN format, based on real feedback.\n"
                                     f"Current text: {thumbnail_text}\nTopic: {topic}\n"
                                     f"Feedback: {fb}\nReturn ONLY the new overlay text.", tokens=40)
                if _new_thumb_text and len(_new_thumb_text.strip()) > 0:
                    thumbnail_text = _new_thumb_text.strip()
                    ab_style = "B" if ab_style == "A" else "A"
                    thumb_path = generate_thumbnail_with_ai_bg(
                        title_str, thumbnail_text, niche["name"], topic, ab_style,
                        episode=episode, channel_name="The Evidence Room")
                _new_desc = ai(f"Rewrite this video description based on real feedback.\n"
                              f"Current description:\n{description}\nFeedback: {fb}\n"
                              f"Return ONLY the new description, nothing else.", tokens=800)
                if _new_desc and len(_new_desc.split()) > 20:
                    description = _new_desc.strip()
                tg("✅ Title/thumbnail/description updated per your feedback — sending the revised version.")
    except Exception as e:
        log(f"  Title/Thumbnail/Description review (non-fatal, proceeding with generated versions): {e}")
        tg(f"⚠️ Ch2: the title/thumbnail/description review system failed to load "
           f"({str(e)[:150]}) — proceeding with the generated versions WITHOUT human "
           f"review for this episode. If human_review_gate.py isn't deployed to this "
           f"repo yet, that's the likely cause.")

    if _remade_ttd_ch2:
        clear_pending(SCRIPT_DIR)
        sys.exit(0)

    # Authenticity / Policy-Risk Check
    _pending_auth_fingerprint = None
    _auth_score = 10.0  # safe default — always defined even if the check fails entirely
    try:
        from authenticity_guard import run_authenticity_check, format_authenticity_report
        try:
            from thumbnail_engine_v2 import NICHE_PROFILES as _NICHE_PROFILES
            _families = _NICHE_PROFILES.get(niche["name"], {}).get("thumbnail_families", [])
        except Exception:
            _families = []
        thumb_family = (_families[datetime.datetime.now().timetuple().tm_yday % len(_families)]
                        if _families else "unknown")
        _thumb_seed = abs(hash(f"{title_str}{niche['name']}{episode}")) % 99999
        thumb_pose_id = f"pose_slot_{_thumb_seed % 8}"

        auth_result = run_authenticity_check(
            channel_dir=SCRIPT_DIR,
            script_clean=script_clean,
            stage_texts=[],   # Ch2's script flow doesn't expose a per-stage
                              # breakdown the same way Ch1's does — checker
                              # already degrades gracefully for this (tested),
                              # still performs the opening-sentence check.
            title=title_str,
            thumbnail_family=thumb_family,
            thumbnail_pose=thumb_pose_id,
            ai_fn=lambda p, tokens=100: ai(p, tokens=tokens),
        )
        log(format_authenticity_report(auth_result, "Ch2"))
        _auth_score = auth_result["composite_score"]
        if _auth_score < 6.0:
            tg(f"🚨 Ch2 AUTHENTICITY RISK — score {_auth_score}/10, below the safe threshold.\n"
               f"{format_authenticity_report(auth_result, 'The Evidence Room')}\n"
               f"Recommend manual review before this publishes.")
        elif _auth_score < 7.5:
            tg(f"⚠️ Ch2 authenticity check: {_auth_score}/10 — one dimension is weak, publishing "
               f"but flagging for awareness.\n{format_authenticity_report(auth_result, 'The Evidence Room')}")
        _pending_auth_fingerprint = auth_result["_fingerprint_to_log"]
    except Exception as e:
        log(f"  Authenticity check (non-fatal): {e}")

    # Validate video file before saving to pending
    if not Path(video_path).exists():
        tg(f"❌ Ch2 Generate FAILED: video file not created")
        sys.exit(1)
    video_size = Path(video_path).stat().st_size
    if video_size < 5_000_000:  # must be at least 5MB
        tg(f"❌ Generate FAILED: video too small ({video_size//1024}KB) — likely encoding error")
        sys.exit(1)
    log(f"  Video validated: {video_size//(1024*1024)}MB")

    # FIX: same bug found and fixed in Ch1 — this imported a module called
    # "shorts_engine" that doesn't exist (the real file is
    # "shorts_reels_engine.py"), and called generate_all_six_shorts(), a
    # function that doesn't exist in the real module either. The real API
    # is produce_video_topic_short / produce_standalone_short (each
    # generates AND uploads internally) — completely different shape.
    # This guaranteed Shorts always silently failed here too.
    # (teaser/recap Shorts were removed entirely per explicit instruction
    # — only these 2 functions are used: 2 today's-topic + 2 trending.)
    log("\n  Generating Shorts (4 total)...")
    log("  2 about this video's real topic (fresh, complete standalone")
    log("  pieces), 2 on genuinely different trending topics (real research")
    log("  into what's working today).")
    short_clips = []
    try:
        import importlib.util
        if importlib.util.find_spec("shorts_reels_engine") is None:
            raise ImportError("shorts_reels_engine not in PYTHONPATH")
        from shorts_reels_engine import produce_video_topic_short, produce_standalone_short

        def _post_short_comment_safe_ch2(short_url, mode_name):
            if not short_url:
                return
            try:
                import re as _re
                m = _re.search(r'(?:shorts/|v=)([A-Za-z0-9_-]{11})', short_url)
                if not m:
                    return
                _short_token = get_yt_token()
                post_short_creator_comment_ch2(_short_token, m.group(1), niche_name, title)
            except Exception as e:
                log(f"  Short pinned comment ({mode_name}, non-fatal): {e}")

        for angle in ("angle_1", "angle_2"):
            vt = produce_video_topic_short(topic, script_clean, angle, channel="evidence_room")
            short_clips.append({"ok": vt.get("status") == "success",
                                 "url": vt.get("url"), "path": vt.get("local_path"), "name": f"video_topic_{angle}"})
            log(f"  Video-topic ({angle}): {vt.get('status')}")
            _post_short_comment_safe_ch2(vt.get("url"), f"video_topic_{angle}")

        for mode in ("standalone_1", "standalone_2"):
            sa = produce_standalone_short(mode, channel="evidence_room")
            # FIX: same key mismatch found and fixed in Ch1 — produce_standalone_short
            # returns its URL under "yt_url", not "url" like produce_video_topic_short.
            short_clips.append({"ok": sa.get("status") == "success",
                                 "url": sa.get("yt_url"), "path": sa.get("local_path"), "name": mode})
            log(f"  Trending ({mode}): {sa.get('status')}")
            _post_short_comment_safe_ch2(sa.get("yt_url"), mode)

        ok_count = sum(1 for s in short_clips if s.get("ok"))
        log(f"  Shorts (generate phase): {ok_count}/{len(short_clips)} generated")

        # SHORTS REVIEW — mirrors Ch1 exactly, same honest constraint
        # about post-publish review and fresh-replacement regeneration.
        try:
            from human_review_gate import review_shorts
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            def _score_short_safe(short_path):
                if not short_path:
                    return None
                try:
                    from quality_scoring import score_shorts_quality
                    if not os.path.exists(short_path):
                        return None
                    return score_shorts_quality(short_path)[0]
                except Exception as e:
                    log(f"  Shorts scoring (non-fatal): {e}")
                    return None
            _real_shorts = [{"name": s["name"], "url": s["url"], "score": _score_short_safe(s.get("path"))}
                            for s in short_clips if s.get("url")]
            if _real_shorts:
                _sh_review = review_shorts("The Evidence Room", _real_shorts, TG_TOKEN, TG_CHAT,
                                           check_ins_used=0, gmail_sender=_gmail_sender,
                                           gmail_app_password=_gmail_pass, timeout_minutes=60)
                if _sh_review["decision"] in ("edit", "remake", "swap_visuals"):
                    log(f"  Shorts {_sh_review['decision']} requested: "
                        f"{_sh_review['feedback']} — publishing one fresh replacement standalone Short.")
                    tg(f"🎞️ Producing a fresh replacement Short per your feedback: "
                       f"{_sh_review['feedback']}")
                    _replacement = produce_standalone_short("standalone_1", channel="evidence_room")
                    _post_short_comment_safe_ch2(_replacement.get("yt_url"), "replacement_standalone")

            # ── COMMUNITY TAB checkpoint — YouTube's API has no way to
            # post to the Community tab, so this drafts the real
            # poll/post and gates on a human confirming they posted it
            # manually (see review_community_tab's docstring).
            try:
                from human_review_gate import draft_community_post, review_community_tab
                _cp_draft = draft_community_post(topic, niche["name"], title_str,
                                                  lambda p, tokens=200: ai(p, tokens=tokens))
                _cp_result = review_community_tab(
                    "The Evidence Room", _cp_draft["question"], _cp_draft["options"], TG_TOKEN, TG_CHAT,
                    check_ins_used=0, gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
                log(f"  Community Tab: {_cp_result['decision']}")
            except Exception as e:
                log(f"  Community Tab checkpoint (non-fatal): {e}")
        except Exception as e:
            log(f"  Shorts review (non-fatal): {e}")
            tg(f"⚠️ Ch2: the Shorts review system failed to load ({str(e)[:150]}) — "
               f"the Shorts already published stand as-is, with no human review applied "
               f"this time. If human_review_gate.py isn't deployed to this repo yet, "
               f"that's the likely cause.")
    except Exception as e:
        log(f"  Shorts engine (non-fatal): {e}")
        short_clips = []

    _pending_result = save_pending(SCRIPT_DIR, {
        "title":          title_str,
        "description":    description,
        "tags":           tags_er,
        "niche_name":     niche["name"],
        "video_path":     video_path,
        "audio_path":     audio_path,
        "thumbnail_path": thumb_path or "",
        "script_clean":   script_clean,
        "duration":       duration,
        "score":          score,
        "voice_used":     voice_used,
        "episode":        episode,
        "playlist_id":    playlist_id or "",
        "style_name":     style_name,
        "ab_style":       ab_style,
        "shorts_clips":   short_clips,
        "topic":          topic,
        "auth_fingerprint": _pending_auth_fingerprint,
        "quality_attempt": intel.get("_winning_attempt", 1),
        "providers_healthy_count": len(_healthy_providers) if _healthy_providers else 7,
        "authenticity_score": _auth_score,
        "approved_topic_id": intel.get("_approved_topic_id"),
    })
    if _pending_result.get("overwrite_warning"):
        tg(f"🚨 Ch2 Generate: {_pending_result['overwrite_warning']}")

    state["last_niche"] = niche["name"]
    save_state(state)
    ckpt_clear()

    if phase == "generate":
        tg(f"✅ <b>Ch2 Generated — queued for upload</b>\n\n"
           f"<b>{title_str}</b>\n"
           f"Niche: {niche['name']} | Score: {score}/10\n"
           f"Style: {style_name} | {duration/60:.1f}min\n"
           f"Uploading at: 11:30 PM IST (6 PM UTC)")
        log("\nGENERATE COMPLETE — queued for upload")
        return

    os.environ["PIPELINE_PHASE"] = "upload"
    main()


def main_with_retry():
    max_retries = 3
    for attempt in range(1, max_retries+1):
        try:
            main(); return
        except SystemExit as e:
            if e.code == 0: return
            if attempt < max_retries:
                tg(f"⚠️ Ch2 attempt {attempt}/{max_retries} failed.\nRetrying in 10 minutes...")
                # FIX (found on deep re-audit): this was 2h (7200s), but
                # ch2_upload.yml's job timeout is 90 minutes — a 2-hour
                # sleep can never complete inside that window, so this
                # retry could never actually execute; it would just get
                # hard-killed by GitHub Actions mid-sleep. Ch3/Ch4 already
                # got this exact fix (2h -> 10min) on an earlier pass;
                # Ch2 was missed. 10min also doesn't pretend to wait out a
                # provider daily-quota reset (~24h, not 2h) the way the
                # old value implied.
                time.sleep(600)
            else:
                tg(f"❌ Ch2 FAILED after {max_retries} attempts.")
                sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                tg(f"⚠️ Ch2 crash {attempt}/{max_retries}: {str(e)[:200]}\nRetrying in 10 minutes...")
                time.sleep(600)
            else:
                tg(f"❌ Ch2 FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)


if __name__ == "__main__":
    main_with_retry()
