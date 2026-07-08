#!/usr/bin/env python3
"""
DeepDive Empire v11.0 - ULTIMATE ENGINE
=========================================
All v10.0 features + 12 new additions:
[1]  Burned-in captions (edge-tts SubMaker -> .ass -> FFmpeg hardcode)
[2]  YouTube chapters (auto from 7-stage word distribution)
[3]  Playlist engine (auto-create per niche, add every video)
[4]  Checkpoint/resume (save after each stage, retry picks up)
[5]  ElevenLabs TTS (premium voice -> edge-tts fallback)
[6]  Trend intelligence (YouTube search top viral titles this month)
[7]  Branded intro + outro (FFmpeg 2s + 5s)
[8]  Performance tracker (per-niche/voice stats in state.json)
[9]  Dynamic thumbnail text (AI extracts 3-word hook from script reveal)
[10] Niche auto-rotation (3 bad episodes -> swap to best performer)
[11] Subtitle style (white bold 48pt, black border, bottom-center)
[12] Channel About update (latest episode after every upload)
"""

import os, sys, json, re, time, random, datetime, glob, asyncio
import subprocess
from pathlib import Path
import requests

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


def run_title_ctr_gate(title_str, title_scores, topic, niche_name,
                        series_name, episode, ai_fn, min_ctr=6.5):
    if not title_scores:
        return title_str, [(title_str, 5.0)]
    v2_scored = sorted([(t, score_title_v2(t)[0]) for t, _ in title_scores],
                        key=lambda x: x[1], reverse=True)
    best_title, best_score = v2_scored[0]
    if best_score >= min_ctr:
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
                    return new_scored[0][0], new_scored
    except:
        pass
    return best_title, v2_scored


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

def generate_chapter_timestamps(script_clean, total_duration_secs, channel_id):
    if total_duration_secs < 120:
        return ""
    structure = CHAPTER_STRUCTURES.get(channel_id, CHAPTER_STRUCTURES["betrayal_deepdive"])
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
    # FIX: Ch4/Ch5 entries were entirely missing — this was genuinely a
    # 3-channel cross-promo system despite the empire having 5 channels,
    # meaning Ch4/Ch5 got zero organic cross-promotion benefit from Ch1/Ch2,
    # and neither existing channel ever mentioned them. Added now so Ch1/Ch2
    # correctly promote all 5 channels once Ch4/Ch5 are live — safe to add
    # now even though Ch4/Ch5 aren't built yet, since this only changes
    # Ch1/Ch2's own description text.
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

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID","")

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


# ================================================================
# CREDENTIALS
# ================================================================
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY", "")
PEXELS_KEY     = os.environ.get("PEXELS_API_KEY", "")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
COHERE_KEY     = os.environ.get("COHERE_API_KEY", "")
MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY", "")
SAMBANOVA_KEY  = os.environ.get("SAMBANOVA_API_KEY", "")
GEMINI_KEY_2   = os.environ.get("GEMINI_API_KEY_2", "")  # backup Gemini key
YT_CLIENT_ID   = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SEC  = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH     = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID", "")
IS_MAKEUP      = os.environ.get("IS_MAKEUP", "false").lower() == "true"

# ================================================================
# ENDPOINTS
# ================================================================
GEMINI_MODELS  = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]  # 2.0-flash retired by Google June 1 2026
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
SAMBANOVA_URL  = "https://api.sambanova.ai/v1/chat/completions"  # 1000 req/day free
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
YT_DATA_URL    = "https://www.googleapis.com/youtube/v3"
YT_UPLOAD_URL  = "https://www.googleapis.com/upload/youtube/v3"
YT_TOKEN_URL   = "https://oauth2.googleapis.com/token"

# ================================================================
# PATHS
# ================================================================
SCRIPT_DIR = Path(__file__).parent
WORK_DIR   = Path("/tmp/deepdive")
WORK_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = SCRIPT_DIR / "state.json"
CKPT_FILE  = SCRIPT_DIR / "checkpoint.json"  # in repo — survives runner restarts

# ================================================================
# CONFIG
# ================================================================
MIN_WORDS   = 1900
MAX_WORDS   = 2100
MIN_GATE   = 8.5   # attempts 1-8 — the real standard, per explicit graduated-gate spec
FINAL_GATE = 6.9   # absolute last-resort floor, attempt 13 only, never crossed below

# Word targets per stage (sum = MIN_WORDS baseline)
STAGE_WORDS = [100, 200, 250, 400, 200, 650, 200]
STAGE_NAMES = ["The Opening", "Before It Happened", "First Warning Signs",
               "Escalation", "A Moment of Peace", "The Truth Revealed", "What This Means"]

EL_VOICES = {
    "dark_horror":        "29vD33N1CtxCmqQRPOHJ",
    "seduction_dark":     "VR6AewLTigWG4xSOukaG",
    "psychological_trap": "pNInz6obpgDQGcFmaJgB",
    "supernatural_real":  "yoZ06aMxZJJ28mfd3POQ",
    "obsession_dark":     "29vD33N1CtxCmqQRPOHJ",
}

DAY_NICHE = {0: "dark_horror", 1: "seduction_dark", 2: "psychological_trap",
             3: "supernatural_real", 4: "obsession_dark"}

NICHES = [
    {
        "name": "dark_horror", "rpm": 13.00, "series": "Dark Hours",
        "search_query": "dark horror true story documentary",
        "dread_style": "physical dread — something real in shared space without anyone knowing",
        "implication": "the listener has almost certainly been somewhere wrong was happening without ever sensing it",
        "topics": [
            "A family discovered something had been living inside their walls for three years — they found out when the child stopped sleeping",
            "A night-shift nurse documented 14 incidents nobody believed — until the third patient died the same way",
            "A hiker survived something in those mountains that three search teams still cannot explain",
            "A woman received a letter from herself — postmarked the day after she was reported missing",
        ],
        "dread_triggers": [
            "the slow realisation something was wrong long before anyone understood it",
            "the moment the ordinary became permanently broken",
            "the detail that made everything before it feel like a lie",
            "the specific thing seen or heard that cannot be explained away",
        ],
    },
    {
        "name": "seduction_dark", "rpm": 14.00, "series": "The Dark Seduction Files",
        "search_query": "dark psychology manipulation documentary true story",
        "dread_style": "the horror of realising you were chosen, not met — the illusion of connection dismantled",
        "implication": "the listener may have been targeted and interpreted the warning signs as love",
        "topics": [
            "A charismatic figure destroyed 23 lives over 8 years using the exact same 14-step method on every target",
            "A relationship revealed to have been planned in complete detail three years before they ever met",
            "How one person convinced seven strangers to cut off their entire families within a single month",
            "The manipulation blueprint used to drain targets of their finances, identity, and sense of reality",
        ],
        "dread_triggers": [
            "the moment the target realised the relationship had never been real",
            "the discovery of preparation that predated the first meeting by years",
            "the pattern only visible in retrospect after it was too late",
            "the phrase repeated word for word to every single target",
        ],
    },
    {
        "name": "psychological_trap", "rpm": 12.00, "series": "The Trap",
        "search_query": "psychological trap gaslighting documentary investigation",
        "dread_style": "the horror of a system — chaos was actually a designed process",
        "implication": "the listener may currently be inside a trap and interpreting it as a difficult relationship",
        "topics": [
            "A 9-stage system designed to make targets financially, emotionally, and socially dependent",
            "How sustained gaslighting over 18 months made a clinical psychologist unable to trust her own memory",
            "The psychological trap that claimed over 4,000 documented victims across 12 countries",
            "The social media campaign that systematically dismantled a person's entire sense of identity",
        ],
        "dread_triggers": [
            "the stage where the target stops trusting their own memory",
            "the moment the system becomes invisible because the target defends it",
            "the technique that makes leaving feel structurally impossible",
            "the realisation that the confusion itself was being deliberately manufactured",
        ],
    },
    {
        "name": "supernatural_real", "rpm": 11.50, "series": "Evidence Files",
        "search_query": "unexplained paranormal evidence documentary classified",
        "dread_style": "the horror of evidence that cannot be explained — the rational framework collapsing",
        "implication": "the listener has probably had an experience they dismissed that deserves to be reconsidered",
        "topics": [
            "A 2019 incident with 14 unconnected witnesses — classified by three agencies within 72 hours",
            "Every occupant of the building reported the identical auditory experience — confirmed by instruments",
            "A medical case where the patient described events they could not have witnessed from their location",
            "A location where 11 of 300 tourists reported the exact same vision on the same afternoon",
        ],
        "dread_triggers": [
            "the evidence no rational explanation can account for",
            "multiple unconnected witnesses describing the exact same impossible detail",
            "the official response that implied far more than it denied",
            "the recording of something that should not have been physically possible",
        ],
    },
    {
        "name": "obsession_dark", "rpm": 13.00, "series": "Consumed",
        "search_query": "obsession stalking dark documentary true crime",
        "dread_style": "the horror of invisible fixation — a life shaped by someone watching from outside",
        "implication": "the listener may have someone in their life whose interest extends far beyond what it appears",
        "topics": [
            "4,380 consecutive days of obsessive behaviour documented in handwritten detail across 47 notebooks",
            "A stalker who embedded as a trusted friend for three years before a single person noticed",
            "An obsession that removed every relationship, asset, and ambition the subject built over seven years",
            "A person who dedicated a decade to watching someone they had never spoken a word to",
        ],
        "dread_triggers": [
            "the detail revealing how long the observation had actually been happening",
            "the moment the target understood the full scope of what they had been living inside",
            "the action proving the obsession had moved beyond passive watching",
            "the evidence the obsession had quietly shaped the target's life without their knowledge",
        ],
    },
]

VOICES = {
    "dark_horror":        ["en-US-JasonNeural", "en-GB-RyanNeural"],  # DavisNeural unavailable on Actions
    "seduction_dark":     ["en-GB-RyanNeural",  "en-US-AndrewNeural"],
    "psychological_trap": ["en-US-BrianNeural", "en-GB-ThomasNeural"],
    "supernatural_real":  ["en-GB-RyanNeural",  "en-US-JasonNeural"],  # DavisNeural unavailable on Actions
    "obsession_dark":     ["en-US-AndrewNeural","en-GB-RyanNeural"],
}

BG_KEYWORDS = {
    "dark_horror": [
        "dark abandoned hallway",
        "horror dark room shadows",
        "dark empty corridor night",
        "abandoned building interior dark",
        "dark basement shadows",
        "flickering light dark room",
        "dark staircase shadows",
        "rain on dark window night",
    ],
    "seduction_dark": [
        "dark silhouette shadow person",
        "dark room candle shadow",
        "noir dark city rain",
        "dark figure walking night",
        "shadow person dark corridor",
        "dark moody interior light",
        "night city noir rain",
        "dark mysterious shadow",
    ],
    "psychological_trap": [
        "dark maze corridor",
        "dark prison cell",
        "shadow trap dark room",
        "dark concrete corridor",
        "surveillance camera dark",
        "dark interrogation room",
        "locked door dark shadow",
        "dark underground tunnel",
    ],
    "supernatural_real": [
        "dark fog mysterious",
        "abandoned hospital dark",
        "dark empty building night",
        "shadow figure dark hallway",
        "dark paranormal fog",
        "empty dark room shadow",
        "haunted building dark",
        "dark window shadow night",
    ],
    "obsession_dark": [
        "surveillance footage dark",
        "dark window watching night",
        "shadow person watching",
        "dark street night rain",
        "security camera footage dark",
        "dark alley shadow figure",
        "night vision dark footage",
        "dark figure shadow watching",
    ],
}

# Secondary keywords if primary returns nothing useful
BG_KEYWORDS_FALLBACK = {
    "dark_horror":        ["dark room", "night shadows", "dark corridor"],
    "seduction_dark":     ["dark shadow", "night city", "dark figure"],
    "psychological_trap": ["dark corridor", "shadows room", "dark concrete"],
    "supernatural_real":  ["dark fog", "night building", "shadow dark"],
    "obsession_dark":     ["surveillance dark", "shadow watching", "night dark"],
}

# ================================================================
# UTILS
# ================================================================
def log(m): print(m, flush=True)

def tg(m):
    if not TG_TOKEN or not TG_CHAT: return
    for chunk in [m[i:i+4000] for i in range(0, len(m), 4000)]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": chunk, "parse_mode": "HTML"},
                timeout=25)
        except Exception as e:
            log(f"TG: {e}")

def tg_buttons(text):
    """Send Telegram message with ✅ APPROVE / ❌ REJECT / ✏️ CHANGE inline buttons."""
    if not TG_TOKEN or not TG_CHAT: return None
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE",      "callback_data": "approved"},
        {"text": "❌ REJECT",       "callback_data": "rejected"},
        {"text": "✏️ CHANGE TITLE", "callback_data": "change"},
    ]]}
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text,
                  "parse_mode": "HTML", "reply_markup": keyboard}, timeout=25)
        return r.json().get("result", {}).get("message_id")
    except: return None

def tg_answer_callback(callback_id, answer_text="Got it"):
    """Dismiss button spinner after press."""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": answer_text}, timeout=20)
    except: pass

def tg_get_updates(offset=None):
    """Get updates including button callbacks."""
    try:
        params = {"timeout": 25,
                  "allowed_updates": ["message", "callback_query"]}
        if offset: params["offset"] = offset
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
                         params=params, timeout=30)
        return r.json().get("result", [])
    except: return []

def load_state():
    try: return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except: return {}

def save_state(s):
    try: STATE_FILE.write_text(json.dumps(s, indent=2))
    except Exception as e: log(f"State save: {e}")

def get_media_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except: return 0.0

def run_ffmpeg(cmd, timeout=1800, label="ffmpeg"):
    log(f"  [{label}] running...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(f"  [{label}] STDERR: {r.stderr[-2000:]}")
        raise RuntimeError(f"{label} failed (code {r.returncode})")
    log(f"  [{label}] OK")
    return r

def strip_md(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*+([^*\n]+)\*+', r'\1', text)
        text = re.sub(r'_+([^_\n]+)_+', r'\1', text)
        text = re.sub(r'`+[^`]*`+', '', text)
        text = re.sub(r'[#*_`\[\]{}<>\\]', '', text)
    return text.strip()

# ================================================================
# CHECKPOINT / RESUME  [NEW #4]
# ================================================================
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

# ================================================================
# AI CALLERS
# ================================================================
# Known Cerebras model names (they change naming without notice)
CEREBRAS_MODELS = [
    "gpt-oss-120b",        # current Cerebras free-tier default (June 2026)
    "zai-glm-4.7",         # current Cerebras free-tier default (June 2026)
    "llama-3.3-70b",       # kept as fallback — catalog is volatile, may return
    "llama3.3-70b",
    "llama3.1-70b",
    "llama3.1-8b",
]  # NOTE: this constant isn't actually read by call_cerebras() below (it has its own
   # inline _models list, now fixed to match). Kept in sync here for anyone reading top-down.

def call_cerebras(prompt, tokens=8000):
    """
    Cerebras Cloud — 1M tokens/day free tier. PRIMARY provider.
    URL + models hardcoded — never relies on module scope.
    401 = bad key. 404 = wrong model name. 429 = rate limit.
    """
    if not CEREBRAS_KEY:
        log("  Cerebras: CEREBRAS_API_KEY not in GitHub Secrets — ADD IT")
        return None
    _url    = "https://api.cerebras.ai/v1/chat/completions"
    _models = ["gpt-oss-120b", "zai-glm-4.7", "llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]  # Cerebras free-tier catalog narrowed to gpt-oss-120b/zai-glm-4.7 as of June 2026 — old llama names kept as fallback in case they return
    for model in _models:
        try:
            r = requests.post(_url,
                headers={"Authorization": f"Bearer {CEREBRAS_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_completion_tokens": min(tokens, 12000),
                      "temperature": 0.88},
                timeout=120)
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"  OK Cerebras ({model})")
                    return t
            elif r.status_code == 401:
                log("  Cerebras 401 UNAUTHORIZED — API key is WRONG or EXPIRED.")
                log("  Fix: go to https://cloud.cerebras.ai/ → API Keys → create new key")
                log("  Then update CEREBRAS_API_KEY in GitHub Secrets.")
                return None  # Wrong key — no point trying other model names
            elif r.status_code == 404:
                log(f"  Cerebras {model}: 404 (wrong model name, trying next)")
                continue
            else:
                log(f"  Cerebras {model}: {r.status_code} | {r.text[:150]}")
                break
        except Exception as e:
            log(f"  Cerebras {model}: {e}")
            break
    return None

def call_groq(prompt, tokens=8000):
    if not GROQ_KEY: return None
    # Groq announced deprecation of llama-3.3-70b-versatile on June 17 2026.
    # Try the recommended replacements first, keep the old name as last-resort.
    for model in ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88, "max_tokens": min(tokens, 4800)}, timeout=90)  # Groq TPM limit = 6000
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100: log(f"OK Groq ({model})"); return t
            elif r.status_code in (400, 404):
                log(f"Groq {model}: {r.status_code} (model gone) — trying next"); continue
            else:
                log(f"Groq {model}: {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"Groq {model}: {e}")
    return None

def call_gemini(prompt, tokens=8000):
    """
    Tries primary GEMINI_API_KEY first.
    If 429 quota exhausted, tries backup GEMINI_API_KEY_2.
    Create a second Google Cloud project for a free second key — doubles quota.
    """
    keys = [k for k in [GEMINI_KEY, GEMINI_KEY_2] if k]
    if not keys:
        log("  Gemini: GEMINI_API_KEY not set")
        return None
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    for key_idx, active_key in enumerate(keys):
        key_label = "primary" if key_idx == 0 else "backup"
        quota_hit = False
        for model in GEMINI_MODELS:
            try:
                url = f"{base}/{model}:generateContent?key={active_key}"
                r = requests.post(url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.88, "maxOutputTokens": min(tokens, 12000)},
                          "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]},
                    timeout=90)
                if r.status_code == 200:
                    c = r.json().get("candidates", [])
                    if c:
                        t = c[0]["content"]["parts"][0]["text"]
                        if t and len(t.strip()) > 100:
                            log(f"  OK Gemini ({model})")
                            return t
                elif r.status_code == 429:
                    log(f"  Gemini ({key_label}) quota exhausted — resets midnight PT")
                    if key_idx == 0 and GEMINI_KEY_2:
                        log("  Trying backup Gemini key (GEMINI_API_KEY_2)...")
                    quota_hit = True
                    break  # break model loop, try next key
                elif r.status_code in [400, 404]:
                    log(f"  Gemini {model}: {r.status_code} — trying next model")
                    continue
                else:
                    log(f"  Gemini {model}: {r.status_code} | {r.text[:200]}")
            except Exception as e:
                log(f"  Gemini {model}: {e}")
        if not quota_hit:
            break  # succeeded or non-quota failure — don't try backup key
    return None

# Free models on OpenRouter — try in order until one responds
OR_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",    # best quality
    "mistralai/mistral-7b-instruct:free",         # reliable fallback
    "google/gemma-2-9b-it:free",                  # Google fallback
    "microsoft/phi-3-mini-128k-instruct:free",    # Microsoft fallback
    "huggingfaceh4/zephyr-7b-beta:free",          # last resort
]

