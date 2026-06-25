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
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n🧠 Psychology documentaries: youtube.com/@TheControlFiles\n\n📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "evidence_room": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology documentaries: youtube.com/@TheControlFiles\n\n📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n\n📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🌑 Dark horror: youtube.com/@BetrayalDeepDive",
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
            timeout=15)
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
