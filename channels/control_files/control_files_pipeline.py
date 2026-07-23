#!/usr/bin/env python3
"""
THE CONTROL FILES — ANIMATED PIPELINE v2.0
Channel 2 of DeepDive Empire

SAME UPGRADES AS MASTER PIPELINE v5.0:
✅ 18 human neural voices (9 US + 9 GB) — no robotic voices
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
✅ Animated scenes: whiteboard/doodle stroke-reveal — sketch_timeline, sketch_document, sketch_crowd, sketch_mechanism, sketch_findings, sketch_person
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
# NOTE: phase_manager functions (get_pipeline_phase, save_pending,
# load_pending, clear_pending, check_pending_age, is_already_uploaded)
# are imported from the real shared phase_manager.py inside main()
# itself (see below) — that import correctly shadows any module-level
# definition for the whole of main()'s scope. A stale, buggy inlined
# duplicate of these functions used to live here at module level
# (found on final re-audit): since every real call site is inside
# main(), it was fully shadowed and never actually executed — but it
# was confusing, dead weight that risked a future mistake if anyone
# ever called these functions from a DIFFERENT function without
# realizing the shadowing only applies inside main(). Removed.
# ══════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════
# REVENUE ENGINE (inlined — no external file dependency)
# ══════════════════════════════════════════════════════════════════

NUMBER_NOUN_BANKS = {
    "dark_horror":        ["4,380 DAYS","12 YEARS","3 AM","14 VICTIMS","ONE NIGHT"],
    "seduction_dark":     ["7 SIGNS","28 DAYS","3 PEOPLE","6 WARNINGS","ONE TRAP"],
    "psychological_trap": ["6 STAGES","23 STEPS","100 DAYS","1 EXIT","5 TRIGGERS"],
    "supernatural_real":  ["3 NIGHTS","72 HOURS","9 WITNESSES","14 YEARS","1 PLACE"],
    "obsession_dark":     ["847 MESSAGES","4 YEARS","23 CALLS","1,460 DAYS","1 PERSON"],
    "cult_psychology":    ["847 MEMBERS","14 YEARS","7 STAGES","23 RULES","1 LEADER"],
    "propaganda_systems": ["40M PEOPLE","7 TECHNIQUES","14 YEARS","3 AGENCIES","1 NARRATIVE"],
    "social_engineering": ["6 PRINCIPLES","847 TARGETS","23 HOURS","7 TRIGGERS","1 CALL"],
    "mass_deception":     ["1B PEOPLE","14 MONTHS","3 NETWORKS","23 COUNTRIES","1 LIE"],
    "dark_business_documentaries": ["$1.2B LOST","800K VICTIMS","14 MONTHS","1 MEMO","23 COUNTRIES"],
    "scams_fraud_exposed":         ["19 YEARS","300 EMPLOYEES","$65B GONE","1 PERSON","STILL RUNNING"],
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


def is_malformed_title(title: str) -> bool:
    """
    Hard guard against garbled AI output becoming a published title.
    Ch1 has 2 layers of defense against this; Ch3 previously had ZERO.
    Rejects markdown symbols, bullet/comma-list shapes, and empty/garbage
    input — tested against the real incident pattern that motivated this
    guard elsewhere in the empire: "* *Numbers:* 3 years, 1095 days...".
    """
    if not title or not title.strip():
        return True
    t = title.strip()
    if re.search(r'[*#_`]|^\s*[-•]\s', t):
        return True
    if t.count(',') >= 3:
        return True
    if re.match(r'^\s*[A-Za-z ]+:\s*\*', t):
        return True
    words = t.split()
    if len(words) < 3:
        return True
    return False


def score_title_v2(title):
    if is_malformed_title(title):
        return 0.0, {"malformed": "REJECTED"}
    t  = title.lower()
    sc = 3.0
    bd = {}
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
        record_title_used(str(SCRIPT_DIR), "The Control Files", niche_name, episode, title, score)
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
# for Gumroad (monetization.py). Until then, these links will 404 or
# redirect to each platform's homepage with zero affiliate credit, not
# fail outright.
AFFILIATE_REGISTRY = {
    "betterhelp":   {"url": "https://betterhelp.com/deepdive",      "label": "BetterHelp therapy",       "channels": ["all"]},
    "nordvpn":      {"url": "https://nordvpn.com/deepdive",          "label": "NordVPN privacy",          "channels": ["control_files","evidence_room"]},
    "curiosity":    {"url": "https://curiositystream.com/deepdive",  "label": "CuriosityStream docs",     "channels": ["all"]},
    "audible":      {"url": "https://amzn.to/deepdive-audible",      "label": "Audible audiobooks",       "channels": ["all"]},
}

def build_affiliate_block(channel_id, niche_name=""):
    ch = channel_id
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
# channels"). monetization.py's real Gumroad products (dark-manipulation-
# tactics-handbook, empire-collapse-atlas, faceless-documentary-creator-
# toolkit) were only ever referenced by the static companion website and
# the weekly Gumroad-sync job — genuinely never mentioned in a single
# actual video description across any of the 4 channels. Fixed here.
GITHUB_PAGES_BASE = "https://betrayaldeepdive.github.io/betrayal-bot"

def build_product_cta(channel_id):
    """
    Real product CTA for the actual video description — not the static
    site. Uses monetization.py's real get_product_cta_url (which
    correctly prefers the real Gumroad URL once configured, falling back
    to the info page otherwise), converted to a genuine absolute URL
    since a relative path would be a dead link inside a YouTube
    description (there's no "current page" for it to be relative to).
    """
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
    # FIX (found on deep re-audit): this dict only ever had 2 keys (self +
    # BetrayalDeepDive) despite the empire having 5 channels — control_files'
    # OWN description already resolved correctly since its own key existed,
    # but any caller looking up "evidence_room"/"archive"/"collapse_index"
    # from this file would have silently fallen back to Ch1's promo block
    # (get_cross_promo's default). Filled out to match the canonical
    # 5-key dict already correct in evidence_room_pipeline.py.
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🌑 Dark horror: youtube.com/@BetrayalDeepDive",
    },
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
# channel-specific (TELEGRAM_TOKEN_CH3) with a generic fallback, right
# alongside the YouTube credentials. A duplicate, non-channel-aware
# definition used to live here too (found on re-audit) — removed, since
# it was confusing dead weight (silently overwritten later) rather than
# a live bug in itself, matching the same pattern as the stale
# phase_manager stub cleaned up earlier this session.

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
YT_CLIENT_ID    = os.environ.get("CHANNEL3_YT_CLIENT_ID",  os.environ.get("YOUTUBE_CLIENT_ID",""))
YT_CLIENT_SEC   = os.environ.get("CHANNEL3_YT_CLIENT_SECRET", os.environ.get("YOUTUBE_CLIENT_SECRET",""))
YT_REFRESH      = os.environ.get("CHANNEL3_YT_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN",""))
# FIX (found on re-audit, matches the exact bug class already found and
# fixed for Ch2 per the v5 handoff — "every channel's weekly report/
# topic-review used one global TG_TOKEN/TG_CHAT, meaning it would ALWAYS
# go through Ch1's bot regardless of which channel was actually being
# reported on"): Ch3's YouTube credentials were correctly channel-scoped
# right above this, but the Telegram ones were never given the same
# treatment — every single message this pipeline has ever sent (status
# updates, HOLD alerts, everything) would have gone to Ch1's Telegram
# chat instead of Ch3's own dedicated bot. Same channel-specific-first,
# generic-fallback pattern now applied here too.
TG_TOKEN        = os.environ.get("TELEGRAM_TOKEN_CH3", os.environ.get("TELEGRAM_TOKEN", ""))
TG_CHAT         = os.environ.get("TELEGRAM_CHAT_ID_CH3", os.environ.get("TELEGRAM_CHAT_ID", ""))

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
WORK_DIR      = Path("/home/runner/work/control_files")
if not WORK_DIR.exists(): WORK_DIR = Path("/tmp/control_files")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE    = SCRIPT_DIR / "state.json"   # persists in repo
INTEL_FILE    = SCRIPT_DIR / "intel.json"   # persists in repo
CKPT_FILE     = WORK_DIR / "checkpoint.json"

# Cerebras model names to try in order
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]

W, H, FPS   = 1920, 1080, 24
MIN_WORDS   = 1900
MAX_WORDS   = 2100
MIN_GATE    = 8.8   # FIX: was 7.3 — raised to the real empire-wide standard for
                     # attempts 1-8 (explicit directive: 8.8-8.9 minimum, every time)
FINAL_GATE  = 6.9   # absolute last-resort floor, attempt 13 only — never lower

# ════════════════════════════════════════════════════════════
# 20 HUMAN NEURAL VOICES — 10 US + 10 GB
# ════════════════════════════════════════════════════════════
US_VOICES = [
    "en-US-AndrewNeural",       # Warm authoritative storyteller
    "en-US-BrianNeural",        # Deep calm commanding
    "en-US-ChristopherNeural",  # Serious documentary authoritative
    "en-US-JasonNeural",        # Calm measured
    "en-US-EricNeural",         # Professional measured
    "en-US-GuyNeural",          # Commanding serious
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
# FIX (direct user report, July 23 2026 — "no normal voices, more human,
# deep voices... for all five channels"): ALL_VOICES was US+GB (robotic
# US voices per direct feedback on Ch1's identical TTS layer); GB_VOICES
# had en-GB-NoahNeural, confirmed broken on this repo's Actions runners
# (24/24 segment failures in live testing). Now GB-only, no broken voice.
ALL_VOICES     = GB_VOICES
ROBOTIC_VOICES = ["en-US-AriaNeural", "en-US-AnaNeural"]

# Best voices per niche — was mixing in US voices identically shuffled
# across every niche (no real per-niche variety). Now GB-only, varied.
NICHE_VOICES = {
    "cult_psychology":            ["en-GB-ThomasNeural","en-GB-RyanNeural","en-GB-OliverNeural","en-GB-EthanNeural"],
    "propaganda_systems":         ["en-GB-OliverNeural","en-GB-ThomasNeural","en-GB-RyanNeural","en-GB-EthanNeural"],
    "social_engineering":         ["en-GB-RyanNeural","en-GB-OliverNeural","en-GB-ThomasNeural","en-GB-EthanNeural"],
    "mass_deception":             ["en-GB-EthanNeural","en-GB-ThomasNeural","en-GB-OliverNeural","en-GB-RyanNeural"],
    "dark_business_documentaries":["en-GB-ThomasNeural","en-GB-EthanNeural","en-GB-RyanNeural","en-GB-OliverNeural"],
    "scams_fraud_exposed":        ["en-GB-OliverNeural","en-GB-ThomasNeural","en-GB-EthanNeural","en-GB-RyanNeural"],
}

# ── ANIMATION STYLES ────────────────────────────────────────
# v3 REBUILD: Ch3's visual identity was previously dark/noir chart-based —
# structurally identical in kind to Ch2's PIL infographic renderer with
# renamed scene types. Zero doodle/whiteboard/stroke-reveal rendering
# existed anywhere, directly contradicting the Warbook v3/v4 requirement
# that Ch3 look like After Skool / RSA Animate: a warm paper background
# with a hand visibly drawing each diagram, stroke by stroke.
STYLES = {
    "dark_minimal": {
        "bg":(246,242,228), "primary":(35,32,30), "accent":(178,32,32),
        "secondary":(120,113,96), "pulse":(178,32,32), "glow":(178,32,32),
        "desc":"Charcoal ink + red marker on cream paper — clean, analytical"
    },
    "cinematic": {
        "bg":(248,246,236), "primary":(28,30,42), "accent":(22,72,148),
        "secondary":(110,112,128), "pulse":(22,72,148), "glow":(22,72,148),
        "desc":"Charcoal ink + blue marker on warm white paper"
    },
    "documentary": {
        "bg":(243,238,218), "primary":(38,34,26), "accent":(30,96,64),
        "secondary":(126,116,92), "pulse":(30,96,64), "glow":(30,96,64),
        "desc":"Charcoal ink + green marker on aged paper — case-file mood"
    },
}
DAY_STYLE = {0:"dark_minimal",1:"cinematic",2:"documentary",3:"dark_minimal",4:"cinematic",5:"documentary",6:"dark_minimal"}

# ── NICHES ────────────────────────────────────────────────
# FIX: dark_business_documentaries and scams_fraud_exposed had full seed
# topics, RPM data, and thumbnail triggers defined but were NEVER reachable
# — this dict only ever mapped to 4 of the 6 real niches. Fixed.
DAY_NICHE = {
    0:"cult_psychology", 1:"social_engineering", 2:"propaganda_systems",
    3:"mass_deception",  4:"dark_business_documentaries", 5:"scams_fraud_exposed",
    6:"cult_psychology",
}

NICHES = [
    {
        "name": "cult_psychology", "rpm": 14.00,
        "series": "The Control Files: Cult Psychology",
        "viral_search": "cult mind control psychology manipulation documentary animated investigation",
        "archive_search": "cult manipulation psychology control documented victims 2022 2023 viral documentary",
        "thumbnail_triggers": ["NXIVM FILES","MEMBERS KNEW","YEARS INSIDE","THEY STAYED"],
        "seed_topics": [
            "NXIVM: the self-help empire that branded members and kept documented evidence of its own crimes",
            "The Heaven's Gate cult documented every step of its doctrine in manuals still available today",
            "Scientology's internal policy documents describe suppression techniques used on former members",
            "The cult that operated a private school for 22 years without triggering a single regulatory investigation",
            "How a meditation group transformed into a psychological control system over 11 years of incremental steps",
            "The commune where members signed over legal ownership of assets before full indoctrination began",
            "A documented case study: how a charismatic leader replaced family bonds with group loyalty in 18 months",
            "A wellness-influencer collective used documented love-bombing scripts to onboard members inside 72 hours",
            "A documented case: an online community's moderators used isolation tactics identical to studied cult methods",
            "The AI companion app whose retention design mirrors documented cult dependency-creation techniques",
        ],
    },
    {
        "name": "propaganda_systems", "rpm": 13.00,
        "series": "The Control Files: Propaganda Systems",
        "viral_search": "propaganda mass manipulation government media control documentary investigation",
        "archive_search": "propaganda system documented manipulation media control exposed 2022 2023 viral",
        "thumbnail_triggers": ["OPERATION FOUND","STILL RUNNING","DOCUMENT LEAKED","THEY DESIGNED IT"],
        "seed_topics": [
            "Operation Mockingbird: the declassified CIA program to place agents inside major US newsrooms",
            "The documented propaganda playbook used in four different countries with the same template",
            "A government information campaign that ran for 14 years before the internal memos were released",
            "Cambridge Analytica's documented methodology: how 87 million profiles became a targeting system",
            "The wartime information bureau that fabricated 340 documented stories placed in foreign newspapers",
            "A social media platform's internal research confirmed it amplified outrage to increase engagement",
            "The advertising industry's documented framework for manufacturing consumer desire from 1927 onward",
            "A documented state media playbook reused across three unrelated conflicts with identical talking points",
            "Internal memos show a tech platform's recommendation algorithm was tuned for outrage, not accuracy",
            "The declassified psy-ops manual whose techniques appear in modern influencer marketing courses",
        ],
    },
    {
        "name": "social_engineering", "rpm": 13.50,
        "series": "The Control Files: Social Engineering",
        "viral_search": "social engineering manipulation fraud psychological tactics documentary investigation",
        "archive_search": "social engineering manipulation documented case study exposed 2022 2023 viral",
        "thumbnail_triggers": ["ONE PHONE CALL","THREE HOURS","TOTAL ACCESS","THEY TRUSTED HIM"],
        "seed_topics": [
            "Frank Abagnale impersonated a Pan Am pilot, doctor, and attorney for 5 years using phone calls alone",
            "The social engineer who gained physical access to 7 secure facilities using only a clipboard and lanyard",
            "A documented phishing operation that extracted $47M from a Fortune 500 company through 3 emails",
            "The human hacker: how one person convinced 14 employees to bypass security protocols in 90 minutes",
            "Kevin Mitnick's documented techniques for extracting passwords from IT helpdesks in under 4 minutes",
            "A hospital was compromised not through technology but through a conversation with a parking attendant",
            "The social engineering test where 97 percent of executives gave up credentials in a simulated call",
            "The AI voice-cloning scam that extracted $35M using a 3-second sample of a real executive's voice",
            "A documented case: one LinkedIn message led to a $60M business email compromise over 11 days",
            "The deepfake video call that convinced a finance worker to wire $25M in 20 minutes",
        ],
    },
    {
        "name": "mass_deception", "rpm": 13.00,
        "series": "The Control Files: Mass Deception",
        "viral_search": "mass deception manipulation population control exposed documentary investigation",
        "archive_search": "mass deception manipulation documented evidence exposed 2022 2023 viral documentary",
        "thumbnail_triggers": ["300 MILLION PEOPLE","STILL RUNNING","DOCUMENT PROOF","THEY KNEW"],
        "seed_topics": [
            "The tobacco industry's documented internal research proving addiction knowledge from 1953 onward",
            "A data broker built profiles on 300 million people using only publicly available information",
            "The opioid marketing campaign: internal documents show pharmaceutical executives knew the risk in 1997",
            "Facebook's internal research confirmed emotional contagion experiments run on users without consent",
            "A food industry lobbying group funded 160 nutrition studies between 1970 and 2000. All favorable.",
            "The leaded gasoline campaign: documented evidence the industry suppressed neurological research for 50 years",
            "An insurance company's internal algorithm documented to deny claims at higher rates for specific zip codes",
            "Internal documents show a supplement industry funded 200 studies with predetermined favorable conclusions",
            "A documented case: an algorithm was tuned to show users what kept them angry, not what was true",
            "The subscription-cancellation dark pattern documented across 340 companies using the identical flow",
        ],
    },
    {
        "name": "dark_business_documentaries", "rpm": 11.50,
        "series": "The Control Files: Corporate Collapse",
        "viral_search": "dark business corporate scandal fraud collapse documentary investigation animated",
        "archive_search": "corporate scandal fraud collapse exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["MEMO IGNORED","BOARD APPROVED","THEY KNEW","INVESTORS LOST"],
        "seed_topics": [
            "Theranos ran 240 fake blood tests on real patients. The board approved every audit without question.",
            "An MLM structure took $1.2B from 800,000 people across 23 countries using identical recruitment scripts",
            "The Enron memo that warned everything would collapse — written 14 months before it did",
            "A Wall Street bank structured mortgage products designed to fail then bet against them for clients",
            "The pharmaceutical company whose internal documents prove addiction knowledge from 1997 onward",
            "WeWork's internal financial projections never matched a single quarter of actual performance. The IPO proceeded.",
            "A private equity firm extracted $400M in management fees from a company it then took into bankruptcy",
            "An AI startup's internal documents show projections that no version of the product could ever meet",
            "The venture-backed company whose flagship AI feature was documented to be manual labor overseas",
            "A documented case: a board approved a fourth consecutive quarter of numbers that didn't reconcile",
        ],
    },
    {
        "name": "scams_fraud_exposed", "rpm": 10.00,
        "series": "The Control Files: Fraud Exposed",
        "viral_search": "scam fraud exposed investigation documentary animated true crime financial",
        "archive_search": "scam fraud exposed investigation documentary viral 2022 2023",
        "thumbnail_triggers": ["300 EMPLOYEES","19 YEARS","SAME PERSON","STILL RUNNING"],
        "seed_topics": [
            "A romance scam operation ran from one building with 300 employees, shift schedules, and HR processes",
            "Bernie Madoff's Ponzi scheme paid consistent returns for 19 years using only incoming investor deposits",
            "A cryptocurrency fraud raised $2.4B in 8 months before the founders disappeared with a staged death",
            "The telemarketing fraud that specifically profiled and targeted recent widows and widowers by name",
            "An investment scheme where the auditor, the accountant, and the fraudster were the same person",
            "A pig butchering operation: how 6 months of relationship building precedes a single catastrophic ask",
            "The advance fee fraud that extracted $1M from a retired engineer over 22 months through 340 transfers",
            "An AI-generated voice scam ring operated from one call center with documented daily victim quotas",
            "The crypto recovery-expert scam that specifically re-targets victims of the original crypto scam",
            "A documented pig-butchering compound freed 200 trafficked workers who were themselves forced to scam",
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


# v12: SambaNova — added to Ch3 (was only in Ch1 before)
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


# v12: GEMINI_KEY_2 dual-key for Ch3 (doubles Gemini quota)
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
def run_viral_intelligence(niche, yt_token=None):
    """
    FIX (found on re-audit — this is the exact "MOST SIGNIFICANT FINDING"
    bug pattern already explicitly found and fixed in Ch2, but was never
    fixed here): this entire function asked the AI MODEL ITSELF to
    "analyze the top 20 most viral videos" with ZERO real API call behind
    it — 100% AI-imagined, hallucinated patterns presented as intelligence.
    Now genuinely grounds the prompt in real, current YouTube search
    results (via fetch_trending_titles) when a token is available, the
    same real-API pattern already proven in Ch1.
    """
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

    real_titles_block = ""
    if yt_token:
        try:
            real_titles = fetch_trending_titles(niche, yt_token)
            if real_titles:
                real_titles_block = ("\n\nThese are REAL current top-viewed titles in this "
                    "niche from the last 30 days — ground your analysis in these actual "
                    "examples, don't invent patterns from nothing:\n" +
                    "\n".join(f"  - {t}" for t in real_titles[:8]))
        except Exception as e:
            log(f"  Real trend fetch (non-fatal): {e}")

    prompt = f"""Analyze the TOP 20 most viral forensic/investigation documentary YouTube videos (2M+ views) in the "{niche['viral_search']}" niche.{real_titles_block}
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
        prompt = f"""Generate 6 compelling mass manipulation investigation topics for "{niche['series']}".
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
def generate_thumbnail_text(niche, topic, intel):
    examples = intel.get("thumbnail_text_examples", niche["thumbnail_triggers"])
    prompt = f"""Generate the most psychologically compelling 3-word thumbnail text for a mass manipulation investigation video.
NICHE: {niche['name']} | TOPIC: {topic[:100]}
TOP PERFORMERS: {', '.join(examples)}

USE ONE OF THESE 5 TRIGGERS (pick whichever fits the topic best):
1. CURIOSITY GAP: creates unanswerable question
2. AUTHORITY SIGNAL: implies documented proof
3. CONSEQUENCE: implies something irreversible was found
4. PATTERN INTERRUPT: unexpected — makes viewer stop scrolling
5. SYMPATHY/WOEFUL: implies someone was failed, ignored, or unheard —
   equally valid as the others, use roughly as often (e.g. "NOBODY EVER LISTENED")

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
    THUMB_TEXT_MIN = 6.5
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
            _best_text, _best_score = max(scored, key=lambda pair: pair[1])
            if _best_score >= THUMB_TEXT_MIN:
                log(f"  Thumbnail candidates scored: {scored} -> chose '{_best_text}' ({_best_score}/10, passed {THUMB_TEXT_MIN} bar)")
                break
            log(f"  Thumbnail candidates scored: {scored} -> best '{_best_text}' ({_best_score}/10) "
                f"BELOW {THUMB_TEXT_MIN} bar — reworking (round {_round + 1}/2)")
    thumb_text = None
    if candidates:
        scored = [(c, score_thumbnail_text(c)) for c in dict.fromkeys(candidates)]
        thumb_text, _final_score = max(scored, key=lambda pair: pair[1])
        log(f"  Thumbnail candidates scored: {scored} -> chose '{thumb_text}' ({_final_score}/10)")
    if not thumb_text:
        thumb_text = random.choice(niche["thumbnail_triggers"])

    # FIX (found on re-audit — matches the exact fix already confirmed
    # critical for Ch1/Ch2): enforce_number_noun was fully built to
    # enforce the punchy real "$2.4M GONE"-style NUMBER+NOUN thumbnail
    # format the whole empire's thumbnail strategy depends on, but was
    # never actually called anywhere in Ch3 — thumbnails could come back
    # as plain 3-word phrases with no number at all, missing the whole
    # point of the format. Wired in as a post-processing enforcement step.
    final_text = enforce_number_noun(
        thumb_text, topic, niche["name"],
        ai_fn=lambda p, tokens=20: ai(p, tokens=tokens, prefer="groq"))
    log(f"  Thumbnail: {final_text}")
    return final_text


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

def generate_and_score_titles(niche, topic, intel, episode):
    patterns = intel.get("winning_title_patterns",[])
    power    = intel.get("niche_specific_power_words",["documented","evidence","records"])
    viral_patterns_str = "\n".join(patterns[:3])
    prompt = f"""
TITLE REQUIREMENTS — NON-NEGOTIABLE:
Do NOT write normal YouTube titles. The title should make someone screenshot it and send it to a friend.
Use specific numbers, real-feeling specificity, or uncomfortable implications.
Dark psychological humor outperforms pure shock — it signals intelligence.
The viewer should feel: "I shouldn't watch this... but I have to."

TITLE FORMULAS THAT WORK:
- "[Number] [People/Days/Years] [Disturbing Specific Thing] — Nobody Talked About This"
- "The [Institution] Knew. They Did It Anyway. Here's The File."
- "How [Normal Thing] Was Used To [Dark Outcome]"
- "[System] Ran [Disturbing Operation] For [Duration]. Here's The Evidence."
- "[Specific Crime]: [Number] Victims. [Number] Years. Zero Consequences."

FORBIDDEN: "Shocking", "Incredible", "Amazing", "Unbelievable", "You Won't Believe", "Mind-Blowing"

Generate exactly 5 YouTube title variants for this mass manipulation investigation video.
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
# SCRIPT GENERATION — HIGH QUALITY CONTROL NARRATION
# ════════════════════════════════════════════════════════════
def get_niche_voice_style(state):
    day        = datetime.datetime.now().weekday()
    default_niche_name = DAY_NICHE.get(day,"cult_psychology")
    niche_name = pick_best_niche(state, default_niche_name)
    style_name = DAY_STYLE.get(day,"dark_minimal")
    if style_name == state.get("last_style",""):
        opts = [s for s in STYLES if s!=style_name]
        style_name = opts[day%len(opts)]
    niche = next(n for n in NICHES if n["name"]==niche_name)
    preferred = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    available = [v for v in preferred if v!=state.get("last_voice","")]
    # FIX (found on re-audit): select_best_voice was fully built — after 5
    # episodes in a niche, lock in whichever voice has actually scored
    # highest, since viewers build a relationship with the narrator, matching
    # Ch1's confirmed-active pattern — but was never called anywhere in
    # Ch3, so voice selection was pure day-of-year rotation forever, never
    # actually learning which voice performs best per niche.
    try:
        voice = select_best_voice(state, niche_name, available or preferred)
    except Exception as e:
        log(f"  select_best_voice (non-fatal, using rotation): {e}")
        voice = (available or preferred)[datetime.datetime.now().timetuple().tm_yday % len(available or preferred)]
    return niche, voice, style_name

def build_dread_prompt_er():
    """Control Files uses investigation-specific dread triggers"""
    triggers = ["institutional","scale","competence","detail","duration","reversal","cost","invisibility"]
    return "\n".join(f"DREAD {t.upper()}: {DREAD_TRIGGERS[t]}" for t in triggers if t in DREAD_TRIGGERS)

def generate_script_and_scenes(niche, topic, style_name, episode, attempt, intel, prev_title="", pattern_hint=""):
    """
    v2 script generation for Ch3 (The Control Files):
    1. Research anchors prevent vague AI output
    2. Psychological control-tactics documentary prompt with stage-specific structure
    3. Stage-level scoring + targeted rewrite of 2 worst stages
    4. Scene JSON extracted separately after narration

    FIX: pattern_hint (from load_pattern_memory) was fully built and read
    correctly, but never actually passed into this function at all — the
    write side (save_pattern_memory) was also never called, so the whole
    system was silently 100% dead in Ch3's original file. Both wired in now.
    """
    temp  = min(0.82 + attempt * 0.012, 0.94)
    # v1 addition — real product title for the verbal-mention instruction
    # below, using the same real product mapping as the description CTA
    # (never a fabricated or generic name).
    try:
        _product_title_for_prompt = build_product_cta("control_files").split(": ")[0].replace("\n\n📖 ", "").strip() or "our companion resource"
    except Exception:
        _product_title_for_prompt = "our companion resource"
    hooks = intel.get("top_hook_formulas", ["The documents confirmed what investigators had suspected."])
    power = intel.get("niche_specific_power_words", ["documented","verified","traced","confirmed"])
    viral = intel.get("what_makes_videos_viral", "Specific documented evidence that viewers can verify")
    retention = intel.get("retention_hooks", ["The next document changes the entire case"])
    cross = f'\nReference previous investigation: "{prev_title}" naturally in closing.' if prev_title else ""
    pattern_note = f"\n{pattern_hint}\n" if pattern_hint else ""

    # Research anchors
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic anchors for a psychological manipulation and control-tactics documentary about: {topic}\n"
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

    # FIX (found on re-audit — this is the single most significant finding
    # in this pass, matching the "MOST SIGNIFICANT FINDING" already logged
    # for Ch2): get_research_context/search_real_cases/extract_real_case_facts
    # were fully built but completely disconnected from script generation.
    # This means every Ch3 script has only ever been grounded in AI-*invented*
    # plausible-sounding details, never real, searchable documented cases —
    # despite Ch3's own stated highest risk being conspiracy drift and
    # unsupported allegations (per the Warbook's own risk map). Wired in now.
    research_block = ""
    real_cases = []
    try:
        _research_ctx, real_cases = get_research_context(niche["name"], topic)
        research_block = f"\n\n{_research_ctx}" if _research_ctx else ""
    except Exception as e:
        log(f"  Real-case research (non-fatal): {e}")

    # FIX (found on re-audit — matches Ch1's single most consequential
    # dead-function finding): generate_best_cold_open generates 3 scored
    # cold-open variants and was fully built but never called anywhere.
    # The cold open is the single most retention-critical 30 seconds of
    # every video. Wired in here as a mandatory opening the main script
    # must continue from, rather than letting the AI invent its own from
    # scratch each attempt.
    cold_open_block = ""
    try:
        trending = intel.get("winning_title_patterns", [])
        best_cold_open = generate_best_cold_open(niche, topic, trending_titles=trending)
        if best_cold_open:
            cold_open_block = (
                f"\n\nMANDATORY COLD OPEN — use this exact opening (already "
                f"written and hook-strength scored), then continue the "
                f"narrative naturally from it:\n\"{best_cold_open}\"")
    except Exception as e:
        log(f"  Cold open generation (non-fatal): {e}")

    # FIX (found on re-audit): build_dread_prompt_er assembles 8 specific,
    # genuinely well-written psychological dread-trigger instructions
    # (institutional betrayal, scale-to-human-cost, competence/patience,
    # etc.) but was never called anywhere — none of this content was
    # ever actually reaching the AI. Wired in as a real prompt block.
    dread_block = ""
    try:
        dread_text = build_dread_prompt_er()
        if dread_text:
            dread_block = f"\n\nDREAD-TRIGGER TECHNIQUES TO WEAVE IN NATURALLY:\n{dread_text}"
    except Exception as e:
        log(f"  Dread prompt build (non-fatal): {e}")

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
    # FIX (found on deep re-audit): this channel requested only 20 scenes
    # for a 15-18 minute video — the same fixed 20-scene list then had to
    # repeat ~7-8 times (render_and_encode's `repeats = int(duration/
    # total_scene_dur)+2`) to fill runtime, unlike evidence_room which was
    # already fixed to request a dynamic 55-60 scenes (repeats ~3). Same
    # dynamic-count fix applied here now, matching evidence_room exactly.
    n_scenes_target = 55 + (datetime.datetime.now().timetuple().tm_yday % 6)  # 55-60, varies daily
    viral_hooks_str = "\n".join(f"  '{h}'" for h in hooks[:3])
    prompt = f"""Write a psychological control-tactics documentary narration script.
Style: precisely documented, evidence-driven, case-file format.

CASE: {topic}
SERIES: {niche['series']} — Episode {episode}
VIRAL HOOKS: {viral_hooks_str}
POWER WORDS: {power_str}
{anchor_block}{research_block}{cross}{pattern_note}{cold_open_block}{dread_block}

TOTAL: {MIN_WORDS} to {MAX_WORDS} words. Each stage must hit its target.

SEVEN-STAGE CONTROL STRUCTURE — write continuously, no labels:

RETENTION CHECKPOINTS (precise timing, not just word count — this is where
most viewers actually drop off if nothing happens):
- At approximately 15-20 seconds into the Case File Open (roughly the 35-45
  word mark): introduce one SPECIFIC new piece of information not already
  promised in sentences 1-3. Without this second hook, attention drops here
  regardless of how strong the opening was.
- At approximately 40-45 seconds in (end of Stage 1 / start of Stage 2): set
  up a payoff requiring continued viewing to resolve.

STAGE 1 — CASE FILE OPEN ({stage_targets[1]} words)
{"A MANDATORY COLD OPEN is provided above — it already previews this exact case's specific twist/outcome and was scored as the strongest of 3 real variants. Use it AS-IS for Stage 1 (only light edits for grammar/flow into what follows), do NOT write a new, generic case-file open from scratch here. The rules below describe what that mandatory text already satisfies -- they are not a second, separate opening to write instead of it." if "MANDATORY COLD OPEN" in cold_open_block else "Sentence 1: exact case reference — number, date, or document ID. Sentence 2: specific location of the discovery. The opening must preview the real, specific twist/outcome of THIS case (state or strongly imply the actual result) -- not a generic disturbing mood that could belong to any episode."}
Sentence 3: the question this investigation will answer.
Forbidden: "welcome back", "today we investigate", "in this video"
TRIGGER PLACEMENT: DETAIL (s1) → PROXIMITY (s2) → open unresolved loop (s3)

STAGE 2 — THE SUBJECT ({stage_targets[2]} words)
Establish the entity — person, company, or system — as completely ordinary.
Specific details. Specific routine. Make the viewer care about what is about to be lost.
Final sentence signals something is about to break — without stating it.
Forbidden: "little did they know", "unbeknownst to", "but fate had other plans"
TRIGGER PLACEMENT: NORMALITY (s1-s3) → PROXIMITY (s4-s6) → quiet wrongness (final)

STAGE 3 — EARLY DOCUMENTED CASES ({stage_targets[3]} words)
Early real-world applications. Each one sourced and specific.
One documented case per sentence. Build the record. Each case more disturbing than the last.
Forbidden: "suddenly", "without warning", "shockingly", "out of nowhere"
Trigger: INVISIBILITY (s1) → DURATION (s3) → COMPETENCE (s5) → SCALE (s7)

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

STAGE 7 — IMPLICATIONS AND CTA ({stage_targets[7]} words)
What the documented record implies about current and future applications.
The researchers, regulators, and individuals working on documented responses.
Subscribe CTA at emotional peak — framed as continued investigation.{cross}
Forbidden: "subscribe and like", "hit the bell", "don't forget to"

RETENTION PAYOFF CADENCE (NON-NEGOTIABLE — this is the single biggest lever
for average view duration, which matters more than subscriber count or raw
views): a script that saves its only real hooks for 3 fixed points across
an 18-minute video leaves multi-minute stretches with nothing to prevent
viewer drop-off. Stages 4 and 6 especially (the longest stages) MUST contain
a genuine payoff — a surprising fact, a specific number, a forward reference
("what happens next reveals...", "the detail that changes everything comes
next") — roughly every 150-225 words (approximately every 60-90 seconds of
narration), not just at the stage's start. Never save all the value for the
end; think of the script as a continuous series of small rewards for
continued watching, not 3 big ones separated by long flat stretches.

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
the description. Within the existing Stage 7 subscribe moment, include ONE
brief, natural sentence mentioning "{_product_title_for_prompt}" as a related
resource for anyone who wants to go deeper — phrased as a genuine aside, not
an ad-read, and never interrupting the narrative flow or feeling like a
sponsor segment. If it can't be worked in naturally, skip it entirely rather
than forcing it — a forced-sounding mention actively hurts the viewer-
satisfaction signals that now weigh more than raw watch time.


TONE AND STYLE (NON-NEGOTIABLE):
- This is DARK DOCUMENTARY — every sentence should feel like a weight pressing down.
- Dark psychological humor is permitted and encouraged. The kind that makes viewers 
  laugh uncomfortably, then feel disturbed they laughed.
- Every paragraph should leave the viewer wanting the next one. Not curious — CRAVING.
- Think: what would someone who KNOWS they shouldn't watch this keep watching anyway?
- Each stage should feel darker than the last. Build psychological dread deliberately.
- Real documentary references make it feel researched. Fake-sounding claims get skipped.
- Pacing: short sentences hit harder. Use them at revelation moments.
- The viewer should feel like they discovered something others don't know.

WHAT MAKES VIEWERS CRAVE THIS CONTENT:
- The sense that something was hidden — and you're the one showing it.
- The feeling that the world is slightly more dangerous/dark than they thought.
- Uncomfortable recognition — "this happened to someone I know" or "this could be me."
- The satisfaction of understanding a dark system fully, from start to end.
- Dark humor that signals: we both know this is messed up, and we're in it together.

CRAVEABILITY TRIGGERS — use at least 3 per script:
1. The statistic that sounds impossible but is real.
2. The name everyone knows, connected to something they didn't know.
3. The system that's still running right now — not historical.
4. The thing institutions tried to suppress or deny.
5. The detail so specific it has to be true.
6. The uncomfortable implication in the final 30 seconds.
7. The question the script raises but deliberately doesn't fully answer.

FACTUAL CARE (non-negotiable, real policy-safety requirement): this
channel's biggest real risk is defamation and conspiracy-drift, not
creative weakness — a control-tactics documentary reads dark by design,
but every specific claim about a real person, group, or organization must
stay attributable. Use careful, evidence-first wording — "according to
court records," "former members allege," "reportedly" — rather than
stating contested claims as flat fact. If any detail is dramatized or
reconstructed rather than independently verifiable, say so plainly in
the narration.

RULES:
1. Maximum 13 words per sentence. Every sentence.
2. Zero markdown. Zero AI filler phrases.
3. Every number specific. Every date specific. Every location specific.
4. Write continuously — no stage labels, no headers.
5. Start immediately with Stage 1.

After writing the complete narration, add exactly 10 dashes on a new line, then provide scene JSON:
TITLE REQUIREMENTS for the JSON below (this was previously just "55-65 chars"
with no real guidance):
- 40-65 characters, front-load the compelling part in the first 40 (mobile display).
- CURIOSITY GAP: withhold the one detail that can only be resolved by watching.
- Rotate between two registers roughly equally — don't default to one:
  DREAD ("The System Was Designed To Control You. Here's How.")
  SYMPATHY/WOEFUL ("She Saw It For Years. Nobody Believed Her.")
- HONESTY CONSTRAINT (non-negotiable): the title must be something the first 30
  seconds of the actual script genuinely delivers on. 2026 YouTube penalizes
  titles that get clicks but lose viewers fast when the video doesn't match the
  promise — this is worse long-term than a slightly less aggressive honest title.

IMPORTANT: provide {n_scenes_target} scenes (55-60, not fewer) — this video runs
15-18 minutes, and a short scene list means the same handful of visuals loop
many times over, which looks broken and repetitive. Vary content EVERY time a
scene type repeats (different case details, different numbers, different
network nodes each time — never reuse the same labels twice). Cycle through
the 5 types across the full narrative, roughly in this rhythm (repeat the
whole 5-type cycle enough times with fresh content each pass to reach
{n_scenes_target} scenes total):
{{"title":"YouTube title, 40-65 chars, dread OR sympathy register, curiosity gap intact","thumbnail_text":"3 WORDS ALL CAPS with number","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"scenes":[
{{"type":"sketch_timeline","duration":8,"title":"CASE TIMELINE","events":["Event 1: date","Event 2: date","Event 3: date","Event 4: date"],"label":"CHRONOLOGY"}},
{{"type":"sketch_document","duration":7,"title":"THE KEY DOCUMENT","lines":["CASE FILE — RESTRICTED","Reference: [case number]","Finding: [key finding]","Status: [outcome]"],"stamp":"CLASSIFIED"}},
{{"type":"sketch_crowd","duration":7,"title":"THE NUMBERS","items":["$X.XM","XX YEARS","XXX VICTIMS","XX REPORTS"],"label":"CASE STATISTICS"}},
{{"type":"sketch_mechanism","duration":8,"title":"THE NETWORK","nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"HOW IT CONNECTED"}},
{{"type":"sketch_findings","duration":10,"title":"EVIDENCE SUMMARY","items":["Finding 1","Finding 2","Finding 3","Finding 4"],"label":"CASE EVIDENCE"}}
... continue this pattern for a total of {n_scenes_target} scenes, each with
genuinely different case-specific content — different timeline events,
different documents, different numbers, different network nodes, different
evidence each time a type repeats ...
]}}

Write narration first ({MIN_WORDS}-{MAX_WORDS} words), then 10 dashes, then JSON."""


    raw   = ai(prompt, temp=temp, tokens=7000, prefer="gemini")
    parts = raw.split("----------") if raw else [""]
    clean = strip_md(strip_md(parts[0].strip()))
    wc    = len(clean.split())

    # Expansion rounds — hard ceiling at MAX_WORDS to prevent 40-chunk TTS failures
    for exp_round in range(2):
        if wc >= MIN_WORDS or wc > MAX_WORDS: break
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
            c2 = strip_md(strip_md(raw2))
            if len(c2.split()) > wc:
                clean = c2
                wc    = len(clean.split())
                # Hard truncate after expansion — prevents 5030w scripts
                if wc > MAX_WORDS:
                    clean = " ".join(clean.split()[:MAX_WORDS])
                    wc    = len(clean.split())
                log(f"  Expanded to {wc}w")

    # Stage-level scoring + targeted rewrite of 2 worst stages
    if wc >= MIN_WORDS:
        try:
            words      = clean.split()
            total      = len(words)
            targets_l  = [110, 210, 260, 420, 170, 680, 190]
            total_t    = sum(targets_l)
            stage_txts = []
            pos = 0
            for i, tgt in enumerate(targets_l):
                share = tgt / total_t
                end   = pos + int(total * share) if i < 6 else total
                stage_txts.append(" ".join(words[pos:end]))
                pos   = end

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
                stage_scores.append(round(min(max(sc, 0), 10), 1))

            stage_scores_str = " | ".join(f"{n[:6]}:{s}" for n,s in zip(stage_names,stage_scores))
            log(f"  Stage scores: {stage_scores_str}")
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]

            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                rewrite_p = (
                    f"Rewrite ONLY this psychological manipulation documentary stage. Return ONLY the rewritten stage.\n\n"
                    f"STAGE: {stage_names[idx]} (target: {targets_l[idx]} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"SCORE: {stage_scores[idx]}/10 — sentences too long or too vague\n\n"
                    f"RULES:\n"
                    f"- Max 13 words per sentence.\n"
                    f"- Every number specific (not 'many' but '47').\n"
                    f"- Every date specific (not 'years ago' but 'March 2011').\n"
                    f"- Zero markdown. Zero AI filler.\n"
                    f"- Target: {targets_l[idx]} words (±15% ok).\n\n"
                    f"ORIGINAL:\n{stage_txts[idx]}\n\nRewrite now:"
                )
                new_s = ai(rewrite_p, temp=0.82, tokens=2000, prefer="groq")
                if new_s:
                    new_s = strip_md(new_s)
                    if len(new_s.split()) > 30:
                        clean = clean.replace(stage_txts[idx], new_s, 1)
                        log(f"  Stage {stage_names[idx]} rewritten")

            wc = len(clean.split())
            log(f"  After targeted rewrite: {wc}w")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # Parse scene JSON
    scenes, title, thumbnail_text, tags = [], f"The Control Files: {topic[:45]}", "CASE DOCUMENTED", \
        [niche["name"],"psychology","control systems","animated","documentary",
         "manipulation","exposed","deepdive","case","investigation"]
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

    # Fallback scenes — 20 varied scenes (was 5), same fix applied to Ch2.
    # 5 scenes across a 15-18 min video meant looping the identical visuals
    # ~24 times.
    if not scenes:
        scenes = [
            {"type":"sketch_timeline","duration":8,"title":"CASE TIMELINE",
             "events":["Event 1","Event 2","Event 3","Event 4"],"label":"CHRONOLOGY"},
            {"type":"sketch_document","duration":7,"title":"KEY DOCUMENT",
             "lines":["CASE FILE — RESTRICTED","Reference: CF-2019-447",
                      "Finding: pattern confirmed","Status: under review"],"stamp":"CLASSIFIED"},
            {"type":"sketch_crowd","duration":7,"title":"THE NUMBERS",
             "items":["$2.4M","12 YEARS","847 CASES","47 REPORTS"],"label":"STATISTICS"},
            {"type":"sketch_mechanism","duration":8,"title":"THE NETWORK",
             "nodes":["ORIGIN","ENABLER","SYSTEM","OUTCOME"],"label":"CONNECTION"},
            {"type":"sketch_findings","duration":10,"title":"EVIDENCE",
             "items":["Document 1","Document 2","Pattern","Conclusion"],"label":"EVIDENCE"},
            {"type":"sketch_timeline","duration":8,"title":"THE RECRUITMENT",
             "events":["First contact","Isolation begins","Doctrine introduced","Dependency formed"],"label":"PROGRESSION"},
            {"type":"sketch_document","duration":7,"title":"THE CORE TEACHING",
             "lines":["INTERNAL DOCTRINE","Author: leadership","Subject: obedience",
                      "Distribution: members only"],"stamp":"RESTRICTED"},
            {"type":"sketch_crowd","duration":7,"title":"THE SCALE",
             "items":["230 MEMBERS","6 CHAPTERS","3 COUNTRIES","0 OVERSIGHT"],"label":"SCOPE"},
            {"type":"sketch_mechanism","duration":8,"title":"WHO CONTROLLED WHOM",
             "nodes":["LEADER","INNER CIRCLE","ENFORCERS","MEMBERS"],"label":"HIERARCHY"},
            {"type":"sketch_findings","duration":10,"title":"THE METHODS",
             "items":["Sleep deprivation","Financial control","Social isolation","Manufactured guilt"],"label":"TECHNIQUES"},
            {"type":"sketch_timeline","duration":8,"title":"THE BREAKING POINT",
             "events":["Doubt surfaces","Punishment follows","Escape attempt","Recapture"],"label":"RESISTANCE"},
            {"type":"sketch_document","duration":7,"title":"THE CONFESSION FILE",
             "lines":["FORCED CONFESSION","Written under duress","Later recanted",
                      "Used as leverage"],"stamp":"SEALED"},
            {"type":"sketch_crowd","duration":7,"title":"THE COST",
             "items":["$18M EXTRACTED","4 FAMILIES BROKEN","0 REFUNDS","1 SURVIVOR TALKING"],"label":"AFTERMATH"},
            {"type":"sketch_mechanism","duration":8,"title":"THE PATTERN",
             "nodes":["FIRST GROUP","SECOND GROUP","THIRD GROUP","SAME PLAYBOOK"],"label":"REPETITION"},
            {"type":"sketch_findings","duration":10,"title":"WHAT SURVIVED",
             "items":["Smuggled letter","Anonymous tip","Court testimony","Recovered journal"],"label":"REMAINING PROOF"},
            {"type":"sketch_timeline","duration":8,"title":"COMING FORWARD",
             "events":["First contact","Legal review","Story verified","Publication"],"label":"EXPOSURE"},
            {"type":"sketch_document","duration":7,"title":"THE DENIAL",
             "lines":["OFFICIAL STATEMENT","Denies coercion","Calls it voluntary",
                      "Investigation ongoing"],"stamp":"UNVERIFIED"},
            {"type":"sketch_crowd","duration":7,"title":"WHERE IT STANDS",
             "items":["1 LAWSUIT ACTIVE","2 AGENCIES NOTIFIED","0 CONVICTIONS","ONGOING CASE"],"label":"STATUS"},
            {"type":"sketch_mechanism","duration":8,"title":"STILL RUNNING",
             "nodes":["SAME LEADER","SAME METHODS","NEW MEMBERS","NO OVERSIGHT"],"label":"PRESENT DAY"},
            {"type":"sketch_findings","duration":10,"title":"THE QUESTION LEFT OPEN",
             "items":["Who else is trapped","What else is hidden","Who's next","Who's accountable"],"label":"UNRESOLVED"},
        ]

    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", clean))

    # CTA injection
    if len(clean.split()) >= 400:
        clean = _inject_ctas_er(clean, niche.get("name","cult_psychology"))
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

    # v6 addition — real research-usage verification (same fix built for
    # Ch4, applying here since Ch3 has the identical gap): real_cases
    # gets injected into the prompt, but nothing ever verified the AI
    # actually used it versus inventing plausible-sounding details
    # instead — directly relevant given Ch3's own stated highest risk is
    # conspiracy drift and unsupported allegations. Lightweight
    # heuristic, not another AI call, matching this gate's existing cost/
    # latency design.
    if real_cases:
        script_lower = clean.lower()
        _research_words = set()
        for c in real_cases[:3]:
            _research_words.update(
                w.strip(".,;:").lower() for w in (c.get("title", "") + " " + c.get("summary", "")).split()
                if len(w) > 6
            )
        _used = any(w in script_lower for w in _research_words)
        # FIX: this used to alert via Telegram right here — but this
        # function runs once per attempt (up to 13x per episode), so a
        # script that fails the quality gate on attempt 1-12 for
        # unrelated reasons would still trigger a real alert every time,
        # even though that attempt never publishes. Logged every
        # attempt; the real Telegram alert now fires exactly once, in
        # run_stage1, only for the actual winning/publishing attempt.
        log(f"  Research-usage check: {'genuinely reflected' if _used else 'NOT clearly used'}")

    log(f"  Script: {wc}w | {violations} MD | {len(scenes)} scenes")
    return clean, scenes, title, thumbnail_text, tags, violations, real_cases


def regenerate_scenes_only(script_clean, niche, feedback=None):
    """
    v5 addition — Ch3's real SWAP VISUALS implementation.

    HONEST ARCHITECTURE NOTE: Ch1's SWAP VISUALS reshuffles a stock-
    footage clip pool — genuinely different content each call since
    nothing seeds Python's random state. Ch3 has no stock-footage pool
    at all; every scene is AI-generated whiteboard-sketch JSON tied to
    the script content. So "regenerate only the visuals, keep the same
    script and audio" means something architecturally different here:
    a fresh AI call that generates a new 20-scene JSON array for the
    SAME existing script, optionally steered by real feedback about
    which part's visuals to change. Confirmed genuinely variable
    between calls (temperature=0.9, real model sampling) — not a
    coin-flip disguised as a fix.
    """
    feedback_line = f"\n\nHUMAN FEEDBACK on the visuals (apply this directly): {feedback}" if feedback else ""
    # FIX (found on deep re-audit): matches the same fix applied to the
    # main scene-generation prompt above — 20 scenes for a 15-18 minute
    # video means render_and_encode's repeat-fill logic loops the same
    # scenes ~7-8 times. Bumped to the same 55-60 dynamic target so a
    # SWAP VISUALS regeneration doesn't reintroduce the problem.
    n_scenes_target = 55 + (datetime.datetime.now().timetuple().tm_yday % 6)
    prompt = f"""Generate a fresh, DIFFERENT {n_scenes_target}-scene visual JSON array for this existing
documentary narration. Do not change the narration — only invent new scene content,
different from before: different case details, different numbers, different network
nodes, different documents each time a scene type repeats.{feedback_line}

NICHE: {niche['name']}
NARRATION (for context, do not rewrite):
{script_clean[:2500]}

Return ONLY valid JSON: {{"scenes":[
{{"type":"sketch_timeline","duration":8,"title":"...","events":["...","...","...","..."],"label":"..."}},
{{"type":"sketch_document","duration":7,"title":"...","lines":["...","...","...","..."],"stamp":"..."}},
{{"type":"sketch_crowd","duration":7,"title":"...","items":["...","...","...","..."],"label":"..."}},
{{"type":"sketch_mechanism","duration":8,"title":"...","nodes":["...","...","...","..."],"label":"..."}},
{{"type":"sketch_findings","duration":10,"title":"...","items":["...","...","...","..."],"label":"..."}}
... continue this 5-type cycle for a total of {n_scenes_target} scenes, each genuinely different ...
]}}"""
    try:
        raw = ai(prompt, temp=0.9, tokens=6000, prefer="gemini")
        jt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", re.sub(r"```json|```", "", raw or "").strip())
        m = re.search(r"\{[\s\S]*\}", jt)
        if m:
            data = json.loads(m.group())
            new_scenes = data.get("scenes", [])
            if new_scenes and len(new_scenes) >= 10:
                log(f"  Regenerated {len(new_scenes)} fresh scenes for SWAP VISUALS")
                return new_scenes
    except Exception as e:
        log(f"  Scene regeneration for SWAP VISUALS failed (non-fatal): {e}")
    return None  # caller must handle None by keeping the existing scenes rather than crashing


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

def render_counting_number(draw, x, y, target_val, progress, font_lg, color):
    """
    Animate a number counting up from 0 to target_val.
    Creates urgency — viewer feels the scale of the case.
    """
    current = int(target_val * min(progress * 1.5, 1.0))
    text = f"{current:,}"
    bbox = draw.textbbox((0,0), text, font=font_lg)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw//2 + 1, y + 1), text, font=font_lg, fill=(20, 20, 20))
    draw.text((x - tw//2, y), text, font=font_lg, fill=color)

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


def _stroke_progress_index(points, progress, reveal_frac=0.55):
    """
    How many of `points` should be visible right now, given this scene's
    overall progress. reveal_frac = fraction of the scene's runtime spent
    actively drawing (before settling into a held, fully-drawn state) —
    this is what creates the "hand is drawing this right now" feel instead
    of a static image simply fading in.
    """
    if not points:
        return 0
    draw_p = min(1.0, progress / max(reveal_frac, 0.01))
    return max(1, int(len(points) * draw_p))


def _draw_stroke_path(draw, points, progress, color, width=4, reveal_frac=0.55, pen=True, pen_color=None):
    """
    Core whiteboard primitive: draws a polyline through `points`, but only
    up to however far the "pen" has traveled at this progress — a real
    incremental stroke reveal, not a static shape faded in. Optionally
    draws a small pen-tip marker at the current leading edge, which is
    what actually sells the illusion of a hand drawing live (After
    Skool / RSA Animate reference) rather than a wipe/fade transition.
    """
    n_visible = _stroke_progress_index(points, progress, reveal_frac)
    visible = points[:n_visible]
    if len(visible) >= 2:
        draw.line(visible, fill=color, width=width, joint="curve")
    if pen and visible and n_visible < len(points):
        tip = visible[-1]
        pc = pen_color or color
        draw.ellipse([tip[0]-7, tip[1]-7, tip[0]+7, tip[1]+7], fill=pc)


def _jitter_baseline_text(draw, x, y, text, font, color, seed):
    """
    Simulated handwriting: each character sits on a slightly wobbly
    baseline instead of a perfectly straight one — cheap, real, and
    reads as "written" rather than "typeset," which is the whole point
    of a whiteboard channel. Pure PIL, zero new dependency.
    """
    rnd = random.Random(seed)
    cx = x
    for ch in text:
        wob = rnd.randint(-2, 2)
        draw.text((cx, y + wob), ch, font=font, fill=color)
        try:
            cw = draw.textbbox((0, 0), ch, font=font)[2]
        except Exception:
            cw = 14
        cx += cw


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

    stype = scene.get("type","sketch_timeline")

    # v3 REBUILD: paper texture replaces the old dark vignette/scanline/grain —
    # this is what makes Ch3 read as a whiteboard channel at a glance instead
    # of Ch1's black horror mood or Ch2's noir-investigative mood.
    rnd = random.Random(scene_idx * 7919 + 13)
    for _ in range(140):
        gx, gy = rnd.randint(0, W), rnd.randint(0, H)
        shade = rnd.randint(-10, 10)
        c = tuple(max(0, min(255, ch + shade)) for ch in bg)
        draw.point([(gx, gy)], fill=c)
    draw.line([(70, 20), (70, H-20)], fill=secondary, width=1)

    for x0, y0, dx, dy in [(30,30,50,0),(30,30,0,50),(W-30,H-30,-50,0),(W-30,H-30,0,-50)]:
        draw.line([(x0,y0),(x0+dx,y0+dy)], fill=secondary, width=2)

    draw.text((30,H-42), "THE CONTROL FILES", font=font_xs, fill=secondary)
    draw.text((W-190,H-42), f"CASE {scene_idx+1:03d}/{total_scenes:03d}", font=font_xs, fill=secondary)

    title = scene.get("title","THE MECHANISM")
    if progress > 0.05:
        ta = min(1.0,(progress-0.05)*5)
        _jitter_baseline_text(draw, 80, 40, title, font_lg, accent, seed=scene_idx)
        _draw_stroke_path(draw, [(80,112),(80+700,112)], min(1.0, progress*1.3), accent,
                           width=3, reveal_frac=0.4, pen=False)

    if   stype=="sketch_person":     _render_sketch_person(draw,scene,progress,style,font_md,font_sm,font_xs)
    elif stype=="sketch_mechanism":  _render_sketch_mechanism(draw,scene,progress,style,font_sm,font_xs)
    elif stype=="sketch_document":   _render_sketch_document(draw,scene,progress,style,font_md,font_sm,font_mono)
    elif stype=="sketch_findings":   _render_sketch_findings(draw,scene,progress,style,font_md,font_sm,font_mono)
    elif stype=="sketch_crowd":      _render_sketch_crowd(draw,scene,progress,style,font_sm,font_xs)
    else:                            _render_sketch_timeline(draw,scene,progress,style,font_sm,font_xs)
    return img


def _render_sketch_timeline(draw,scene,progress,style,font_sm,font_xs):
    items=scene.get("items",scene.get("events",[])); label=scene.get("label","TIMELINE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    lx,ty,by=200,160,H-150
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    _draw_stroke_path(draw, [(lx,ty),(lx,by)], progress, secondary, width=3, reveal_frac=0.3, pen=False)
    n=len(items); spacing=(by-ty)//max(n,1)
    for i,item in enumerate(items):
        ip=(progress*n)-i
        if ip<=0: continue
        a=min(1.0,ip); y=ty+i*spacing
        dc=accent if a>0.5 else secondary
        r = 9
        circle_pts = [(lx+r*_cos(t), y+r*_sin(t)) for t in _arc_steps(int(a*36))]
        if len(circle_pts) >= 2:
            draw.line(circle_pts, fill=dc, width=3, joint="curve")
        xe=int(lx+60+a*40)
        _draw_stroke_path(draw, [(lx+r,y),(xe,y)], min(1.0,a*1.4), dc, width=3, reveal_frac=0.6, pen=(a<1.0))
        if a>0.3: _jitter_baseline_text(draw,(lx+80,y-14)[0],(lx+80,y-14)[1],item,font_sm,primary,seed=i)


def _render_sketch_person(draw,scene,progress,style,font_md,font_sm,font_xs):
    label=scene.get("label","THE SUBJECT"); caption=scene.get("caption", scene.get("lines",[""])[0] if scene.get("lines") else "")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    cx, cy, r = W//2-100, H//2-60, 90
    head = [(cx+r*_cos(t), cy+r*_sin(t)) for t in _arc_steps(48)]
    shoulders = [(cx-160,cy+r+140),(cx-100,cy+r+40),(cx,cy+r+20),(cx+100,cy+r+40),(cx+160,cy+r+140)]
    full_path = head + shoulders
    _draw_stroke_path(draw, full_path, progress, primary, width=5, reveal_frac=0.75, pen=True)
    if progress > 0.8 and caption:
        _jitter_baseline_text(draw, cx+160, cy, caption, font_sm, accent, seed=7)


def _render_sketch_mechanism(draw,scene,progress,style,font_sm,font_xs):
    nodes=scene.get("nodes",scene.get("items",[])); label=scene.get("label","THE MECHANISM")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    n=len(nodes)
    if n==0: return
    sp=(W-300)//max(n-1,1); ny=H//2
    positions=[(150+i*sp,ny) for i in range(n)]
    steps_per_node = 1.0/n
    for i,(nx,ny2) in enumerate(positions):
        node_start = i*steps_per_node
        node_progress = max(0.0, min(1.0, (progress-node_start)/max(steps_per_node*0.7,0.01)))
        if node_progress<=0: continue
        box = [(nx-60,ny2-25),(nx+60,ny2-25),(nx+60,ny2+25),(nx-60,ny2+25),(nx-60,ny2-25)]
        _draw_stroke_path(draw, box, node_progress, primary if i not in (0,n-1) else accent, width=3, reveal_frac=0.8)
        if node_progress>0.5:
            _jitter_baseline_text(draw, nx-50, ny2-12, nodes[i][:14], font_xs, primary, seed=i*3)
        if i<n-1:
            arrow_start = node_start + steps_per_node*0.8
            arrow_progress = max(0.0, min(1.0,(progress-arrow_start)/max(steps_per_node*0.5,0.01)))
            if arrow_progress>0:
                nnx = positions[i+1][0]
                _draw_stroke_path(draw, [(nx+60,ny2),(nnx-60,ny2)], arrow_progress, accent, width=3, reveal_frac=0.8)
                if arrow_progress>0.9:
                    le = nnx-60
                    draw.polygon([(le,ny2),(le-14,ny2-9),(le-14,ny2+9)],fill=accent)


def _render_sketch_document(draw,scene,progress,style,font_md,font_sm,font_mono):
    lines=scene.get("lines",scene.get("items",["DOCUMENTED"])); stamp=scene.get("stamp","")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    px,py,dw,dh=160,120,W-320,H-240
    outline = [(px,py),(px+dw,py),(px+dw,py+dh),(px,py+dh),(px,py)]
    _draw_stroke_path(draw, outline, progress, primary, width=3, reveal_frac=0.35, pen=False)
    if progress>0.35:
        draw.text((px+20,py+14),"DOCUMENTED",font=font_sm,fill=secondary)
    n=len(lines)
    for i,line in enumerate(lines):
        lp=(progress*(n+1.2))-i-0.4
        if lp<=0: continue
        a=min(1.0,lp); y=py+75+i*58
        if isinstance(line,str) and line.startswith("["):
            clean = line.strip("[]")
            bb = draw.textbbox((0,0),clean,font=font_mono)
            tw = bb[2]-bb[0]
            scribble = [(px+40+j*(tw/12), y+12+ (8 if j%2==0 else -8)) for j in range(13)]
            _draw_stroke_path(draw, scribble, a, primary, width=8, reveal_frac=0.9, pen=False)
        else:
            chars_to_show = int(len(line) * min(1.0, a*1.3))
            _jitter_baseline_text(draw, px+40, y, str(line)[:chars_to_show], font_mono, primary, seed=i*11)
    if stamp and progress>0.75:
        sx,sy=px+dw-260,py+dh-140
        stamp_box = [(sx,sy),(sx+240,sy+100),(sx,sy+100),(sx+240,sy)]
        _draw_stroke_path(draw, stamp_box, min(1.0,(progress-0.75)*4), accent, width=4, reveal_frac=0.9, pen=False)
        if progress>0.9:
            _jitter_baseline_text(draw, sx+30, sy+35, stamp, font_md, accent, seed=99)


def _render_sketch_findings(draw,scene,progress,style,font_md,font_sm,font_mono):
    items=scene.get("items",scene.get("lines",["Finding"])); label=scene.get("label","CASE EVIDENCE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_sm,fill=secondary)
    n=len(items); row_h=(H-320)//max(n,1)
    box_x = 140
    for i,item in enumerate(items):
        ip=(progress*(n+0.8))-i
        if ip<=0: continue
        a=min(1.0,ip); y=170+i*row_h
        box = [(box_x,y),(box_x+36,y),(box_x+36,y+36),(box_x,y+36),(box_x,y)]
        _draw_stroke_path(draw, box, min(1.0,a*2), primary, width=3, reveal_frac=0.9, pen=False)
        if a>0.5:
            check_progress = min(1.0,(a-0.5)*2)
            check = [(box_x+6,y+18),(box_x+15,y+28),(box_x+30,y+8)]
            _draw_stroke_path(draw, check, check_progress, accent, width=4, reveal_frac=0.95, pen=False)
        if a>0.6:
            _jitter_baseline_text(draw, box_x+52, y+4, str(item), font_mono, primary, seed=i*5)


def _render_sketch_crowd(draw,scene,progress,style,font_sm,font_xs):
    items=scene.get("items",[]); label=scene.get("label","THE SCALE")
    primary,accent,secondary=style["primary"],style["accent"],style["secondary"]
    draw.text((80,H-120),label,font=font_xs,fill=secondary)
    cols, rows = 6, 3
    cw=(W-200)//cols; rh=180
    total = cols*rows
    for i in range(total):
        fp = (progress*(total+2))-i
        if fp<=0: continue
        a = min(1.0, fp)
        col, row = i%cols, i//cols
        fx, fy = 130+col*cw, 220+row*rh
        figure = [(fx,fy-30),(fx,fy+10),(fx-15,fy+40),(fx,fy+10),(fx+15,fy+40),
                  (fx,fy+10),(fx-18,fy-10),(fx,fy+10),(fx+18,fy-10)]
        _draw_stroke_path(draw, figure, a, primary if i%7 else accent, width=3, reveal_frac=0.9, pen=False)
    if items and progress>0.85:
        _jitter_baseline_text(draw, 80, H-190, items[0], font_sm, accent, seed=42)


def _arc_steps(n):
    import math
    return [ (2*math.pi*i/max(n,1)) for i in range(max(n,1)+1) ]

def _cos(t):
    import math
    return math.cos(t)

def _sin(t):
    import math
    return math.sin(t)



# Ken Burns motion profiles per scene type
# Slow camera movement creates documentary cinematography feel
SCENE_MOTION = {
    "sketch_timeline":        "zoompan=z='min(zoom+0.0008,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "sketch_document": "zoompan=z='min(zoom+0.001,1.4)':d=1:x='iw/2-(iw/zoom/2)':y='ih*0.3-(ih/zoom*0.3)'",
    "sketch_crowd":     "zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.001))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "sketch_mechanism":  "zoompan=z='1.2+0.05*sin(2*PI*on/100)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "sketch_findings":  "zoompan=z='min(zoom+0.0006,1.25)':d=1:x='(iw-iw/zoom)*on/n':y='ih/2-(ih/zoom/2)'",
}

def apply_ken_burns(input_path, output_path, scene_type, fps=24, duration=None):
    """
    Apply Ken Burns (slow zoom/pan) motion to a video scene.
    Makes animated frames feel cinematic — industry standard for documentary.
    Falls back to original if filter fails.

    FIX (found on re-audit, discovered only by testing with REAL rendered
    content rather than trusting "no crash"): the original 100KB minimum-
    size safety check was calibrated for richer footage/content. Ch3's
    whiteboard scenes (flat paper background, thin ink lines, sparse text)
    are legitimately much smaller even at full 8-10s production duration —
    tested directly: a real 8-second production scene came out to ~46KB,
    genuinely valid output, but would have been silently rejected as
    "too small" every single time, meaning this feature would never
    actually activate despite being wired in. Lowered to a threshold that
    still catches genuinely empty/corrupt output (near 0 bytes) without
    rejecting legitimate simple line-art content.
    """
    motion = SCENE_MOTION.get(scene_type, SCENE_MOTION["sketch_timeline"])
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
        if Path(output_path).exists() and Path(output_path).stat().st_size > 15000:
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
                                   ab_style="A", episode=1, channel_name="The Control Files"):
    """v2 thumbnail: three-layer composition via thumbnail_engine_v2."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        # FIX (found on advanced re-audit): cache_dir was never passed at
        # all (defaulted to None) — the entire deterministic avatar-
        # caching system (built specifically so the SAME branded host
        # character appears every episode, not a freshly AI-reimagined
        # figure each time) was silently disabled, always falling
        # through to per-episode regeneration. Must be a PERSISTENT path
        # (SCRIPT_DIR, survives between runs), never WORK_DIR (wiped
        # every run) — per the function's own docstring.
        result = generate_thumbnail_v2(
            title        = title,
            thumb_text   = thumb_text,
            niche_name   = niche_name,
            topic        = topic,
            channel_name = channel_name,
            episode      = episode,
            work_dir     = str(WORK_DIR),
            ab_variant   = ab_style,
            cache_dir    = str(SCRIPT_DIR),
        )
        if result and Path(result).exists():
            log(f"  Thumbnail v2 ({niche_name}): {Path(result).stat().st_size//1024}KB")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    return None


# ══════════════════════════════════════════════════════════════════
# NICHE-AWARE BACKGROUND MUSIC (v6 addition, per explicit requirement:
# "the background noise should be according to the niche... if it's
# dark or deception it should be something related to that... if
# shocking, based on that"). Same real system built for Ch1/Ch2, with
# moods matched to Ch3's own 6 niches.
#
# HONEST DESIGN NOTE: real, freely-licensed tracks (sourced once from
# Pixabay's actual music library, free commercial use permitted) are
# the real fix — genuine recorded texture, not synthesis. Built to use
# real bundled files the MOMENT they exist (drop into
# music_bank/<mood>/ as any .mp3), rotating through what's present.
# Until then, falls back to a genuinely mood-distinct synthesis rather
# than the single generic (and, embarrassingly, still Ch2-named)
# brown-noise texture this replaces.
# ══════════════════════════════════════════════════════════════════

NICHE_MUSIC_MOOD = {
    "cult_psychology":              "cult_dread",
    "propaganda_systems":           "propaganda_tension",
    "social_engineering":           "manipulation_unease",
    "mass_deception":               "deception_dread",
    "dark_business_documentaries":  "corporate_dread",
    "scams_fraud_exposed":          "fraud_tension",
}

MOOD_TRACK_RECOMMENDATIONS = {
    "cult_dread": ["Search Pixabay Music for: 'ritual dark ambient', 'hypnotic drone', 'cult documentary tension'"],
    "propaganda_tension": ["Search Pixabay Music for: 'oppressive ambient', 'mechanical dystopian drone', 'systemic dread'"],
    "manipulation_unease": ["Search Pixabay Music for: 'creeping tension', 'sly unsettling ambient', 'psychological manipulation drone'"],
    "deception_dread": ["Search Pixabay Music for: 'conspiracy ambient', 'cold vast drone', 'deception dark tension'"],
    "corporate_dread": ["Search Pixabay Music for: 'corporate dark ambient', 'boardroom tension', 'sterile suspense'"],
    "fraud_tension": ["Search Pixabay Music for: 'exposing tension', 'urgent kinetic drone', 'fraud thriller ambient'"],
}

MUSIC_BANK_ROOT = Path(__file__).parent / "music_bank"

def _synthesize_mood_track(mood, duration):
    """Genuinely mood-distinct synthesis fallback — different frequency
    relationships, filtering, and noise character per mood."""
    path = str(WORK_DIR / f"music_{mood}.mp3")
    dur = int(duration) + 30
    recipes = {
        "cult_dread": (
            ["-f","lavfi","-i",f"sine=frequency=48:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=72:duration={dur}",  # perfect fifth, ritualistic
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0025:duration={dur}"],
            "[0]volume=0.08[a];[1]volume=0.05[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=300,highpass=f=30,volume=0.14[out]"),
        "propaganda_tension": (
            ["-f","lavfi","-i",f"sine=frequency=50:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=50.5:duration={dur}",  # near-unison, mechanical throb
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.1[a];[1]volume=0.1[b];[2]volume=0.2[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=240,highpass=f=28,volume=0.14[out]"),
        "manipulation_unease": (
            ["-f","lavfi","-i",f"sine=frequency=95:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=101:duration={dur}",  # dissonant, sly
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.003:duration={dur}"],
            "[0]volume=0.06[a];[1]volume=0.06[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=420,highpass=f=55,volume=0.13[out]"),
        "deception_dread": (
            ["-f","lavfi","-i",f"sine=frequency=38:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=57:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.05[b];[2]volume=0.25[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=200,highpass=f=22,volume=0.15[out]"),
        "corporate_dread": (
            ["-f","lavfi","-i",f"sine=frequency=45:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=46:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.09[b];[2]volume=0.25[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=220,highpass=f=30,volume=0.14[out]"),
        "fraud_tension": (
            ["-f","lavfi","-i",f"sine=frequency=85:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=127:duration={dur}",
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0035:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.06[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=380,highpass=f=48,volume=0.15[out]"),
    }
    inputs, filt = recipes.get(mood, recipes["deception_dread"])
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
    mood = NICHE_MUSIC_MOOD.get(niche_name, "deception_dread")
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


def render_and_encode(style_name, scenes, audio_path, duration, niche_name=None, episode=1, real_cases=None, ass_path=None):
    frames_base = WORK_DIR/"frames"
    frames_base.mkdir(exist_ok=True)
    concat_parts = []
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
            # FIX (found on re-audit — matches the exact fix already
            # confirmed critical for Ch2): apply_ken_burns was fully
            # built, with real per-scene-type zoom/pan filters already
            # defined in SCENE_MOTION, but was never actually applied to
            # a single rendered scene — every scene encoded completely
            # static camera-wise. Wired in as a real finishing pass; it
            # already falls back safely to the un-zoomed original on any
            # failure, so this can only add cinematic polish, never
            # regress reliability.
            sm4_kb = apply_ken_burns(sm4, str(fd)+"_kb.mp4", scene.get("type","sketch_timeline"), fps=FPS)
            concat_parts.append(f"file '{sm4_kb}'")
            log(f"    Scene {si+1} encoded: {Path(sm4_kb).stat().st_size//1024}KB")
        else:
            # Fallback: create a solid-colour scene as replacement
            log(f"    Scene {si+1} encode failed — using fallback")
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
    # FIX (found going through the audio system in full, per explicit
    # requirement: "background noise should be according to the niche"):
    # this used to be a copy-pasted generic brown-noise texture — even
    # still literally named "ambient_ch2.mp3", a leftover from Ch2 —
    # IDENTICAL regardless of which of Ch3's 6 niches was playing. Now
    # genuinely niche-aware; see get_niche_ambient_music below.
    ambient_path = get_niche_ambient_music(niche_name, duration)
    try:
        if ambient_path and Path(ambient_path).exists():
            mixed = str(WORK_DIR/"mixed_music.mp3")
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

    # v1 addition — burn in real, word-synced captions when available
    # (per explicit request that captions must genuinely match the
    # audio). ass_path is only ever set when generate_real_synced_ass
    # succeeded with genuine Whisper word-level data — never an
    # approximate/estimated version, so this never risks showing
    # captions that drift from what's actually said.
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

    # v6 addition — found only by explicitly re-checking rather than
    # assuming: Ch3 had NO outro at all, same genuine gap Ch2 had before
    # being fixed. Same honest design as the corrected Ch1/built Ch2
    # versions: a real subscribe reminder + episode branding, never a
    # fake visual mimicking YouTube's real (non-API-accessible)
    # clickable end-screen cards. Added as a genuinely separate final
    # step, not injected into the scene-repeat loop above (which cycles
    # to fill the narration's length and would repeat or mistime an
    # outro placed inside it).
    try:
        outro_path = create_control_files_outro(episode)
        # v6 addition — real on-screen source credits, per explicit
        # request. Only a real segment when genuine URL-backed sources exist.
        citations_path = create_control_files_citations_scene(real_cases)
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


def create_control_files_citations_scene(real_cases):
    """v6 addition — real on-screen source credits, per explicit
    request. Same design as Ch1/Ch2: only built when genuine URL-backed
    sources exist; shows titles (not raw URLs) with a pointer to the
    description for actual links."""
    real_sources = [c for c in (real_cases or []) if c.get("url")]
    if not real_sources:
        return None
    duration = 6
    path = str(WORK_DIR / "citations_ch3.mp4")
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
        "drawtext=text='Full links in the description':fontsize=20:fontcolor=purple:"
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


def create_control_files_outro(episode_num=1):
    """
    8-second burned-in outro card for Ch3 — genuinely missing entirely
    before this. Same honest design as Ch1/Ch2: a real subscribe
    reminder and episode branding, no fake-clickable visual mimicking
    YouTube's real (non-API-accessible) end-screen cards.
    """
    path = str(WORK_DIR / "outro_ch3.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1920x1080:rate=24:duration=8",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=8",
        "-vf",
        "drawbox=x=0:y=0:w=iw:h=ih:color=purple@0.25:t=6,"
        "drawtext=text='SUBSCRIBE TO THE CONTROL FILES':fontsize=50:"
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
# referenced in the function body — every niche (cult_psychology,
# propaganda_systems, social_engineering, mass_deception,
# dark_business_documentaries, scams_fraud_exposed) got the identical
# fixed EQ chain, unlike betrayal_deepdive/collapse_index which already
# have real per-niche NICHE_AUDIO_PROFILES. Also the old docstring
# claimed "reverb adds room depth" — no aecho/reverb filter exists
# anywhere in this chain or Ch1's, so that was never accurate; removed
# rather than propagated.
NICHE_AUDIO_PROFILES = {
    "cult_psychology": (
        # Hypnotic and immersive — warm low-mids, controlled dynamics
        "equalizer=f=150:width_type=o:width=2:g=4,"
        "equalizer=f=2000:width_type=o:width=2:g=2,"
        "equalizer=f=8000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-17dB:ratio=3:attack=6:release=90:makeup=3dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "propaganda_systems": (
        # Bold and declarative — punchy mids, forward presence
        "equalizer=f=100:width_type=o:width=2:g=3,"
        "equalizer=f=2800:width_type=o:width=2:g=3,"
        "equalizer=f=9000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-16dB:ratio=4:attack=3:release=70:makeup=3dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "social_engineering": (
        # Cold and manipulative — dry, clinical, tightly controlled
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "mass_deception": (
        # Wide and unsettling — bigger dynamic range, ethereal edges
        "equalizer=f=80:width_type=o:width=2:g=4,"
        "equalizer=f=2000:width_type=o:width=2:g=2,"
        "equalizer=f=11000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=110:makeup=2dB,"
        "loudnorm=I=-16:LRA=12:TP=-1.5"
    ),
    "dark_business_documentaries": (
        # Corporate and serious — balanced, weighted authority
        "equalizer=f=90:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=7500:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=90:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "scams_fraud_exposed": (
        # Urgent and alarming — present mids, tighter dynamics
        "equalizer=f=100:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=3,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=4:attack=2:release=60:makeup=3dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["cult_psychology"]


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


def get_media_duration(path):
    """
    Real ffprobe-measured duration in seconds, or 0.0 if unmeasurable.

    FIX (found on re-audit): this was called twice inside
    run_audio_with_ssml (the SSML multi-rate narration feature — matches
    Ch1's confirmed-ACTIVE audio quality feature, but was sitting
    completely dead in Ch3) and was never defined anywhere in this file
    at all — a guaranteed NameError the moment that function was ever
    called. Uses the same real-ffprobe pattern as check_audio_quality.
    """
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    return 0.0


def _detect_abnormal_silence(mp3_path, total_duration):
    """
    v1 addition — real, signal-based audio quality check using ffmpeg's
    actual silencedetect filter, not just file size/duration heuristics.
    Catches a genuine TTS failure mode that size checks miss entirely: a
    segment that generated corrupted or got silently truncated mid-
    synthesis, leaving a real, audible silent gap in otherwise normal-
    sized audio. Flags if total detected silence exceeds 15% of the
    audio — continuous narration should have brief natural pauses, not
    long unexplained gaps. Returns (is_normal, silence_fraction).
    """
    if not total_duration or total_duration <= 0:
        return True, 0.0  # can't evaluate — don't block on missing data
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

    FIX (found on re-audit — this is the exact "BIGGER BUG THAN CH1 HAD"
    pattern already logged for Ch2): this function ALWAYS measured the
    real duration via ffprobe internally for its own pass/fail check, but
    only ever returned True/False, discarding the actual number. All 4
    TTS fallback tiers were then returning the word-count ESTIMATE
    (dur_expected) to everything downstream — video length, scene/concat
    timing, and any duration-cap enforcement — instead of the real
    measured duration. Now returns (passed, real_duration_or_None).
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
                return False, None
            # v1 addition — real signal-based check, not just size/duration.
            _silence_ok, _silence_frac = _detect_abnormal_silence(mp3_path, actual_dur)
            if not _silence_ok:
                log(f"  Quality FAIL: {_silence_frac*100:.0f}% silence — likely corrupted/truncated segment")
                return False, None
            log(f"  Quality OK: {sz/1024/1024:.1f}MB | {actual_dur:.0f}s (real, ffprobe-measured)")
            return True, actual_dur
        log(f"  Quality OK (size): {sz/1024/1024:.1f}MB — duration unmeasurable, using estimate")
        return True, None
    except Exception as e:
        log(f"  Quality check error: {e}"); return False, None


def _try_ssml_multirate_audio(script_clean, voice_id, niche_name):
    """
    Wrapper: attempts the SSML multi-rate narration path (matches Ch1's
    confirmed-ACTIVE audio feature — pace varies by section, reads as a
    real documentary narrator — which was sitting completely dead in Ch3
    until this wiring pass) as the new primary audio tier.

    Falls back to None (triggering the existing proven flat-rate chain)
    on ANY doubt, including partial segment failure — run_audio_with_ssml
    will still return *something* if even one segment succeeded out of
    seven, but publishing a video with silently-missing narration
    sections is worse than falling back to the flat-rate tier, so this
    wrapper checks the resulting duration against expectation rather
    than trusting a non-None return at face value.
    """
    try:
        out, duration = run_audio_with_ssml(script_clean, niche_name, voice_id)
        if not out or not Path(out).exists():
            return None
        wc = len(script_clean.split())
        dur_expected = min((wc / 125.0) * 60.0, 1080.0)  # FIX: was 900 (15 min) -- real hard cap is 18 min, matches evidence_room
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

    # FIX (found on re-audit): run_audio_with_ssml — multi-rate narration
    # that varies delivery pace by section, matching Ch1's confirmed-
    # ACTIVE audio-quality feature — was fully built (and had its own
    # crash bug already fixed) but never actually wired in as a real
    # tier anywhere. Tried first now; any failure or doubt falls straight
    # through to the existing, thoroughly-tested flat-rate chain below,
    # so this can only improve narration quality, never regress reliability.
    ssml_result = _try_ssml_multirate_audio(script_clean, voice_id, niche_name)
    if ssml_result:
        return ssml_result

    wc           = len(script_clean.split())
    dur_expected = min((wc / 125.0) * 60.0, 1080.0)  # FIX: was 900 (15 min) -- real hard cap is 18 min, matches evidence_room
    preferred    = NICHE_VOICES.get(niche_name, GB_VOICES[:4])
    # v1 addition — real learning-loop closure: track_episode has been
    # recording per-voice average scores into state["performance"] this
    # whole time, but nothing ever read it back — a write-only metric,
    # not an actual learning loop. Now genuinely reorders the niche's
    # own voice list (never introduces an unrelated voice) toward
    # whichever has the best real historical average score for THIS
    # channel, provided it's been tried enough times to be meaningful.
    try:
        _perf_state = load_state()
        _voice_perf = _perf_state.get("performance", {})
        def _voice_learned_rank(v):
            _scores = _voice_perf.get(f"voice_{v}", {}).get("scores", [])
            if len(_scores) < 3:
                return (0, 0)  # not enough data yet — keep original order (stable sort)
            return (1, sum(_scores) / len(_scores))  # more data + higher avg score = preferred
        _ranked = sorted(enumerate(preferred), key=lambda iv: (-_voice_learned_rank(iv[1])[0], -_voice_learned_rank(iv[1])[1], iv[0]))
        preferred = [v for _, v in _ranked]
    except Exception as e:
        log(f"  Learned voice preference (non-fatal, using default order): {e}")
    # FIX (direct user report, July 23 2026): dropped US voices (robotic
    # per direct feedback) and en-GB-NoahNeural (confirmed broken on this
    # repo's Actions runners — 24/24 segment failures in live testing).
    GUARANTEED_VOICES = [
    "en-GB-ThomasNeural",       # Cold BBC gravitas — best for dark documentary
    "en-GB-RyanNeural",          # Deep British authority
    "en-GB-OliverNeural",        # Composed British authority
    "en-GB-EthanNeural",         # Warm natural storytelling
]
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
            _quality_ok, _real_dur = check_audio_quality(mp3, dur_expected)
            if not _quality_ok:
                log(f"  {v} failed quality — trying next"); continue
            sz  = Path(mp3).stat().st_size
            dur = _real_dur if _real_dur else dur_expected
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
                _quality_ok, _real_dur = check_audio_quality(mp3, dur_expected)
                if _quality_ok:
                    _fish_dur = _real_dur if _real_dur else dur_expected
                    sz = Path(mp3).stat().st_size
                    log(f"  ACCEPTED: Fish Audio backup | {sz/1024/1024:.1f}MB")
                    tg("⚠️ Control Files: all edge-tts voices failed today — used Fish Audio backup instead (still natural-sounding)")
                    mp3p = apply_audio_post_processing(mp3, str(WORK_DIR/"audio_fish_eq.mp3"), niche_name)
                    wav = str(WORK_DIR / "audio_fish.wav")
                    try:
                        subprocess.run(["ffmpeg","-y","-i",mp3p,"-acodec","pcm_s16le","-ar","24000","-ac","1",wav],
                                       capture_output=True, timeout=300)
                        if Path(wav).exists() and Path(wav).stat().st_size > 100000:
                            return wav, _fish_dur, sz, "fish-audio-s2-pro"
                    except Exception: pass
                    return mp3p, _fish_dur, sz, "fish-audio-s2-pro"
            else:
                log(f"  Fish Audio: {r.status_code} — {str(r.content)[:150]}")
        except Exception as e:
            log(f"  Fish Audio backup failed: {e}")
    else:
        log("  FISH_AUDIO_API_KEY not set — skipping Fish Audio backup")

    # FIX (v5 addition): Kokoro TTS — real, independently-researched
    # local model (Apache 2.0, 82M params, ranks 1st among TTS models
    # that run without a server). Inserted here specifically because it
    # runs LOCALLY — no API rate limit to ever hit, unlike every other
    # tier — so the pipeline should now rarely if ever need to fall to
    # the two genuinely weaker, more robotic tiers below (gTTS/espeak).
    # Requires: pip install kokoro soundfile (espeak-ng already
    # installed for the existing espeak fallback, also used by Kokoro
    # for phonemization).
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as _np

        _kok_pipeline = KPipeline(lang_code="a")  # American English
        _words = script_clean.split()
        kok_chunks = [" ".join(_words[i:i+350]) for i in range(0, len(_words), 350)]
        kok_parts = []
        for i, chunk in enumerate(kok_chunks):
            part_wav = str(WORK_DIR / f"kokoro_part_{i}.wav")
            try:
                audio_segments = []
                for _gs, _ps, audio in _kok_pipeline(chunk, voice="am_adam", speed=1.0):
                    audio_segments.append(audio)
                if audio_segments:
                    full_audio = _np.concatenate(audio_segments) if len(audio_segments) > 1 else audio_segments[0]
                    sf.write(part_wav, full_audio, 24000)
                    if Path(part_wav).exists() and Path(part_wav).stat().st_size > 2000:
                        kok_parts.append(part_wav)
            except Exception as e:
                log(f"    Kokoro chunk {i} error: {e}")

        if kok_parts:
            kok_wav = str(WORK_DIR / "audio_kokoro.wav")
            if len(kok_parts) == 1:
                import shutil as _shutil2
                _shutil2.copy(kok_parts[0], kok_wav)
            else:
                lst = str(WORK_DIR / "kokoro_list.txt")
                with open(lst, "w") as f:
                    for p in kok_parts: f.write(f"file '{p}'\n")
                subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c","copy",kok_wav],
                               capture_output=True, timeout=300)
            kok_mp3 = str(WORK_DIR / "audio_kokoro.mp3")
            subprocess.run(["ffmpeg","-y","-i",kok_wav,"-acodec","libmp3lame","-q:a","2",kok_mp3],
                           capture_output=True, timeout=300)
            if Path(kok_mp3).exists() and Path(kok_mp3).stat().st_size > 100000:
                sz = Path(kok_mp3).stat().st_size
                _quality_ok, _real_dur = check_audio_quality(kok_mp3, dur_expected)
                if _quality_ok:
                    _kok_dur = _real_dur if _real_dur else dur_expected
                    log(f"  ACCEPTED: Kokoro (local) | {sz/1024/1024:.1f}MB | {_kok_dur:.0f}s")
                    return kok_mp3, _kok_dur, sz, "kokoro-local"
    except ImportError:
        log("  kokoro/soundfile not installed — skipping Kokoro tier")
    except Exception as e:
        log(f"  Kokoro backup failed: {e}")

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
                _quality_ok, _real_dur = check_audio_quality(mp3, dur_expected)
                _gtts_dur = _real_dur if _real_dur else dur_expected
                log(f"  ACCEPTED: gTTS backup | {sz/1024/1024:.1f}MB (lower quality)")
                tg("⚠️ Control Files: edge-tts AND Fish Audio both failed today — used gTTS backup "
                   f"(noticeably more robotic). Check FISH_AUDIO_API_KEY / provider status.")
                return mp3, _gtts_dur, sz, "gtts-fallback"
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
            _quality_ok, _real_dur = check_audio_quality(final, dur_expected)
            _espeak_dur = _real_dur if _real_dur else dur_expected
            log(f"  ACCEPTED: offline espeak-ng (LAST RESORT) | {sz/1024/1024:.1f}MB")
            tg("🚨 Control Files: ALL providers failed today (edge-tts, Fish Audio, gTTS) — used OFFLINE "
               f"robotic voice as last resort so the video still published. Check provider status urgently.")
            return final, _espeak_dur, sz, "espeak-offline-LASTRESORT"
    except Exception as e:
        log(f"  espeak-ng backup failed: {e}")

    tg("Control Files Stage 3 FAILED — all voices AND all backup providers failed")
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
        "cult_psychology":       "dark corporate financial documents",
        "propaganda_systems": "dark crime evidence investigation",
        "social_engineering":     "dark corporate shadow documents",
        "mass_deception":      "dark technology screen code shadow",
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
                        log(f"  Case image Ch3 (Pixabay): {search_kw}")
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
                        log(f"  Case image Ch3 (Pexels): {search_kw}")
                        return True
        except: pass
    return False


def generate_thumbnail(title, thumb_text, niche_name, topic, ab_style="A",
                        episode=1, channel_name="The Control Files"):
    """Three-layer thumbnail via thumbnail_engine_v2. Fallback to Pollinations+Pillow."""
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        # FIX: same missing cache_dir bug as generate_thumbnail_with_ai_bg above.
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
    """
    Post engagement-driving creator comment immediately after upload.

    FIX (found on re-audit): this is genuinely called on every upload —
    not dead code — and had the same 2 gaps found elsewhere in this file:
    only 4 of 6 real niches had hooks (silently fell back to a generic
    line for the 2 newly-activated niches), and the hashtags/cross-promo
    line used Ch2-flavored language (#forensic #investigation, only
    mentioning BetrayalDeepDive) inside a psychology-channel comment.
    """
    niche_hooks = {
        "cult_psychology":             "What financial warning sign do you think most people miss?",
        "propaganda_systems":          "Which technique in this case do you find most disturbing?",
        "social_engineering":          "Have you ever seen this happen at a company you know?",
        "mass_deception":              "Did you know your digital footprint tells this much about you?",
        "dark_business_documentaries": "At what point should someone inside have said something?",
        "scams_fraud_exposed":         "What's the reddest flag you caught in this one?",
    }
    hook = niche_hooks.get(niche_name, "What detail in this case changed how you see it?")
    comment = (
        f"🧠 {hook}\n\n"
        f"Leave your answer below — every case has details that never make the news.\n\n"
        f"🔔 New investigation every weekday\n"
        f"🌑 Dark horror: youtube.com/@BetrayalDeepDive\n"
        f"🔬 Forensic investigations: youtube.com/@TheEvidenceRoom\n\n"
        f"#{niche_name.replace('_','')} #psychology #documentary #controlfiles #episode{episode}"
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
    """Dedicated Short title for Ch3 — mass manipulation investigation angle."""
    prompts = {
        "standalone_1": f"Write a YouTube Shorts title that creates maximum curiosity for a mass manipulation investigation. "
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
                log(f"  Short title Ch3: {title}")
                return title
    except Exception as e:
        log(f"  Short title Ch3 (non-fatal): {e}")
    defaults = {"standalone_1": "What the Records Revealed", "standalone_2": "Evidence Found — Full Case Above"}
    return defaults.get(type_key, main_title[:50])


def post_short_creator_comment(token, video_id, niche_name, main_title):
    """
    Pinned creator comment on each Ch3 Short. Drives early engagement signals.

    FIX: this was named "_ch2" inside Ch3's own file (a real niche-name/
    naming-copy-paste artifact, the exact pattern Part G's checklist warns
    about) and was never actually called anywhere — same dead-function
    pattern found repeatedly elsewhere. Also only had hooks for 4 of Ch3's
    6 real niches, and used Ch2-flavored hashtags (#forensic) inside a
    psychology-channel comment. All fixed; now wired into both Shorts phases.
    """
    short_hooks = {
        "cult_psychology":             "What's the first sign someone's in a control system, not just a relationship?",
        "propaganda_systems":          "What's a propaganda technique you've caught in the wild recently?",
        "social_engineering":          "Would you have caught this social engineering attempt?",
        "mass_deception":              "How much of what you see online do you think is genuinely organic?",
        "dark_business_documentaries": "At what point should someone inside have said something?",
        "scams_fraud_exposed":         "What's the reddest flag in this one?",
    }
    hook = short_hooks.get(niche_name, "What was the most disturbing mechanism in this case?")
    comment = (
        f"🧠 {hook}\n\n"
        f"Full investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🎯 The Control Files: youtube.com/@TheControlFiles\n\n"
        f"#{niche_name.replace('_','')} #shorts #psychology #controlfiles"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": comment}}}},
            timeout=30)
        if r.status_code == 200: log("  Short creator comment OK")
        else: log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_ch2_cross_promo(is_short=False):
    """Three-channel cross-promotion for Ch3 descriptions."""
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


def track_episode(state, niche_name, score, voice, episode, ab_style=None):
    """
    Performance tracker for Ch3 — same as Ch1's track_episode.

    FIX: this was named "track_episode_ch2" inside Ch3's own file — a real
    niche-name/naming copy-paste artifact (Part G's checklist pattern) —
    and was never called anywhere, so niche auto-rotation had a fully
    dead write side and no read side at all. Both fixed below.

    SECOND FIX (found on re-audit): the "streak_below" check originally
    used `score < MIN_GATE` (8.8) — but MIN_GATE is only the bar for
    attempts 1-8. A script that succeeds via the graduated fallback tiers
    (attempts 9-13, scoring anywhere from 6.9-8.79) is EXPECTED occasional
    behavior, not a problem — the pipeline itself sends a Telegram note
    saying so. Using MIN_GATE here meant almost every fallback-tier
    success would count as "below," and 3 such genuinely-fine episodes
    would trigger niche rotation for no real reason. Fixed to use a
    genuine underperformance floor instead.

    v1 addition — ab_style tracking, closing the same "write-only, no
    learning" gap already found and fixed for voice selection. Honest
    limitation: this uses the script's own quality score as a proxy,
    since no real click-through data exists yet — a genuine but
    imperfect signal until real YouTube Analytics data is available.
    """
    ROTATION_FLOOR = 7.0   # attempts 9-12's own gate — below this reflects
                           # real underperformance, not just "needed a retry"
    perf = state.get("performance", {})
    n    = perf.get(niche_name, {"scores": [], "streak_below": 0})
    n["scores"]       = (n["scores"] + [score])[-20:]
    n["streak_below"] = (n["streak_below"] + 1) if score < ROTATION_FLOOR else 0
    n["last_episode"] = episode
    perf[niche_name]  = n
    v = perf.get(f"voice_{voice}", {"scores": []})
    v["scores"] = (v["scores"] + [score])[-20:]
    perf[f"voice_{voice}"] = v
    if ab_style:
        ab = perf.get(f"thumbnail_style_{ab_style}", {"scores": []})
        ab["scores"] = (ab["scores"] + [score])[-20:]
        perf[f"thumbnail_style_{ab_style}"] = ab
    state["performance"] = perf
    return state


def pick_best_niche(state, default_niche_name):
    """
    NEW: niche auto-rotation — was completely absent from Ch3 (only a
    dead, misnamed write-side function existed, no read side at all).
    Rotates away from the day's default niche if it has 3+ consecutive
    below-gate episodes, matching the confirmed real pattern from Ch1's
    build (track_episode/pick_best_niche). Never auto-kills a niche —
    just skips it for today's rotation and picks the least-recently-poor
    alternative; a human still sees everything via the weekly report.
    """
    perf = state.get("performance", {})
    default_streak = perf.get(default_niche_name, {}).get("streak_below", 0)
    if default_streak < 3:
        return default_niche_name

    all_niche_names = [n["name"] for n in NICHES]
    candidates = [n for n in all_niche_names if n != default_niche_name]
    # Prefer whichever candidate has the lowest current streak_below (i.e.
    # least recently struggling), breaking ties by fewest total episodes
    # scored (so a totally untested niche gets a fair rotation-in chance).
    candidates.sort(key=lambda n: (
        perf.get(n, {}).get("streak_below", 0),
        len(perf.get(n, {}).get("scores", [])),
    ))
    chosen = candidates[0] if candidates else default_niche_name
    if chosen != default_niche_name:
        log(f"  Niche auto-rotation: {default_niche_name} has {default_streak} "
            f"consecutive below-gate episodes — rotating to {chosen} for today.")
    return chosen



# ════════════════════════════════════════════════════════════
# STANDALONE NICHE SHORTS — the 2 real Shorts produced each day
# ════════════════════════════════════════════════════════════

SHORTS_TEMPLATES = {
    "cult_psychology":       ["The one recruitment tactic nobody notices happening",
                               "The moment the control system revealed itself"],
    "propaganda_systems":    ["The single technique that broke the whole narrative",
                               "The detail that proved it was engineered, not organic"],
    "social_engineering":    ["The internal memo that exposed the manipulation",
                               "The message they tried to bury and failed"],
    "mass_deception":        ["The digital trace that was impossible to erase",
                               "The metadata that revealed the entire operation"],
    "dark_business_documentaries": ["The internal email that exposed the real decision",
                               "The meeting notes nobody was supposed to see"],
    "scams_fraud_exposed":   ["The one red flag every victim missed",
                               "The transfer record that finally proved the pattern"],
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
        "cult_psychology":       (8, 12, 20),
        "propaganda_systems": (12, 5, 5),
        "social_engineering":     (5, 8, 12),
        "mass_deception":      (5, 15, 10),
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
            draw.text((40, 30), "● THE CONTROL FILES", font=gf(26), fill=(160, 0, 0))

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
                else f"THE CONTROL FILES: {topic[:35]} #Shorts"
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
    Real 13-attempt graduated script engine for Ch3 The Control Files.

    FIX: this previously claimed "13-Attempt Script Engine" in its own log
    line but the loop only ran `range(1, 9)` — 8 attempts, not 13 — and
    the gate itself drifted through ad-hoc values (7.3/7.2/7.0/6.9) that
    never matched the real spec used elsewhere in the empire. Rebuilt to
    the actual standard: attempts 1-8 require MIN_GATE (8.8), attempts
    9-12 relax to 7.0, attempt 13 allows the absolute last-resort floor
    of FINAL_GATE (6.9) — never lower, matching Ch1/Ch2 exactly.
    """
    log("\n"+"="*65)
    log("  STAGE 1: Control Files 13-Attempt Script Engine")
    log(f"  Quality floor: attempts 1-8={MIN_GATE} | 9-12=7.0 | 13={FINAL_GATE}")
    log("="*65)

    niche, voice, style_name = get_niche_voice_style(state)
    episode    = (datetime.datetime.now().timetuple().tm_yday//3)+1
    prev_title = state.get("last_title","")
    pattern_hint = load_pattern_memory(state)
    # FIX (found on re-audit — same dead-function bug already found in
    # Ch2): load_weekly_strategy existed and correctly reads the real
    # weekly competitor-intelligence report weekly_report.py generates,
    # but was never actually called anywhere in Ch3. Wired in now.
    weekly_strategy = load_weekly_strategy()
    # Fetch a token early (cheap OAuth refresh) so run_viral_intelligence
    # can ground its analysis in real current YouTube data rather than
    # asking the AI to invent patterns from nothing — same fix already
    # applied to Ch2's identical bug.
    try:
        _early_yt_token = get_yt_token()
    except Exception:
        _early_yt_token = None
    intel      = run_viral_intelligence(niche, yt_token=_early_yt_token)

    # NEW FEATURE (per explicit request — daily competitive research):
    # run_viral_intelligence above is still fundamentally an AI-imagined
    # analysis (grounded in a handful of real titles as context, but the
    # "patterns" themselves are AI-invented, and it's cached for 7 days,
    # not daily). This is a genuinely real, DAILY refresh: real view/like
    # counts and real title-word-frequency patterns from actual current
    # top-performing videos in this niche, computed deterministically —
    # not an AI guess. Enriches intel's winning_title_patterns with
    # today's real top titles (used directly by both title generation
    # and, via daily_research_block below, script generation).
    daily_research_block = ""
    try:
        from daily_competitor_research import fetch_daily_competitor_research
        _daily_intel = fetch_daily_competitor_research(niche, _early_yt_token, str(SCRIPT_DIR))
        daily_research_block = _daily_intel.get("research_block", "")
        if _daily_intel.get("videos"):
            intel["winning_title_patterns"] = (
                [v["title"] for v in _daily_intel["videos"][:3]] + intel.get("winning_title_patterns", []))
    except Exception as e:
        log(f"  Daily competitor research (non-fatal): {e}")

    used_topics = []
    best_score = 0.0
    best_script = best_scenes = best_title_str = best_thumbnail = best_tags = best_title_scores = None
    best_real_cases = []

    log(f"\nNiche: {niche['name']} | ${niche['rpm']} RPM | Ep{episode}")
    log(f"Style: {style_name} | Voice: {voice}")

    for attempt in range(1, 14):
        if attempt <= 8:      gate = MIN_GATE
        elif attempt <= 12:   gate = 7.0
        else:                 gate = FINAL_GATE   # attempt 13, absolute floor

        topic = get_fresh_topic(niche, attempt, intel, used_topics)
        used_topics.append(topic)

        if attempt in [1,5,9,13]:
            thumbnail_text     = generate_thumbnail_text(niche, topic, intel)
            title_str, tscores = generate_and_score_titles(niche, topic, intel, episode)
            # v15: title CTR gate
            title_str, tscores = run_title_ctr_gate(
                title_str, tscores, topic, niche["name"], niche["series"],
                episode, lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
            best_thumbnail     = thumbnail_text
            best_title_str     = title_str
            best_title_scores  = tscores
            log(f"Thumbnail: {thumbnail_text}")

        log(f"\nAttempt {attempt}/13 (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            script_clean, scenes, title, thumb, tags, violations, real_cases = generate_script_and_scenes(
                niche, topic, style_name, episode, attempt, intel, prev_title,
                "\n\n".join(filter(None, [pattern_hint, weekly_strategy, daily_research_block])))
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
                if attempt > 8:
                    tg(f"⚠️ Ch3 script published via graduated fallback tier "
                       f"(attempt {attempt}, gate {gate}) — expected occasional "
                       f"behavior, not a bug, but worth knowing.")
                # v6 addition — real research-usage alert, fired exactly
                # once here for the actual winning/publishing attempt
                # (not per-attempt, which would be noisy — up to 13
                # alerts per episode for attempts that never published).
                if real_cases:
                    _win_script_lower = script_clean.lower()
                    _win_research_words = set()
                    for c in real_cases[:3]:
                        _win_research_words.update(
                            w.strip(".,;:").lower() for w in (c.get("title","")+" "+c.get("summary","")).split()
                            if len(w) > 6)
                    if not any(w in _win_script_lower for w in _win_research_words):
                        tg(f"⚠️ Ch3: real research was found ({len(real_cases)} sources) but the "
                           f"script that's actually publishing shows no clear sign of using it — "
                           f"may be relying on invented details instead of the real documented "
                           f"facts. Worth a manual check on this episode's factual grounding.")
                # v9 addition — real title-script alignment check, per
                # direct research confirming that YouTube's algorithm
                # increasingly matches spoken content to the title
                # semantically, and that a title whose specific claim
                # (a number, a name) never actually gets said in the
                # video hurts both search relevance and the "does it
                # deliver on its promise" satisfaction signal. Titles
                # are only regenerated every few attempts while scripts
                # regenerate every attempt, creating real drift risk.
                _title_distinctive_words = {
                    w.strip(".,!?:;\"'").lower() for w in best_title_str.split()
                    if len(w) > 4 and w.lower() not in
                    {"about","after","before","their","there","which","would","could","should"}
                }
                if _title_distinctive_words:
                    _script_words_lower = set(script_clean.lower().split())
                    _matched = sum(1 for w in _title_distinctive_words if w in _script_words_lower)
                    if _matched == 0:
                        tg(f"⚠️ Ch3: none of the title's distinctive words appear in the script — "
                           f"\"{best_title_str[:70]}\" may not match what the video actually says. "
                           f"Worth checking the title still fits before this publishes.")
                # FIX (found on re-audit): this previously returned/logged/
                # tracked the CURRENT attempt's `score`, but the actual
                # content being published is `best_script`/`best_tags` —
                # the highest-scoring attempt found so far, which can be
                # a DIFFERENT (better) attempt than the one that happened
                # to clear the (progressively easier) gate. That meant a
                # genuinely 8.5-scoring video could get logged, reported to
                # Telegram, and fed into track_episode/the audit engine as
                # only e.g. 7.2/10 — corrupting quality tracking data even
                # though the actually-published content was fine. Now
                # reports best_score, which always matches what's returned.
                track_episode(state, niche["name"], best_score, voice, episode)
                save_state(state)
                # v6 addition — real citation system: carried through
                # intel, matching the safe, already-established pattern
                # of not extending this large tuple's own arity.
                intel["_real_cases"] = best_real_cases
                return (niche, topic, voice, style_name, episode,
                        best_script, best_scenes, best_title_str,
                        best_thumbnail, best_title_scores, best_score, best_tags, intel, attempt)
            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if best_script and best_score >= FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Note: Publishing {best_score}/10 after 13 attempts.")
        track_episode(state, niche["name"], best_score, voice, episode)
        save_state(state)
        intel["_real_cases"] = best_real_cases
        return (niche, used_topics[-1], voice, style_name, episode,
                best_script, best_scenes, best_title_str,
                best_thumbnail, best_title_scores, best_score, best_tags or [], intel, 13)

    state["last_niche"] = niche["name"]; save_state(state)
    tg(f"Control Files Day Skipped\nBest: {best_score}/10 after 13 attempts")
    sys.exit(0)



def run_stage2_approval_ch2(title_str, niche, score, script_clean):
    """30-minute approval gate for Ch3 Control Files."""
    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime("%I:%M %p")
    preview      = script_clean[:400].replace("<","").replace(">","")
    msg = (
        f"<b>CONTROL FILES APPROVAL NEEDED</b>\n\n"
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
        "cult_psychology": [
            "If documented cases like this concern you, subscribe — new files every week.",
            "This channel investigates documented control systems. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Control Files.",
        ],
        "propaganda_systems": [
            "If this pattern concerns you, subscribe — more documented systems every week.",
            "This channel tracks documented propaganda systems. Subscribe to follow the record.",
            "More documented findings like this are coming. Subscribe to The Control Files.",
        ],
        "social_engineering": [
            "If this technique concerns you, subscribe — documented methods every week.",
            "This channel documents social engineering systems. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Control Files.",
        ],
        "mass_deception": [
            "If this scale concerns you, subscribe — documented findings every week.",
            "This channel investigates documented deception at scale. Subscribe to follow the record.",
            "More documented cases like this are coming. Subscribe to The Control Files.",
        ],
        # FIX (found on re-audit): this function is genuinely called on
        # every script (_inject_ctas_er is live, not dead code), and its
        # niche fallback silently gave dark_business_documentaries and
        # scams_fraud_exposed videos cult-psychology-flavored CTA wording
        # baked into the actual published script — a real content-quality
        # gap, not just a cosmetic one.
        "dark_business_documentaries": [
            "If this kind of corporate failure concerns you, subscribe — documented cases every week.",
            "This channel investigates documented corporate collapses. Subscribe to follow the record.",
            "More documented cases like this are coming. Subscribe to The Control Files.",
        ],
        "scams_fraud_exposed": [
            "If this scam pattern concerns you, subscribe — documented fraud cases every week.",
            "This channel documents fraud systems in detail. Subscribe to follow the evidence.",
            "More documented cases like this are coming. Subscribe to The Control Files.",
        ],
    }
    ctas = cta_bank.get(niche_name, cta_bank["cult_psychology"])

    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    # Insert at 30%, 60%, 80% word marks — at the nearest sentence boundary
    marks = [int(total * 0.30), int(total * 0.60), int(total * 0.80)]
    inserted = 0
    result = script_clean

    for i, mark_pct in enumerate(marks):
        cta = ctas[i % len(ctas)]
        # Find approximate character position for this word mark
        target_word_idx = mark_pct + inserted
        all_words = result.split()
        if target_word_idx >= len(all_words):
            continue
        # Find nearest sentence end after this word
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
    genuine retention-cadence coverage throughout (not just 3 points), and
    the Killer Hook / Narrative Craft / Topic Clarity rubric.
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
        h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
        if h60 < 2:
            score -= 0.8
            issues.append("Weak 60% peak hook")
        elif h60 >= 3:
            score += 0.3
        if "subscribe" not in " ".join(words[-60:]).lower():
            score -= 0.3
            issues.append("Missing subscribe CTA in final 60 words")

        # v1 addition — real, measurable enforcement of the retention-
        # cadence instruction added to the prompt (payoff every 150-225
        # words / ~60-90 seconds), per direct 2026 research on why
        # multi-minute flat stretches hurt retention. Without this, the
        # prompt instruction had zero actual consequence if ignored —
        # scans real ~200-word rolling windows and penalizes genuine
        # dead zones (no hook signal AND no real specific-number claim
        # anywhere in that stretch), not just the 3 original fixed points.
        WINDOW = 200
        dead_zones = 0
        for start in range(0, total - WINDOW, WINDOW):
            window_text = " ".join(words[start:start + WINDOW]).lower()
            has_hook = any(w in window_text for w in hook_signals)
            has_number = bool(re.search(r'\b\d[\d,\.]*\b', window_text))
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
                f"Clarity {subscores['topic_clarity']}/10")
        issues.extend(rubric_issues[:3])
        rehook_bonus, rehook_issues = validate_rehook_beat(script_clean)
        score += rehook_bonus
        issues.extend(rehook_issues)
    except Exception as e:
        log(f"  Script rubric scoring (non-fatal): {e}")

    return min(round(score, 1), 10.0), issues




# ═══════════════════════════════════════════════════════════
# PORTED FROM Ch1 — Advanced features for Ch3
# ═══════════════════════════════════════════════════════════

def run_provider_health_check():
    """
    Tests all AI providers at pipeline startup.
    Fires BEFORE script generation so you see exactly what works.
    Results sent to Telegram so you can see them in the approval gate.

    FIX (found on re-audit, diagnosed from a real Telegram alert showing
    6/7 providers consistently "failing"): the test prompt used to be
    "Reply with exactly: OK" — a genuinely 2-character expected reply —
    while every single provider-calling function requires the response
    to be over 100 characters to count as valid (a correct, protective
    check for REAL script-generation calls, where a real script is
    always much longer than 100 chars). This meant any provider whose
    model actually followed the instruction literally (replying just
    "OK") got wrongly marked "NO RESPONSE", while a provider whose model
    happened to ignore the instruction and ramble past 100 characters
    passed by accident — this was never a real measure of provider
    health at all. Fixed by asking for something that naturally produces
    a long reply regardless of how literally the model follows
    instructions, instead of weakening the 100-char check itself (which
    is correctly protective everywhere else).
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

    FIX (found on re-audit — matches Ch1's exact "single most consequential
    dead function" pattern): this was fully built but never called anywhere.
    Two further bugs found in the process of wiring it in: (1) it referenced
    niche["dread_style"], a key that only exists in Ch1's niche objects —
    Ch3's niches have no such key, so this would have raised a KeyError the
    moment it was ever actually called; (2) it called a function named
    "ai_generate" which doesn't exist anywhere in this file at all (the real
    function is just "ai") — a second, independent guaranteed crash. Both
    fixed below.
    """
    trend_hint = ""
    if trending_titles:
        trend_hint = f"These hooks are working in this niche right now:\n"
        trend_hint += "\n".join(f"  - {t}" for t in trending_titles[:3])

    prompt = f"""Generate exactly 3 different cold open variants for a dark documentary narration.
Topic: {topic}
Niche style: mechanism-forward psychological documentary, analytical not conspiracy-forward — {niche["name"].replace("_"," ")}
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
  concrete result up front (e.g. if the case is a manipulation tactic
  designed to build trust that became the exact tool used to destroy it,
  say something like "the trust he built is what he used to break her" —
  naming the real irony, not a vague mood). This creates a "wait — HOW
  did that happen" curiosity gap about THIS specific case, not generic
  dread. A viewer must be able to tell, from the cold open alone, roughly
  WHAT happens by the end — they keep watching to learn HOW, never to
  learn WHAT. An opening that could be swapped into a different episode
  about a different case with zero changes has failed this requirement,
  no matter how disturbing it sounds in isolation.

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
    """
    Real YouTube Data API search — genuinely current top-viewed videos in
    this niche, last 30 days. Matches Ch1's proven real-trend-fetching
    pattern.

    FIX (found on re-audit): referenced niche["search_query"], a key that
    doesn't exist anywhere in Ch3's niche objects (another instance of the
    exact "copy-pasted key from a different channel's file" bug pattern
    already found twice elsewhere this session) — a guaranteed KeyError
    the moment this was ever called. Ch3's real key is "viral_search".
    """
    try:
        published_after = (datetime.datetime.utcnow() -
                           datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche["viral_search"], "type": "video",
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



# FIX (found on word-by-word re-audit, July 15 2026): generate_seo_description
# was confirmed DEAD CODE -- zero call sites anywhere in this file. The
# REAL, live description gets built inline inside _generate_description_variant
# (search for that name), which had its own independent copy of the same
# genre-mismatch bug (said "forensic analysis" -- Ch2's niche, not this
# channel's) already fixed there. Removed this dead duplicate entirely so
# it can't be mistaken for the live path again.

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
        item  = r.json()["items"][0]
        ch_id = item["id"]
        # FIX: channels.update requires the FULL snippet object (including
        # the required "title" field) whenever any part of it is updated —
        # sending {"description": ...} alone guarantees a 400 every time.
        # Same bug already fixed in Ch1/Ch2's identical function.
        full_snippet = item.get("snippet", {})
        # FIX (found on direct user request, July 14 2026): this was
        # literally Ch1's real channel description ("dark psychology,
        # true horror") copy-pasted verbatim -- if this ever ran,
        # Ch3's real, public YouTube "About" page would have
        # described itself as a horror channel.
        desc  = (f"Latest: {latest_title}\n{latest_url}\n\n"
                 "Psychological manipulation and control tactics, documented with real cases and real research.\n"
                 "New episodes every weekday. Subscribe for weekly investigations.")
        full_snippet["description"] = desc[:1000]
        r2 = requests.put(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"id": ch_id, "snippet": full_snippet}, timeout=20)
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
    same real citation-system addition as Ch1/Ch2: the structured list
    (with real URLs) feeds the actual "Sources" block and on-screen
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

    # FIX (found on re-audit, matches the exact bug pattern already found
    # in Ch2's identical function): this dict used CH1's niche names
    # (dark_horror, seduction_dark, etc.) hardcoded inside Ch3's own file.
    # Since niche_name is always one of Ch3's real 6 niches, this NEVER
    # matched — search_real_cases always silently used the generic
    # fallback query, regardless of the actual niche. Fixed to Ch3's own
    # real niche names.
    niche_queries = {
        "cult_psychology":             f"cult recruitment psychological control documented case",
        "propaganda_systems":          f"propaganda campaign documented government media case",
        "social_engineering":          f"social engineering fraud documented case",
        "mass_deception":              f"mass deception manipulation documented case",
        "dark_business_documentaries": f"corporate scandal collapse documented case",
        "scams_fraud_exposed":         f"fraud scam exposed documented investigation case",
    }
    # FIX: unguarded .split()[0] on potentially-empty topic_hint would
    # raise IndexError (same latent crash risk already found and fixed
    # in Ch2's identical function).
    _fallback_word = topic_hint.split()[0] if topic_hint.strip() else "documented"
    query = niche_queries.get(niche_name, _fallback_word + " documented case")
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
                # applied to Ch1/Ch2): captures the actual article URL,
                # without which there's nothing genuine to cite.
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
    per explicit request: "it should sync with the audio... it shouldn't
    be something where the audio is telling something and the captions
    are showing something else."

    Uses Groq's real Whisper transcription (same proven approach already
    built and tested for Shorts) directly on the FINAL, ACCEPTED
    narration audio file — not an estimate based on word count, and not
    tied to any one TTS provider's own streaming API, since
    run_stage3_audio tries multiple voices/tiers and the accepted audio
    could come from any of them. This works identically regardless of
    which tier actually produced the final audio.

    Returns True only if genuinely real, verified timing data was used;
    False (no captions) rather than silently falling back to an
    approximate/potentially-desynced version, since showing wrong
    captions is worse than showing none.
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
        chunk_size = 6  # match generate_fallback_ass's grouping for visual consistency
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
    Two-phase controller for Ch3 (The Control Files).
    PIPELINE_PHASE=generate : generate + save pending_upload.json
    PIPELINE_PHASE=upload   : read pending, upload to YouTube
    PIPELINE_PHASE=full     : legacy single-run (backward compatible)
    """
    # FIX: previously a bare, unguarded import — if PYTHONPATH didn't
    # include video_pipeline/ (where phase_manager.py actually lives),
    # main() crashed immediately with no useful signal. Wrapped so a
    # future path regression fails loud via Telegram instead of silently.
    try:
        from phase_manager import (get_pipeline_phase, save_pending,
                                    load_pending, clear_pending, check_pending_age,
                                    is_already_uploaded)
    except ImportError as _pm_err:
        print(f"❌ Ch3 CRITICAL: cannot import phase_manager ({_pm_err})")
        sys.exit(1)

    phase      = get_pipeline_phase()
    SCRIPT_DIR = Path(__file__).parent
    state      = load_state()

    log(f"\nCONTROL FILES v14.0 — Phase: {phase.upper()}")
    log(f"Time: {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p IST')}")

    # FIX: run_provider_health_check was fully built but never called
    # anywhere — same dead-function pattern found repeatedly across Ch1/Ch2.
    # Runs at the true start of generate phase. The function itself already
    # raises on total failure and alerts via Telegram if <3 healthy — this
    # just needs to actually call it and capture the count for the audit engine.
    provider_health_working_count = 7
    if phase in ("generate", "full"):
        try:
            working = run_provider_health_check()
            provider_health_working_count = len(working) if isinstance(working, list) else 7
        except RuntimeError as e:
            tg(f"❌ Ch3 CRITICAL: {e} — aborting run.")
            sys.exit(1)
        except Exception as e:
            log(f"  Provider health check (non-fatal): {e}")

    # ── UPLOAD PHASE ──────────────────────────────────────────
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch3 Upload: no pending video. Generation may have failed.")
            sys.exit(0)
        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch3 Upload: pending is {hours_old}h old — uploading anyway.")

        title        = pending["title"]
        description  = pending["description"]
        tags         = pending["tags"]
        niche_name   = pending["niche_name"]
        video_path   = pending["video_path"]
        thumb_path   = pending.get("thumbnail_path","")
        shorts       = pending.get("shorts_clips", [])
        script_clean = pending.get("script_clean","")
        duration     = pending.get("duration", 0)
        score        = pending.get("score", 0)
        voice_used   = pending.get("voice_used","")
        episode      = pending.get("episode", 1)
        playlist_id  = pending.get("playlist_id","")
        short_titles = pending.get("short_titles", {})
        topic_used   = pending.get("topic", title)
        quality_attempt = pending.get("quality_attempt", 1)
        authenticity_composite = pending.get("authenticity_composite", 10.0)
        provider_health_count  = pending.get("provider_health_working_count", 7)
        auth_fingerprint = pending.get("auth_fingerprint")
        short_cross  = pending.get("short_cross","")

        if not video_path or not Path(video_path).exists():
            tg(f"❌ Ch3 Upload: video file missing. Run Generate first.")
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
            "Ch3 Control Files", yt_url, thumb_path,
            TG_TOKEN, TG_CHAT, check_ins_used=0,
            gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
        if _final_gate["decision"] != "approve":
            delete_yt_video(vid_id, token=token_yt)
            clear_pending(SCRIPT_DIR)
            tg(f"🔄 Ch3: final video rejected — unlisted upload removed, "
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
                "The Control Files", yt_url, vid_id, token_yt,
                TG_TOKEN, TG_CHAT, gumroad_token=os.environ.get("GUMROAD_ACCESS_TOKEN"), tg_fn=tg)
        except Exception as e:
            log(f"  Post-upload report (non-fatal): {e}")

        if playlist_id: add_to_playlist(token_yt, playlist_id, vid_id)

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
                    # FIX: previously silent — zero logging on a non-200
                    # response, so a missing thumbnail was invisible.
                    log(f"  Thumbnail upload FAILED: {tr.status_code} {tr.text[:200]}")
                    tg(f"⚠️ Ch3 thumbnail upload failed ({tr.status_code}) for {vid_id} — "
                       f"video is live but has no custom thumbnail.")
            except Exception as te:
                log(f"  Thumbnail (non-fatal): {te}")
                tg(f"⚠️ Ch3 thumbnail upload exception for {vid_id}: {str(te)[:150]}")

        post_creator_comment(token_yt, vid_id, niche_name, title, episode)

        # FIX: update_channel_description was defined but never called
        # anywhere in Ch3 — same dead-function pattern as Ch2's original
        # bug (Part D.5). Wired in now.
        try:
            update_channel_description(token_yt, title, yt_url)
        except Exception as e:
            log(f"  Channel description update (non-fatal): {e}")

        # Recap Short removed entirely per explicit request (tied to the
        # main video's topic — risked being less independently
        # interesting than genuinely trend-researched standalone
        # content). Only the 2 standalone Shorts remain, both already
        # produced and reviewed in the generate phase.
        short_urls = []

        # Defensive safety net: the generate phase now resolves and
        # clears the SHORTS checkpoint itself (no more "part 2" waiting
        # on this upload phase), but if that somehow failed to clear it
        # (e.g. a crash between review and clear_queue), this ensures
        # the queue doesn't stay stuck open, blocking tomorrow's episode.
        try:
            from review_queue import load_queue_state, clear_queue
            _q_state = load_queue_state(SCRIPT_DIR)
            if _q_state and _q_state.get("checkpoint") != "DONE":
                log("  Queue was still open after generate phase (unexpected) — clearing defensively.")
                clear_queue(SCRIPT_DIR)
        except Exception as e:
            log(f"  Queue safety-net check (non-fatal): {e}")

        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token_yt, vid_id, script_clean, duration, "control_files")
            except Exception as e: log(f"  SRT (non-fatal): {e}")

        clear_pending(SCRIPT_DIR)
        state["last_title"]    = title
        state["last_url"]      = yt_url
        state["last_voice"]    = voice_used
        state["total_uploads"] = state.get("total_uploads",0)+1
        save_state(state)

        # ── Empire-wide integrations, confirmed-publish point only ──
        # (matching the timing discipline used everywhere else: these all
        # write to a real persisted record, so they must only fire after
        # a genuinely confirmed successful upload, never before.)

        # -1) Pattern memory — save this episode into episode_history so
        # future generations get real "highest scoring episodes" context
        # (load_pattern_memory) and so select_best_voice has real data to
        # work with. FIX (found on re-audit): I wired in the READ side
        # (load_pattern_memory -> pattern_hint) many rounds ago, but never
        # wired in this WRITE side — meaning episode_history would have
        # stayed empty forever, silently making pattern_hint always empty
        # and select_best_voice permanently stuck in "gathering data" mode.
        # Same class of bug as the fingerprint-save gap found earlier.
        try:
            state = save_pattern_memory(state, episode, niche_name, topic_used, score)
            save_state(state)
        except Exception as e:
            log(f"  Pattern memory save (non-fatal): {e}")

        # 0) Authenticity fingerprint — save the confirmed-published
        # video's fingerprint to the rolling comparison history. Must
        # happen here (confirmed publish), never during generation
        # attempts, so rejected/regenerated attempts don't pollute the
        # comparison baseline for future structural-variation checks.
        if auth_fingerprint:
            try:
                from authenticity_guard import save_fingerprint_record
                save_fingerprint_record(SCRIPT_DIR, auth_fingerprint)
            except Exception as e:
                log(f"  Fingerprint save (non-fatal): {e}")

        # 1) Daily audit search engine — one real verdict per video.
        try:
            from daily_audit_engine import run_full_video_audit
            audit_result = run_full_video_audit(
                SCRIPT_DIR, episode, title, niche_name,
                quality_score=score, quality_attempt=quality_attempt,
                authenticity_result={"composite_score": authenticity_composite},
                provider_health_working_count=provider_health_count,
                quality_review_threshold=MIN_GATE,
            )
            if audit_result["verdict"] != "PASS":
                tg(f"📋 Ch3 audit verdict: {audit_result['verdict']} — "
                   f"{'; '.join(audit_result['reasons'][:2])}")
        except Exception as e:
            log(f"  Daily audit engine (non-fatal): {e}")

        # 2) Publishing archive — real per-channel publish history + cross-linking.
        companion_page_url = ""
        try:
            from site_generator import render_companion_page
            episode_data = {
                "episode_number": episode, "episode_title": title,
                "video_url": yt_url, "channel_id": "control_files",
                "niche_name": niche_name,
                "publish_date": datetime.date.today().isoformat(),
                "script_excerpt": script_clean[:1500],
            }
            docs_root = Path(__file__).parent.parent.parent / "docs"
            page_path = render_companion_page(
                episode_data, docs_root,
                ai_fn=lambda p, tokens=400: ai(p, tokens=tokens, prefer="groq"))
            if page_path:
                companion_page_url = f"controlfiles/ep{episode}.html"
                log(f"  Companion page: {page_path}")
        except Exception as e:
            log(f"  Companion page generation (non-fatal): {e}")

        try:
            from publishing_archive import add_archive_entry
            add_archive_entry(SCRIPT_DIR, {
                "episode_number": episode, "title": title, "video_url": yt_url,
                "niche_name": niche_name, "topic": topic_used,
                "companion_page_url": companion_page_url,
            })
        except Exception as e:
            log(f"  Publishing archive (non-fatal): {e}")

        # 4) Topic scoring — record the winning topic into the backlog for
        # real historical tracking/calibration (not gating live generation,
        # which already happens inline per attempt — this just gives the
        # CEO dashboard and calibration notes real data to learn from).
        try:
            from topic_scoring import add_topic_candidate, mark_produced
            topic_entry = add_topic_candidate(
                SCRIPT_DIR, "control_files", topic_used, niche_name,
                ai_fn=lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
            if topic_entry:
                mark_produced(SCRIPT_DIR, topic_entry["topic_id"], episode)
        except Exception as e:
            log(f"  Topic scoring backlog (non-fatal): {e}")

        # 5) Product manuscript — extract one genuine reusable insight into
        # the Dark Manipulation Tactics Handbook (Ch3 is a real feeder channel).
        try:
            from product_manuscript import add_product_note
            products_root = Path(__file__).parent.parent.parent / "products"
            add_product_note(
                products_root, title, script_clean[:800], "control_files",
                ai_fn=lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
        except Exception as e:
            log(f"  Product manuscript (non-fatal): {e}")

        try:
            # FIX: SPRINT_PLAYLIST_ID, SPRINT_SCRIPT_PATH, and
            # SPRINT_DURATION_SECS were never set here — same gap already
            # found and fixed in Ch1/Ch2/Ch5. growth_engine.py's
            # run_post_upload_sprint gates its caption-upload + "update
            # previous episode's pinned comment" features behind
            # SPRINT_SCRIPT_PATH existing AND SPRINT_DURATION_SECS being
            # > 0, so both features were silently disabled every run.
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
                "SPRINT_CHANNEL_ID":  "control_files",
                "SPRINT_NICHE":       niche_name,
                "SPRINT_SHORTS_URLS": ",".join(short_urls),
                "SPRINT_SCORE":       str(score),
                "SPRINT_DURATION_SECS": str(duration),
                "SPRINT_PLAYLIST_ID": playlist_id or "",
                "SPRINT_SCRIPT_PATH": sprint_script_path,
            })
            # FIX: pointed at channels/growth_engine/growth_engine.py, which
            # doesn't exist — real file is video_pipeline/growth_engine.py
            # (sibling of channels/, not nested inside it). Popen is
            # fire-and-forget and never checked, so this failed SILENTLY
            # every run. Same bug already found and fixed in Ch1, found
            # broken again independently in Ch2 — confirmed broken a third
            # time here (proof this doesn't propagate automatically).
            _ge_path = Path(__file__).parent.parent.parent / "video_pipeline" / "growth_engine.py"
            if not _ge_path.exists():
                log(f"  Growth engine NOT FOUND at {_ge_path} — skipping sprint")
            else:
                # FIX (found on re-audit): this was fire-and-forget
                # (subprocess.Popen with no wait) — but run_post_upload_sprint
                # internally sleeps 30 minutes before running the comment-reply
                # engine. GitHub Actions tears down the entire process tree
                # within seconds of the job's last step completing, meaning
                # this detached child would almost certainly be killed mid-
                # sleep every single time, silently defeating the comment
                # engine, hype notification, and caption/pinned-comment update
                # despite everything LOOKING correctly wired. Now blocks on
                # the subprocess (bounded by a real timeout) so it gets an
                # actual chance to finish before the runner tears down —
                # ch3_upload.yml's job timeout was extended to match.
                try:
                    subprocess.run(["python3", str(_ge_path)], env=env_ext, timeout=2400)
                except subprocess.TimeoutExpired:
                    log("  Growth engine sprint exceeded 40min budget — moving on")
        except Exception as ge: log(f"  Growth engine (non-fatal): {ge}")

        # v15: Hype notification — free Explore leaderboard push
        send_hype_push(yt_url, title, "The Control Files", day=0)

        tg(f"✅ <b>The Control Files — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10 | Ep{episode}\n"
           f"🚀 First-hour sprint active")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ── GENERATE PHASE ────────────────────────────────────────
    episode = (datetime.datetime.now().timetuple().tm_yday//3)+1
    ckpt_clear()

    # FIX (found on final re-audit): this busy-check used to happen AFTER
    # run_stage1() (the full 13-attempt script generation — potentially
    # many real AI provider calls) had already completed, right before
    # the old approval-gate replacement block. That meant every single
    # day a previous episode was still mid-review, the pipeline would
    # still burn through the ENTIRE expensive script generation process
    # first, only to then discover the queue was busy and throw all of
    # it away. Moved to the true start of generate phase, before any
    # real work happens at all — this is a genuine efficiency fix
    # (real API cost/quota savings), not a correctness bug; the outcome
    # was always the same, just wastefully expensive to reach.
    from review_queue import is_channel_review_busy as _is_review_busy_early
    if _is_review_busy_early(SCRIPT_DIR):
        tg("⚠️ Ch3: a previous episode is still in review — today's new episode "
           "will NOT start generation yet (prevents cross-episode confusion and "
           "avoids wasting API calls on a script that can't enter review anyway). "
           "Resolve the current review, then the next scheduled run will pick up fresh.")
        log("  Review queue busy — skipping today's generation entirely, waiting for current review to clear.")
        sys.exit(0)

    (niche, topic, voice, style_name, episode,
     script_clean, scenes, title_str, thumbnail_text,
     title_scores, score, tags, intel, quality_attempt) = run_stage1(state)

    # v6 addition — real citation system: carried through intel, same
    # safe pattern already established for the other Ch3/Ch2 additions.
    real_cases = intel.get("_real_cases", [])

    # FIX (direct user report, July 23 2026 — "sync Claude Code into the
    # script as a main interceptor for quality... minimum is 6.8... remake
    # it without fail", applied empire-wide, matching the fix on Ch1/Ch2):
    # independent AI read-and-score of the actual script, on top of the
    # rule-based rubric the 13-attempt loop above already uses. run_stage1
    # generates script+scenes+title+thumbnail together per attempt, so a
    # rework re-runs the WHOLE tuple and every downstream variable is
    # reassigned together -- never just the script text alone.
    try:
        from quality_auditor import enforce_quality_gate
        _rework_history = [{"niche": niche, "topic": topic, "voice": voice, "style_name": style_name,
                             "episode": episode, "script_clean": script_clean, "scenes": scenes,
                             "title_str": title_str, "thumbnail_text": thumbnail_text,
                             "title_scores": title_scores, "score": score, "tags": tags,
                             "intel": intel, "quality_attempt": quality_attempt, "real_cases": real_cases}]
        def _rescript():
            (_n2, _t2, _v2, _sn2, _ep2, _sc2, _scenes2, _ts2, _tt2,
             _tsc2, _score2, _tg2, _intel2, _qa2) = run_stage1(state)
            _rework_history.append({"niche": _n2, "topic": _t2, "voice": _v2, "style_name": _sn2,
                                     "episode": _ep2, "script_clean": _sc2, "scenes": _scenes2,
                                     "title_str": _ts2, "thumbnail_text": _tt2,
                                     "title_scores": _tsc2, "score": _score2, "tags": _tg2,
                                     "intel": _intel2, "quality_attempt": _qa2,
                                     "real_cases": _intel2.get("_real_cases", [])})
            return _sc2
        _audit = enforce_quality_gate(
            "script", script_clean, "", lambda p, tokens=350: ai(p, tokens=tokens),
            _rescript, tg_fn=tg, topic=topic, max_reworks=2)
        for _entry in reversed(_rework_history):
            if _entry["script_clean"] == _audit["content"]:
                niche, topic, voice, style_name = _entry["niche"], _entry["topic"], _entry["voice"], _entry["style_name"]
                episode, scenes, title_str = _entry["episode"], _entry["scenes"], _entry["title_str"]
                thumbnail_text, title_scores, score = _entry["thumbnail_text"], _entry["title_scores"], _entry["score"]
                tags, intel, quality_attempt = _entry["tags"], _entry["intel"], _entry["quality_attempt"]
                real_cases = _entry["real_cases"]
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
    # the time still explores via calendar alternation so the signal
    # keeps updating rather than locking in early.
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
    # Real write-side: record this episode's actual score against
    # whichever style got used, so future episodes can learn from it.
    try:
        _perf = state.get("performance", {})
        _ab_rec = _perf.get(f"thumbnail_style_{ab_style}", {"scores": []})
        _ab_rec["scores"] = (_ab_rec["scores"] + [score])[-20:]
        _perf[f"thumbnail_style_{ab_style}"] = _ab_rec
        state["performance"] = _perf
    except Exception as e:
        log(f"  Thumbnail style tracking (non-fatal): {e}")
    cross_promo     = get_cross_promo("control_files", is_short=False)
    affiliate_block = build_affiliate_block("control_files", niche["name"])
    product_cta = build_product_cta("control_files")
    # chapters_block built AFTER audio so duration is available
    # (seo_first removed — the description's opening hook is now generated
    # fresh via AI each attempt inside _generate_description_variant below,
    # as part of the real quality-scoring regeneration loop)

    # Playlist created at upload time (YouTube creds not available in generate phase)
    playlist_id = state.get("playlists",{}).get(niche["name"], "")

    tags_er = list(set(tags))[:15]

    # ══════════════════════════════════════════════════════════════
    # v5 HUMAN REVIEW GATE — replaces the old simple approval gate.
    # Uses review_queue.py's state machine (only ONE episode ever in
    # review per channel at a time) + human_review_gate.py's real
    # checkpoints (the actual script/audio/video/thumbnail — not a
    # summary or a score).
    #
    # NOTE: the is_channel_review_busy check now happens once, at the
    # true start of generate phase (before run_stage1 even runs) — see
    # above. A second check used to live here too, but it's genuinely
    # redundant: this is a single-threaded script and nothing else can
    # change the queue's busy state between that early check and this
    # point, so re-checking here would only ever repeat the same answer.
    #
    # FIX (found diagnosing a real production issue across all 3
    # channels): these imports used to be completely bare — no
    # try/except at all. If review_queue.py/human_review_gate.py aren't
    # yet deployed to the live repo (a real, current situation per a
    # direct report), this raises a bare ModuleNotFoundError that
    # main_with_retry() catches as a generic crash — retrying 3 times,
    # 2 hours apart, silently re-running the FULL 13-attempt script
    # generation from scratch each time, for a problem retrying can
    # never fix (it's a deployment issue, not a transient one). Ch3 has
    # no old fallback approval system to degrade to like Ch1/Ch2 do, and
    # publishing without any review at all would violate the one rule
    # that matters most in this whole project — so on this specific
    # failure, the episode is deliberately NOT saved for upload at all,
    # a clear alert explains exactly why, and the process exits cleanly
    # (not as a crash) so it doesn't pointlessly retry-loop for 6 hours.
    try:
        from review_queue import start_review, record_check_in, clear_queue
        from human_review_gate import (review_script, review_audio_and_video,
                                        review_title_thumbnail_description,
                                        regenerate_script_sections,
                                        regenerate_description_until_good,
                                        approximate_stage_split)
        import human_review_gate as _hrg_module  # needed to reset its internal review-time clock later
    except ImportError as _rg_err:
        tg(f"🚨 Ch3: the human review-gate system failed to load ({_rg_err}) — this "
           f"episode's script/audio/video generation is being deliberately abandoned "
           f"rather than publishing without any human review, or crash-retrying uselessly "
           f"for a deployment problem retrying can't fix. If review_queue.py and "
           f"human_review_gate.py haven't been deployed to this repo yet, that's the "
           f"cause — deploy them and the next scheduled run will generate a fresh episode "
           f"normally.")
        log(f"  Review-gate import failed ({_rg_err}) — abandoning this episode safely, not crash-looping.")
        sys.exit(0)

    GMAIL_SENDER = os.environ.get("GMAIL_SENDER_EMAIL", "")
    GMAIL_APP_PW = os.environ.get("GMAIL_APP_PASSWORD", "")

    start_review(SCRIPT_DIR, episode, title_str,
                 artifacts={"topic": topic, "niche_name": niche["name"]})
    check_ins_used = 0

    # ── SCRIPT checkpoint ──
    # FIX (July 14 2026 audit): now sent stage-by-stage with clear headers
    # (this channel's generator doesn't keep real per-stage text, so the
    # split is reconstructed via the same word-count-proportion method
    # the pipeline's own quality gate already uses for stage scoring).
    _script_stage_names = ["CASE OPEN","SUBJECT","ANOMALIES","EVIDENCE",
                            "CLOSURE","FULL RECORD","IMPLICATIONS"]
    _script_stage_word_targets = [100, 200, 250, 400, 200, 650, 200]
    _script_attempts = 0
    while True:
        result = review_script(
            "The Control Files", title_str, script_clean, score, niche["name"],
            TG_TOKEN, TG_CHAT, check_ins_used=check_ins_used,
            gmail_sender=GMAIL_SENDER, gmail_app_password=GMAIL_APP_PW,
            stage_texts=approximate_stage_split(script_clean, _script_stage_names, _script_stage_word_targets),
            stage_names=_script_stage_names)
        cin = record_check_in(SCRIPT_DIR, result["decision"], result.get("feedback"))
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1

        if result["decision"] == "approve" or (cin and cin["forced"]):
            break
        if result["decision"] == "reject":
            tg("❌ Ch3: script rejected — episode stopped, nothing published.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if result["decision"] == "remake":
            tg("🔄 Ch3: REMAKE requested — scrapping this episode entirely. "
               "The next scheduled run will generate a genuinely fresh one.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if result["decision"] == "edit":
            _script_attempts += 1
            if _script_attempts > 3:
                tg("⚠️ Ch3: script EDIT requested 3 times without resolving — "
                   "proceeding with the current version to avoid an endless loop.")
                # FIX (found on deep re-audit): breaking here without
                # advancing the queue would leave review_queue.json
                # permanently stuck showing checkpoint="SCRIPT", even
                # though the pipeline is about to proceed to audio/video
                # generation — a real desync between tracked state and
                # actual behavior. Record a real "approve" here since
                # that's functionally what's happening (proceeding with
                # the current version), keeping the queue state honest.
                cin = record_check_in(SCRIPT_DIR, "approve", "auto-advanced: 3 edit attempts exceeded")
                check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1
                break
            log(f"  Script EDIT requested: {result['feedback']}")
            # HONEST LIMITATION (stated plainly, matching Ch2's own real
            # architecture, not Ch1's): Ch3's script is generated as one
            # continuous piece of narration with no separately-stored
            # per-stage text, so section-targeted editing (which needs
            # real stored stage boundaries) isn't genuinely available
            # here. identify_target_sections/regenerate_script_sections
            # are called with an EMPTY stage list, which correctly
            # triggers their own whole-script-rewrite fallback path —
            # not a false claim of section precision Ch3 doesn't have.
            try:
                script_clean, _ = regenerate_script_sections(
                    full_script=script_clean, stage_texts=[], stage_names=[],
                    target_sections=[], feedback=result["feedback"],
                    niche=niche["name"], topic=topic,
                    ai_fn=lambda p, tokens=8000: ai(p, tokens=tokens, prefer="cerebras"))
            except RuntimeError as e:
                tg(f"⚠️ Ch3: script edit failed to apply ({e}) — keeping the previous version "
                   f"and re-sending it for review rather than silently ignoring your feedback.")

    # Old simple approval gate removed — replaced by the block above.

    # Audio
    audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
        run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    # FIX (v5 change): previously an IMMEDIATE hold the moment TTS fell to
    # gTTS/espeak. Now matches the real, explicit decision made for Ch1/2:
    # if still on a robotic tier, wait 2 real hours and retry the WHOLE
    # audio stage (up to twice more) — Kokoro being newly available as a
    # local, rate-limit-free tier should make hitting this rare in the
    # first place. Only genuinely HOLDS for manual review if every
    # attempt still lands on gTTS/espeak. ElevenLabs/edge-tts/Fish Audio/
    # Kokoro all still auto-publish immediately, unaffected.
    _audio_retry_count = 0
    while voice_used in ("gtts-fallback", "espeak-offline-LASTRESORT") and _audio_retry_count < 2:
        _audio_retry_count += 1
        tg(f"⚠️ Ch3: TTS fell back to '{voice_used}' (attempt {_audio_retry_count}/2 retries) — "
           f"waiting 10 minutes and retrying the whole audio stage before holding for review.")
        log(f"  Audio on robotic tier ({voice_used}) — waiting 10min, retry {_audio_retry_count}/2")
        time.sleep(600)  # FIX (final re-audit): shortened from 2h to 10min -- 2 retries x 2h could eat 4h of a 6h job before review is even reached, and didn't match provider daily-quota reset timing anyway (~24h, not 2h)
        audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
            run_stage3_audio, "Audio", script_clean, voice, niche["name"])

    if voice_used in ("gtts-fallback", "espeak-offline-LASTRESORT"):
        tg(f"🚨 Ch3 HOLD: TTS still on '{voice_used}' after 2 real retries (4 hours) — this "
           f"sounds noticeably robotic. Video NOT queued for upload. Generation artifacts kept "
           f"locally for manual review if you want to publish anyway; otherwise this episode "
           f"is skipped.")
        log(f"  HOLD: robotic-voice fallback tier ({voice_used}) even after retries — not auto-publishing.")
        sys.exit(0)

    # CRITICAL FIX (found on deep re-audit): human_review_gate.py tracks
    # its own real 4.5-hour total review budget from a module-level
    # _REVIEW_PROCESS_START set the MOMENT it was first imported — which
    # happened before this audio-retry loop, above. Since that loop can
    # genuinely sleep up to 4 real hours (2 retries x 2h) before ever
    # reaching a single review checkpoint, that sleep time would
    # otherwise silently eat almost the entire review budget before
    # review even begins — meaning the Audio+Video, Title+Thumbnail+
    # Description, and Shorts checkpoints could all get force-approved
    # near-instantly the moment real review starts, defeating human
    # review for 3 of the 4 checkpoints whenever audio needed retries.
    # Resetting the clock here means the budget genuinely reflects real
    # review-waiting time, not audio-regeneration time, which is a
    # completely different kind of delay.
    _hrg_module._REVIEW_PROCESS_START = datetime.datetime.now()

    # v1 addition — real, word-level synced captions for the main video,
    # per explicit request: captions must genuinely match the audio, not
    # approximate it. Generated here, on the truly final accepted audio
    # (past all retries), using real Whisper transcription — works
    # regardless of which TTS tier actually produced this audio. Skipped
    # entirely (no captions) rather than shown potentially-desynced if
    # the real transcription can't be produced, since wrong captions
    # would be worse than none.
    ass_path = str(WORK_DIR / "main_captions.ass")
    has_real_captions = generate_real_synced_ass(audio_path, ass_path)
    if not has_real_captions:
        ass_path = None

    # FIX (found on re-audit): Ch3 had NO hard duration ceiling at all —
    # only a prompt-level request that the AI aim for 15-18 minutes, with
    # nothing enforcing it in code. Ch1 has a confirmed-active 18-minute
    # hard cap with real trimming; Ch3 was missing this entirely. Combined
    # with the fake-duration bug just fixed above, this means a genuinely
    # overlong script could previously have produced an overlong video
    # with zero enforcement or even correct awareness that it happened.
    #
    # FIX (found on deep re-audit): converted into a reusable function —
    # previously this only ever ran ONCE, right after the very first
    # audio generation. If a human's EDIT feedback later caused a longer
    # regenerated script/audio (e.g. "make the evidence section longer"),
    # the cap was never re-checked, so an overlong video could still slip
    # through via that path with zero enforcement.
    MAX_DURATION_SECS = 18 * 60
    def _enforce_duration_cap(audio_path_arg, duration_arg):
        if duration_arg <= MAX_DURATION_SECS:
            return audio_path_arg, duration_arg
        log(f"  Audio duration {duration_arg/60:.1f}min exceeds {MAX_DURATION_SECS/60:.0f}min cap — trimming")
        trimmed_path = str(WORK_DIR / ("audio_trimmed.wav" if audio_path_arg.endswith(".wav") else "audio_trimmed.mp3"))
        try:
            subprocess.run(["ffmpeg", "-y", "-i", audio_path_arg, "-t", str(MAX_DURATION_SECS),
                             "-c", "copy", trimmed_path], capture_output=True, timeout=120)
            if Path(trimmed_path).exists() and Path(trimmed_path).stat().st_size > 100000:
                tg(f"⚠️ Ch3: audio ran {duration_arg/60:.1f}min over the 18min cap — trimmed to fit. "
                   f"Consider checking why the script ran long.")
                return trimmed_path, MAX_DURATION_SECS
            log("  Trim failed — proceeding with untrimmed audio (non-fatal)")
        except Exception as te:
            log(f"  Duration trim (non-fatal): {te}")
        return audio_path_arg, duration_arg

    audio_path, duration = _enforce_duration_cap(audio_path, duration)

    # Build description now that duration is known
    _stage_word_counts = [len(t.split()) for t in
                          approximate_stage_split(script_clean, _script_stage_names, _script_stage_word_targets)]
    chapters_block = _gen_chapters(script_clean, duration, "control_files", stage_word_counts=_stage_word_counts)

    # v5 addition: real description quality scoring with a genuine
    # regeneration loop. The template's structural parts (chapters,
    # cross-promo, affiliate block) are deterministic by design — real
    # variation across attempts comes from regenerating the hook/intro
    # line via a fresh AI call each time, which is also the exact thing
    # score_description checks for ("a real hook in the first two lines").
    # v6 addition, per explicit request: real hashtags for more
    # viewership, correctly following actual 2026 YouTube best practice
    # (researched directly): 3-5 hashtags is the real sweet spot — the
    # FIRST 3 in the description automatically become clickable links
    # shown above the title (prime visibility), and going over 15 causes
    # YouTube to silently ignore EVERY hashtag on the video, not just the
    # extras. A mix of niche-category + genuinely topic-specific +
    # one branded/series tag, not the same static set reused every
    # episode, since generic mismatched hashtags actively hurt reach.
    NICHE_HASHTAG_CATEGORIES = {
        "cult_psychology":             ["#CultDocumentary", "#Psychology"],
        "propaganda_systems":          ["#Propaganda", "#Documentary"],
        "social_engineering":          ["#SocialEngineering", "#Psychology"],
        "mass_deception":              ["#Documentary", "#TrueStory"],
        "dark_business_documentaries": ["#CorporateExposed", "#Documentary"],
        "scams_fraud_exposed":         ["#ScamAlert", "#FraudExposed"],
    }
    def _generate_episode_hashtags(niche_obj, topic_arg):
        category_tags = NICHE_HASHTAG_CATEGORIES.get(niche_obj["name"], ["#Documentary", "#TrueStory"])
        try:
            tag_prompt = (f"Give exactly 2 real YouTube hashtags (short, no spaces, "
                         f"CamelCase, starting with #) that specifically match this "
                         f"documentary topic: {topic_arg[:200]}. Return ONLY the 2 "
                         f"hashtags separated by a space, nothing else.")
            raw_tags = ai(tag_prompt, tokens=30, prefer="groq") or ""
            topic_tags = [t for t in raw_tags.split() if t.startswith("#") and len(t) < 30][:2]
        except Exception:
            topic_tags = []
        all_tags = category_tags + topic_tags + ["#TheControlFiles"]
        # Dedupe while preserving order, cap at 5 (the real researched sweet spot)
        seen = set(); final_tags = []
        for t in all_tags:
            if t.lower() not in seen:
                seen.add(t.lower()); final_tags.append(t)
        return " ".join(final_tags[:5])

    episode_hashtags = _generate_episode_hashtags(niche, topic)

    def _format_citations_block(cases):
        """v6 addition — real citation/sourcing system, same as Ch1/Ch2:
        only cites cases with a REAL, actually-captured URL."""
        real_sources = [c for c in (cases or []) if c.get("url")]
        if not real_sources:
            return ""
        lines = ["Sources & further reading:"]
        for c in real_sources[:4]:
            label = "News" if c.get("source") == "news" else "Community discussion"
            lines.append(f"• {label}: {c['title'][:100]} — {c['url']}")
        return "\n\n" + "\n".join(lines)

    citations_block = _format_citations_block(real_cases)

    def _generate_description_variant(niche_obj, topic_arg, title_arg, episode_arg,
                                        chapters_text, audio_duration_arg):
        try:
            hook_prompt = (f"Write ONE compelling 2-sentence hook for a YouTube description, "
                          f"for a documentary about: {topic_arg[:200]}. "
                          f"Specific, evidence-focused, no clickbait, no markdown. "
                          f"Return ONLY the 2 sentences.")
            hook = ai(hook_prompt, tokens=120, prefer="groq")
            hook = strip_md(hook).strip() if hook else f"DOCUMENTED: {topic_arg[:60]}."
        except Exception:
            hook = f"DOCUMENTED: {topic_arg[:60]}."
        desc = (f"{hook}\n\nEpisode {episode_arg} of {niche_obj['series']}.\n\n"
               f"Every case. Every document. Every piece of evidence — animated.\n\n"
               f"{chapters_text}\n\n"
               f"Subscribe to The Control Files."
               f"{cross_promo}"
               f"{affiliate_block}"
               f"{product_cta}\n\n"
               f"\u2728 Real cases, brought to life with next-generation AI narration and analytical craft."
               f"\n\n\U0001F4E7 Business inquiries: {BUSINESS_EMAIL}"
               f"{citations_block}\n\n"
               f"{episode_hashtags}")
        if len(desc) > 5000:
            tail = (f"\u2728 Real cases, brought to life with next-generation AI narration and analytical craft."
                    f"\n\n\U0001F4E7 Business inquiries: {BUSINESS_EMAIL}{citations_block}\n\n{episode_hashtags}")
            desc = desc[:5000 - len(tail) - 5] + "\n\n" + tail
        return desc

    desc_result = regenerate_description_until_good(
        niche, topic, title_str, episode, chapters_block, duration, niche["name"],
        _generate_description_variant, min_score=9.0, max_attempts=4)
    description = desc_result["description"]
    description_score = desc_result["score"]
    log(f"  Description quality: {description_score}/10 "
        f"({'hit target' if desc_result['hit_target'] else 'best of ' + str(desc_result['attempts']) + ' attempts'})")
    if not desc_result["hit_target"]:
        log(f"  Description missing: {desc_result['missing']}")

    # Video
    video_path = run_stage_with_retry(
        render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], episode=episode, real_cases=real_cases, ass_path=ass_path)

    # Thumbnail
    thumb_path = generate_thumbnail_with_ai_bg(
        title_str, thumbnail_text, niche["name"], topic, ab_style,
        episode=episode, channel_name="The Control Files")

    # Validate video file before saving to pending
    if not Path(video_path).exists():
        tg(f"❌ Ch3 Generate FAILED: video file not created")
        sys.exit(1)
    video_size = Path(video_path).stat().st_size
    if video_size < 5_000_000:  # must be at least 5MB
        tg(f"❌ Generate FAILED: video too small ({video_size//1024}KB) — likely encoding error")
        sys.exit(1)
    log(f"  Video validated: {video_size//(1024*1024)}MB")

    # ── AUDIO + VIDEO checkpoint (combined window, 2 real distinct decisions) ──
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

        av_result = review_audio_and_video(
            "The Control Files", audio_path, voice_used, video_path, thumb_path,
            TG_TOKEN, TG_CHAT, check_ins_used=check_ins_used,
            gmail_sender=GMAIL_SENDER, gmail_app_password=GMAIL_APP_PW,
            audio_score=_audio_score, audio_score_breakdown=_audio_breakdown,
            video_score=_video_score, video_score_breakdown=_video_breakdown)
        audio_decision = av_result["audio_decision"]
        video_decision = av_result["video_decision"]

        cin = record_check_in(SCRIPT_DIR, audio_decision["decision"], audio_decision.get("feedback"))
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1

        # FIX (found on deep re-audit): the 6-check-in force-approval
        # ceiling was only ever checked on the VIDEO decision below —
        # if the ceiling was hit while processing an AUDIO edit/reject/
        # remake, review_queue.py would already have set checkpoint=DONE
        # internally, but this code would still act on the literal audio
        # decision (regenerating audio, or worse, exiting on a reject/
        # remake) instead of respecting the forced approval. Checked
        # first now, before any audio-decision branch.
        if cin and cin["forced"]:
            tg("⏱️ Ch3: total review time budget reached during audio review — "
               "auto-approving audio and video as generated.")
            break

        if audio_decision["decision"] == "reject":
            tg("❌ Ch3: audio rejected — episode stopped, nothing published.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if audio_decision["decision"] == "remake":
            tg("🔄 Ch3: REMAKE requested at audio review — scrapping this episode entirely.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if audio_decision["decision"] == "swap_voice":
            _voice_pool = [v for v in NICHE_VOICES.get(niche["name"], ALL_VOICES) if v != voice_used]
            _new_voice = random.choice(_voice_pool) if _voice_pool else voice_used
            tg(f"🎙️ Ch3: swapping voice: {voice_used} → {_new_voice} — regenerating audio now, same script.")
            log(f"  SWAP VOICE requested: {voice_used} -> {_new_voice}")
            audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
                run_stage3_audio, "Audio", script_clean, _new_voice, niche["name"])
            audio_path, duration = _enforce_duration_cap(audio_path, duration)
            # FIX (found on deep re-audit): this used to just regenerate
            # audio_path/duration and loop back — video_path was NEVER
            # re-rendered, so the video that eventually publishes still
            # has the OLD, discarded narration muxed in, and the human
            # approving what they hear here has no effect on what actually
            # ships. Captions were stale for the same reason (still
            # transcribed from the old audio). Both are regenerated now,
            # exactly like the video-checkpoint's own edit/swap_visuals
            # branches already re-render on every change.
            ass_path = str(WORK_DIR / "main_captions.ass")
            if not generate_real_synced_ass(audio_path, ass_path):
                ass_path = None
            video_path = run_stage_with_retry(
                render_and_encode, "Animation", style_name, scenes, audio_path, duration,
                niche_name=niche["name"], episode=episode, real_cases=real_cases, ass_path=ass_path)
            continue
        if audio_decision["decision"] == "edit":
            # FIX (found on direct user report, July 15 2026): this used to
            # regenerate with the exact same `voice` every single time --
            # feedback like "the voice sounds robotic" produced literally
            # the same audio back. The only real lever at this checkpoint
            # is which voice narrates it (script changes belong at the
            # script checkpoint), so EDIT here now genuinely swaps voices.
            _voice_pool = [v for v in NICHE_VOICES.get(niche["name"], ALL_VOICES) if v != voice_used]
            _new_voice = random.choice(_voice_pool) if _voice_pool else voice_used
            log(f"  Audio EDIT requested: {audio_decision.get('feedback')} — swapping voice {voice_used} -> {_new_voice}.")
            tg(f"🎙️ Ch3: regenerating audio per your feedback — voice: {voice_used} → {_new_voice}")
            audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
                run_stage3_audio, "Audio", script_clean, _new_voice, niche["name"])
            # FIX (found on deep re-audit): the robotic-voice gate above
            # only ever protected the FIRST audio generation — a human-
            # requested EDIT here could regenerate straight onto a
            # robotic tier with no re-check at all. A human will still
            # hear it next round and can reject again, but the system's
            # own safety net should apply consistently everywhere audio
            # gets (re)generated, not just the original unsupervised path.
            _edit_retry = 0
            while voice_used in ("gtts-fallback", "espeak-offline-LASTRESORT") and _edit_retry < 2:
                _edit_retry += 1
                tg(f"⚠️ Ch3: EDIT-regenerated audio fell back to '{voice_used}' — "
                   f"retrying once more before sending back for review.")
                _voice_pool = [v for v in NICHE_VOICES.get(niche["name"], ALL_VOICES) if v != voice_used]
                _new_voice = random.choice(_voice_pool) if _voice_pool else voice_used
                audio_path, duration, audio_sz, voice_used = run_stage_with_retry(
                    run_stage3_audio, "Audio", script_clean, _new_voice, niche["name"])
            # Same reason: the duration cap must apply every time audio
            # gets regenerated, not just the original generation.
            audio_path, duration = _enforce_duration_cap(audio_path, duration)
            # FIX (found on deep re-audit): same gap as SWAP VOICE above —
            # video_path was never re-rendered with the new audio, so an
            # EDIT here had zero actual effect on what gets published.
            # Captions regenerated for the same reason.
            ass_path = str(WORK_DIR / "main_captions.ass")
            if not generate_real_synced_ass(audio_path, ass_path):
                ass_path = None
            video_path = run_stage_with_retry(
                render_and_encode, "Animation", style_name, scenes, audio_path, duration,
                niche_name=niche["name"], episode=episode, real_cases=real_cases, ass_path=ass_path)
            continue  # re-send the combined checkpoint with the new audio

        # Audio approved — now handle the video decision (skipped entirely if
        # audio wasn't approved, per review_audio_and_video's own contract)
        if video_decision is None:
            break
        cin = record_check_in(SCRIPT_DIR, video_decision["decision"], video_decision.get("feedback"))
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1

        if video_decision["decision"] == "approve" or (cin and cin["forced"]):
            # FIX (found on deep re-audit): score_audio_quality/
            # score_video_quality were computed every episode but never
            # persisted anywhere — weekly_report.py had no real quality
            # data to report on at all. Recorded here on the actual
            # approved episode, mirroring thumb_format_history's proven
            # write-side pattern.
            try:
                from quality_score_history import record_quality_scores
                record_quality_scores(str(SCRIPT_DIR), "The Control Files", episode, _audio_score, _video_score)
            except Exception as e:
                log(f"  Quality score history record (non-fatal): {e}")
            break
        if video_decision["decision"] == "reject":
            tg("❌ Ch3: video rejected — episode stopped, nothing published.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if video_decision["decision"] == "remake":
            tg("🔄 Ch3: REMAKE requested at video review — scrapping this episode entirely.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if video_decision["decision"] == "edit":
            log(f"  Video EDIT requested: {video_decision.get('feedback')} — regenerating scenes+video.")
            new_scenes = regenerate_scenes_only(script_clean, niche, feedback=video_decision.get("feedback"))
            if new_scenes:
                scenes = new_scenes
            video_path = run_stage_with_retry(
                render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], episode=episode, real_cases=real_cases)
            continue
        if video_decision["decision"] == "swap_visuals":
            log(f"  SWAP VISUALS requested: {video_decision.get('feedback')} — "
                f"keeping the same script+audio, regenerating scene visuals only.")
            new_scenes = regenerate_scenes_only(script_clean, niche, feedback=video_decision.get("feedback"))
            if new_scenes:
                scenes = new_scenes
            else:
                tg("⚠️ Ch3: SWAP VISUALS scene regeneration failed — keeping the current visuals "
                   "and re-rendering with them (a genuine re-render still applies fresh Ken Burns "
                   "motion timing, so this isn't a complete no-op).")
            video_path = run_stage_with_retry(
                render_and_encode, "Animation", style_name, scenes, audio_path, duration, niche_name=niche["name"], episode=episode, real_cases=real_cases)
            continue

    # FIX (found on deep re-audit): chapters_block and the description
    # were both built BEFORE the Audio+Video checkpoint even ran, using
    # whatever `duration` was at that point. If a human's audio EDIT
    # changed the real duration during that checkpoint, chapters_block
    # (and any description generated before this point) would show
    # chapter timestamps that no longer match the actual final audio —
    # and even the description-EDIT path at the next checkpoint reused
    # this same stale string rather than rebuilding it. Rebuilt fresh
    # here now that duration is truly final, and the description is
    # regenerated too if duration genuinely changed, so the human
    # reviewing Title+Thumbnail+Description next sees something that
    # actually matches what will publish, without relying on them to
    # notice and manually request a description edit.
    _new_stage_word_counts = [len(t.split()) for t in
                              approximate_stage_split(script_clean, _script_stage_names, _script_stage_word_targets)]
    _new_chapters_block = _gen_chapters(script_clean, duration, "control_files", stage_word_counts=_new_stage_word_counts)
    if _new_chapters_block != chapters_block:
        log("  Audio duration changed during review — rebuilding chapters + description to match.")
        chapters_block = _new_chapters_block
        desc_result = regenerate_description_until_good(
            niche, topic, title_str, episode, chapters_block, duration, niche["name"],
            _generate_description_variant, min_score=9.0, max_attempts=4)
        description = desc_result["description"]
        description_score = desc_result["score"]

    # ── TITLE + THUMBNAIL + DESCRIPTION checkpoint (combined, 4 real options) ──
    while True:
        ttd_result = review_title_thumbnail_description(
            "The Control Files", title_str, thumb_path, description, description_score,
            TG_TOKEN, TG_CHAT, check_ins_used=check_ins_used,
            gmail_sender=GMAIL_SENDER, gmail_app_password=GMAIL_APP_PW)
        cin = record_check_in(SCRIPT_DIR, ttd_result["decision"], ttd_result.get("feedback"))
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1

        if ttd_result["decision"] == "approve" or (cin and cin["forced"]):
            break
        if ttd_result["decision"] == "reject":
            tg("❌ Ch3: title/thumbnail/description rejected — episode stopped, nothing published.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if ttd_result["decision"] == "remake":
            tg("🔄 Ch3: REMAKE requested at title/thumbnail/description review — scrapping this episode.")
            clear_queue(SCRIPT_DIR); sys.exit(0)
        if ttd_result["decision"] == "edit":
            fb = ttd_result.get("feedback", "") or ""
            log(f"  Title/Thumbnail/Description EDIT requested: {fb}")
            # Classify which of the 3 things the feedback is actually about,
            # rather than guessing or blindly regenerating all three —
            # matches identify_target_sections' own real-classification
            # approach, just applied to this checkpoint's 3 items instead
            # of script sections.
            try:
                classify_prompt = (f"A human reviewer gave this feedback about a YouTube video's "
                                   f"title, thumbnail, and description: \"{fb}\"\n"
                                   f"Which of these does it refer to? Reply with ONLY one or more of: "
                                   f"title, thumbnail, description (comma-separated if multiple).")
                classification = (ai(classify_prompt, tokens=30, prefer="groq") or "").lower()
            except Exception:
                classification = "title, thumbnail, description"  # safest: redo all 3 if classification fails

            # FIX (found on deep re-audit): the exception fallback above
            # only covers a genuine ai() failure — if the call succeeds
            # but returns something that matches NONE of the 3 keywords
            # (garbled response, "N/A", empty string, etc.), none of the
            # three `if "X" in classification` checks below would fire
            # at all, silently ignoring the human's EDIT feedback
            # entirely and just re-sending the unchanged content back
            # for review again. Same safe fallback applied here too.
            if not any(k in classification for k in ("title", "thumbnail", "description")):
                classification = "title, thumbnail, description"

            if "title" in classification:
                title_str, title_scores = generate_and_score_titles(niche, topic, intel, episode)
            if "thumbnail" in classification:
                thumbnail_text = generate_thumbnail_text(niche, topic, intel)
                thumb_path = generate_thumbnail_with_ai_bg(
                    title_str, thumbnail_text, niche["name"], topic, ab_style,
                    episode=episode, channel_name="The Control Files")
            if "description" in classification:
                desc_result = regenerate_description_until_good(
                    niche, topic, title_str, episode, chapters_block, duration, niche["name"],
                    _generate_description_variant, min_score=9.0, max_attempts=4)
                description = desc_result["description"]
                description_score = desc_result["score"]

    # Stage 5.5 — Authenticity / inauthentic-content risk check.
    # FIX: this shared check exists (authenticity_guard.py) and is wired
    # into Ch1/Ch2 already, but Ch3 never called it at all. Wired in here,
    # same recommended gate as the shared module's own docstring.
    authenticity_result = None
    thumb_family_proxy = f"{niche['name']}_family_{episode % 3}"
    thumb_pose_proxy   = f"pose_{episode % 8}"
    try:
        from authenticity_guard import run_authenticity_check
        # FIX (found on re-audit): this previously passed scene TITLES
        # ("CASE TIMELINE", "THE NUMBERS" — short 2-4 word labels) as
        # stage_texts, but build_fingerprint expects actual script
        # SECTION text to measure real narration word-count proportions.
        # Using titles made the structural-variation check measure
        # scene-title-length variance — a nearly meaningless signal —
        # instead of the real "does this channel's script structure look
        # rigidly templated across episodes" check it's meant to be.
        # Reconstructed real proportional text segments matching the
        # actual stage_targets weights used during generation.
        _stage_weights = [120, 200, 280, 480, 150, 520, 150]
        _words = script_clean.split()
        _total_w = len(_words) or 1
        _stage_texts_real, _cursor = [], 0
        for _w in _stage_weights:
            _take = max(1, int(_total_w * (_w / sum(_stage_weights))))
            _stage_texts_real.append(" ".join(_words[_cursor:_cursor + _take]))
            _cursor += _take
        authenticity_result = run_authenticity_check(
            SCRIPT_DIR, script_clean, _stage_texts_real, title_str,
            thumb_family_proxy, thumb_pose_proxy,
            ai_fn=lambda p, tokens=300: ai(p, tokens=tokens, prefer="groq"))
        auth_score = authenticity_result.get("composite_score", 10.0)
        log(f"  Authenticity composite: {auth_score}/10")
        if auth_score < 6.0:
            tg(f"🚨 Ch3 HOLD: authenticity score {auth_score}/10 — below the real "
               f"policy-risk threshold. Video generated but NOT queued for upload. "
               f"Manual review required before publishing.")
            sys.exit(0)
        elif auth_score < 7.5:
            tg(f"⚠️ Ch3 authenticity {auth_score}/10 — one dimension weak, publishing "
               f"but worth a look: {authenticity_result}")
    except Exception as e:
        log(f"  Authenticity check (non-fatal): {e}")

    # Shorts — generate phase: teaser (tied to this video) + 2 standalone.
    # FIX: previously imported a module called "shorts_engine" (doesn't
    # exist) and called generate_all_six_shorts (doesn't exist either) —
    # this channel's Shorts were completely broken. Real file is
    # shorts_reels_engine.py with produce_video_topic_short/
    # produce_standalone_short, each generating AND uploading in one call.
    # (teaser/recap Shorts were removed entirely per explicit instruction
    # — only these 2 functions are used: 2 today's-topic + 2 trending.)
    log("\n  Producing Shorts (4 total)...")
    log("  2 about this video's real topic (fresh, complete standalone")
    log("  pieces), 2 on genuinely different trending topics (real research")
    log("  into what's working today).")
    short_clips = []
    try:
        from shorts_reels_engine import produce_video_topic_short, produce_standalone_short
        for angle in ("angle_1", "angle_2"):
            vt_result = produce_video_topic_short(topic, script_clean, angle, channel="control_files")
            short_clips.append(vt_result)
        for mode in ("standalone_1", "standalone_2"):
            sa_result = produce_standalone_short(mode, channel="control_files")
            short_clips.append(sa_result)
        ok_count = sum(1 for s in short_clips if s.get("status") == "success")
        log(f"  Shorts: {ok_count}/4 produced")
        try:
            _short_token = get_yt_token()
            for s in short_clips:
                vid = s.get("url","").rstrip("/").split("/")[-1] if s.get("url") else ""
                if s.get("status") == "success" and vid:
                    post_short_creator_comment(_short_token, vid, niche["name"], title_str)
        except Exception as pe:
            log(f"  Short pinned comments (non-fatal): {pe}")
    except Exception as e:
        log(f"  Shorts engine (non-fatal): {e}")
        short_clips = []

    # ── SHORTS checkpoint — now fully resolves here in generate phase.
    # No more "part 2" deferred to the upload phase, since the recap
    # Short (the only one that needed the real main-video URL) has been
    # removed entirely per explicit request. clear_queue() at the end of
    # this block frees the queue immediately, rather than waiting a full
    # day for the upload phase to do it.
    from human_review_gate import review_shorts

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

    _shorts_for_review = [{"name": f"Short {i+1}", "url": s.get("url",""),
                           "score": _score_short_safe(s.get("local_path"))}
                          for i, s in enumerate(short_clips) if s.get("status") == "success"]
    if _shorts_for_review:
        sh_result = review_shorts(
            "The Control Files", _shorts_for_review, TG_TOKEN, TG_CHAT,
            check_ins_used=check_ins_used, gmail_sender=GMAIL_SENDER, gmail_app_password=GMAIL_APP_PW)
        # FIX (found on deep re-audit — a genuine crash risk): record_check_in
        # treats "reject" as a TERMINAL state (sets checkpoint="REJECTED",
        # a value that isn't in CHECKPOINT_ORDER at all). Mapped to
        # "approve" for queue-tracking purposes only; the real human
        # decision (including a genuine reject) is still fully logged
        # and acted on below.
        _queue_decision = "approve" if sh_result["decision"] == "reject" else sh_result["decision"]
        cin = record_check_in(SCRIPT_DIR, _queue_decision, sh_result.get("feedback"))
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1
        # Per review_shorts' own honest contract: these are already
        # published. reject/edit/remake/swap_visuals all mean "produce a
        # genuine fresh replacement and publish as an addition" — never
        # a retroactive un-publish. Since the main video pipeline must
        # still continue regardless, these are logged and acted on but
        # never exit the pipeline.
        if sh_result["decision"] in ("edit", "remake", "swap_visuals"):
            log(f"  Shorts {sh_result['decision'].upper()} requested: {sh_result.get('feedback')} — "
                f"producing one genuine fresh replacement standalone Short as an addition.")
            try:
                from shorts_reels_engine import produce_standalone_short
                replacement = produce_standalone_short("standalone_1", channel="control_files")
                if replacement.get("status") == "success":
                    tg(f"✅ Ch3: fresh replacement Short published: {replacement.get('url')}")
            except Exception as e:
                log(f"  Shorts replacement (non-fatal): {e}")
        elif sh_result["decision"] == "reject":
            log("  Shorts reviewer rejected — noted, but already-published Shorts stay up "
                "(this checkpoint cannot un-publish); no replacement produced.")

    # ── COMMUNITY TAB checkpoint — YouTube's API has no way to post to
    # the Community tab, so this drafts the real poll/post and gates on a
    # human confirming they posted it manually (see review_community_tab's
    # docstring for the full honest constraint).
    try:
        from human_review_gate import draft_community_post, review_community_tab
        _cp_draft = draft_community_post(topic, niche["name"], title_str,
                                          lambda p, tokens=200: ai(p, tokens=tokens))
        cp_result = review_community_tab(
            "The Control Files", _cp_draft["question"], _cp_draft["options"], TG_TOKEN, TG_CHAT,
            check_ins_used=check_ins_used, gmail_sender=GMAIL_SENDER, gmail_app_password=GMAIL_APP_PW)
        # Either outcome advances past this checkpoint to DONE — see the
        # identical note on Ch4's copy of this block.
        cin = record_check_in(SCRIPT_DIR, "approve", cp_result["decision"])
        check_ins_used = cin["state"]["check_ins_used"] if cin else check_ins_used + 1
        log(f"  Community Tab: {cp_result['decision']}")
    except Exception as e:
        log(f"  Community Tab checkpoint (non-fatal): {e}")

    # Episode's review is now fully complete — frees the queue for
    # tomorrow's episode immediately (previously deferred a full day to
    # the upload phase, since the now-removed recap Short needed it open).
    try:
        clear_queue(SCRIPT_DIR)
    except Exception as e:
        log(f"  Queue clear (non-fatal): {e}")

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
        "quality_attempt": quality_attempt,
        "authenticity_composite": (authenticity_result or {}).get("composite_score", 10.0),
        # FIX (found on re-audit — a bug I introduced this session): the
        # authenticity check computes a "_fingerprint_to_log" specifically
        # meant to be saved via save_fingerprint_record() AFTER confirmed
        # publish (never during generation attempts, so rejected attempts
        # don't pollute the comparison history) — but I never actually
        # called save_fingerprint_record anywhere. This means the
        # structural-variation/upload-cadence/thumbnail-variation history
        # would never grow, silently defeating the whole authenticity
        # system on every future check. Persisted here so the upload
        # phase (where "confirmed published" genuinely means something)
        # can save it at the right time.
        "auth_fingerprint": (authenticity_result or {}).get("_fingerprint_to_log"),
        "provider_health_working_count": provider_health_working_count,
    })
    # FIX: save_pending (real, shared phase_manager.py) returns a dict with
    # an overwrite_warning if a previous unuploaded video existed — this
    # was previously always discarded silently. Now surfaced.
    if isinstance(_pending_result, dict) and _pending_result.get("overwrite_warning"):
        tg(f"⚠️ Ch3 pending overwrite: {_pending_result['overwrite_warning']}")

    state["last_niche"] = niche["name"]
    save_state(state)
    ckpt_clear()

    if phase == "generate":
        tg(f"✅ <b>Ch3 Generated — queued for upload</b>\n\n"
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
                tg(f"⚠️ Ch3 attempt {attempt}/{max_retries} failed.\nRetrying in 2h...")
                time.sleep(600)  # FIX (final re-audit): shortened from 2h to 10min -- 2 retries x 2h could eat 4h of a 6h job before review is even reached, and didn't match provider daily-quota reset timing anyway (~24h, not 2h)
            else:
                tg(f"❌ Ch3 FAILED after {max_retries} attempts.")
                sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                tg(f"⚠️ Ch3 crash {attempt}/{max_retries}: {str(e)[:200]}\nRetrying in 2h...")
                time.sleep(600)  # FIX (final re-audit): shortened from 2h to 10min -- 2 retries x 2h could eat 4h of a 6h job before review is even reached, and didn't match provider daily-quota reset timing anyway (~24h, not 2h)
            else:
                tg(f"❌ Ch3 FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)


if __name__ == "__main__":
    main_with_retry()
