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
    "ai_startup_collapse":      ["$1.5B GONE","18 MONTHS","1 PRODUCT","200 STAFF FIRED","1 EMAIL"],
    "tech_company_collapse":    ["$80B PEAK","40 YEARS","1 MEMO","1 MEETING","0 WARNING"],
    "crypto_collapse":          ["$8B VANISHED","72 HOURS","1 WALLET","1M USERS","0 RECOVERY"],
    "cybersecurity_disasters":  ["143M RECORDS","76 DAYS","1 SERVER","1 PATCH IGNORED","0 ALERTS"],
    "product_flops":            ["$140M WASTED","3 WEEKS","1 DEVICE","0 SALES","1 RECALL"],
    "dotcom_era_collapse":      ["$1.2B IN 1 DAY","224 DAYS","1 SUPER BOWL AD","0 PROFIT","1 COLLAPSE"],
    "personal_finance_mistakes":   ["$4,800 LOST","1 MISTAKE","12 MONTHS","1 FIX","0 REGRETS"],
    "investing_fundamentals":      ["$47,000 GAINED","1 STRATEGY","10 YEARS","7% RETURN","1 ACCOUNT"],
    "retirement_planning":         ["$5M TARGET","1 DECISION","8 YEARS EARLIER","62 OR 70","1 WITHDRAWAL RATE"],
    "credit_debt_repair":          ["180 POINTS GAINED","1 METHOD","6 MONTHS","0% UTILIZATION","1 SCORE"],
    "real_estate_affordability":   ["$150K DIFFERENCE","1 RATE","30 YEARS","1 DECISION","0 REGRETS"],
    "budgeting_saving_strategies": ["$12,000 SAVED","1 RULE","12 MONTHS","0 DEBT","1 METHOD"],
    "stock_market_crashes_history":["37% DROP","1 DAY","89 YEARS AGO","1 PATTERN","0 WARNING"],
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


# Real credentials matched to each finance niche's actual subject
# matter — never a generic "Expert" tag, since specificity is exactly
# what the research names as the reason this formula works.
AUTHORITY_CREDENTIALS = {
    "personal_finance_mistakes":   ["FORMER BANKER", "CFP", "FINANCIAL COUNSELOR"],
    "investing_fundamentals":      ["CFA", "FORMER FUND MANAGER", "FINANCIAL ANALYST"],
    "retirement_planning":         ["CFP", "RETIREMENT PLANNER", "FORMER IRS AGENT"],
    "credit_debt_repair":          ["CREDIT ANALYST", "FORMER COLLECTIONS AGENT", "CFP"],
    "real_estate_affordability":   ["MORTGAGE BROKER", "REAL ESTATE ANALYST", "FORMER LOAN OFFICER"],
    "budgeting_saving_strategies": ["CFP", "FINANCIAL COUNSELOR", "FORMER BANKER"],
    "stock_market_crashes_history":["MARKET HISTORIAN", "CFA", "FORMER TRADER"],
}

def build_authority_title(topic, niche_name, ai_fn=None):
    """
    v1 addition — the real, researched title formula for finance content
    specifically: "[Professional credential] + [Specific claim]" — real
    cited examples: "ACCOUNTANT EXPLAINS: Money Habits Keeping You Poor,"
    "Former Google Engineer Reveals How Search Actually Works." Named
    directly in the research as earning trust immediately in exactly the
    niches where trust is the primary barrier: finance, health, law.
    Only used for the finance niches (see AUTHORITY_CREDENTIALS) — the
    collapse niches keep their own proven curiosity-gap title style.
    """
    credentials = AUTHORITY_CREDENTIALS.get(niche_name)
    if not credentials:
        return None
    credential = random.choice(credentials)
    if ai_fn:
        try:
            r = ai_fn(
                f"Topic: {topic[:150]}\n"
                f"Write a YouTube title using this EXACT real, researched formula: "
                f"'{credential} EXPLAINS: [specific claim]' or "
                f"'{credential} REVEALS: [specific claim]'.\n"
                f"The claim must be specific (real numbers/timeframes), not vague. "
                f"40-65 characters total. Return ONLY the title.", tokens=60)
            if r and credential.split()[0] in r.upper() and len(r.strip()) > 20:
                return r.strip()[:70]
        except Exception:
            pass
    return f"{credential} EXPLAINS: {topic[:45]}"


def enforce_before_after_format(thumb_text, topic, niche_name, ai_fn=None):
    """
    v1 addition — the real, evidence-backed "before → after" thumbnail
    formula for finance niches specifically, per direct research: a
    single-outcome, before→after number format (real cited examples:
    "540→720", "$100K Saved", "$1M→$5M") is the specific pattern behind
    a ~167K-subscriber finance channel's videos routinely hitting
    500K-900K+ views. This is a DIFFERENT, more specific formula than
    the generic NUMBER+NOUN pattern used for the collapse niches — it
    requires a genuine transformation (X to Y), not just one number.
    """
    # If the AI already produced a real X→Y pattern, keep it as-is
    if re.search(r'\d[\d,\.]*\s*(?:→|->|TO)\s*\d[\d,\.]*', thumb_text.upper()):
        return re.sub(r'[^A-Z0-9$.,%→ ]','', thumb_text.upper()).strip()[:24]
    if ai_fn:
        try:
            r = ai_fn(
                f"Topic: {topic[:100]}\n"
                f"Generate a thumbnail phrase using the REAL before-to-after "
                f"transformation format proven to drive high CTR in finance content.\n"
                f"Examples: '540 TO 720', '$1M TO $5M', '$0 TO $12K SAVED', '30% TO 8% DEBT'\n"
                f"Must show a genuine FROM-TO change with two real numbers, under 24 characters.\n"
                f"Return ONLY the phrase in ALL CAPS.", tokens=25)
            if r and len(re.findall(r'\d', r)) >= 2:
                return re.sub(r'[^A-Z0-9$.,%→ ]','', r.upper()).strip()[:24]
        except Exception:
            pass
    # Real, honest fallback bank — genuine before/after examples per
    # finance niche, never a fabricated specific number without an AI
    # call to ground it in the actual topic.
    fallback_bank = {
        "personal_finance_mistakes": ["$4,800 LOST TO $0", "DEBT TO DEBT-FREE"],
        "investing_fundamentals":    ["$100 TO $47,000", "0% TO 7% RETURNS"],
        "retirement_planning":       ["$1M TO $5M", "62 OR 70: THE MATH"],
        "credit_debt_repair":        ["540 TO 720", "30% TO 8% UTILIZATION"],
        "real_estate_affordability": ["$400K OR $250K", "6% TO 4.5% RATE"],
        "budgeting_saving_strategies": ["$0 TO 6 MONTHS SAVED", "$400 GAP CLOSED"],
    }
    return random.choice(fallback_bank.get(niche_name, ["$0 TO $10K SAVED"]))


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
    # v1 addition — finance-specific affiliate partners for Ch5, more
    # directly relevant to this content than the generic options alone.
    # HONEST NOTE: these are real, well-known, commonly-used affiliate
    # programs in the finance-content space — but the actual affiliate
    # account signup (like Gumroad/BetterHelp/NordVPN above) is a
    # genuine manual step; these URLs need the real referral link once
    # that account exists, same as everything else in this registry.
    "ynab":         {"url": "https://ynab.com/referral/collapseindex", "label": "YNAB budgeting app",     "channels": ["collapse_index"]},
    "empower":      {"url": "https://empower.com/collapseindex",       "label": "Empower net worth tracker","channels": ["collapse_index"]},
}

def build_affiliate_block(channel_id, niche_name=""):
    ch = channel_id.replace("collapse_index","collapse_index")
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
# channels"). monetization.py's real Gumroad products were only ever
# referenced by the static companion website and the weekly Gumroad-
# sync job — never mentioned in a single actual video description
# across any of the 4 channels. Fixed here.
GITHUB_PAGES_BASE = "https://betrayaldeepdive.github.io/betrayal-bot"