def call_openrouter(prompt, tokens=8000):
    if not OPENROUTER_KEY:
        log("  OpenRouter: OPENROUTER_API_KEY not set — skipping")
        return None
    for model in OR_FREE_MODELS:
        try:
            r = requests.post(OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://github.com/BetrayalDeepDive/betrayal-bot"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": min(tokens, 4000), "temperature": 0.88}, timeout=90)  # OR free models
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                if t and len(t.strip()) > 100:
                    log(f"OK OpenRouter ({model.split('/')[-1]})")
                    return t
            else:
                log(f"OpenRouter {model.split('/')[-1]}: {r.status_code} | {r.text[:200]}")
                if r.status_code == 429: time.sleep(3)
        except Exception as e:
            log(f"OpenRouter {model}: {e}")
    return None


# ================================================================
# COHERE — free tier, 20 RPM, strong long-form writing
# ================================================================
COHERE_URL = "https://api.cohere.com/v2/chat"

def call_cohere(prompt, tokens=8000):
    """Cohere Command R+ free tier — 20 RPM, excellent for structured long-form scripts."""
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY not set — skipping")
        return None
    try:
        r = requests.post(COHERE_URL,
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "command-r-08-2024",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000),
                  "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("message", {}).get("content", [{}])
            text = t[0].get("text", "") if t else ""
            if text and len(text.strip()) > 100:
                log("OK Cohere")
                return text
        else:
            log(f"  Cohere {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log(f"  Cohere: {e}")
    return None


# ================================================================
# MISTRAL AI — free tier via La Plateforme, strong creative writing
# ================================================================
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def call_sambanova(prompt, tokens=8000):
    """
    SambaNova Cloud — free tier, no daily quota wall, llama-3.3-70b.
    Sign up free at https://cloud.sambanova.ai — takes 2 minutes.
    Add SAMBANOVA_API_KEY to GitHub Secrets.
    1,000 requests/day free. Fast inference.
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
                log("  SambaNova 401 — API key invalid. Check SAMBANOVA_API_KEY secret.")
                return None
            elif r.status_code == 429:
                log("  SambaNova 429 — daily limit reached")
                return None
            else:
                log(f"  SambaNova {r.status_code}: {r.text[:120]}")
        except Exception as e:
            log(f"  SambaNova: {e}")
    return None

def call_mistral(prompt, tokens=8000):
    """Mistral AI free tier — reliable European servers, strong at structured writing."""
    if not MISTRAL_KEY:
        log("  Mistral: MISTRAL_API_KEY not set — skipping")
        return None
    try:
        r = requests.post(MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "mistral-small-latest",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": min(tokens, 4000),
                  "temperature": 0.88},
            timeout=120)
        if r.status_code == 200:
            t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if t and len(t.strip()) > 100:
                log("OK Mistral")
                return t
        else:
            log(f"  Mistral {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log(f"  Mistral: {e}")
    return None

def ai_generate(prompt, tokens=8000):
    """
    Provider order: Cerebras → Gemini → Groq → OpenRouter → Cohere → Mistral
    6 layers of fallback. Sleep 10s between failures.
    """
    # Provider order: primary free → backup free → quota-based → fallbacks
    # SambaNova is between Cerebras and Gemini — same quality, no quota wall
    providers = [call_cerebras, call_sambanova, call_gemini,
                 call_groq, call_openrouter, call_cohere, call_mistral]
    for i, fn in enumerate(providers):
        r = fn(prompt, tokens)
        if r: return r
        if i < len(providers) - 1:
            log(f"  Waiting 10s before next provider...")
            time.sleep(10)
    return None

# ================================================================
# TREND INTELLIGENCE  [NEW #6]
# ================================================================
def fetch_trending_titles(niche, token):
    try:
        published_after = (datetime.datetime.utcnow() -
                           datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = requests.get(f"{YT_DATA_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "q": niche["search_query"], "type": "video",
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

    result = ai_generate(prompt, tokens=300)
    if result:
        t = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
        if len(t) > 40:
            log(f"  Viral angle: {t[:90]}")
            return t
    return None


def generate_trend_informed_topic(niche, trending_titles):
    """
    Pick a topic informed by trends WITHOUT spending an AI token call.
    If trending titles exist, we use a curated topic from the niche list
    (they are already psychologically optimised) and note the trend angle.
    The trend titles are instead passed to the script prompt to influence
    tone and hook — not wasted on a separate AI summary call.
    """
    if not trending_titles:
        return random.choice(niche["topics"])
    # Use a niche topic but log the trend context for the script prompt
    topic = random.choice(niche["topics"])
    log(f"  Trend-informed topic selected (no AI call): {topic[:80]}")
    return topic

# ================================================================
# PERFORMANCE TRACKER  [NEW #8, #10]
# ================================================================
def track_episode(state, niche_name, score, voice, episode):
    perf = state.get("performance", {})
    n    = perf.get(niche_name, {"scores": [], "streak_below": 0})
    n["scores"]       = (n["scores"] + [score])[-20:]
    n["streak_below"] = (n["streak_below"] + 1) if score < 7.5 else 0
    n["last_episode"] = episode
    perf[niche_name]  = n
    v = perf.get(f"voice_{voice}", {"scores": []})
    v["scores"] = (v["scores"] + [score])[-20:]
    perf[f"voice_{voice}"] = v
    state["performance"] = perf
    return state

def pick_best_niche(state, scheduled_name):
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
        avg    = sum(scores) / len(scores) if scores else 7.5
        if avg > best_avg:
            best_avg  = avg
            best_name = n["name"]
    log(f"  Swapped to: {best_name} (avg {best_avg:.1f})")
    return best_name

# ================================================================
# SCORE
# ================================================================
def score_result(r):
    if not r: return 0.0, []
    s = 5.0
    w = r.get("words", 0)
    if w >= MIN_WORDS: s += 2.8
    elif w >= 1600:    s += 0.8
    else:              s -= 2.0
    v = r.get("violations", 0)
    if v == 0:   s += 2.2
    elif v <= 2: s += 0.8
    else:        s -= 1.5
    # v12: retention hook validation
    script = r.get("script", "")
    if script:
        penalty, hook_issues = _validate_retention_hooks_ch1(script)
        s += penalty
    return min(round(s, 1), 10.0), []


def _validate_retention_hooks_ch1(script_clean):
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
Niche style: {niche["dread_style"]}
{trend_hint}

Each cold open must:
- Be 80-120 words
- Start with the single most disturbing fact — mid-action, no preamble
- Never say "welcome back", "today", "in this video"
- Use a specific date, time, or number in the first sentence
- Create a question the listener cannot stop thinking about

Format your response EXACTLY as:
VARIANT_1:
[cold open text here]
VARIANT_2:
[cold open text here]
VARIANT_3:
[cold open text here]

Write all 3 now. Zero markdown."""

    raw = ai_generate(prompt, tokens=1200)
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

def search_real_cases(niche_name, topic_hint):
    """
    Search Google News RSS and Reddit for real documented cases
    matching this niche. Returns list of real case summaries.
    No API key required for either source.
    """
    import xml.etree.ElementTree as ET
    import urllib.parse

    # Build niche-specific search queries
    niche_queries = {
        "dark_horror":        f"{topic_hint.split()[0]} horror true story documented",
        "seduction_dark":     f"manipulation relationship psychology documented case",
        "psychological_trap": f"gaslighting psychological abuse documented case",
        "supernatural_real":  f"unexplained phenomenon documented evidence case",
        "obsession_dark":     f"stalking obsession documented court case",
    }
    query = niche_queries.get(niche_name, topic_hint.split()[0] + " documented case")
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
                if title is not None and title.text:
                    cases.append({
                        "source":  "news",
                        "title":   title.text[:120],
                        "summary": desc.text[:200] if desc is not None and desc.text else "",
                        "date":    pub.text[:20] if pub is not None and pub.text else "",
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
                if title and len(title) > 20:
                    cases.append({
                        "source":  "reddit",
                        "title":   title[:120],
                        "summary": d.get("selftext", "")[:200],
                        "date":    "",
                        "score":   d.get("score", 0),
                    })
            log(f"  Real cases from Reddit: {len([c for c in cases if c['source']=='reddit'])}")
    except Exception as e:
        log(f"  Reddit (non-fatal): {e}")

    return cases[:6]  # top 6 real cases


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

    result = ai_generate(prompt, tokens=300)
    if result:
        brief = result.strip()[:400]
        if len(brief) > 50:
            log(f"  Real case brief: {brief[:80]}...")
            return brief
    return ""


def get_research_context(niche_name, topic):
    """
    Main research entry point. Returns a research context string
    to inject into the script prompt before generation.
    """
    log("  Researching real documented cases...")
    cases = search_real_cases(niche_name, topic)
    if not cases:
        log("  No real cases found — proceeding with AI-generated topic")
        return ""
    brief = extract_real_case_facts(cases, niche_name)
    if not brief:
        return ""
    return (
        f"REAL DOCUMENTED CASE RESEARCH (use these real facts in your script):\n"
        f"{brief}\n"
        f"IMPORTANT: Use these real facts as the foundation. Do not invent details. "
        f"Build the narrative around documented reality."
    )

def build_script_prompt(niche, topic, episode, attempt,
                        trending_titles=None, research_context=""):
    """
    v2 script prompt — 7-stage architecture with stage-specific
    word targets, trigger placements, and forbidden phrases per stage.
    """
    intensities = [
        "precisely observed, factual, and quietly disturbing",
        "forensically detailed — each fact more specific than the last",
        "at maximum specificity — every sentence contains one undeniable concrete detail",
    ]
    intensity = intensities[min(attempt - 1, 2)]

    trend_block = ""
    if trending_titles:
        trend_block = "\nWHAT IS WORKING IN THIS NICHE RIGHT NOW:\n"
        trend_block += "\n".join(f"  '{t}'" for t in trending_titles[:4])
        trend_block += "\nMatch their emotional register. Never copy. Outperform them.\n"

    pattern_ctx  = load_pattern_memory(load_state())
    strategy_ctx = load_weekly_strategy()
    combined     = "\n".join(filter(None, [pattern_ctx, strategy_ctx]))
    pattern_block = f"\nPATTERN MEMORY (scored 8+/10 previously):\n{combined}\n" if combined else ""

    research_block = f"\nRESEARCH CONTEXT:\n{research_context}\n" if research_context else ""

    stage_targets = {
        1: 120,   # Cold open — short and brutal
        2: 200,   # The before
        3: 280,   # First signals
        4: 480,   # Escalation — most evidence
        5: 150,   # False resolution
        6: 520,   # Real reveal — climax
        7: 150,   # Implication + CTA
    }

    return f"""Write a {intensity} dark investigative documentary narration.

TOPIC: {topic}
SERIES: {niche["series"]} — Episode {episode}
{trend_block}{pattern_block}{research_block}

TOTAL WORD REQUIREMENT: {MIN_WORDS} to {MAX_WORDS} words.
Each stage must hit its target. If any stage runs short, expand with more specific evidence.

SEVEN-STAGE STRUCTURE — write continuously, no labels, no headers:

SIGNATURE OPENING (brand consistency — real successful channels have this,
generic AI content doesn't): begin the cold open with a recognizable rhythm
specific to this series — the exact words can vary per episode, but the
STRUCTURE should feel unmistakably like {niche["series"]} within the first
sentence, not interchangeable with any other true-crime channel.

CASE SELECTION: prefer a genuinely underreported or lesser-known angle over
the most famous/oversaturated version of this story, if the topic allows it.
This is both a differentiation advantage (viewers haven't seen this take
everywhere already) and a real protection against looking like mass-produced
generic content — original research reads as authored, not templated.

CENTRAL FRACTURE (channel strength, not optional): every script must revolve
around ONE central relationship fracture — a specific betrayal between two
specific people — not a generic "something creepy happened." Name the
relationship explicitly (sister/sister, patient/doctor, mother/son) and keep
the entire narrative anchored to that one fracture rather than drifting into
a vague atmosphere piece.

FICTION LABELING (non-negotiable, real policy-safety requirement): if any
part of this story is dramatized, composited from multiple cases, or not
independently verifiable as reported fact, the script MUST include a clear,
natural spoken acknowledgment of this — e.g. "names and details in this
account have been changed" or "this account draws on patterns from multiple
documented cases." This is not a disclaimer to bury — say it plainly,
early, without breaking the tone. Never present invented specifics as
verified fact.

RETENTION CHECKPOINTS (precise timing, not just word count — this is where
most viewers actually drop off if nothing happens):
- At approximately 15-20 seconds into the Cold Open (roughly the 35-45 word
  mark, not the very first sentence): introduce one SPECIFIC new piece of
  information that was NOT already promised in sentences 1-3. This is the
  second hook — without it, attention drops right here regardless of how
  strong the opening 3 sentences were.
- At approximately 40-45 seconds in (end of Stage 1 / start of Stage 2):
  set up a payoff that requires continuing to watch to resolve — a question,
  an incomplete number, a named person whose role isn't yet explained.

STAGE 1 — COLD OPEN ({stage_targets[1]} words)
Sentence 1 must contain an exact number, date, or duration.
Sentence 2 places the listener somewhere recognisable.
Sentence 3 opens a loop the script must close.
Forbidden: "welcome back", "today we", "in this video", "join me"
Trigger: DETAIL (sentence 1), PROXIMITY (sentence 2), open loop (sentence 3)

STAGE 2 — THE BEFORE ({stage_targets[2]} words)
Establish the subject as completely ordinary. Specific routine, specific place.
Final sentence: signal something is about to break — without stating it.
Forbidden: "little did they know", "but little did", "unbeknownst to them"
Trigger: NORMALITY (sentences 1-3), PROXIMITY (sentences 4-6)

STAGE 3 — FIRST SIGNALS ({stage_targets[3]} words)
Small wrong things. Individually explainable. One per sentence. Build accumulation.
Start with the smallest possible wrong detail.
Forbidden: "suddenly", "out of nowhere", "without warning"
Trigger: INVISIBILITY (s1), DURATION (s3), SCALE (s5), INSTITUTIONAL (s7)

STAGE 4 — ESCALATION ({stage_targets[4]} words)
Open with one short sentence that reframes Stage 3 entirely.
Signs become undeniable. Short sentences, then one longer one. Specific evidence.
Forbidden: passive voice, vague quantities ("many", "several", "some")
Trigger: SCALE (s1), COMPETENCE (s4), INSTITUTIONAL (s7), COMPLICITY (s10)

STAGE 5 — FALSE RESOLUTION ({stage_targets[5]} words)
Normalcy briefly returns. Specific timeframe. Listener exhales.
Final sentence: subtly, quietly wrong — not dramatic, not announced.
Forbidden: "but it wasn't over", "however", "little did they know", "or so they thought"
Trigger: NORMALITY (s1-3), REPETITION (s4), quiet wrongness (final)

STAGE 6 — THE REAL REVEAL ({stage_targets[6]} words)
One short sentence destroys the false resolution. Then one idea per short paragraph.
Most disturbing section. Be thorough. Let each paragraph land before moving on.
Forbidden: "in conclusion", "to summarise", "as we can see"
Trigger per paragraph: REVERSAL, DETAIL, COST, SCALE, DURATION, INSTITUTIONAL, REPETITION

STAGE 7 — IMPLICATION AND CTA ({stage_targets[7]} words)
Imply — never state — that this pattern extends beyond this case.
Subscribe CTA at the emotional peak, not as afterthought.
Forbidden: "subscribe and like", "hit the bell", "don't forget to"
Trigger: REPETITION (s1), PROXIMITY (s3), subscribe CTA (final 2 sentences)

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

RULES:
1. Maximum 13 words per sentence. Count them.
2. Zero markdown — no symbols, headers, bullets, asterisks.
3. Zero AI filler — no "moreover", "furthermore", "interestingly", "it is worth noting".
4. Every number must be specific: not "many" but "forty-seven".
5. Every date must be specific: not "years ago" but "a Thursday in March 2019".
6. Every location must be specific: not "a small town" but "a city of 340,000 people".
7. Start immediately. No preamble. No introduction.
8. Write one continuous narrative — do not number or label stages.

Write the complete script now:"""


def generate_script_content(niche, topic, episode, attempt,
                             trending_titles=None, research_context=""):
    """
    v2 script generation:
    1. Generate full script with stage-structured v2 prompt
    2. Score each of 7 stages independently
    3. Rewrite only the 2 worst-scoring stages with targeted instructions
    4. Inject subscribe CTAs at 30/60/80% marks
    """
    # Step 1: Generate research anchors to prevent vague AI output
    anchors = {}
    try:
        anchor_prompt = (
            f"Generate specific realistic research anchors for a documentary about: {topic}\n"
            f"Return ONLY valid JSON (no backticks):\n"
            f'{{"duration":"how long before discovery e.g. 4380 days",'
            f'"people_count":"number affected e.g. 847 confirmed cases",'
            f'"first_signal_date":"e.g. a Tuesday in March 2011",'
            f'"discovery_date":"e.g. October 14 2019",'
            f'"location":"specific-feeling place e.g. a city of 340000 people",'
            f'"key_number":"most disturbing specific number",'
            f'"cost":"what was permanently lost e.g. $2.4 million over eleven years"}}'
        )
        anchor_raw = ai_generate(anchor_prompt, tokens=300)
        if anchor_raw:
            anchor_raw = re.sub(r"```json|```", "", anchor_raw).strip()
            m = re.search(r"\{[\s\S]*?\}", anchor_raw)
            if m:
                anchors = json.loads(m.group())
                log(f"  Research anchors loaded: {len(anchors)} fields")
    except Exception as e:
        log(f"  Anchors (non-fatal): {e}")

    # Inject anchors into research_context
    if anchors:
        anchor_lines = "\n".join(f"  {k}: {v}" for k, v in anchors.items() if v)
        research_context = f"USE THESE SPECIFIC DETAILS:\n{anchor_lines}\n{research_context}"

    # FIX: generate_best_cold_open existed fully built — generates 3 real
    # variants and scores each on hook strength (specificity, sentence
    # length, dread keywords, avoiding weak openers) — but was never
    # actually called anywhere. The cold open is the single most
    # retention-critical 30 seconds of the whole video, and it was being
    # left entirely to whatever the main script prompt produced in one
    # shot, with no A/B scoring at all.
    try:
        best_cold_open = generate_best_cold_open(niche, topic, trending_titles)
        if best_cold_open:
            research_context = (f"MANDATORY COLD OPEN — use this exact opening, scored as the "
                                f"strongest of 3 real variants, then continue the script from there:\n"
                                f"{best_cold_open}\n\n{research_context}")
    except Exception as e:
        log(f"  Cold open scoring (non-fatal): {e}")

    # Step 2: Generate script
    raw = ai_generate(build_script_prompt(
        niche, topic, episode, attempt, trending_titles, research_context), tokens=8000)
    if raw:
        for _exp in range(2):
            raw_wc = len(raw.split())
            if raw_wc >= MIN_WORDS or raw_wc > MAX_WORDS: break
            log(f"  Script {raw_wc}w short — expanding...")
            try:
                ep = (f"Script is {raw_wc}w, needs {MIN_WORDS}."
                      f" Add {MIN_WORDS - raw_wc} more words to Stage 4 and Stage 6."
                      f" Zero markdown. Max 13 words per sentence."
                      f" Return the COMPLETE script with additions:\n\n"
                      + raw[:4000])
                raw2 = ai_generate(ep, tokens=8000)
                if raw2 and len(raw2.split()) > raw_wc:
                    raw = raw2
                    # Hard truncate raw to MAX_WORDS after expansion
                    if len(raw.split()) > MAX_WORDS:
                        raw = " ".join(raw.split()[:MAX_WORDS])
                    log(f"  Expanded to {len(raw.split())}w")
            except Exception as _e:
                log(f"  Expansion (non-fatal): {_e}"); break
    if not raw:
        return None
    script     = strip_md(strip_md(raw))
    wc         = len(script.split())
    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
    log(f"  Script: {wc}w | {violations} violations")

    # Step 3: Expand if short
    if wc < MIN_WORDS:
        deficit = MIN_WORDS - wc
        log(f"  Short by {deficit}w — expanding stages 4 and 6...")
        exp = (
            f"This documentary script is {wc} words. It needs {MIN_WORDS} minimum. "
            f"Expand the Escalation section and the Reveal section only. "
            f"Add specific evidence, exact numbers, exact dates, witness reactions. "
            f"Max 13 words per sentence. Zero markdown. "
            f"Return the COMPLETE expanded script.\n\nSCRIPT:\n{script}"
        )
        raw2 = ai_generate(exp, tokens=8000)
        if raw2:
            s2 = strip_md(strip_md(raw2))
            if len(s2.split()) > wc:
                script     = s2
                wc         = len(script.split())
                violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
                # Hard truncate to MAX_WORDS
                if wc > MAX_WORDS:
                    script = " ".join(script.split()[:MAX_WORDS])
                    wc = len(script.split())
                log(f"  Expanded: {wc}w")

    # Step 4: Stage-level scoring + targeted rewrite of 2 worst stages
    if wc >= MIN_WORDS:
        try:
            # Split script proportionally into 7 stages
            words    = script.split()
            total    = len(words)
            targets  = [110, 210, 260, 420, 170, 680, 190]
            total_t  = sum(targets)
            stage_texts = []
            pos = 0
            for i, tgt in enumerate(targets):
                share = tgt / total_t
                end   = pos + int(total * share) if i < 6 else total
                stage_texts.append(" ".join(words[pos:end]))
                pos   = end

            # Score each stage
            stage_names   = ["COLD OPEN","THE BEFORE","FIRST SIGNALS",
                             "ESCALATION","FALSE RESOLUTION","THE REVEAL","IMPLICATION"]
            hook_signals  = ["subscribe","next","what happens","revealed","about to",
                             "this changes","thirty seconds","coming up","stay"]
            forbidden_per = [
                ["welcome back","today we","in this video","join me"],
                ["little did they know","unbeknownst"],
                ["suddenly","out of nowhere","without warning"],
                [],
                ["but it wasn't over","however","or so they thought"],
                ["in conclusion","to summarise","as we can see"],
                ["subscribe and like","hit the bell","don't forget"],
            ]

            stage_scores = []
            # Real specificity/craveability signals — the rubric previously only
            # checked word-count adherence and forbidden-phrase absence, which
            # rewards STRUCTURE but never actually measures whether the script
            # achieved genuine specificity or used its required craveability
            # triggers. A script could hit every structural target and still
            # read flat. This closes that gap with real, measurable checks.
            vague_quantity_words = ["many", "several", "some", "numerous", "various",
                                     "a lot of", "countless", "multiple"]
            vague_time_words = ["years ago", "some time later", "at some point",
                                 "a while later", "eventually", "in time"]
            specificity_signals = [r'\b\d+\b', r'\$\d', r'\b\d{4}\b']  # numbers, money, years
            craveability_signals = ["still", "today", "confirmed", "documented",
                                     "records show", "never released", "still running",
                                     "still active", "remains", "to this day"]

            for i, (stext, sname, starget, sforbidden) in enumerate(
                    zip(stage_texts, stage_names, targets, forbidden_per)):
                sc    = 5.0
                sw    = len(stext.split())
                ratio = sw / max(starget, 1)
                if 0.85 <= ratio <= 1.15:   sc += 2.0
                elif 0.70 <= ratio <= 1.30: sc += 0.8
                else:                       sc -= 1.5
                found_forbidden = [f for f in sforbidden if f in stext.lower()]
                sc -= len(found_forbidden) * 0.8
                sents = [s for s in re.split(r"(?<=[.!?])\s+", stext) if s.strip()]
                long  = [s for s in sents if len(s.split()) > 13]
                if len(long) / max(len(sents), 1) > 0.2:
                    sc -= 0.8
                if i in [0, 6]:  # cold open and CTA — check for hooks
                    if not any(h in stext.lower() for h in hook_signals[:3]):
                        sc -= 0.5
                ai_phrases = ["moreover","furthermore","it is worth noting","in conclusion"]
                sc -= sum(0.4 for p in ai_phrases if p in stext.lower())

                # Real specificity check — reward actual numbers/dates present,
                # penalize the vague-quantity words the prompt explicitly forbids
                # but nothing was previously verifying were actually absent.
                stext_lower = stext.lower()
                num_hits = sum(1 for pat in specificity_signals if re.search(pat, stext))
                if num_hits >= 2: sc += 1.0
                elif num_hits == 0: sc -= 1.0
                vague_q_found = sum(1 for w in vague_quantity_words if w in stext_lower)
                sc -= vague_q_found * 0.6
                vague_t_found = sum(1 for w in vague_time_words if w in stext_lower)
                sc -= vague_t_found * 0.6

                # Real craveability check — reward language that signals the
                # trigger types actually landed (present-tense/still-running
                # framing, documented/confirmed specificity), not just assumed
                # from following the structural instructions.
                crave_hits = sum(1 for w in craveability_signals if w in stext_lower)
                if crave_hits >= 1: sc += 0.8

                stage_scores.append(round(min(max(sc, 0), 10), 1))

            score_str = " | ".join(f"{n[:8]}:{s}" for n,s in zip(stage_names, stage_scores))
            log(f"  Stage scores: {score_str}")

            # Rewrite the 2 worst stages
            worst_two = sorted(range(len(stage_scores)), key=lambda i: stage_scores[i])[:2]
            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                sdef_name   = stage_names[idx]
                sdef_target = targets[idx]
                sdef_forb   = forbidden_per[idx]
                forb_str    = ", ".join(f'"{f}"' for f in sdef_forb) if sdef_forb else "none"
                rewrite_p   = (
                    f"Rewrite ONLY this single script stage. Return ONLY the rewritten stage.\n\n"
                    f"STAGE: {sdef_name} (target: {sdef_target} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"CURRENT SCORE: {stage_scores[idx]}/10\n"
                    f"PROBLEMS: sentences over 13 words, vague quantities, forbidden phrases\n"
                    f"FORBIDDEN: {forb_str}\n\n"
                    f"RULES:\n"
                    f"- Maximum 13 words per sentence. Every sentence.\n"
                    f"- Every number must be specific (not 'many' but '47').\n"
                    f"- Zero markdown. Zero AI filler phrases.\n"
                    f"- More visceral and specific than the original.\n"
                    f"- Target: {sdef_target} words (±15% acceptable).\n\n"
                    f"ORIGINAL STAGE:\n{stage_texts[idx]}\n\n"
                    f"Write the improved version now:"
                )
                new_stage = ai_generate(rewrite_p, tokens=2000)
                if new_stage:
                    new_stage = strip_md(new_stage)
                    if len(new_stage.split()) > 30:
                        script = script.replace(stage_texts[idx], new_stage, 1)
                        log(f"  Stage {sdef_name} rewritten ({stage_scores[idx]}/10 → improved)")

            wc         = len(script.split())
            violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
            log(f"  After targeted rewrite: {wc}w | {violations} violations")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # FIX: fiction-labeling was only a prompt INSTRUCTION with zero code-level
    # verification — meaning it was hoped-for, not guaranteed, every single
    # run. Since this is a real policy-safety requirement (not a creative
    # nicety), this follows the exact same reliable "guard" pattern already
    # used for the subscribe CTA below: check for it, and if the AI didn't
    # include it, force it in rather than trust compliance.
    fiction_signals = ["names and details", "names have been changed", "composite",
                        "dramatiz", "reconstruct", "multiple documented cases",
                        "account draws on", "identifying details"]
    if not any(sig in script.lower() for sig in fiction_signals):
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
        disclosure = " Some names and identifying details in this account have been changed."
        if len(sentences) > 1:
            sentences[0] = sentences[0].rstrip() + disclosure
            script = " ".join(sentences)
        else:
            # FIX (found in Pass 3 re-check): if the script has only 0 or 1
            # "sentences" (e.g. missing end punctuation, or some upstream
            # issue produced a single run-on blob), the sentence-based
            # insertion above silently did nothing — no disclosure, no log,
            # no fallback. Since this guard exists to GUARANTEE the
            # disclosure appears, not just usually, it now always adds it
            # regardless of how the script is shaped.
            script = script.rstrip() + disclosure
        wc = len(script.split())
        log("  Fiction-labeling: AI didn't include it — force-inserted (guaranteed, not hoped-for)")

    # Step 5: CTA injection
    if len(script.split()) >= 400:
        script = _inject_ctas_ch1(script, niche["name"])
        # Subscribe CTA guard
        if "subscribe" not in " ".join(script.split()[-60:]).lower():
            script += " Subscribe to this channel for more documented cases."
        script_clean = script
        wc     = len(script.split())
        log(f"  CTAs injected — final: {wc}w")

    return {"script": script, "words": wc, "violations": violations, "stage_texts": stage_texts}


def _inject_ctas_ch1(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30%/60%/80% marks for Ch1 (BetrayalDeepDive).
    Uses sentence boundary detection so CTAs never split mid-sentence.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    cta_pool = {
        "dark_horror": {
            "30pct": ["Subscribe to BetrayalDeepDive. The worst part is thirty seconds away.",
                      "If what you just heard disturbed you, subscribe. There is more."],
            "60pct": ["Subscribe now. What comes next is why this channel exists.",
                      "Subscribe to BetrayalDeepDive before the next revelation."],
            "80pct": ["Subscribe. New investigation every weekday.",
                      "Subscribe to BetrayalDeepDive if you want the rest of them."],
        },
        "seduction_dark": {
            "30pct": ["Subscribe. The psychology behind this gets darker from here.",
                      "Subscribe to BetrayalDeepDive. The pattern you are seeing repeats."],
            "60pct": ["Subscribe before the mechanism is fully revealed.",
                      "Subscribe to BetrayalDeepDive. The next section changes the whole story."],
            "80pct": ["Subscribe. The final layer is thirty seconds away.",
                      "Subscribe to BetrayalDeepDive — new case every weekday."],
        },
        "psychological_trap": {
            "30pct": ["Subscribe. The trap is about to be fully visible.",
                      "Subscribe to BetrayalDeepDive. Every step was deliberate."],
            "60pct": ["Subscribe before the final mechanism is shown.",
                      "Subscribe to BetrayalDeepDive. What is documented next changes everything."],
            "80pct": ["Subscribe. Every weekday. A new case that redefines what you thought you knew.",
                      "Subscribe to BetrayalDeepDive if you want the forty-seven other cases."],
        },
        "supernatural_real": {
            "30pct": ["Subscribe. The documented evidence arrives in thirty seconds.",
                      "Subscribe to BetrayalDeepDive. The explanation is not what you expect."],
            "60pct": ["Subscribe before the final evidence is shown.",
                      "Subscribe to BetrayalDeepDive. This is the part that has no rational explanation."],
            "80pct": ["Subscribe. What was documented here has never been explained.",
                      "Subscribe to BetrayalDeepDive — new investigation every weekday."],
        },
        "obsession_dark": {
            "30pct": ["Subscribe. The escalation documented next is why this case is different.",
                      "Subscribe to BetrayalDeepDive. Every detail here was deliberate."],
            "60pct": ["Subscribe before the final revelation.",
                      "Subscribe to BetrayalDeepDive. The next sixty seconds reframe everything."],
            "80pct": ["Subscribe. New case every weekday. You will not regret it.",
                      "Subscribe to BetrayalDeepDive if you want to understand what drove this."],
        },
    }
    pool  = cta_pool.get(niche_name, cta_pool["dark_horror"])
    seed  = abs(hash(script_clean[:80])) % 2
    c30   = pool["30pct"][seed]
    c60   = pool["60pct"][seed]
    c80   = pool["80pct"][seed]

    def nearest_boundary(words, target, window=25):
        for delta in range(window):
            for d in [1, -1]:
                idx = target + delta * d
                if 0 <= idx < len(words):
                    if words[idx].rstrip().endswith((".", "?", "!")):
                        return idx + 1
        return target

    b80 = nearest_boundary(words, int(total * 0.80))
    b60 = nearest_boundary(words, int(total * 0.60))
    b30 = nearest_boundary(words, int(total * 0.30))

    w = words[:]
    w.insert(b80, f"\n\n{c80}\n\n")
    w.insert(b60, f"\n\n{c60}\n\n")
    w.insert(b30, f"\n\n{c30}\n\n")
    return re.sub(r'\n{3,}', '\n\n', " ".join(w)).strip()

# ================================================================
# TITLE + CHAPTERS  [NEW #2]
# ================================================================
def generate_titles(niche, topic, episode, state=None, trending_titles=None):
    # FIX: the prompt asked the AI to "rotate" between dread and sympathy
    # framing, but nothing tracked which register was actually used last
    # time — dread-language titles tend to score slightly higher on the
    # hook-word scorer, so without real enforcement this could quietly
    # drift back to all-dread despite the instruction. Track it in state
    # and explicitly request the OPPOSITE register each time.
    last_register = (state or {}).get("last_title_register", "dread")
    target_register = "sympathy" if last_register == "dread" else "dread"
    register_instruction = (
        "Focus on the SYMPATHY/WOEFUL formulas below — make the viewer feel FOR "
        "someone, not just unsettled."
        if target_register == "sympathy" else
        "Focus on the DREAD formulas below — create unease before the video starts."
    )
    sympathy_words = {"alone","listened","warned","blamed","cost","everything","last","tried"}

    if state is not None:
        state["last_title_register"] = target_register  # persists via later save_state(state)

    # FIX: trending_titles was already being fetched from the REAL YouTube
    # Data API elsewhere in this pipeline (actual current top-performing
    # video titles in this niche, last 30 days) — but it was only ever used
    # for topic selection and the script's cold open, never passed into the
    # actual title-writing step. That meant titles were formula-only, blind
    # to what's genuinely working right now. Wired in here.
    trend_block = ""
    if trending_titles:
        real_titles = "\n".join(f'  - "{t}"' for t in trending_titles[:6])
        trend_block = f"""
REAL CURRENT TOP-PERFORMING TITLES IN THIS NICHE (actual YouTube data, last 30
days, not invented) — study these for what's genuinely landing with audiences
right now, then write something that would fit alongside them without copying:
{real_titles}
Notice their actual phrasing rhythm, specificity level, and emotional angle —
match that energy, don't just follow the formulas below in isolation.
"""

    prompt = f"""
{trend_block}TITLE REQUIREMENTS — NON-NEGOTIABLE:
- Do NOT write normal YouTube titles. Normal = ignored.
- The title should feel like something a person would screenshot and send to a friend.
- Use specific numbers, real-feeling names, or uncomfortable specificity.
- The best titles create DREAD before the video starts — but dread is not the only
  register. A sympathetic, heartbreaking, "this could have been anyone" angle often
  outperforms pure shock, because it makes the viewer feel FOR someone, not just
  unsettled. Rotate between dread-driven and sympathy-driven framing rather than
  defaulting to dread every time — both are proven, and variety prevents the channel
  from reading as one-note.
- Dark humor in titles outperforms pure shock — it signals intelligence.
- The title should make someone feel like: "I shouldn't watch this... but I have to"
  OR "I need to know what happened to them" (sympathy-driven equivalent).
- CURIOSITY GAP: give enough to create genuine interest but withhold the one detail
  that can only be resolved by watching. Don't explain the outcome in the title.
- HONESTY CONSTRAINT (critical, non-negotiable): the title must be something the
  first 30 seconds of the actual video genuinely delivers on. YouTube's 2026 ranking
  now actively penalizes titles that get clicks but lose viewers fast when the video
  doesn't match the promise — this is worse for the channel long-term than a slightly
  less aggressive but honest title. Never promise a specific reveal the video doesn't
  actually contain in its opening.

TITLE FORMULAS THAT WORK (dread-driven):
- "[Number] [People/Days/Years] [Disturbing Specific Thing] — Nobody Talked About This"
- "The [Institution] Knew. They Did It Anyway. Here's The File."
- "How [Completely Normal Thing] Was Used To [Dark Outcome]"
- "[Name or System] Ran [Disturbing Operation] For [Specific Duration]. Here's The Evidence."
- "They Thought It Was [Normal Thing]. It Was [Dark Reality]."
- "The [Number]-Day [Dark Event] Everyone Pretended Didn't Happen"
- "[Specific Crime/System]: [Number] Victims. [Number] Years. [Number] Investigations. Zero Arrests."

TITLE FORMULAS THAT WORK (sympathy/woeful-driven — use these roughly as often as dread ones):
- "She Tried To Warn Them For [Number] Years. Nobody Listened."
- "[Number] Days Alone. Nobody Came. Here's What Happened To [Him/Her]."
- "All [Name] Wanted Was [Simple Normal Thing]. It Cost [Him/Her] Everything."
- "Everyone Blamed [Him/Her]. The Truth Was Worse Than Anyone Guessed."
- "The Last [Number] Days Of A Life Nobody Was Watching"

TITLE FORMULAS THAT WORK (concrete/object-driven — cleaner and more specific
than pure dread/sympathy, often outperforms both by feeling more real):
- "The Last Tape From Room [Number]"
- "Why She Betrayed Her Own [Sister/Brother/Mother]"
- "The [Hospital Wing/Facility] They Closed Forever"
- "He Heard [Family Member] After The Funeral"
- "The Confession Hidden In The [Journal/Tape/File]"
- "The [Patient/Person] Who Invented A Second Life"
- "Nobody Believed The Second [Recording/Call/Witness]"
- "The House That Remembered What [He/She] Did"

FORBIDDEN TITLE WORDS: "Shocking", "Incredible", "Amazing", "Unbelievable", 
"You Won't Believe", "Mind-Blowing", "Epic", "Ultimate", "Best"
These signal low-quality content. Avoid them completely.

Generate 5 YouTube titles for a dark investigative documentary.
Series: {niche["series"]}, Episode {episode}. Topic: {topic}
REGISTER FOR THIS EPISODE (enforced, alternates every episode): {register_instruction}
Rules: 40-65 chars each (fits fully on mobile). Front-load the most compelling part
in the first 40 characters. Opens a psychological loop. Specific numbers where natural.
Dark investigative tone. No colons unless essential. No quotes.
IMPORTANT: Start with a NUMBER or specific statistic for highest CTR.
Return ONLY 5 titles, one per line."""
    raw  = ai_generate(prompt, tokens=400)
    best = f"{niche['series']}: {topic[:55]}"
    best_score = 0

    def looks_like_title(t):
        # FIX: the AI sometimes returns a formatted fact list instead of a
        # title (e.g. "* *Numbers:* 3 years, 1095 days, 4 walls, 1 child,
        # 0 sleep, etc.") — that passed the old length-only filter and even
        # scored HIGH (numbers + "years"/"days" hook words), so it got
        # accepted as the actual video title. Reject anything that isn't
        # actually shaped like a single title line.
        if any(ch in t for ch in ("*", "_", "`", "#")):
            return False
        if t.count(",") >= 3:          # real titles don't read as a comma list
            return False
        if t.lower().startswith(("numbers:", "stats:", "facts:", "-", "•")):
            return False
        return True

    if raw:
        lines = [l.strip() for l in raw.strip().splitlines()
                 if 30 <= len(l.strip()) <= 80 and looks_like_title(l.strip())]
        if lines:
            # FIX: this used to score candidates with a simple additive
            # word-count/hook-word/number-bonus check. There was already a
            # genuinely more sophisticated scorer built (score_title_v2 +
            # run_title_ctr_gate) — real curiosity-gap phrase detection,
            # specificity+name combo, revelation language, pattern interrupt,
            # with TARGETED regeneration based on exactly which dimension
            # scored weak — sitting completely unused elsewhere in this file.
            # Wired in now instead of the simpler check.
            title_scores = [(l, 0) for l in lines]
            best, v2_scored = run_title_ctr_gate(
                lines[0], title_scores, topic, niche["name"], niche["series"],
                episode, ai_generate, min_ctr=6.5)
            best_score = v2_scored[0][1] if v2_scored else 0
            log(f"  Title (v2 scorer): {best_score}/10 — {best[:55]}")

    return best

def generate_chapters(audio_duration):
    if audio_duration < 60:
        return "0:00 Introduction"
    total = sum(STAGE_WORDS)
    lines = []
    elapsed = 0.0
    for i, (name, words) in enumerate(zip(STAGE_NAMES, STAGE_WORDS)):
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        lines.append(f"{mins}:{secs:02d} {name}")
        elapsed += audio_duration * (words / total)
    return "\n".join(lines)

# ================================================================
# DYNAMIC THUMBNAIL TEXT  [NEW #9]
# ================================================================
def generate_dynamic_thumbnail_text(script):
    """
    Generate NUMBER+NOUN thumbnail text — the highest CTR format in dark documentary.
    Examples: "4,380 DAYS"  "14 VICTIMS"  "ONE LETTER"  "$2.4M GONE"  "7 WITNESSES"
    The specific number creates believability. The noun creates visceral impact.
    Both together create a loop the viewer must close by watching.
    """
    words  = script.split()
    # Sample key sections of script for numbers and nouns
    sample = " ".join(words[:80]) + " " + " ".join(words[int(len(words)*0.4):int(len(words)*0.6)])
    sample = sample[:1000]
    prompt = f"""From this documentary narration, generate thumbnail text following the NUMBER+NOUN format.

This format drives the highest click-through rates in dark documentary YouTube:
- A SPECIFIC NUMBER (exact, real-feeling: days, victims, years, dollars, witnesses, documents)
- A POWERFUL NOUN (visceral, specific to the case)
- 2-4 words total, ALL CAPS

EXAMPLES OF HIGH-CTR FORMAT:
"4,380 DAYS" | "14 VICTIMS" | "ONE LETTER" | "$2.4M GONE" | "7 WITNESSES"
"17 YEARS" | "3 BODIES" | "ONE ENVELOPE" | "23 ACCOUNTS" | "48 HOURS"

AVOID generic phrases like "SOMETHING WRONG" or "DARK TRUTH" — these have low CTR.
The number must come from or be inspired by the actual content below.

NARRATION EXCERPT:
{sample}

Return ONLY the 2-4 word phrase in ALL CAPS. Nothing else."""
    raw = ai_generate(prompt, tokens=60)
    if raw:
        phrase = re.sub(r'[^A-Z0-9 ]', '', raw.strip().upper()).strip()
        if 2 <= len(phrase.split()) <= 4:
            return phrase
    return " ".join(script.split()[:3]).upper()

# ================================================================
# SEO DESCRIPTION
# ================================================================
def generate_seo_description(niche, topic, title, episode, chapters_text, audio_duration=0):
    dur_min = int(audio_duration / 60) if audio_duration > 60 else 15
    prompt = f"""Write a YouTube video description for a dark investigative documentary.
Title: {title} | Series: {niche["series"]}, Episode {episode}
Topic: {topic} | Duration: ~{dur_min} minutes

Structure:
1. Two hook sentences on the core disturbing fact. Creates urgency to watch.
2. Three sentences on what the investigation reveals. No spoilers.
3. One line: Watch until the end — the final revelation changes everything.
4. Chapters section (paste verbatim):\n{chapters_text or "0:00 Introduction"}
5. Eight keyword sentences using: dark documentary, true investigation, psychological analysis,
   hidden truth, {niche["name"].replace("_", " ")}, classified evidence, real case, dark nonfiction
6. One line: New investigations every week — subscribe so you never miss one.
7. Ten relevant hashtags

Total: 280-350 words. Plain text. No markdown."""
    # Build SEO hook for first 100 chars (shown in YouTube search results)
    # Format: [SPECIFIC CLAIM]. [EMOTIONAL HOOK]. Full investigation below.
    seo_hooks = {
        "dark_horror":        f"DOCUMENTED: {topic[:45]}.",
        "seduction_dark":     f"EXPOSED: {topic[:45]}.",
        "psychological_trap": f"CLASSIFIED: {topic[:45]}.",
        "supernatural_real":  f"EVIDENCE: {topic[:45]}.",
        "obsession_dark":     f"DOCUMENTED: {topic[:45]}.",
    }
    seo_first_line = seo_hooks.get(niche["name"], f"INVESTIGATION: {topic[:55]}.")

    raw = ai_generate(prompt, tokens=1000)
    # v12: three-channel cross-promo in every description
    cross_promo_txt = get_cross_promo("betrayal_deepdive", is_short=False)
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo_txt
        desc += "\n\n⚠️ This video features AI-assisted narration and editing."
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"Subscribe for new investigations every week.\n\n"
            f"#{niche['name'].replace('_', '')} #documentary #investigation"
            f"{cross_promo_txt}\n\n"
            f"⚠️ This video features AI-assisted narration and editing.")

# ================================================================
# ELEVENLABS TTS  [NEW #5]
# ================================================================
def call_elevenlabs(script, niche_name, output_path):
    if not ELEVENLABS_KEY: return False
    # Quick key validation — avoids wasting time on a 3-chunk run with an invalid key
    try:
        test = requests.get("https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": ELEVENLABS_KEY}, timeout=20)
        if test.status_code == 401:
            log("  ElevenLabs key invalid (401) — skipping, using edge-tts")
            return False
    except Exception: pass
    voice_id = EL_VOICES.get(niche_name, "29vD33N1CtxCmqQRPOHJ")
    chunks   = [script[i:i+4500] for i in range(0, len(script), 4500)]
    parts    = []
    try:
        for idx, chunk in enumerate(chunks):
            log(f"  ElevenLabs chunk {idx+1}/{len(chunks)}")
            r = requests.post(f"{ELEVENLABS_URL}/{voice_id}",
                headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
                json={"text": chunk, "model_id": "eleven_monolingual_v1",
                      "voice_settings": {"stability": 0.45, "similarity_boost": 0.82}},
                timeout=120)
            if r.status_code != 200:
                log(f"  ElevenLabs {r.status_code}")
                return False
            part = str(WORK_DIR / f"el_{idx}.mp3")
            with open(part, "wb") as f: f.write(r.content)
            parts.append(part)
            time.sleep(1)
        if len(parts) == 1:
            import shutil; shutil.copy(parts[0], output_path)
        else:
            lst = str(WORK_DIR / "el_list.txt")
            with open(lst, "w") as f:
                for p in parts: f.write(f"file '{p}'\n")
            run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", output_path], label="el-concat")
        log("OK ElevenLabs")
        return True
    except Exception as e:
        log(f"  ElevenLabs error: {e}")
        return False

# ================================================================
# EDGE-TTS WITH SUBTITLE GENERATION  [NEW #1]
# ================================================================
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
            # edge-tts SubMaker API varies by version — some versions don't have
            # generate_subs() at all (AttributeError), others have it but with a
            # different signature (TypeError). Catch both instead of just TypeError.
            try:
                subs_text = sub.generate_subs()
            except (TypeError, AttributeError):
                subs_text = None
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
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,50,1

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

def generate_fallback_ass(script, audio_duration, ass_path):
    """Approximate timing subtitles when edge-tts SubMaker unavailable."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,50,1

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

async def _edge_tts_segment(text, voice, rate, path):
    """Generate audio for one segment with a specific rate."""
    import edge_tts
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await asyncio.wait_for(comm.save(path), timeout=90)

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


def check_audio_quality(mp3_path, dur_expected):
    """Verify audio file is valid and meets minimum quality threshold."""
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 500_000:
            log(f"  Audio quality FAIL: {sz}b — too small"); return False
        r = subprocess.run(
            ["ffprobe","-v","quiet","-show_entries","format=duration",
             "-of","csv=p=0", str(mp3_path)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual = float(r.stdout.strip())
            if actual < dur_expected * 0.5:
                log(f"  Audio quality FAIL: {actual:.0f}s vs {dur_expected:.0f}s expected")
                return False
            log(f"  Audio quality OK: {sz/1024/1024:.1f}MB | {actual:.0f}s")
            return True
        log(f"  Audio quality OK (size only): {sz/1024/1024:.1f}MB"); return True
    except Exception as e:
        log(f"  Audio quality check error: {e}"); return False

def run_audio_stage(script, niche_name, edge_voice):
    audio_path = str(WORK_DIR / "narration.mp3")
    vtt_path   = str(WORK_DIR / "captions.vtt")
    ass_path   = str(WORK_DIR / "captions.ass")
    has_ass    = False

    log(f"  Words: {len(script.split())} | ElevenLabs: {'yes' if ELEVENLABS_KEY else 'no'}")

    # Try ElevenLabs premium voice first
    el_ok = call_elevenlabs(script, niche_name, audio_path)

    if el_ok:
        pass  # ElevenLabs doesn't support SSML rate — use as-is
    else:
        # Try SSML multi-rate audio (7 delivery speeds across 7 stages)
        log("  Trying SSML dynamic-rate audio...")
        # Truncate script to MAX_WORDS before SSML to prevent long audio failures
        _ssml_words = script.split()
        if len(_ssml_words) > MAX_WORDS:
            script = " ".join(_ssml_words[:MAX_WORDS])
            log(f"  Script truncated to {MAX_WORDS}w before SSML")
        ssml_path, ssml_dur = run_audio_with_ssml(script, niche_name, edge_voice)
        if ssml_path and ssml_dur > 60 and ssml_dur < 1800:  # 30-min max sanity cap
            import shutil
            if str(ssml_path) != str(audio_path):
                shutil.copy(ssml_path, audio_path)
            else:
                log("  SSML: skipping self-copy")
            duration = ssml_dur
            log(f"  SSML audio OK: {duration:.1f}s")
            return audio_path, duration, None, edge_voice

    if not el_ok:
        voices_to_try = [edge_voice] + [v for v in
            ["en-GB-RyanNeural", "en-US-BrianNeural", "en-US-JasonNeural"] if v != edge_voice]  # DavisNeural unavailable on Actions
        for _vfi, v in enumerate(voices_to_try):
            if _vfi > 0: time.sleep(3)  # avoid edge-tts rate limit
            try:
                log(f"  edge-tts: {v}")
                got_subs = asyncio.run(asyncio.wait_for(_edge_tts_stream(script, v, audio_path, vtt_path), timeout=120))
                if Path(audio_path).exists() and Path(audio_path).stat().st_size > 50000:
                    if got_subs and Path(vtt_path).exists():
                        has_ass = vtt_to_ass(vtt_path, ass_path)
                    log(f"  OK edge-tts ({v}) | captions: {has_ass}")
                    break
            except Exception as e: log(f"  {v}: {e}")

    if not Path(audio_path).exists() or Path(audio_path).stat().st_size < 10000:
        # ── FALLBACK CHAIN: every edge-tts voice failed today. Try alternate
        # providers before giving up entirely. Ordered by quality: Fish Audio
        # (natural, free tier via API key) -> gTTS (free, no key, noticeably
        # more robotic but reliable) -> offline espeak-ng (guaranteed local
        # synthesis, most robotic, true last resort).
        log("  All edge-tts voices exhausted — trying backup TTS providers...")
        script_clean = script
        dur_expected = min((len(script_clean.split()) / 125.0) * 60.0, 1080.0)  # matches 18-min hard cap
        fallback_ok = False

        fish_key = os.environ.get("FISH_AUDIO_API_KEY", "")
        if fish_key:
            try:
                r = requests.post("https://api.fish.audio/v1/tts",
                    headers={"Authorization": f"Bearer {fish_key}",
                             "Content-Type": "application/json",
                             "model": "s2-pro"},
                    json={"text": script_clean, "format": "mp3",
                          "normalize": True, "prosody": {"speed": 1.0}},
                    timeout=180)
                if r.status_code == 200 and len(r.content) > 50000:
                    with open(audio_path, "wb") as f: f.write(r.content)
                    log(f"  ACCEPTED: Fish Audio backup | {Path(audio_path).stat().st_size/1024/1024:.1f}MB")
                    tg("⚠️ Ch1: all edge-tts voices failed today — used Fish Audio backup instead (still natural-sounding)")
                    fallback_ok = True
                    edge_voice = "fish-audio-backup"
                else:
                    log(f"  Fish Audio: {r.status_code}")
            except Exception as e:
                log(f"  Fish Audio backup failed: {e}")
        else:
            log("  FISH_AUDIO_API_KEY not set — skipping Fish Audio backup")

        if not fallback_ok:
            try:
                from gtts import gTTS
                import shutil as _shutil
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
                        _shutil.copy(parts[0], audio_path)
                    else:
                        lst = str(WORK_DIR / "gtts_list.txt")
                        with open(lst, "w") as f:
                            for p in parts: f.write(f"file '{p}'\n")
                        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c","copy",audio_path],
                                       capture_output=True, timeout=300)
                    if Path(audio_path).exists() and Path(audio_path).stat().st_size > 50000:
                        log(f"  ACCEPTED: gTTS backup | {Path(audio_path).stat().st_size/1024/1024:.1f}MB (lower quality)")
                        tg("⚠️ Ch1: edge-tts AND Fish Audio both failed today — used gTTS backup "
                           "(noticeably more robotic). Check FISH_AUDIO_API_KEY / provider status.")
                        fallback_ok = True
                        edge_voice = "gtts-fallback"
            except Exception as e:
                log(f"  gTTS backup failed: {e}")

        if not fallback_ok:
            try:
                wav = str(WORK_DIR / "audio_espeak.wav")
                subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", wav, script_clean[:20000]],
                               capture_output=True, timeout=180)
                if Path(wav).exists() and Path(wav).stat().st_size > 50000:
                    subprocess.run(["ffmpeg","-y","-i",wav,audio_path], capture_output=True, timeout=60)
                    if Path(audio_path).exists():
                        log(f"  ACCEPTED: offline espeak-ng (LAST RESORT) | {Path(audio_path).stat().st_size/1024/1024:.1f}MB")
                        tg("🚨 Ch1: ALL providers failed today (edge-tts, Fish Audio, gTTS) — used OFFLINE "
                           "robotic voice as last resort so the video still published. Check provider status urgently.")
                        fallback_ok = True
                        edge_voice = "espeak-offline-LASTRESORT"
            except Exception as e:
                log(f"  espeak-ng backup failed: {e}")

        if not fallback_ok:
            raise RuntimeError("All TTS failed")

    duration = get_media_duration(audio_path)
    log(f"  Duration: {duration:.1f}s ({duration/60:.1f} min)")

    # HARD CEILING: 18 minutes, no exceptions. This is a safety net that
    # doesn't depend on finding the root cause of any upstream overshoot
    # (script length, TTS rate, a fallback concatenating extra audio,
    # anything) — whatever the cause, the final audio physically cannot
    # exceed this. Trims cleanly rather than an abrupt mid-word cut where
    # possible, and always alerts so the overshoot itself still gets
    # investigated rather than silently masked every time.
    HARD_MAX_SECONDS = 18 * 60
    if duration > HARD_MAX_SECONDS:
        log(f"  ⚠️ Audio exceeded 18-min hard cap ({duration/60:.1f} min) — trimming")
        trimmed = str(WORK_DIR / "narration_trimmed.mp3")
        run_ffmpeg(["ffmpeg", "-y", "-i", audio_path, "-t", str(HARD_MAX_SECONDS),
                    "-c", "copy", trimmed], label="hard-duration-cap", timeout=120)
        if Path(trimmed).exists() and Path(trimmed).stat().st_size > 50000:
            audio_path = trimmed
            duration = get_media_duration(audio_path)
            tg(f"⚠️ Ch1: narration ran {duration/60:.1f}min — over the 18-min limit, "
               f"had to trim it. The generation itself needs checking (script or TTS "
               f"rate produced too much audio) — this trim is a safety net, not a fix.")
            log(f"  Trimmed to: {duration:.1f}s ({duration/60:.1f} min)")

    # Apply documentary-grade audio post-processing
    processed_path = str(WORK_DIR / "narration_processed.mp3")
    audio_path = apply_audio_post_processing(audio_path, processed_path, niche_name=niche_name)

    if not has_ass:
        log("  Generating approximate timing captions...")
        generate_fallback_ass(script, duration, ass_path)
        has_ass = True

    return audio_path, duration, ass_path if has_ass else None, edge_voice

# ================================================================
# VIDEO DOWNLOAD
# ================================================================
def download_pixabay_video(keywords):
    """
    Search Pixabay with niche-specific dark keywords.
    Tries each keyword, picks the longest dark atmospheric result.
    Falls back to secondary keywords if primary set returns nothing.
    """
    if not PIXABAY_KEY: return None

    def try_keyword(kw):
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": kw, "per_page": 8,
                        "video_type": "film", "orientation": "horizontal"}, timeout=25)
            if r.status_code == 200 and r.json().get("hits"):
                # Pick longest video (more loop material for longer episodes)
                hit = max(r.json()["hits"], key=lambda h: h.get("duration", 0))
                url = hit["videos"]["medium"]["url"]
                path = str(WORK_DIR / "background.mp4")
                log(f"  Pixabay OK: '{kw}' ({hit.get('duration', 0)}s)")
                with requests.get(url, timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000:
                    return path
        except Exception as e:
            log(f"  Pixabay '{kw}': {e}")
        return None

    # Try primary keywords
    for kw in keywords:
        result = try_keyword(kw)
        if result: return result

    # Try fallback keywords (shorter, simpler terms)
    log("  Pixabay primary keywords exhausted — trying fallback terms")
    for kw in ["dark corridor", "dark room shadows", "night shadows dark",
               "dark abstract", "shadow dark background"]:
        result = try_keyword(kw)
        if result: return result

    return None

def download_pexels_video(keywords):
    if not PEXELS_KEY: return None
    for kw in keywords:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": kw, "per_page": 8, "orientation": "landscape",
                         "size": "large"}, timeout=25)
            if r.status_code == 200 and r.json().get("videos"):
                video  = r.json()["videos"][0]
                files  = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))
                target = next((f for f in files if f.get("width", 0) >= 720), files[-1]) if files else None
                if not target: continue
                path   = str(WORK_DIR / "background.mp4")
                log(f"  Pexels: {kw}")
                with requests.get(target["link"], timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(path).stat().st_size > 50000: return path
        except Exception as e: log(f"  Pexels '{kw}': {e}")
    return None

def generate_basic_shorts(video_path, audio_duration, title, niche_name, work_dir):
    """
    Real, working Shorts generator using only FFmpeg — no shorts_engine.py
    dependency needed (that module doesn't exist in the repo; this used to
    mean 0 Shorts, every single run, silently). Produces 2 solid vertical
    (1080x1920) Shorts cut directly from the already-finished main video:
      - Teaser: ~40s starting at the 10% mark
      - Reveal/recap: ~40s starting at the 67% mark
    Both get a bold hook-text overlay. Uses the exact same crop/scale/
    drawtext techniques already proven reliable elsewhere in this file —
    deliberately NOT a new fragile dependency.
    Returns a list of short dicts with 'ok' and 'path' keys, matching the
    shape the caller already expects from shorts_engine.
    """
    results = []
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font_path = next((fp for fp in font_paths if Path(fp).exists()), None)
    accent = NICHE_ACCENT_COLORS.get(niche_name, "0xE01010") if "NICHE_ACCENT_COLORS" in globals() else "0xE01010"

    clips = [
        ("teaser", 0.10, "WAIT FOR IT"),
        ("reveal", 0.67, "THE TRUTH"),
    ]

    for name, start_frac, hook_text in clips:
        try:
            start_t = max(0, start_frac * audio_duration)
            dur     = min(40, audio_duration - start_t - 1)
            if dur < 15:
                log(f"  Short ({name}): not enough runway at this mark — skipping")
                results.append({"ok": False, "path": None, "name": name})
                continue

            out_path = str(Path(work_dir) / f"short_{name}.mp4")
            vf_parts = [
                "crop=ih*9/16:ih:(iw-ih*9/16)/2:0",
                "scale=1080:1920",
            ]
            if font_path:
                esc = hook_text.replace("'", "")
                vf_parts.append(
                    f"drawtext=fontfile={font_path}:text='{esc}':"
                    f"fontsize=90:fontcolor=white:borderw=5:bordercolor=black:"
                    f"box=1:boxcolor={accent}@0.6:boxborderw=24:"
                    f"x=(w-text_w)/2:y=140"
                )
            vf = ",".join(vf_parts)

            run_ffmpeg([
                "ffmpeg", "-y", "-ss", f"{start_t:.2f}", "-i", video_path,
                "-t", f"{dur:.2f}", "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "21",
                "-c:a", "aac", "-b:a", "160k", out_path
            ], label=f"short-{name}", timeout=300)

            if Path(out_path).exists() and Path(out_path).stat().st_size > 200_000:
                log(f"  Short ({name}): {Path(out_path).stat().st_size//1024}KB")
                results.append({"ok": True, "path": out_path, "name": name})
            else:
                results.append({"ok": False, "path": None, "name": name})
        except Exception as e:
            log(f"  Short ({name}) failed (non-fatal): {e}")
            results.append({"ok": False, "path": None, "name": name})

    return results


def upload_basic_shorts(shorts, upload_fn, token, playlist_id, main_title, niche_name):
    """
    Companion to generate_basic_shorts() — uploads whatever it produced.
    Matches the shape returned by generate_basic_shorts (list of dicts
    with 'ok'/'path'/'name'), not the shorts_engine format (that module
    doesn't exist in this repo). Returns list of uploaded URLs.
    """
    urls = []
    for s in shorts:
        if not s.get("ok") or not s.get("path"):
            continue
        try:
            name = s.get("name", "clip")
            short_title = f"{main_title[:80]} #shorts"
            short_desc  = (f"{main_title}\n\nFull investigation on the channel.\n"
                            f"#shorts #darkpsychology #truecrime")
            url, vid_id = upload_fn(s["path"], short_title, short_desc, [], token=token)
            if url:
                urls.append(url)
                log(f"  Short ({name}) uploaded: {url}")
                if playlist_id:
                    try:
                        add_to_playlist(token, playlist_id, vid_id)
                    except Exception:
                        pass
        except Exception as e:
            log(f"  Short ({s.get('name','?')}) upload failed (non-fatal): {e}")
    return urls


def generate_approximate_srt(script, audio_duration, out_path):
    """
    growth_engine.py (which used to provide upload_srt_captions) doesn't
    exist in this repo — SRT captions have been silently skipped every
    single run. This builds a real SRT file without needing precise
    word-level timing: split the script into sentences, distribute
    timestamps proportionally across audio_duration (same reliable
    proportional-timing approach already used for background video
    matching and kinetic text elsewhere in this file). Not perfectly
    word-accurate, but genuinely useful for accessibility/SEO — far
    better than no caption track at all.
    """
    import re as _re
    sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', script) if s.strip()]
    if not sentences:
        return False
    total_words = sum(len(s.split()) for s in sentences)
    if total_words == 0:
        return False

    def fmt_ts(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    t = 0.0
    for i, sent in enumerate(sentences):
        wc = len(sent.split())
        dur = audio_duration * (wc / total_words)
        start, end = t, min(t + dur, audio_duration)
        lines.append(str(i + 1))
        lines.append(f"{fmt_ts(start)} --> {fmt_ts(end)}")
        lines.append(sent)
        lines.append("")
        t = end

    try:
        Path(out_path).write_text("\n".join(lines), encoding="utf-8")
        return True
    except Exception as e:
        log(f"  SRT write failed (non-fatal): {e}")
        return False


def upload_captions_track(token, video_id, srt_path, language="en"):
    """
    Uploads an SRT as a real YouTube caption track via the documented
    captions.insert API (multipart: JSON metadata + the SRT file body).
    This is a genuine gap-filler for the missing growth_engine module —
    built directly against YouTube's public API docs. Non-fatal: logs
    and returns False on any failure rather than blocking the upload.
    """
    try:
        metadata = {
            "snippet": {
                "videoId": video_id,
                "language": language,
                "name": "English",
                "isDraft": False,
            }
        }
        boundary = "----deepdive-captions-boundary"
        srt_bytes = Path(srt_path).read_bytes()
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + srt_bytes + f"\r\n--{boundary}--".encode("utf-8")

        r = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/captions"
            "?part=snippet&uploadType=multipart",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            data=body, timeout=60)
        if r.status_code in (200, 201):
            log("  OK Captions track uploaded")
            return True
        else:
            log(f"  Captions upload: {r.status_code} — {r.text[:200]}")
            return False
    except Exception as e:
        log(f"  Captions upload failed (non-fatal): {e}")
        return False


def get_stage_matched_video(niche, script, audio_duration):
    """
    Sequential audio-matched footage: the script is split into 55-75
    proportional segments (~12-15s of narration each), scaled dynamically
    to the actual video length. Each segment gets its own real
    Pixabay/Pexels clip, fetched using keywords drawn from THAT segment's
    actual narration content plus the niche's dark visual language, and
    that clip plays during exactly that segment — not shuffled or
    reordered. Shuffling for raw cut-count risked showing a clip during
    narration it didn't actually match; sequential + segment-matched
    keeps every visual genuinely tied to what's being said at that moment.
    Falls back to a single looped video if too few real clips come back.
    """
    words     = script.split()
    total     = len(words)

    # Dynamic segment count: target ~13.5s/clip (middle of the 12-15s
    # range), clamped to 55-75 regardless of exact video length so a
    # 15-min and an 18-min video both stay in the requested density band.
    TARGET_SECONDS_PER_CLIP = 13.5
    n_buckets = int(round(audio_duration / TARGET_SECONDS_PER_CLIP))
    n_buckets = max(55, min(75, n_buckets))

    # Expanded theme list (was 28, now 60) so segments this close together
    # don't hit the same theme label repeatedly — each tagged with a
    # niche-appropriate visual mood that follows the story's natural arc
    # (open -> unease -> escalation -> reveal -> aftermath), so even
    # segments without a strong extracted keyword still get a
    # mood-appropriate fallback term.
    theme_cycle = [
        "dark discovery opening", "ordinary life before dark", "quiet unease",
        "warning signs shadows", "growing dread", "isolation loneliness",
        "dark escalation danger", "chase pursuit tension", "trapped confined space",
        "surveillance watching", "documents evidence records", "empty corridor dread",
        "closing in danger", "false safety calm", "before the truth",
        "dark revelation truth exposed", "shocking discovery", "confrontation tension",
        "aftermath consequences", "empty aftermath", "quiet devastation",
        "haunting memory", "unresolved dread", "lingering shadow",
        "final warning", "closing image", "haunting final image", "dark fade out",
        "first signs missed", "silent house dread", "empty street night",
        "locked door tension", "shadow figure distant", "rain window dark",
        "phone call unanswered", "footsteps behind", "flickering light dread",
        "abandoned building interior", "clock ticking tension", "search investigation",
        "hidden room discovery", "torn photograph evidence", "handwritten note dread",
        "empty chair absence", "broken window entry", "dark basement stairs",
        "streetlight flicker night", "closed curtains hidden", "silent phone dread",
        "waiting room tension", "night drive alone", "empty parking lot",
        "locked drawer secret", "dust covered room", "old newspaper clipping",
        "security camera static", "dark hallway mirror", "half open door",
        "candle burning dark", "storm approaching dread", "final silence",
    ]
    bucket_words = max(1, total // n_buckets)
    segment_dur  = audio_duration / n_buckets

    fetched_clips = []
    black_fallback_count = 0
    stopwords  = {"the","a","an","and","or","but","in","on","at","to","for",
                  "of","with","by","from","this","that","was","were","had","have",
                  "it","its","he","she","they","their","his","her","be","been",
                  "not","no","so","as","if","then","than","when","what","who"}

    for i in range(n_buckets):
        base_kw = theme_cycle[i % len(theme_cycle)]
        start = i * bucket_words
        end   = min(start + bucket_words, total)
        stage_text = " ".join(words[start:end]).lower()

        stage_words= [w.strip(".,!?;:") for w in stage_text.split()
                      if len(w) > 4 and w not in stopwords]
        from collections import Counter
        top_nouns  = [w for w,_ in Counter(stage_words).most_common(2)]
        # Keyword = actual narration content at this exact moment + niche
        # theme, so the visual matches BOTH the audio and the niche mood.
        kw = " ".join(top_nouns[:1]) + " " + base_kw if top_nouns else base_kw

        clip_path  = str(WORK_DIR / f"seg_{i}.mp4")
        log(f"  Segment {i+1}/{n_buckets} (t={i*segment_dur:.0f}s) footage: '{kw[:40]}'")

        downloaded = False
        search_terms = [kw, base_kw, BG_KEYWORDS.get(niche["name"], ["dark shadows"])[i % 3],
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
                        log(f"    Segment {i+1} Pixabay: 429 rate limited")
            except Exception as e:
                log(f"    Segment {i+1} Pixabay: {e}")

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
                            log(f"    Segment {i+1} Pexels: 429 rate limited")
                except Exception as e:
                    log(f"    Segment {i+1} Pexels: {e}")

        if not downloaded:
            black_fallback_count += 1
            run_ffmpeg(["ffmpeg","-y","-f","lavfi",
                f"-i","color=c=black:size=1280x720:rate=24:duration={segment_dur:.1f}",
                "-c:v","libx264","-pix_fmt","yuv420p", clip_path],
                label=f"seg-{i}-fallback")
            log(f"  Segment {i+1}: NO footage found on Pixabay or Pexels — using black clip")

        if Path(clip_path).exists():
            fetched_clips.append(clip_path)

    if black_fallback_count > 0:
        tg(f"⚠️ {black_fallback_count}/{n_buckets} background segments had NO real footage "
           f"(Pixabay+Pexels both empty/exhausted) — used black clip instead. Check PIXABAY_KEY / PEXELS_API_KEY.")

    if len(fetched_clips) < 8:
        log("  Sequential matched footage insufficient — falling back to single looped video")
        return None

    # Trim/pad each clip to EXACTLY its segment's duration and scale — this
    # keeps every clip aligned to the real timestamp it was matched against,
    # so clip N plays while segment N's narration is actually being spoken.
    parts = []
    for i, clip in enumerate(fetched_clips):
        scaled = str(WORK_DIR / f"seg_{i}_scaled.mp4")
        # FIX: added fps=24 — each of these 55-75 fetched clips can have a
        # different native frame rate (24/25/30/60fps depending on the
        # source). Without normalizing here, before this internal -c copy
        # concat, mixed frame rates across segments risk timing drift or
        # glitches at the internal seams — same category of issue as the
        # audio sample-rate mismatch found and fixed in this same review.
        run_ffmpeg(["ffmpeg","-y","-stream_loop","2","-i",clip,
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,"
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24",
            "-t",f"{segment_dur:.2f}","-c:v","libx264","-preset","ultrafast",
            "-pix_fmt","yuv420p","-an", scaled], label=f"seg-scale-{i}")
        if Path(scaled).exists():
            parts.append(scaled)

    if not parts:
        return None

    list_file = str(WORK_DIR / "stage_list.txt")
    combined  = str(WORK_DIR / "background_staged.mp4")
    with open(list_file, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")

    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,
                "-c","copy","-t",str(audio_duration+5),combined], label="stage-concat")
    if Path(combined).exists() and Path(combined).stat().st_size > 50000:
        log(f"  Sequential matched video: {len(parts)} audio-matched segments | "
            f"{Path(combined).stat().st_size//(1024*1024)}MB")
        return combined
    return None

def get_background_video(niche, audio_duration, script=""):
    # Try stage-matched footage first (7 clips matching 7 script stages)
    if script:
        staged = get_stage_matched_video(niche, script, audio_duration)
        if staged: return staged
        log("  Stage-matched failed — using single keyword search")

    kws = BG_KEYWORDS.get(niche["name"], ["dark shadow night"])
    v   = download_pixabay_video(kws)
    if v: return v
    v   = download_pexels_video(kws)
    if v: return v
    path = str(WORK_DIR / "background.mp4")
    dur  = max(int(audio_duration) + 15, 60)
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=black:size=1280x720:rate=24:duration={dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", path], label="bg-fallback")
    return path


def apply_audio_post_processing(input_path, output_path=None, niche_name=None):
    """
    Niche-specific documentary-grade audio processing via FFmpeg.
    Uses NICHE_AUDIO_PROFILES to select the right EQ chain per niche.
    Falls back to default chain if niche not found.
    """
    try:
        af = NICHE_AUDIO_PROFILES.get(niche_name,
            # Default: warm documentary — broad appeal
            "equalizer=f=60:width_type=o:width=2:g=4,"
            "equalizer=f=250:width_type=o:width=2:g=2,"
            "equalizer=f=3000:width_type=o:width=2:g=-1,"
            "equalizer=f=8000:width_type=o:width=2:g=-2,"
                        "acompressor=threshold=-20dB:ratio=3:attack=3:release=100:makeup=3dB,"
            "loudnorm=I=-16:LRA=11:TP=-1.5"
        )
        run_ffmpeg([
            "ffmpeg", "-y", "-i", input_path,
            "-af", af,
            "-c:a", "mp3", "-q:a", "2", output_path
        ], label=f"audio-{niche_name or 'default'}", timeout=300)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            log(f"  Audio post-processed ({niche_name}): {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e:
        log(f"  Audio processing failed (non-fatal): {e}")
    return input_path


# ── Niche-specific audio profiles ────────────────────────────
# Each niche has a unique emotional target requiring different EQ/dynamics.
NICHE_AUDIO_PROFILES = {
    "dark_horror": (
        # Deep physical dread — heavy bass, cavernous reverb, dark tone
        "equalizer=f=60:width_type=o:width=2:g=5,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=10000:width_type=o:width=2:g=-4,"
        "acompressor=threshold=-18dB:ratio=4:attack=3:release=100:makeup=3dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "seduction_dark": (
        # Intimate and warm — close-mic feel, barely any reverb
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-4,"
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "psychological_trap": (
        # Dry and clinical — no reverb, tight compression, analytical voice
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        # No aecho — completely dry, clinical, no escape
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"          # tighter range = more controlled
    ),
    "supernatural_real": (
        # Wide ethereal space — large reverb, bass depth, mysterious
        "equalizer=f=80:width_type=o:width=2:g=4,"
        "equalizer=f=2000:width_type=o:width=2:g=2,"
        "equalizer=f=12000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2dB,"
        "loudnorm=I=-16:LRA=13:TP=-1.5"         # wider dynamics = more uncanny
    ),
    "obsession_dark": (
        # Intimate obsessive — no reverb, maximum presence, suffocating
        "equalizer=f=200:width_type=o:width=2:g=5,"
        "equalizer=f=400:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-5,"
        # No echo — obsession has no space, no distance
        "acompressor=threshold=-12dB:ratio=5:attack=2:release=30:makeup=4dB,"
        "loudnorm=I=-18:LRA=7:TP=-1.5"          # quieter, more intimate
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["dark_horror"]

# Dark footage keywords for standalone Shorts per niche
NICHE_SHORT_KEYWORDS = {
    "dark_horror":        "dark abandoned shadow horror atmospheric",
    "seduction_dark":     "dark silhouette shadow noir dramatic",
    "psychological_trap": "dark corridor psychology shadow mind",
    "supernatural_real":  "dark fog mysterious night paranormal",
    "obsession_dark":     "dark surveillance shadow night watching",
}

# ================================================================
# AMBIENT MUSIC
# ================================================================
def generate_ambient_music(duration):
    path = str(WORK_DIR / "music.mp3")
    dur  = int(duration) + 30
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=55:duration={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={dur}",
        "-f", "lavfi", "-i", f"aevalsrc=random(0)*0.003:duration={dur}",
        "-filter_complex",
        "[0]volume=0.07[a];[1]volume=0.035[b];[2]volume=0.4[c];"
        "[a][b][c]amix=inputs=3:duration=first,lowpass=f=280,highpass=f=28,volume=0.14[out]",
        "-map", "[out]", "-c:a", "mp3", "-q:a", "4", path
    ], label="music-gen")
    return path

# ================================================================
# INTRO + OUTRO  [NEW #7]
# ================================================================
def create_intro(series_name):
    path = str(WORK_DIR / "intro.mp4")
    text = series_name.replace("'", "").replace('"', "")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=2",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=2",
        "-vf", f"drawtext=text='{text}':fontsize=72:fontcolor=red:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", path
    ], label="intro")
    return path

def create_outro(series_name="Dark Hours", episode_num=1):
    """
    8-second end screen outro with visual end screen:
    - 0-3s: SUBSCRIBE CTA with series name
    - 3-8s: NEXT INVESTIGATION card pointing to channel
    Revenue driver: end screens are responsible for 15-30% of subscriber conversions.
    """
    # FIX: this used series_name directly with zero sanitization — every
    # other drawtext usage in this file strips quotes/colons since those
    # break ffmpeg's filter syntax. This one didn't, despite being the one
    # function here that's still genuinely called on every video.
    series_name = series_name.replace("'", "").replace('"', "").replace(":", "")
    path = str(WORK_DIR / "outro.mp4")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=8",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=8",
        "-vf",
        # Layer 1: Background pulse (red border)
        "drawbox=x=0:y=0:w=iw:h=ih:color=red@0.3:t=4,"
        # Layer 2: Series name (top)
        "drawtext=text='SUBSCRIBE TO " + series_name.upper() + "':fontsize=38:"
        "fontcolor=red:x=(w-text_w)/2:y=80:enable='between(t,0,8)',"
        # Layer 3: Bell icon substitute text
        "drawtext=text='🔔 NEW INVESTIGATION EVERY WEEKDAY':fontsize=28:"
        "fontcolor=white:x=(w-text_w)/2:y=160:enable='between(t,0,8)',"
        # Layer 4: End screen card (appears at 3s)
        "drawbox=x=780:y=200:w=460:h=260:color=red@0.8:t=fill:"
        "enable='between(t,3,8)',"
        "drawbox=x=780:y=200:w=460:h=260:color=white:t=3:"
        "enable='between(t,3,8)',"
        "drawtext=text='NEXT':fontsize=32:fontcolor=white:"
        "x=850:y=230:enable='between(t,3,8)',"
        "drawtext=text='INVESTIGATION':fontsize=28:fontcolor=white:"
        "x=800:y=275:enable='between(t,3,8)',"
        "drawtext=text='→':fontsize=48:fontcolor=red:"
        "x=940:y=310:enable='between(t,3,8)',"
        # Layer 5: Subscribe button card
        "drawbox=x=40:y=200:w=420:h=120:color=red@0.9:t=fill:"
        "enable='between(t,3,8)',"
        "drawtext=text='SUBSCRIBE':fontsize=48:fontcolor=white:"
        "x=90:y=235:enable='between(t,3,8)',"
        # Layer 6: Episode counter
        "drawtext=text='Investigation #" + str(episode_num) + "':fontsize=26:"
        "fontcolor=gray:x=40:y=H-60:enable='between(t,0,8)'",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", path
    ], label="outro-endscreen")
    return path

def concat_parts(parts, output_path):
    existing = [p for p in parts if p and Path(p).exists()]
    lst = str(WORK_DIR / "concat.txt")
    with open(lst, "w") as f:
        for p in existing: f.write(f"file '{p}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", lst, "-c", "copy", output_path], label="concat")
    return output_path




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
    """
    Load the top-performing script patterns from state.json.
    Used to inform the next script generation with what actually worked.
    """
    history = state.get("episode_history", [])
    if not history: return ""
    # Sort by score, take top 5
    top = sorted(history, key=lambda x: x.get("score", 0), reverse=True)[:5]
    if not top: return ""
    lines = ["WHAT HAS WORKED BEST FOR THIS CHANNEL (use as inspiration):"]
    for ep in top:
        lines.append(f"  Score {ep.get('score',0)}/10: {ep.get('topic','')[:80]}")
        lines.append(f"    Hook: {ep.get('hook_type','')}")
        lines.append(f"    Cold open style: {ep.get('cold_open_style','')}")
    return "\n".join(lines)

def save_pattern_memory(state, episode, niche_name, topic, score,
                        hook_type="", cold_open_style=""):
    """Store this episode's pattern data for future learning."""
    history = state.get("episode_history", [])
    history.append({
        "episode":         episode,
        "niche":           niche_name,
        "topic":           topic[:100],
        "score":           score,
        "hook_type":       hook_type,
        "cold_open_style": cold_open_style,
        "date":            datetime.datetime.now().strftime("%Y-%m-%d"),
    })
    state["episode_history"] = history[-50:]  # keep last 50 episodes
    return state

# ================================================================
# THUMBNAIL  [NEW #9 — dynamic text from script]
# ================================================================

def get_thumbnail_style(state, episode):
    """
    A/B thumbnail testing — alternate between 2 styles.
    Style A: Blood red text on AI-generated dark background (weeks 1,3,5...)
    Style B: White text with strong glow on darker AI background (weeks 2,4,6...)
    Weekly report will identify which drives better CTR.
    """
    week_number = datetime.datetime.now().isocalendar()[1]
    style       = "A" if week_number % 2 == 1 else "B"
    state.setdefault("thumbnail_ab", {})
    state["thumbnail_ab"]["last_style"]   = style
    state["thumbnail_ab"]["last_episode"] = episode
    log(f"  Thumbnail style: {style} (week {week_number})")
    return style


def fetch_case_relevant_image(topic, niche_name, out_path):
    """
    Search for a REAL case-relevant image using Pixabay/Pexels photo APIs.
    These keys are already set — zero additional cost.

    Priority:
    1. Pixabay photos (topic-specific search)
    2. Pexels photos (topic-specific search)
    3. Pollinations.ai (AI-generated atmospheric, free fallback)

    A real case-relevant image drives 2-3× higher CTR vs generic dark backgrounds
    because it creates immediate visual context for what the video covers.
    """
    # Extract 2-3 most specific keywords from topic for image search
    stopwords = {"a","an","the","and","or","but","in","on","at","to","for",
                 "of","with","by","from","this","that","was","were","had",
                 "have","it","he","she","they","who","what","when","how"}
    topic_words = [w.strip(".,!?-") for w in topic.lower().split()
                   if len(w) > 3 and w not in stopwords]
    search_kw = " ".join(topic_words[:3])

    # Niche visual modifiers — add context to make images darker/more relevant
    niche_mod = {
        "dark_horror":        "dark shadow dramatic",
        "seduction_dark":     "shadow silhouette mystery",
        "psychological_trap": "dark corridor abstract",
        "supernatural_real":  "mysterious dark atmospheric",
        "obsession_dark":     "shadow watching dark",
    }
    mod = niche_mod.get(niche_name, "dark dramatic")
    full_query = f"{search_kw} {mod}"

    # Try Pixabay photos first
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/",
                params={"key": PIXABAY_KEY, "q": full_query,
                        "image_type": "photo", "orientation": "horizontal",
                        "min_width": 1280, "safesearch": "true",
                        "per_page": 5, "order": "popular"},
                timeout=25)
            if r.status_code == 200 and r.json().get("hits"):
                hit = r.json()["hits"][0]
                img_url = hit.get("webformatURL") or hit.get("largeImageURL")
                if img_url:
                    ir = requests.get(img_url, timeout=30)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f:
                            f.write(ir.content)
                        log(f"  Case image (Pixabay): {search_kw}")
                        return True, "photo"
        except Exception as e:
            log(f"  Pixabay photo (non-fatal): {e}")

    # Try Pexels photos
    if PEXELS_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": full_query, "per_page": 5,
                        "orientation": "landscape", "size": "large"},
                timeout=25)
            if r.status_code == 200 and r.json().get("photos"):
                photo = r.json()["photos"][0]
                img_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                if img_url:
                    ir = requests.get(img_url, timeout=30)
                    if ir.status_code == 200 and len(ir.content) > 20000:
                        with open(out_path, "wb") as f:
                            f.write(ir.content)
                        log(f"  Case image (Pexels): {search_kw}")
                        return True, "photo"
        except Exception as e:
            log(f"  Pexels photo (non-fatal): {e}")

    # Fallback: Pollinations AI-generated atmospheric
    import urllib.parse
    prompt = (f"{search_kw} {mod} ultra dark atmospheric cinematic "
              f"documentary no faces no text 8k dramatic")
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width=1280&height=720&nologo=true&seed={abs(hash(topic)) % 9999}")
    try:
        r = requests.get(url, timeout=45)
        if r.status_code == 200 and len(r.content) > 30000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            log(f"  Case image (Pollinations AI): {search_kw}")
            return True, "ai"
    except Exception as e:
        log(f"  Pollinations (non-fatal): {e}")

    return False, "none"


def composite_thumbnail(bg_path, bg_type, thumb_text, title, ab_style, niche_name,
                         topic="", episode=1):
    """
    v2 thumbnail: three-layer composition using thumbnail_engine_v2.
    Layer 1: background (Pollinations.ai, niche-specific prompt)
    Layer 2: silhouette figure (ab_style A only)
    Layer 3: text with 5-layer shadow stack

    FIX: this used to hardcode episode=1 and pass title in place of topic,
    regardless of what was actually being generated — because this function's
    own signature never accepted topic/episode at all, so even though the
    caller (generate_thumbnail) HAD the real values, they could never reach
    here. Since thumbnail_engine_v2 renders an episode badge, every thumbnail
    past episode 1 would have shown the wrong episode number.
    """
    try:
        import importlib.util
        if importlib.util.find_spec("thumbnail_engine_v2") is None:
            raise ImportError("thumbnail_engine_v2 not found")
        from thumbnail_engine_v2 import generate_thumbnail_v2
        result = generate_thumbnail_v2(
            title        = title,
            thumb_text   = thumb_text,
            niche_name   = niche_name,
            topic        = topic or title,
            channel_name = "BetrayalDeepDive",
            episode      = episode,
            work_dir     = str(WORK_DIR),
            ab_variant   = ab_style,
            cache_dir    = str(SCRIPT_DIR),  # persistent repo path — avatar
                                              # cache must survive between
                                              # runs, unlike WORK_DIR
        )
        if result and Path(result).exists():
            log(f"  Thumbnail v2: {Path(result).stat().st_size//1024}KB | {ab_style} variant | Ep{episode}")
            return result
    except Exception as e:
        log(f"  Thumbnail v2 (non-fatal): {e}")
    return None


def fetch_pollinations_image(topic, niche_name, thumb_path):
    """Legacy wrapper — delegates to thumbnail_engine_v2."""
    got, _ = fetch_case_relevant_image(topic, niche_name, thumb_path)
    return got


def generate_thumbnail(thumb_text, niche_name, title, topic="", episode=0):
    """
    Full thumbnail pipeline:
    1. Search for REAL case-relevant image (Pixabay photo → Pexels photo → Pollinations AI)
    2. Composite the image with NUMBER+NOUN text overlay
    3. A/B style (red/white) based on week number
    Case-specific real imagery drives 2-3× higher CTR vs generic backgrounds.
    """
    state    = load_state()
    ab_style = get_thumbnail_style(state, episode)
    save_state(state)

    # Fetch case-relevant image (real photo or AI-generated)
    bg_path = str(WORK_DIR / "thumb_bg.jpg")
    got_image, bg_type = fetch_case_relevant_image(topic or thumb_text, niche_name, bg_path)

    # Composite with NUMBER+NOUN text
    result = composite_thumbnail(
        bg_path if got_image else None,
        bg_type, thumb_text, title, ab_style, niche_name,
        topic=topic, episode=episode)
    if result:
        return result

    # Final fallback: original Pillow-only method
    thumb_path = str(WORK_DIR / "thumbnail.jpg")
    pol_path   = str(WORK_DIR / "pollinations_bg.jpg")
    got_image  = fetch_pollinations_image(topic or thumb_text, niche_name, pol_path)

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        W, H = 1280, 720
        if got_image and Path(pol_path).exists():
            # Use Pollinations AI image as background, darkened
            bg_img = Image.open(pol_path).convert("RGB").resize((W, H))
            # Darken significantly so text remains readable
            from PIL import ImageEnhance
            bg_img = ImageEnhance.Brightness(bg_img).enhance(0.25)
            img = bg_img
        else:
            img = Image.new("RGB", (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        vig  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd   = ImageDraw.Draw(vig)
        for i in range(200):
            a = int(150 * (1 - i / 200))
            vd.rectangle([i, i, W-i, H-i], outline=(70, 0, 0, a))
        img.paste(Image.new("RGB", (W, H), (70, 0, 0)), mask=vig.split()[3])

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        def get_font(sz):
            for fp in font_paths:
                if Path(fp).exists():
                    try: return ImageFont.truetype(fp, sz)
                    except: pass
            return ImageFont.load_default()

        words = thumb_text.split()
        lines = [thumb_text] if len(words) <= 3 else [
            " ".join(words[:len(words)//2]), " ".join(words[len(words)//2:])]

        fm   = get_font(115)
        th   = len(lines) * 125
        sy   = (H - th) // 2 - 30
        for i, line in enumerate(lines):
            y    = sy + i * 125
            bbox = draw.textbbox((0, 0), line, font=fm)
            x    = (W - (bbox[2] - bbox[0])) // 2
            # A/B style colours
            if ab_style == "A":
                shadow_col = (0, 0, 0)
                text_col   = (200, 0, 0)  # blood red
            else:
                shadow_col = (0, 0, 0)
                text_col   = (255, 255, 255)
            for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4),(-4,0),(4,0)]:
                draw.text((x+dx, y+dy), line, font=fm, fill=shadow_col)
            draw.text((x, y), line, font=fm, fill=text_col)

        sub  = title[:65] + ("…" if len(title) > 65 else "")
        fs   = get_font(34)
        bb   = draw.textbbox((0, 0), sub, font=fs)
        sx   = (W - (bb[2] - bb[0])) // 2
        draw.text((sx+2, sy+th+20), sub, font=fs, fill=(20, 20, 20))
        draw.text((sx,   sy+th+18), sub, font=fs, fill=(210, 210, 210))
        draw.text((28, 22), "● DARK DOCUMENTARY", font=get_font(26), fill=(150, 0, 0))

        img.save(thumb_path, "JPEG", quality=95)
        log(f"OK Thumbnail: {Path(thumb_path).stat().st_size//1024}KB")
        return thumb_path
    except Exception as e:
        log(f"  Pillow error: {e} — trying ImageMagick")
    try:
        safe  = thumb_text.replace("'", "")[:28]
        stit  = title[:55].replace("'", "")
        subprocess.run(["convert", "-size", "1280x720", "xc:black",
            "-fill", "#C80000", "-pointsize", "115", "-gravity", "Center", "-annotate", "0", safe,
            "-fill", "#D2D2D2", "-pointsize", "34", "-gravity", "South", "-annotate", "0+0+60", stit,
            "-fill", "#960000", "-pointsize", "26", "-gravity", "NorthWest",
            "-annotate", "0+28+22", "DARK DOCUMENTARY", thumb_path],
            check=True, capture_output=True, timeout=30)
        log("OK Thumbnail (ImageMagick)")
        return thumb_path
    except Exception as e2:
        log(f"  Thumbnail failed: {e2}")
    return None

# ================================================================
# VIDEO COMPOSITION  (video + narration + music + burned captions)
# ================================================================

# ── Niche-specific atmospheric grading — makes stock footage feel like it
# belongs to a distinct dark brand instead of generic unedited clips.
# Free: pure FFmpeg eq/curves/vignette, no external LUT or paid tool.
NICHE_VISUAL_GRADE = {
    "dark_horror": (
        "eq=brightness=-0.08:contrast=1.25:saturation=0.75,"
        "vignette=PI/3.2"
    ),
    "seduction_dark": (
        "eq=brightness=-0.05:contrast=1.15:saturation=0.85,"
        "colorbalance=rs=0.08:bs=-0.06,"      # push toward warm magenta shadows
        "vignette=PI/3.8"
    ),
    "psychological_trap": (
        "eq=brightness=-0.06:contrast=1.3:saturation=0.55,"  # cold, clinical, desaturated
        "colorbalance=bs=0.08,"
        "vignette=PI/4"
    ),
    "supernatural_real": (
        "eq=brightness=-0.07:contrast=1.2:saturation=0.7,"
        "colorbalance=gs=0.06:bs=0.05,"       # eerie teal shift
        "vignette=PI/3.5"
    ),
    "obsession_dark": (
        "eq=brightness=-0.1:contrast=1.35:saturation=0.6,"   # suffocating, dark, close
        "vignette=PI/2.8"
    ),
}
DEFAULT_VISUAL_GRADE = NICHE_VISUAL_GRADE["dark_horror"]

def compose_video(narration_path, bg_path, music_path, ass_path,
                  audio_duration, label="main", niche_name=None):
    output   = str(WORK_DIR / f"composed_{label}.mp4")
    bg_dur   = get_media_duration(bg_path)
    loop_n   = max(int(audio_duration / max(bg_dur, 1)) + 2, 1)
    has_mus  = music_path and Path(music_path).exists()
    has_sub  = ass_path and Path(ass_path).exists()

    # Subtitles disabled — timing sync not reliable enough for dark content
    grade = NICHE_VISUAL_GRADE.get(niche_name, DEFAULT_VISUAL_GRADE)
    # fps=24 added — normalizes whatever native frame rate the source
    # background clip has (this path also serves the single-clip fallback,
    # whose source rate is unpredictable), consistent with intro/outro's
    # hardcoded 24fps so the final -c copy concat doesn't hit a mismatch.
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,"
          f"{grade}")

    if has_mus:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path,
            "-i", narration_path, "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[n];[2:a]volume=0.08[m];[n][m]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-t", str(audio_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path, "-i", narration_path,
            "-map", "0:v", "-map", "1:a",
            "-t", str(audio_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    run_ffmpeg(cmd, timeout=1800, label=f"compose-{label}")
    log(f"OK {label}: {Path(output).stat().st_size//(1024*1024)}MB")
    return output

# ================================================================
# SHORTS CREATION
# ================================================================
def _offset_ass_subtitles(ass_path, offset_seconds, output_path):
    """
    Shift all ASS subtitle timestamps back by offset_seconds.
    Required when creating Shorts that start mid-way through the main audio —
    the subtitle times need to be relative to the Short's start, not the main video.
    """
    def ass_to_sec(t):
        # H:MM:SS.cc
        try:
            h, m, rest = t.split(":")
            s, cs = rest.split(".")
            return int(h)*3600 + int(m)*60 + int(s) + int(cs)/100
        except: return 0.0

    def sec_to_ass(total):
        total = max(0.0, total)
        h  = int(total) // 3600
        m  = (int(total) % 3600) // 60
        s  = int(total) % 60
        cs = int(round((total - int(total)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    try:
        lines = Path(ass_path).read_text(encoding="utf-8").splitlines()
        out   = []
        for line in lines:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 3:
                    start = ass_to_sec(parts[1].strip()) - offset_seconds
                    end   = ass_to_sec(parts[2].strip()) - offset_seconds
                    parts[1] = " " + sec_to_ass(start)
                    parts[2] = sec_to_ass(end)
                    line = ",".join(parts)
            out.append(line)
        Path(output_path).write_text("\n".join(out), encoding="utf-8")
        return True
    except Exception as e:
        log(f"  ASS offset error: {e}")
        return False


def create_short(narration_path, bg_path, music_path, ass_path,
                 start_sec, duration_sec, label):
    seg_audio = str(WORK_DIR / f"{label}_seg.mp3")
    output    = str(WORK_DIR / f"{label}.mp4")

    run_ffmpeg(["ffmpeg", "-y", "-i", narration_path,
        "-ss", str(start_sec), "-t", str(duration_sec), "-c:a", "copy", seg_audio],
        label=f"{label}-cut")

    bg_dur = get_media_duration(bg_path)
    loop_n = max(int(duration_sec / max(bg_dur, 1)) + 2, 1)
    has_mus = music_path and Path(music_path).exists()
    has_sub = ass_path and Path(ass_path).exists()

    # Subtitles disabled on Shorts — timing sync not reliable
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
          "crop=405:720:(iw-405)/2:0,scale=1080:1920,fps=24")

    # fps=24 + explicit -ar 44100 added — same fix as the main video path,
    # since this background source clip's native frame rate is unknown and
    # the audio source (seg_audio) may not be at a fixed rate either.
    if has_mus:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path,
            "-i", seg_audio, "-i", music_path,
            "-filter_complex",
            "[1:a]volume=1.0[n];[2:a]volume=0.08[m];[n][m]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-t", str(duration_sec),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_n), "-i", bg_path, "-i", seg_audio,
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration_sec),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-vf", vf, "-movflags", "+faststart", output
        ]
    run_ffmpeg(cmd, timeout=300, label=label)
    return output

# ================================================================
# YOUTUBE API
# ================================================================
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
        err = d.get("error", "unknown")
        desc = d.get("error_description", "")
        if not globals().get("YOUTUBE_REFRESH_TOKEN", os.environ.get("YOUTUBE_REFRESH_TOKEN","")):
            raise Exception(f"YouTube token failed: refresh_token secret not set. "
                            f"Add YOUTUBE_REFRESH_TOKEN to GitHub Secrets.")
        raise Exception(f"YouTube token failed: {err} — {desc}")
    _tok_cache["token"]      = d["access_token"]
    _tok_cache["expires_at"] = now + d.get("expires_in", 3600)
    log("OK YouTube token")
    return d["access_token"]

def upload_yt(path, title, desc, tags, token=None, privacy="public"):
    token = token or get_yt_token()
    fs    = Path(path).stat().st_size
    log(f"  Uploading: {Path(path).name} ({fs//(1024*1024)}MB)")
    log(f"  Title: {title[:70]}")
    init = requests.post(
        f"{YT_UPLOAD_URL}/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(fs), "X-Upload-Content-Type": "video/mp4"},
        json={"snippet": {"title": title[:100], "description": desc,
                          "tags": tags[:15], "categoryId": "22"},
              "status": {"privacyStatus": privacy,
                         "selfDeclaredMadeForKids": False, "madeForKids": False,
                         "containsSyntheticMedia": True}},  # mandatory AI disclosure since Mar 2024
        timeout=30)
    url = init.headers.get("Location")
    if not url:
        raise Exception(f"No upload URL. {init.status_code}: {init.text[:300]}")

    CHUNK    = 16 * 1024 * 1024
    uploaded = 0
    retries  = 0
    with open(path, "rb") as f:
        while uploaded < fs:
            data = f.read(CHUNK)
            if not data: break
            end = uploaded + len(data) - 1
            try:
                up = requests.put(url,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Length": str(len(data)),
                             "Content-Range": f"bytes {uploaded}-{end}/{fs}",
                             "Content-Type": "video/mp4"},
                    data=data, timeout=600)
                if up.status_code in [200, 201]:
                    vid_id = up.json().get("id")
                    yt_url = f"https://www.youtube.com/watch?v={vid_id}"
                    log(f"  OK uploaded: {yt_url}")
                    return yt_url, vid_id
                elif up.status_code == 308:
                    rh       = up.headers.get("Range", "")
                    uploaded = int(rh.split("-")[1]) + 1 if rh else uploaded + len(data)
                    log(f"  {int(uploaded*100/fs)}%")
                    retries  = 0
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

def upload_thumbnail(video_id, thumb_path, token):
    # NOTE: this function is not currently called anywhere — the actual
    # active thumbnail upload is inline in the main upload flow (already
    # fixed earlier for the same silent-failure issue). Brought this one
    # up to the same standard for hygiene, in case anything calls it later.
    if not thumb_path or not Path(thumb_path).exists(): return
    try:
        with open(thumb_path, "rb") as f:
            r = requests.post(
                f"{YT_UPLOAD_URL}/thumbnails/set?videoId={video_id}&uploadType=media",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
                data=f.read(), timeout=60)
        if r.status_code in [200, 201]:
            log("OK Thumbnail uploaded")
        else:
            log(f"  Thumbnail upload FAILED: {r.status_code} — {r.text[:300]}")
            tg(f"⚠️ Thumbnail upload failed ({r.status_code}) — video published without a custom thumbnail.")
    except Exception as e: log(f"  Thumbnail (non-fatal): {e}")

def ensure_niche_playlist(token, niche_name, series_name):
    """[NEW #3] Find or create a per-niche playlist."""
    try:
        r = requests.get(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true", "maxResults": 50}, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                if series_name.lower() in item["snippet"]["title"].lower():
                    pid = item["id"]
                    log(f"  Playlist found: {pid}")
                    return pid
        r2 = requests.post(f"{YT_DATA_URL}/playlists",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet,status"},
            json={"snippet": {"title": f"{series_name} — Full Investigations",
                              "description": f"All episodes of {series_name}. New investigations weekly."},
                  "status": {"privacyStatus": "public"}}, timeout=20)
        if r2.status_code == 200:
            pid = r2.json()["id"]
            log(f"OK Playlist created: {pid}")
            return pid
    except Exception as e: log(f"  Playlist (non-fatal): {e}")
    return None

def add_to_playlist(token, playlist_id, video_id):
    """[NEW #3] Add video to playlist."""
    if not playlist_id: return
    try:
        r = requests.post(f"{YT_DATA_URL}/playlistItems",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
            timeout=20)
        if r.status_code in [200, 201]: log("OK Added to playlist")
        else: log(f"  Playlist add {r.status_code}")
    except Exception as e: log(f"  Playlist add (non-fatal): {e}")


def post_creator_comment(token, video_id, niche_name, title, episode):
    """
    Post a creator comment immediately after upload.
    Critical for revenue: early engagement signals boost algorithmic distribution.
    The comment contains SEO keywords, cross-promotion, and a hook question
    that drives replies (more engagement signals).
    """
    niche_hooks = {
        "dark_horror":        "Have you ever been somewhere and felt something was wrong?",
        "seduction_dark":     "Have you ever ignored warning signs because you wanted to believe?",
        "psychological_trap": "Have you ever been manipulated without realising it at the time?",
        "supernatural_real":  "Have you ever had an experience you couldn't rationally explain?",
        "obsession_dark":     "Is there someone in your life whose interest feels like more than it appears?",
    }
    hook = niche_hooks.get(niche_name,
        "What was the detail in this case that disturbed you the most?")
    comment = (
        f"👁️ {hook}\n\n"
        f"Drop your answer below — I read every reply.\n\n"
        f"🔔 Subscribe for a new investigation every weekday\n"
        f"📋 Full case sources in the description\n"
        f"🔎 Evidence Room channel: youtube.com/@TheEvidenceRoom\n\n"
        f"#{niche_name.replace('_','')} #documentary #investigation #episode{episode}"
    )
    try:
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            params={"part": "snippet"},
            json={"snippet": {
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": comment}}
            }}, timeout=30)
        if r.status_code == 200:
            log(f"  Creator comment posted OK")
            return r.json()["id"]
        else:
            log(f"  Creator comment {r.status_code} (non-fatal): {r.text[:100]}")
    except Exception as e:
        log(f"  Creator comment (non-fatal): {e}")
    return None

# ================================================================
# v12.0 NEW FUNCTIONS — TRAFFIC & REVENUE MAXIMISATION
# ================================================================

def generate_dedicated_short_title(main_title, short_type, niche_name):
    """
    Generate a dedicated Short title optimised for Shorts algorithm.
    DIFFERENT from the main video title — Shorts have their own discovery.
    Targets: curiosity gap, specific claim, under 60 chars.
    """
    prompts = {
        "teaser": f"Write a YouTube Shorts title that creates maximum curiosity. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, starts with a shocking fact or question, no 'watch' or 'click'. "
                  "Return ONLY the title.",
        "recap":  f"Write a YouTube Shorts title revealing the key finding. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, implies the truth was found, feels conclusive. "
                  "Return ONLY the title.",
    }
    type_key = "teaser" if "teaser" in short_type.lower() else "recap"
    try:
        result = ai_generate(prompts[type_key], tokens=80)
        if result:
            title = re.sub(r'[#*_`]', '', result.strip().split("\n")[0].strip())
            if 15 < len(title) < 65:
                log(f"  Short title: {title}")
                return title
    except Exception as e:
        log(f"  Short title (non-fatal): {e}")
    # Fallback: use a hook from the main title
    hooks = {"teaser": "This Is What Nobody Told You", "recap": "The Truth They Didn't Want Found"}
    return hooks.get(type_key, main_title[:50])


def post_short_creator_comment(token, video_id, niche_name, main_title):
    """
    Post a creator comment on each Short immediately after upload.
    Shorts comments drive early engagement signals = algorithmic boost.
    Different from main video comment — Shorts audience is colder.
    """
    short_hooks = {
        "dark_horror":        "Does this happen more than we know?",
        "seduction_dark":     "Have you ever seen these warning signs in real life?",
        "psychological_trap": "Is this happening around you right now?",
        "supernatural_real":  "What is the rational explanation for this?",
        "obsession_dark":     "Do you know someone whose interest feels like this?",
    }
    hook = short_hooks.get(niche_name, "What do you think happened?")
    comment = (
        f"💬 {hook}\n\n"
        f"Full investigation ↑ above.\n"
        f"🔔 New case every weekday → subscribe\n"
        f"🔬 Forensic crimes: youtube.com/@TheEvidenceRoom\n"
        f"🧠 Mass manipulation: youtube.com/@TheControlFiles\n\n"
        f"#{niche_name.replace('_','')} #shorts #documentary"
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
            log("  Short creator comment OK")
        else:
            log(f"  Short comment {r.status_code} (non-fatal)")
    except Exception as e:
        log(f"  Short comment (non-fatal): {e}")


def build_three_channel_cross_promo(niche_name, is_short=False):
    """
    Build standardised three-channel cross-promotion block.
    Injects in every description — main video AND Shorts.
    Three-channel flywheel: each channel sends viewers to both others.
    """
    if is_short:
        return (
            "\n\n🔬 Full forensic investigations: youtube.com/@TheEvidenceRoom"
            "\n🧠 Mass manipulation exposed: youtube.com/@TheControlFiles"
        )
    return (
        "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
        "\n🧠 Mass manipulation & propaganda: youtube.com/@TheControlFiles"
        "\n\n📺 New investigation every weekday on all three channels."
    )


def run_ch1_viral_intelligence(niche):
    """
    Viral intelligence engine for Ch1 (ported from Ch2).
    Runs weekly — results cached in state.json under 'viral_intel'.
    Finds what's working in the dark horror/psychological documentary niche.
    """
    state = load_state()
    intel = state.get("viral_intel", {})
    name  = niche["name"]
    if name in intel:
        try:
            last = datetime.datetime.fromisoformat(intel[name].get("last_run", "2020-01-01"))
            if (datetime.datetime.now() - last).days < 7:
                log(f"  Ch1 viral intel cached ({name})")
                return intel[name]
        except: pass

    log(f"  Running Ch1 viral intelligence: {name}...")
    prompt = f"""Analyze the TOP 20 most viral dark documentary YouTube videos (2M+ views) in the
"{niche['search_query']}" niche.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"retention_hooks":["30pct","60pct","80pct"],
"niche_power_words":["word1","word2","word3","word4","word5","word6"],
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6"]}}"""
    try:
        text = ai_generate(prompt, tokens=400)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','', re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            d = json.loads(m.group())
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d
            state["viral_intel"] = intel
            save_state(state)
            log("  Ch1 viral intel loaded")
            return d
    except Exception as e:
        log(f"  Ch1 viral intel err: {e}")

    fallback = {
        "top_hook_formulas": niche.get("dread_triggers", [])[:3],
        "winning_title_patterns": ["NUMBER + NOUN format", "The [THING] That Changed Everything"],
        "thumbnail_text_examples": [t.upper() for t in niche.get("topics", [])[:3]],
        "retention_hooks": ["The next detail is the one that changes everything",
                            "What was found at this point made investigators stop",
                            "The final revelation is the one nobody expected"],
        "niche_power_words": ["documented","witnessed","concealed","discovered","classified","permanent"],
        "fresh_topic_ideas": niche.get("topics", []),
        "last_run": datetime.datetime.now().isoformat()
    }
    intel[name] = fallback
    state["viral_intel"] = intel
    save_state(state)
    return fallback


def get_ch1_archive_topic(niche, attempt, used_topics):
    """
    Archive fallback: when fresh topics are exhausted (attempt > 8),
    dig into proven viral stories from 2022-2024.
    """
    prompt = f"""Find 6 documented real-world stories from 2022-2024 that fit
the "{niche['name'].replace('_',' ')}" niche and went viral as documentary YouTube videos.
Focus: {niche['search_query']}
Not already used: {[t[:40] for t in used_topics[:4]]}
Return ONLY a JSON array: ["Story 1","Story 2","Story 3","Story 4","Story 5","Story 6"]"""
    try:
        text = ai_generate(prompt, tokens=400)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','', re.sub(r'```json|```','',text).strip())
        m = re.search(r'\[[\s\S]*?\]', text)
        if m:
            topics = json.loads(m.group())
            unused = [t for t in topics if t not in used_topics]
            if unused:
                chosen = random.choice(unused)
                log(f"  Archive topic: {chosen[:70]}")
                return chosen
    except Exception as e:
        log(f"  Archive topic err: {e}")
    unused_seeds = [t for t in niche["topics"] if t not in used_topics]
    return random.choice(unused_seeds) if unused_seeds else niche["topics"][0]


def update_channel_description(token, latest_title, latest_url):
    """[NEW #12] Update channel About with latest episode."""
    try:
        r = requests.get(f"{YT_DATA_URL}/channels",
            headers={"Authorization": f"Bearer {token}"},
            params={"part": "snippet", "mine": "true"}, timeout=20)
        if r.status_code != 200: return
        ch_id = r.json()["items"][0]["id"]
        # FIX: YouTube's channels.update requires the FULL snippet object
        # when part=snippet, not just the field being changed — sending
        # only {"description": ...} without the existing "title" is
        # missing a required field and returns 400 every time. Grab the
        # existing snippet from the GET above and only mutate description.
        existing_snippet = r.json()["items"][0].get("snippet", {})
        desc  = (f"Latest: {latest_title}\n{latest_url}\n\n"
                 "Investigative documentary narrations — dark psychology, true horror, classified evidence.\n"
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
def cleanup():
    try:
        for f in glob.glob(str(WORK_DIR / "*")):
            if os.path.isfile(f): os.remove(f)
        log("OK Cleaned temp files")
    except Exception as e: log(f"  Cleanup (non-fatal): {e}")

# ================================================================
# MAIN PIPELINE
# ================================================================

def run_provider_health_check():
    """
    Tests all AI providers at pipeline startup.
    Fires BEFORE script generation so you see exactly what works.
    Results sent to Telegram so you can see them in the approval gate.
    """
    log("\n" + "="*65)
    log("  AI PROVIDER HEALTH CHECK")
    log("="*65)
    test = "Reply with exactly: OK"
    results = {}

    checks = [
        ("Cerebras",    call_cerebras),
        ("SambaNova",   call_sambanova),
        ("Gemini",      call_gemini),
        ("Groq",        call_groq),
        ("OpenRouter",  call_openrouter),
        ("Cohere",      call_cohere),
        ("Mistral",     call_mistral),
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


def generate_ch1_short_script(niche_name, topic, short_num):
    """45-second standalone Short script optimised for Shorts algorithm."""
    angles = {
        0: "the single most psychologically disturbing documented fact",
        1: "the warning sign that was visible but ignored — and what happened next",
    }
    prompt = (
        f"Write a 45-second YouTube Shorts narration script.\n"
        f"Topic: {topic}\nFocus: {angles.get(short_num, angles[0])}\n"
        f"Tone: Dark investigative psychological documentary\n\n"
        f"STRUCTURE:\n"
        f"Line 1 (HOOK 3sec): Specific number/date/fact. Mid-action. No intro.\n"
        f"Lines 2-4 (BUILD 20sec): Three short sentences max 10 words each.\n"
        f"Lines 5-6 (REVEAL 15sec): Most disturbing documented detail.\n"
        f"Line 7 (CTA 5sec): Follow for the full investigation.\n\n"
        f"RULES: 120-130 words total. No markdown. Plain text only."
    )
    result = ai_generate(prompt, tokens=350)
    if result:
        clean = result.strip().replace("**","").replace("##","").replace("*","")
        words = clean.split()
        return " ".join(words[:130]) if len(words) > 132 else clean
    return None

def create_ch1_standalone_short(script, niche_name, short_num, edge_voice):
    """Create standalone Short: dark atmospheric footage + narration. No subtitles."""
    audio_out = str(WORK_DIR / f"ch1_short_audio_{short_num}.mp3")
    try:
        import edge_tts as _edge
        async def _gen():
            comm = _edge.Communicate(text=script, voice=edge_voice, rate="-5%")
            await asyncio.wait_for(comm.save(audio_out), timeout=120)
        asyncio.run(_gen())
    except Exception as e:
        log(f"  Short {short_num+1} audio: {e}"); return None

    if not Path(audio_out).exists() or Path(audio_out).stat().st_size < 20000:
        return None

    try:
        import json as _j
        dp = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
                             "-show_streams",audio_out], capture_output=True, text=True, timeout=30)
        dur = 45.0
        for s in _j.loads(dp.stdout).get("streams",[]):
            if s.get("codec_type") == "audio":
                dur = float(s.get("duration", 45.0)); break
    except: dur = 45.0

    kw  = NICHE_SHORT_KEYWORDS.get(niche_name, "dark shadow atmospheric")
    bg  = None
    if PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": kw, "per_page": 3}, timeout=25)
            if r.status_code == 200 and r.json().get("hits"):
                url = r.json()["hits"][0]["videos"]["medium"]["url"]
                bgp = str(WORK_DIR / f"ch1_short_bg_{short_num}.mp4")
                with requests.get(url, timeout=30, stream=True) as dl:
                    with open(bgp, "wb") as f:
                        for chunk in dl.iter_content(32768): f.write(chunk)
                if Path(bgp).exists() and Path(bgp).stat().st_size > 50000:
                    bg = bgp
        except: pass

    out = str(WORK_DIR / f"ch1_standalone_short_{short_num}.mp4")
    if bg:
        # Real footage — vertical crop, darkened, NO subtitles
        run_ffmpeg(["ffmpeg","-y","-stream_loop","-1","-i",bg,"-i",audio_out,
            "-vf","scale=1280:720:force_original_aspect_ratio=decrease,"
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                  "crop=405:720:(iw-405)/2:0,scale=1080:1920,"
                  "eq=brightness=-0.3:contrast=1.3",
            "-c:v","libx264","-preset","fast","-crf","22",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",str(dur+0.3),"-shortest",out],
            label=f"ch1-short-{short_num}", timeout=180)
    else:
        run_ffmpeg(["ffmpeg","-y","-f","lavfi",
            "-i","color=c=black:size=1080x1920:rate=24",
            "-i",audio_out,"-c:v","libx264","-preset","fast","-crf","22",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",str(dur+0.3),"-shortest",out],
            label=f"ch1-short-fallback-{short_num}", timeout=120)

    if Path(out).exists() and Path(out).stat().st_size > 200000:
        log(f"  Ch1 Short {short_num+1}: {Path(out).stat().st_size//(1024*1024)}MB")
        return out
    return None



# ================================================================
# WRAPPER FUNCTIONS — bridge between main() calls and implementations
# ================================================================

def run_stage1(state):
    """
    13-attempt script engine for Ch1 BetrayalDeepDive.
    Returns (niche_name, niche, topic, script_result, trending_titles).
    """
    log("\n"+"="*65)
    log("  STAGE 1: BetrayalDeepDive 13-Attempt Script Engine")
    log(f"  Graduated quality gate: attempts 1-8 require {MIN_GATE} | "
        f"attempts 9-12 relax to 7.0 | attempt 13 absolute floor {FINAL_GATE}")
    log("="*65)

    day        = datetime.datetime.now().weekday()
    niche_name = pick_best_niche(state, DAY_NICHE.get(day, "dark_horror"))
    niche      = next(n for n in NICHES if n["name"] == niche_name)
    episode    = state.get("episode_count", 0) + 1
    prev_title = state.get("last_title", "")

    intel          = run_ch1_viral_intelligence(niche)
    trending       = []
    used_topics    = []
    gate           = MIN_GATE
    best_score     = 0.0
    best_result    = None
    best_topic     = niche["topics"][0]
    best_trending  = []

    log(f"\nNiche: {niche_name} | ${niche['rpm']} RPM | Ep{episode}")

    # Topic-scoring backlog integration — same pattern as Ch2: prefer a
    # human-approved topic from the real backlog over fresh generation.
    _approved_topic_entry = None
    try:
        from topic_scoring import get_next_approved_topic
        _approved_topic_entry = get_next_approved_topic(SCRIPT_DIR)
    except Exception as e:
        log(f"  Topic backlog check (non-fatal): {e}")

    for attempt in range(1, 14):
        # Graduated 13-level quality gate, per explicit specification:
        # attempts 1-8 require the high bar (8.5) — this is where the system
        # should be succeeding under normal conditions; attempts 9-13 relax
        # to 7.0 as a real fallback, never lower; attempt 13 specifically
        # allows 6.9 as the absolute last-resort floor, never crossed below.
        if attempt == 13:
            gate = FINAL_GATE       # 6.9 — absolute floor, last attempt only
        elif attempt >= 9:
            gate = 7.0              # attempts 9-12 — relaxed fallback tier
        else:
            gate = 8.5              # attempts 1-8 — the real standard

        # Get fresh topic each attempt
        if _approved_topic_entry and attempt == 1:
            topic = _approved_topic_entry["topic_text"]
        elif attempt <= 8:
            fresh = intel.get("fresh_topic_ideas", niche["topics"])
            unused = [t for t in fresh if t not in used_topics]
            topic = unused[0] if unused else random.choice(niche["topics"])
            try:
                from topic_scoring import add_topic_candidate
                add_topic_candidate(SCRIPT_DIR, "betrayal_deepdive", topic, niche_name,
                                     lambda p, tokens=200: ai_generate(p, tokens=tokens))
            except Exception as e:
                log(f"  Topic scoring (non-fatal): {e}")
        else:
            topic = get_ch1_archive_topic(niche, attempt, used_topics)
        used_topics.append(topic)

        # Research real cases for this topic
        research_ctx = get_research_context(niche_name, topic)

        log(f"\nAttempt {attempt}/13 (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            result = generate_script_content(
                niche, topic, episode, attempt,
                trending_titles=trending,
                research_context=research_ctx)

            if not result:
                time.sleep(5); continue

            score, _ = score_result(result)
            wc       = result.get("words", 0)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w")

            if score > best_score:
                best_score   = score
                best_result  = result
                best_topic   = topic
                best_trending= trending

            if score >= gate:
                log(f"\nSCRIPT APPROVED: {score}/10 | Attempt {attempt}\n")
                result["attempt"] = attempt  # for the audit engine — which gate tier this cleared
                return niche_name, niche, topic, result, trending

            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if best_result and best_score >= FINAL_GATE:
        log(f"\nUsing best: {best_score}/10 after 13 attempts")
        tg(f"Note: Publishing {best_score}/10 after 13 attempts.")
        best_result["attempt"] = 13  # fires only after all 13 attempts are exhausted
        return niche_name, niche, best_topic, best_result, best_trending

    tg(f"Ch1 Day Skipped\nBest: {best_score}/10 after 13 attempts")
    sys.exit(0)


def pick_voice(niche_name, state):
    """Select best voice for this niche based on performance history."""
    available = VOICES.get(niche_name, ["en-GB-RyanNeural", "en-US-BrianNeural"])
    return select_best_voice(state, niche_name, available)


def run_approval_gate(title, niche_name, script_clean, edge_voice, score):
    """30-minute Telegram approval gate before video generation."""
    niche = next(n for n in NICHES if n["name"] == niche_name)
    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime("%I:%M %p")
    preview      = script_clean[:400].replace("<","").replace(">","")

    approval_text = (
        f"🌑 <b>BETRAYAL DEEPDIVE — APPROVAL NEEDED</b>\n\n"
        f"📌 <b>Title:</b> {title}\n\n"
        f"🎯 <b>Niche:</b> {niche_name} | ${niche['rpm']} RPM\n"
        f"🎙️ <b>Voice:</b> {edge_voice}\n"
        f"📝 <b>Script:</b> {len(script_clean.split())}w | {score}/10\n\n"
        f"⏰ Auto-uploads at {deadline_str}\n\n"
        f"👇 <b>APPROVE / REJECT / CHANGE TITLE</b>"
    )
    tg_buttons(approval_text)
    time.sleep(1)
    tg(f"📖 <b>Script Preview:</b>\n<code>{preview}...</code>")

    updates = tg_get_updates()
    offset  = (max(u["update_id"] for u in updates)+1) if updates else 0
    reminded = set()

    while datetime.datetime.now() < deadline:
        time.sleep(30)
        for u in tg_get_updates(offset):
            offset = u["update_id"] + 1
            if "callback_query" in u:
                cb   = u["callback_query"]
                data = cb.get("data", "")
                cbid = cb.get("id", "")
                if data == "approved":
                    tg_answer_callback(cbid, "Approved!")
                    tg("APPROVED. Generating video now...")
                    return "approved"
                elif data == "rejected":
                    tg_answer_callback(cbid, "Rejected")
                    tg("REJECTED. Stopping pipeline.")
                    return "rejected"
                continue
            txt = u.get("message",{}).get("text","").upper().strip()
            cid = str(u.get("message",{}).get("chat",{}).get("id",""))
            if cid == str(TG_CHAT):
                if any(w in txt for w in ["APPROVE","YES","GO","OK","UPLOAD"]):
                    tg("APPROVED."); return "approved"
                if any(w in txt for w in ["REJECT","NO","SKIP","CANCEL"]):
                    tg("REJECTED."); return "rejected"
        mins = int((deadline - datetime.datetime.now()).total_seconds()/60)
        if 13<=mins<=17 and "15" not in reminded:
            reminded.add("15")
            tg_buttons(f"⏰ 15 min until auto-upload\n<b>{title}</b>")
        elif 3<=mins<=6 and "5" not in reminded:
            reminded.add("5")
            tg_buttons("🚨 5 MIN — AUTO-UPLOADING SOON")

    tg("30 min expired — AUTO-APPROVED.")
    return "auto_approved"



# ════════════════════════════════════════════════════════════
# KINETIC TYPOGRAPHY — animated text overlays at key story beats
# Per user requirement: "animation for key beats, stock footage as
# backdrop" (Ch1 style pairing: atmospheric motion + minimal kinetic
# type overlays). Free, built entirely with FFmpeg drawtext — no new
# API, no paid service, no self-hosted model.
# ════════════════════════════════════════════════════════════

NICHE_ACCENT_COLORS = {
    "dark_horror":        "0xE01010",  # blood red
    "seduction_dark":     "0xB0208A",  # deep magenta
    "psychological_trap": "0x4A6FA5",  # cold clinical blue
    "supernatural_real":  "0x2FA0A0",  # eerie teal
    "obsession_dark":     "0x8B0000",  # dark red, suffocating
}

def extract_key_phrases(script, num_phrases=6):
    """
    Split the script proportionally into `num_phrases` segments (same
    stage-proportion approach as inject_ssml_rate) and pull the single
    most punchy short phrase from each — prioritizing numbers and dread
    hook-words, same scoring logic as the title generator. These become
    the on-screen kinetic text callouts, timed to stage boundaries so
    they don't need fragile word-level timing data.
    Returns list of (phrase, start_fraction, end_fraction) — fractions
    of total audio_duration, so the caller can convert to real seconds.
    """
    hook_words = ["never", "nobody", "secret", "revealed", "truth", "years", "days",
                  "finally", "hidden", "classified", "documented", "knew", "told", "found",
                  "no one", "alone", "silence", "disappeared", "vanished", "warning"]

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if s.strip()]
    if not sentences:
        return []

    total = len(sentences)
    chunk_size = max(1, total // num_phrases)
    phrases = []

    def score(sent):
        s = 0
        if any(c.isdigit() for c in sent): s += 3
        for hw in hook_words:
            if hw in sent.lower(): s += 2
        wc = len(sent.split())
        if 3 <= wc <= 8: s += 2       # short punchy fragments overlay better than long lines
        return s

    for i in range(num_phrases):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, total)
        if start_idx >= total:
            break
        chunk = sentences[start_idx:end_idx]
        if not chunk:
            continue
        best = max(chunk, key=score)
        # Trim to a punchy fragment: first clause, capped at 6 words for on-screen impact
        words = re.sub(r'[^\w\s0-9,]', '', best).split()
        fragment = " ".join(words[:6]).upper()
        if not fragment.strip():
            continue
        start_frac = i / num_phrases
        end_frac   = (i + 1) / num_phrases
        phrases.append((fragment, start_frac, end_frac))

    return phrases


def add_horror_atmosphere_fx(video_path, script, audio_duration, niche_name, output_path):
    """
    Horror-appropriate visual treatment — replaces the earlier boxed
    kinetic-text-callout system (that was an explainer-video convention,
    wrong genre fit for dark psychology/horror content). Built and
    verified against real rendered test output before going into
    production, same discipline as everything else in this pipeline:
      - continuous film grain (dread, unease, "found footage" texture)
      - 2 brief chromatic-aberration bursts at key story beats (glitch/wrong feeling)
      - ONE jump-scare white flash at the biggest reveal moment (~65% through)
      - unstable, jittery, flickering text instead of confident boxed captions
    All pure FFmpeg (noise, rgbashift, blend, drawtext) — no new dependency,
    no repeat of the Lottie dead end. Non-fatal: falls back to the
    un-treated video if anything goes wrong.
    """
    try:
        phrases = extract_key_phrases(script, num_phrases=5)
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font_path = next((fp for fp in font_paths if Path(fp).exists()), None)

        # ── Continuous film grain — applied throughout ──
        video_filters = ["noise=alls=15:allf=t+u"]

        # ── Chromatic aberration bursts at 2 dread beats ──
        if len(phrases) >= 2:
            beat_fracs = [phrases[1][1], phrases[-1][1]]  # 2nd and last story beat
        elif phrases:
            beat_fracs = [phrases[0][1]]
        else:
            beat_fracs = [0.3, 0.7]
        for frac in beat_fracs[:2]:
            t0 = max(0.5, frac * audio_duration)
            t1 = min(t0 + 0.5, audio_duration - 0.2)
            if t1 > t0:
                video_filters.append(f"rgbashift=rh=6:bh=-6:enable='between(t,{t0:.2f},{t1:.2f})'")

        # ── Unstable, jittery, flickering text (no box, no confident callout) ──
        if font_path and phrases:
            DISPLAY_SECONDS = 3.0
            for phrase, start_frac, end_frac in phrases:
                t0 = start_frac * audio_duration
                t1 = min(t0 + DISPLAY_SECONDS, end_frac * audio_duration)
                if t1 - t0 < 1.2:
                    continue
                esc = phrase.replace("'", "").replace(":", "").replace("\\", "")
                # Jittery position (small sine wobble) + irregular flicker alpha
                # (on/off pattern mimicking a failing light / interference),
                # instead of a smooth confident fade — reads as unstable/dread.
                video_filters.append(
                    f"drawtext=fontfile={font_path}:text='{esc}':"
                    f"fontsize=58:fontcolor=white:borderw=3:bordercolor=black:"
                    f"x='(w-text_w)/2+5*sin(45*t)':y='h-h/3+3*cos(38*t)':"
                    f"alpha='if(lt(mod(t*17,1),0.82),1,0)':"
                    f"enable='between(t,{t0:.2f},{t1:.2f})'"
                )

        # ── ONE jump-scare white flash at the biggest reveal moment ──
        flash_frac = 0.65
        flash_t0 = flash_frac * audio_duration
        flash_t1 = flash_t0 + 0.15

        # ── Sound design: tension riser building into the flash, impact
        # hit exactly at it, a continuous low ambient dread drone under
        # the whole track, and quieter stinger hits at the 2 chromatic-
        # aberration beats (previously those had a visual glitch but no
        # matching audio cue at all). Untouched item from the free-tier
        # audit — previously zero sound design beyond generic ambient
        # noise. Can't fetch real sound libraries (not in the allowed
        # network), so all of this synthesizes real audio procedurally
        # via FFmpeg — each piece tested by actual render + volume
        # measurement before integrating, not assumed to work. (One
        # planned addition — a brief tension-dip/ducking beat right
        # before the flash — did NOT test cleanly and was dropped rather
        # than shipped unverified.)
        riser_start = max(0, flash_t0 - 2.5)
        riser_delay_ms = int(riser_start * 1000)
        impact_delay_ms = int(flash_t0 * 1000)

        stinger_filters = []
        stinger_labels = []
        for si, frac in enumerate(beat_fracs[:2]):
            t0 = max(0.5, frac * audio_duration)
            delay_ms = int(t0 * 1000)
            label = f"stinger{si}"
            stinger_filters.append(
                f"sine=frequency=55:duration=0.4,"
                f"afade=t=out:st=0.03:d=0.37,volume=1.4,"
                f"adelay={delay_ms}|{delay_ms}[{label}]"
            )
            stinger_labels.append(f"[{label}]")

        drone_duration = audio_duration + 1
        stinger_chain = ";".join(stinger_filters)
        stinger_inputs = "".join(stinger_labels)
        n_mix_inputs = 4 + len(stinger_labels)  # original + riser + impact + drone + stingers

        filter_complex = (
            f"[0:v]{','.join(video_filters)}[graded];"
            f"color=c=white:size=1280x720:rate=24[whitesrc];"
            f"[whitesrc]trim=duration={audio_duration:.2f},setpts=PTS-STARTPTS[wht];"
            f"[graded][wht]blend=all_expr='if(between(T,{flash_t0:.2f},{flash_t1:.2f}),B,A)':shortest=1[out];"
            f"aevalsrc=0.15*sin(2*PI*t*(80+220*t)):d=2.5:s=44100,"
            f"afade=t=in:d=0.3,afade=t=out:st=2.0:d=0.5,"
            f"adelay={riser_delay_ms}|{riser_delay_ms}[riser];"
            f"sine=frequency=65:duration=0.6,"
            f"afade=t=out:st=0.05:d=0.55,volume=3,"
            f"adelay={impact_delay_ms}|{impact_delay_ms}[impact];"
            f"sine=frequency=45:duration={drone_duration:.2f},"
            f"volume=0.06[drone];"
            f"{stinger_chain};"
            f"[1:a][riser][impact][drone]{stinger_inputs}amix=inputs={n_mix_inputs}:"
            f"duration=first:dropout_transition=0[mixedaudio]"
        )

        run_ffmpeg([
            "ffmpeg", "-y", "-i", video_path, "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "[mixedaudio]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-ar", "44100", output_path
        ], label="horror-fx", timeout=600)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 1_000_000:
            log(f"  Horror atmosphere FX applied: grain + {len(beat_fracs[:2])} glitch bursts + "
                f"1 jump-scare flash + {len(phrases)} unstable text beats")
            return output_path
        else:
            log("  Horror FX: output invalid — using un-treated video (non-fatal)")
            return video_path
    except Exception as e:
        log(f"  Horror atmosphere FX failed (non-fatal): {e}")
        return video_path


def assemble_video(niche_name, audio_path, audio_duration, topic, script="", episode=1):
    """Assemble final video: background footage + narration + ambient music
    + kinetic text overlays at key story beats (dark/atmospheric style,
    matched to niche — mix approach: animation for key beats, stock
    footage as backdrop)."""
    niche       = next(n for n in NICHES if n["name"] == niche_name)
    # FIX: this was calling get_background_video (ONE clip, looped for the
    # entire runtime) even though get_stage_matched_video (55-75 dynamically-
    # sized, sequential, audio-matched clips — already fully built and
    # working) existed in this same file and was never wired in. That's
    # exactly why the video showed "only one background the whole time."
    search_kw   = ""  # only used by the single-clip fallback below
    bg_path     = get_stage_matched_video(niche, script, audio_duration)
    if not bg_path:
        log("  Stage-matched video unavailable — falling back to single looped clip")
        bg_path = get_background_video(niche, audio_duration, search_kw)
    mus_path    = generate_ambient_music(audio_duration)
    composed    = compose_video(audio_path, bg_path, mus_path, None,
                                 audio_duration, label="main", niche_name=niche_name)

    if script:
        overlaid = str(WORK_DIR / "composed_horror_fx.mp4")
        composed = add_horror_atmosphere_fx(composed, script, audio_duration,
                                             niche_name, overlaid)

    # FIX (warbook v3 retention blueprint): removed the 2-second silent
    # black branded intro card that used to play BEFORE the cold open. That
    # was 2 full seconds of static text and dead silence at the exact
    # moment retention is most fragile — directly violates "no intro
    # branding, no throat-clearing" in the first 15 seconds. Replaced with
    # a small persistent corner watermark burned into the main video
    # instead, which preserves branding without costing any of the
    # critical opening seconds.
    watermark_text = niche["series"].replace("'", "").replace('"', "").replace(":", "")
    composed_watermarked = str(WORK_DIR / "composed_watermarked.mp4")
    run_ffmpeg([
        "ffmpeg", "-y", "-i", composed,
        "-vf", f"drawtext=text='{watermark_text}':fontsize=22:fontcolor=white@0.55:"
               f"x=w-text_w-20:y=20:borderw=1:bordercolor=black@0.4",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy", composed_watermarked
    ], label="watermark", timeout=300)
    if Path(composed_watermarked).exists() and Path(composed_watermarked).stat().st_size > 1_000_000:
        composed = composed_watermarked

    # FIX: create_outro's episode_num defaults to 1 and was never being
    # passed the real episode — same category of bug as the thumbnail
    # episode badge found earlier. Every outro card has shown
    # "Investigation #1" regardless of actual episode number.
    outro    = create_outro(niche["series"], episode)
    final    = str(WORK_DIR / "final.mp4")
    concat_parts([composed, outro], final)
    sz = Path(final).stat().st_size
    log(f"  Final video: {sz//(1024*1024)}MB")
    return final



def generate_thumbnail_text(niche, topic, title=""):
    """Generate 3-word NUMBER+NOUN style thumbnail text — matches the ACTUAL
    generated title's register (dread or sympathy), not an independent guess.
    FIX: the docstring here used to claim this matched the title generator,
    but the function never actually received the title at all — thumbnail
    and title registers could genuinely clash (e.g. sympathy title, dread
    thumbnail) since they were chosen completely independently."""
    fallback_bank = {
        "dark_horror":        ["LAST TAPE FOUND", "ROOM 307 SEALED", "SECOND VOICE HEARD",
                                "SHE LIED ALWAYS", "NOBODY EVER LISTENED"],
        "seduction_dark":     ["SEVEN WARNING SIGNS", "ONE TRAP CLOSED", "TWENTY EIGHT DAYS",
                                "ALL SHE WANTED", "COST HER EVERYTHING"],
        "psychological_trap": ["SIX STAGES FOUND", "NO EXIT EXISTS", "DOCUMENTED MIND CONTROL",
                                "EVERYONE BLAMED HIM", "TRUTH WAS WORSE"],
        "supernatural_real":  ["WITNESSES CONFIRMED THIS", "NINE NIGHTS RECORDED", "STILL UNEXPLAINED TODAY",
                                "ALONE THE WHOLE", "NOBODY CAME BACK"],
        "obsession_dark":     ["FOUR YEARS TRACKED", "EIGHT HUNDRED MESSAGES", "ONE PERSON KNEW",
                                "SHE WAS ALONE", "LAST DAYS UNSEEN"],
    }
    title_context = (
        f"\nTHE ACTUAL VIDEO TITLE (match its register exactly — if it's dread-driven,\n"
        f"the thumbnail must be dread-driven too; if it's sympathy/woeful, match that.\n"
        f"Do not clash with this title's tone): \"{title}\"\n"
        if title else ""
    )
    prompt = (
        f"Generate the most psychologically compelling 3-word thumbnail text "
        f"for a dark documentary video.\n"
        f"NICHE: {niche['name']} | TOPIC: {topic[:100]}\n"
        f"{title_context}\n"
        f"USE THESE TRIGGERS (pick ONE register, don't mix — and it MUST match\n"
        f"the title's register above if one is given):\n"
        f"1. CURIOSITY GAP: creates an unanswerable question\n"
        f"2. DREAD register: implies something disturbing was confirmed\n"
        f"3. SYMPATHY/WOEFUL register: implies someone was failed, ignored, or alone —\n"
        f"   equally valid as dread, use this roughly half the time\n"
        f"4. SPECIFICITY: a number or concrete detail, not vague\n"
        f"5. PATTERN INTERRUPT: unexpected — makes viewer stop scrolling\n\n"
        f"Rules: EXACTLY 3 words. ALL CAPS. Dark and specific. Never generic.\n"
        f"Return ONLY 3 words. Example: FOUND INSIDE WALLS or NOBODY EVER LISTENED"
    )
    try:
        result = ai_generate(prompt, tokens=15)
        if result:
            result = re.sub(r'[^A-Z\s]', '', result.upper()).strip()
            words  = result.split()[:3]
            if len(words) == 3:
                log(f"  Thumbnail: {' '.join(words)}")
                return ' '.join(words)
    except Exception as e:
        log(f"  Thumbnail text (non-fatal): {e}")
    return random.choice(fallback_bank.get(niche.get("name", "dark_horror"), fallback_bank["dark_horror"]))


def run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode):
    """Generate thumbnail with NUMBER+NOUN enforcement."""
    # Enforce NUMBER+NOUN format.
    # FIX: this used to be a bare `from revenue_engine import enforce_number_noun`
    # with no error handling — if revenue_engine.py isn't in the repo (it wasn't
    # among the files ever shared with me, and doesn't appear in the repo folder
    # listing), that import throws and takes down the ENTIRE generate run at
    # Stage 5, every single time. A local enforce_number_noun() already exists
    # in this same file (top of file) — fall back to it instead of crashing.
    try:
        from revenue_engine import enforce_number_noun as _enforce_number_noun
        thumb_text = _enforce_number_noun(thumb_text, topic, niche_name, ai_generate)
    except Exception as e:
        log(f"  revenue_engine unavailable, using built-in enforce_number_noun ({e})")
        thumb_text = enforce_number_noun(thumb_text, topic, niche_name, ai_generate)
    return generate_thumbnail(thumb_text, niche_name, title, topic, episode)


def build_niche_tags(niche_name):
    """Build SEO-optimised tag list for this niche."""
    base_tags = [niche_name.replace("_"," "), "documentary", "investigation",
                 "dark documentary", "true story", "psychological", "evidence",
                 "classified", "deepdive", "betrayal", "horror documentary",
                 "dark psychology", "real story", "mystery", "disturbing"]
    niche_specific = {
        "dark_horror":        ["dark horror","horror documentary","true horror"],
        "seduction_dark":     ["dark seduction","manipulation","psychology"],
        "psychological_trap": ["psychological","gaslighting","manipulation trap"],
        "supernatural_real":  ["supernatural","paranormal","unexplained"],
        "obsession_dark":     ["obsession","stalking","dark true story"],
    }
    return list(set(base_tags + niche_specific.get(niche_name, [])))[:15]


def ensure_playlist(token, niche_name, series_name):
    """Alias for ensure_niche_playlist."""
    return ensure_niche_playlist(token, niche_name, series_name)


def main():
    """
    Two-phase pipeline controller.
    PIPELINE_PHASE=generate : runs script/audio/video/thumbnail, saves pending_upload.json
    PIPELINE_PHASE=upload   : reads pending_upload.json, uploads to YouTube
    PIPELINE_PHASE=full     : legacy single-run mode (backward compatible)
    """
    from phase_manager import (get_pipeline_phase, save_pending,
                                load_pending, clear_pending, check_pending_age,
                                is_already_uploaded)

    phase = get_pipeline_phase()
    log("=" * 70)
    log(f"BETRAYAL DEEPDIVE v14.0 — Phase: {phase.upper()}")
    log(f"Time (IST): {datetime.datetime.now().strftime('%a %d %b %Y %I:%M %p')}")
    log("=" * 70)

    SCRIPT_DIR = Path(__file__).parent
    state = load_state()

    # ══════════════════════════════════════════════════════════
    # UPLOAD PHASE — reads pending_upload.json, uploads, done
    # ══════════════════════════════════════════════════════════
    if phase == "upload":
        pending = load_pending(SCRIPT_DIR)
        if not pending or is_already_uploaded(pending):
            tg("⚠️ Ch1 Upload: no pending video found. Generation may have failed last night.")
            log("No pending upload — exiting.")
            sys.exit(0)

        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch1 Upload: pending video is {hours_old}h old — may be stale. Uploading anyway.")

        log(f"Loading pending video ({hours_old}h old): {pending.get('title','?')[:60]}")
        title       = pending["title"]
        description = pending["description"]
        tags        = pending["tags"]
        niche_name  = pending["niche_name"]
        video_path  = pending["video_path"]
        topic       = pending.get("topic", title)  # FIX: was never extracted at all —
        # produce_recap_short's "main_topic" parameter needs the actual story
        # details to write a real recap script from ("pick the most jaw-
        # dropping reveal from the full story"); a bare title has none of
        # that. Falls back to title only if topic is somehow missing.
        thumb_path  = pending.get("thumbnail_path","")
        shorts      = pending.get("shorts_clips", [])
        script_clean= pending.get("script_clean","")
        duration    = pending.get("duration", 0)
        score       = pending.get("score", 0)
        edge_voice  = pending.get("voice_used","")
        episode     = pending.get("episode", 1)
        playlist_id = pending.get("playlist_id","")
        short_titles= pending.get("short_titles", {})
        short_cross = pending.get("short_cross", "")

        # Verify video file exists
        if not Path(video_path).exists():
            tg(f"❌ Ch1 Upload FAILED: video file missing at {video_path}")
            sys.exit(1)

        token = get_yt_token()

        # Upload main video
        yt_url, vid_id = run_stage_with_retry(
            upload_yt, "Upload",
            video_path, title, description, tags, token=token)

        # FIX: ensure_niche_playlist existed fully built but was never
        # called anywhere — playlist_id was always empty string (state
        # never had a real playlist ID to read), meaning add_to_playlist
        # below, despite being correctly wired, never actually fired.
        if not playlist_id:
            try:
                playlist_id = ensure_niche_playlist(token, niche_name, "BetrayalDeepDive")
                if playlist_id:
                    state.setdefault("playlists", {})[niche_name] = playlist_id
            except Exception as e:
                log(f"  Playlist creation (non-fatal): {e}")

        if playlist_id:
            add_to_playlist(token, playlist_id, vid_id)

        # Thumbnail
        if thumb_path and Path(thumb_path).exists():
            try:
                with open(thumb_path,"rb") as tf:
                    tr = requests.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={vid_id}&uploadType=media",
                        headers={"Authorization":f"Bearer {token}","Content-Type":"image/jpeg"},
                        data=tf.read(), timeout=60)
                if tr.status_code in [200,201]:
                    log("  Thumbnail uploaded")
                else:
                    # FIX: this used to fail completely silently — no log line
                    # at all on a non-200 response, which is exactly why a
                    # missing thumbnail was invisible in the logs. A common
                    # cause here is the channel not yet being verified for
                    # custom thumbnails (same "Intermediate features" gate as
                    # the 15-minute video length cap).
                    log(f"  Thumbnail upload FAILED: {tr.status_code} — {tr.text[:300]}")
                    tg(f"⚠️ Thumbnail upload failed ({tr.status_code}) — video published without "
                       f"a custom thumbnail. Check channel verification / Feature eligibility.")
            except Exception as te: log(f"  Thumbnail (non-fatal): {te}")

        post_creator_comment(token, vid_id, niche_name, title, episode)

        # FIX: shorts_reels_engine's produce_teaser_short/produce_standalone_short
        # already generate AND upload internally (they don't return a file to
        # upload separately) — those already went out during the generate
        # phase. The only Short that belongs here is the recap, because it's
        # the only one that needs the real video URL, which doesn't exist
        # until this exact point.
        short_urls = [s.get("url") for s in shorts if s.get("ok") and s.get("url")]
        try:
            import importlib.util
            if importlib.util.find_spec("shorts_reels_engine") is None:
                raise ImportError("shorts_reels_engine not in PYTHONPATH")
            from shorts_reels_engine import produce_recap_short
            recap = produce_recap_short(topic, yt_url, channel="betrayal_deepdive")
            if recap.get("status") == "success" and recap.get("url"):
                short_urls.append(recap["url"])
                # Reuses the already-available upload-phase token — no
                # extra OAuth call needed here, unlike the generate-phase
                # Shorts above.
                try:
                    import re as _re
                    m = _re.search(r'(?:shorts/|v=)([A-Za-z0-9_-]{11})', recap["url"])
                    if m:
                        post_short_creator_comment(token, m.group(1), niche_name, title)
                except Exception as e:
                    log(f"  Recap Short pinned comment (non-fatal): {e}")
            log(f"  Recap Short: {recap.get('status')}")
            log(f"  Total Shorts this episode: {len(short_urls)}")
        except Exception as e:
            log(f"  Recap Short (non-fatal): {e}")

        # SRT captions
        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token, vid_id, script_clean, duration, "betrayal_deepdive")
            except Exception as e:
                log(f"  SRT (non-fatal): {e} — using built-in approximate captions instead")
                try:
                    srt_path = str(WORK_DIR / "captions_approx.srt")
                    if generate_approximate_srt(script_clean, duration, srt_path):
                        upload_captions_track(token, vid_id, srt_path)
                except Exception as e2:
                    log(f"  Fallback captions also failed (non-fatal): {e2}")

        update_channel_description(token, title, yt_url)

        # Log this video's fingerprint to history NOW — only after a real,
        # confirmed publish, so a rejected/failed attempt never pollutes the
        # comparison history the authenticity checker relies on.
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
        # same discipline as above, only after confirmed real success.
        try:
            from site_generator import render_companion_page
            from publishing_archive import add_archive_entry, get_related_episodes

            # SCRIPT_DIR IS video_pipeline/ for Ch1 — repo root is 1 level up
            docs_root = SCRIPT_DIR.parent / "docs"
            related = get_related_episodes(SCRIPT_DIR, niche_name, exclude_episode_number=episode)

            page_path = render_companion_page(
                episode_data={
                    "episode_number": episode,
                    "episode_title": title,
                    "video_url": yt_url,
                    "channel_id": "betrayal_deepdive",
                    "niche_name": niche_name,
                    "publish_date": datetime.date.today().isoformat(),
                    "script_excerpt": script_clean[:600],
                    "related_links": related,
                },
                output_root=docs_root,
                ai_fn=lambda p, tokens=500: ai_generate(p, tokens=tokens),
            )
            if page_path:
                add_archive_entry(SCRIPT_DIR, {
                    "episode_number": episode,
                    "title": title,
                    "video_url": yt_url,
                    "niche_name": niche_name,
                    "topic": topic,
                    "companion_page_url": f"betrayaldeepdive/ep{episode}.html",
                })
                log(f"  Companion page generated: {page_path}")
            else:
                log("  Companion page generation skipped (non-fatal)")
        except Exception as e:
            log(f"  Companion page / archive (non-fatal): {e}")

        # Extract a genuine reusable insight into the right product
        # manuscript — same success-only timing as everything above.
        try:
            from product_manuscript import add_product_note
            products_root = SCRIPT_DIR.parent / "products"
            note = add_product_note(products_root, title, script_clean[:800],
                                      "betrayal_deepdive",
                                      lambda p, tokens=300: ai_generate(p, tokens=tokens))
            if note:
                log(f"  Product note added to '{note['chapter']}': {note['note_text'][:80]}")
            else:
                log("  Product note skipped (duplicate or extraction miss, non-fatal)")
        except Exception as e:
            log(f"  Product note extraction (non-fatal): {e}")

        clear_pending(SCRIPT_DIR)

        # Save state
        state["last_title"]    = title
        state["last_url"]      = yt_url
        state["last_voice"]    = edge_voice
        state["total_uploads"] = state.get("total_uploads", 0) + 1

        # FIX: save_pattern_memory existed fully built but was never
        # actually called anywhere — the pattern-memory system that
        # informs future script prompts with what's worked before was
        # reading from a permanently empty history. Wired in here, using
        # the real final score, right alongside the other state updates.
        # FIX: track_episode existed fully built but was never called —
        # without this, streak_below never incremented, meaning
        # pick_best_niche's auto-rotation logic could never actually
        # trigger no matter how many episodes underperformed.
        state = track_episode(state, niche_name, score, edge_voice, episode)

        state = save_pattern_memory(state, episode, niche_name, topic, score)

        # The unified audit search engine — ties script quality, real
        # authenticity risk, and provider health into one searchable
        # verdict per video, persisted for real historical search.
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
                tg(f"🚨 Ch1 AUDIT HOLD — Episode {episode}: {audit_result['reasons']}")
        except Exception as e:
            log(f"  Audit engine (non-fatal): {e}")

        save_state(state)

        # First-hour sprint
        try:
            # FIX: SPRINT_SCRIPT_PATH and SPRINT_PLAYLIST_ID were never set —
            # growth_engine.py gates its "update previous episode's pinned
            # comment" feature behind SPRINT_SCRIPT_PATH existing, so that
            # feature was silently disabled every single run. Both values
            # are already available here; just needed to actually pass them.
            sprint_script_path = str(WORK_DIR / "sprint_script.txt")
            try:
                Path(sprint_script_path).write_text(script_clean)
            except Exception:
                sprint_script_path = ""

            env_ext = os.environ.copy()
            env_ext.update({
                "GROWTH_ENGINE_MODE":  "sprint",
                "SPRINT_VIDEO_URL":    yt_url,
                "SPRINT_VIDEO_TITLE":  title,
                "SPRINT_CHANNEL_ID":   "betrayal_deepdive",
                "SPRINT_NICHE":        niche_name,
                "SPRINT_SHORTS_URLS":  ",".join(short_urls),
                "SPRINT_SCORE":        str(score),
                "SPRINT_DURATION_SECS":str(duration),
                "SPRINT_PLAYLIST_ID":  playlist_id or "",
                "SPRINT_SCRIPT_PATH":  sprint_script_path,
            })
            # FIX: this pointed at channels/growth_engine/growth_engine.py,
            # a path that doesn't exist — the real file lives right next to
            # master_pipeline.py. Because this uses Popen (fire-and-forget,
            # doesn't wait for or check the subprocess), the wrong path
            # failed silently INSIDE that separate process every single
            # time — python3 printed "can't open file" to its own stderr,
            # which nothing here ever captured or reported. This is very
            # likely the actual reason growth-engine features (hype
            # notifications, comment engine, CTR recovery) never visibly
            # ran, with zero error anywhere to point at.
            subprocess.Popen(
                ["python3", str(Path(__file__).parent / "growth_engine.py")],
                env=env_ext)
        except Exception as ge:
            log(f"  Growth engine sprint (non-fatal): {ge}")

        # v15: Hype notification — free Explore leaderboard push
        send_hype_push(yt_url, title, "BetrayalDeepDive", day=0)

        tg(f"✅ <b>BetrayalDeepDive — LIVE</b>\n\n"
           f"<b>{title}</b>\n🔗 {yt_url}\n\n"
           f"Niche: {niche_name} | Score: {score}/10\n"
           f"Ep{episode} | {len(short_urls)} Shorts uploaded\n"
           f"🚀 First-hour sprint active — watch + Hype now")
        log(f"\nUPLOAD COMPLETE: {yt_url}")
        return

    # ══════════════════════════════════════════════════════════
    # GENERATE PHASE (or legacy full mode)
    # ══════════════════════════════════════════════════════════
    episode = state.get("episode_count", 0) + 1
    if not IS_MAKEUP:
        ckpt_clear()

    try:
        # FIX: run_provider_health_check existed fully built (tests all 7
        # providers, hard-stops if all fail, alerts if fewer than 3 work)
        # but was NEVER actually called anywhere — cascading provider
        # failures went completely undetected until the whole run failed
        # deep into script generation instead of being caught upfront.
        _healthy_providers = run_provider_health_check()

        # token obtained at upload time — not needed for script generation

        log("\nSTAGE 1: Script")
        niche_name, niche, topic, script_result, trending_titles = run_stage1(state)

        # Find the backlog ID for this topic, if it came from an approved
        # entry — looked up by matching topic text rather than changing
        # run_stage1's return signature (safer, avoids touching every
        # call site of an already-established function).
        _approved_topic_id_for_pending = None
        try:
            from topic_scoring import load_topic_database
            for _t in load_topic_database(SCRIPT_DIR):
                if _t.get("topic_text") == topic and _t.get("status") == "approved":
                    _approved_topic_id_for_pending = _t["topic_id"]
                    break
        except Exception as e:
            log(f"  Topic ID lookup (non-fatal): {e}")
        script_clean = script_result["script"]
        wc           = script_result["words"]
        score_val    = score_result(script_result)[0]
        edge_voice   = pick_voice(niche_name, state)

        tg(f"Ch1 Script ready: {niche_name} | {wc}w | {score_val}/10\n{topic[:80]}")

        # Approval gate
        # FIX: generate_titles's dread/sympathy alternation reads
        # state["last_title_register"] to decide which register to use next —
        # but state was never being passed in here, so it always saw state=None
        # and always computed the same register, every single episode. The
        # alternation looked implemented but never actually alternated.
        title_result = run_stage_with_retry(generate_titles, "Titles", niche, topic, episode, state, trending_titles)
        title        = title_result if title_result else f"{niche['series']} Ep{episode}"

        decision = run_approval_gate(title, niche_name, script_clean, edge_voice, score_val)
        if decision == "rejected":
            log("Rejected by approval gate."); sys.exit(0)

        log("\nSTAGE 3: Audio")
        audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
            run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
        edge_voice = voice_used

        # STRICTER AUDIO GATE — explicit decision made after real discussion
        # about video quality standards: previously the pipeline would fall
        # all the way to espeak-ng and still auto-publish, trading "always
        # publishes something" for a genuinely robotic voice reaching real
        # viewers. This flips that tradeoff — gTTS or espeak specifically
        # now HOLDS the video and alerts for manual review, rather than
        # publishing something below the stated bar. ElevenLabs, edge-tts,
        # and Fish Audio all still auto-publish normally; only the two
        # noticeably robotic tiers trigger a hold.
        if edge_voice in ("gtts-fallback", "espeak-offline-LASTRESORT"):
            tg(f"🛑 Ch1 HOLD — audio fell back to {edge_voice}, below the stated voice-quality "
               f"bar. This episode is NOT being published automatically. Review the audio, or "
               f"manually approve if it's acceptable, then re-run.\n\nTitle: {title}")
            log(f"  HOLD: audio tier {edge_voice} is below the auto-publish bar. Stopping here.")
            sys.exit(0)

        # FIX: check_audio_quality existed fully built (validates real file
        # size AND real measured duration against what the script's word
        # count implies) but was never called anywhere — a truncated or
        # corrupted audio file could silently reach video assembly undetected.
        _expected_dur = (len(script_clean.split()) / 125.0) * 60.0
        if not check_audio_quality(audio_path, _expected_dur):
            tg(f"⚠️ Ch1 audio quality check failed — expected ~{_expected_dur:.0f}s, "
               f"got {audio_duration:.0f}s. Proceeding, but this episode's audio needs review.")

        log("\nSTAGE 4: Video")
        video_path = run_stage_with_retry(
            assemble_video, "Video", niche_name, audio_path, audio_duration, topic, script_clean, episode)

        log("\nSTAGE 5: Thumbnail")
        ab_style    = "A" if datetime.datetime.now().isocalendar()[1] % 2 == 1 else "B"
        thumb_text  = generate_thumbnail_text(niche, topic, title)
        thumb_path  = run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode)

        log("\nSTAGE 5.5: Authenticity / Policy-Risk Check")
        _auth_score = 10.0  # safe default — always defined even if the check below fails entirely
        try:
            from authenticity_guard import run_authenticity_check, save_fingerprint_record, format_authenticity_report
            # Replicate thumbnail_engine_v2's exact seed formula so the family/
            # pose logged here match what actually got rendered, without
            # needing that module to return them explicitly.
            _thumb_seed = abs(hash(f"{title}{niche_name}{episode}")) % 99999
            try:
                from thumbnail_engine_v2 import NICHE_PROFILES as _NICHE_PROFILES
                _families = _NICHE_PROFILES.get(niche_name, {}).get("thumbnail_families", [])
            except Exception:
                _families = []
            thumb_family = (_families[datetime.datetime.now().timetuple().tm_yday % len(_families)]
                            if _families else "unknown")
            thumb_pose_slots = 8  # matches CHANNEL_AVATARS pose_variations length
            thumb_pose_id = f"pose_slot_{_thumb_seed % thumb_pose_slots}"

            auth_result = run_authenticity_check(
                channel_dir=SCRIPT_DIR,
                script_clean=script_clean,
                stage_texts=script_result.get("stage_texts", []),
                title=title,
                thumbnail_family=thumb_family,
                thumbnail_pose=thumb_pose_id,
                ai_fn=lambda p, tokens=100: ai_generate(p, tokens=tokens),
            )
            log(format_authenticity_report(auth_result, "Ch1"))
            _auth_score = auth_result["composite_score"]
            if _auth_score < 6.0:
                tg(f"🚨 Ch1 AUTHENTICITY RISK — score {_auth_score}/10, below the safe threshold.\n"
                   f"{format_authenticity_report(auth_result, 'BetrayalDeepDive')}\n"
                   f"Recommend manual review before this publishes.")
            elif _auth_score < 7.5:
                tg(f"⚠️ Ch1 authenticity check: {_auth_score}/10 — one dimension is weak, publishing "
                   f"but flagging for awareness.\n{format_authenticity_report(auth_result, 'BetrayalDeepDive')}")
            # Fingerprint gets saved to history only in the upload phase, after
            # a real publish is confirmed — see phase="upload" section below.
            _pending_auth_fingerprint = auth_result["_fingerprint_to_log"]
        except Exception as e:
            log(f"  Authenticity check (non-fatal): {e}")
            _pending_auth_fingerprint = None

        log("\nSTAGE 6: Shorts")
        log("  Teaser (ties to main video) + 2 standalone Shorts now.")
        log("  Recap Short runs in the upload phase — it needs the real")
        log("  video URL, which doesn't exist until upload actually happens.")
        # FIX: this used to import a module called "shorts_engine" that
        # doesn't exist — the real file is "shorts_reels_engine.py", and its
        # actual functions (produce_teaser_short, produce_recap_short,
        # produce_standalone_short) are completely different from the
        # generate_all_six_shorts() this code assumed existed. That
        # combination guaranteed this always failed. Wired to the real API now.
        shorts = []
        try:
            import importlib.util
            if importlib.util.find_spec("shorts_reels_engine") is None:
                raise ImportError("shorts_reels_engine not in PYTHONPATH")
            from shorts_reels_engine import produce_teaser_short, produce_standalone_short

            teaser = produce_teaser_short(topic, script_clean, channel="betrayal_deepdive")
            shorts.append({"ok": teaser.get("status") == "success",
                           "path": None, "url": teaser.get("url"), "name": "teaser"})
            log(f"  Teaser: {teaser.get('status')}")

            # FIX: post_short_creator_comment existed fully built (drives
            # real early-engagement signals via a pinned comment on each
            # Short) but was never called anywhere — the actual active
            # Shorts system (shorts_reels_engine.py) has zero pinned-
            # comment capability of its own, so this was a genuine gap,
            # not superseded code. Fetches its own token here since this
            # runs in the generate phase, before the real upload-phase
            # OAuth flow.
            def _post_short_comment_safe(short_url, mode_name):
                if not short_url:
                    return
                try:
                    import re as _re
                    m = _re.search(r'(?:shorts/|v=)([A-Za-z0-9_-]{11})', short_url)
                    if not m:
                        return
                    _short_token = get_yt_token()
                    post_short_creator_comment(_short_token, m.group(1), niche_name, title)
                except Exception as e:
                    log(f"  Short pinned comment ({mode_name}, non-fatal): {e}")

            _post_short_comment_safe(teaser.get("url"), "teaser")

            for mode in ("standalone_1", "standalone_2"):
                sa = produce_standalone_short(mode, channel="betrayal_deepdive")
                # FIX: produce_standalone_short returns its URL under the key
                # "yt_url", inconsistent with produce_teaser_short/
                # produce_recap_short which both use "url" — this was
                # silently returning None here every time, even on success,
                # dropping standalone Shorts from every downstream count.
                shorts.append({"ok": sa.get("status") == "success",
                               "path": None, "url": sa.get("yt_url"), "name": mode})
                log(f"  Standalone ({mode}): {sa.get('status')}")
                _post_short_comment_safe(sa.get("yt_url"), mode)

            ok_count = sum(1 for s in shorts if s.get("ok"))
            log(f"  Shorts (generate phase): {ok_count}/{len(shorts)} generated")
        except Exception as e:
            log(f"  Shorts engine (non-fatal): {e} — using built-in FFmpeg fallback instead")
            try:
                shorts = generate_basic_shorts(video_path, audio_duration, title,
                                                niche_name, str(WORK_DIR))
                ok_count = sum(1 for s in shorts if s.get("ok"))
                log(f"  Fallback Shorts: {ok_count}/{len(shorts)} generated")
                tg(f"  Shorts (fallback): {ok_count}/{len(shorts)} generated")
            except Exception as e2:
                log(f"  Fallback Shorts also failed (non-fatal): {e2}")
                shorts = []

        # Build description
        description = generate_seo_description(
            niche, topic, title, episode,
            generate_chapter_timestamps(script_clean, audio_duration, "betrayal_deepdive"),
            audio_duration)

        # FIX: build_affiliate_block existed in this file but was NEVER
        # actually called anywhere — genuinely dead code, meaning every
        # Ch1 video published so far has been missing real affiliate
        # income entirely, while Ch2 had this correctly wired in. Real
        # income infrastructure that existed but was never connected.
        affiliate_block = build_affiliate_block("betrayal_deepdive", niche_name)
        if affiliate_block:
            description = f"{description}{affiliate_block}"

        # Playlist
        # Playlist created at upload time (YouTube creds not in generate phase)
        playlist_id = state.get("playlists", {}).get(niche_name, "")

        tags = build_niche_tags(niche_name)

        # Validate video before saving to pending
        if not Path(video_path).exists():
            tg("Ch1 Generate FAILED: video file not created")
            sys.exit(1)
        v_sz = Path(video_path).stat().st_size
        if v_sz < 5_000_000:
            tg(f"Ch1 Generate FAILED: video too small ({v_sz//1024}KB)")
            sys.exit(1)
        log(f"  Video validated: {v_sz//(1024*1024)}MB")

        # Save pending (generate phase ends here)
        _pending_result = save_pending(SCRIPT_DIR, {
            "title":         title,
            "description":   description,
            "tags":          tags,
            "niche_name":    niche_name,
            "video_path":    video_path,
            "audio_path":    audio_path,
            "thumbnail_path":thumb_path or "",
            "script_clean":  script_clean,
            "duration":      audio_duration,
            "score":         score_val,
            "voice_used":    voice_used,
            "episode":       episode,
            "playlist_id":   playlist_id or "",
            "ab_style":      ab_style,
            "shorts_clips":  shorts,   # full 6-Short list from shorts_engine
            "topic":         topic,
            "auth_fingerprint": _pending_auth_fingerprint,
            "approved_topic_id": _approved_topic_id_for_pending,
            "quality_attempt": script_result.get("attempt", 1),
            "providers_healthy_count": len(_healthy_providers) if _healthy_providers else 7,
            "authenticity_score": _auth_score,
        })
        if _pending_result.get("overwrite_warning"):
            tg(f"🚨 Ch1 Generate: {_pending_result['overwrite_warning']}")

        state["episode_count"] = episode
        save_state(state)

        if phase == "generate":
            # Find upload time for this channel
            upload_time_msg = "10:30 PM IST (5 PM UTC)"
            tg(f"✅ <b>Ch1 Generated — queued for upload</b>\n\n"
               f"<b>{title}</b>\n"
               f"Niche: {niche_name} | {wc}w | {score_val}/10\n"
               f"Voice: {voice_used} | {audio_duration/60:.1f}min\n"
               f"Uploading at: {upload_time_msg}\n\n"
               f"🎯 Reply CANCEL to abort upload before that time.")
            log(f"\nGENERATE COMPLETE — video queued for upload at {upload_time_msg}")
            return

        # Legacy full mode: upload immediately
        log("\nLEGACY FULL MODE: uploading now...")
        os.environ["PIPELINE_PHASE"] = "upload"
        main()  # re-enter in upload phase

    except Exception as e:
        log(f"\nFAILED: {e}")
        tg(f"❌ <b>Ch1 Pipeline FAILED</b>\n\n{str(e)[:400]}")
        raise


if __name__ == "__main__":
    main()