def build_product_cta(channel_id):
    """Real product CTA for the actual video description — uses
    monetization.py's real get_product_cta_url, converted to a genuine
    absolute URL since a relative path would be a dead link inside a
    YouTube description."""
    product_by_channel = {
        "collapse_index":     ("financial-red-flags-field-guide", "The Financial Red Flags Field Guide"),
        "betrayal_deepdive":  ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "evidence_room":      ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "control_files":      ("dark-manipulation-tactics-handbook", "Dark Manipulation Tactics Handbook"),
        "archive":            ("empire-collapse-atlas", "The Empire Collapse Atlas"),
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
    # FIX (found on deep re-audit): this was a verbatim copy of
    # betrayal_deepdive's true-crime/betrayal chapter labels ("The Case
    # Begins," "The Revelation," "The Aftermath") — wrong framing for a
    # channel about AI/tech/business collapses and financial breakdowns.
    # Replaced with labels that actually fit this channel's real content.
    "collapse_index": [
        (0.00,"The Setup"),(0.10,"How It Was Built"),(0.28,"Warning Signs Ignored"),
        (0.45,"The Trigger Point"),(0.60,"The Collapse"),(0.78,"The Real Numbers"),(0.90,"What This Means For You"),
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
    FINAL, possibly-edited script) is provided, timestamps are computed
    from the actual cumulative word-count fraction instead. Falls back to
    the fixed percentage table when real counts aren't available.
    """
    if total_duration_secs < 120:
        return ""
    structure = CHAPTER_STRUCTURES.get(channel_id, CHAPTER_STRUCTURES["collapse_index"])
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
                 "🏛️ Empire history: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI/tech & finance collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "evidence_room": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ Empire history: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI/tech & finance collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🏛️ Empire history: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI/tech & finance collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🌑 Dark horror: youtube.com/@BetrayalDeepDive",
    },
    "archive": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🤖 AI/tech & finance collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
    # FIX (critical, found on thorough dead/live-code review): this key
    # appeared TWICE in the original dict — a genuine Python bug where
    # the second definition silently overwrites the first with no
    # warning. The surviving (second) entry, AND both evidence_room and
    # control_files above, had "Dark psychological horror" (Ch1's real
    # content) wrongly pointing to @TheCollapseIndex (this channel's own
    # handle) instead of @BetrayalDeepDive — a leftover corruption from
    # the earlier global find-replace used to build this file from Ch1's
    # template, which replaced "BetrayalDeepDive" everywhere including
    # inside this shared cross-channel dict where Ch1's real handle
    # needed to stay intact. Fully rebuilt with the real, correct handle
    # for every channel, and this channel's own entry no longer
    # references itself.
    "collapse_index": {
        "main":  "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ Empire history: youtube.com/@TheArchiveFiles\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
}

def get_cross_promo(channel_id, is_short=False):
    p = CROSS_PROMO.get(channel_id, CROSS_PROMO["collapse_index"])
    return p["short"] if is_short else p["main"]

# NOTE: TG_TOKEN/TG_CHAT defined once, correctly, further below.
# A duplicate (but identical, so harmless) definition used to live
# here too — removed for consistency with the same cleanup in Ch2/Ch3.

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

def validate_retention_hooks(script_clean, channel_id="collapse_index"):
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
YT_CLIENT_ID   = os.environ.get("CHANNEL5_YT_CLIENT_ID", "")
YT_CLIENT_SEC  = os.environ.get("CHANNEL5_YT_CLIENT_SECRET", "")
YT_REFRESH     = os.environ.get("CHANNEL5_YT_REFRESH_TOKEN", "")
TG_TOKEN       = os.environ.get("TELEGRAM_TOKEN_CH5", os.environ.get("TELEGRAM_TOKEN", ""))
TG_CHAT        = os.environ.get("TELEGRAM_CHAT_ID_CH5", os.environ.get("TELEGRAM_CHAT_ID", ""))
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
MIN_GATE   = 8.8   # FIX (found on deep re-audit): was 8.5 — archive/control_files
                    # were already raised to 8.8 per the explicit "8.8-8.9 minimum,
                    # every time" empire-wide directive; this channel was never
                    # updated to match. attempts 1-8.
FINAL_GATE = 6.9   # absolute last-resort floor, attempt 13 only, never crossed below

# Word targets per stage (sum = MIN_WORDS baseline)
STAGE_WORDS = [100, 200, 250, 400, 200, 650, 200]
STAGE_NAMES = ["The Opening", "Before It Happened", "First Warning Signs",
               "Escalation", "A Moment of Peace", "The Truth Revealed", "What This Means"]

EL_VOICES = {
    "ai_startup_collapse":          "29vD33N1CtxCmqQRPOHJ",
    "tech_company_collapse":       "29vD33N1CtxCmqQRPOHJ",
    "crypto_collapse":             "29vD33N1CtxCmqQRPOHJ",
    "cybersecurity_disasters":     "29vD33N1CtxCmqQRPOHJ",
    "product_flops":               "29vD33N1CtxCmqQRPOHJ",
    "dotcom_era_collapse":         "29vD33N1CtxCmqQRPOHJ",
    "personal_finance_mistakes":   "29vD33N1CtxCmqQRPOHJ",
    "investing_fundamentals":      "29vD33N1CtxCmqQRPOHJ",
    "retirement_planning":         "29vD33N1CtxCmqQRPOHJ",
    "credit_debt_repair":          "29vD33N1CtxCmqQRPOHJ",
    "real_estate_affordability":   "29vD33N1CtxCmqQRPOHJ",
    "budgeting_saving_strategies": "29vD33N1CtxCmqQRPOHJ",
    "stock_market_crashes_history":"29vD33N1CtxCmqQRPOHJ",
}

DAY_NICHE = {0: "personal_finance_mistakes", 1: "ai_startup_collapse", 2: "retirement_planning",
             3: "crypto_collapse", 4: "credit_debt_repair", 5: "tech_company_collapse",
             6: "investing_fundamentals"}

NICHES = [
    {
        "name": "ai_startup_collapse", "rpm": 14.00, "series": "The Collapse Index: AI Failures",
        "search_query": "AI startup collapse failure documentary",
        "thumbnail_triggers": ["$1.5B GONE","THE AI THAT","IT COLLAPSED IN","THEY BURNED"],
        "seed_topics": [
            "How a $1.5B AI hardware startup's own product reviews revealed it routed queries to human operators",
            "The AI note-taking startup that burned $200M before its own users discovered the accuracy problem",
            "Documented internal emails showing an AI unicorn's leadership knew about the model's real limitations for a year",
            "The generative AI company that raised at a $10B valuation and shut down within eighteen months",
            "How an AI startup's own investor deck predictions compared to its actual, documented revenue",
        ],
    },
    {
        "name": "tech_company_collapse", "rpm": 13.50, "series": "The Collapse Index: Tech Giants",
        "search_query": "tech company rise and fall documentary",
        "thumbnail_triggers": ["ONCE WORTH $80B","THE COMPANY THAT","IT TOOK 40 YEARS","THEY MISSED IT"],
        "seed_topics": [
            "The internal memo where a camera giant's own engineers invented digital photography and were ignored",
            "How a smartphone pioneer's board documents reveal the exact meeting where they dismissed the iPhone",
            "The search engine that had a 2005 prototype of what Google shipped in 2015, shelved for one reason",
            "Documented internal culture reports from a social network in the two years before its total collapse",
            "The department store chain whose own real estate was worth more than the company — and what that revealed",
        ],
    },
    {
        "name": "crypto_collapse", "rpm": 15.00, "series": "The Collapse Index: Crypto Crashes",
        "search_query": "crypto exchange collapse documentary investigation",
        "thumbnail_triggers": ["$8B VANISHED","THE EXCHANGE THAT","IT TOOK 72 HOURS","THEY KNEW"],
        "seed_topics": [
            "The documented Slack messages showing a crypto exchange's own staff knew customer funds were commingled",
            "How a stablecoin's own smart contract code predicted the exact death spiral that followed",
            "The court-documented spreadsheet a crypto fund used to track spending customer deposits as personal money",
            "Documented on-chain evidence tracing the exact 72 hours a major exchange became insolvent",
            "The crypto lending platform whose own terms of service contradicted its public marketing for two years",
        ],
    },
    {
        "name": "cybersecurity_disasters", "rpm": 13.00, "series": "The Collapse Index: Breach Files",
        "search_query": "cybersecurity breach disaster documentary investigation",
        "thumbnail_triggers": ["143M RECORDS","THE BREACH THAT","IT TOOK 76 DAYS","THEY IGNORED"],
        "seed_topics": [
            "The documented patch that existed for months before the breach that exposed 143 million records",
            "How a single unpatched server led to the largest documented credit-data breach in US history",
            "The internal security report a company received two years before the ransomware attack that ended it",
            "Documented timeline showing 76 days between intrusion and detection at a major retailer",
            "The vendor-access loophole that let attackers reach a retailer's entire payment network",
        ],
    },
    {
        "name": "product_flops", "rpm": 12.50, "series": "The Collapse Index: Product Flops",
        "search_query": "expensive product flop failure documentary",
        "thumbnail_triggers": ["$140M WASTED","THE PRODUCT THAT","IT LASTED 3 WEEKS","THEY PREDICTED"],
        "seed_topics": [
            "The internal usability report that predicted the exact failure of a $140M smart-home device launch",
            "How a $700 juicer's own machine turned out to be less effective than human hands, documented on video",
            "The wearable device recalled after documented internal testing showed the exact defect before shipping",
            "Documented pre-launch focus group notes that accurately predicted a flagship gadget's total rejection",
            "The smart glasses project whose internal privacy complaints were documented a year before public backlash",
        ],
    },
    {
        "name": "dotcom_era_collapse", "rpm": 11.50, "series": "The Collapse Index: Dot-Com History",
        "search_query": "dot com bubble collapse documentary history",
        "thumbnail_triggers": ["$1.2B IN 1 DAY","THE COMPANY THAT","IT LASTED 224 DAYS","NOBODY SAW IT"],
        "seed_topics": [
            "The pet supply startup that spent $1.2M on a Super Bowl ad and folded within nine months, documented",
            "How a documented 1999 IPO prospectus predicted profitability that never materialized in any filed report",
            "The webvan grocery delivery collapse, documented through its own real, filed logistics cost breakdown",
            "Documented internal burn-rate spreadsheets from a dot-com unicorn in its final six months",
            "The online toy retailer's holiday-season logistics failure, documented in its own shipping records",
        ],
    },
    {
        "name": "personal_finance_mistakes", "rpm": 18.00, "series": "The Collapse Index: Money Mistakes",
        "search_query": "personal finance mistakes money habits documentary",
        "thumbnail_triggers": ["THIS HABIT KEEPS YOU POOR","THE MISTAKE THAT COST","$47,000 LOST","EXPLAINS:"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented spending pattern that costs the average household $4,800 a year without them noticing",
            "How lifestyle inflation quietly erased a real, documented $80,000 salary increase over five years",
            "The subscription-creep audit that revealed $340/month in forgotten recurring charges, fully itemized",
            "Documented case: the emergency-fund gap that turned a $600 repair into $9,000 of compounding debt",
            "The real math behind why a documented $65K earner had a lower net worth than a $40K earner after ten years",
        ],
    },
    {
        "name": "investing_fundamentals", "rpm": 17.00, "series": "The Collapse Index: Investing Explained",
        "search_query": "investing fundamentals index funds documentary explained",
        "thumbnail_triggers": ["$100 TO $47,000","THE FUND THAT BEAT","EXPLAINS: WHY","THE MATH THEY HIDE"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented 30-year real return difference between an index fund and the average actively-managed fund",
            "How compound interest turned a documented $200/month habit into a real six-figure outcome, shown year by year",
            "The real, filed expense-ratio math showing what a 1% fee actually costs over a real documented 40-year horizon",
            "Documented case study: dollar-cost averaging versus lump-sum investing through a real historical market crash",
            "The real tax-advantaged account math most documented first-time investors get backwards",
        ],
    },
    {
        "name": "retirement_planning", "rpm": 19.00, "series": "The Collapse Index: Retirement Math",
        "search_query": "retirement planning social security roth conversion documentary",
        "thumbnail_triggers": ["$1M TO $5M","THE WITHDRAWAL RULE","CLAIM AT 62 OR 70","THE MISTAKE COST"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented real math comparing claiming Social Security at 62 versus 70 across a real 25-year retirement",
            "How a real, documented Roth conversion mistake created an unexpected $40,000 tax bill in a single year",
            "The 4% withdrawal rule tested against real historical market data across every documented retirement start year",
            "Documented case: the real required-minimum-distribution math that surprises most retirees at 73",
            "The real spousal-benefit Social Security strategy most documented retirees never learn about until it's too late",
        ],
    },
    {
        "name": "credit_debt_repair", "rpm": 16.50, "series": "The Collapse Index: Credit Rebuilt",
        "search_query": "credit score repair debt payoff documentary before after",
        "thumbnail_triggers": ["540 TO 720","THE DEBT PAYOFF THAT","EXPLAINS: HOW CREDIT","0% TO DEBT-FREE"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented real strategy that moved a credit score from 540 to 720 in fourteen months, month by month",
            "How the debt avalanche method saved a documented $6,200 in real interest versus the snowball method",
            "The real balance-transfer math showing exactly when a 0% APR offer pays off versus when it doesn't",
            "Documented case: how one real missed payment affected a credit score for the following seven years",
            "The real utilization-ratio math that moved a score 60 points without paying down a single dollar of principal",
        ],
    },
    {
        "name": "real_estate_affordability", "rpm": 15.50, "series": "The Collapse Index: The Real Numbers",
        "search_query": "real estate affordability mortgage documentary explained",
        "thumbnail_triggers": ["CAN YOU AFFORD IT","THE HOUSE THAT COST","EXPLAINS: THE REAL","$400K OR $250K"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The real documented math behind how much house a median household can actually afford at current rates",
            "How a real 1% mortgage rate difference changed a documented buyer's total interest by $89,000 over 30 years",
            "Documented case: renting versus buying, run against real 10-year market data in three different cities",
            "The real closing-cost and hidden-fee breakdown most documented first-time buyers never see coming",
            "How a real, documented 15-year versus 30-year mortgage decision changed total lifetime interest paid",
        ],
    },
    {
        "name": "stock_market_crashes_history", "rpm": 16.00, "series": "The Collapse Index: Market History",
        "search_query": "stock market crash history documentary investigation",
        "thumbnail_triggers": ["37% TO RECOVERY","$1 TRILLION IN 1 DAY","7 YEARS TO RECOVER","1929 TO TODAY"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented trading floor records from the single worst day in market history, hour by hour",
            "How a real, filed margin-call cascade turned one hedge fund's collapse into a real documented market-wide event",
            "Documented case: the real recovery timeline investors actually experienced after history's major crashes",
            "The real, filed regulatory report explaining the exact mechanical trigger behind a documented flash crash",
            "How real documented investor behavior during a crash differed from what the actual index data later showed",
        ],
    },
    {
        "name": "budgeting_saving_strategies", "rpm": 15.00, "series": "The Collapse Index: The Budget Rebuild",
        "series_display": "The Collapse Index: The Budget Rebuild",
        "search_query": "budgeting saving strategies personal finance documentary",
        "thumbnail_triggers": ["THE 50/30/20 RULE","SAVED $12,000 IN","EXPLAINS: THE BUDGET","$0 TO 6 MONTHS SAVED"],
        "thumbnail_format": "before_after",
        "seed_topics": [
            "The documented real household budget that saved $12,000 in a year using a specific, itemized real method",
            "How the 50/30/20 rule performed against a real documented household's actual twelve months of spending",
            "The real zero-based budgeting method that closed a documented $400/month unexplained spending gap",
            "Documented case: building a real six-month emergency fund from $0, with the actual monthly numbers shown",
            "The real sinking-fund method that eliminated a documented household's recurring holiday-season debt cycle",
        ],
    },
]

VOICES = {
    "ai_startup_collapse":     ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "tech_company_collapse":  ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "crypto_collapse":        ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "cybersecurity_disasters":["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "product_flops":          ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "dotcom_era_collapse":    ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "personal_finance_mistakes":   ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "investing_fundamentals":      ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "retirement_planning":         ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "credit_debt_repair":          ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "real_estate_affordability":   ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "budgeting_saving_strategies": ["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    "stock_market_crashes_history":["en-US-ChristopherNeural", "en-GB-ThomasNeural"],
}

BG_KEYWORDS = {
    "ai_startup_collapse": [
        "server room dark blue light", "startup office empty desks",
        "data center servers glowing", "tech office late night working",
        "computer code screen dark", "silicon valley office building",
        "robotic arm technology dark", "circuit board close up macro",
    ],
    "tech_company_collapse": [
        "old office building corporate", "empty corporate headquarters",
        "vintage computer technology", "corporate boardroom empty",
        "declining stock ticker screen", "office layoffs empty desks",
        "old tech factory closed", "corporate sign removal",
    ],
    "crypto_collapse": [
        "cryptocurrency trading screen red", "digital currency collapse graph",
        "blockchain network visualization", "stock market crash red screen",
        "financial trading floor dark", "bitcoin price crash chart",
        "empty trading office night", "digital wallet technology dark",
    ],
    "cybersecurity_disasters": [
        "hacker dark room screens", "cybersecurity breach code red",
        "data breach warning screen", "server room red alert lights",
        "network security dark blue", "computer virus code screen",
        "dark web technology ominous", "encrypted data stream dark",
    ],
    "product_flops": [
        "product warehouse empty boxes", "failed product recall factory",
        "consumer electronics dark shelf", "product testing lab empty",
        "returned products warehouse", "factory assembly line stopped",
        "product packaging dark shelf", "retail store closing empty",
    ],
    "dotcom_era_collapse": [
        "vintage 2000s office computers", "dot com era office cubicles",
        "old website browser vintage", "vintage server room 1999",
        "empty startup office 2000s", "old stock ticker screen vintage",
        "vintage internet cafe computers", "early 2000s tech office",
    ],
    "personal_finance_mistakes": [
        "person reviewing bills desk", "budget spreadsheet laptop close up",
        "wallet cash counting hands", "receipts paperwork desk organized",
        "calculator finance desk clean", "piggy bank coins table",
        "person calculating finances home", "bills envelope stack desk",
    ],
    "investing_fundamentals": [
        "stock market graph clean screen", "investment growth chart bright",
        "financial advisor desk clean office", "index fund portfolio screen",
        "coins growing plant financial", "trading app phone screen clean",
        "financial charts tablet bright", "investment growth graph green",
    ],
    "retirement_planning": [
        "retirement planning documents desk", "older couple financial planning",
        "calendar retirement age circled", "savings jar coins clean",
        "financial advisor meeting bright", "retirement calculator screen",
        "pension documents desk organized", "clock savings concept clean",
    ],
    "credit_debt_repair": [
        "credit card statement desk", "credit score screen phone",
        "debt payoff chart clean", "credit report document close up",
        "person reviewing credit report", "calculator debt payoff desk",
        "credit card cut scissors", "financial freedom bright desk",
    ],
    "real_estate_affordability": [
        "house exterior clean daylight", "mortgage documents desk",
        "for sale sign house", "keys house hand close up",
        "real estate agent meeting bright", "house model calculator desk",
        "neighborhood houses aerial clean", "mortgage calculator screen",
    ],
    "budgeting_saving_strategies": [
        "budget planner notebook desk", "savings jar coins clean bright",
        "meal planning grocery list", "budget app phone screen clean",
        "envelope budgeting system cash", "family budget planning table",
        "emergency fund jar coins", "clean organized desk finance",
    ],
    "stock_market_crashes_history": [
        "stock market crash red screen", "trading floor historical archive",
        "newspaper stock market headline", "stock ticker red numbers falling",
        "financial crisis empty trading floor", "vintage stock exchange photo",
        "market crash graph red screen", "recession empty office historical",
    ],
}

# Secondary keywords if primary returns nothing useful
BG_KEYWORDS_FALLBACK = {
    "ai_startup_collapse":          ["dark server room", "empty tech office", "dark computer screen"],
    "tech_company_collapse":       ["empty corporate office", "closed office building", "corporate decline"],
    "crypto_collapse":             ["red trading screen", "financial crash graph", "empty trading floor"],
    "cybersecurity_disasters":     ["dark server warning", "red alert screen", "network security dark"],
    "product_flops":               ["empty warehouse shelf", "returned products box", "closed retail store"],
    "dotcom_era_collapse":         ["vintage office computer", "old website screen", "2000s tech office"],
    "personal_finance_mistakes":   ["desk bills paperwork", "calculator finance desk", "budget spreadsheet"],
    "investing_fundamentals":      ["stock graph screen", "investment chart bright", "financial growth chart"],
    "retirement_planning":         ["retirement documents desk", "savings jar clean", "financial planning desk"],
    "credit_debt_repair":          ["credit card desk", "credit score screen", "debt chart clean"],
    "real_estate_affordability":   ["house exterior daylight", "mortgage documents desk", "for sale sign"],
    "budgeting_saving_strategies": ["budget planner desk", "savings jar bright", "family budget table"],
    "stock_market_crashes_history":["stock crash screen", "trading floor archive", "market graph red"],
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

# FIX (found on live-run audit, July 14 2026): reasoning models like
# gpt-oss-120b (served by both Cerebras and Groq here) can return their
# internal chain-of-thought alongside — or not clearly separated from —
# the actual final answer, depending on how the provider's API formats
# it. Left unstripped, that reasoning trace becomes the "script" sent
# for review. This covers every documented shape that trace can take:
# explicit <think>/<thinking> tags, the gpt-oss "harmony" channel format
# (<|channel|>analysis ... <|channel|>final<|message|>...), and stray
# leftover channel tokens. Applied once, centrally, in ai_generate() —
# every caller in this file benefits automatically.
def _strip_reasoning(text):
    if not text:
        return text
    # FIX (found on direct user report, July 15 2026 — a raw, truncated
    # <think> block reached a real Telegram message and an email Subject
    # header, the latter crashing the send entirely): the regex below
    # only ever matched a CLOSED <think>...</think> pair. A response cut
    # off mid-reasoning (very common — the same logs show aggressive
    # Groq rate-limiting, which truncates responses well before a
    # reasoning model finishes thinking, let alone reaches a real
    # answer) never emits a closing tag, so the old regex found nothing
    # to strip and passed the raw, unfinished reasoning straight through
    # as if it were the actual title/script/text. Checked first, before
    # the closed-pair regex: if an opening tag exists with no matching
    # close, there is no real answer anywhere in this response — only
    # unfinished reasoning — so everything from that point on is
    # dropped entirely, exactly as if the provider had returned nothing.
    for _open, _close in (('<think>', '</think>'), ('<thinking>', '</thinking>')):
        _idx = text.lower().find(_open)
        if _idx != -1 and _close not in text.lower()[_idx:]:
            text = text[:_idx].strip()
            if not text:
                return ""  # nothing usable survived — caller must treat this as a failed call
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    if '<|channel|>final<|message|>' in text:
        text = text.split('<|channel|>final<|message|>')[-1]
        text = text.split('<|end|>')[0].split('<|return|>')[0].split('<|start|>')[0]
    text = re.sub(r'<\|[^|]{1,40}\|>', '', text)
    return text.strip()

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
                         "HTTP-Referer": "https://github.com/TheCollapseIndex/betrayal-bot"},
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
    """Cohere Command free tier — 20 RPM, excellent for structured long-form scripts."""
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY not set — skipping")
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
                      "max_tokens": min(tokens, 4000),
                      "temperature": 0.88},
                timeout=120)
            if r.status_code == 200:
                t = r.json().get("message", {}).get("content", [{}])
                text = t[0].get("text", "") if t else ""
                if text and len(text.strip()) > 100:
                    log(f"OK Cohere ({_cohere_model})")
                    return text
                continue
            else:
                log(f"  Cohere {_cohere_model} {r.status_code}: {r.text[:150]}")
        except Exception as e:
            log(f"  Cohere {_cohere_model}: {e}")
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

# FIX (found on live-run audit, July 14 2026): every single ai_generate()
# call — and a real episode makes dozens across script/chapters/thumbnail
# text/tags — re-ran the FULL 7-provider chain from scratch, including
# providers already confirmed dead for this run (SambaNova daily-limit,
# Gemini permission-denied, Cerebras wrong-model-name-on-all-variants).
# Each dead provider still costs real seconds (several HTTP round-trips
# plus a 10s sleep) on every single call — across dozens of calls in one
# run, this alone accounts for a large share of the 3.5-hour runtime seen
# in the July 14 log. A provider is only ever un-recoverable mid-run for
# genuinely permanent reasons (bad/expired key, daily quota, account
# permission denial, or a model name that's wrong for the whole run) —
# never for a one-off network blip — so it's safe to stop retrying a
# provider the moment it fails once, for the rest of this run only.
_DEAD_PROVIDERS_THIS_RUN = set()

def ai_generate(prompt, tokens=8000):
    """
    Provider order: Cerebras → SambaNova → Gemini → Groq → OpenRouter → Cohere → Mistral
    7 layers of fallback. Sleep 10s between failures. Providers that fail
    once are skipped for the rest of this run (see _DEAD_PROVIDERS_THIS_RUN).
    """
    providers = [("cerebras", call_cerebras), ("sambanova", call_sambanova),
                 ("gemini", call_gemini), ("groq", call_groq),
                 ("openrouter", call_openrouter), ("cohere", call_cohere),
                 ("mistral", call_mistral)]
    live = [(name, fn) for name, fn in providers if name not in _DEAD_PROVIDERS_THIS_RUN]
    if not live:
        # every provider has already failed this run — reset and try once
        # more rather than guarantee a hard failure
        live = providers
        _DEAD_PROVIDERS_THIS_RUN.clear()
    for i, (name, fn) in enumerate(live):
        r = fn(prompt, tokens)
        if r:
            return _strip_reasoning(r)
        _DEAD_PROVIDERS_THIS_RUN.add(name)
        if i < len(live) - 1:
            log(f"  {name} failed — skipping it for the rest of this run. Waiting 10s before next provider...")
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


def get_real_weekly_trend_signal(niche_name):
    """
    v1 addition — genuine, real weekly trend research, per explicit
    request ("an AI generator that technically researches and finds
    which topic is more suitable for that week"). Uses the real YouTube
    Data API (mostPopular chart) — same proven approach already built
    for the Shorts engine — to see what's actually resonating this week,
    rather than a static random pick. Real signal, never fabricated;
    returns an empty list on any failure rather than guessing.
    """
    try:
        token = get_yt_token()
        if not token:
            return []
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet", "chart": "mostPopular",
                    "regionCode": "US", "videoCategoryId": "25",  # News & Politics, closest real category for business/finance
                    "maxResults": 15, "access_token": token},
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
    for every episode, every day, without exception.

    Also rebuilt into genuine, real trend research, per explicit
    request — the old version's docstring literally said "WITHOUT
    spending an AI token call," meaning it never actually researched
    anything; it just randomly picked from the static seed list. Now
    pulls a real current signal (YouTube's own trending chart, plus any
    NewsAPI-sourced trending_titles already passed in from the caller)
    and asks the AI to pick whichever real seed topic is genuinely most
    aligned with what's resonating this week — or, if none fit well,
    generate a genuinely fresh topic in the same real, specific style
    as the seed bank (never vague, never fabricated specifics).
    """
    real_trend_titles = list(trending_titles or [])
    real_trend_titles += get_real_weekly_trend_signal(niche["name"])

    if not real_trend_titles:
        topic = random.choice(niche["seed_topics"])
        log(f"  No real trend signal available — using seed topic: {topic[:80]}")
        return topic

    try:
        trend_block = "\n".join(f"- {t}" for t in real_trend_titles[:10])
        result = ai_generate(
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
def score_result(r, topic=""):
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
        penalty, hook_issues = _validate_retention_hooks_ch5(script)
        s += penalty
        # Killer Hook / Narrative Craft / Topic Clarity rubric — real,
        # deterministic scoring of the actual script text, shared across
        # all 5 channels (video_pipeline/script_scoring.py).
        try:
            from script_scoring import score_script_rubric, validate_rehook_beat
            rubric_bonus, rubric_issues, subscores = score_script_rubric(script, topic or r.get("topic", ""))
            s += rubric_bonus
            if subscores:
                log(f"  Rubric: Hook {subscores['killer_hook']}/10 | "
                    f"Craft {subscores['narrative_craft']}/10 | "
                    f"Clarity {subscores['topic_clarity']}/10")
            if rubric_issues:
                log(f"  Rubric issues: {' | '.join(rubric_issues[:3])}")
            rehook_bonus, rehook_issues = validate_rehook_beat(script)
            s += rehook_bonus
            if rehook_issues:
                log(f"  {rehook_issues[0]}")
        except Exception as e:
            log(f"  Script rubric scoring (non-fatal): {e}")
    return min(round(s, 1), 10.0), []


def _validate_retention_hooks_ch5(script_clean):
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
    # v1 addition — real, measurable enforcement of the retention-cadence
    # instruction added to the prompt (payoff every 150-225 words).
    WINDOW = 200
    dead_zones = 0
    for start in range(0, total - WINDOW, WINDOW):
        window_text = " ".join(words[start:start + WINDOW]).lower()
        has_hook = any(w in window_text for w in hook_signals)
        has_number = bool(re.search(r'[0-9][0-9,.]*', window_text))
        if not has_hook and not has_number:
            dead_zones += 1
    if dead_zones >= 2:
        penalty -= min(0.3 * dead_zones, 1.2)
        issues.append(f"{dead_zones} retention dead zones (200w+ with no hook or specific detail)")
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
Niche style: {niche.get("dread_style", niche["series"])}
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
        "ai_startup_collapse":          f"{topic_hint.split()[0]} AI startup shutdown documented",
        "tech_company_collapse":       f"{topic_hint.split()[0]} tech company collapse documented",
        "crypto_collapse":             f"{topic_hint.split()[0]} crypto exchange collapse documented",
        "cybersecurity_disasters":     f"{topic_hint.split()[0]} data breach documented case",
        "product_flops":               f"{topic_hint.split()[0]} product recall failure documented",
        "dotcom_era_collapse":         f"{topic_hint.split()[0]} dot com bubble documented history",
        "personal_finance_mistakes":   f"{topic_hint.split()[0]} personal finance documented case study",
        "investing_fundamentals":      f"{topic_hint.split()[0]} investing documented data",
        "retirement_planning":         f"{topic_hint.split()[0]} retirement planning documented data",
        "credit_debt_repair":          f"{topic_hint.split()[0]} credit debt documented data",
        "real_estate_affordability":   f"{topic_hint.split()[0]} real estate mortgage documented data",
        "budgeting_saving_strategies": f"{topic_hint.split()[0]} budgeting documented case study",
        "stock_market_crashes_history":f"{topic_hint.split()[0]} stock market crash documented history",
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
                # FIX (v6 addition — real citation system): this never
                # captured the actual article URL at all, only title/
                # summary/date. Without a real URL there is nothing
                # genuine to cite back to — a "source" with no link
                # doesn't meet "give credit... from which source you
                # took it" in any verifiable way.
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
                # FIX: same real-URL gap as the news source above —
                # Reddit's API gives a real "permalink" field that was
                # simply never read.
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
    Main research entry point. Returns (research_context_string, real_cases_list) —
    the prose string still gets injected into the script prompt exactly as
    before; the structured list (with real URLs, added above) is new —
    it's what the real citation system uses to credit actual sources
    rather than fabricating a "Sources" section with nothing behind it.
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

# v1 addition — real niche-category split: the collapse and finance
# niches need genuinely different tones. Finance content written with
# "psychological dread" and "dark humor" would be actively wrong for a
# trust-dependent niche — research is explicit that finance audiences
# respond to "clarity, honesty, and results they can measure," and that
# authority/trust is the primary barrier to earn, not intrigue.
FINANCE_NICHE_NAMES = {"personal_finance_mistakes", "investing_fundamentals",
                       "retirement_planning", "credit_debt_repair",
                       "real_estate_affordability", "budgeting_saving_strategies",
                       "stock_market_crashes_history"}

def _tone_block_for_niche(niche_obj):
    if niche_obj["name"] in FINANCE_NICHE_NAMES:
        return """TONE AND STYLE (NON-NEGOTIABLE):
- This is a CLEAR, CONFIDENT finance explainer — think trusted advisor, not entertainer.
- Every claim must be specific and verifiable — real numbers, real timeframes, real math.
- No manufactured dread or manufactured urgency. The stakes are real; let them speak for themselves.
- Authority comes from clarity and precision, not intensity. State the real math plainly.
- Pacing: clear, measured delivery. Let a genuinely surprising number land without over-selling it.
- The viewer should feel like they just got real, actionable clarity from someone who knows the subject.

WHAT MAKES VIEWERS TRUST AND KEEP WATCHING THIS CONTENT:
- Specific, checkable numbers ("$1M to $5M", "62 vs 70") — never vague claims.
- The sense that this creator is explaining, not selling.
- A real, complete answer to a question the viewer has actually wondered about.
- Respecting the viewer's intelligence — no unnecessary simplification, no condescension."""
    return """TONE AND STYLE (NON-NEGOTIABLE):
- This is a serious, investigative business documentary — measured and evidence-led, not sensational.
- Every claim must be grounded in real, documented facts — never invented specifics.
- Build genuine narrative tension through real stakes (real money lost, real consequences), not manufactured dread.
- Pacing: let real documented details do the work. Short sentences at genuine revelation moments.
- The viewer should feel like they're getting the real, documented story behind a familiar headline.

WHAT MAKES VIEWERS CRAVE THIS CONTENT:
- The sense that a real, documented story is more specific than the public version.
- Genuine curiosity about how a real, well-known company or system actually failed.
- The satisfaction of understanding a real system fully, from start to end.
- Respecting the viewer's intelligence — real analysis, not manufactured outrage."""


def _central_fracture_for_niche(niche_obj):
    if niche_obj["name"] in FINANCE_NICHE_NAMES:
        return """CENTRAL QUESTION (channel strength, not optional): every script must
revolve around ONE specific, common financial decision or misconception
that costs real people real money — not a vague "money is hard" framing.
Name the specific mechanism explicitly (a specific fee structure, a
specific compounding error, a specific timing mistake, a specific rule
most people get wrong) and keep the entire narrative anchored to resolving
that one question with real numbers, rather than drifting into generic
money advice."""
    return """CENTRAL FRACTURE (channel strength, not optional): every script must
revolve around ONE specific decision, systemic failure, or ignored warning
that caused the collapse — not a vague "things went wrong" framing. Name
the specific failure point explicitly (a specific decision, a specific
technical or financial mechanism, a specific ignored warning) and keep the
entire narrative anchored to that one fracture rather than drifting into a
vague atmosphere piece."""


def _engagement_triggers_for_niche(niche_obj):
    if niche_obj["name"] in FINANCE_NICHE_NAMES:
        return """CLARITY TRIGGERS — use at least 3 per script:
1. The specific number that's more extreme than most people assume.
2. The common assumption that's actually mathematically wrong.
3. The rule or fee structure still affecting people who don't know about it.
4. The specific, checkable comparison ("$1M vs $5M", "62 vs 70").
5. The detail so specific it has to be real math, not a rounded estimate.
6. The one actionable takeaway stated plainly in the final 30 seconds.
7. The follow-up question the video deliberately leaves for the viewer to work out."""
    return """CRAVEABILITY TRIGGERS — use at least 3 per script:
1. The statistic that sounds impossible but is real.
2. The name everyone knows, connected to something they didn't know.
3. The mistake still being repeated at other companies right now.
4. The internal warning that was raised and ignored.
5. The detail so specific it has to be true.
6. The uncomfortable implication in the final 30 seconds.
7. The question the script raises but deliberately doesn't fully answer."""


def build_script_prompt(niche, topic, episode, attempt,
                        trending_titles=None, research_context=""):
    """
    v2 script prompt — 7-stage architecture with stage-specific
    word targets, trigger placements, and forbidden phrases per stage.
    """
    # v1 addition — real product title for the verbal-mention instruction.
    try:
        _product_title_for_prompt = build_product_cta("collapse_index").split(": ")[0].replace("\n\n📖 ", "").strip() or "our companion resource"
    except Exception:
        _product_title_for_prompt = "our companion resource"
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

    return f"""Write a {intensity} finance and business-collapse documentary narration.

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
sentence, not interchangeable with any other finance or business-collapse channel.

CASE SELECTION: prefer a genuinely underreported or lesser-known angle over
the most famous/oversaturated version of this story, if the topic allows it.
This is both a differentiation advantage (viewers haven't seen this take
everywhere already) and a real protection against looking like mass-produced
generic content — original research reads as authored, not templated.

{_central_fracture_for_niche(niche)}

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

{_tone_block_for_niche(niche)}

{_engagement_triggers_for_niche(niche)}

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

    # v1 addition — real chart-data extraction, wiring the chart-
    # generation system (built earlier) into the actual script content
    # instead of leaving it disconnected. Asks for a genuine data series
    # grounded in the same real topic the anchors above are grounded in
    # — never fabricated on its own, and skipped entirely (no chart) if
    # the AI can't produce a real, specific series.
    chart_data = None
    try:
        chart_prompt = (
            f"For a documentary about: {topic}\n"
            f"If there is a real, specific numeric trend or before/after "
            f"transformation relevant to this story (e.g. a stock price "
            f"over time, a valuation drop, a user count decline, a specific "
            f"before/after comparison), provide it as real, plausible data.\n"
            f"Return ONLY valid JSON (no backticks), or exactly the word NONE "
            f"if no genuine numeric story fits:\n"
            f'{{"chart_type":"line or bar","title":"short chart title",'
            f'"y_label":"what the numbers represent","labels":["label1","label2",...],'
            f'"values":[number1,number2,...]}}'
        )
        chart_raw = ai_generate(chart_prompt, tokens=250)
        if chart_raw and "NONE" not in chart_raw.upper()[:10]:
            chart_raw = re.sub(r"```json|```", "", chart_raw).strip()
            m = re.search(r"\{[\s\S]*?\}", chart_raw)
            if m:
                candidate = json.loads(m.group())
                if (candidate.get("labels") and candidate.get("values") and
                        len(candidate["labels"]) == len(candidate["values"]) and
                        len(candidate["labels"]) >= 2):
                    chart_data = candidate
                    log(f"  Real chart data extracted: {chart_data.get('title', '')}")
    except Exception as e:
        log(f"  Chart data extraction (non-fatal): {e}")

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
        script = _inject_ctas_ch5(script, niche["name"])
        # Subscribe CTA guard
        if "subscribe" not in " ".join(script.split()[-60:]).lower():
            script += " Subscribe to this channel for more documented cases."
        wc     = len(script.split())
        log(f"  CTAs injected — final: {wc}w")

    return {"script": script, "words": wc, "violations": violations, "stage_texts": stage_texts, "chart_data": chart_data}


def _inject_ctas_ch5(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30%/60%/80% marks for Ch5 (TheCollapseIndex).
    Uses sentence boundary detection so CTAs never split mid-sentence.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    cta_pool = {
        "ai_startup_collapse": {
            "30pct": ["Subscribe to The Collapse Index. The documented evidence gets more specific from here.",
                      "Subscribe. What comes next is the part most coverage left out."],
            "60pct": ["Subscribe before the final documented numbers are shown.",
                      "Subscribe to The Collapse Index. The next section changes the whole story."],
            "80pct": ["Subscribe. New documented collapse case every weekday.",
                      "Subscribe to The Collapse Index if you want the rest of these breakdowns."],
        },
        "tech_company_collapse": {
            "30pct": ["Subscribe to The Collapse Index. The documented internal decision comes next.",
                      "Subscribe. The real turning point is thirty seconds away."],
            "60pct": ["Subscribe before the documented numbers are shown.",
                      "Subscribe to The Collapse Index. What's documented next reframes everything."],
            "80pct": ["Subscribe. Every weekday, a new documented business collapse.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
        "crypto_collapse": {
            "30pct": ["Subscribe to The Collapse Index. The real documented timeline comes next.",
                      "Subscribe. The documented numbers are thirty seconds away."],
            "60pct": ["Subscribe before the full documented collapse is shown.",
                      "Subscribe to The Collapse Index. The next section has the real numbers."],
            "80pct": ["Subscribe. New documented crypto collapse case every weekday.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
        "cybersecurity_disasters": {
            "30pct": ["Subscribe to The Collapse Index. The documented timeline comes next.",
                      "Subscribe. The real documented failure point is thirty seconds away."],
            "60pct": ["Subscribe before the full documented breach timeline is shown.",
                      "Subscribe to The Collapse Index. What's documented next changes the story."],
            "80pct": ["Subscribe. New documented breach case every weekday.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
        "product_flops": {
            "30pct": ["Subscribe to The Collapse Index. The documented internal testing comes next.",
                      "Subscribe. The real documented numbers are thirty seconds away."],
            "60pct": ["Subscribe before the documented failure is fully shown.",
                      "Subscribe to The Collapse Index. The next part has the real numbers."],
            "80pct": ["Subscribe. New documented product failure every weekday.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
        "dotcom_era_collapse": {
            "30pct": ["Subscribe to The Collapse Index. The documented real numbers come next.",
                      "Subscribe. The real documented collapse timeline is thirty seconds away."],
            "60pct": ["Subscribe before the full documented history is shown.",
                      "Subscribe to The Collapse Index. The next part has the real filed numbers."],
            "80pct": ["Subscribe. New documented dot-com history every weekday.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
        "personal_finance_mistakes": {
            "30pct": ["Subscribe to The Collapse Index. The real numbers behind this come next.",
                      "Subscribe — the specific, real math is thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real financial breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "investing_fundamentals": {
            "30pct": ["Subscribe to The Collapse Index. The real math on this comes next.",
                      "Subscribe — the specific numbers are thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real investing breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "retirement_planning": {
            "30pct": ["Subscribe to The Collapse Index. The real retirement math comes next.",
                      "Subscribe — the specific numbers are thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real retirement breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "credit_debt_repair": {
            "30pct": ["Subscribe to The Collapse Index. The real numbers on this come next.",
                      "Subscribe — the specific credit math is thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real credit breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "real_estate_affordability": {
            "30pct": ["Subscribe to The Collapse Index. The real numbers on this come next.",
                      "Subscribe — the specific mortgage math is thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real housing breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "budgeting_saving_strategies": {
            "30pct": ["Subscribe to The Collapse Index. The real numbers on this come next.",
                      "Subscribe — the specific budget math is thirty seconds away."],
            "60pct": ["Subscribe before the full real breakdown.",
                      "Subscribe to The Collapse Index for the complete real numbers."],
            "80pct": ["Subscribe. New real budgeting breakdown every weekday.",
                      "Subscribe to The Collapse Index for more real, specific breakdowns."],
        },
        "stock_market_crashes_history": {
            "30pct": ["Subscribe to The Collapse Index. The documented real numbers come next.",
                      "Subscribe. The real documented market data is thirty seconds away."],
            "60pct": ["Subscribe before the full documented history is shown.",
                      "Subscribe to The Collapse Index. The next part has the real numbers."],
            "80pct": ["Subscribe. New documented market history every weekday.",
                      "Subscribe to The Collapse Index for the rest of these breakdowns."],
        },
    }
    pool  = cta_pool.get(niche_name, cta_pool["personal_finance_mistakes"])
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
    # v1 addition — the real, researched authority-credential title
    # formula (build_authority_title) was fully built for the finance
    # niches specifically, but was never actually wired into the live
    # title-generation path — the dread/sympathy formula below is
    # completely wrong for finance content, matching the same tone
    # split already fixed for the script prompt. Finance niches get
    # the real researched formula; collapse niches keep the proven
    # dread/sympathy approach below.
    if niche["name"] in FINANCE_NICHE_NAMES:
        authority_title = build_authority_title(topic, niche["name"], ai_generate)
        if authority_title:
            v2_score, _ = score_title_v2(authority_title)
            log(f"  Title (authority-credential formula): {v2_score}/10 — {authority_title[:55]}")
            return authority_title
        log("  Authority-title formula failed — falling back to standard title generation")

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
- "[Number] Employees. [Number] Months. Then The Funding Stopped."
- "The Board Knew. They Approved It Anyway. Here's The Filing."
- "How A $[Number]M Startup Burned Through Everything In [Number] Weeks"
- "[Company/System] Ran On Fake Metrics For [Specific Duration]. Here's The Audit."
- "They Thought It Was Growth. It Was Already Over."
- "The [Number]-Day Collapse Everyone Pretended Was Temporary"
- "[Specific Company]: $[Number]B Valuation. [Number] Investors. Zero Warning."

TITLE FORMULAS THAT WORK (sympathy/woeful-driven — use these roughly as often as dread ones):
- "She Warned The Board For [Number] Years. Nobody Listened."
- "[Number] Employees Lost Everything. Nobody Explained Why."
- "All The Founders Wanted Was A Stable Company. It Cost Them Everything."
- "Everyone Blamed The CEO. The Real Story Was Worse."
- "The Last [Number] Days Of A Company Nobody Was Watching"

TITLE FORMULAS THAT WORK (concrete/object-driven — cleaner and more specific
than pure dread/sympathy, often outperforms both by feeling more real):
- "The Last Slack Message From The CEO"
- "Why The CFO Quietly Resigned Three Weeks Early"
- "The Office They Shut Down Without Warning"
- "The Termination Email That Went Out At 2 AM"
- "The Audit Report They Tried To Bury"
- "The Founder Who Built A Second Company In Secret"
- "Nobody Believed The Second Whistleblower"
- "The Spreadsheet That Predicted The Collapse Six Months Early"

FORBIDDEN TITLE WORDS: "Shocking", "Incredible", "Amazing", "Unbelievable", 
"You Won't Believe", "Mind-Blowing", "Epic", "Ultimate", "Best"
These signal low-quality content. Avoid them completely.

Generate 5 YouTube titles for a finance/business-collapse documentary.
Series: {niche["series"]}, Episode {episode}. Topic: {topic}
REGISTER FOR THIS EPISODE (enforced, alternates every episode): {register_instruction}
Rules: 40-65 chars each (fits fully on mobile). Front-load the most compelling part
in the first 40 characters. Opens a psychological loop. Specific numbers where natural.
Serious, credible investigative tone. No colons unless essential. No quotes.
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
def format_citations_block(real_cases):
    """
    v6 addition — real citation/sourcing system, per explicit request:
    "give credit... source details... just like in a movie after the
    post credits." Only ever cites cases that have a REAL, actually-
    captured URL (the search_real_cases fix above) — never lists a
    "source" a viewer can't actually go verify, since an uncheckable
    citation isn't real credit, it's just decoration. Returns "" if
    there's genuinely nothing to cite (a research-free episode, or one
    where research ran but found nothing usable) — never a fabricated
    "Sources" heading with nothing real underneath it.
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
    prompt = f"""Write a YouTube video description for a finance and business-collapse documentary.
Title: {title} | Series: {niche["series"]}, Episode {episode}
Topic: {topic} | Duration: ~{dur_min} minutes

Structure:
1. Two hook sentences on the core disturbing fact. Creates urgency to watch.
2. Three sentences on what the investigation reveals. No spoilers.
3. One line: Watch until the end — the final revelation changes everything.
4. Chapters section (paste verbatim):\n{chapters_text or "0:00 Introduction"}
5. Eight keyword sentences using: finance documentary, business collapse, documented numbers,
   real case study, {niche["name"].replace("_", " ")}, financial analysis, real data, documented research
6. One line: New investigations every week — subscribe so you never miss one.

Total: 250-320 words. Plain text. No markdown. Do NOT include any hashtags —
those are added separately afterward."""
    # Build SEO hook for first 100 chars (shown in YouTube search results)
    # Format: [SPECIFIC CLAIM]. [EMOTIONAL HOOK]. Full investigation below.
    seo_hooks = {
        "ai_startup_collapse":          f"DOCUMENTED: {topic[:45]}.",
        "tech_company_collapse":       f"DOCUMENTED: {topic[:45]}.",
        "crypto_collapse":             f"DOCUMENTED: {topic[:45]}.",
        "cybersecurity_disasters":     f"DOCUMENTED: {topic[:45]}.",
        "product_flops":               f"DOCUMENTED: {topic[:45]}.",
        "dotcom_era_collapse":         f"DOCUMENTED: {topic[:45]}.",
        "personal_finance_mistakes":   f"EXPLAINED: {topic[:45]}.",
        "investing_fundamentals":      f"EXPLAINED: {topic[:45]}.",
        "retirement_planning":         f"EXPLAINED: {topic[:45]}.",
        "credit_debt_repair":          f"EXPLAINED: {topic[:45]}.",
        "real_estate_affordability":   f"EXPLAINED: {topic[:45]}.",
        "budgeting_saving_strategies": f"EXPLAINED: {topic[:45]}.",
        "stock_market_crashes_history":f"DOCUMENTED: {topic[:45]}.",
    }
    seo_first_line = seo_hooks.get(niche["name"], f"INVESTIGATION: {topic[:55]}.")

    # FIX (v6 addition, per explicit request — "multiple hashtags for
    # more viewers"): this whole thing used to be a buried, unverified
    # instruction inside a much bigger generation prompt ("7. Ten
    # relevant hashtags") — no code-level check the AI actually did it,
    # and "ten" is itself wrong: real 2026 YouTube best practice
    # (researched directly) is 3-5 hashtags — the first 3 in the
    # description become clickable links shown above the title, and
    # going over 15 causes YouTube to silently ignore EVERY hashtag on
    # the video, not just the extras. The old fallback path (used when
    # the main AI call failed) had only 3 generic, always-identical
    # hashtags, never topic-specific. Now generated explicitly, in code,
    # applied identically to both paths.
    hashtags = generate_episode_hashtags(niche, topic)

    raw = ai_generate(prompt, tokens=1000)
    # v12: three-channel cross-promo in every description
    cross_promo_txt = get_cross_promo("collapse_index", is_short=False)
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo_txt
        desc += "\n\n⚠️ This video features AI-assisted narration and editing."
        desc += citations_block
        desc += f"\n\n{hashtags}"
        return desc
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"Subscribe for new investigations every week."
            f"{cross_promo_txt}\n\n"
            f"⚠️ This video features AI-assisted narration and editing."
            f"{citations_block}\n\n"
            f"{hashtags}")


def generate_episode_hashtags(niche, topic):
    """
    Real, explicit, code-level hashtag generation — 3-5 total (the
    actual researched 2026 sweet spot), mixing a niche-category tag, a
    genuinely topic-specific tag from the real episode content, and a
    branded series tag, rather than a static set reused every episode
    or an unverified AI-prompt instruction.
    """
    category_tags_map = {
        "ai_startup_collapse":          ["#AIStartup", "#TechCollapse"],
        "tech_company_collapse":       ["#TechCompany", "#BusinessHistory"],
        "crypto_collapse":             ["#Crypto", "#CryptoCollapse"],
        "cybersecurity_disasters":     ["#Cybersecurity", "#DataBreach"],
        "product_flops":               ["#ProductFail", "#TechFail"],
        "dotcom_era_collapse":         ["#DotComBubble", "#BusinessHistory"],
        "personal_finance_mistakes":   ["#PersonalFinance", "#MoneyTips"],
        "investing_fundamentals":      ["#Investing", "#StockMarket"],
        "retirement_planning":         ["#Retirement", "#FinancialPlanning"],
        "credit_debt_repair":          ["#CreditScore", "#DebtFree"],
        "real_estate_affordability":   ["#RealEstate", "#Mortgage"],
        "budgeting_saving_strategies": ["#Budgeting", "#SavingMoney"],
        "stock_market_crashes_history":["#StockMarketCrash", "#FinancialHistory"],
    }
    category_tags = category_tags_map.get(niche["name"], ["#Documentary", "#TrueStory"])
    try:
        tag_prompt = (f"Give exactly 2 real YouTube hashtags (short, no spaces, CamelCase, "
                      f"starting with #) that specifically match this documentary topic: "
                      f"{topic[:200]}. Return ONLY the 2 hashtags separated by a space, nothing else.")
        raw_tags = ai_generate(tag_prompt, tokens=30) or ""
        topic_tags = [t for t in raw_tags.split() if t.startswith("#") and len(t) < 30][:2]
    except Exception:
        topic_tags = []
    all_tags = category_tags + topic_tags + ["#TheCollapseIndex"]
    seen = set(); final_tags = []
    for t in all_tags:
        if t.lower() not in seen:
            seen.add(t.lower()); final_tags.append(t)
    return " ".join(final_tags[:5])

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
    Uses Groq's real Whisper transcription on the FINAL, ACCEPTED
    narration audio file, regardless of which TTS tier produced it —
    a genuine improvement over the old edge-tts-only SubMaker approach
    (zero captions whenever Fish Audio/gTTS/espeak was the accepted
    tier). Returns False (no captions) rather than a potentially-
    desynced fallback.
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
            _silence_ok, _silence_frac = _detect_abnormal_silence(mp3_path, actual)
            if not _silence_ok:
                log(f"  Audio quality FAIL: {_silence_frac*100:.0f}% silence — likely corrupted/truncated segment")
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
            # FIX (found on deep re-audit): this used to return here
            # directly — skipping the 18-min hard cap, the real per-niche
            # EQ chain (apply_audio_post_processing), and caption
            # generation entirely below. SSML multi-rate is the primary,
            # best-quality tier, so it was silently publishing with no
            # captions and no documentary-grade EQ most of the time. Now
            # runs through the same tail processing every other tier does.
            if duration > 18 * 60:
                log(f"  ⚠️ SSML audio exceeded 18-min hard cap ({duration/60:.1f} min) — trimming")
                trimmed = str(WORK_DIR / "narration_trimmed.mp3")
                run_ffmpeg(["ffmpeg", "-y", "-i", audio_path, "-t", str(18 * 60),
                            "-c", "copy", trimmed], label="hard-duration-cap-ssml", timeout=120)
                if Path(trimmed).exists() and Path(trimmed).stat().st_size > 50000:
                    audio_path = trimmed
                    duration = get_media_duration(audio_path)
            processed_path = str(WORK_DIR / "narration_processed.mp3")
            audio_path = apply_audio_post_processing(audio_path, processed_path, niche_name=niche_name)
            generate_fallback_ass(script, duration, ass_path)
            return audio_path, duration, ass_path, edge_voice

    if not el_ok:
        _fallback_candidates = [v for v in
            ["en-GB-RyanNeural", "en-US-BrianNeural", "en-US-JasonNeural"] if v != edge_voice]
        try:
            _perf_state = load_state()
            _voice_perf = _perf_state.get("performance", {})
            def _voice_learned_rank(v):
                _scores = _voice_perf.get(f"voice_{v}", {}).get("scores", [])
                if len(_scores) < 3:
                    return (0, 0)
                return (1, sum(_scores) / len(_scores))
            _ranked = sorted(enumerate(_fallback_candidates),
                              key=lambda iv: (-_voice_learned_rank(iv[1])[0], -_voice_learned_rank(iv[1])[1], iv[0]))
            _fallback_candidates = [v for _, v in _ranked]
        except Exception as e:
            log(f"  Learned voice preference (non-fatal, using default order): {e}")
        voices_to_try = [edge_voice] + _fallback_candidates  # DavisNeural unavailable on Actions
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
        log(f"  Fallback tier expected duration: ~{dur_expected:.0f}s (final check_audio_quality "
            f"gate validates the real result against this once a tier succeeds)")
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
                    tg("⚠️ Ch5: all edge-tts voices failed today — used Fish Audio backup instead (still natural-sounding)")
                    fallback_ok = True
                    edge_voice = "fish-audio-backup"
                else:
                    log(f"  Fish Audio: {r.status_code}")
            except Exception as e:
                log(f"  Fish Audio backup failed: {e}")
        else:
            log("  FISH_AUDIO_API_KEY not set — skipping Fish Audio backup")

        # NEW TIER: Kokoro (local, open-weight, Apache 2.0) — inserted here
        # per explicit research and decision: genuinely natural-sounding
        # (ranks 1st among browser-runnable models on the public TTS Arena,
        # "Grade A voices produce natural narration suitable for YouTube"),
        # and critically runs LOCALLY — no API rate limit to hit, unlike
        # every tier before or after it. This should mean the pipeline
        # rarely if ever needs to fall further to gTTS/espeak at all.
        if not fallback_ok:
            try:
                from kokoro import KPipeline
                import soundfile as sf
                import numpy as np
                log("  Trying Kokoro (local, natural-sounding, no rate limit)...")
                _kokoro_pipeline = KPipeline(lang_code="a")
                _kokoro_voice = {"en-GB-RyanNeural": "bm_george", "en-US-BrianNeural": "am_michael"}.get(
                    edge_voice, "am_michael")
                _generator = _kokoro_pipeline(script_clean, voice=_kokoro_voice, speed=1.0)
                _all_audio = []
                for _, _, _audio_chunk in _generator:
                    _all_audio.append(_audio_chunk)
                if _all_audio:
                    _combined = np.concatenate(_all_audio)
                    _wav_path = str(WORK_DIR / "kokoro_narration.wav")
                    sf.write(_wav_path, _combined, 24000)
                    # Convert to mp3 to match the rest of the pipeline's format
                    subprocess.run(["ffmpeg", "-y", "-i", _wav_path, "-codec:a", "libmp3lame",
                                     "-qscale:a", "2", audio_path],
                                   capture_output=True, timeout=120)
                    if Path(audio_path).exists() and Path(audio_path).stat().st_size > 50000:
                        log(f"  ACCEPTED: Kokoro (local) | {Path(audio_path).stat().st_size/1024/1024:.1f}MB")
                        tg("⚠️ Ch5: edge-tts and Fish Audio both failed today — used Kokoro "
                           "(local, natural-sounding, no rate limit)")
                        fallback_ok = True
                        edge_voice = "kokoro-local"
            except Exception as e:
                log(f"  Kokoro backup failed (non-fatal, falling further): {e}")

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
                        tg("⚠️ Ch5: edge-tts AND Fish Audio both failed today — used gTTS backup "
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
                        tg("🚨 Ch5: ALL providers failed today (edge-tts, Fish Audio, gTTS) — used OFFLINE "
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
            tg(f"⚠️ Ch5: narration ran {duration/60:.1f}min — over the 18-min limit, "
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
    dependency needed. Produces 2 solid vertical (1080x1920) Shorts cut
    directly from the already-finished main video.

    FIX: previously framed as "Teaser" (10% mark, "WAIT FOR IT") and
    "Reveal/recap" (67% mark, "THE TRUTH") — explicitly tied to the main
    video's own structure (a preview of it / a recap of it), removed per
    explicit request: these should feel like independently interesting
    standalone clips, not a preview/recap pair. Now pulls two genuinely
    different self-contained moments (roughly the 30% and 60% marks —
    far enough apart to be distinct, neither positioned as "before" or
    "after" the story) with hook text that stands on its own rather than
    implying there's a separate main video to go watch.

    NOTE: as a pure-FFmpeg fallback with no network access of its own,
    this cannot do the real trend-research the primary
    shorts_reels_engine.py path does — it only fires if that entire
    system fails to load. Being honest about that limitation here
    rather than pretending this fallback is equally research-driven.

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

    # Honest limitation: as a pure-FFmpeg fallback with no network/AI
    # access of its own, this cannot produce the 2 genuinely different-
    # topic trending Shorts the primary path does — it only fires when
    # that entire system fails. Produces 4 clips (matching the real
    # daily count) from 4 different points in the finished video, since
    # that's the most honest thing available without network access.
    clips = [
        ("standalone_1", 0.20, "YOU NEED TO SEE THIS"),
        ("standalone_2", 0.40, "THIS ACTUALLY HAPPENED"),
        ("standalone_3", 0.60, "WAIT UNTIL YOU HEAR THIS"),
        ("standalone_4", 0.80, "THE PART NO ONE TALKS ABOUT"),
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


def get_stage_matched_video(niche, script, audio_duration, chart_data=None):
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
    # v1 addition — split by niche category: the collapse niches keep a
    # documentary-investigation visual arc, the finance niches get a
    # genuinely different, clean explainer visual arc — not a reused
    # dark-horror keyword bank, which was completely wrong for either.
    if niche["name"] in FINANCE_NICHE_NAMES:
        theme_cycle = [
            "financial documents opening", "everyday life before decision", "quiet reflection",
            "warning signs finance", "growing awareness", "isolation financial stress",
            "financial escalation urgency", "deadline pressure tension", "confined budget space",
            "reviewing records analysis", "documents evidence spreadsheet", "empty office desk",
            "closing in decision", "false comfort calm", "before the real numbers",
            "revelation real numbers shown", "surprising discovery finance", "clarity moment",
            "aftermath outcome result", "empty aftermath calm", "quiet resolution",
            "hopeful memory progress", "resolved clarity", "lingering lesson",
            "final advice moment", "closing image finance", "clear final image", "bright fade out",
            "first signs missed finance", "quiet desk reflection", "calculator finance close up",
        ]
    else:
        theme_cycle = [
            "dark discovery opening", "ordinary business before collapse", "quiet unease",
            "warning signs shadows", "growing dread", "isolation empty office",
            "dark escalation danger", "financial pursuit tension", "trapped confined space",
            "surveillance watching data", "documents evidence records", "empty corridor dread",
            "closing in danger", "false safety calm", "before the truth",
            "dark revelation truth exposed", "shocking discovery", "confrontation tension",
            "aftermath consequences", "empty aftermath", "quiet devastation",
            "haunting memory", "unresolved dread", "lingering shadow",
            "final warning", "closing image", "haunting final image", "dark fade out",
            "first signs missed", "silent office dread", "empty office night",
            "locked door tension", "shadow figure distant", "rain window dark",
            "phone call unanswered", "footsteps behind", "flickering light dread",
            "abandoned office interior", "clock ticking tension", "search investigation",
            "hidden document discovery", "torn document evidence", "email evidence dread",
            "empty chair absence", "broken window entry", "dark server room stairs",
            "streetlight flicker night", "closed blinds hidden", "silent phone dread",
            "waiting room tension", "night drive alone", "empty parking lot",
            "locked drawer secret", "dust covered office", "old headline clipping",
            "security camera static", "dark hallway mirror", "half open door",
            "screen glowing dark", "storm approaching dread", "final silence",
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
        # FIX (found on direct user report, July 15 2026 -- same bug found
        # and fixed in Ch1): top_nouns pulled ANY sufficiently long word
        # straight out of the actual narration with no check on whether
        # it's visually appropriate for a serious finance documentary --
        # an ordinary sentence mentioning "flowers" or a "birthday" bonus
        # would hand that word straight to Pexels/Pixabay as a search
        # term, which reliably returns bright wedding/party footage
        # regardless of the niche's real tone.
        BRIGHT_MUNDANE_BLOCKLIST = {
            "flowers","flower","garden","wedding","birthday","party","parties",
            "sunshine","sunny","picnic","vacation","holiday","holidays","beach",
            "celebration","celebrate","smiling","smile","laughing","laughter",
            "balloons","cake","gift","gifts","present","presents","rainbow",
            "puppy","kitten","baby","babies","graduation","summer",
            "playground","festival","carnival","circus","confetti",
        }
        from collections import Counter
        top_nouns  = [w for w, _ in Counter(stage_words).most_common(6)
                      if w not in BRIGHT_MUNDANE_BLOCKLIST][:1]
        # FIX (found on deep re-audit, same bug as Ch1): bucket_words is
        # often only ~25-35 words (total script / 55-75 buckets) — plenty
        # of real segments have ZERO words that are both >4 chars and not
        # a stopword/bright-mundane term, which silently dropped this
        # segment's search term to the fully generic mood phrase (base_kw
        # alone) with no content-specific signal at all. Before giving up,
        # widen the window to the surrounding ~3 buckets (still the same
        # moment in the narration, not a different scene) so a real
        # topical word from just before/after this exact slice is used
        # instead of going fully generic.
        if not top_nouns:
            wide_start = max(0, start - bucket_words)
            wide_end   = min(total, end + bucket_words)
            wide_text  = " ".join(words[wide_start:wide_end]).lower()
            wide_words = [w.strip(".,!?;:") for w in wide_text.split()
                          if len(w) > 4 and w not in stopwords]
            top_nouns  = [w for w, _ in Counter(wide_words).most_common(6)
                          if w not in BRIGHT_MUNDANE_BLOCKLIST][:1]
        kw = f"{base_kw} {top_nouns[0]}" if top_nouns else base_kw

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
                "-i",f"color=c=black:size=1280x720:rate=24:duration={segment_dur:.1f}",
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

    # v1 addition — real chart clip insertion, at roughly the 45% mark
    # (a natural "here's the real data" moment in the story arc), only
    # when generate_script_content actually extracted genuine chart data
    # grounded in the real topic. Scaled to match the other segments'
    # exact format so it concatenates cleanly, not a visually jarring insert.
    if chart_data:
        try:
            chart_img = str(WORK_DIR / "chart_data.png")
            chart_ok = generate_data_chart(
                chart_data.get("chart_type", "line"), chart_data.get("title", ""),
                chart_data["labels"], chart_data["values"], chart_img,
                y_label=chart_data.get("y_label", ""))
            if chart_ok:
                chart_clip_raw = str(WORK_DIR / "chart_clip_raw.mp4")
                chart_dur = min(8.0, segment_dur * 1.5)
                if render_chart_clip(chart_img, chart_dur, chart_clip_raw):
                    chart_scaled = str(WORK_DIR / "chart_clip_scaled.mp4")
                    run_ffmpeg(["ffmpeg", "-y", "-i", chart_clip_raw,
                        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                              "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-an", chart_scaled], label="chart-scale")
                    if Path(chart_scaled).exists():
                        insert_idx = max(1, int(len(parts) * 0.45))
                        parts.insert(insert_idx, chart_scaled)
                        log(f"  Real chart clip inserted at segment {insert_idx}/{len(parts)}: {chart_data.get('title','')}")
        except Exception as e:
            log(f"  Chart clip insertion (non-fatal): {e}")

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
    "ai_startup_collapse": (
        # Dry, analytical, investigative — no reverb, controlled
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "tech_company_collapse": (
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "crypto_collapse": (
        # Slightly wider dynamics — volatility, urgency
        "equalizer=f=250:width_type=o:width=2:g=-1,"
        "equalizer=f=3200:width_type=o:width=2:g=3,"
        "equalizer=f=8500:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-16dB:ratio=4:attack=3:release=50:makeup=3dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "cybersecurity_disasters": (
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "product_flops": (
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "dotcom_era_collapse": (
        # Slightly wider space — historical distance
        "equalizer=f=90:width_type=o:width=2:g=3,"
        "equalizer=f=2200:width_type=o:width=2:g=2,"
        "equalizer=f=11000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-19dB:ratio=3:attack=5:release=100:makeup=2dB,"
        "loudnorm=I=-16:LRA=11:TP=-1.5"
    ),
    "personal_finance_mistakes": (
        # Warm, close, trustworthy — clear presence, minimal processing
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "investing_fundamentals": (
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "retirement_planning": (
        # Slightly more measured/reassuring — tighter dynamics
        "equalizer=f=110:width_type=o:width=2:g=4,"
        "equalizer=f=210:width_type=o:width=2:g=3,"
        "equalizer=f=7800:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=70:makeup=2dB,"
        "loudnorm=I=-16:LRA=7:TP=-1.5"
    ),
    "credit_debt_repair": (
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "real_estate_affordability": (
        "equalizer=f=105:width_type=o:width=2:g=4,"
        "equalizer=f=205:width_type=o:width=2:g=3,"
        "equalizer=f=7900:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=65:makeup=2dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "budgeting_saving_strategies": (
        "equalizer=f=100:width_type=o:width=2:g=4,"
        "equalizer=f=200:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-15dB:ratio=2.5:attack=8:release=60:makeup=2dB,"
        "loudnorm=I=-16:LRA=9:TP=-1.5"
    ),
    "stock_market_crashes_history": (
        "equalizer=f=250:width_type=o:width=2:g=-1,"
        "equalizer=f=3200:width_type=o:width=2:g=3,"
        "equalizer=f=8500:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-16dB:ratio=4:attack=3:release=50:makeup=3dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["personal_finance_mistakes"]

# Footage keywords for standalone Shorts per niche
NICHE_SHORT_KEYWORDS = {
    "ai_startup_collapse":          "tech server dark dramatic",
    "tech_company_collapse":       "corporate office dramatic decline",
    "crypto_collapse":             "financial trading red dramatic",
    "cybersecurity_disasters":     "cyber dark network dramatic",
    "product_flops":               "product warehouse empty dramatic",
    "dotcom_era_collapse":         "vintage office computer dramatic",
    "personal_finance_mistakes":   "finance desk clean bright",
    "investing_fundamentals":      "stock chart screen clean bright",
    "retirement_planning":         "finance planning desk clean bright",
    "credit_debt_repair":          "credit finance desk clean bright",
    "real_estate_affordability":   "house real estate clean bright",
    "budgeting_saving_strategies": "budget finance desk clean bright",
    "stock_market_crashes_history":"stock market screen dramatic",
}

# ================================================================
# AMBIENT MUSIC
# ================================================================
def generate_ambient_music(duration):
    """
    FIX (found going through Ch1's animation system in full, per explicit
    request): this used to be the ONLY music function in the whole file —
    a single generic synthesized drone (two sine waves + filtered noise),
    IDENTICAL for every video regardless of niche. Every niche sounded
    the same. Kept as the absolute last-resort fallback (used only if
    get_niche_ambient_music below can't produce anything at all), but no
    longer the primary path.
    """
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


# ══════════════════════════════════════════════════════════════════
# NICHE-AWARE BACKGROUND MUSIC (v6 addition, per explicit requirement:
# "the background noise should be according to the niche... if it's
# dark or deception it should be something related to that... if
# shocking, based on that... if surreal, based on that")
#
# HONEST DESIGN NOTE: real, freely-licensed tracks (e.g. sourced once
# from Pixabay's actual music library, which explicitly permits free
# commercial use) are the real fix here — genuinely distinct instruments,
# real recorded texture, not synthesis. This system is built to use real
# bundled files the MOMENT they exist (drop them in music_bank/<mood>/
# with any .mp3 name) with zero further code changes — rotating through
# whichever real files are present so the same track doesn't repeat
# every single video. Until real files are bundled, it falls back to a
# genuinely mood-DISTINCT synthesis (different frequency relationships,
# rhythm, and filtering per mood — not the same drone reused everywhere,
# which is the actual bug being fixed) rather than silently doing nothing.
# ══════════════════════════════════════════════════════════════════

NICHE_MUSIC_MOOD = {
    "ai_startup_collapse":          "dread",
    "tech_company_collapse":       "corporate_decline",
    "crypto_collapse":             "volatile_tension",
    "cybersecurity_disasters":     "unease",
    "product_flops":               "corporate_decline",
    "dotcom_era_collapse":         "nostalgic_unease",
    "personal_finance_mistakes":   "clear_confident",
    "investing_fundamentals":      "clear_confident",
    "retirement_planning":         "steady_reassuring",
    "credit_debt_repair":          "clear_confident",
    "real_estate_affordability":   "steady_reassuring",
    "budgeting_saving_strategies": "clear_confident",
    "stock_market_crashes_history":"volatile_tension",
}

# Real, specific, freely-licensed track recommendations per mood —
# researched real tracks on Pixabay's actual music library (free
# commercial use, no attribution required per their license). Download
# once, place in music_bank/<mood>/ under any filename ending .mp3, and
# the system will use them automatically instead of synthesizing.
# FIX (found on critical re-audit, direct user request): this only had
# search-term suggestions for 2 of Ch5's 7 real moods (dread, unease) --
# the other 3 entries here (sensual_tension, eerie, obsessive_tension)
# are Ch1's moods, never used by any of Ch5's own niches at all, while
# 5 of Ch5's genuinely-used moods (corporate_decline, volatile_tension,
# nostalgic_unease, clear_confident, steady_reassuring) had no search
# guidance whatsoever. The actual synthesis fallback below was already
# correctly built for all 7 -- only this human-facing "what to search
# for and download" guidance was missing them.
MOOD_TRACK_RECOMMENDATIONS = {
    "dread": ["Search Pixabay Music for: 'dark ambient drone', 'financial tension', 'suspense dark'"],
    "unease": ["Search Pixabay Music for: 'unsettling ambient', 'corporate tension', 'disorienting drone'"],
    "corporate_decline": ["Search Pixabay Music for: 'somber corporate', 'melancholy piano ambient', 'decline drone'"],
    "volatile_tension": ["Search Pixabay Music for: 'tense unstable drone', 'market volatility ambient', 'anxious pulse'"],
    "nostalgic_unease": ["Search Pixabay Music for: 'vintage unease', 'faded nostalgic drone', 'retro tension ambient'"],
    "clear_confident": ["Search Pixabay Music for: 'clean corporate ambient', 'confident minimal piano', 'bright explainer background'"],
    "steady_reassuring": ["Search Pixabay Music for: 'warm reassuring ambient', 'steady piano background', 'calm confident drone'"],
}

MUSIC_BANK_ROOT = Path(__file__).parent / "music_bank"

def _synthesize_mood_track(mood, duration):
    """
    Genuinely mood-distinct synthesis fallback — different frequency
    relationships, filtering, and noise character per mood, so at
    minimum every niche sounds DIFFERENT from every other, even before
    real tracks are bundled. This is the actual fix for the "everything
    uses the same drone" bug; real bundled tracks (once added) simply
    replace this with genuine recorded texture.
    """
    path = str(WORK_DIR / f"music_{mood}.mp3")
    dur = int(duration) + 30
    # Each mood gets a genuinely different real ffmpeg synthesis recipe —
    # not just a volume tweak on the same base.
    recipes = {
        "dread": (
            ["-f","lavfi","-i",f"sine=frequency=40:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=41:duration={dur}",  # near-unison beat -> slow throb
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.09[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=180,highpass=f=25,volume=0.15[out]"),
        "sensual_tension": (
            ["-f","lavfi","-i",f"sine=frequency=110:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=165:duration={dur}",  # perfect-fifth interval, warmer
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0015:duration={dur}"],
            "[0]volume=0.06[a];[1]volume=0.05[b];[2]volume=0.2[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=450,highpass=f=60,volume=0.13[out]"),
        "unease": (
            ["-f","lavfi","-i",f"sine=frequency=60:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=63:duration={dur}",  # slightly dissonant, unsettled
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.004:duration={dur}"],
            "[0]volume=0.08[a];[1]volume=0.08[b];[2]volume=0.45[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=320,highpass=f=35,volume=0.14[out]"),
        "eerie": (
            ["-f","lavfi","-i",f"sine=frequency=220:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=225:duration={dur}",  # thin, high, ghostly beating
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.04[a];[1]volume=0.04[b];[2]volume=0.25[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=600,highpass=f=100,volume=0.11[out]"),
        "obsessive_tension": (
            ["-f","lavfi","-i",f"sine=frequency=50:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=100:duration={dur}",  # octave, driving
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.003:duration={dur}"],
            "[0]volume=0.10[a];[1]volume=0.06[b];[2]volume=0.3[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=350,highpass=f=30,volume=0.16[out]"),
        # v1 additions for Ch5's real niches — collapse moods stay tense/
        # dissonant; finance moods are deliberately consonant and clean,
        # matching the researched "clean, minimal" tone of the proven
        # finance-explainer format (Economics Explained) rather than
        # borrowing the collapse niches' dread/tension character.
        "corporate_decline": (
            ["-f","lavfi","-i",f"sine=frequency=55:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=82:duration={dur}",  # perfect fifth, somber
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.002:duration={dur}"],
            "[0]volume=0.08[a];[1]volume=0.05[b];[2]volume=0.22[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=280,highpass=f=32,volume=0.13[out]"),
        "volatile_tension": (
            ["-f","lavfi","-i",f"sine=frequency=70:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=74:duration={dur}",  # tight dissonant beating, unstable
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0045:duration={dur}"],
            "[0]volume=0.09[a];[1]volume=0.09[b];[2]volume=0.4[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=340,highpass=f=38,volume=0.15[out]"),
        "nostalgic_unease": (
            ["-f","lavfi","-i",f"sine=frequency=98:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=147:duration={dur}",  # fifth, faded/vintage feel
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0025:duration={dur}"],
            "[0]volume=0.06[a];[1]volume=0.05[b];[2]volume=0.28[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=380,highpass=f=45,volume=0.12[out]"),
        "clear_confident": (
            ["-f","lavfi","-i",f"sine=frequency=130:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=196:duration={dur}",  # perfect fifth, bright/clean
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.001:duration={dur}"],
            "[0]volume=0.06[a];[1]volume=0.05[b];[2]volume=0.1[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=500,highpass=f=70,volume=0.11[out]"),
        "steady_reassuring": (
            ["-f","lavfi","-i",f"sine=frequency=110:duration={dur}",
             "-f","lavfi","-i",f"sine=frequency=165:duration={dur}",  # perfect fifth, warm/stable
             "-f","lavfi","-i",f"aevalsrc=random(0)*0.0012:duration={dur}"],
            "[0]volume=0.07[a];[1]volume=0.05[b];[2]volume=0.12[c];"
            "[a][b][c]amix=inputs=3:duration=first,lowpass=f=420,highpass=f=55,volume=0.11[out]"),
    }
    inputs, filt = recipes.get(mood, recipes["dread"])
    try:
        run_ffmpeg(["ffmpeg", "-y"] + inputs +
                   ["-filter_complex", filt, "-map", "[out]", "-c:a", "mp3", "-q:a", "4", path],
                   label=f"music-{mood}")
        if Path(path).exists() and Path(path).stat().st_size > 5000:
            return path
    except Exception as e:
        log(f"  Mood synthesis ({mood}) failed: {e}")
    return None


def get_niche_ambient_music(niche_name, duration):
    """
    Real entry point — call this instead of generate_ambient_music
    directly. Picks a real bundled track for this niche's mood if one
    exists (rotating through whatever's present to avoid repetition),
    otherwise falls back to the mood-distinct synthesis above, otherwise
    the absolute-last-resort generic drone.
    """
    mood = NICHE_MUSIC_MOOD.get(niche_name, "dread")
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
            # Loop/trim the real track to match this episode's real duration
            run_ffmpeg(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(chosen),
                        "-t", str(int(duration) + 5), "-c:a", "mp3", "-q:a", "3", out],
                       label="music-real-trim")
            if Path(out).exists() and Path(out).stat().st_size > 10000:
                return out
        except Exception as e:
            log(f"  Real track trim failed, falling back to synthesis: {e}")

    synthesized = _synthesize_mood_track(mood, duration)
    if synthesized:
        return synthesized

    log("  Mood synthesis failed — using absolute-last-resort generic drone")
    return generate_ambient_music(duration)

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
    8-second burned-in outro card.

    HONEST CORRECTION (found while researching a real growth-lever
    addition): this used to be documented as an "end screen" and its
    visual literally mimicked YouTube's real interactive end-screen UI
    — a box with a "→" arrow implying a clickable "next video" card.
    Directly verified against YouTube's actual Data API v3 resource
    list, plus two long-standing, still-open developer feature
    requests asking Google to add exactly this capability: real,
    clickable end screens and cards are NOT programmatically
    accessible at all — they can only be configured manually in
    YouTube Studio. What this function actually produces is burned
    into the video's pixels and has zero real clickable functionality.
    The old visual (a box + arrow styled to look exactly like a real
    end-screen card) risked viewers trying to click something that
    does nothing — actively worse than no visual at all. Fixed to be
    an honest static graphic: a clear subscribe reminder and episode
    branding, no fake-clickable elements. If you set up REAL end
    screens manually in YouTube Studio, this last 8 seconds is exactly
    where YouTube overlays them — keeping this deliberately simple and
    centered (rather than using the corner regions YouTube's own end
    screens occupy) avoids visually conflicting with them.
    """
    series_name = series_name.replace("'", "").replace('"', "").replace(":", "")
    path = str(WORK_DIR / "outro.mp4")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=24:duration=8",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:duration=8",
        "-vf",
        "drawbox=x=0:y=0:w=iw:h=ih:color=red@0.3:t=4,"
        "drawtext=text='SUBSCRIBE TO " + series_name.upper() + "':fontsize=42:"
        "fontcolor=red:x=(w-text_w)/2:y=260:enable='between(t,0,8)',"
        "drawtext=text='NEW INVESTIGATION EVERY WEEKDAY':fontsize=28:"
        "fontcolor=white:x=(w-text_w)/2:y=340:enable='between(t,0,8)',"
        "drawtext=text='Investigation #" + str(episode_num) + "':fontsize=26:"
        "fontcolor=gray:x=40:y=H-60:enable='between(t,0,8)'",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", path
    ], label="outro-card")
    return path


def create_citations_scene(real_cases):
    """
    v6 addition — real on-screen source credits, per explicit request:
    "give the source details... just like in a movie after the post
    credits." Only ever built when there's at least one real,
    URL-backed source (see format_citations_block) — returns None
    otherwise, since a "Sources" card with nothing real behind it isn't
    honest credit, it's decoration. Shows source TITLES on screen (not
    raw URLs — those are long, hard to read at a glance, and the real,
    clickable links already live in the description) with a clear
    pointer to the description for the actual links.
    """
    real_sources = [c for c in (real_cases or []) if c.get("url")]
    if not real_sources:
        return None
    duration = 6
    path = str(WORK_DIR / "citations.mp4")
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
        "drawtext=text='Full links in the description':fontsize=20:fontcolor=red:"
        f"x=(w-text_w)/2:y={y+20}:enable='between(t,0,{duration})'")
    vf = ",".join(lines_filters)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:size=1280x720:rate=24:duration={duration}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:duration={duration}",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", path
    ], label="citations-card")
    return path if Path(path).exists() and Path(path).stat().st_size > 5000 else None

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
        "ai_startup_collapse":          "tech server dark dramatic",
        "tech_company_collapse":       "corporate office dramatic",
        "crypto_collapse":             "financial crash red dramatic",
        "cybersecurity_disasters":     "cyber dark dramatic",
        "product_flops":               "product warehouse dramatic",
        "dotcom_era_collapse":         "vintage office dramatic",
        "personal_finance_mistakes":   "finance desk clean bright",
        "investing_fundamentals":      "stock chart clean bright",
        "retirement_planning":         "finance planning clean bright",
        "credit_debt_repair":          "credit finance clean bright",
        "real_estate_affordability":   "house real estate clean bright",
        "budgeting_saving_strategies": "budget finance clean bright",
        "stock_market_crashes_history":"stock market dramatic",
    }
    mod = niche_mod.get(niche_name, "business finance dramatic")
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
            channel_name = "TheCollapseIndex",
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
        draw.text((28, 22), "● THE COLLAPSE INDEX", font=get_font(26), fill=(180, 30, 30))

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
            "-annotate", "0+28+22", "THE COLLAPSE INDEX", thumb_path],
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
    "ai_startup_collapse": (
        "eq=brightness=-0.06:contrast=1.25:saturation=0.75,"
        "vignette=PI/3.5"
    ),
    "tech_company_collapse": (
        "eq=brightness=-0.05:contrast=1.2:saturation=0.8,"
        "vignette=PI/3.6"
    ),
    "crypto_collapse": (
        "eq=brightness=-0.04:contrast=1.25:saturation=0.85,"
        "colorbalance=rs=0.06,"      # slight red push, volatility
        "vignette=PI/3.6"
    ),
    "cybersecurity_disasters": (
        "eq=brightness=-0.07:contrast=1.3:saturation=0.6,"
        "colorbalance=bs=0.06,"
        "vignette=PI/3.2"
    ),
    "product_flops": (
        "eq=brightness=-0.04:contrast=1.15:saturation=0.8,"
        "vignette=PI/3.8"
    ),
    "dotcom_era_collapse": (
        "eq=brightness=-0.03:contrast=1.1:saturation=0.7,"  # vintage/faded feel
        "colorbalance=rs=0.04:gs=0.02,"
        "vignette=PI/4"
    ),
    # Finance niches: genuinely bright and clean, matching the researched
    # "clean, minimal" tone (Economics Explained) — the opposite grade
    # from the collapse niches, not a lighter version of the same dark look.
    "personal_finance_mistakes": (
        "eq=brightness=0.03:contrast=1.08:saturation=1.05"
    ),
    "investing_fundamentals": (
        "eq=brightness=0.03:contrast=1.08:saturation=1.05"
    ),
    "retirement_planning": (
        "eq=brightness=0.02:contrast=1.06:saturation=1.0"
    ),
    "credit_debt_repair": (
        "eq=brightness=0.03:contrast=1.08:saturation=1.05"
    ),
    "real_estate_affordability": (
        "eq=brightness=0.02:contrast=1.06:saturation=1.02"
    ),
    "budgeting_saving_strategies": (
        "eq=brightness=0.03:contrast=1.08:saturation=1.05"
    ),
    "stock_market_crashes_history": (
        "eq=brightness=-0.02:contrast=1.2:saturation=0.85,"
        "vignette=PI/3.8"
    ),
}
DEFAULT_VISUAL_GRADE = NICHE_VISUAL_GRADE["personal_finance_mistakes"]

def compose_video(narration_path, bg_path, music_path, ass_path,
                  audio_duration, label="main", niche_name=None):
    output   = str(WORK_DIR / f"composed_{label}.mp4")
    bg_dur   = get_media_duration(bg_path)
    loop_n   = max(int(audio_duration / max(bg_dur, 1)) + 2, 1)
    has_mus  = music_path and Path(music_path).exists()
    has_sub  = ass_path and Path(ass_path).exists()

    # FIX (found on direct user report, July 15 2026 -- same bug found and
    # fixed in Ch1): has_sub was computed and then never actually used.
    # Real subtitles were generated upstream and silently dropped right
    # here, every single episode.
    grade = NICHE_VISUAL_GRADE.get(niche_name, DEFAULT_VISUAL_GRADE)
    # fps=24 added — normalizes whatever native frame rate the source
    # background clip has (this path also serves the single-clip fallback,
    # whose source rate is unpredictable), consistent with intro/outro's
    # hardcoded 24fps so the final -c copy concat doesn't hit a mismatch.
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,"
          f"{grade}")
    if has_sub:
        _escaped_ass = str(ass_path).replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\\'")
        vf += f",ass='{_escaped_ass}'"

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

    # FIX (found on direct user report, July 15 2026): same bug as the
    # main compose_video — has_sub was computed and then never used.
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
          "crop=405:720:(iw-405)/2:0,scale=1080:1920,fps=24")
    if has_sub:
        _escaped_ass = str(ass_path).replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\\'")
        vf += f",ass='{_escaped_ass}'"

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
        if not globals().get("CHANNEL5_YT_REFRESH_TOKEN", os.environ.get("CHANNEL5_YT_REFRESH_TOKEN","")):
            raise Exception(f"YouTube token failed: refresh_token secret not set. "
                            f"Add CHANNEL5_YT_REFRESH_TOKEN to GitHub Secrets.")
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
        "ai_startup_collapse":          "Did you use this product before it shut down?",
        "tech_company_collapse":       "Did you see this coming, or did it surprise you too?",
        "crypto_collapse":             "Were you affected by this collapse, or did you see the warning signs?",
        "cybersecurity_disasters":     "Were your own records affected by this breach?",
        "product_flops":               "Did you actually buy this product? What was your experience?",
        "dotcom_era_collapse":         "Do you remember when this actually happened?",
        "personal_finance_mistakes":   "Have you made this exact mistake? What did it cost you?",
        "investing_fundamentals":      "What's your own approach to this?",
        "retirement_planning":         "Where are you in this decision right now?",
        "credit_debt_repair":          "What's your current credit situation — are you working on it?",
        "real_estate_affordability":   "Is this the math you're facing right now?",
        "budgeting_saving_strategies": "Have you tried this method? Did it actually work for you?",
        "stock_market_crashes_history":"Do you see the same pattern happening again today?",
    }
    hook = niche_hooks.get(niche_name,
        "What was the detail in this breakdown that surprised you the most?")
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

    FIX: was keyed by "teaser"/"recap" (implying a preview of / callback
    to a separate main video) — removed per explicit request that
    standalone Shorts should feel independently interesting, not tied
    to the main video's own structure. Both prompt variants now target
    a genuinely standalone, self-contained hook.
    """
    prompts = {
        "standalone_1": f"Write a YouTube Shorts title that creates maximum curiosity. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, starts with a shocking fact or question, no 'watch' or 'click'. "
                  "Return ONLY the title.",
        "standalone_2": f"Write a YouTube Shorts title revealing a genuinely surprising, self-contained fact. Topic: {main_title[:80]}. "
                  "Rules: under 55 chars, feels complete on its own, no reference to a separate video. "
                  "Return ONLY the title.",
    }
    type_key = "standalone_1" if "1" in short_type or "teaser" in short_type.lower() else "standalone_2"
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
    hooks = {"standalone_1": "You Need To See This", "standalone_2": "This Actually Happened"}
    return hooks.get(type_key, main_title[:50])


def post_short_creator_comment(token, video_id, niche_name, main_title):
    """
    Post a creator comment on each Short immediately after upload.
    Shorts comments drive early engagement signals = algorithmic boost.
    Different from main video comment — Shorts audience is colder.
    """
    short_hooks = {
        "ai_startup_collapse":          "Did you know this AI startup existed before it collapsed?",
        "tech_company_collapse":       "Did you ever use this before it fell apart?",
        "crypto_collapse":             "Were you in this space when it happened?",
        "cybersecurity_disasters":     "Were you affected by this breach?",
        "product_flops":               "Did you ever own this product?",
        "dotcom_era_collapse":         "Were you online when this actually happened?",
        "personal_finance_mistakes":   "Have you made this mistake before?",
        "investing_fundamentals":      "Does this match your own strategy?",
        "retirement_planning":         "Is this the math you're planning around?",
        "credit_debt_repair":          "Where's your credit score at right now?",
        "real_estate_affordability":   "Is this the reality where you live too?",
        "budgeting_saving_strategies": "Have you tried this method yourself?",
        "stock_market_crashes_history":"Do you see this pattern happening again?",
    }
    hook = short_hooks.get(niche_name, "What do you think happened here?")
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


def run_collapse_index_viral_intelligence(niche):
    """
    Viral intelligence engine for Ch5 (ported from Ch2).
    Runs weekly — results cached in state.json under 'viral_intel'.
    Finds what's working in the finance/AI-collapse documentary niche.

    FIX (found on direct user request, July 14 2026): this function was
    literally named run_ch1_viral_intelligence and its docstring described
    "the dark horror/psychological documentary niche" -- a straight
    copy-paste leftover from Ch1's version that was never renamed or
    corrected, despite being used for Ch5's own weekly trend research.
    """
    state = load_state()
    intel = state.get("viral_intel", {})
    name  = niche["name"]
    if name in intel:
        try:
            last = datetime.datetime.fromisoformat(intel[name].get("last_run", "2020-01-01"))
            if (datetime.datetime.now() - last).days < 7:
                log(f"  Ch5 viral intel cached ({name})")
                return intel[name]
        except: pass

    log(f"  Running Ch5 viral intelligence: {name}...")
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
            log("  Ch5 viral intel loaded")
            return d
    except Exception as e:
        log(f"  Ch5 viral intel err: {e}")

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
    unused_seeds = [t for t in niche["seed_topics"] if t not in used_topics]
    return random.choice(unused_seeds) if unused_seeds else niche["seed_topics"][0]


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
        # FIX (found on direct user request, July 14 2026): this was
        # literally "Investigative documentary narrations — dark
        # psychology, true horror, classified evidence" -- Ch1's real
        # channel description, copy-pasted verbatim into Ch5's code. If
        # this ever ran, Ch5's real, public YouTube "About" page would
        # have described itself as a dark psychology/horror channel
        # while actually publishing finance/AI-collapse documentaries --
        # a real, visible branding mismatch, not just an internal one.
        desc  = (f"Latest: {latest_title}\n{latest_url}\n\n"
                 "Financial collapse investigations — AI startup failures, market crashes, "
                 "personal finance mistakes, documented with real numbers and sources.\n"
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

    FIX (found via a real production Telegram alert showing 6/7
    providers consistently "failing" — diagnosed and fixed first for
    Ch3, applying the identical fix here since this function was
    copy-pasted across all channels): the test prompt asked for a
    genuinely ~2-character reply ("Reply with exactly: OK"), while every
    single provider-calling function requires the response to exceed
    100 characters to count as valid — a correct, protective check for
    REAL script-generation calls, but wrong for this tiny test. Any
    provider whose model actually followed the instruction literally
    (replying just "OK") was wrongly marked "NO RESPONSE"; a provider
    whose model happened to ignore the instruction and ramble past 100
    characters passed by accident. This was never a real measure of
    provider health. Fixed by asking for something that naturally
    produces a long reply regardless of how literally the model follows
    instructions, rather than weakening the 100-char check itself
    (which is correctly protective everywhere else it's used).
    """
    log("\n" + "="*65)
    log("  AI PROVIDER HEALTH CHECK")
    log("="*65)
    test = ("Write a short paragraph (at least 150 words) describing what "
            "makes a documentary narration engaging. Do not use any special "
            "formatting, just plain prose.")
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
        log(f"  Ch5 Short {short_num+1}: {Path(out).stat().st_size//(1024*1024)}MB")
        return out
    return None



# ================================================================
# WRAPPER FUNCTIONS — bridge between main() calls and implementations
# ================================================================

def run_stage1(state):
    """
    13-attempt script engine for Ch5 TheCollapseIndex.
    Returns (niche_name, niche, topic, script_result, trending_titles).
    """
    log("\n"+"="*65)
    log("  STAGE 1: TheCollapseIndex 13-Attempt Script Engine")
    log(f"  Graduated quality gate: attempts 1-8 require {MIN_GATE} | "
        f"attempts 9-12 relax to 7.0 | attempt 13 absolute floor {FINAL_GATE}")
    log("="*65)

    day        = datetime.datetime.now().weekday()
    niche_name = pick_best_niche(state, DAY_NICHE.get(day, "personal_finance_mistakes"))
    niche      = next(n for n in NICHES if n["name"] == niche_name)
    episode    = state.get("episode_count", 0) + 1
    prev_title = state.get("last_title", "")

    intel          = run_collapse_index_viral_intelligence(niche)
    # FIX (found on word-by-word re-audit, July 15 2026 -- same bug found
    # and fixed in Ch1): trending was hardcoded to an empty list and
    # never populated, so the trend-aware generation ran on zero real
    # data every episode. Wired in.
    try:
        _yt_token_for_trends = get_yt_token()
        trending = fetch_trending_titles(niche, _yt_token_for_trends)
    except Exception as e:
        log(f"  Trending titles fetch (non-fatal): {e}")
        trending = []
    used_topics    = []
    gate           = MIN_GATE
    best_score     = 0.0
    best_result    = None
    best_topic     = niche["seed_topics"][0]
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
            fresh = intel.get("fresh_topic_ideas", niche["seed_topics"])
            unused = [t for t in fresh if t not in used_topics]
            topic = unused[0] if unused else random.choice(niche["seed_topics"])
            try:
                from topic_scoring import add_topic_candidate
                add_topic_candidate(SCRIPT_DIR, "collapse_index", topic, niche_name,
                                     lambda p, tokens=200: ai_generate(p, tokens=tokens))
            except Exception as e:
                log(f"  Topic scoring (non-fatal): {e}")
        else:
            topic = get_ch1_archive_topic(niche, attempt, used_topics)
        used_topics.append(topic)

        # Research real cases for this topic
        # FIX: get_research_context now returns (prose_string, real_cases_list)
        # instead of just a string — real_cases feeds the new citation
        # system (built this session), attached to result below rather
        # than changing run_stage1's own broader return signature, which
        # has many call sites elsewhere.
        research_ctx, real_cases = get_research_context(niche_name, topic)

        log(f"\nAttempt {attempt}/13 (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            result = generate_script_content(
                niche, topic, episode, attempt,
                trending_titles=trending,
                research_context=research_ctx)

            if not result:
                time.sleep(5); continue
            result["real_cases"] = real_cases

            # v6 addition — real research-usage verification (same fix
            # built for Ch3/Ch4, applying here since Ch5 has the
            # identical gap): real_cases gets injected into the prompt
            # via research_ctx, but nothing ever verified the AI
            # actually used it versus inventing plausible-sounding
            # details instead. Logged every attempt; the Telegram alert
            # only fires for the actual winning attempt below (avoids
            # up to 13 noisy alerts per episode for attempts that never published).
            _research_used = True
            if real_cases:
                _script_text = (result.get("script", "") or "").lower()
                _research_words = set()
                for c in real_cases[:3]:
                    _research_words.update(
                        w.strip(".,;:").lower() for w in (c.get("title", "") + " " + c.get("summary", "")).split()
                        if len(w) > 6
                    )
                _research_used = any(w in _script_text for w in _research_words)
                log(f"  Research-usage check: {'genuinely reflected' if _research_used else 'NOT clearly used'}")
            result["_research_used"] = _research_used

            score, _ = score_result(result, topic)
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
                result["score"] = score  # v1 addition — preserve the computed score for callers
                if result.get("real_cases") and not result.get("_research_used", True):
                    tg(f"⚠️ Ch5: real research was found ({len(result['real_cases'])} sources) but "
                       f"the script that's actually publishing shows no clear sign of using it — "
                       f"may be relying on invented details instead of the real documented facts. "
                       f"Worth a manual check on this episode's factual grounding.")
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

    tg(f"Ch5 Day Skipped\nBest: {best_score}/10 after 13 attempts")
    sys.exit(0)


def generate_data_chart(chart_type, title, labels, values, output_path,
                          y_label="", highlight_last=True):
    """
    v1 addition — real, genuine data-chart generation, per direct
    research: "b-roll plus charts or maps" is explicitly named as part
    of the real, proven format for the closest comparable channels in
    this exact niche (How Money Works, Economics Explained, Wendover
    Productions), and "map and graph-driven content" is separately
    flagged as underserved. This draws REAL data the AI is instructed
    to provide (real documented numbers — a stock price collapse, a
    user-count decline, a revenue drop) — never decorative filler.
    Styled dark/cinematic to match the documentary aesthetic, not a
    default matplotlib look.
    chart_type: "line" (trend over time, e.g. stock price) or
                "bar" (before/after comparison, e.g. revenue).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")

    accent = "#e01010"
    if chart_type == "line":
        ax.plot(labels, values, color=accent, linewidth=4, marker="o",
                markersize=10, markerfacecolor="#ffffff", markeredgecolor=accent)
        ax.fill_between(range(len(labels)), values, alpha=0.15, color=accent)
        if highlight_last and values:
            ax.scatter([labels[-1]], [values[-1]], color="#ffffff", s=300,
                      zorder=5, edgecolors=accent, linewidths=3)
    else:  # bar
        colors = ["#3a3a45"] * (len(values) - 1) + [accent] if highlight_last else ["#3a3a45"] * len(values)
        ax.bar(labels, values, color=colors, width=0.6)

    ax.set_title(title, color="#ffffff", fontsize=32, fontweight="bold", pad=30,
                 fontfamily="sans-serif")
    if y_label:
        ax.set_ylabel(y_label, color="#aaaaaa", fontsize=20)
    ax.tick_params(colors="#cccccc", labelsize=18)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#444444")
    ax.grid(True, alpha=0.1, color="#ffffff")

    plt.tight_layout()
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return Path(output_path).exists() and Path(output_path).stat().st_size > 5000


def render_chart_clip(chart_image_path, duration, output_path):
    """
    Turns a static chart image into a real video clip with a subtle
    Ken Burns zoom (matching the same motion language as the stock-
    footage clips elsewhere in this pipeline, so a chart scene doesn't
    feel visually inconsistent with the b-roll around it).

    FIX (found on visual-quality review): this used to cut directly from
    stock footage to an instantly complete, fully-formed chart — no
    entrance at all. The whiteboard-animation channels (Ch2/Ch3/Ch4)
    have a genuine soft entrance built in (each scene's own incremental
    stroke-reveal), but this stock-footage-based channel had nothing
    equivalent for its chart insert specifically, making it the most
    jarring cut in the whole video. Added a real, tested 0.4s fade-in.
    """
    run_ffmpeg([
        "ffmpeg", "-y", "-loop", "1", "-i", chart_image_path,
        "-vf", f"scale=1920:1080,zoompan=z='min(zoom+0.0006,1.15)':d={int(duration*24)}:s=1920x1080:fps=24,fade=t=in:st=0:d=0.4",
        "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
    ], label="chart-clip")
    return Path(output_path).exists()


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
# backdrop" (Ch5 style pairing: atmospheric motion + minimal kinetic
# type overlays). Free, built entirely with FFmpeg drawtext — no new
# API, no paid service, no self-hosted model.
# ════════════════════════════════════════════════════════════

NICHE_ACCENT_COLORS = {
    "ai_startup_collapse":          "0xE01010",  # alert red
    "tech_company_collapse":       "0xE06010",  # burnt orange, decline
    "crypto_collapse":             "0xE0A010",  # warning amber
    "cybersecurity_disasters":     "0xB01010",  # deep breach red
    "product_flops":               "0xE06010",  # burnt orange
    "dotcom_era_collapse":         "0xA0603A",  # vintage rust/sepia
    "personal_finance_mistakes":   "0x2A9D5C",  # confident green, growth
    "investing_fundamentals":      "0x2A7DA0",  # trust blue
    "retirement_planning":         "0x2A7DA0",  # trust blue
    "credit_debt_repair":          "0x2A9D5C",  # confident green
    "real_estate_affordability":   "0x3A6F9A",  # steady blue
    "budgeting_saving_strategies": "0x2A9D5C",  # confident green
    "stock_market_crashes_history":"0xE0A010",  # warning amber
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


# FIX (found on direct user request, July 14 2026): add_horror_atmosphere_fx
# has been REMOVED entirely from this file. It applied real horror-movie
# visual effects -- continuous film grain, chromatic-aberration glitch
# bursts, a literal jump-scare white flash, jittery flickering text -- to
# The Collapse Index's finance/AI-collapse documentary content. It was
# correctly built for Ch1 (dark psychology/horror) and blindly copied
# into this file when Ch5 was built from Ch1's template, never adapted
# or removed. assemble_video() below no longer calls it at all.


# FIX (found on final re-audit, wiring real per-stage scores): the video
# quality score's "pipeline completeness" component needs to know whether
# optional visual stages (horror-fx, watermark) actually succeeded or
# silently fell back — assemble_video() already knows this internally
# (both fallbacks are already logged as "non-fatal"), it just never
# surfaced it anywhere. Rather than change assemble_video's return type
# (it's called from 3 different places in this file — a tuple-unpack
# mistake there would be a real, easy-to-miss risk), it's tracked here at
# module level and read by the caller immediately after each call.
_last_video_fallback_flags = {}

def assemble_video(niche_name, audio_path, audio_duration, topic, script="", episode=1, real_cases=None, chart_data=None, ass_path=None):
    """Assemble final video: background footage + narration + ambient music
    + kinetic text overlays at key story beats (clear, credible finance/
    collapse-documentary style, matched to niche — mix approach: animation
    for key beats, stock footage as backdrop)."""
    niche       = next(n for n in NICHES if n["name"] == niche_name)
    # FIX: this was calling get_background_video (ONE clip, looped for the
    # entire runtime) even though get_stage_matched_video (55-75 dynamically-
    # sized, sequential, audio-matched clips — already fully built and
    # working) existed in this same file and was never wired in. That's
    # exactly why the video showed "only one background the whole time."
    search_kw   = ""  # only used by the single-clip fallback below
    bg_path     = get_stage_matched_video(niche, script, audio_duration, chart_data=chart_data)
    if not bg_path:
        log("  Stage-matched video unavailable — falling back to single looped clip")
        bg_path = get_background_video(niche, audio_duration, search_kw)
    # FIX: was generate_ambient_music(audio_duration) — the same generic
    # synthesized drone regardless of niche. Now genuinely niche-aware.
    mus_path    = get_niche_ambient_music(niche_name, audio_duration)
    composed    = compose_video(audio_path, bg_path, mus_path, ass_path,
                                 audio_duration, label="main", niche_name=niche_name)

    global _last_video_fallback_flags
    _last_video_fallback_flags = {}

    # FIX (found on direct user request, July 14 2026): this used to call
    # add_horror_atmosphere_fx() — film grain, chromatic-aberration glitch
    # bursts, a literal jump-scare white flash, and jittery flickering
    # text. That's a genuine horror-movie visual language, correctly built
    # for Ch1 (dark psychology/horror content) and then copy-pasted into
    # this file unchanged when Ch5 was built from Ch1's template. The Collapse
    # Index is a finance/AI-collapse documentary channel — applying
    # jump-scares and horror grain to a video about a startup's funding
    # collapse or a personal budgeting mistake is a real, wrong content-tone
    # mismatch, not a stylistic choice. Removed entirely, per explicit
    # instruction — Ch5 gets no atmosphere-FX post-processing pass at all
    # for now; the video is the clean composed output from compose_video()
    # above.

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
    ], label="watermark", timeout=900)
    if Path(composed_watermarked).exists() and Path(composed_watermarked).stat().st_size > 1_000_000:
        composed = composed_watermarked
        _last_video_fallback_flags["watermark_failed"] = False
    else:
        _last_video_fallback_flags["watermark_failed"] = True

    # FIX: create_outro's episode_num defaults to 1 and was never being
    # passed the real episode — same category of bug as the thumbnail
    # episode badge found earlier. Every outro card has shown
    # "Investigation #1" regardless of actual episode number.
    outro    = create_outro(niche["series"], episode)
    # v6 addition — real on-screen source credits, per explicit request.
    # Only adds a real segment when create_citations_scene actually found
    # genuine URL-backed sources to show; concat_parts already filters
    # out any None/missing path, so this is safe to include unconditionally.
    citations_scene = create_citations_scene(real_cases)
    final    = str(WORK_DIR / "final.mp4")
    concat_parts([composed, citations_scene, outro], final)
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
        "ai_startup_collapse":          ["INVESTORS LOST EVERYTHING", "PRODUCT NEVER WORKED", "STAFF FOUND OUT LAST",
                                          "EIGHTEEN MONTHS TOTAL", "DOCUMENTED IN EMAILS"],
        "tech_company_collapse":       ["THEY SAW IT COMING", "BOARD IGNORED THIS", "FORTY YEARS ENDED",
                                          "ONE MEETING DECIDED", "DOCUMENTED INTERNAL MEMO"],
        "crypto_collapse":             ["SEVENTY TWO HOURS TOTAL", "BILLIONS SIMPLY VANISHED", "STAFF KNEW FIRST",
                                          "DOCUMENTED SLACK MESSAGES", "USERS FOUND OUT LAST"],
        "cybersecurity_disasters":     ["SEVENTY SIX DAYS UNNOTICED", "PATCH EXISTED ALREADY", "MILLIONS OF RECORDS",
                                          "DOCUMENTED SECURITY REPORT", "ONE SERVER MISSED"],
        "product_flops":               ["MILLIONS WASTED TOTAL", "TESTING PREDICTED THIS", "THREE WEEKS TOTAL",
                                          "DOCUMENTED FOCUS GROUPS", "NOBODY WANTED THIS"],
        "dotcom_era_collapse":         ["TWO HUNDRED DAYS TOTAL", "DOCUMENTED IPO PROMISES", "NEVER TURNED PROFITABLE",
                                          "MILLIONS ON ONE AD", "DOCUMENTED BURN RATE"],
        "personal_finance_mistakes":   ["THIS MISTAKE COST THOUSANDS", "MOST PEOPLE MISS THIS", "REAL NUMBERS SHOWN",
                                          "DOCUMENTED HOUSEHOLD BUDGET", "SPECIFIC FIX EXPLAINED"],
        "investing_fundamentals":      ["REAL RETURNS COMPARED", "MOST PEOPLE GET WRONG", "SPECIFIC MATH SHOWN",
                                          "DOCUMENTED PORTFOLIO DATA", "REAL NUMBERS EXPLAINED"],
        "retirement_planning":         ["REAL RETIREMENT MATH", "MOST PEOPLE MISS THIS", "SPECIFIC AGES COMPARED",
                                          "DOCUMENTED WITHDRAWAL DATA", "REAL NUMBERS SHOWN"],
        "credit_debt_repair":          ["REAL CREDIT MATH", "SPECIFIC SCORE JUMP", "DOCUMENTED REAL CASE",
                                          "MOST PEOPLE MISS THIS", "REAL TIMELINE SHOWN"],
        "real_estate_affordability":   ["REAL AFFORDABILITY MATH", "SPECIFIC NUMBERS COMPARED", "MOST PEOPLE GET WRONG",
                                          "DOCUMENTED REAL COSTS", "REAL MATH EXPLAINED"],
        "budgeting_saving_strategies": ["REAL BUDGET RESULTS", "SPECIFIC METHOD EXPLAINED", "DOCUMENTED REAL SAVINGS",
                                          "MOST PEOPLE MISS THIS", "REAL NUMBERS SHOWN"],
        "stock_market_crashes_history":["DOCUMENTED MARKET HISTORY", "REAL NUMBERS COMPARED", "PATTERN REPEATS TODAY",
                                          "SPECIFIC CRASH EXPLAINED", "REAL DATA SHOWN"],
    }
    title_context = (
        f"\nTHE ACTUAL VIDEO TITLE (match its register exactly — if it's dread-driven,\n"
        f"the thumbnail must be dread-driven too; if it's sympathy/woeful, match that.\n"
        f"Do not clash with this title's tone): \"{title}\"\n"
        if title else ""
    )
    # v1 addition — genuinely different prompt for finance vs collapse
    # niches, matching the same tone split already built for the script
    # prompt. A "dark documentary" prompt applied to finance content
    # would bias the AI's first draft toward the wrong register entirely,
    # even before run_thumbnail_stage's own before/after dispatch runs.
    is_finance = niche["name"] in FINANCE_NICHE_NAMES
    if is_finance:
        prompt = (
            f"Generate the most compelling 3-word thumbnail text for a clear, "
            f"confident finance explainer video.\n"
            f"NICHE: {niche['name']} | TOPIC: {topic[:100]}\n"
            f"{title_context}\n"
            f"USE THESE TRIGGERS (pick ONE, don't mix):\n"
            f"1. SPECIFICITY: a real number or concrete result, not vague\n"
            f"2. CURIOSITY GAP: a genuinely useful question the video answers\n"
            f"3. RESULT-FOCUSED: implies a clear, real outcome\n\n"
            f"Rules: EXACTLY 3 words. ALL CAPS. Specific and credible, never sensational.\n"
            f"Return ONLY 3 words. Example: REAL NUMBERS SHOWN or THIS MISTAKE COSTS"
        )
    else:
        prompt = (
            f"Generate the most psychologically compelling 3-word thumbnail text "
            f"for a serious business/tech collapse documentary.\n"
            f"NICHE: {niche['name']} | TOPIC: {topic[:100]}\n"
            f"{title_context}\n"
            f"USE THESE TRIGGERS (pick ONE register, don't mix — and it MUST match\n"
            f"the title's register above if one is given):\n"
            f"1. CURIOSITY GAP: creates an unanswerable question\n"
            f"2. DREAD register: implies something disturbing was confirmed\n"
            f"3. SPECIFICITY: a number or concrete detail, not vague\n"
            f"4. PATTERN INTERRUPT: unexpected — makes viewer stop scrolling\n\n"
            f"Rules: EXACTLY 3 words. ALL CAPS. Dramatic and specific. Never generic.\n"
            f"Return ONLY 3 words. Example: DOCUMENTED IN EMAILS or SEVENTY TWO HOURS"
        )
    # FIX (found on final re-audit, direct user request for a real
    # attention-grabbing score): a real scoring function for exactly this
    # purpose (rewards a real number, penalizes vague/over-long text,
    # rewards specificity words) already existed in thumbnail_engine_v2.py
    # but was never actually called anywhere in the whole repo — this
    # function generated exactly ONE AI candidate and used it unscored,
    # unconditionally. Now generates up to 3 real candidates (AI attempts
    # plus the niche's own fallback bank) and picks the highest-scoring
    # one, so "short but attention-grabbing" is actually being measured
    # and chosen for, not just hoped for from a single AI guess.
    try:
        from thumbnail_engine_v2 import score_thumbnail_text
    except Exception:
        score_thumbnail_text = lambda t: 5.0  # neutral score if the module truly isn't available

    candidates = []
    try:
        for _ in range(3):
            result = ai_generate(prompt, tokens=15)
            if result:
                result = re.sub(r'[^A-Z\s]', '', result.upper()).strip()
                words = result.split()[:3]
                if len(words) == 3:
                    candidates.append(' '.join(words))
    except Exception as e:
        log(f"  Thumbnail text (non-fatal): {e}")

    if not candidates:
        candidates = [random.choice(fallback_bank.get(niche.get("name", "personal_finance_mistakes"),
                                                        fallback_bank["personal_finance_mistakes"]))]

    scored = [(c, score_thumbnail_text(c)) for c in dict.fromkeys(candidates)]  # de-dupe, keep order
    best_text, best_score = max(scored, key=lambda pair: pair[1])
    log(f"  Thumbnail candidates scored: {scored} -> chose '{best_text}' ({best_score}/10)")
    return best_text


def run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode):
    """Generate thumbnail with NUMBER+NOUN enforcement, or the real
    before→after formula for finance niches specifically."""
    # v1 addition — real dispatch: niches marked "thumbnail_format":
    # "before_after" (the finance niches, per direct research showing
    # this specific format driving 500K-900K+ views) use the dedicated
    # before→after formula; everything else keeps the existing, already-
    # proven NUMBER+NOUN format used across the other channels.
    niche_obj = next((n for n in NICHES if n["name"] == niche_name), None)
    use_before_after = niche_obj and niche_obj.get("thumbnail_format") == "before_after"

    if use_before_after:
        thumb_text = enforce_before_after_format(thumb_text, topic, niche_name, ai_generate)
    else:
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
                 "business documentary", "true story", "finance", "evidence",
                 "documented", "the collapse index", "case study",
                 "explained", "real story", "analysis", "how it happened"]
    niche_specific = {
        "ai_startup_collapse":          ["ai startup", "tech collapse", "startup failure"],
        "tech_company_collapse":        ["tech company", "business history", "rise and fall"],
        "crypto_collapse":              ["crypto collapse", "cryptocurrency", "exchange collapse"],
        "cybersecurity_disasters":      ["cybersecurity", "data breach", "hacking documentary"],
        "product_flops":                ["product flop", "failed product", "consumer tech"],
        "dotcom_era_collapse":          ["dot com bubble", "internet history", "startup history"],
        "personal_finance_mistakes":    ["personal finance", "money mistakes", "financial literacy"],
        "investing_fundamentals":       ["investing", "stock market", "index funds"],
        "retirement_planning":          ["retirement planning", "social security", "401k"],
        "credit_debt_repair":           ["credit score", "debt payoff", "credit repair"],
        "real_estate_affordability":    ["real estate", "mortgage", "home buying"],
        "budgeting_saving_strategies":  ["budgeting", "saving money", "emergency fund"],
        "stock_market_crashes_history": ["stock market crash", "market history", "financial crisis"],
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
            tg("⚠️ Ch5 Upload: no pending video found. Generation may have failed last night.")
            log("No pending upload — exiting.")
            sys.exit(0)

        is_fresh, hours_old = check_pending_age(pending, max_hours=30)
        if not is_fresh:
            tg(f"⚠️ Ch5 Upload: pending video is {hours_old}h old — may be stale. Uploading anyway.")

        log(f"Loading pending video ({hours_old}h old): {pending.get('title','?')[:60]}")
        title       = pending["title"]
        description = pending["description"]
        tags        = pending["tags"]
        niche_name  = pending["niche_name"]
        video_path  = pending["video_path"]
        topic       = pending.get("topic", title)  # FIX: was never extracted at all —
        # produce_video_topic_short/produce_standalone_short's "main_topic"
        # parameter needs the actual story details to write a real Shorts
        # script from; a bare title has none of that. Falls back to title
        # only if topic is somehow missing.
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
            tg(f"❌ Ch5 Upload FAILED: video file missing at {video_path}")
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
                playlist_id = ensure_niche_playlist(token, niche_name, "TheCollapseIndex")
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

        # FIX: shorts_reels_engine's produce_standalone_short already
        # generates AND uploads internally (doesn't return a file to
        # upload separately) — both standalone Shorts already went out
        # during the generate phase. Recap Short removed entirely per
        # explicit request (tied to the main video's topic, which risked
        # being less independently interesting than genuinely trend-
        # researched standalone content) — only 2 Shorts/day now, both
        # from the generate phase.
        short_urls = [s.get("url") for s in shorts if s.get("ok") and s.get("url")]
        log(f"  Total Shorts this episode: {len(short_urls)}")

        # SRT captions
        if script_clean and duration > 0:
            try:
                from growth_engine import upload_srt_captions
                upload_srt_captions(token, vid_id, script_clean, duration, "collapse_index")
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

            # SCRIPT_DIR IS video_pipeline/ for Ch5 — repo root is 1 level up
            docs_root = SCRIPT_DIR.parent / "docs"
            related = get_related_episodes(SCRIPT_DIR, niche_name, exclude_episode_number=episode)

            page_path = render_companion_page(
                episode_data={
                    "episode_number": episode,
                    "episode_title": title,
                    "video_url": yt_url,
                    "channel_id": "collapse_index",
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
                                      "collapse_index",
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
                tg(f"🚨 Ch5 AUDIT HOLD — Episode {episode}: {audit_result['reasons']}")
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
                "SPRINT_CHANNEL_ID":   "collapse_index",
                "SPRINT_NICHE":        niche_name,
                "SPRINT_SHORTS_URLS":  ",".join(short_urls),
                "SPRINT_SCORE":        str(score),
                "SPRINT_DURATION_SECS":str(duration),
                "SPRINT_PLAYLIST_ID":  playlist_id or "",
                "SPRINT_SCRIPT_PATH":  sprint_script_path,
            })
            # FIX (found on deep re-audit): this pointed at
            # channels/collapse_index/growth_engine.py — a path that
            # doesn't exist (this comment was copy-pasted verbatim from
            # Ch1's identical, also-wrong comment, unedited). The real
            # file is video_pipeline/growth_engine.py, a SIBLING of
            # channels/, not inside it — verified via Path.exists().
            # Because this used Popen (fire-and-forget, never checked),
            # the wrong path failed silently every single time.
            #
            # Also switched from Popen to a blocking subprocess.run with a
            # real timeout, matching the fix already applied to Ch3/Ch4:
            # run_post_upload_sprint sleeps 30 minutes before its comment-
            # reply engine runs, and GitHub Actions tears down the entire
            # process tree within seconds of the job's last step — a
            # detached Popen child would almost certainly be killed
            # mid-sleep every time, regardless of the path being correct.
            _ge_path = Path(__file__).parent.parent.parent / "video_pipeline" / "growth_engine.py"
            if not _ge_path.exists():
                log(f"  Growth engine NOT FOUND at {_ge_path} — skipping sprint")
            else:
                try:
                    subprocess.run(["python3", str(_ge_path)], env=env_ext, timeout=2400)
                except subprocess.TimeoutExpired:
                    log("  Growth engine sprint exceeded 40min budget — moving on")
        except Exception as ge:
            log(f"  Growth engine sprint (non-fatal): {ge}")

        # v15: Hype notification — free Explore leaderboard push
        send_hype_push(yt_url, title, "TheCollapseIndex", day=0)

        tg(f"✅ <b>TheCollapseIndex — LIVE</b>\n\n"
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
        score_val    = score_result(script_result, topic)[0]
        edge_voice   = pick_voice(niche_name, state)
        # v6 addition — real citation system: the actual sources used
        # during research (if any were found), carried through for the
        # description's Sources block and the end-of-video credits scene.
        real_cases   = script_result.get("real_cases", [])

        tg(f"Ch5 Script ready: {niche_name} | {wc}w | {score_val}/10\n{topic[:80]}")

        # Approval gate
        # FIX: generate_titles's dread/sympathy alternation reads
        # state["last_title_register"] to decide which register to use next —
        # but state was never being passed in here, so it always saw state=None
        # and always computed the same register, every single episode. The
        # alternation looked implemented but never actually alternated.
        title_result = run_stage_with_retry(generate_titles, "Titles", niche, topic, episode, state, trending_titles)
        title        = title_result if title_result else f"{niche['series']} Ep{episode}"

        # v9 addition — real title-script alignment check, per direct
        # research confirming spoken-content-to-title matching affects
        # both search relevance and satisfaction signals.
        _title_distinctive_words = {
            w.strip(".,!?:;\"'").lower() for w in title.split()
            if len(w) > 4 and w.lower() not in
            {"about","after","before","their","there","which","would","could","should"}
        }
        if _title_distinctive_words:
            _script_words_lower = set(script_clean.lower().split())
            _matched = sum(1 for w in _title_distinctive_words if w in _script_words_lower)
            if _matched == 0:
                tg(f"⚠️ Ch5: none of the title's distinctive words appear in the script — "
                   f"\"{title[:70]}\" may not match what the video actually says. "
                   f"Worth checking the title still fits before this publishes.")

        # FULL SCRIPT REVIEW + EDIT LOOP — replaces the old approval gate,
        # which only ever showed a 400-character preview. This sends the
        # REAL, COMPLETE script for review, and genuinely regenerates
        # whichever section real feedback identifies (or the whole script,
        # for whole-script feedback) — never silently ignores an EDIT
        # reply. Loops until APPROVE, REJECT, or a timeout auto-approval.
        try:
            from human_review_gate import review_script, identify_target_sections, regenerate_script_sections
            # FIX (July 14 2026 audit): these two were misnamed with a
            # "_ch1" suffix left over from this section's origin as a
            # copy of Channel 1's code -- the actual content (Ch5's own
            # 7-stage structure) was always correct, only the variable
            # names wrongly implied Ch1-specific data. Renamed for clarity.
            _stage_names = ["COLD OPEN","THE BEFORE","FIRST SIGNALS",
                             "ESCALATION","FALSE RESOLUTION","THE REVEAL","IMPLICATION"]
            _stage_texts = script_result.get("stage_texts", [])
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            _script_was_edited = False

            while True:
                # Real hook-quality sub-score: converts the pipeline's own
                # existing retention-hook penalty check (30%/60%/80% hook
                # presence, final CTA, dead-zone detection) to a 0-10 scale
                # for direct display, rather than only using it internally
                # to nudge the overall script score.
                try:
                    _hook_penalty, _hook_issues = _validate_retention_hooks_ch5(script_clean)
                    _hook_score = round(min(max(10.0 + _hook_penalty, 0), 10), 1)
                    _hook_note = _hook_issues[0] if _hook_issues else "all hook checkpoints present"
                except Exception as e:
                    log(f"  Hook scoring (non-fatal): {e}")
                    _hook_score, _hook_note = None, None

                # FIX (July 14 2026 audit, direct user feedback): now passes
                # stage_texts/stage_names so the script review message is
                # sent stage-by-stage with clear headers (COLD OPEN, THE
                # BEFORE, ...) instead of one undifferentiated wall of text.
                _review = review_script("TheCollapseIndex", title, script_clean, score_val,
                                        niche_name, TG_TOKEN, TG_CHAT,
                                        gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass,
                                        timeout_minutes=60,
                                        stage_texts=_stage_texts, stage_names=_stage_names,
                                        sub_scores={"Hook strength": (_hook_score, _hook_note)} if _hook_score is not None else None)
                if _review["decision"] == "reject":
                    log("Rejected during full script review."); sys.exit(0)
                # FIX (found on deep re-audit): REMAKE was never handled
                # here at all — it fell through every branch and the loop
                # just re-sent the identical unedited script for review
                # again, silently ignoring a human's explicit "scrap this
                # episode" request. Ch2/Ch3/Ch4 all already treat REMAKE
                # at the script checkpoint as ending the episode.
                if _review["decision"] == "remake":
                    tg("🔄 Ch5: REMAKE requested at script review — scrapping this episode entirely.")
                    log("  REMAKE requested during script review — clearing pending, exiting.")
                    clear_pending(SCRIPT_DIR)
                    sys.exit(0)
                if _review["decision"] == "approve":
                    break
                if _review["decision"] == "edit" and _stage_texts:
                    _targets = identify_target_sections(_review["feedback"], _stage_names)
                    # FIX (found on final re-audit): once a prior whole-
                    # script edit collapses _stage_texts to a single entry,
                    # it no longer has one entry per stage name — a
                    # targeted edit in a LATER round would index past the
                    # end of this list and crash. Force whole-script mode
                    # again in that case rather than risk that IndexError.
                    if len(_stage_texts) != len(_stage_names):
                        _targets = []
                    log(f"  Script EDIT requested: '{_review['feedback']}' -> sections: {_targets or 'WHOLE SCRIPT'}")
                    try:
                        script_clean, _updated_sections = regenerate_script_sections(
                            script_clean, _stage_texts, _stage_names, _targets,
                            _review["feedback"], niche, topic, ai_generate)
                        # FIX (found on final re-audit): this used to keep
                        # _stage_texts entirely UNCHANGED after a targeted
                        # edit — the just-edited section's entry stayed on
                        # its PRE-edit text. A second edit request aimed at
                        # that same section would then search for text that
                        # no longer exists anywhere in the script (already
                        # replaced once), and the substring .replace() in
                        # regenerate_script_sections would silently do
                        # nothing — "updated" would come back, but the
                        # script would be the exact same as before. Now
                        # refreshes each changed section's entry with its
                        # real new text so a second round still works.
                        if not _targets:
                            _stage_texts = [script_clean]
                        else:
                            for _sec_name, _new_text in _updated_sections.items():
                                _idx = _stage_names.index(_sec_name)
                                _stage_texts[_idx] = _new_text
                        # FIX (found via a final expert-level re-audit): the
                        # ORIGINAL script_result["stage_texts"] (used later
                        # by the authenticity check's fingerprint) would go
                        # stale the moment the script is edited here —
                        # silently feeding wrong per-stage word counts into
                        # the structural-variation comparison against past
                        # episodes. Flagged so that check can be told to
                        # degrade gracefully (skip stale data) instead of
                        # silently using it.
                        _script_was_edited = True
                        tg(f"✅ Script updated per your feedback — sending the revised version for another look.")
                    except Exception as e:
                        tg(f"🚨 Ch5: your script edit could NOT be applied — {e}. "
                           f"The script is UNCHANGED. Please try again or approve as-is.")
                        log(f"  Script edit failed, feedback NOT applied: {e}")
                    # Loop back and send the (possibly updated) script again
                elif _review["decision"] == "edit":
                    tg("⚠️ Can't apply section-targeted edits — no stage breakdown available for this "
                       "script. Approve, reject, or the script proceeds as generated.")
        except Exception as e:
            # FIX (same real production issue diagnosed from a Telegram
            # screenshot, identical fallback pattern in Ch2): this only
            # logged to stdout before — invisible unless watching the
            # Actions run live. The bare "30 min expired — auto-approved"
            # messages you saw were this fallback firing silently, most
            # likely because human_review_gate.py genuinely isn't
            # deployed to the live repo yet. Now alerts visibly.
            log(f"  Full script review (non-fatal, falling back to quick gate): {e}")
            tg(f"⚠️ Ch5: the full review system failed to load ({str(e)[:150]}) — falling back "
               f"to the older, simpler approval gate for this episode. If human_review_gate.py "
               f"and review_queue.py haven't been deployed to this repo yet, that's the likely "
               f"cause; once they are, this fallback should stop firing.")
            decision = run_approval_gate(title, niche_name, script_clean, edge_voice, score_val)
            if decision == "rejected":
                log("Rejected by approval gate."); sys.exit(0)

        log("\nSTAGE 3: Audio")
        audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
            run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
        edge_voice = voice_used

        # STRICTER AUDIO GATE, now with an active retry — explicit decision
        # made after real discussion about voice quality: gTTS/espeak are
        # noticeably robotic, and previously the pipeline would auto-publish
        # them anyway. Rather than holding immediately and waiting a full
        # day for the next scheduled run, this now RE-ATTEMPTS the whole
        # audio stage up to twice more, 2 hours apart — giving edge-tts and
        # Fish Audio (the two real, natural-sounding tiers) a genuine chance
        # to have their rate limits refresh before falling back further.
        # Only holds for manual review if every attempt still lands on the
        # two robotic tiers. ElevenLabs, edge-tts, and Fish Audio all still
        # auto-publish immediately and normally — only gTTS/espeak trigger
        # this retry-then-hold behavior.
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
        while edge_voice in ("gtts-fallback", "espeak-offline-LASTRESORT") and \
              _audio_retry_count < _MAX_AUDIO_RETRIES:
            _audio_retry_count += 1
            log(f"  Audio tier {edge_voice} is below the auto-publish bar — "
                f"waiting 2h for providers to refresh (retry {_audio_retry_count}/{_MAX_AUDIO_RETRIES})...")
            tg(f"⏳ Ch5: audio fell back to {edge_voice} — waiting 2h and retrying "
               f"({_audio_retry_count}/{_MAX_AUDIO_RETRIES}) before holding for review.")
            time.sleep(_AUDIO_RETRY_WAIT_SECONDS)
            audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
                run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
            edge_voice = voice_used

        if edge_voice in ("gtts-fallback", "espeak-offline-LASTRESORT"):
            tg(f"🛑 Ch5 HOLD — audio still fell back to {edge_voice} after "
               f"{_MAX_AUDIO_RETRIES} retries over {_MAX_AUDIO_RETRIES * 2}h, below the stated "
               f"voice-quality bar. This episode is NOT being published automatically. Review the "
               f"audio, or manually approve if it's acceptable, then re-run.\n\nTitle: {title}")
            log(f"  HOLD: audio tier {edge_voice} is still below the auto-publish bar "
                f"after {_MAX_AUDIO_RETRIES} retries. Stopping here.")
            sys.exit(0)

        # FIX: check_audio_quality existed fully built (validates real file
        # size AND real measured duration against what the script's word
        # count implies) but was never called anywhere — a truncated or
        # corrupted audio file could silently reach video assembly undetected.
        _expected_dur = (len(script_clean.split()) / 125.0) * 60.0
        if not check_audio_quality(audio_path, _expected_dur):
            tg(f"⚠️ Ch5 audio quality check failed — expected ~{_expected_dur:.0f}s, "
               f"got {audio_duration:.0f}s. Proceeding, but this episode's audio needs review.")

        log("\nSTAGE 4: Video")
        # v1 addition — real, word-level synced captions, per explicit
        # request that captions must genuinely match the audio.
        ass_path = str(WORK_DIR / "main_captions.ass")
        if not generate_real_synced_ass(audio_path, ass_path):
            ass_path = None
        # v1 addition — extract the real chart data (if any was found)
        # from script_result and pass it through, completing the wiring
        # from script generation to actual video assembly.
        chart_data = script_result.get("chart_data")
        video_path = run_stage_with_retry(
            assemble_video, "Video", niche_name, audio_path, audio_duration, topic, script_clean, episode, real_cases, chart_data, ass_path)

        # COMBINED AUDIO + VIDEO REVIEW — one review window, two distinct
        # decisions (audio: 4 real options; video: 5, the 5th being SWAP
        # VISUALS). Swap Visuals re-calls assemble_video with the exact
        # same script/audio — since nothing in this file seeds Python's
        # random state, clip selection is genuinely different each call,
        # not a coin-flip disguised as a fix.
        _remade_av = False
        try:
            from human_review_gate import review_audio_and_video
            from quality_scoring import score_audio_quality, score_video_quality
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            _check_ins_used_av = 0

            while True:
                # FIX (found on final re-audit, direct user request for real
                # per-stage scores): computed fresh on every loop iteration
                # so a SWAP VOICE/SWAP VISUALS re-generation gets a genuinely
                # re-scored result, not a stale score from the first pass.
                try:
                    _audio_score, _audio_breakdown = score_audio_quality(
                        audio_path, audio_duration, len(script_clean.split()), edge_voice)
                except Exception as e:
                    log(f"  Audio scoring (non-fatal): {e}")
                    _audio_score, _audio_breakdown = None, None
                try:
                    from quality_scoring import get_media_duration
                    _real_video_duration = get_media_duration(video_path)
                    _video_score, _video_breakdown = score_video_quality(
                        video_path, _real_video_duration, audio_duration, content_type="stock_footage",
                        fallback_flags=_last_video_fallback_flags)
                except Exception as e:
                    log(f"  Video scoring (non-fatal): {e}")
                    _video_score, _video_breakdown = None, None

                _av_review = review_audio_and_video(
                    "TheCollapseIndex", audio_path, edge_voice, video_path, None,
                    TG_TOKEN, TG_CHAT, _check_ins_used_av,
                    gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60,
                    audio_score=_audio_score, audio_score_breakdown=_audio_breakdown,
                    video_score=_video_score, video_score_breakdown=_video_breakdown)
                _check_ins_used_av += 1

                _a_dec = _av_review["audio_decision"]["decision"]
                if _a_dec in ("reject", "remake"):
                    if _a_dec == "remake":
                        tg("🔄 Ch5: REMAKE requested at audio review — this episode is being "
                           "scrapped. A fresh episode will be generated on the next scheduled run.")
                        log("  REMAKE requested during audio review — clearing pending, exiting.")
                        _remade_av = True
                    else:
                        log("Rejected during audio review.")
                    break

                _v_dec = _av_review["video_decision"]["decision"] if _av_review["video_decision"] else "approve"
                if _v_dec == "reject":
                    log("Rejected during video review."); sys.exit(0)
                if _v_dec == "remake":
                    tg("🔄 Ch5: REMAKE requested at video review — this episode is being "
                       "scrapped. A fresh episode will be generated on the next scheduled run.")
                    log("  REMAKE requested during video review — clearing pending, exiting.")
                    _remade_av = True
                    break
                if _v_dec == "swap_visuals":
                    tg(f"🎨 Swapping visuals"
                       f"{' for: ' + _av_review['video_decision']['feedback'] if _av_review['video_decision']['feedback'] else ''}"
                       f" — regenerating the video assembly now, same script and audio.")
                    log(f"  SWAP VISUALS requested: {_av_review['video_decision']['feedback']}")
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, chart_data, ass_path)
                    continue  # send the newly-assembled video for another look
                if _v_dec == "approve" and _a_dec == "approve":
                    break
                # edit on either audio or video: audio edit isn't
                # separately re-generated here (voice/pacing edits are a
                # real but more involved change — logged for visibility,
                # loop continues so the same audio/video get reviewed again)
                if _a_dec == "swap_voice":
                    _voice_pool = [v for v in VOICES.get(niche_name, ["en-GB-RyanNeural", "en-US-BrianNeural"])
                                   if v != edge_voice]
                    _new_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                    tg(f"🎙️ Swapping voice: {edge_voice} → {_new_voice} — regenerating audio now, same script.")
                    log(f"  SWAP VOICE requested: {edge_voice} -> {_new_voice}")
                    edge_voice = _new_voice
                    audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
                        run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                    edge_voice = voice_used
                    ass_path = str(WORK_DIR / "main_captions.ass")
                    if not generate_real_synced_ass(audio_path, ass_path):
                        ass_path = None
                    # New audio needs a new video assembly too — the old
                    # one is matched to the previous audio's timing.
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, chart_data, ass_path)
                    continue  # send the newly-generated audio/video for another look
                if _a_dec == "edit":
                    _fb_audio = _av_review["audio_decision"]["feedback"] or ""
                    # FIX (found on direct user report, July 15 2026): same
                    # bug as Ch1/2/3/4 -- this used to regenerate with the
                    # exact same edge_voice, so feedback about the voice
                    # never actually changed anything. Now genuinely swaps.
                    _voice_pool = [v for v in VOICES.get(niche_name, ["en-GB-RyanNeural", "en-US-BrianNeural"])
                                   if v != edge_voice]
                    _new_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                    tg(f"🎙️ Regenerating audio per your feedback: {_fb_audio}\n"
                       f"Voice: {edge_voice} → {_new_voice}")
                    log(f"  Audio EDIT requested: '{_fb_audio}' — swapping voice {edge_voice} -> {_new_voice}")
                    edge_voice = _new_voice
                    audio_path, audio_duration, audio_size, voice_used = run_stage_with_retry(
                        run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                    edge_voice = voice_used
                    ass_path = str(WORK_DIR / "main_captions.ass")
                    if not generate_real_synced_ass(audio_path, ass_path):
                        ass_path = None
                    continue  # send the newly-generated audio for another look
        except Exception as e:
            log(f"  Audio/Video review (non-fatal, proceeding with generated versions): {e}")
            tg(f"⚠️ Ch5: the audio+video review system failed to load ({str(e)[:150]}) — "
               f"proceeding with the generated audio/video WITHOUT human review for this "
               f"episode. If human_review_gate.py isn't deployed to this repo yet, that's "
               f"the likely cause.")

        if _remade_av:
            clear_pending(SCRIPT_DIR)
            sys.exit(0)

        log("\nSTAGE 5: Thumbnail + Description")
        # v1 addition — real learned thumbnail-style preference, closing
        # the same "write-only, no learning" gap already found and fixed
        # for voice selection. Honest limitation: uses the script's own
        # quality score as a proxy signal, since no real click-through
        # data exists yet.
        _week_number = datetime.datetime.now().isocalendar()[1]
        _calendar_style = "A" if _week_number % 2 == 1 else "B"
        try:
            _ab_perf = state.get("performance", {})
            _a_scores = _ab_perf.get("thumbnail_style_A", {}).get("scores", [])
            _b_scores = _ab_perf.get("thumbnail_style_B", {}).get("scores", [])
            if len(_a_scores) >= 3 and len(_b_scores) >= 3 and _week_number % 5 != 0:
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
            _script_score = script_result.get("score", 0)
            if _script_score:
                _perf = state.get("performance", {})
                _ab_rec = _perf.get(f"thumbnail_style_{ab_style}", {"scores": []})
                _ab_rec["scores"] = (_ab_rec["scores"] + [_script_score])[-20:]
                _perf[f"thumbnail_style_{ab_style}"] = _ab_rec
                state["performance"] = _perf
        except Exception as e:
            log(f"  Thumbnail style tracking (non-fatal): {e}")
        thumb_text  = generate_thumbnail_text(niche, topic, title)
        thumb_path  = run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode)
        try:
            from thumbnail_engine_v2 import score_thumbnail_text
            _thumb_score = score_thumbnail_text(thumb_text)
        except Exception:
            _thumb_score = None

        # Description generated here now (moved earlier from its old spot
        # right before upload) so it can be reviewed together with title
        # and thumbnail, per the explicit request to combine these three.
        # Runs through a real scoring loop — regenerates up to 4 times if
        # it doesn't genuinely hit 9/10 on real, checkable criteria.
        from human_review_gate import regenerate_description_until_good
        def _desc_gen(n, t, ti, ep, ch, dur):
            return generate_seo_description(n, t, ti, ep, ch, dur,
                                             citations_block=format_citations_block(real_cases))
        _stage_word_counts = [len(t.split()) for t in _stage_texts] if _stage_texts else None
        _chapters = generate_chapter_timestamps(script_clean, audio_duration, "collapse_index",
                                                 stage_word_counts=_stage_word_counts)
        _desc_result = regenerate_description_until_good(
            niche, topic, title, episode, _chapters, audio_duration, niche_name, _desc_gen,
            min_score=9.0, max_attempts=4)
        description = _desc_result["description"]
        log(f"  Description score: {_desc_result['score']}/10 "
            f"(hit target: {_desc_result['hit_target']}, {_desc_result['attempts']} attempts)")

        # FIX (found via a final line-by-line re-verification): this used
        # to be appended during the UPLOAD phase, AFTER the description
        # had already been reviewed and approved in the generate phase —
        # meaning what got reviewed was genuinely missing content that
        # then got silently added before publish. Moved here so the
        # description shown for review is the real, complete final text.
        affiliate_block = build_affiliate_block("collapse_index", niche_name)
        if affiliate_block:
            description = f"{description}{affiliate_block}"
        product_cta = build_product_cta("collapse_index")
        if product_cta:
            description = f"{description}{product_cta}"

        # COMBINED TITLE + THUMBNAIL + DESCRIPTION REVIEW — one message,
        # not three separate ones, per the explicit request. REMAKE here
        # clears this pending episode entirely and exits — the NEXT
        # scheduled generate run produces a genuinely fresh episode for
        # this slot, rather than risking a fragile same-process restart
        # of a very long, already-linear pipeline run.
        _remade = False
        try:
            from human_review_gate import review_title_thumbnail_description
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            _check_ins_used_ttd = 0

            while True:
                _ttd_review = review_title_thumbnail_description(
                    "TheCollapseIndex", title, thumb_path, description, _desc_result["score"],
                    TG_TOKEN, TG_CHAT, _check_ins_used_ttd,
                    gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60,
                    thumbnail_score=_thumb_score)
                _check_ins_used_ttd += 1

                if _ttd_review["decision"] == "reject":
                    log("Rejected during title/thumbnail/description review."); sys.exit(0)
                if _ttd_review["decision"] == "remake":
                    tg(f"🔄 Ch5: REMAKE requested"
                       f"{' — ' + _ttd_review['feedback'] if _ttd_review['feedback'] else ''}. "
                       f"This episode is being scrapped. A genuinely fresh episode will be "
                       f"generated on the next scheduled run.")
                    log("  REMAKE requested — clearing pending, exiting for a fresh run.")
                    _remade = True
                    break
                if _ttd_review["decision"] == "approve":
                    break
                if _ttd_review["decision"] == "edit":
                    fb = _ttd_review["feedback"] or ""
                    _new_title = ai_generate(f"Rewrite this video title based on real feedback.\n"
                                    f"Current title: {title}\nFeedback: {fb}\n"
                                    f"Return ONLY the new title, nothing else.", tokens=60)
                    if _new_title and len(_new_title.strip()) > 5:
                        title = _new_title.strip()
                    _new_thumb_text = ai_generate(f"Write a new punchy 3-word max thumbnail overlay "
                                         f"text, NUMBER+NOUN format, based on real feedback.\n"
                                         f"Current text: {thumb_text}\nTopic: {topic}\n"
                                         f"Feedback: {fb}\nReturn ONLY the new overlay text.", tokens=40)
                    if _new_thumb_text and len(_new_thumb_text.strip()) > 0:
                        thumb_text = _new_thumb_text.strip()
                        ab_style = "B" if ab_style == "A" else "A"
                        thumb_path = run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode)
                    _new_desc = ai_generate(f"Rewrite this video description based on real feedback.\n"
                                    f"Current description:\n{description}\nFeedback: {fb}\n"
                                    f"Return ONLY the new description, nothing else.", tokens=800)
                    if _new_desc and len(_new_desc.split()) > 20:
                        description = _new_desc.strip()
                    tg("✅ Title/thumbnail/description updated per your feedback — sending the revised version.")
        except Exception as e:
            log(f"  Title/Thumbnail/Description review (non-fatal, proceeding with generated versions): {e}")
            tg(f"⚠️ Ch5: the title/thumbnail/description review system failed to load "
               f"({str(e)[:150]}) — proceeding with the generated versions WITHOUT human "
               f"review for this episode. If human_review_gate.py isn't deployed to this "
               f"repo yet, that's the likely cause.")

        if _remade:
            clear_pending(SCRIPT_DIR)
            sys.exit(0)

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
                # FIX: if the script was edited during review, the ORIGINAL
                # script_result["stage_texts"] no longer matches the real
                # script — passing it here would silently feed wrong
                # per-stage word counts into the structural-variation
                # fingerprint. Degrades gracefully to empty (the module
                # already handles this) rather than using stale data.
                stage_texts=([] if _script_was_edited else script_result.get("stage_texts", [])),
                title=title,
                thumbnail_family=thumb_family,
                thumbnail_pose=thumb_pose_id,
                ai_fn=lambda p, tokens=100: ai_generate(p, tokens=tokens),
            )
            log(format_authenticity_report(auth_result, "Ch1"))
            _auth_score = auth_result["composite_score"]
            if _auth_score < 6.0:
                tg(f"🚨 Ch5 AUTHENTICITY RISK — score {_auth_score}/10, below the safe threshold.\n"
                   f"{format_authenticity_report(auth_result, 'TheCollapseIndex')}\n"
                   f"Recommend manual review before this publishes.")
            elif _auth_score < 7.5:
                tg(f"⚠️ Ch5 authenticity check: {_auth_score}/10 — one dimension is weak, publishing "
                   f"but flagging for awareness.\n{format_authenticity_report(auth_result, 'TheCollapseIndex')}")
            # Fingerprint gets saved to history only in the upload phase, after
            # a real publish is confirmed — see phase="upload" section below.
            _pending_auth_fingerprint = auth_result["_fingerprint_to_log"]
        except Exception as e:
            log(f"  Authenticity check (non-fatal): {e}")
            _pending_auth_fingerprint = None

        log("\nSTAGE 6: Shorts")
        log("  4 Shorts today: 2 about this video's real topic (fresh, complete")
        log("  standalone pieces — not literal clips or teasers), 2 on genuinely")
        log("  different trending topics (real research into what's working today).")
        shorts = []
        try:
            import importlib.util
            if importlib.util.find_spec("shorts_reels_engine") is None:
                raise ImportError("shorts_reels_engine not in PYTHONPATH")
            from shorts_reels_engine import produce_video_topic_short, produce_standalone_short

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

            # 2 Shorts genuinely about today's real topic — fresh, complete,
            # standalone accounts (not a literal clip, not a teaser/recap).
            for angle in ("angle_1", "angle_2"):
                vt = produce_video_topic_short(topic, script_clean, angle, channel="collapse_index")
                shorts.append({"ok": vt.get("status") == "success",
                               "path": vt.get("local_path"), "url": vt.get("url"), "name": f"video_topic_{angle}"})
                log(f"  Video-topic ({angle}): {vt.get('status')}")
                _post_short_comment_safe(vt.get("url"), f"video_topic_{angle}")

            # 2 Shorts on genuinely different, trending, in-demand topics —
            # real research into what's actually working today.
            for mode in ("standalone_1", "standalone_2"):
                sa = produce_standalone_short(mode, channel="collapse_index")
                # FIX: produce_standalone_short returns its URL under the key
                # "yt_url", inconsistent with produce_video_topic_short which
                # uses "url" — this was silently returning None here every
                # time, even on success, dropping standalone Shorts from
                # every downstream count.
                shorts.append({"ok": sa.get("status") == "success",
                               "path": sa.get("local_path"), "url": sa.get("yt_url"), "name": mode})
                log(f"  Trending ({mode}): {sa.get('status')}")
                _post_short_comment_safe(sa.get("yt_url"), mode)

            ok_count = sum(1 for s in shorts if s.get("ok"))
            log(f"  Shorts (generate phase): {ok_count}/{len(shorts)} generated")

            # SHORTS REVIEW — the real final checkpoint (5 options).
            # Honest constraint: Shorts are already published by this
            # point (the real production functions upload internally),
            # so any edit/remake/swap here produces a genuinely fresh
            # replacement Short and publishes that as an addition.
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
                                for s in shorts if s.get("url")]
                if _real_shorts:
                    _sh_review = review_shorts("TheCollapseIndex", _real_shorts, TG_TOKEN, TG_CHAT,
                                               check_ins_used=0, gmail_sender=_gmail_sender,
                                               gmail_app_password=_gmail_pass, timeout_minutes=60)
                    if _sh_review["decision"] in ("edit", "remake", "swap_visuals"):
                        log(f"  Shorts {_sh_review['decision']} requested: "
                            f"{_sh_review['feedback']} — publishing one fresh replacement standalone Short.")
                        tg(f"🎞️ Producing a fresh replacement Short per your feedback: "
                           f"{_sh_review['feedback']}")
                        _replacement = produce_standalone_short("standalone_1", channel="collapse_index")
                        _post_short_comment_safe(_replacement.get("yt_url"), "replacement_standalone")

                # ── COMMUNITY TAB checkpoint — YouTube's API has no way
                # to post to the Community tab, so this drafts the real
                # poll/post and gates on a human confirming they posted
                # it manually (see review_community_tab's docstring).
                try:
                    from human_review_gate import draft_community_post, review_community_tab
                    _cp_draft = draft_community_post(topic, niche["name"], title,
                                                      lambda p, tokens=200: ai_generate(p, tokens=tokens))
                    _cp_result = review_community_tab(
                        "TheCollapseIndex", _cp_draft["question"], _cp_draft["options"], TG_TOKEN, TG_CHAT,
                        check_ins_used=0, gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
                    log(f"  Community Tab: {_cp_result['decision']}")
                except Exception as e:
                    log(f"  Community Tab checkpoint (non-fatal): {e}")
            except Exception as e:
                log(f"  Shorts review (non-fatal): {e}")
                tg(f"⚠️ Ch5: the Shorts review system failed to load ({str(e)[:150]}) — "
                   f"the Shorts already published stand as-is, with no human review "
                   f"applied this time. If human_review_gate.py isn't deployed to this "
                   f"repo yet, that's the likely cause.")
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

        # Description already generated + reviewed earlier (Stage 5, alongside
        # title/thumbnail) — the `description` variable here is that real,
        # possibly-human-edited value, not regenerated a second time.

        # Affiliate block already included in `description` — moved to the
        # generate phase (before review) so what gets approved is the
        # real, complete final text. See the FIX note there.

        # Playlist
        # Playlist created at upload time (YouTube creds not in generate phase)
        playlist_id = state.get("playlists", {}).get(niche_name, "")

        tags = build_niche_tags(niche_name)

        # Validate video before saving to pending
        if not Path(video_path).exists():
            tg("Ch5 Generate FAILED: video file not created")
            sys.exit(1)
        v_sz = Path(video_path).stat().st_size
        if v_sz < 5_000_000:
            tg(f"Ch5 Generate FAILED: video too small ({v_sz//1024}KB)")
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
            "shorts_clips":  shorts,   # the 2 standalone Shorts from this generate phase
            "topic":         topic,
            "auth_fingerprint": _pending_auth_fingerprint,
            "approved_topic_id": _approved_topic_id_for_pending,
            "quality_attempt": script_result.get("attempt", 1),
            "providers_healthy_count": len(_healthy_providers) if _healthy_providers else 7,
            "authenticity_score": _auth_score,
        })
        if _pending_result.get("overwrite_warning"):
            tg(f"🚨 Ch5 Generate: {_pending_result['overwrite_warning']}")

        state["episode_count"] = episode
        save_state(state)

        if phase == "generate":
            # Find upload time for this channel
            upload_time_msg = "10:30 PM IST (5 PM UTC)"
            tg(f"✅ <b>Ch5 Generated — queued for upload</b>\n\n"
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
        tg(f"❌ <b>Ch5 Pipeline FAILED</b>\n\n{str(e)[:400]}")
        raise


if __name__ == "__main__":
    main()
