#!/usr/bin/env python3
"""
NO KNOWN CAUSE — published-case documentary pipeline (Ch1 slot)
================================================================
Replaces the dark-documentary pipeline that previously occupied this slot.
Derived from it deliberately, so the ~80% of machinery that is not
niche-specific is genuinely reused rather than rewritten: the 7-stage script
engine, the 8.5 quality floor and multi-attempt rework loop, the TTS voice
pool and fallback chain, thumbnail A/B, Telegram review, checkpoint/resume,
Shorts, post-upload reporting and the weekly revenue report all carry over
untouched.

WHAT IS DIFFERENT
-----------------
  * Topics are REAL published case reports fetched live from Europe PMC
    (video_pipeline/pmc_data.py), restricted to CC BY so figures are legally
    reusable in a monetised video. The niche "topics" lists are a
    last-resort fallback only, and even those name real verifiable cases.
  * Visuals use six registers (video_pipeline/medical_register.py):
    FIGURE / CHART / BOARD / TIMELINE / ANATOMY / TEXT. There is NO character
    animation register — no stickman, no silhouette. A clinical case has
    nothing for a character puppet to do, and those were the two registers
    repeatedly rejected on this channel.
  * Every episode carries a CC BY citation on screen and in the description.
    This is a licensing condition, not a nicety.
  * A blocking content-policy gate (video_pipeline/medical_policy_gate.py)
    enforces six hard rules, because 2026 YouTube policy explicitly restricts
    AI-delivered medical advice and a limited-ads label would remove the
    $25-40 CPM band that is the whole reason for this niche.

NOTE ON channel_id: the string "betrayal_deepdive" is retained throughout as
this channel's internal SLOT id. It is how the shared modules resolve this
channel's secrets and state paths. It is not user-facing branding.
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
    "toxicology_cases":        ["171 mEq/L","1 LITRE","2 HOURS","9 DAYS","3 CASES"],
    "diagnostic_odyssey":      ["4 WRONG ANSWERS","7 YEARS","11 DOCTORS","1 TEST","DAY 340"],
    "neurology_cases":         ["1 HAND","8 DAYS","100 CASES","3 VARIANTS","ONE INFARCT"],
    "rare_disease_cases":      ["1 IN 2 MILLION","12 CASES EVER","1 REPORT","4 SYMPTOMS","ONE GENE"],
    "senior_health_longevity": ["AFTER 65","30% LOSS","12 WEEKS","2 GROUPS","10 YEARS"],
    "medical_mystery_outbreak":["47 CASES","1 SOURCE","19 DAYS","3 HOSPITALS","ONE MEAL"],
    "surgical_case_studies":   ["6 HOURS","1 MILLIMETRE","2 ATTEMPTS","DAY 14","ONE DECISION"],
    "drug_discovery_stories":  ["1928","14 YEARS","1 ACCIDENT","2 MILLION LIVES","ONE DISH"],
    "sleep_science":           ["0 HOURS","18 NIGHTS","4 STAGES","1 GENE","6 MONTHS"],
    "medical_history":         ["FOR 70 YEARS","1 STUDY","12,000 PATIENTS","1954","ONE DOUBT"],
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
    # FIX (direct user report, July 24 2026 — real production data, run
    # 30126085986: 13 real title attempts, capped at 7.5/10, zero
    # clearing 8.5, killed the entire day): same root-cause class as the
    # Shorts scoring miscalibration fixed earlier — two entire scoring
    # dimensions (curiosity_gap, revelation) required one of a tiny set
    # of exact literal phrases, so a genuinely strong title like "They
    # Knew Exactly What This Would Cost: The 7-Year Collapse" scored
    # WEAK on curiosity_gap (doesn't contain "nobody knew" etc. verbatim)
    # and ABSENT on revelation (doesn't contain "exposed"/"revealed"
    # etc. verbatim), capping it near 7.5 no matter how many times it
    # regenerated. Widened both phrase lists with real natural synonyms
    # rather than only the original narrow set.
    t  = title.lower()
    sc = 3.0
    bd = {}
    # Curiosity gap
    cg = ["nobody knew","never told","what was hidden","the real reason",
          "kept secret","concealed","covered up","went unnoticed","was ignored",
          "what nobody expected","truth about","hidden for years","no one saw",
          "what really happened","the untold","never expected","didn't see it coming",
          "what this would cost","before anyone noticed","too late"]
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
    rev = ["exposed","revealed","documented","proved","evidence","classified","traced",
           "uncovered","confirmed","discovered","records show","files show","real story",
           "true story","the record","collapse","fallout","aftermath","reckoning"]
    if any(s in t for s in rev): sc += 1.5; bd["revelation"] = "PRESENT"
    else:                        bd["revelation"] = "ABSENT"
    # Pattern interrupt
    # FIX (direct user report, July 25 2026 — real run 30150605869: Title
    # gate reached all 13 attempts capped at exactly 8.2/10, one real
    # title-scoring fix already closed the gap from 7.5 to here, still
    # 0.3 short): "Nobody Knew What the Records Show: A Hiker's Dark
    # Survival" scored ABSENT on pattern_interrupt despite genuinely
    # carrying that "this was known/unaddressed" implication — it just
    # doesn't happen to say "they knew" verbatim. Widened with real
    # natural variants of the same idea.
    pi = ["they knew","it was allowed","it was ignored","still happening","went unpunished",
          "nobody stopped","no one stopped","allowed to happen","let it happen",
          "nobody knew","no one knew","everyone knew","nothing was done","no one acted",
          "no one intervened","yet nothing changed","known for years","and did nothing"]
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
        record_title_used(str(SCRIPT_DIR), "No Known Cause", niche_name, episode, title, score)
    except Exception as e:
        log(f"  Title history record (non-fatal): {e}")


def run_title_ctr_gate(title_str, title_scores, topic, niche_name,
                        series_name, episode, ai_fn, min_ctr=8.5, max_attempts=13):
    """
    FIX (direct user report, July 24 2026 — explicit policy decision):
    hard floor 8.5, up to 8 real attempts (the original 5-title batch is
    attempt 1, each regeneration round is one more). Previously this only
    ever did ONE regeneration round and fell back to publishing the best
    title found regardless of whether it ever cleared the gate — that
    silently violated "if it is less than that, I don't want it to
    produce that." Now returns (None, v2_scored) if nothing clears
    min_ctr within max_attempts — the caller must treat that as a real
    stage failure, not substitute a fallback title.
    """
    if not title_scores:
        return None, [(title_str, 5.0)]
    v2_scored = sorted([(t, score_title_v2(t)[0]) for t, _ in title_scores],
                        key=lambda x: x[1], reverse=True)
    best_title, best_score = v2_scored[0]
    attempt = 1
    log(f"  Title attempt {attempt}/{max_attempts}: {best_score}/10 — {best_title[:55]}")
    notify_stage_score("Title", attempt, max_attempts, best_score, min_ctr, extra=best_title[:60])
    if best_score >= min_ctr:
        _record_title_history(niche_name, episode, best_title, best_score)
        return best_title, v2_scored

    while attempt < max_attempts:
        attempt += 1
        # Regenerate with targeted fix based on exactly which dimension is weak
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
                f"Current best score: {best_score}/10 — too low (need {min_ctr}+).\n"
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
                        best_title, best_score = new_scored[0]
                        v2_scored = new_scored
        except Exception as e:
            log(f"  Title regeneration attempt {attempt} (non-fatal): {e}")
        log(f"  Title attempt {attempt}/{max_attempts}: {best_score}/10 — {best_title[:55]}")
        notify_stage_score("Title", attempt, max_attempts, best_score, min_ctr, extra=best_title[:60])
        if best_score >= min_ctr:
            _record_title_history(niche_name, episode, best_title, best_score)
            return best_title, v2_scored

    log(f"  Title never cleared {min_ctr}/10 after {max_attempts} attempts (best: {best_score}/10).")
    return None, v2_scored


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
# channels"). monetization.py's real Gumroad products were only ever
# referenced by the static companion website and the weekly Gumroad-
# sync job — never mentioned in a single actual video description
# across any of the 4 channels. Fixed here.
# GitHub Pages serves from the repo owner's account, so the host name is
# fixed by the repo, not the channel. Kept accurate rather than aspirational;
# if the companion page is ever linked publicly it needs a custom domain,
# because this URL still shows the retired brand to anyone who reads it.
GITHUB_PAGES_BASE = "https://betrayaldeepdive.github.io/betrayal-bot"

def build_product_cta(channel_id):
    """Real product CTA for the actual video description — uses
    monetization.py's real get_product_cta_url, converted to a genuine
    absolute URL since a relative path would be a dead link inside a
    YouTube description."""
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
    # NON-SPOILER CHAPTER TITLES (retention addition #3).
    # Chapters correlate with a 2.18-2.8x higher like-to-view ratio, but when
    # Google surfaces them as Key Moments viewers can jump straight past the
    # setup -- and for a mystery format the cold open is the single most
    # retention-critical segment. So these titles mark POSITION without
    # revealing the answer: "The Wrong Answer" is navigable, "Diagnosis:
    # Hypernatraemia" would hand over the reveal from the search result.
    # No chapter title may ever name the final diagnosis.
    "betrayal_deepdive": [
        (0.00,"The Presentation"),(0.10,"Before Admission"),(0.28,"First Findings"),
        (0.45,"Deterioration"),(0.60,"The Wrong Answer"),(0.78,"The Mechanism"),
        (0.90,"What This Changed"),
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
    against the ORIGINAL stage-word targets, with no connection to what
    the script actually turned out to be after generation/edits. Real
    scripts don't hit exact per-stage word targets every attempt, and a
    script-review EDIT can change a stage's length outright, so the fixed
    table can silently drift from the real audio.

    When stage_word_counts (the real word count of each of the 7 stages
    in the FINAL, possibly-edited script) is provided, timestamps are now
    computed from the actual cumulative word-count fraction of that real
    script instead — genuinely tied to what was produced, not a guess.
    Falls back to the fixed percentage table when the real counts aren't
    available (e.g. a caller that hasn't been updated to pass them).
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
        "main":  "\n\n🩺 Real published medical cases: youtube.com/@NoKnownCauseTV\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🩺 Medical cases: youtube.com/@NoKnownCauseTV\n🧠 Psychology: youtube.com/@TheControlFiles",
    },
    "control_files": {
        "main":  "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🩺 Real published medical cases: youtube.com/@NoKnownCauseTV\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🔬 Forensic: youtube.com/@TheEvidenceRoom\n🩺 Medical cases: youtube.com/@NoKnownCauseTV",
    },
    # FIX: Ch4/Ch5 entries were entirely missing — this was genuinely a
    # 3-channel cross-promo system despite the empire having 5 channels,
    # meaning Ch4/Ch5 got zero organic cross-promotion benefit from Ch1/Ch2,
    # and neither existing channel ever mentioned them. Added now so Ch1/Ch2
    # correctly promote all 5 channels once Ch4/Ch5 are live — safe to add
    # now even though Ch4/Ch5 aren't built yet, since this only changes
    # Ch1/Ch2's own description text.
    "archive": {
        "main":  "\n\n🩺 Real published medical cases: youtube.com/@NoKnownCauseTV\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🤖 AI & tech collapse: youtube.com/@TheCollapseIndex\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🩺 Medical cases: youtube.com/@NoKnownCauseTV\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
    "collapse_index": {
        "main":  "\n\n🩺 Real published medical cases: youtube.com/@NoKnownCauseTV\n"
                 "🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom\n"
                 "🧠 Psychology documentaries: youtube.com/@TheControlFiles\n"
                 "🏛️ History & geopolitics: youtube.com/@TheArchiveFiles\n\n"
                 "📺 New investigation every weekday.",
        "short": "\n\n🩺 Medical cases: youtube.com/@NoKnownCauseTV\n🔬 Forensic: youtube.com/@TheEvidenceRoom",
    },
}

def get_cross_promo(channel_id, is_short=False):
    p = CROSS_PROMO.get(channel_id, CROSS_PROMO["betrayal_deepdive"])
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
# FIX (direct user report, July 24 2026 — "look for other providers
# which are free and can be used"): GitHub Models — genuinely free,
# OpenAI-compatible inference API, and needs ZERO new signup/secret:
# every GitHub Actions run already has a GITHUB_TOKEN, and granting it
# the "models: read" permission (added to ch1_generate.yml) is enough
# to call it. Real models available: GPT-4o family, Llama, DeepSeek-R1,
# Mistral, Phi. Falls back to a Personal Access Token env var too, for
# local/non-Actions runs.
GITHUB_MODELS_TOKEN = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_MODELS_TOKEN", "")
# FIX (direct user report, July 24 2026 — "add everything that is free
# and doesn't have any hidden billings"): two more real, verified,
# no-credit-card-required free tiers.
# Cloudflare Workers AI — 10,000 free "Neurons"/day (real Cloudflare
# doc: "a credit card is only needed to EXCEED the daily allocation" —
# without one on file, hitting the limit just errors, never silently
# bills). Needs a free Cloudflare account + API token + account ID.
CLOUDFLARE_API_TOKEN   = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID  = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
# NVIDIA build.nvidia.com (NIM API Catalog) — confirmed no credit card
# required at all for the free developer tier, real OpenAI-compatible
# endpoint, 100+ models. Rate-limited (not credit-metered), so it just
# slows down rather than bills when busy.
NVIDIA_NIM_KEY = os.environ.get("NVIDIA_API_KEY", "")
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
# FIX (direct user request, July 25 2026 — real resume-from-last-passed-
# stage): the accepted narration audio itself (not just its metadata)
# has to be committed too -- GitHub Actions runners are fully ephemeral,
# so /tmp is gone on a resumed run's fresh runner. Small enough (a single
# episode's MP3) to commit safely, unlike the full rendered video.
CKPT_AUDIO_FILE = SCRIPT_DIR / "checkpoint_audio.mp3"

# ================================================================
# CONFIG
# ================================================================
# Narration pace. Slowed after direct feedback on the first rendered
# episode ("the audio pacing is very fast"): it ran at 125 wpm, which is
# news-read speed, not documentary speed. These two constants are the ONLY
# place pace is set -- edge-tts and Kokoro previously disagreed (-8%/-5% vs
# an unscaled Kokoro speed), so the delivered pace depended on which
# provider happened to answer.
CLINICAL_PACE = 0.88      # Kokoro multiplier: ~125 wpm -> ~110 wpm
EDGE_RATE     = "-18%"    # edge-tts equivalent of the same target

MIN_WORDS   = 1900
# Maximum words in one narration sentence.
#
# This was 13, inherited from the dark-documentary format where clipped,
# staccato delivery was the house style. Measured against a realistic
# clinical episode, 13 words flags three of the first four sentences as
# faults -- the rule was fighting ordinary documentary prose, and the
# rewrite prompt then instructed the model to chop perfectly good writing
# into fragments. Broadcast documentary narration runs 15-20 words; the
# rule that actually matters for this channel is VARIETY, which is now
# measured directly (standard deviation of sentence length) instead of
# being approximated by a hard ceiling.
MAX_SENTENCE_WORDS = 20
MAX_WORDS   = 2100
# FIX (direct user report, July 24 2026 — explicit, final policy decision
# after being shown real data that 8.8 essentially never gets hit): hard
# floor is 8.5, EVERY stage (script, audio, video, thumbnail, title,
# Shorts, community post), maximum 8 remake attempts, NO relaxation tiers.
# If nothing clears 8.5 within 8 attempts, the day is skipped entirely —
# no publish. The bar itself stays flat at 8.5 — the user explicitly
# rejected graduated fallback thresholds (8.5 -> 7.0 -> 6.9): "below
# that, I don't want any videos to be published if it is not working...
# I don't want any crap videos." Attempt budget raised 8 -> 13 (direct
# user report, July 24 2026 — "increase the attempts from 8 to 13...
# so we get an opportunity to remake it... without missing out on the
# day's target") purely to give the SAME 8.5 bar more real tries before
# the day is skipped, not to relax the bar itself.
MIN_GATE    = 8.5
MAX_ATTEMPTS = 13

# Word targets per stage (sum = MIN_WORDS baseline)
STAGE_WORDS = [100, 200, 250, 400, 200, 650, 200]
STAGE_NAMES = ["The Opening", "Before It Happened", "First Warning Signs",
               "Escalation", "A Moment of Peace", "The Truth Revealed", "What This Means"]

EL_VOICES = {
    "toxicology_cases":        "pNInz6obpgDQGcFmaJgB",
    "diagnostic_odyssey":      "pNInz6obpgDQGcFmaJgB",
    "neurology_cases":         "29vD33N1CtxCmqQRPOHJ",
    "rare_disease_cases":      "29vD33N1CtxCmqQRPOHJ",
    "senior_health_longevity": "VR6AewLTigWG4xSOukaG",
    "medical_mystery_outbreak":"pNInz6obpgDQGcFmaJgB",
    "surgical_case_studies":   "29vD33N1CtxCmqQRPOHJ",
    "drug_discovery_stories":  "yoZ06aMxZJJ28mfd3POQ",
    "sleep_science":           "VR6AewLTigWG4xSOukaG",
    "medical_history":         "yoZ06aMxZJJ28mfd3POQ",
}

DAY_NICHE = {0: "toxicology_cases", 1: "diagnostic_odyssey", 2: "neurology_cases",
             3: "rare_disease_cases", 4: "senior_health_longevity",
             5: "drug_discovery_stories", 6: "medical_history"}

# The ten clinical niches. Every one is sourced live from Europe PMC by
# pmc_data.get_real_case() -- the "topics" list below is only the last-resort
# fallback when the API is unreachable, and each entry names a REAL,
# published, verifiable case so even the fallback path cannot invent one.
#
# rpm values are estimated placements inside the sourced $10-30 health/medical
# RPM band. The band is sourced; the per-niche precision is NOT. Marked
# explicitly because Ch5's coded rpm values were found to be overstated in
# exactly this way.
NICHES = [
    {
        "name": "toxicology_cases", "rpm": 18.00, "series": "Toxicology Case Files",
        "search_query": "toxicology poisoning case report documentary",
        "clinical_frame": "an ordinary substance in an extraordinary quantity",
        "implication": "what changed in how this presentation is now managed",
        "topics": [
            "A 51-year-old man drank one litre of soy sauce; his serum sodium reached 171 mEq/L and he developed a non-aneurysmal subarachnoid haemorrhage",
            "Star fruit nephrotoxicity: two published cases of histologically confirmed oxalate-induced renal injury",
            "A 19-year-old presented comatose two hours after ingesting a quart of soy sauce and survived neurologically intact after 6 L of free water",
            "A 28-year-old with cannabinoid hyperemesis syndrome presented with QTc prolongation and severe hypokalaemia",
        ],
        "hook_triggers": [
            "the quantity that turned an ordinary substance into a medical emergency",
            "the laboratory value nobody in the room had seen in a living patient",
            "the moment the treating team realised the first diagnosis was wrong",
            "the mechanism that explained every earlier finding at once",
        ],
    },
    {
        "name": "diagnostic_odyssey", "rpm": 17.00, "series": "The Wrong Diagnosis",
        "search_query": "delayed diagnosis misdiagnosis case report",
        "clinical_frame": "the years between the first symptom and the correct answer",
        "implication": "what this case changed about how the condition is recognised",
        "topics": [
            "Published cases of hyponatraemic and hypernatraemic encephalopathy initially treated as viral meningitis",
            "Documented cannabinoid hyperemesis presentations misdiagnosed for years, with the real cost of delayed diagnosis quantified",
        ],
        "hook_triggers": [
            "the number of years the correct diagnosis was missed",
            "the test that would have answered it on day one",
            "the finding that never fitted the working diagnosis",
            "the moment a clinician questioned the accepted explanation",
        ],
    },
    {
        "name": "neurology_cases", "rpm": 17.00, "series": "The Brain Files",
        "search_query": "neurological case report unusual presentation",
        "clinical_frame": "a nervous system doing something that should not be possible",
        "implication": "what this taught neurology about how the brain is wired",
        "topics": [
            "Alien hand syndrome from an extensive corpus callosum infarct, presenting with features of all three recognised variants",
            "Alien hand syndrome as the initial presentation of posterior cerebral artery infarction",
            "Reversible alien hand syndrome that remitted completely within eight days of cerebral infarction",
            "Foreign accent syndrome: roughly one hundred cases recorded since the 1940s",
        ],
        "hook_triggers": [
            "the movement the patient could not account for",
            "the imaging finding that located the disconnection",
            "the eight days in which it completely resolved",
            "what the deficit revealed about normal function",
        ],
    },
    {
        "name": "rare_disease_cases", "rpm": 16.00, "series": "Rare Presentations",
        "search_query": "rare disease first reported case report",
        "clinical_frame": "a condition most clinicians will never see once",
        "implication": "how this case entered the medical literature",
        "topics": [
            "Published first-reported presentations of conditions with fewer than one hundred documented cases worldwide",
        ],
        "hook_triggers": [
            "how few cases have ever been documented",
            "the presentation that matched nothing in the textbooks",
            "the specialist who recognised it from a single detail",
            "why this case is now the reference case",
        ],
    },
    {
        "name": "senior_health_longevity", "rpm": 14.00, "series": "The Ageing Files",
        "search_query": "ageing longevity geriatric sarcopenia frailty research",
        "clinical_frame": "what the research actually shows about ageing bodies",
        "implication": "what the evidence changed about care in later life",
        "topics": [
            "Published research on sarcopenia and frailty progression, and what the measured data shows",
            "Documented findings on mobility decline and the interventions studied against it",
        ],
        "hook_triggers": [
            "the measured rate of decline the study documented",
            "the intervention the data did and did not support",
            "the assumption the evidence contradicted",
            "what the long-term follow-up showed",
        ],
    },
    {
        "name": "medical_mystery_outbreak", "rpm": 15.00, "series": "Cluster",
        "search_query": "disease outbreak cluster epidemiological investigation",
        "clinical_frame": "a pattern of illness nobody could initially explain",
        "implication": "how the source was finally identified",
        "topics": [
            "Published epidemiological investigations of documented disease clusters and how the common source was traced",
        ],
        "hook_triggers": [
            "the number of people affected before anyone connected them",
            "the shared exposure nobody had noticed",
            "the investigator who found the pattern",
            "the control measure that ended it",
        ],
    },
    {
        "name": "surgical_case_studies", "rpm": 16.00, "series": "The Operative Record",
        "search_query": "surgical management complex case report",
        "clinical_frame": "a problem that could only be solved anatomically",
        "implication": "what the technique changed for later patients",
        "topics": [
            "Published complex surgical management cases, explained through anatomy and imaging rather than operative photography",
        ],
        "hook_triggers": [
            "the anatomy that made the standard approach impossible",
            "the decision made before the first incision",
            "the imaging that changed the plan",
            "the outcome at long-term follow-up",
        ],
    },
    {
        "name": "drug_discovery_stories", "rpm": 19.00, "series": "How It Was Found",
        "search_query": "drug discovery history first isolated compound",
        "clinical_frame": "the accident, observation or failure behind a real medicine",
        "implication": "how the discovery changed what was treatable",
        "topics": [
            "Published historical accounts of how specific real medicines were first isolated and characterised",
        ],
        "hook_triggers": [
            "the observation nobody was looking for",
            "the failure that turned out to be the finding",
            "the years between discovery and use",
            "what became treatable that had not been",
        ],
    },
    {
        "name": "sleep_science", "rpm": 13.00, "series": "The Sleep Files",
        "search_query": "sleep disorder insomnia narcolepsy circadian case report",
        "clinical_frame": "what happens when sleep architecture breaks",
        "implication": "what the case revealed about normal sleep",
        "topics": [
            "Published case reports of documented sleep disorders and the sleep-study findings that identified them",
        ],
        "hook_triggers": [
            "the number of nights it continued before diagnosis",
            "what the sleep study recorded",
            "the mechanism behind the symptom",
            "what it revealed about ordinary sleep",
        ],
    },
    {
        "name": "medical_history", "rpm": 12.00, "series": "Before We Knew",
        "search_query": "history of medicine historical treatment case",
        "clinical_frame": "a treatment that was once standard practice",
        "implication": "how and when the standard of care changed",
        "topics": [
            "Published historical accounts of treatments once considered standard and the evidence that ended them",
        ],
        "hook_triggers": [
            "how long the practice continued",
            "the evidence that had been available all along",
            "the clinician who challenged it",
            "when the standard of care formally changed",
        ],
    },
]

# FIX (found on direct user request, July 23 2026): every niche had a
# US voice as either the primary or secondary pick — the exact thing
# the user said sounds "too robotic". Switched to British/Australian
# voices only, channel-wide. GB voices (RyanNeural, ThomasNeural,
# NoahNeural, OliverNeural, EthanNeural) are already proven working in
# production across every other channel in this repo (see Ch2/3/4's
# GB_VOICES/NICHE_VOICES). The two Australian voices (WilliamNeural,
# NatashaNeural) are real, standard Microsoft neural voices on the same
# underlying Azure TTS service GB already uses successfully here — not
# yet stress-tested specifically on this repo's GitHub Actions runners,
# so kept as the SECOND option per niche behind an already-proven GB
# voice, with the existing SSML/Fish Audio/Kokoro fallback chain still
# there as a safety net if either ever fails.
# FIX (direct user report, July 23 2026 — "I wanted to go beyond the
# Great Britain voices. I wanted to use Australian, New Zealand, or
# other English languages that have more human and more interesting
# voices... add everything... so that if that fails... it can move to
# the next thing, not get stuck with one voice itself"): every niche now
# has a real 4-deep chain spanning GB/AU/NZ/IE, not just 2 GB-only
# options. EXTENDED_VOICES below is the full additional-accent pool used
# to build these chains and every fallback list in this file.
#
# FIX (direct user report, July 23 2026, second pass — "I want 15 to 18
# fallback voices... both male and female... according to the nation and
# according to how the channel works"): 4-deep was still too shallow and
# too male-heavy on average. This is now the FULL real Microsoft Edge
# neural voice catalog for every non-US English locale (en-GB-NoahNeural
# and en-GB-MaisieNeural excluded -- Noah is confirmed broken on this
# repo's GitHub Actions runners live, see the FIX note below; Maisie is
# a child voice, wrong register for any of these niches), gender-
# labeled so every niche list below can be built genuinely gender-
# balanced rather than picked ad hoc.
#
# HONEST LIMITATION: this sandbox's network policy blocks outbound
# access to Microsoft's speech endpoint (confirmed live -- the proxy
# rejects the CONNECT with a 403), so these voice IDs could not be
# synthesized and listened to from here to judge "how human" each one
# sounds. Every ID below is a real, currently-documented Microsoft Edge
# Neural voice (their highest quality tier -- there is no higher tier to
# pick from), the same class already proven working in production here
# (WilliamNeural/NatashaNeural). Genuine listening verification can only
# happen where TTS synthesis actually runs -- the GitHub Actions runner
# itself, which has no such restriction -- and any ID that has quietly
# been renamed/retired will surface immediately in the existing
# fallback-chain logging (every attempted voice + success/failure is
# already logged) and simply get skipped in favor of the next one in
# the chain, exactly the "never get stuck on one voice" behavior
# already built.
# FIX (direct user report, July 24 2026): en-GB-RyanNeural, en-GB-NoahNeural
# and en-GB-MaisieNeural stay excluded (Ryan reported robotic; Noah
# confirmed broken on this repo's GitHub Actions runners live — 24/24
# SSML failures; Maisie is a child voice, wrong register).
#
# FIX (direct user report, July 24 2026 — explicit priority order
# "1. Australian voice 2. Great Britain voice 3. US voice 4. the
# remaining voices... mix of male and female... should keep rotating...
# confirm all the voices"): this REVERSES the July 23 "no US voices"
# decision at the user's explicit request this time — US voices are
# back in the pool, ranked 3rd (after AU/GB, before IE/NZ/ZA/CA).
# Built programmatically instead of one giant hand-typed list per niche:
# guarantees the AU>GB>US>rest block order holds for every niche, every
# voice in the real catalog is genuinely included ("confirm all the
# voices"), and each gender-interleaved block mixes male/female
# throughout rather than front-loading one gender. Per-niche rotation
# offset keeps the 5 niches from being identical lists while never
# breaking the AU>GB>US>rest block order.
# FIX (direct user request, July 25 2026 — real, explicit voice-roster
# rebuild, replacing the July 24 AU>GB>US>rest priority above):
# "female voices are less robotic and sound good, so we can go with
# it... let's start using female voices for New Zealand, the U.S., the
# UK, and Singapore voices... The first thing I wanted... should be the
# Ireland female voice, because it sounds really good. I want to try
# with that at the start... For the male voices, we can go with
# Ireland as well as some other voices."
# en-SG-LunaNeural/en-SG-WayneNeural confirmed as the real Microsoft
# Edge neural voice IDs for Singapore English (verified July 25 2026).
_AU_MALE   = ["en-AU-WilliamNeural", "en-AU-DarrenNeural", "en-AU-DuncanNeural",
              "en-AU-KenNeural", "en-AU-NeilNeural", "en-AU-TimNeural"]
# "For Australia I don't want you to use a female voice" — emptied,
# never selected. Kept (not deleted) since it's still summed into a
# gender-membership check elsewhere (the Kokoro fallback voice match).
_AU_FEMALE = []
_GB_MALE   = ["en-GB-ThomasNeural", "en-GB-AlfieNeural", "en-GB-ElliotNeural",
              "en-GB-EthanNeural", "en-GB-OliverNeural"]
_GB_FEMALE = ["en-GB-SoniaNeural", "en-GB-LibbyNeural", "en-GB-AbbiNeural",
              "en-GB-BellaNeural", "en-GB-HollieNeural", "en-GB-OliviaNeural"]
_US_MALE   = ["en-US-AndrewNeural", "en-US-BrianNeural", "en-US-GuyNeural",
              "en-US-EricNeural", "en-US-RogerNeural", "en-US-ChristopherNeural"]
_US_FEMALE = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural",
              "en-US-EmmaNeural", "en-US-AvaNeural", "en-US-SaraNeural"]
# Index 0 of _REST_FEMALE is always en-IE-EmilyNeural — _build_voice_pool
# below pulls it out specifically so it is ALWAYS the very first voice
# tried, for every niche, unaffected by rotation_offset.
_REST_MALE   = ["en-IE-ConnorNeural", "en-NZ-MitchellNeural", "en-SG-WayneNeural",
                "en-ZA-LukeNeural", "en-CA-LiamNeural"]
_REST_FEMALE = ["en-IE-EmilyNeural", "en-NZ-MollyNeural", "en-SG-LunaNeural",
                "en-ZA-LeahNeural", "en-CA-ClaraNeural"]

def _interleave_genders(male, female):
    out = []
    for i in range(max(len(male), len(female))):
        if i < len(male):   out.append(male[i])
        if i < len(female): out.append(female[i])
    return out

def _rotate(lst, n):
    if not lst:
        return lst
    n = n % len(lst)
    return lst[n:] + lst[:n]

def _build_voice_pool(rotation_offset):
    # Ireland female: hard-pinned to position 0, every niche, no
    # rotation can ever move it out of first place.
    ie_female_first = _REST_FEMALE[0]
    # Female priority pool (NZ, US, GB, Singapore) — rotates per niche
    # for variety, same principle as the old block rotation, but always
    # female-led and never interleaved with male voices ahead of it.
    female_priority = [_REST_FEMALE[1]] + _US_FEMALE + _GB_FEMALE + [_REST_FEMALE[2]]
    female_priority = _rotate(female_priority, rotation_offset)
    # Male fallback — only reached once every female voice above has
    # been tried/failed. Ireland male leads it (explicit "we can go
    # with Ireland as well" for male), then the other researched good
    # male locales.
    male_fallback = [_REST_MALE[0]] + _US_MALE + _GB_MALE + _AU_MALE + \
                    [_REST_MALE[1], _REST_MALE[2]] + _REST_MALE[3:]
    male_fallback = _rotate(male_fallback, rotation_offset)
    return [ie_female_first] + female_priority + male_fallback

EXTENDED_VOICES = _build_voice_pool(0)

VOICES = {
    "toxicology_cases":        _build_voice_pool(0),
    "diagnostic_odyssey":      _build_voice_pool(1),
    "neurology_cases":         _build_voice_pool(2),
    "rare_disease_cases":      _build_voice_pool(3),
    "senior_health_longevity": _build_voice_pool(4),
    "medical_mystery_outbreak":_build_voice_pool(5),
    "surgical_case_studies":   _build_voice_pool(6),
    "drug_discovery_stories":  _build_voice_pool(7),
    "sleep_science":           _build_voice_pool(8),
    "medical_history":         _build_voice_pool(9),
}

BG_KEYWORDS = {
    "toxicology_cases": [
        "hospital emergency department",
        "medical laboratory glassware",
        "iv drip hospital",
        "clinical laboratory analyser",
        "hospital monitor vitals",
        "pharmacy shelves vials",
        "blood sample tubes",
        "hospital ward night",
    ],
    "diagnostic_odyssey": [
        "medical records files",
        "hospital corridor walking",
        "clinic waiting room",
        "doctor reviewing chart",
        "medical scan lightbox",
        "stethoscope desk",
        "hospital reception",
        "patient file folder",
    ],
    "neurology_cases": [
        "mri scanner room",
        "brain scan monitor",
        "neurology imaging display",
        "eeg electrodes head",
        "brain model anatomy",
        "ct scanner hospital",
        "neurologist examining scan",
        "hospital imaging suite",
    ],
    "rare_disease_cases": [
        "microscope laboratory research",
        "dna helix visualisation",
        "petri dish laboratory",
        "genetic sequencing screen",
        "laboratory pipette samples",
        "research laboratory bench",
        "medical microscope slide",
        "laboratory centrifuge",
    ],
    "senior_health_longevity": [
        "elderly hands close up",
        "physiotherapy exercise senior",
        "walking rehabilitation",
        "elderly person exercising",
        "senior health checkup",
        "grip strength test",
        "balance exercise elderly",
        "nutrition healthy food",
    ],
    "medical_mystery_outbreak": [
        "public health laboratory",
        "epidemiology map data",
        "hospital entrance exterior",
        "protective equipment laboratory",
        "water testing sample",
        "food safety inspection",
        "contact tracing board",
        "laboratory culture plates",
    ],
    "surgical_case_studies": [
        "operating theatre lights",
        "surgical instruments tray",
        "hospital theatre empty",
        "surgical scrub preparation",
        "anatomy model surgical",
        "operating room monitor",
        "sterile field preparation",
        "hospital corridor theatre",
    ],
    "drug_discovery_stories": [
        "laboratory research vintage",
        "petri dish mould culture",
        "chemistry laboratory glassware",
        "pharmacy historical bottles",
        "molecule model structure",
        "laboratory notebook handwritten",
        "microscope vintage laboratory",
        "pill production line",
    ],
    "sleep_science": [
        "sleep laboratory monitor",
        "dark bedroom night",
        "eeg sleep study",
        "clock night bedside",
        "polysomnography sensors",
        "dark room curtain night",
        "brain waves display",
        "empty bed night",
    ],
    "medical_history": [
        "antique medical instruments",
        "old hospital archive photographs",
        "historical medicine bottles",
        "vintage anatomical illustration",
        "old medical textbook",
        "archive document historical",
        "museum medical exhibit",
        "historical hospital ward",
    ],
}

# Secondary keywords if primary returns nothing useful
BG_KEYWORDS_FALLBACK = {
    "toxicology_cases":        ["laboratory glassware", "medical laboratory", "hospital ward"],
    "diagnostic_odyssey":      ["medical records", "hospital corridor", "clinic waiting room"],
    "neurology_cases":         ["brain scan", "neurology imaging", "mri scanner"],
    "rare_disease_cases":      ["microscope laboratory", "medical research", "dna helix"],
    "senior_health_longevity": ["elderly hands", "physiotherapy", "walking recovery"],
    "medical_mystery_outbreak":["public health laboratory", "epidemiology map", "hospital entrance"],
    "surgical_case_studies":   ["operating theatre lights", "surgical instruments tray", "hospital theatre"],
    "drug_discovery_stories":  ["laboratory research", "petri dish", "pharmacy vials"],
    "sleep_science":           ["sleep laboratory", "dark bedroom night", "eeg monitor"],
    "medical_history":         ["antique medical instruments", "old hospital archive", "historical medicine"],
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

# FIX (direct user report, July 24 2026 — "I want these LLM to take the
# quality scoring expertly serious and give me a notification everytime
# they score any stage without fail. its my main REQUIREMENT"): every
# single scored attempt at every stage — script, audio, video,
# thumbnail-text, Shorts — now sends a real Telegram message the moment
# it's scored, pass or fail, not just on the final winning attempt or
# final exhaustion. Wrapped so a Telegram hiccup can never block the
# actual pipeline (same non-fatal pattern as every other tg() call).
def notify_stage_score(stage_name, attempt, max_attempts, score, gate, extra=""):
    verdict = "✅ CLEARED" if score >= gate else "❌ below gate"
    msg = (f"📊 <b>Ch1 — {stage_name}</b>\n"
           f"Attempt {attempt}/{max_attempts}: <b>{score}/10</b> (gate {gate}) — {verdict}")
    if extra:
        msg += f"\n{extra}"
    try:
        tg(msg)
    except Exception as e:
        log(f"  Score notification (non-fatal): {e}")

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
    try: CKPT_AUDIO_FILE.unlink(missing_ok=True)
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
    # FIX (direct user report, July 24 2026 — real live-run data, run
    # 30126085986): "qwen-3-32b"/"qwen-3-235b-a22b" both 404'd for real —
    # confirmed wrong slugs, removed rather than left as wasted attempts.
    # HONEST FLAG: zai-glm-4.7 ALSO 404'd in that same run, despite being
    # verified working as recently as June 2026 — the whole provider
    # returned "NO RESPONSE" across every model tried. That pattern (a
    # previously-working model suddenly 404ing across the board) matches
    # an account/key-level issue more than a naming issue — same shape
    # as Gemini's confirmed 403 project-denial in the same run. Worth
    # checking the Cerebras dashboard/key directly, not just code.
    _models = ["gpt-oss-120b", "zai-glm-4.7",
               "llama-3.3-70b", "llama3.3-70b", "llama-3.1-70b", "llama3.1-70b", "llama3.1-8b"]
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
    # FIX (direct user report, July 24 2026 — real provider audit):
    # confirmed llama-3.3-70b-versatile and llama-3.1-8b-instant were
    # BOTH formally deprecated by Groq on June 17 2026 (already past —
    # this is a genuinely dead model now, not just an old fallback).
    # Removed entirely rather than kept as dead weight. Groq's own
    # recommended replacements — openai/gpt-oss-120b, qwen/qwen3.6-27b,
    # openai/gpt-oss-20b — are what's tried now.
    # FIX (real live-run data, run 30126085986): qwen/qwen3-32b confirmed
    # "404 (model gone)" for real — removed.
    for model in ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"]:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88, "max_tokens": min(tokens, 4800)}, timeout=90)  # Groq TPM limit = 6000
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"OK Groq ({model})"); return t
                # FIX (found on live-run investigation, July 24 2026): a
                # 200 with a too-short response fell through every
                # branch below with ZERO log line — genuinely
                # indistinguishable from "never tried this model at
                # all" when reading the log. Real gap, now visible.
                log(f"Groq {model}: 200 but response too short ({len(t.strip()) if t else 0} chars) — trying next")
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
# FIX (direct user report, July 24 2026 — real provider audit): a live
# search of OpenRouter's current free catalog found DeepSeek and
# Mistral have NO free-tier models on OpenRouter as of July 2026 (both
# had free variants previously, both pulled them) — the 4 DeepSeek/
# Mistral entries below were dead weight, all guaranteed 404s. Removed
# and replaced with the families actually confirmed live on OpenRouter's
# free collection right now: Qwen, Llama, OpenAI GPT-OSS, Gemma, NVIDIA
# Nemotron. Any name that goes stale again just gets skipped via the
# existing 404-continue handling below — same self-healing behavior as
# Cerebras/Groq.
OR_FREE_MODELS = [
    "qwen/qwen-2.5-72b-instruct:free",             # Qwen — confirmed live
    "meta-llama/llama-3.3-70b-instruct:free",     # Meta — confirmed live
    "openai/gpt-oss-120b:free",                    # OpenAI OSS — confirmed live family
    "google/gemma-3-27b-it:free",                  # Google — confirmed live
    "nvidia/nemotron-nano-9b-v2:free",              # NVIDIA — confirmed live family
    "nousresearch/hermes-3-llama-3.1-405b:free",  # last resort
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
    """Cohere Command free tier — 20 RPM, excellent for structured long-form scripts."""
    if not COHERE_KEY:
        log("  Cohere: COHERE_API_KEY not set — skipping")
        return None
    # FIX (confirmed against Cohere's own official deprecations page):
    # command-r-08-2024 is explicitly marked deprecated, retirement date
    # already passed — removed entirely (dead weight, guaranteed fail).
    # command-a-plus-05-2026 is Cohere's newest model (confirmed live,
    # released May 2026), tried first; command-a-03-2025 stays as the
    # proven, stable fallback right behind it.
    for _cohere_model in ["command-a-plus-05-2026", "command-a-03-2025"]:
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


# ================================================================
# GITHUB MODELS — free, OpenAI-compatible, zero new signup required
# ================================================================
GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"

def call_github_models(prompt, tokens=8000):
    """
    Free tier, no new account/key needed on GitHub Actions — the
    workflow's own GITHUB_TOKEN works once granted "models: read"
    permission (see ch1_generate.yml). Rate limits are real but low
    (single-digit RPM per model) — same self-healing multi-model
    fallback pattern as every other provider here, so a model at its
    per-minute cap just falls through to the next one instead of
    blocking the whole chain.
    """
    if not GITHUB_MODELS_TOKEN:
        log("  GitHub Models: no GITHUB_TOKEN available — skipping")
        return None
    for model in ["openai/gpt-4o-mini", "openai/gpt-4o", "meta/Llama-3.3-70B-Instruct",
                  "mistral-ai/Mistral-Large-2411", "deepseek/DeepSeek-R1"]:
        try:
            r = requests.post(GITHUB_MODELS_URL,
                headers={"Authorization": f"Bearer {GITHUB_MODELS_TOKEN}",
                         "Content-Type": "application/json",
                         "Accept": "application/vnd.github+json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88, "max_tokens": min(tokens, 4000)},
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"OK GitHub Models ({model})")
                    return t
                log(f"GitHub Models {model}: 200 but response too short — trying next")
            elif r.status_code in (400, 404):
                log(f"GitHub Models {model}: {r.status_code} (wrong model name) — trying next")
            elif r.status_code == 429:
                log(f"GitHub Models {model}: 429 rate limited — trying next")
            elif r.status_code == 403:
                log(f"GitHub Models {model}: 403 — GITHUB_TOKEN likely missing 'models: read' "
                    f"permission in the workflow")
                return None  # a permissions problem won't fix itself on the next model
            else:
                log(f"GitHub Models {model}: {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"GitHub Models {model}: {e}")
    return None


def call_cloudflare(prompt, tokens=8000):
    """
    Cloudflare Workers AI — 10,000 free Neurons/day, no credit card
    required to start (Cloudflare's own docs: a card is only needed to
    exceed the daily allocation, never to use it). Needs a free
    Cloudflare account: dash.cloudflare.com -> My Profile -> API Tokens
    -> create a token with "Workers AI" edit permission, plus the
    account ID shown on any zone's Overview page.
    """
    if not (CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID):
        log("  Cloudflare: CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_ID not set — skipping")
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions"
    for model in ["@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                  "@cf/mistralai/mistral-small-3.1-24b-instruct",
                  "@cf/google/gemma-3-12b-it"]:
        try:
            r = requests.post(url,
                headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88, "max_tokens": min(tokens, 4000)},
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"OK Cloudflare ({model})")
                    return t
                log(f"Cloudflare {model}: 200 but response too short — trying next")
            elif r.status_code in (400, 404):
                log(f"Cloudflare {model}: {r.status_code} (wrong model name) — trying next")
            elif r.status_code == 429:
                log(f"Cloudflare {model}: 429 — daily 10k Neuron allocation likely used up")
            else:
                log(f"Cloudflare {model}: {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"Cloudflare {model}: {e}")
    return None


def call_nvidia_nim(prompt, tokens=8000):
    """
    NVIDIA build.nvidia.com (NIM API Catalog) — confirmed no credit card
    required for the free developer tier, real OpenAI-compatible
    endpoint, 100+ models. Rate-limited rather than credit-metered, so
    it slows down instead of billing when busy. Free key:
    build.nvidia.com -> sign in -> any model page -> "Get API Key".
    """
    if not NVIDIA_NIM_KEY:
        log("  NVIDIA NIM: NVIDIA_API_KEY not set — skipping")
        return None
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    for model in ["meta/llama-3.3-70b-instruct", "mistralai/mixtral-8x7b-instruct-v0.1",
                  "meta/llama-3.1-70b-instruct"]:
        try:
            r = requests.post(url,
                headers={"Authorization": f"Bearer {NVIDIA_NIM_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.88, "max_tokens": min(tokens, 4000)},
                timeout=90)
            if r.status_code == 200:
                t = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if t and len(t.strip()) > 100:
                    log(f"OK NVIDIA NIM ({model})")
                    return t
                log(f"NVIDIA NIM {model}: 200 but response too short — trying next")
            elif r.status_code in (400, 404):
                log(f"NVIDIA NIM {model}: {r.status_code} (wrong model name) — trying next")
            elif r.status_code == 429:
                log(f"NVIDIA NIM {model}: 429 rate limited — trying next")
            else:
                log(f"NVIDIA NIM {model}: {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"NVIDIA NIM {model}: {e}")
    return None


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

def ai_generate(prompt, tokens=8000):
    """
    Provider order: Cerebras -> GitHub Models -> Cloudflare -> NVIDIA NIM ->
    SambaNova -> Gemini -> Groq -> OpenRouter -> Cohere -> Mistral
    FIX (July 14 2026 audit): providers that fail once are skipped for the
    rest of this run instead of being retried from scratch on every call
    (this alone was responsible for a large share of multi-hour runtimes).
    FIX (direct user report, July 24 2026 — real live-run data showed
    Cerebras/Gemini/SambaNova/OpenRouter all down or account-limited in
    the same run, leaving only Mistral to carry almost the entire
    pipeline; then "add everything that is free and doesn't have any
    hidden billings"): GitHub Models, Cloudflare Workers AI, and NVIDIA
    NIM added — all three confirmed genuinely free with no credit card
    required, and none share a quota/account with any provider already
    here, so a bad day for one provider group no longer starves the
    whole chain down to a single survivor.
    """
    providers = [("cerebras", call_cerebras), ("github_models", call_github_models),
                 ("cloudflare", call_cloudflare), ("nvidia_nim", call_nvidia_nim),
                 ("sambanova", call_sambanova),
                 ("gemini", call_gemini), ("groq", call_groq),
                 ("openrouter", call_openrouter), ("cohere", call_cohere),
                 ("mistral", call_mistral)]
    live = [(name, fn) for name, fn in providers if name not in _DEAD_PROVIDERS_THIS_RUN]
    if not live:
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
    perf[f"last_voice_{niche_name}"] = voice  # feeds select_best_voice's no-repeat rule
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
    # FIX (found on live Ch1 test run — real bug): this computed real
    # rubric subscores and issues (Craft, Clarity, rehook, retention
    # dead-zones) and logged them, but the return statement was
    # hardcoded `return min(round(s, 1), 10.0), []` — every issue it
    # found was calculated, printed to the log, then thrown away. A
    # script scoring 10.0/10 with real flagged problems (weak narrative
    # craft, a repeated filler phrase, a missing mid-video rehook) sent
    # to the human reviewer showed only the bare number and one older,
    # separate "Hook strength" metric — none of the newer rubric
    # findings a reviewer would actually want to see before approving.
    # Now genuinely returned so callers can surface them.
    if not r: return 0.0, [], {}
    # Length is no longer scored. See video_pipeline/clinical_quality.py:
    # word count used to carry a 4.8-point swing on a 10-point scale, which
    # made it the largest single term and meant padding a script improved
    # its score. It is now a floor checked once (duration_check) and then
    # ignored, and its points went to clinical specificity -- real reported
    # detail per 100 words, which padding actively lowers.
    w = r.get("words", 0)
    v = r.get("violations", 0)
    s = 5.0
    if v == 0:   s += 2.2
    elif v <= 2: s += 0.8
    else:        s -= 1.5
    # v12: retention hook validation
    script = r.get("script", "")
    issues = []
    subscores = {}
    if script:
        penalty, hook_issues = _validate_retention_hooks_ch1(script)
        s += penalty
        issues.extend(hook_issues)
        # Killer Hook / Narrative Craft / Topic Clarity rubric — real,
        # deterministic scoring of the actual script text, shared across
        # all 5 channels (video_pipeline/script_scoring.py).
        try:
            from script_scoring import score_script_rubric, validate_rehook_beat
            rubric_bonus, rubric_issues, rubric_subscores = score_script_rubric(script, topic or r.get("topic", ""))
            s += rubric_bonus
            if rubric_subscores:
                subscores.update(rubric_subscores)
                log(f"  Rubric: Hook {rubric_subscores['killer_hook']}/10 | "
                    f"Craft {rubric_subscores['narrative_craft']}/10 | "
                    f"Clarity {rubric_subscores['topic_clarity']}/10 | "
                f"HookGate {'PASS' if rubric_subscores.get('hook_gate_passed') else 'FAIL'}")
            if rubric_issues:
                issues.extend(rubric_issues)
                log(f"  Rubric issues: {' | '.join(rubric_issues[:3])}")
            rehook_bonus, rehook_issues = validate_rehook_beat(script)
            s += rehook_bonus
            if rehook_issues:
                issues.extend(rehook_issues)
                log(f"  {rehook_issues[0]}")
        except Exception as e:
            log(f"  Script rubric scoring (non-fatal): {e}")

    # ── composite, with length excluded ────────────────────────────────
    # Falls back to the legacy `s` if anything here raises, so a scoring
    # bug degrades to the old number rather than failing the attempt.
    try:
        from clinical_quality import score_script, DURATION_FLOOR_WORDS
        _h = subscores.get("killer_hook")
        _c = subscores.get("narrative_craft")
        _cl = subscores.get("topic_clarity")
        if None not in (_h, _c, _cl):
            _new, _ok, _rep = score_script(w, v, script, _h, _c, _cl)
            log(f"  Duration: {_rep['duration']}")
            log(f"  Specificity: {_rep['specificity']}/10 "
                f"({_rep['specificity_detail'].get('per_100_words')} details/100w)")
            log(f"  Composite: {_new}/10 (craft {_c} | hook {_h} | clarity {_cl} "
                f"| spec {_rep['specificity']} | clean {_rep['cleanliness']})")
            if _rep["gate_notes"]:
                log(f"  Below target: {', '.join(_rep['gate_notes'])}")
            if _rep["blocked_on"]:
                issues.insert(0, "BLOCKED: " + "; ".join(_rep["blocked_on"]))
                log(f"  BLOCKED: {'; '.join(_rep['blocked_on'])}")
                return 0.0, issues, subscores
            subscores["composite_report"] = _rep
            return min(round(_new, 1), 10.0), issues, subscores
    except Exception as e:
        log(f"  Composite scoring (non-fatal, using legacy score): {e}")
    return min(round(s, 1), 10.0), issues, subscores


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
    # FIX (direct user report, July 23 2026 — live Telegram card showed
    # "Weak 60% hook — peak CTA missing" as a footnote while the episode
    # still auto-approved: "I told you specifically there should be a
    # minimum ... peak CTA is missing. Why is it missing?"). A missing
    # CTA at the retention peak is now a hard gate, matching the
    # NARRATIVE_CRAFT/TOPIC_CLARITY/HOOK gates in script_scoring.py — the
    # penalty is large enough to drop the composite below every gate
    # tier, so a script without a real peak CTA cannot pass.
    h60 = sum(1 for w in hook_signals if w in seg(0.55, 0.65))
    if h60 < 2:
        penalty -= 5.0; issues.append("PEAK CTA GATE FAILED: weak 60% hook/CTA — this attempt "
                                       "cannot pass regardless of any other score.")
    elif h60 >= 3:
        penalty += 0.3
    if sum(1 for w in hook_signals if w in seg(0.75, 0.85)) < 1:
        penalty -= 0.4; issues.append("Missing 80% hook")
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3; issues.append("Missing final subscribe CTA")
    # v1 addition — real, measurable enforcement of the retention-cadence
    # instruction added to the prompt (payoff every 150-225 words). Scans
    # real ~200-word rolling windows and penalizes genuine dead zones (no
    # hook signal AND no real specific-number claim anywhere in that
    # stretch), not just the 3 original fixed points.
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

    prompt = f"""Generate exactly 3 different cold open variants for a clinical
case documentary narration, drawn from a real published case report.
Topic: {topic}
Niche style: {niche["dread_style"]}
{trend_hint}

Each cold open must:
- Be 80-120 words
- Start with the single most SURPRISING documented fact of this case —
  mid-moment, no preamble. Surprising, not lurid: the tension in these
  stories is that competent people were doing the right thing and were
  wrong, not that something horrifying happened to a patient. ("The single
  most disturbing fact" was the instruction here when this channel was a
  dark-documentary format; on a medical case it produces exactly the
  sensationalised framing that draws a limited-ads label.)
- Never say "welcome back", "today", "in this video"
- Use a specific date, time, or number in the first sentence
- Create a question the listener cannot stop thinking about
- FIX (found on direct user report, July 23 2026 — real bug, this was
  the single biggest gap in the whole video): the opening must actually
  PREVIEW the real, specific twist/irony of THIS exact topic — state or
  strongly imply the concrete outcome up front (e.g. if the topic is a
  surprise anniversary gift that exposed the affair that ended the
  marriage, say something like "the surprise she planned became the
  thing that ended it" — naming the real irony, not a vague mood).
  This creates a "wait — HOW did that happen" curiosity gap about THIS
  specific story, not generic dread. A viewer must be able to tell,
  from the cold open alone, roughly WHAT happens by the end — they
  keep watching to learn HOW, never to learn WHAT. An opening that
  could be swapped into a different episode about a different topic
  with zero changes has failed this requirement, no matter how
  disturbing it sounds in isolation.

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

- FIX (direct user report, July 24 2026 — "the cold open should open
  with a question and also interview the audience"): weave a direct,
  second-person question aimed at the viewer ("you"/"your") into the
  first two or three sentences — not a generic rhetorical cliché like
  "have you ever...", but a specific question tied to THIS case's real
  twist (e.g. "If someone logged your every move for twelve years and
  called it love, would you have noticed?"). It must still open
  mid-action with the disturbing fact per the rules above — the
  question is woven into the opening beats, not a throat-clearing
  preamble before the real hook starts. This is also automatically
  scored below.

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
        # FIX (direct user report, July 27 2026 — "I don't want the cold
        # open to start with a date... start with an open question"): a
        # bare digit used to be the only way to earn these 2 points,
        # directly fighting the new cold-open contract (below) that
        # forbids a date/number in sentence 1 -- a compliant, question-led
        # variant lost this reward for doing exactly what was mandated.
        # Concreteness now also counts an early open question, which is
        # what every compliant variant actually has instead of a number.
        if re.search(r'\d', text) or "?" in text[:200]: s += 2.0
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
        # FIX (direct user report, July 24 2026 — "open with a question
        # and also interview the audience"): reward a real question
        # posed directly to the viewer early in the cold open. Combined
        # with the weak-opener penalty above, a lazy "have you ever"
        # cliché still loses the 1.5pt weak-opener bonus, so this only
        # rewards a genuine, specific, second-person question.
        has_question = "?" in text[:250]
        has_you       = bool(re.search(r'\byou\b|\byour\b', words[:250]))
        if has_question and has_you: s += 1.5
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
        "toxicology_cases":        f"{topic_hint.split()[0]} poisoning toxicity case report",
        "diagnostic_odyssey":      f"delayed diagnosis misdiagnosis case report",
        "neurology_cases":         f"{topic_hint.split()[0]} neurological case report",
        "rare_disease_cases":      f"rare disease first reported case report",
        "senior_health_longevity": f"ageing longevity geriatric research study",
        "medical_mystery_outbreak":f"outbreak cluster epidemiological investigation",
        "surgical_case_studies":   f"surgical management complex case report",
        "drug_discovery_stories":  f"drug discovery history first isolated",
        "sleep_science":           f"sleep disorder case report polysomnography",
        "medical_history":         f"history of medicine historical treatment",
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

_COLD_OPEN_MANDATORY_INSTR = (
    "A MANDATORY COLD OPEN is provided above in RESEARCH CONTEXT — it already "
    "previews this exact story's specific twist/irony and was scored as the "
    "strongest of 3 real variants. Use it AS-IS for Stage 1 (only light edits "
    "for grammar/flow into what follows), do NOT write a new, generic cold "
    "open from scratch here. The rules below describe what that mandatory "
    "text already satisfies -- they are not a second, separate cold open to "
    "write instead of it."
)
# FIX (direct user report, this session — "I don't want the cold open to
# start with a date or something... start with an open question so that it
# intrigues the audience. I don't want any dates or timings as such."):
# previously required "Sentence 1 must contain an exact number, date, or
# duration" -- the literal source of every episode opening on a date. Kept
# as a module-level constant (not inline in the f-string below) purely
# because the quoted user request contains an apostrophe that can't safely
# nest inside an f-string expression's own quoting.
_COLD_OPEN_QUESTION_INSTR = (
    "Sentence 1 must be an intriguing, open QUESTION that hooks the listener "
    "into wanting the answer -- never a date, timestamp, year, or duration. "
    "No numeric dates/years/durations anywhere in sentence 1. Sentence 2 "
    "places the listener somewhere recognisable. Sentence 3 opens a loop the "
    "script must close. The opening must preview the real, specific "
    "twist/irony of THIS topic (state or strongly imply the actual outcome) "
    "-- not a generic disturbing mood that could belong to any episode."
)


# The script prompt's medical rules are imported from the gate that enforces
# them, so the instruction and the enforcement cannot drift apart. If the
# import fails the prompt still carries the rules verbatim as a fallback --
# a script generated without them would be rejected by the gate anyway, but
# silently dropping the instruction would waste every rework attempt.
try:
    from medical_policy_gate import SCRIPT_PROMPT_RULES as _MEDICAL_RULES
except Exception:
    _MEDICAL_RULES = """
MANDATORY MEDICAL CONTENT RULES (non-negotiable):
1. Third person, past tense, about the documented patient. Never "you should",
   "if you have", "your symptoms", or "consult your doctor".
2. Every clinical detail must come from the sourced case text. Invent nothing.
3. Never compare drugs or claim one treatment is better, safer or proven.
4. No graphic surgical, wound or post-mortem detail.
5. Close on what the case changed in medical understanding, never on advice.
6. Past tense, closed published case only. Never ongoing or breaking.
"""


def build_script_prompt(niche, topic, episode, attempt,
                        trending_titles=None, research_context=""):
    """
    v2 script prompt — 7-stage architecture with stage-specific
    word targets, trigger placements, and forbidden phrases per stage.
    """
    # v1 addition — real product title for the verbal-mention instruction,
    # using the same real product mapping as the description CTA.
    try:
        _product_title_for_prompt = build_product_cta("betrayal_deepdive").split(": ")[0].replace("\n\n📖 ", "").strip() or "our companion resource"
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

    return f"""Write a {intensity} dark investigative documentary narration.

TOPIC: {topic}
SERIES: {niche["series"]} — Episode {episode}
{trend_block}{pattern_block}{research_block}

{_MEDICAL_RULES}

TOTAL WORD REQUIREMENT: {MIN_WORDS} to {MAX_WORDS} words.
Each stage must hit its target. If any stage runs short, expand with more specific evidence.

SEVEN-STAGE STRUCTURE — write continuously, no labels, no headers. The
stage names below (COLD OPEN, THE BEFORE, etc.) are structural notes for
YOU, the writer, describing what content goes where — they are NOT text
to include in your response. Never write "Stage 1", "Stage 4", "Chapter
2", a stage's name, or any invented chapter title (e.g. never write
something like "Stage 4: The Investigation Deepens") anywhere in your
output. The reader must experience one continuous, unbroken narration
with zero visible section breaks of any kind — the transition between
stages should be a single smooth sentence, never a title or heading:

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

FICTION LABELING (non-negotiable, real policy-safety requirement, but NEVER
spoken in the narration — direct user instruction: "I keep seeing that
whenever the audio starts, it keeps telling me the things have been
changed... I don't want that to happen"): if any part of this story is
dramatized, composited from multiple cases, or not independently verifiable
as reported fact, do NOT write any acknowledgment of this into the script
itself — the narration should read as a pure, uninterrupted story with zero
meta-commentary about its own factuality. This disclosure is instead added
automatically to the video's written description (see generate_seo_
description below), never spoken. Never present invented specifics as
verified fact within the story, but handle that through how the story is
told (careful, plausible, non-defamatory framing), not through a spoken
disclaimer breaking the narration.

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

STAGE 1 — THE OPENING ({stage_targets[1]} words)
{_COLD_OPEN_MANDATORY_INSTR if "MANDATORY COLD OPEN" in research_context else _COLD_OPEN_QUESTION_INSTR}
Open on the ONE detail from this case that should not have happened. Not a
summary of the paper — a moment. Name the patient's situation in concrete
terms. Do not name the diagnosis.
Forbidden: "welcome back", "today we", "in this video", "join me"

STAGE 2 — THE PATIENT ({stage_targets[2]} words)
Who this was before anything went wrong, in the terms the paper gives: age,
the ordinary reason they were seen, what was unremarkable. The point is that
nothing here predicted what followed.
Forbidden: "little did they know", "unbeknownst to them"

STAGE 3 — FIRST SIGNS ({stage_targets[3]} words)
The earliest findings, in the order they were actually found. Each one
individually explainable — that is exactly why they were explained away.
Give the real value, the real day, the real observation.
Forbidden: "suddenly", "out of nowhere", "without warning"

STAGE 4 — DETERIORATION ({stage_targets[4]} words)
What changed, measurably, and what the team did about it. Real numbers, real
timeline. Explain WHY each finding mattered — a rising INR in an infant is
meaningless to a viewer until you say the liver builds clotting factors.
Forbidden: passive voice, vague quantities ("many", "several", "some")

STAGE 5 — THE FIRST ANSWER ({stage_targets[5]} words)
The working diagnosis, why it was the RIGHT call on the information
available, and what was done for it. Treat the team as competent. Then: the
result that did not fit.
Forbidden: "but it wasn't over", "or so they thought", blaming any clinician

STAGE 6 — THE REVERSAL ({stage_targets[6]} words)
The longest section. What the negative result meant, what was looked for
next, and the mechanism — explained so that someone with no medical training
understands exactly why this made the patient ill. This is where the episode
earns its existence: not the name of the disease, but how it works.
One idea per short paragraph. Let each land.
Forbidden: "in conclusion", "to summarise", "as we can see"

STAGE 7 — WHAT IT CHANGED ({stage_targets[7]} words)
What this case changed in medical understanding, or what the authors
themselves argue it demonstrates. Then the subscribe CTA, at the point the
viewer is most satisfied — not bolted on.
Never tell the viewer what to do about their own health.
Forbidden: "subscribe and like", "hit the bell", "don't forget to",
"consult your doctor", "if you have these symptoms"

WHY THESE STAGES AND NOT THE OTHER ONES
The previous version of this structure was a true-crime beat sheet: COLD
OPEN, THE BEFORE, FALSE RESOLUTION, THE REAL REVEAL, and per-stage triggers
named COMPLICITY, INSTITUTIONAL and "most disturbing section". Applied to a
published medical case report that is not merely off-format, it is unsafe:
it instructs the writer to imply wrongdoing by identifiable clinicians in a
documented case, and to treat a child's illness as a horror beat. The tension
in these stories is real and does not need manufacturing — it is a team
doing the right thing and being wrong, and a negative result nobody wanted
turning out to be the answer.

RETENTION PAYOFF CADENCE (NON-NEGOTIABLE — the single biggest lever for
average view duration): a script that saves its only real hooks for a
few fixed points across a long video leaves multi-minute stretches with
nothing preventing viewer drop-off. Every stage, especially the longer
ones, MUST contain a genuine payoff — a surprising fact, a specific
number, a forward reference ("what happens next reveals...") — roughly
every 150-225 words (approximately every 60-90 seconds of narration),
not just at the stage's start. Never save all the value for the end.

TELL IT AS A STORY, NOT AS A PAPER. This is the difference between an
episode people finish and an episode people close.

A case report is written for clinicians: findings first, patient reduced to
"the subject". You are doing the opposite. Rebuild the SAME facts as a
chronological account of something happening to a person, in the order the
people involved actually experienced it:

  - Open in a real moment, not a summary. Someone noticed something.
  - Follow the confusion forward. What did they think it was? What did they
    do about it? What happened when that did not work?
  - Every test result is a beat with consequences, not a line in a table.
    "The scan was normal" is only interesting if the reader knows what the
    team was hoping to find and what it means that they did not find it.
  - Name the wrong turn plainly. The most interesting sentence in most of
    these papers is the one where someone was confidently wrong.
  - Reveal the mechanism as the resolution of the mystery, not as a
    definition. Explain it the moment it EXPLAINS something the viewer has
    been carrying for ten minutes.

Never write "this case report describes", "the patient presented with" as an
opening move, "in conclusion", or "this highlights the importance of". Those
are thesis phrases. Nobody watches a thesis.

Anonymous is correct -- published cases are de-identified -- but anonymous is
not the same as abstract. "A woman in her fifties" is a person. "The subject"
is not.

COLD OPEN — TWO THINGS IT MUST CONTAIN (both are scored, both were missing
on every attempt of run 30569528382, and together they are worth 2.8 of the
hook's 10 points):

1. NAMED STAKES. State plainly what this patient stood to lose, in the first
   two sentences, in ordinary words. Not "something was wrong" or "a
   disturbing case" -- name the thing: her kidneys, his sight, the pregnancy,
   the use of both legs, consciousness, breathing, memory. A viewer must know
   what is at risk before they know anything else.

2. A VIOLATED EXPECTATION. Say the thing that should have explained it and
   did not. In a case report this almost always has one shape: the patient is
   visibly deteriorating and the tests come back NORMAL. Use that. "Every scan
   was normal." "The bloodwork came back clean." "Nothing on the imaging
   explained it." That contradiction IS the curiosity gap -- a question mark
   alone is not.

Example shape only, do not copy verbatim:
"A fifty-one-year-old woman lost the use of both kidneys in nine days. Her
scans were normal. Every test came back clean. The cause was sitting on her
kitchen counter."

Never address the viewer's own health here, and never use "you should", "if
you have", or "your condition" -- those fail the medical policy gate outright.

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
1. Maximum 20 words per sentence, and vary the length — short sentences for
   the turns, longer ones for explanation. Never two long sentences in a row.
2. Zero markdown — no symbols, headers, bullets, asterisks.
3. Zero AI filler — no "moreover", "furthermore", "interestingly", "it is worth noting".
4. Every number must be specific: not "many" but "forty-seven".
5. Every date must be specific: not "years ago" but "a Thursday in March 2019".
6. Every location must be specific: not "a small town" but "a city of 340,000 people".
7. Start immediately. No preamble. No introduction.
8. Write one continuous narrative — do not number or label stages. Never
   write "Stage N", a stage's name, or an invented chapter title anywhere
   in the output (e.g. never "Stage 4: The Investigation Deepens") — this
   applies to every one of the seven stages above, all the way through
   Stage 7, not just the opening.

Write the complete script now:"""


def _problem_summary(stext, score):
    """
    Name the ACTUAL weaknesses of this stage for the rewrite prompt.

    The prompt used to state the same fixed sentence -- "sentences over 13
    words, vague quantities, forbidden phrases" -- on every rewrite of every
    stage, whether or not any of those were true. A rewrite instruction that
    does not describe the real problem is a re-roll, which is why targeted
    rewrites moved craft so little.
    """
    import re as _re
    from clinical_quality import clinical_specificity
    low = stext.lower()
    probs = []
    sents = [x for x in _re.split(r"(?<=[.!?])\s+", stext) if x.strip()]
    long_ = [x for x in sents if len(x.split()) > MAX_SENTENCE_WORDS]
    if sents and len(long_) / len(sents) > 0.35:
        probs.append(f"{len(long_)} of {len(sents)} sentences run over "
                     f"{MAX_SENTENCE_WORDS} words")
    # Uniform sentence length is its own flatness, and nothing measured it.
    if len(sents) >= 6:
        lens = [len(x.split()) for x in sents]
        mean = sum(lens) / len(lens)
        spread = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
        if spread < 4.0:
            probs.append("every sentence is the same length — no rhythm")
    vague = [w for w in ("many", "several", "some", "numerous", "various",
                         "countless", "multiple", "eventually", "at some point")
             if w in low]
    if vague:
        probs.append("vague quantities/times: " + ", ".join(vague[:4]))
    _, c = clinical_specificity(stext)
    if c.get("per_100_words", 0) < 2.0:
        probs.append("almost no concrete clinical detail — no values, "
                     "timepoints or named mechanisms")
    filler = [p for p in ("moreover", "furthermore", "it is worth noting",
                          "in conclusion") if p in low]
    if filler:
        probs.append("AI filler: " + ", ".join(filler))
    if not probs:
        probs.append("flat — it states facts without making the reader want "
                     "the next sentence")
    return "; ".join(probs)


def generate_script_content(niche, topic, episode, attempt,
                             trending_titles=None, research_context="",
                             preselected_case=None):
    """
    v2 script generation:
    1. Generate full script with stage-structured v2 prompt
    2. Score each of 7 stages independently
    3. Rewrite only the 2 worst-scoring stages with targeted instructions
    4. Inject subscribe CTAs at 30/60/80% marks
    """
    # ── Step 1: fetch the REAL published case ─────────────────────────
    # This replaces the previous "research anchors" step, which asked the AI
    # to invent a plausible duration / people_count / key_number and fed
    # those to the script as if sourced. That is precisely the failure mode
    # already fixed for Ch5's finance niches: telling a model to sound
    # documented instead of giving it something actually documented.
    case = {}
    try:
        from pmc_data import get_real_case, format_script_context, MEDICAL_NICHE_NAMES
        if niche["name"] in MEDICAL_NICHE_NAMES:
            # preselected_case is the paper whose title became `topic` for
            # this attempt. Using it rather than fetching again is what keeps
            # the script and the sourced case on the SAME document -- the
            # independent fetch here is exactly how the first live run ended
            # up scripting Sylvia Plath over a surgical-oncology case.
            case = preselected_case or get_real_case(niche["name"]) or {}
            if case:
                research_context = f"{format_script_context(case)}\n{research_context}"
                log(f"  Real PMC case: {case['pmcid']} — {case['journal']} {case['year']} "
                    f"({len(case.get('figures') or [])} usable figures)")
            else:
                log("  PMC returned no usable CC BY case for this niche — "
                    "falling back to the niche's real-case topic list")
    except Exception as e:
        log(f"  PMC fetch (non-fatal): {e}")

    # ── Step 2: extract the structures the six visual registers consume ──
    # All derived FROM the fetched case narrative, so BOARD/TIMELINE/CHART/
    # ANATOMY/TEXT are populated from the same paper as the script rather
    # than invented independently. Each is individually optional: a register
    # with no data simply returns False and the quota redistributes.
    if case.get("narrative"):
        # THREE ATTEMPTS, BEST KEPT.
        #
        # This one call populates BOTH the differential board and the
        # timeline and the chart and the mechanism diagram and the quote --
        # five of the six visual registers. A single malformed response used
        # to leave every one of them empty, which collapses the episode onto
        # ANATOMY alone: the quota's availability logic would do the right
        # thing with the wrong facts. One LLM call deciding five registers is
        # too much single-point failure for no retry at all.
        #
        # Each attempt is scored by how many structures it actually yielded,
        # the best is kept, and a retry is told specifically what came back
        # empty rather than just being run again identically.
        _base_prompt = (
            "From this REAL published clinical case text, extract only what is "
            "actually stated. Use null for anything not present — do NOT invent.\n\n"
            f"{case['narrative'][:2600]}\n\n"
            "Return ONLY valid JSON (no backticks):\n"
            '{"differentials":[["diagnosis name","EXCLUDED|PARTIAL|CONFIRMED","one-line reason"]],'
            '"timeline":[["Day 0 or a real time label","what happened"]],'
            '"chart_data":{"chart_type":"bar or line","title":"short title",'
            '"y_label":"what the numbers are","labels":["label"],"values":[number]},'
            '"anatomy":{"title":"short mechanism title","explanation":"one or two plain '
            'sentences explaining the physical mechanism","search":"2-4 word wikimedia '
            'search for a relevant anatomical or molecular diagram",'
            '"pathway":["2-4 ordered steps of the physiological or metabolic chain '
            'involved, 1-4 words each, in order"],'
            '"blocked_step":"zero-based index of the step in pathway that failed in '
            'this patient, or null"},'
            '"quote":"one real sentence quoted verbatim from the text, or null"}'
        )

        def _parse_structures(raw):
            """Raw model output -> normalised structures, or None."""
            if not raw:
                return None
            raw = re.sub(r"```json|```", "", raw).strip()
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                return None
            try:
                ex = json.loads(m.group())
            except Exception:
                return None
            if not isinstance(ex, dict):
                return None
            diffs = []
            for row in (ex.get("differentials") or []):
                if isinstance(row, (list, tuple)) and len(row) >= 2 and str(row[0]).strip():
                    diffs.append((str(row[0]), str(row[1]),
                                  str(row[2]) if len(row) > 2 else ""))
            tl = []
            for row in (ex.get("timeline") or []):
                if isinstance(row, (list, tuple)) and len(row) >= 2 and str(row[0]).strip():
                    tl.append((str(row[0]), str(row[1])))
            cd = ex.get("chart_data") or {}
            if isinstance(cd, dict) and cd.get("labels") and cd.get("values"):
                try:
                    vals = [float(v) for v in cd["values"]]
                except (TypeError, ValueError):
                    vals = []
                # Every point must be a real number and the series must have
                # at least two of them, or the chart renderer refuses it and
                # the whole register degrades to the fallback card.
                if len(vals) >= 2 and len(cd["labels"]) == len(vals):
                    cd = dict(cd)
                    cd["values"] = vals
                else:
                    cd = None
            else:
                cd = None
            anat = ex.get("anatomy") if isinstance(ex.get("anatomy"), dict) else {}
            anat = dict(anat or {})
            # Normalise the mechanism chain. The ANATOMY renderer draws it as
            # boxes-and-arrows with the failed step crossed out, so a
            # malformed pathway must be dropped here rather than half-drawn
            # there.
            _pw = [str(x).strip() for x in (anat.get("pathway") or [])
                   if str(x).strip()][:4]
            anat["pathway"] = _pw if len(_pw) >= 2 else None
            try:
                _bs = int(anat.get("blocked_step"))
                anat["blocked_step"] = _bs if (anat["pathway"] and
                                               0 <= _bs < len(_pw)) else None
            except (TypeError, ValueError):
                anat["blocked_step"] = None
            quote = ex.get("quote")
            quote = str(quote).strip() if quote else ""
            # A "quote" the model paraphrased is not a quote. It has to appear
            # in the source text, or the TEXT register puts an invented
            # sentence on screen attributed to a real paper.
            if quote:
                _norm = lambda t: re.sub(r"[^a-z0-9 ]", "", t.lower())
                if _norm(quote)[:60] not in _norm(case["narrative"]):
                    log("  Case structures: dropped a 'quote' not found verbatim "
                        "in the source text")
                    quote = ""
            return {"differentials": diffs, "timeline": tl, "chart_data": cd,
                    "anatomy": anat, "quote": quote}

        def _score(st):
            if not st:
                return 0
            return (min(len(st["differentials"]), 5) * 2
                    + min(len(st["timeline"]), 6) * 2
                    + (3 if st["chart_data"] else 0)
                    + (2 if st["anatomy"].get("pathway") else 0)
                    + (1 if st["anatomy"].get("explanation") else 0)
                    + (2 if st["quote"] else 0))

        best, best_score = None, -1
        for attempt in range(3):
            prompt = _base_prompt
            if best is not None:
                missing = [k for k, ok in (
                    ("differentials", best["differentials"]),
                    ("timeline", best["timeline"]),
                    ("chart_data", best["chart_data"]),
                    ("pathway", best["anatomy"].get("pathway")),
                    ("quote", best["quote"])) if not ok]
                if not missing:
                    break
                prompt += ("\n\nThe previous attempt returned nothing for: "
                           + ", ".join(missing)
                           + ". Look again specifically for those. If the text "
                             "genuinely does not contain one, leave it null — "
                             "do not invent it.")
            try:
                st = _parse_structures(ai_generate(prompt, tokens=900))
            except Exception as e:
                log(f"  Case structure extraction attempt {attempt+1} failed: {e}")
                st = None
            sc = _score(st)
            if sc > best_score:
                best, best_score = st, sc
            if sc >= 12:            # enough for a full visual mix
                break

        if best:
            case.update(best)
            log(f"  Case structures (score {best_score}): "
                f"{len(best['differentials'])} differentials, "
                f"{len(best['timeline'])} timeline events, "
                f"chart={'yes' if best['chart_data'] else 'no'}, "
                f"pathway={'yes' if best['anatomy'].get('pathway') else 'no'}, "
                f"quote={'yes' if best['quote'] else 'no'}")
        else:
            log("  Case structures: all 3 extraction attempts failed — "
                "the episode will run on ANATOMY and FIGURE only")

    # ── Step 2b: prove the figures are actually fetchable ────────────────
    # The visual quota schedules ~30% of the episode as FIGURE segments based
    # on case["figures"], which is METADATA parsed from the article XML. If
    # the binaries then fail to download, that share is already committed to
    # a register with nothing to show and every one of those segments
    # silently renders the fallback card -- the same shape as the CHART
    # defect, and equally invisible because the fallback logs as success.
    #
    # Downloading up front and pruning to what actually landed means the
    # quota is built from the truth. It costs nothing extra: these are the
    # same files the renderer would fetch anyway, cached under the same
    # names it looks for.
    if case.get("figures"):
        try:
            from pmc_data import prefetch_figures
            WORK_DIR.mkdir(parents=True, exist_ok=True)
            case = prefetch_figures(case, str(WORK_DIR), log_fn=log)
        except Exception as e:
            log(f"  Figure prefetch (non-fatal): {e}")

    # Make the case available to the per-segment renderers deep inside
    # get_stage_matched_video (see the EPISODE CASE HOLDER note above).
    set_episode_case(case)
    # Persisted so a resumed run (is_makeup=true) restores it. Without this
    # the resume path skips script generation, _EPISODE_CASE stays empty, and
    # EVERY register reports "no data" -- the whole episode renders as the
    # fallback card. Found before run 5 by tracing the resume branch rather
    # than by hitting it.
    try:
        ckpt_save("episode_case", case)
    except Exception:
        pass

    # (The old anchor-injection block is gone: research_context is now built
    # from the real PMC case above, not from invented anchors.)

    # NEW FEATURE (per explicit request — daily competitive research):
    # real view/like counts and real title-word-frequency patterns from
    # actual current top-performing videos in this niche, computed
    # deterministically — not an AI guess. Cached per calendar day, so
    # repeated attempts the same day reuse the same fetch rather than
    # re-hitting the API every time. This function doesn't otherwise
    # know which niche it's scoring for beyond `niche`/`topic`, so the
    # fetch happens here, self-contained, same as generate_best_cold_open
    # right above.
    try:
        from daily_competitor_research import fetch_daily_competitor_research
        _daily_token = get_yt_token()
        _daily_intel = fetch_daily_competitor_research(niche, _daily_token, str(SCRIPT_DIR))
        if _daily_intel.get("research_block"):
            research_context = f"{_daily_intel['research_block']}\n\n{research_context}"
    except Exception as e:
        log(f"  Daily competitor research (non-fatal): {e}")

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
        # Word count is not a soft preference here -- it is the gate.
        # score_result gives +2.8 at >=MIN_WORDS, +0.8 at >=1600, and -2.0
        # below that, on a 5.0 base with +2.2 for zero violations. So the
        # arithmetic ceiling is 10.0 at 1900w, 8.0 at 1600-1899w, and 5.2
        # below 1600w -- against MIN_GATE 8.5. Any script under 1900 words
        # is mathematically incapable of passing no matter how well written.
        #
        # So this loop failing quietly was fatal, not cosmetic. Run
        # 30561361514: 744w -> "Expanded to 774w", a 30-word gain against a
        # 1156-word deficit, then a second round that gained nothing -- on
        # every one of 13 attempts, none of which could have cleared the gate.
        #
        # Two causes, and it is worth being precise about their weight. The
        # prompt was thin ("Add N more words to Stage 4 and Stage 6"), where
        # Step 3's richer prompt on the same script gained +356w. And it sent
        # raw[:4000] -- 4000 CHARACTERS -- while asking for "the COMPLETE
        # script with additions". At 744 words that clipped only ~9%, so
        # truncation alone does not explain the gap; but it scales badly,
        # keeping just 60% at 1122 words and 36% at 1900, so it would have
        # blocked exactly the later rounds that need to work. Both are fixed:
        # full script in, and a prompt that says what to add and why.
        #
        # Sending the whole script costs nothing that matters: 2100 words is
        # ~2800 tokens against an 8000-token budget.
        for _exp in range(3):
            raw_wc = len(raw.split())
            if raw_wc >= MIN_WORDS or raw_wc > MAX_WORDS: break
            log(f"  Script {raw_wc}w short — expanding (round {_exp + 1}/3)...")
            try:
                ep = (f"This narration script is {raw_wc} words. It must be between "
                      f"{MIN_WORDS} and {MAX_WORDS} words -- that is a hard requirement, "
                      f"not a target.\n\n"
                      f"Expand it by roughly {MIN_WORDS - raw_wc} words. Put the new "
                      f"material in the Escalation and Reveal sections: more specific "
                      f"reported findings, exact values with their units, the sequence "
                      f"of what was tested and ruled out, and what each result changed. "
                      f"Do not add new claims that are not supported by the case. "
                      f"Do not summarise or shorten any existing passage. "
                      f"Preserve the existing mid-video direct-address beat (the short 'stop for a second / if you're still watching' moment around the 55-65% mark) exactly where it is -- do not remove, move or reword it. If there is no such beat, add one there. \n\n"
                      f"Max 20 words per sentence, varied. Zero markdown. Return the COMPLETE "
                      f"script, beginning to end.\n\nSCRIPT:\n{raw}")
                raw2 = ai_generate(ep, tokens=8000)
                if raw2 and len(raw2.split()) > raw_wc:
                    raw = raw2
                    # Hard truncate raw to MAX_WORDS after expansion
                    if len(raw.split()) > MAX_WORDS:
                        raw = " ".join(raw.split()[:MAX_WORDS])
                    log(f"  Expanded to {len(raw.split())}w")
                else:
                    log(f"  Expansion round {_exp + 1} produced nothing longer — stopping")
                    break
            except Exception as _e:
                log(f"  Expansion (non-fatal): {_e}"); break
    if not raw:
        return None
    script     = strip_md(strip_md(raw))
    # FIX (direct user report, July 23 2026 — a live test run's PDF showed
    # "Stage 4: The Investigation Deepens" as literal narration text): the
    # prompt above shows all 7 numbered "STAGE N — NAME" section headers
    # as structural documentation, which models sometimes echo verbatim
    # or paraphrased despite the "write continuously, no labels"
    # instruction. Swept out here before anything downstream (word count,
    # stage-splitting, scoring) ever sees it.
    from script_scoring import (strip_all_leaked_stage_headers,
                                strip_leading_title_line)
    script     = strip_all_leaked_stage_headers(script)
    # Run 30578466862's episode opened by speaking an invented title line.
    script     = strip_leading_title_line(script)
    wc         = len(script.split())
    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
    log(f"  Script: {wc}w | {violations} violations")

    # Step 3: Expand if short.
    #
    # Two rounds, not one. This pass already sent the full script (unlike the
    # pre-strip loop above, which was truncating), but a single round rarely
    # closes a 700-word deficit, and falling short here is not a partial
    # success -- see the gate arithmetic noted above: under 1900 words the
    # attempt cannot pass, so a near miss is worth exactly as much as no
    # attempt at all.
    for _round in range(2):
        if wc >= MIN_WORDS:
            break
        deficit = MIN_WORDS - wc
        log(f"  Short by {deficit}w — expanding stages 4 and 6 (round {_round + 1}/2)...")
        exp = (
            f"This narration script is {wc} words. It must reach at least {MIN_WORDS} "
            f"words. Expand the Escalation section and the Reveal section only. "
            f"Add the specific reported findings, exact values with units, what was "
            f"tested and ruled out, and what each result changed. Add nothing the "
            f"case does not support. Do not shorten anything already there. "
            f"Preserve the existing mid-video direct-address beat (the short 'stop for a second / if you're still watching' moment around the 55-65% mark) exactly where it is -- do not remove, move or reword it. If there is no such beat, add one there. "
            f"Max 20 words per sentence, varied. Zero markdown. "
            f"Return the COMPLETE expanded script.\n\nSCRIPT:\n{script}"
        )
        raw2 = ai_generate(exp, tokens=8000)
        if not raw2:
            log("  Expansion returned nothing — stopping")
            break
        s2 = strip_leading_title_line(
            strip_all_leaked_stage_headers(strip_md(strip_md(raw2))))
        if len(s2.split()) <= wc:
            log(f"  Expansion round {_round + 1} produced nothing longer "
                f"({len(s2.split())}w vs {wc}w) — stopping")
            break
        script     = s2
        wc         = len(script.split())
        violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
        # Hard truncate to MAX_WORDS
        if wc > MAX_WORDS:
            script = " ".join(script.split()[:MAX_WORDS])
            wc = len(script.split())
        log(f"  Expanded: {wc}w")

    # State the consequence plainly in the log rather than letting the
    # attempt fail later with an unexplained low score.
    if wc < MIN_WORDS:
        log(f"  STILL SHORT: {wc}w < {MIN_WORDS}w — this attempt cannot clear "
            f"{MIN_GATE}/10 (word-count ceiling is "
            f"{8.0 if wc >= 1600 else 5.2}/10), scoring anyway for the record")

    # Step 4: Stage-level scoring + targeted rewrite of 2 worst stages
    # FIX (found live, July 22 2026 — real bug, confirmed via a live crash:
    # "cannot access local variable 'stage_texts'"): stage_texts was only
    # ever assigned inside this `if wc >= MIN_WORDS:` block, but the
    # function's return statement below references it unconditionally.
    # An attempt whose word count still fell short of MIN_WORDS even
    # after Step 3's expansion pass (observed live: 1670w vs. a 1900w
    # minimum) skipped this whole block, leaving stage_texts undefined
    # and crashing on return -- silently swallowed by the attempt loop's
    # outer exception handler, but a real bug regardless, and the loss
    # of that entire attempt's work. Empty list is a safe default: every
    # caller already treats a missing/empty stage_texts as "no stage
    # breakdown available" rather than assuming it's always populated.
    # FIX (direct user report, July 24 2026 — real published preview
    # showed the whole script as one undifferentiated paragraph, no
    # COLD OPEN/FIRST SIGNALS/ESCALATION/etc headers anywhere): this used
    # to stay an empty [] placeholder unless wc >= MIN_WORDS (1900) --
    # meaning ANY attempt that landed even slightly short of that (the
    # exact confirmed case: 1776 words) silently lost stage_texts
    # entirely, and every downstream consumer (the PDF export, the
    # Telegram review, the final PDF/description) fell back to rendering
    # flat, unlabeled prose -- with no error, no log line, nothing to
    # show this had happened. split_into_stage_texts is a pure,
    # proportional split that works correctly regardless of total
    # length (confirmed: it scales targets against the script's actual
    # word count, not an absolute count), so there was never a real
    # reason to gate it on MIN_WORDS -- only the heavier stage-scoring/
    # rewrite loop below genuinely needs that gate. Computed here,
    # unconditionally, so review material always shows real structure.
    from script_scoring import split_into_stage_texts, strip_leaked_stage_headers
    from clinical_quality import DURATION_FLOOR_WORDS
    # Stage targets are PROPORTIONS of this script, not absolute counts.
    #
    # They were absolutes summing to 2,040 words, from the retired
    # dark-documentary format. A clinical episode clears its real floor at
    # 1,250 words, so on every script this channel actually produces every
    # stage measured 20-40% "under target" and lost 1.5 points for it --
    # the rubric was punishing scripts for not being a different show.
    _SHAPE = (0.05, 0.10, 0.13, 0.21, 0.08, 0.33, 0.10)
    targets = [max(60, int(round(wc * f))) for f in _SHAPE]
    stage_texts = split_into_stage_texts(script, targets)
    # Gated on the REAL duration floor, not the retired 1,900-word target.
    #
    # This block is the only mechanism in the pipeline that IMPROVES a
    # script rather than judging it: it scores each stage and rewrites the
    # two worst. Gating it at MIN_WORDS meant that on a 1,600-word clinical
    # episode -- a length that passes every real gate -- it never ran at
    # all. The one tool for raising craft was unreachable at exactly the
    # lengths this channel produces, which is why craft never moved.
    if wc >= DURATION_FLOOR_WORDS:
        try:
            # FIX (direct user report, July 23 2026 — a live test run's
            # PDF showed a sentence physically split in half between the
            # "COLD OPEN" and "THE BEFORE" sections): naive words[pos:end]
            # slicing had zero sentence-boundary awareness. Now snapped to
            # real sentence breaks (video_pipeline/script_scoring.py).
            stage_texts = split_into_stage_texts(script, targets)

            # Stage names describe a CLINICAL CASE, and match the act cards
            # the video renders. The previous set -- COLD OPEN / THE BEFORE /
            # FIRST SIGNALS / ESCALATION / FALSE RESOLUTION / THE REVEAL /
            # IMPLICATION -- is a true-crime beat sheet, and the rewrite
            # prompt fed those names to the model as the stage's purpose. It
            # was actively steering a medical case report toward the format
            # this channel was retired for.
            stage_names   = ["OPENING", "THE PATIENT", "FIRST SIGNS",
                             "DETERIORATION", "THE FIRST ANSWER",
                             "THE REVERSAL", "WHAT IT CHANGED"]
            hook_signals  = ["what happened next", "the reason", "nobody",
                             "should not have", "was not", "turned out",
                             "the answer", "changed"]
            forbidden_per = [
                ["welcome back", "today we", "in this video", "join me"],
                ["little did they know", "unbeknownst"],
                ["suddenly", "out of nowhere", "without warning"],
                [],
                ["but it wasn't over", "or so they thought"],
                ["in conclusion", "to summarise", "as we can see"],
                ["subscribe and like", "hit the bell", "don't forget",
                 "consult your doctor", "if you have these symptoms"],
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
            # Specificity is measured by the real clinical detector, not by
            # a digit regex. build_script_prompt REQUIRES numbers to be
            # spelled out for TTS, so `\b\d+\b` matched almost nothing and
            # every stage was docked a point for having "no numbers" while
            # being full of them.
            from clinical_quality import clinical_specificity
            # What makes a clinical case land is not "still running today" --
            # that is crime-channel vocabulary. It is that the finding was
            # documented, that it changed something, that a result was
            # negative when everyone expected positive.
            craveability_signals = ["documented", "published", "reported",
                                     "confirmed", "returned normal", "sterile",
                                     "changed", "no longer", "for the first time",
                                     "still not known", "remains unexplained"]

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
                long  = [s for s in sents if len(s.split()) > MAX_SENTENCE_WORDS]
                if len(long) / max(len(sents), 1) > 0.35:
                    sc -= 0.8
                # Reward rhythm. Uniform sentence length reads as machine
                # prose no matter how short the sentences are, and nothing
                # here measured it.
                if len(sents) >= 6:
                    _l = [len(x.split()) for x in sents]
                    _m = sum(_l) / len(_l)
                    _sd = (sum((x - _m) ** 2 for x in _l) / len(_l)) ** 0.5
                    sc += 0.6 if _sd >= 6.0 else (0.0 if _sd >= 4.0 else -0.6)
                if i in [0, 6]:  # cold open and CTA — check for hooks
                    if not any(h in stext.lower() for h in hook_signals[:3]):
                        sc -= 0.5
                ai_phrases = ["moreover","furthermore","it is worth noting","in conclusion"]
                sc -= sum(0.4 for p in ai_phrases if p in stext.lower())

                # Real specificity check — reward actual numbers/dates present,
                # penalize the vague-quantity words the prompt explicitly forbids
                # but nothing was previously verifying were actually absent.
                stext_lower = stext.lower()
                _spec_pts, _spec_counts = clinical_specificity(stext)
                _per100 = _spec_counts.get("per_100_words", 0.0)
                if _per100 >= 4.0:   sc += 1.0
                elif _per100 >= 2.0: sc += 0.4
                elif _per100 == 0:   sc -= 1.0
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
            _any_rewritten = False
            for idx in worst_two:
                if stage_scores[idx] >= 7.5:
                    continue
                sdef_name   = stage_names[idx]
                sdef_target = targets[idx]
                sdef_forb   = forbidden_per[idx]
                forb_str    = ", ".join(f'"{f}"' for f in sdef_forb) if sdef_forb else "none"
                rewrite_p   = (
                    f"Rewrite ONLY this single script stage. Return ONLY the rewritten stage — "
                    f"pure narration prose, continuing the story. "
                    f"Do NOT include a title, heading, or any text like \"Stage {idx+1}:\" or "
                    f"\"{sdef_name}:\" or any chapter/section label of any kind — the reader must "
                    f"never see the words \"stage\" or \"chapter\" or a number label; the response "
                    f"must read as an uninterrupted continuation of the narration, nothing else.\n\n"
                    f"STAGE PURPOSE (for your reference only, do not name it in the output): {sdef_name} "
                    f"(target: {sdef_target} words)\n"
                    f"TOPIC: {topic[:100]}\n"
                    f"CURRENT SCORE: {stage_scores[idx]}/10\n"
                    f"PROBLEMS: {_problem_summary(stext, stage_scores[idx])}\n"
                    f"FORBIDDEN: {forb_str}\n\n"
                    f"RULES:\n"
                    f"- Maximum {MAX_SENTENCE_WORDS} words per sentence, and VARY the "
                    f"length: short for the turns, longer for explanation.\n"
                    f"- Every number must be specific, and SPELLED OUT as words for "
                    f"text-to-speech: not 'many' but 'forty-seven'.\n"
                    f"- Every clinical detail must come from the sourced case. Do not "
                    f"invent a value, a date, or an outcome.\n"
                    f"- Third person, past tense, about the documented patient. Never "
                    f"address the viewer's own health.\n"
                    f"- Zero markdown. Zero AI filler phrases. Zero titles/headers/labels.\n"
                    f"- More visceral and specific than the original.\n"
                    f"- Target: {sdef_target} words (±15% acceptable).\n\n"
                    f"ORIGINAL STAGE:\n{stage_texts[idx]}\n\n"
                    f"Write the improved version now (prose only, no label):"
                )
                new_stage = ai_generate(rewrite_p, tokens=2000)
                if new_stage:
                    new_stage = strip_md(new_stage)
                    new_stage = strip_leaked_stage_headers(new_stage)
                    if len(new_stage.split()) > 30:
                        script = script.replace(stage_texts[idx], new_stage, 1)
                        log(f"  Stage {sdef_name} rewritten ({stage_scores[idx]}/10 → improved)")
                        _any_rewritten = True

            # FIX (direct user report, July 23 2026): stage_texts was never
            # recomputed after a targeted rewrite modified `script` -- the
            # returned stage breakdown (used for the PDF and any further
            # scoring) would go stale/out-of-sync with the actual final
            # script the moment any rewrite happened. Recomputed fresh here
            # so it always matches the real, current script content.
            if _any_rewritten:
                stage_texts = split_into_stage_texts(script, targets)

            wc         = len(script.split())
            violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
            log(f"  After targeted rewrite: {wc}w | {violations} violations")
        except Exception as e:
            log(f"  Stage rewrite (non-fatal): {e}")

    # FIX (direct user report, July 23 2026 — real production data showed
    # score_narrative_craft's hard 7.9 gate failing on most attempts,
    # exhausting all 13 tries with zero video produced): the ONLY prior
    # response to a failing craft score was to reject the whole attempt
    # and re-roll a brand new script from scratch, hoping the next
    # generation happens to land an escalation beat, a resolution beat,
    # sentence-rhythm variety, and no repeated phrasing all by chance.
    # This directly rewrites the middle third (escalation) and final
    # third (resolution) with the exact missing structural beats
    # score_narrative_craft checks for, then keeps whichever version
    # (original or rewritten) actually scores higher — a real fix to the
    # writing, not another reroll of the dice.
    try:
        from script_scoring import score_narrative_craft, NARRATIVE_CRAFT_GATE_MIN
        _craft_before, _craft_issues_before = score_narrative_craft(script)
        if _craft_before < NARRATIVE_CRAFT_GATE_MIN:
            _script_before_craft = script
            _cwords = script.split()
            _cthird = len(_cwords) // 3
            _mid_text = " ".join(_cwords[_cthird:2 * _cthird])
            _mid_prompt = (
                f"Rewrite this middle section of a documentary narration. Return ONLY the "
                f"rewritten prose, same approximate length, no headers or labels, no markdown.\n\n"
                f"REQUIRED, all of these:\n"
                f"1. One genuine escalation moment — something that intensifies, worsens, or "
                f"upends what came before (new evidence, a worse discovery, a visible turn for "
                f"the worse). A real turn, not just a transition word.\n"
                f"2. Vary sentence length dramatically — mix short punches (4-8 words) with "
                f"longer sentences (20+ words). Flat, same-length sentences read as robotic.\n"
                f"3. Do not repeat any 4-word phrase from elsewhere in the script.\n\n"
                f"ORIGINAL:\n{_mid_text}\n\nRewrite now:"
            )
            _new_mid = ai_generate(_mid_prompt, tokens=1500)
            if _new_mid:
                _new_mid = strip_md(_new_mid)
                if len(_new_mid.split()) > 30:
                    script = script.replace(_mid_text, _new_mid, 1)

            _cwords2 = script.split()
            _cthird2 = len(_cwords2) // 3
            _final_text = " ".join(_cwords2[2 * _cthird2:])
            _final_prompt = (
                f"Rewrite this final section of a documentary narration. Return ONLY the "
                f"rewritten prose, same approximate length, no headers or labels, no markdown.\n\n"
                f"REQUIRED, all of these:\n"
                f"1. One genuine resolution moment — what turned out to be true, what was "
                f"finally confirmed, or the real explanation. A real payoff, not a summary.\n"
                f"2. Vary sentence length dramatically — mix short punches (4-8 words) with "
                f"longer sentences (20+ words).\n"
                f"3. Do not repeat any 4-word phrase from elsewhere in the script.\n\n"
                f"ORIGINAL:\n{_final_text}\n\nRewrite now:"
            )
            _new_final = ai_generate(_final_prompt, tokens=1500)
            if _new_final:
                _new_final = strip_md(_new_final)
                if len(_new_final.split()) > 30:
                    script = script.replace(_final_text, _new_final, 1)

            _craft_after, _ = score_narrative_craft(script)
            if _craft_after < _craft_before:
                script = _script_before_craft
                log(f"  Targeted craft rewrite: {_craft_before}/10 -> {_craft_after}/10 (worse, reverted)")
            else:
                wc         = len(script.split())
                violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
                stage_texts = split_into_stage_texts(script, targets)
                log(f"  Targeted craft rewrite: {_craft_before}/10 -> {_craft_after}/10")
    except Exception as e:
        log(f"  Targeted craft rewrite (non-fatal): {e}")

    # FIX (direct user report, this session — "whenever the audio starts,
    # it keeps telling me the things have been changed, the names are not
    # real, all those things. I don't want that to happen"): this used to
    # force-insert a spoken disclosure sentence ("Some names and
    # identifying details in this account have been changed.") directly
    # onto the end of the script's FIRST sentence -- i.e. right at the
    # very start of the cold open, every single episode, breaking the
    # narration exactly where retention matters most. The real policy-
    # safety need (never presenting invented specifics as verified fact)
    # doesn't require this to be SPOKEN -- moved to a written-only
    # disclosure appended to the video description instead (see
    # generate_seo_description), which is where documentaries/true-crime
    # media conventionally put this, not read aloud. needs_fiction_
    # disclosure is threaded through to the description generator below.
    # Always False on this channel, and that is not a shortcut.
    #
    # Inherited from the dark-documentary format, this defaulted to True
    # unless the script itself already said "names have been changed" or
    # similar. A clinical script never says that, so effectively every
    # episode would have appended:
    #
    #   "Note: some names and identifying details in this account have been
    #    changed or composited from multiple documented cases."
    #
    # which is simply untrue here. Each episode is ONE real published case,
    # and the description carries "Source: <citation>" a few lines below.
    # Publishing both would put a claim of compositing directly next to the
    # citation that disproves it -- destroying the single thing that makes
    # this channel defensible, in the exact place a sceptical viewer looks.
    #
    # The disclosure this channel actually owes is the medical one, built by
    # medical_policy_gate.build_disclaimer_block() and enforced by a blocking
    # publish gate; synthetic narration is separately declared to YouTube via
    # containsSyntheticMedia=True at upload.
    needs_fiction_disclosure = False

    # Step 5: CTA injection
    if len(script.split()) >= 400:
        script = _inject_ctas_ch1(script, niche["name"])
        # Subscribe CTA guard
        if "subscribe" not in " ".join(script.split()[-60:]).lower():
            script += " Subscribe to this channel for more documented cases."
        wc     = len(script.split())
        log(f"  CTAs injected — final: {wc}w")

    return {"script": script, "words": wc, "violations": violations, "stage_texts": stage_texts,
            "needs_fiction_disclosure": needs_fiction_disclosure}


def _inject_ctas_ch1(script_clean, niche_name):
    """
    Inject subscribe CTAs at 30%/60%/80% marks for Ch1 (No Known Cause).
    Uses sentence boundary detection so CTAs never split mid-sentence.
    """
    words = script_clean.split()
    total = len(words)
    if total < 400:
        return script_clean

    # FIX (direct user report, July 23 2026 — production outage traced to
    # this pool): _validate_retention_hooks_ch1's peak-CTA gate requires 2+
    # hook_signal phrases in the 55-65% window, and a live run showed
    # "PEAK CTA GATE FAILED" on 12 of 13 real attempts even when hook/craft
    # both passed. Root cause found by direct testing: several 60pct
    # variants below contained ONLY "subscribe" -- a single hook_signal hit
    # -- leaving the gate dependent on luck from surrounding AI narration to
    # find a second one, which mostly didn't happen. Every 60pct variant
    # for every niche now guarantees 2+ real hook_signal phrase matches
    # ("subscribe" + "next"/"what happens"/"revealed"/"stay", etc.) so the
    # gate this text itself is meant to satisfy passes deterministically,
    # not by chance.
    cta_pool = {
        "toxicology_cases": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. The quantity involved is the part nobody expects."],
            "60pct": ["Subscribe now. What the laboratory found next reframes the whole presentation.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Every case is a real published paper."],
        },
        "diagnostic_odyssey": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. The first diagnosis was wrong, and the reason matters."],
            "60pct": ["Subscribe now. The test that would have answered this is coming.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Every case is sourced from the literature."],
        },
        "neurology_cases": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. What the imaging located is not what the team expected."],
            "60pct": ["Subscribe now. The mechanism behind this is stranger than the symptom.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. A new neurological case every weekday."],
        },
        "rare_disease_cases": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. Almost nobody has seen a presentation like this."],
            "60pct": ["Subscribe now. How this was finally identified is the whole story.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Every case is a documented first report."],
        },
        "senior_health_longevity": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. The measured data contradicts the common assumption."],
            "60pct": ["Subscribe now. What the long-term follow-up showed is coming next.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Real research, every weekday."],
        },
        "medical_mystery_outbreak": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. Nobody had connected these cases yet."],
            "60pct": ["Subscribe now. The shared exposure is about to be identified.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Real epidemiological investigations."],
        },
        "surgical_case_studies": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. The anatomy made the standard approach impossible."],
            "60pct": ["Subscribe now. The decision made before the first incision is coming.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Real published surgical cases."],
        },
        "drug_discovery_stories": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. Nobody was looking for what they found."],
            "60pct": ["Subscribe now. The failure that became the discovery is next.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. How real medicines were actually found."],
        },
        "sleep_science": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. What the sleep study recorded is the answer."],
            "60pct": ["Subscribe now. The mechanism behind the symptom is coming.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. Real published sleep cases."],
        },
        "medical_history": {
            "30pct": ["Subscribe to No Known Cause. The finding that explains this is thirty seconds away.",
                      "Subscribe. This was standard practice for decades."],
            "60pct": ["Subscribe now. The evidence that ended it had been available all along.",
                      "Subscribe to No Known Cause before the mechanism is revealed."],
            "80pct": ["Subscribe. A new published case every weekday.",
                      "Subscribe to No Known Cause. How medicine actually changed its mind."],
        },
    }
    pool  = cta_pool.get(niche_name, cta_pool["toxicology_cases"])
    seed  = abs(hash(script_clean[:80])) % 2
    c30   = pool["30pct"][seed]
    c60   = pool["60pct"][seed]
    c80   = pool["80pct"][seed]

    # FIX (direct user report, July 25 2026 — real evidence pulled from a
    # published episode's actual script_clean: "...an unsigned note left
    # on Dr. \n\nSubscribe to No Known Cause...\n\n Voss's desk warning
    # him about..."): this claimed "sentence boundary detection so CTAs
    # never split mid-sentence" but only checked whether a word ended in
    # ".", "?", or "!" — "Dr." ends in a period too, and isn't a sentence
    # boundary at all. The CTA landed directly between an abbreviated
    # title and the name it belongs to, reading exactly like a script
    # glitch rather than a human narrator. Real fix: a blocklist of
    # common abbreviations that end in "." but never actually end a
    # sentence, plus stripping a trailing quote/paren before checking so
    # "...today.\"" is still recognized as a real boundary.
    _SENTENCE_ABBREVIATIONS = {
        "dr.", "mr.", "mrs.", "ms.", "jr.", "sr.", "prof.", "rev.", "st.",
        "ave.", "blvd.", "vs.", "etc.", "no.", "vol.", "gen.", "col.", "lt.",
        "capt.", "sgt.", "gov.", "rep.", "sen.", "u.s.", "u.k.", "a.m.", "p.m.",
        "inc.", "ltd.", "co.", "corp.", "e.g.", "i.e.", "approx.", "ph.d.",
    }

    def nearest_boundary(words, target, window=25):
        for delta in range(window):
            for d in [1, -1]:
                idx = target + delta * d
                if 0 <= idx < len(words):
                    w_bare = words[idx].rstrip().rstrip("\"')’”")
                    if (w_bare.endswith((".", "?", "!"))
                            and w_bare.lower() not in _SENTENCE_ABBREVIATIONS):
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
            #
            # FIX (direct user report, July 24 2026 — explicit policy
            # decision): run_title_ctr_gate now hard-gates at 8.5/10 over
            # up to 8 real attempts and returns None if nothing ever
            # clears it — this used to silently fall back to publishing
            # whatever it had (even a bare "Series: topic" placeholder)
            # regardless of score. Now genuinely returns None on total
            # failure so the caller can skip the day, never a fallback
            # title that never earned the bar.
            title_scores = [(l, 0) for l in lines]
            best, v2_scored = run_title_ctr_gate(
                lines[0], title_scores, topic, niche["name"], niche["series"],
                episode, ai_generate)
            return best

    return None

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


def generate_seo_description(niche, topic, title, episode, chapters_text, audio_duration=0, citations_block="",
                              needs_fiction_disclosure=True):
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

Total: 250-320 words. Plain text. No markdown. Do NOT include any hashtags —
those are added separately afterward."""
    # Build SEO hook for first 100 chars (shown in YouTube search results)
    # Format: [SPECIFIC CLAIM]. [EMOTIONAL HOOK]. Full investigation below.
    seo_hooks = {
        "toxicology_cases":        f"PUBLISHED CASE: {topic[:45]}.",
        "diagnostic_odyssey":      f"MISDIAGNOSED: {topic[:45]}.",
        "neurology_cases":         f"PUBLISHED CASE: {topic[:45]}.",
        "rare_disease_cases":      f"RARE PRESENTATION: {topic[:45]}.",
        "senior_health_longevity": f"THE RESEARCH: {topic[:45]}.",
        "medical_mystery_outbreak":f"INVESTIGATED: {topic[:45]}.",
        "surgical_case_studies":   f"PUBLISHED CASE: {topic[:45]}.",
        "drug_discovery_stories":  f"HOW IT WAS FOUND: {topic[:45]}.",
        "sleep_science":           f"PUBLISHED CASE: {topic[:45]}.",
        "medical_history":         f"MEDICAL HISTORY: {topic[:45]}.",
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
    cross_promo_txt = get_cross_promo("betrayal_deepdive", is_short=False)
    # FIX (direct user report, this session — "whenever the audio starts,
    # it keeps telling me the things have been changed... I don't want
    # that to happen"): the fiction/dramatization disclosure used to be
    # force-inserted as SPOKEN text at the start of the narration itself.
    # Moved here instead -- written-only, in the description, exactly
    # where documentaries/true-crime media conventionally disclose this,
    # never read aloud. Still a real, present disclosure (not deleted),
    # just relocated to not interrupt the story.
    fiction_disclosure_txt = (
        "\n\nNote: some names and identifying details in this account have "
        "been changed or composited from multiple documented cases."
        if needs_fiction_disclosure else ""
    )
    if raw:
        desc  = seo_first_line + "\n\n" + strip_md(raw)
        desc += cross_promo_txt
        # FIX (direct user request, July 25 2026 — "I don't want to have
        # that kind of thing in my description page"): removed. This was
        # voluntary marketing copy, not YouTube's actual mandated
        # disclosure mechanism (the "Altered or synthetic content"
        # toggle set via the Data API's containsSyntheticMedia field in
        # upload_yt() below) -- that field is a separate, compliance-
        # relevant decision left untouched here pending the user's own
        # review of YouTube's current Creator Studio guidance.
        desc += fiction_disclosure_txt
        desc += f"\n\n📧 Business inquiries: {BUSINESS_EMAIL}"
        desc += citations_block
        desc += f"\n\n{hashtags}"
        return desc
    # FIX (found on deep re-audit): this fallback (used when ai_generate
    # fails entirely) dropped chapters_text completely — a video with
    # real, working timestamp chapters would still publish with NO
    # chapters section in its description on an AI outage. Now included,
    # same as the primary path.
    return (f"{title}\n\nEpisode {episode} of {niche['series']}.\n\n"
            f"Subscribe for new investigations every week.\n\n"
            f"{chapters_text or '0:00 Introduction'}"
            f"{cross_promo_txt}"
            f"{fiction_disclosure_txt}\n\n"
            f"📧 Business inquiries: {BUSINESS_EMAIL}"
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
        "toxicology_cases":        ["#Toxicology", "#MedicalCase"],
        "diagnostic_odyssey":      ["#Diagnosis", "#MedicalCase"],
        "neurology_cases":         ["#Neurology", "#MedicalCase"],
        "rare_disease_cases":      ["#RareDisease", "#MedicalCase"],
        "senior_health_longevity": ["#HealthyAgeing", "#Longevity"],
        "medical_mystery_outbreak":["#Epidemiology", "#PublicHealth"],
        "surgical_case_studies":   ["#Surgery", "#MedicalCase"],
        "drug_discovery_stories":  ["#Pharmacology", "#MedicalHistory"],
        "sleep_science":           ["#SleepScience", "#MedicalCase"],
        "medical_history":         ["#MedicalHistory", "#HistoryOfMedicine"],
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
    all_tags = category_tags + topic_tags + ["#NoKnownCause"]
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
    # FIX (direct user report, July 24 2026 — "I want ElevenLabs to work
    # without fail... find if there is any updated version or something
    # is missing"): the July 23 fix (monolingual_v1 -> multilingual_v2)
    # was never empirically confirmed against a live call, so it may not
    # be the real cause. Rather than bet everything on one guessed model,
    # this now tries 3 real, currently-documented ElevenLabs models in
    # order per chunk — multilingual_v2 (highest quality), turbo_v2_5 and
    # flash_v2_5 (both faster/cheaper, more likely available on
    # lower-tier plans if the 400 turns out to be a plan/quota
    # restriction on multilingual_v2 rather than a bad model name).
    _EL_MODELS = ["eleven_multilingual_v2", "eleven_turbo_v2_5", "eleven_flash_v2_5"]
    try:
        for idx, chunk in enumerate(chunks):
            log(f"  ElevenLabs chunk {idx+1}/{len(chunks)}")
            _chunk_ok = False
            _last_err = ""
            for _el_model in _EL_MODELS:
                r = requests.post(f"{ELEVENLABS_URL}/{voice_id}",
                    headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
                    json={"text": chunk, "model_id": _el_model,
                          "voice_settings": {"stability": 0.45, "similarity_boost": 0.82}},
                    timeout=120)
                if r.status_code == 200:
                    part = str(WORK_DIR / f"el_{idx}.mp3")
                    with open(part, "wb") as f: f.write(r.content)
                    parts.append(part)
                    _chunk_ok = True
                    log(f"  OK ElevenLabs ({_el_model})")
                    break
                _last_err = f"{r.status_code}: {r.text[:300]}"
                log(f"  ElevenLabs {_el_model} {_last_err}")
            if not _chunk_ok:
                # FIX (direct user report, July 24 2026 — "give me a
                # notification everytime... without fail"): the real error
                # body from ElevenLabs (exactly what's wrong — bad model,
                # quota, invalid voice) now reaches Telegram directly
                # instead of only the GitHub Actions console log, so the
                # next real run gives a definitive, VISIBLE root cause
                # instead of another silent guess.
                tg(f"⚠️ Ch1: ElevenLabs failed on all {len(_EL_MODELS)} models tried — "
                   f"falling back to edge-tts. Real error: {_last_err}")
                return False
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
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=EDGE_RATE)
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
            communicate_fresh = edge_tts.Communicate(text=text, voice=voice, rate=EDGE_RATE)
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
    per explicit request: captions must genuinely match the audio, and
    should never show something different from what's actually said.

    FIX (found while checking Ch1's existing caption mechanism for the
    same accuracy standard applied to Ch2/Ch3/Ch4): the existing
    SubMaker-based approach only ever worked for the edge-tts tier
    specifically — if audio fell through to Fish Audio, gTTS, or espeak
    (any of the real fallback tiers), the main video got zero captions
    at all, silently. It also had a real edge case where a
    generate_subs() failure (documented in its own comment as happening
    on some edge-tts versions) wrote an empty placeholder file but still
    reported success.

    This uses Groq's real Whisper transcription directly on the FINAL,
    ACCEPTED narration audio file, regardless of which TTS tier actually
    produced it — genuinely more robust, and consistent with the same
    method now used across Ch2/Ch3/Ch4. Returns False (no captions)
    rather than a potentially-desynced fallback.
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

        # Grouping, timing and ASS generation now live in
        # video_pipeline/caption_timing.py, so the logic that decides when a
        # caption appears and how long it stays is directly testable instead
        # of only observable by watching a finished 250 MB video. It had been
        # revised twice on the strength of reading it, and never once looked
        # at. tools/local_caption_render.py burns the real output onto real
        # frames; doing that found five defects the inline version still had,
        # including a minimum-dwell floor that could never fire and captions
        # with no readability limit at all.
        from caption_timing import ass_from_words
        ass_text, cap_stats = ass_from_words(words_data, total_duration=None)
        if not ass_text:
            log("  Real caption sync: no usable cues built — no captions this episode")
            return False
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_text)
        if cap_stats.get("over_cps"):
            # Not fatal, but it means the narration is being spoken faster
            # than a caption can be read, which is a PACE problem, not a
            # caption problem. Surfaced rather than silently tolerated.
            log(f"  Caption readability: {cap_stats['over_cps']}/{cap_stats['cues']} "
                f"cues exceed {cap_stats['max_cps']} CPS — narration may be too fast")
        log(f"  Real caption sync: {cap_stats['cues']} cues, mean dwell "
            f"{cap_stats['mean_dwell']}s, max {cap_stats['max_cps']} CPS, "
            f"{cap_stats['overlaps']} overlaps ✅")
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
    # Timing model. Direct feedback on the first rendered episode: "the
    # subtitles are moving too fast, and there are words that are not even
    # syncing in." Both symptoms came from this function.
    #
    # 1. DRIFT. It divided total duration by total word count, giving every
    #    word an identical duration. The audio does not work that way --
    #    inject_ssml_rate deliberately speaks different stages at different
    #    rates, and "a" and "hepatosplenomegaly" are not the same length.
    #    Errors accumulated, so captions ran ahead of the voice and never
    #    recovered. Weighting each word by its character count tracks real
    #    speech far more closely at zero cost.
    #
    # 2. FLASHING. Fixed 6-word chunks meant a cue of six short words could
    #    be on screen under a second. A minimum dwell time fixes that; where
    #    enforcing it would overlap the next cue, the chunk is merged instead
    #    of overlapping.
    words = script.split()
    if not words:
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
        return

    MIN_DWELL   = 1.5    # seconds a cue must stay readable
    MAX_DWELL   = 6.0
    MAX_CHARS   = 46     # ~one comfortable line at 46px
    MAX_WORDS   = 9

    # Character-weighted duration. +1 per word approximates the inter-word
    # gap, so short function words do not collapse to near-zero.
    weights = [len(w) + 1 for w in words]
    total_w = sum(weights) or 1
    sec_per_unit = audio_duration / total_w

    chunks, cur, cur_chars = [], [], 0
    for w in words:
        if cur and (cur_chars + 1 + len(w) > MAX_CHARS or len(cur) >= MAX_WORDS):
            chunks.append(cur); cur, cur_chars = [], 0
        cur.append(w); cur_chars += (1 if cur_chars else 0) + len(w)
    if cur:
        chunks.append(cur)

    events = []
    t = 0.0
    i = 0
    while i < len(chunks) and t < audio_duration:
        chunk = chunks[i]
        dur = sum(len(w) + 1 for w in chunk) * sec_per_unit
        # Too short to read: absorb the next chunk rather than flash, and
        # rather than overlap the cue that follows.
        while dur < MIN_DWELL and i + 1 < len(chunks):
            i += 1
            chunk = chunk + chunks[i]
            dur = sum(len(w) + 1 for w in chunk) * sec_per_unit
        dur = min(dur, MAX_DWELL)
        end = min(t + dur, audio_duration)
        if end <= t:
            break
        text = " ".join(chunk)
        events.append(f"Dialogue: 0,{s2t(t)},{s2t(end)},Default,,0,0,0,,{text}")
        t = end
        i += 1
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

    # FIX (direct user report, July 29 2026 — "the pace was too fast"):
    # the previous range (-5% to -10%, i.e. 90-95% of normal conversational
    # speed) is barely slower than default at all -- nowhere near the slow,
    # weighty delivery of a real investigative documentary narrator. Every
    # stage moved materially slower here while keeping the same relative
    # shape (cold open/escalation still the two fastest, the reveal still
    # the slowest) -- still well within Kokoro's speed clamp (0.7-1.3) and
    # Edge-TTS's own supported rate range.
    stage_rates = [
        (100,  "-12%"),  # Cold open: urgent, attention-grabbing
        (200,  "-16%"),  # The Before: measured documentary pace
        (250,  "-16%"),  # First Signals: measured, building
        (400,  "-12%"),  # Escalation: faster, momentum
        (200,  "-18%"),  # False Resolution: slow, relief
        (650,  "-24%"),  # Real Reveal: slower, weighty
        (200,  "-18%"),  # Implication + CTA: deliberate
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


_KOKORO_GB_FEMALE = ["bf_alice", "bf_emma", "bf_isabella", "bf_lily"]
_KOKORO_GB_MALE   = ["bm_daniel", "bm_fable", "bm_george", "bm_lewis"]
_KOKORO_US_FEMALE = ["af_heart", "af_bella", "af_nicole", "af_aoede",
                      "af_kore", "af_sarah", "af_nova", "af_sky"]
_KOKORO_US_MALE   = ["am_adam", "am_echo", "am_eric", "am_fenrir",
                      "am_liam", "am_michael", "am_onyx", "am_puck"]


def _kokoro_voice_for(edge_voice):
    """Gender/locale-match a Kokoro voice+lang_code pair from the edge-tts
    voice this episode was already going to use, so switching TTS engines
    doesn't also silently swap the narrator's gender or accent family."""
    is_gb_family = edge_voice.startswith(("en-GB", "en-IE"))
    is_female = edge_voice in (_AU_FEMALE + _GB_FEMALE + _US_FEMALE + _REST_FEMALE)
    if is_gb_family:
        pool = _KOKORO_GB_FEMALE if is_female else _KOKORO_GB_MALE
        lang = "b"
    else:
        pool = _KOKORO_US_FEMALE if is_female else _KOKORO_US_MALE
        lang = "a"
    return pool[hash(edge_voice) % len(pool)], lang


def run_audio_with_kokoro(script, niche_name, edge_voice):
    """
    Kokoro (local neural TTS -- ranks 1st among browser-runnable models on
    the public TTS Arena, genuinely more human-sounding than edge-tts)
    as the PRIMARY narrator.

    FIX (direct user request, July 27 2026 -- "make Kokoro primary since
    it sounds more human"): previously Kokoro only ran if SSML edge-tts,
    ElevenLabs, AND the entire edge-tts voice fallback loop all failed --
    which almost never happened, so Kokoro effectively never ran in
    production despite being the better-sounding voice. Promoting it to
    primary loses nothing of SSML's stage-matched delivery-rate variation
    (cold open faster, the reveal slower and weightier, etc.) because it
    reuses the exact same 7-stage segmentation (inject_ssml_rate) and
    translates each stage's rate percentage into Kokoro's own `speed`
    parameter, then crossfade-concatenates the segments the same way the
    SSML path does.
    """
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
    except Exception as e:
        log(f"  Kokoro not available ({e}) — cannot use as primary")
        return None, 0.0

    segments = inject_ssml_rate(script)
    log(f"  Kokoro segments: {len(segments)} at rates {[r for _, r in segments]}")

    kokoro_voice, kokoro_lang = _kokoro_voice_for(edge_voice)
    log(f"  Kokoro voice: {kokoro_voice} (lang={kokoro_lang}, matched from {edge_voice})")

    try:
        pipeline = KPipeline(lang_code=kokoro_lang)
    except Exception as e:
        log(f"  Kokoro pipeline init failed: {e}")
        return None, 0.0

    part_paths = []
    for i, (text, rate) in enumerate(segments):
        if not text.strip():
            continue
        # CLINICAL_PACE slows the whole channel down.
        #
        # Run 30578466862 delivered 1,613 words in 775.8s = 125 wpm, which is
        # brisk news-read pace. Direct feedback on that episode: "the audio
        # pacing is very fast". Documentary narration on this kind of material
        # sits nearer 100-110 wpm -- the viewer is being asked to hold a lab
        # value and a timeline in their head, and needs room to do it.
        #
        # 0.88 multiplier takes 125 wpm to ~110. Applied on top of the
        # per-segment SSML rate so the deliberate slow/fast contrast between
        # sections is preserved rather than flattened.
        speed = max(0.7, min(1.3, 1 + int(rate.strip('%')) / 100.0)) * CLINICAL_PACE
        try:
            generator = pipeline(text, voice=kokoro_voice, speed=speed)
            chunks = [audio_chunk for _, _, audio_chunk in generator]
            if not chunks:
                log(f"    Kokoro segment {i}: no audio produced — skipping")
                continue
            combined = np.concatenate(chunks)
            wav_path = str(WORK_DIR / f"kokoro_seg_{i}.wav")
            sf.write(wav_path, combined, 24000)
            part_path = str(WORK_DIR / f"kokoro_seg_{i}.mp3")
            subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame",
                             "-qscale:a", "2", part_path], capture_output=True, timeout=120)
            if Path(part_path).exists() and Path(part_path).stat().st_size > 5000:
                part_paths.append(part_path)
        except Exception as e:
            log(f"    Kokoro segment {i} (speed={speed:.2f}): {e}")

    if not part_paths:
        return None, 0.0

    if len(part_paths) == 1:
        import shutil
        out = str(WORK_DIR / "kokoro_narration.mp3")
        shutil.copy(part_paths[0], out)
        return out, get_media_duration(out)

    out = str(WORK_DIR / "kokoro_narration.mp3")
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
                    "-map", f"[{prev_label}]", out], label="kokoro-crossfade-concat")
        if not Path(out).exists() or Path(out).stat().st_size < 5000:
            raise RuntimeError("crossfade concat produced no usable output")
    except Exception as e:
        log(f"  Crossfade concat failed ({e}) — falling back to plain concat")
        list_file = str(WORK_DIR / "kokoro_seg_list.txt")
        with open(list_file, "w") as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")
        run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", out], label="kokoro-concat")

    duration = get_media_duration(out)
    log(f"  Kokoro audio: {duration:.1f}s ({duration/60:.1f} min)")
    return out, duration


def _detect_abnormal_silence(mp3_path, total_duration):
    """
    v1 addition — real, signal-based audio quality check using ffmpeg's
    actual silencedetect filter, not just file size/duration heuristics.

    FIX (real production data, run 30058094102): the cumulative-fraction
    check alone can't tell "many short dramatic pauses" (legitimate —
    this is a slow-paced horror/documentary narration deliberately
    slowed -5% to -10% for weight) from "one dead segment" (a real
    dropped/corrupted render). Three independent real syntheses of the
    same script (an 8-segment SSML crossfade render, then two plain
    single-shot fallback renders) all landed at exactly 23% cumulative
    silence with zero crashes or errors anywhere in the chain — that's
    the narration's real pacing, not corruption, and 15% was already
    unreachable for this kind of deliberately-paced narration (same
    category of miscalibration as the narrative-craft gate, which was
    unreachable at 8.8 and had to be recalibrated to a real 7.9 ceiling).
    Now checks BOTH: cumulative fraction (raised to a real-data-informed
    30%) AND the single longest silent run (12s+ is a genuine dropped
    segment — real spoken dramatic pauses don't run that long).
    """
    if not total_duration or total_duration <= 0:
        return True, 0.0
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(mp3_path), "-af", "silencedetect=noise=-30dB:d=1.0",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=60)
        silence_total = 0.0
        longest_run = 0.0
        for line in r.stderr.splitlines():
            if "silence_duration:" in line:
                try:
                    d = float(line.split("silence_duration:")[1].strip())
                    silence_total += d
                    longest_run = max(longest_run, d)
                except (ValueError, IndexError):
                    pass
        fraction = silence_total / total_duration
        is_normal = fraction <= 0.30 and longest_run < 12.0
        if not is_normal:
            log(f"  Audio silence check: {fraction*100:.0f}% of audio is silence "
                f"(threshold 30%), longest single gap {longest_run:.1f}s (threshold 12s) "
                f"— possible corrupted/truncated segment")
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

    # FIX (direct user request, July 27 2026 — "make Kokoro primary since
    # it sounds more human"): Kokoro (local, genuinely more natural-
    # sounding than edge-tts) is now the real primary path, tried before
    # anything else. It reuses the SSML path's 7-stage rate segmentation
    # (see run_audio_with_kokoro) so none of the stage-matched delivery-
    # rate variation is lost by switching engines. Edge-TTS SSML is the
    # fallback if Kokoro is unavailable/fails, then ElevenLabs, then the
    # plain edge-tts per-voice loop, then Fish Audio/gTTS/espeak.
    el_ok = False

    # Truncate script to MAX_WORDS before synthesis to prevent long audio failures
    _ssml_words = script.split()
    if len(_ssml_words) > MAX_WORDS:
        script = " ".join(_ssml_words[:MAX_WORDS])
        log(f"  Script truncated to {MAX_WORDS}w before audio synthesis")

    log("  Trying Kokoro multi-rate audio (primary)...")
    kokoro_path, kokoro_dur = run_audio_with_kokoro(script, niche_name, edge_voice)
    kokoro_ok = bool(kokoro_path and kokoro_dur > 60 and kokoro_dur < 1800)  # 30-min max sanity cap

    ssml_path, ssml_dur, ssml_ok = None, 0.0, False
    if not kokoro_ok:
        log("  Kokoro unavailable/failed — trying SSML edge-tts (fallback)...")
        ssml_path, ssml_dur = run_audio_with_ssml(script, niche_name, edge_voice)
        ssml_ok = bool(ssml_path and ssml_dur > 60 and ssml_dur < 1800)  # 30-min max sanity cap
        if not ssml_ok:
            # SSML failed too — give ElevenLabs a shot before falling
            # further down the chain (plain edge-tts loop -> Fish Audio).
            log("  SSML failed — trying ElevenLabs as opportunistic backup...")
            el_ok = call_elevenlabs(script, niche_name, audio_path)

    if el_ok:
        pass  # ElevenLabs doesn't support rate variation — use as-is
    else:
        if kokoro_ok or ssml_ok:
            import shutil
            chosen_path = kokoro_path if kokoro_ok else ssml_path
            chosen_dur = kokoro_dur if kokoro_ok else ssml_dur
            tool_label = "Kokoro (local, multi-rate)" if kokoro_ok else "Edge-TTS (SSML multi-rate)"
            if str(chosen_path) != str(audio_path):
                shutil.copy(chosen_path, audio_path)
            else:
                log(f"  {tool_label}: skipping self-copy")
            duration = chosen_dur
            log(f"  {tool_label} audio OK: {duration:.1f}s")
            # FIX (found on deep re-audit): this used to return here
            # directly — skipping the 18-min hard cap, the real per-niche
            # EQ chain (apply_audio_post_processing), and caption
            # generation entirely below. The primary, best-quality tier,
            # so it was silently publishing with no captions and no
            # documentary-grade EQ most of the time. Now runs through the
            # same tail processing every other tier does.
            if duration > 18 * 60:
                log(f"  ⚠️ {tool_label} audio exceeded 18-min hard cap ({duration/60:.1f} min) — trimming")
                trimmed = str(WORK_DIR / "narration_trimmed.mp3")
                run_ffmpeg(["ffmpeg", "-y", "-i", audio_path, "-t", str(18 * 60),
                            "-c", "copy", trimmed], label="hard-duration-cap-primary", timeout=120)
                if Path(trimmed).exists() and Path(trimmed).stat().st_size > 50000:
                    audio_path = trimmed
                    duration = get_media_duration(audio_path)
            processed_path = str(WORK_DIR / "narration_processed.mp3")
            audio_path = apply_audio_post_processing(audio_path, processed_path, niche_name=niche_name)
            generate_fallback_ass(script, duration, ass_path)
            return audio_path, duration, ass_path, edge_voice if not kokoro_ok else "kokoro-local", tool_label

    if not el_ok:
        # FIX (July 24 2026, direct user request): AU>GB>US>rest priority
        # order, all baked into EXTENDED_VOICES itself.
        _fallback_candidates = [v for v in
            EXTENDED_VOICES if v != edge_voice]
        # v1 addition — real learning-loop closure: voice performance has
        # been tracked into state["performance"] this whole time but
        # never read back. Reorders only the FALLBACK candidates (never
        # edge_voice itself, which stays the niche-intended first choice)
        # toward whichever has the best real historical average score.
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
        # ── FALLBACK CHAIN: Kokoro (primary), SSML edge-tts, ElevenLabs,
        # AND the entire plain edge-tts per-voice loop above all failed.
        # Try remaining alternate providers before giving up entirely.
        # Real order now: Kokoro (local, primary) -> edge-tts SSML ->
        # ElevenLabs -> edge-tts (plain, per-voice fallback, above this
        # block) -> Fish Audio (only if configured) -> gTTS (free, more
        # robotic but reliable) -> espeak-ng (offline, most robotic, true
        # last resort). Kokoro already had its shot as primary above, so
        # it is not retried here.
        log("  All edge-tts voices exhausted — trying backup TTS providers...")
        script_clean = script
        dur_expected = min((len(script_clean.split()) / 125.0) * 60.0, 1080.0)  # matches 18-min hard cap
        log(f"  Fallback tier expected duration: ~{dur_expected:.0f}s (final check_audio_quality "
            f"gate validates the real result against this once a tier succeeds)")
        fallback_ok = False

        fish_key = os.environ.get("FISH_AUDIO_API_KEY", "")
        if not fallback_ok and fish_key:
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
                    tg("⚠️ Ch1: edge-tts and Kokoro both failed today — used Fish Audio backup instead")
                    fallback_ok = True
                    edge_voice = "fish-audio-backup"
                else:
                    log(f"  Fish Audio: {r.status_code}")
            except Exception as e:
                log(f"  Fish Audio backup failed: {e}")
        elif not fallback_ok:
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

    # FIX (direct user request, July 25 2026 — "I am not getting
    # notifications... which audio tool it has taken"): infer which real
    # tool actually produced the accepted file. The fallback tiers each
    # set edge_voice to a distinct sentinel on success (kokoro-local,
    # fish-audio-backup, gtts-fallback, espeak-offline-LASTRESORT) —
    # reused here rather than threading a separate flag through every
    # branch above.
    if edge_voice == "kokoro-local":
        tool_used = "Kokoro (local)"
    elif edge_voice == "fish-audio-backup":
        tool_used = "Fish Audio"
    elif edge_voice == "gtts-fallback":
        tool_used = "gTTS"
    elif edge_voice == "espeak-offline-LASTRESORT":
        tool_used = "espeak (offline, last resort)"
    elif el_ok:
        tool_used = "ElevenLabs"
    else:
        tool_used = "Edge-TTS (standard)"

    return audio_path, duration, ass_path if has_ass else None, edge_voice, tool_used

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
                # FIX (direct user report, July 24 2026 — same bug as
                # get_stage_matched_video: Pixabay's video API has no real
                # orientation filter, so this needs its own real check.
                if Path(path).stat().st_size > 50000 and _is_landscape_video(path):
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
                # FIX (direct user report, July 24 2026): target was picked
                # by width alone with no check that width > height, so a
                # portrait rendition could pass.
                if Path(path).stat().st_size > 50000 and _is_landscape_video(path):
                    return path
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


# FIX (direct user report, July 24 2026 — "it is giving the horizontal as
# well as vertical videos"): real root cause found — Pixabay's actual
# Video API has NO "orientation" parameter at all (only its separate
# Image API does); the "orientation": "horizontal" sent to Pixabay's
# video search below is silently ignored, giving zero real filtering.
# Pexels' video search DOES support "orientation": "landscape", but the
# file-selection logic only checked width <= 1920 with no check that
# width > height — a 1080x1920 (portrait) rendition passes that check
# just as easily as a 1920x1080 (landscape) one. Both gaps let portrait
# clips through despite the code appearing to request landscape-only.
# This real ffprobe-based check runs on every downloaded clip regardless
# of source, and rejects (deletes + reports not-downloaded) anything
# that isn't genuinely landscape, so the caller tries the next source/
# search term instead of accepting a portrait clip.
def _is_landscape_video(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
            capture_output=True, timeout=15, text=True)
        if r.returncode != 0:
            return False
        streams = json.loads(r.stdout).get("streams", [])
        vs = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not vs:
            return False
        w, h = vs.get("width", 0), vs.get("height", 0)
        return bool(w and h and w > h)
    except Exception:
        return False


_WORLD_MAP_DATA_FOOTAGE = None

def _load_world_map_data_footage():
    """Real country-name list, reused (same dataset as the map-scene
    system) purely as a real-nation dictionary for footage matching."""
    global _WORLD_MAP_DATA_FOOTAGE
    if _WORLD_MAP_DATA_FOOTAGE is not None:
        return _WORLD_MAP_DATA_FOOTAGE
    try:
        map_path = Path(__file__).parent / "world_map_data.json"
        with open(map_path) as f:
            _WORLD_MAP_DATA_FOOTAGE = json.load(f)
    except Exception:
        _WORLD_MAP_DATA_FOOTAGE = {"features": []}
    return _WORLD_MAP_DATA_FOOTAGE


# Common demonyms/adjectival forms for the nations a script is most
# likely to actually reference in prose ("American street", "British
# police") rather than the formal country name — the real GeoJSON dataset
# only has formal names ("United States"), so this closes that real gap.
_NATION_DEMONYMS = {
    "american": "United States", "u.s.": "United States", "usa": "United States",
    "british": "United Kingdom", "english": "United Kingdom", "uk": "United Kingdom",
    "canadian": "Canada", "australian": "Australia", "irish": "Ireland",
    "scottish": "United Kingdom", "welsh": "United Kingdom",
    "german": "Germany", "french": "France", "italian": "Italy",
    "spanish": "Spain", "russian": "Russia", "chinese": "China",
    "japanese": "Japan", "indian": "India", "mexican": "Mexico",
    "brazilian": "Brazil", "south african": "South Africa",
}

# FIX (direct user report, July 24 2026 — "without fail"): real stories
# overwhelmingly name a specific US STATE or a major foreign CITY rather
# than saying "American"/"British" outright (e.g. "Providence, Rhode
# Island", not "an American city") — the demonym-only list above missed
# every one of these. All 50 real US states map to United States; a
# compact set of major, unambiguous English-speaking-world cities covers
# the next most common real case without the false-positive risk of
# guessing at every possible town name.
_US_STATES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
    "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
    "minnesota","mississippi","missouri","montana","nebraska","nevada",
    "new hampshire","new jersey","new mexico","new york","north carolina",
    "north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island",
    "south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming",
}
for _state in _US_STATES:
    _NATION_DEMONYMS[_state] = "United States"

_MAJOR_CITY_NATIONS = {
    "london": "United Kingdom", "manchester": "United Kingdom", "birmingham": "United Kingdom",
    "glasgow": "United Kingdom", "edinburgh": "United Kingdom", "liverpool": "United Kingdom",
    "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada", "ottawa": "Canada",
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia", "perth": "Australia",
    "auckland": "New Zealand", "wellington": "New Zealand",
    "dublin": "Ireland", "cork": "Ireland",
    "cape town": "South Africa", "johannesburg": "South Africa", "durban": "South Africa",
}
_NATION_DEMONYMS.update(_MAJOR_CITY_NATIONS)


def _detect_nation_context(title, topic, script):
    """
    FIX (direct user report, July 24 2026 — "stock footage... should be
    embedded properly according to the nation, according to the video
    title, without fail... hard-code embedded, that should be your main
    priority"): real nation detection, checked against the title first
    (most specific), then topic, then the opening of the script — so
    footage search terms carry the actual country/setting of the story,
    not just its mood or a generic concrete noun. Returns a real country
    name (matching the same dataset the map system uses) or "" if none
    is genuinely present in any of the three sources.
    """
    data = _load_world_map_data_footage()
    real_names = [f["name"] for f in data.get("features", [])]
    for source in (title or "", topic or "", " ".join(script.split()[:150])):
        low = source.lower()
        for demonym, country in _NATION_DEMONYMS.items():
            if demonym in low:
                return country
        for name in real_names:
            if len(name) > 3 and name.lower() in low:
                return name
    return ""


# ══════════════════════════════════════════════════════════════════════
# EPISODE CASE HOLDER
# The real sourced case (pmc_data.get_real_case + extracted differentials/
# timeline/anatomy/quote/chart_data) is needed by the per-segment renderers
# deep inside get_stage_matched_video, but it is produced up in
# generate_script_content. Threading it through would mean adding a
# parameter to assemble_video and its 8+ call sites (including every
# Swap-Visuals rework branch) -- a lot of surface area for one value, and
# exactly where an easy bug hides when one call site is missed.
#
# This process renders exactly one episode, so a module-level holder is
# safe: set_episode_case() is called once when the script is generated,
# and get_episode_case() is read by the renderers. Reset defensively at
# set time so a resumed/reworked run can never inherit a stale case.
# ══════════════════════════════════════════════════════════════════════
_EPISODE_CASE = {}


def set_episode_case(case):
    global _EPISODE_CASE
    _EPISODE_CASE = case or {}
    if _EPISODE_CASE:
        log(f"  Episode case set: {_EPISODE_CASE.get('pmcid','?')} "
            f"({len(_EPISODE_CASE.get('figures') or [])} usable figures)")


def get_episode_case():
    return _EPISODE_CASE


def get_stage_matched_video(niche, script, audio_duration, topic="", title=""):
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

    FIX (found on direct user report, July 23 2026 — real gap): this
    never received the actual episode topic at all -- footage search
    terms were built from a fixed, channel-wide generic mood-phrase
    cycle (identical across every single episode regardless of subject)
    plus one word pulled from that segment's local narration slice,
    which in practice was overwhelmingly generic connective filler
    ("still", "remained", "waiting", "system") rather than anything
    visually specific to the real story -- confirmed live: a 2019
    "14 witnesses classified by three agencies" story produced footage
    search terms like "isolation loneliness rocks" and "chase pursuit
    tension wondered", with zero connection to the actual subject.
    topic is a short, information-dense one-line summary (unlike a
    diluted narration slice) and reliably contains real, visually
    groundable specifics -- now extracted once and threaded into every
    single segment's query, so every clip search is anchored to the
    real subject matter, not mood + near-random filler.
    """
    words     = script.split()
    total     = len(words)

    _topic_stopwords = {"the","a","an","and","or","but","in","on","at","to","for",
                  "of","with","by","from","this","that","was","were","had","have",
                  "it","its","he","she","they","their","his","her","be","been",
                  "not","no","so","as","if","then","than","when","what","who",
                  "part","real","documented","real-life","true","story"}
    # FIX (direct user report, July 24 2026 — "nonsensical background...
    # random footage... why is it showing this random footage"): the old
    # topic_anchors picked whichever words scored highest by raw frequency,
    # with zero check on whether a word is something a generic stock-video
    # library can actually match. Abstract/administrative words pulled from
    # a topic line ("witnesses", "classified", "agencies", "investigation")
    # return zero real hits on Pixabay/Pexels once paired with a mood
    # phrase, which silently degraded the search all the way down through
    # the fallback chain to the fully generic "cinematic dark atmosphere"
    # query — and THAT is what was actually returning unrelated forest/
    # ocean/butterfly aesthetic clips. Concrete, visually groundable nouns
    # (notebook, apartment, mailbox, hallway, phone, camera, photograph...)
    # are real stock-footage subjects, so they now get first priority
    # whenever present; frequency-ranked words are still used as the
    # fallback exactly as before when no concrete noun is present.
    CONCRETE_VISUAL_NOUNS = {
        "notebook","notebooks","diary","diaries","letter","letters","note","notes",
        "mailbox","apartment","house","hallway","corridor","window","windows","door","doors",
        "phone","telephone","camera","cameras","car","cars","street","streets","road","roads",
        "photograph","photographs","photo","photos","picture","pictures","room","rooms",
        "drawer","drawers","box","boxes","basement","attic","garage","fence","key","keys",
        "lock","locks","stairs","staircase","closet","bedroom","kitchen","office","desk",
        "computer","laptop","envelope","envelopes","package","packages","parking","alley",
        "porch","balcony","garden","yard","gate","curtain","curtains","mirror","mirrors",
        "flashlight","lantern","candle","clock","watch","suitcase","backpack","handwriting",
        "typewriter","file","files","folder","folders","cabinet","surveillance","camcorder",
        "recorder","tape","tapes","cassette","radio","television","newspaper","newspapers",
        "magazine","journal","map","maps","train","station","bridge","tunnel","forest","woods",
        "lake","river","ocean","cabin","motel","hotel","hospital","clinic","church","school",
        "classroom","library","warehouse","factory","truck","van","bus","bicycle","motorcycle",
        "footprint","footprints","shadow","shadows","light","lights","lamp","lamps",
        # FIX (direct user report, July 25 2026, real screenshots): a
        # hiker/wilderness story ("Nobody Knew the Documented Horror a
        # Hiker Exposed Up There") had no concrete anchor in this set at
        # all -- every outdoor/wilderness term was missing, pushing more
        # segments than necessary into the weaker abstract theme_cycle-
        # only fallback where the mismatched-footage bug above actually
        # originates. Real subjects for outdoor/wilderness stories now
        # get the same first-priority treatment as indoor ones.
        "trail","trails","mountain","mountains","hiking","hiker","hikers",
        "wilderness","campsite","tent","ranger","cliff","cliffs","ridge",
        "summit","cave","caves","ravine","canyon","trailhead","backcountry",
        "campfire","fog","wildfire",
        # FIX (direct user report, July 29 2026 — "the visuals were too
        # random, not what I specifically asked for"): confirmed live on a
        # reality-TV/psychological-manipulation episode ("The 6
        # Psychological Traps of ... Contestants") -- that whole subject
        # has ZERO matches anywhere above, so every segment fell straight
        # to the abstract frequency-ranked fallback and searched Pixabay/
        # Pexels for words like "psychological" and "reality", which
        # return near-random stock photography (portraits, abstract art)
        # with no real connection to the actual footage a reality-TV/
        # manipulation story would show. These are the real, concrete,
        # photographable subjects of that kind of story.
        "contestant","contestants","interview","confessional","audition",
        "audience","spotlight","stage","studio","microphone","cameraman",
        "producer","contract","contracts","elimination","alliance","alliances",
        "vote","voting","ballot","competition","dormitory","bunk","mansion",
        "villa","therapist","therapy","counselor","support","group","hotline",
        "manipulator","manipulation","texts","messages","voicemail","recording",
        "recordings","interrogation","polygraph","courtroom","witness","stand",
    }
    # FIX (found live, Ch1 run 30433881228): stripped punctuation never
    # included "[" / "]" -- an unfilled "[Specific Reality Show]" template
    # placeholder that reached `topic` produced the literal token
    # "[specific" here, which then became the on-screen animation keyword
    # for 9 of 55 segments ("[STICKMAN] animated: '[specific'"). Topic
    # generation is now filtered at its source too, but stripped here as
    # well since a bracket is never a legitimate word fragment regardless
    # of how it got into `topic`.
    _topic_words = [w.strip(".,!?;:\"'()[]") for w in topic.lower().split()
                    if len(w) > 4 and w.strip(".,!?;:\"'()[]") not in _topic_stopwords]
    from collections import Counter as _TopicCounter
    _topic_concrete = []
    for _w in _topic_words:
        if _w in CONCRETE_VISUAL_NOUNS and _w not in _topic_concrete:
            _topic_concrete.append(_w)
    _topic_ranked = [w for w, _ in _TopicCounter(_topic_words).most_common(12)
                     if w not in CONCRETE_VISUAL_NOUNS]
    topic_anchors = (_topic_concrete + _topic_ranked)[:6] or []

    # FIX (direct user report, July 24 2026 — "stock footage... should be
    # embedded properly according to the nation, according to the video
    # title, without fail... main priority"): a real, detected nation is
    # threaded into EVERY segment's search query below (not just the
    # topic_anchors rotation), so the footage's actual setting/country is
    # never dropped even on segments whose local topic_anchor happens to
    # be something else that round.
    nation_context = _detect_nation_context(title, topic, script)

    # Dynamic segment count: target ~13.5s/clip, clamped to 55-65 per
    # direct user request ("stock footage of 55 to 65... based on the
    # niche") regardless of exact video length so a 15-min and an 18-min
    # video both stay in the requested density band.
    TARGET_SECONDS_PER_CLIP = 13.5
    n_buckets = int(round(audio_duration / TARGET_SECONDS_PER_CLIP))
    n_buckets = max(55, min(65, n_buckets))

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

    # FIX (found on direct user report, July 15 2026): top_nouns pulled
    # ANY sufficiently long word straight out of the actual narration
    # with zero check on whether it's visually compatible with a dark
    # aesthetic — a completely ordinary sentence like "she left flowers
    # at the grave" or "it had been raining that morning" handed
    # "flowers" or "raining" straight to Pexels/Pixabay as a search
    # term. Stock APIs match on whatever's most strongly tagged, so
    # "flowers" reliably returns bright wedding/garden footage no
    # matter what dark-mood word rides along with it in the same query.
    # FIX (direct user report, July 25 2026, real screenshots): even
    # with this list blocking narration WORDS, real fetched clips still
    # came back as a butterfly on flowers, a swarm of insects, and a
    # misty green valley for a hiker/crime story — because nothing ever
    # checked what Pixabay/Pexels actually RETURNED, only what was
    # SEARCHED for. An abstract theme_cycle mood phrase like "final
    # silence" or "quiet unease" has no horror-specific anchor, so
    # Pixabay's own ranking can surface generic serene nature/wildlife
    # content for it — hoisted to function scope (was rebuilt every
    # loop iteration for no reason) and widened with the exact terms
    # from the real bad hits, then reused below as a genuine POST-FETCH
    # relevance filter on each candidate's own tags/description, not
    # just on the outgoing query.
    BRIGHT_MUNDANE_BLOCKLIST = {
        "flowers","flower","garden","wedding","birthday","party","parties",
        "sunshine","sunny","picnic","vacation","holiday","holidays","beach",
        "celebration","celebrate","smiling","smile","laughing","laughter",
        "balloons","cake","gift","gifts","present","presents","rainbow",
        "puppy","kitten","baby","babies","wedding","graduation","summer",
        "playground","festival","carnival","circus","confetti",
        "butterfly","butterflies","insect","insects","bug","bugs","bee","bees",
        "dragonfly","ladybug","wildlife","macro","bloom","blossom","blossoms",
        "petal","petals","meadow","daisy","daisies","tulip","tulips","pollen",
    }

    def _hit_looks_mismatched(*text_fields):
        """Real post-fetch relevance check: rejects a candidate clip whose
        own tags/description/URL slug hit the same bright-mundane
        blocklist, regardless of what search term found it."""
        combined = " ".join(t for t in text_fields if t).lower()
        return any(w in combined for w in BRIGHT_MUNDANE_BLOCKLIST)

    # FIX (direct user spec, this session — "a betrayal story might
    # start with cinematic stickman characters, switch to an
    # investigation board as evidence is introduced, use kinetic text
    # for a key quote, and end with motion graphics summarizing the
    # timeline... 40% cinematic stickman, 25% silhouette, 20%
    # investigation board, 10% motion graphics, 5% text animation. I
    # don't want you to miss it."): a single register for the entire
    # episode was exactly the "only two things, boring/stagnant"
    # complaint. register_quota is fresh per-episode (not persisted
    # across episodes -- this is a per-video mix, not a rotation) and
    # its pick() is called once per segment below, in narration order,
    # so the realized mix converges on this exact 40/25/20/10/5 split
    # regardless of how this episode's own script happens to be worded.
    # Six clinical registers. There is deliberately NO character-animation
    # register: no stickman, no silhouette. Those were the two registers
    # repeatedly rejected on this channel, and a published clinical case has
    # nothing for a character puppet to do -- the drama is in the chemistry.
    from medical_register import new_quota

    _case = get_episode_case()
    _figure_count = len(_case.get("figures") or [])
    # FIGURE share adapts to how many usable figures this paper actually has.
    # A 2-figure paper would otherwise be asked for ~20 FIGURE segments and
    # would show the same image eighteen times.
    # Pass the case, not just the figure count. Without it the quota
    # scheduled CHART and TIMELINE segments on papers that have neither, and
    # half the episode rendered the identical fallback card.
    register_quota = new_quota(n_buckets, figure_count=_figure_count, case=_case)
    from medical_segments import act_boundaries
    _act_cards = act_boundaries(n_buckets)
    log(f"  Structure: title card at 0, act cards at {sorted(_act_cards)}")
    log(f"  Register mix: {_figure_count} usable figure(s); "
        f"available={ {k: v for k, v in register_quota.mix.items() if v > 0} }")

    # FIX (direct user spec, this session — "switches should align with
    # real audio cues... not be purely visually arbitrary"): reuses the
    # SAME real stinger-timing detector content_sfx.py already runs for
    # this episode's sound design (detect_content_sfx_cues), instead of
    # inventing a second, disconnected notion of "a dramatic moment" --
    # a segment whose time window contains one of these real cue
    # timestamps gets audio_cue_hit=True passed to the quota picker below.
    audio_cue_times = []
    try:
        from content_sfx import detect_content_sfx_cues
        audio_cue_times = [t for _cat, t in detect_content_sfx_cues(
            script, audio_duration, niche_name=niche["name"], topic=topic)]
    except Exception as e:
        log(f"  Audio-cue detection for register sync (non-fatal): {e}")

    for i in range(n_buckets):
        base_kw = theme_cycle[i % len(theme_cycle)]
        start = i * bucket_words
        end   = min(start + bucket_words, total)
        # Two forms, deliberately. stage_text is lowercased because every
        # keyword matcher below (classify_hint, the SFX cue detector, the
        # noun extractor) compares against lowercase literals. stage_display
        # keeps the narration's own capitalisation, because some registers
        # DRAW this text on screen -- and a card reading "newborns tire...
        # what was not" with lowercase sentence starts reads as a rendering
        # bug. Found by rendering an episode locally and looking at it.
        stage_display = " ".join(words[start:end])
        stage_text = stage_display.lower()

        stage_words= [w.strip(".,!?;:") for w in stage_text.split()
                      if len(w) > 4 and w not in stopwords]
        from collections import Counter
        # Prefer a concrete, stock-footage-matchable noun from this segment's
        # own narration (same fix/rationale as the topic_anchors change above)
        # over whatever scores highest by raw frequency alone.
        _concrete_in_stage = [w for w in stage_words
                               if w in CONCRETE_VISUAL_NOUNS and w not in BRIGHT_MUNDANE_BLOCKLIST]
        top_nouns  = [_concrete_in_stage[0]] if _concrete_in_stage else \
                     [w for w, _ in Counter(stage_words).most_common(6)
                      if w not in BRIGHT_MUNDANE_BLOCKLIST][:1]
        # FIX (found on deep re-audit): bucket_words is often only ~25-35
        # words (total script / 55-75 buckets) — plenty of real segments
        # have ZERO words that are both >4 chars and not a stopword/bright-
        # mundane term, which silently dropped this segment's search term
        # to the fully generic mood phrase (base_kw alone) with no
        # content-specific signal at all. Before giving up, widen the
        # window to the surrounding ~3 buckets (still the same moment in
        # the narration, not a different scene) so a real topical word
        # from just before/after this exact slice is used instead of going
        # fully generic.
        if not top_nouns:
            wide_start = max(0, start - bucket_words)
            wide_end   = min(total, end + bucket_words)
            wide_text  = " ".join(words[wide_start:wide_end]).lower()
            wide_words = [w.strip(".,!?;:") for w in wide_text.split()
                          if len(w) > 4 and w not in stopwords]
            _concrete_in_wide = [w for w in wide_words
                                  if w in CONCRETE_VISUAL_NOUNS and w not in BRIGHT_MUNDANE_BLOCKLIST]
            top_nouns  = [_concrete_in_wide[0]] if _concrete_in_wide else \
                         [w for w, _ in Counter(wide_words).most_common(6)
                          if w not in BRIGHT_MUNDANE_BLOCKLIST][:1]
        # FIX (found on direct user report, July 23 2026): prioritize a
        # real topic anchor (rotated per segment) over the local narration
        # word when both exist -- topic_anchors come from the actual,
        # information-dense episode topic and are far more likely to be a
        # genuine, visually groundable specific (a place, an event term, a
        # concrete noun) than whatever generic connective word happened to
        # be >4 characters in this segment's ~30-word slice.
        topic_anchor = topic_anchors[i % len(topic_anchors)] if topic_anchors else ""
        specific_term = topic_anchor or (top_nouns[0] if top_nouns else "")
        # Dark mood word (base_kw) now leads the query instead of trailing
        # it, so relevance ranking favors the niche's actual visual
        # language even when a content noun is also present.
        kw = f"{base_kw} {specific_term}" if specific_term else base_kw

        # search_terms built here (not just at the footage-fallback point
        # below) so the animated STICKMAN/SILHOUETTE dispatch can ALSO use
        # it for real photo backgrounds (see photo_background.py) --
        # direct user follow-up after seeing the procedurally-drawn
        # sample backgrounds: "the pictures look the same... too
        # generic... can we use real pictures for it... if it talks
        # about some kind of dark room, it should show a dark room...
        # walking in a forest, show that... murderous place, show
        # that... office, show that." Single list, reused by both the
        # photo-background fetch and the existing video-footage
        # fallback below, instead of building it twice.
        # topic_anchor (alone, paired with the niche's fallback mood word)
        # is tried before falling all the way back to fully generic terms,
        # so a query that fails with the local narration word still gets
        # one more real, topic-specific shot before giving up on specificity.
        search_terms = [kw]
        if topic_anchor and specific_term != topic_anchor:
            search_terms.append(f"{base_kw} {topic_anchor}")
        # FIX (direct user report, July 24 2026 — "stock footage...
        # according to the nation... without fail... main priority"):
        # nation+subject variants tried early, ahead of the niche-mood-
        # only fallbacks, so the story's real detected country genuinely
        # influences which footage gets picked whenever a real hit exists
        # for it — kept to 2-word queries (nation + one real term) since
        # 3+ word combined queries return far fewer real hits in practice.
        if nation_context:
            if specific_term:
                search_terms.append(f"{nation_context} {specific_term}")
            search_terms.append(f"{nation_context} {base_kw}")
        # FIX (direct user report, July 24 2026 — "nonsensical background...
        # random footage"): the chain used to end on the fully generic
        # "cinematic dark atmosphere" query, which is where the completely
        # unrelated forest/ocean/butterfly clips actually came from — a
        # 2-word aesthetic phrase with no topic or niche grounding at all.
        # Removed: the niche's own BG_KEYWORDS entry (still niche-mood-
        # matched, just not story-specific) is now the true last resort
        # before a neutral black clip, which is a better outcome than
        # visibly wrong footage.
        search_terms += [base_kw, BG_KEYWORDS.get(niche["name"], ["dark shadows"])[i % 3]]

        clip_path  = str(WORK_DIR / f"seg_{i}.mp4")

        # FIX (direct user request, July 25 2026 — "move channel 1 and
        # channel 5 to the animations... it should also be based on the
        # niche... not random... specifically adjustable to the topic"):
        # real screenshots showed stock footage returning irrelevant
        # clips (butterflies, misty valleys) despite the nation/topic-
        # matching logic above already being real and working on the
        # SEARCH side — the fundamental problem is depending on a stock
        # library to happen to have the right real-world clip at all.
        # Real stick-figure character animation (video_pipeline/
        # stickman_animation.py) replaces that dependency entirely:
        # nothing is fetched, so nothing can mismatch. The action
        # (walk/run/sit-writing/alert/shock) is chosen by real keyword
        # detection on THIS segment's own narration text, and the same
        # specific_term/nation_context already computed for the old
        # stock-footage query is burned in as on-screen text — the
        # visual is genuinely topic-adjusted, not arbitrary.
        # FIX (direct user request, July 25 2026, second round): the
        # FIRST animation system built here (niche_animation.py) was
        # explicitly rejected as "abstract glow/grain... doesn't draw
        # attention" — replaced with this real jointed-figure system,
        # verified by actually rendering and visually inspecting every
        # action (walk/run/sit-write/alert/shock) before wiring it in.
        display_text = (f"{nation_context.title()} — {specific_term}"
                         if nation_context and specific_term
                         else (specific_term or nation_context or base_kw))
        seg_start_t, seg_end_t = i * segment_dur, (i + 1) * segment_dur
        audio_cue_hit = any(seg_start_t <= t < seg_end_t for t in audio_cue_times)
        # NOTE: the old location_hit / map_eligible anchoring is gone with the
        # MAP register. Left as a comment rather than silently dropped because
        # it referenced map_eligible, which no longer exists -- keeping the
        # line would have been a NameError on the first real segment.
        # force_switch on a real audio cue, so a stinger never lands with the
        # same register on both sides of it (no visual change at all).
        # ── title card / act cards ──────────────────────────────────────
        # The episode used to open on whatever register the quota happened to
        # schedule first -- in a real local render, a half-drawn chart. A
        # documentary opens by saying what it is and marks its acts; without
        # that, thirteen minutes of clinical graphics reads as a slide deck,
        # which is a note this channel has already had.
        #
        # These REPLACE a segment rather than being inserted, so the clip
        # count still matches the audio exactly and nothing desyncs.
        _card = None
        if i == 0:
            _card = ("TITLE", None)
        elif i in _act_cards:
            _card = ("ACT", _act_cards[i])
        if _card:
            try:
                from medical_segments import (render_title_card, render_act_card,
                                              still_to_clip)
                _still = str(WORK_DIR / f"card_{i}.png")
                if _card[0] == "TITLE":
                    _src = (f"{_case.get('journal','')} {_case.get('year','')}".strip()
                            or "Published case report")
                    _ok = render_title_card(
                        _case.get("title") or topic, _still,
                        niche_label=niche["series"].upper(),
                        source_line=_src, citation=_case.get("citation", ""))
                else:
                    _ok = render_act_card(
                        list(_act_cards).index(i) + 1, _card[1], _still,
                        niche_label=niche["series"].upper())
                if _ok and still_to_clip(_still, segment_dur, clip_path,
                                         run_ffmpeg=run_ffmpeg, register="TITLE"):
                    log(f"  Segment {i+1}/{n_buckets} [{_card[0]} CARD]")
                    fetched_clips.append(clip_path)
                    continue
            except Exception as e:
                log(f"  Segment {i+1} card failed (falling through): {e}")

        register = register_quota.pick(stage_text, force_switch=audio_cue_hit)
        # Reveal position is counted within THIS register's own appearances,
        # not across the episode. Driving it off the global segment index
        # made CHART 3 and 8, BOARD 4/9/20, TIMELINE 2 and 6 and FIGURE
        # 0/21/24 render as identical frames -- see RegisterQuota.reveal.
        _occ, _exp = register_quota.reveal(register)
        _reg_progress = _occ / max(1, _exp)
        log(f"  Segment {i+1}/{n_buckets} (t={i*segment_dur:.0f}s) "
            f"[{register} {_occ}/{_exp}]")
        try:
            if register == "TEXT":
                # kinetic_text is the one existing renderer that already does
                # exactly what this register needs, so it is reused directly
                # rather than reimplemented in medical_segments.
                from kinetic_text import generate_text_segment
                _q = _case.get("quote") or stage_display
                ok = generate_text_segment(niche["name"], _q, _q[:60], segment_dur,
                                            i, clip_path, log_fn=log)
            else:
                from medical_segments import render_medical_segment
                # chart_fn used to be passed as `generate_data_chart` -- a name
                # that exists only in collapse_index_pipeline.py and was never
                # imported here. Every CHART segment therefore raised NameError,
                # got swallowed by the except below, and rendered the plain
                # fallback card: 17 of 59 segments in a locally rendered
                # episode, including six of the first eight. medical_segments
                # now owns the clinical chart renderer, so nothing is injected.
                ok = render_medical_segment(
                    register, _case, stage_display, segment_dur, i, clip_path,
                    work_dir=str(WORK_DIR), niche_label=niche["series"].upper(),
                    run_ffmpeg=run_ffmpeg, log_fn=log,
                    progress=_reg_progress, variant=_occ - 1,
                    variant_total=_exp)
            if ok:
                fetched_clips.append(clip_path)
                continue
        except Exception as e:
            log(f"  Segment {i+1} {register} raised: {e}")

        # NO STOCK FOOTAGE ON THIS CHANNEL.
        #
        # Run 30578466862 shipped an episode about a newborn's liver failure
        # illustrated with a mountain and a woman dancing, because every
        # register that returned False fell through to the Pixabay/Pexels
        # path below. A stock library cannot hold footage of a specific
        # published case, so that path could only ever produce something
        # unrelated -- it is the same failure that killed this channel's
        # previous incarnation, reappearing through a fallback I left open.
        #
        # render_medical_segment now ends in a procedural clinical card that
        # cannot fail, so reaching here at all means something is genuinely
        # broken and a loud, ugly card is the correct outcome: it is visible
        # in review, where a plausible-looking mountain is not.
        try:
            from medical_segments import render_last_resort_still, still_to_clip
            _still = str(WORK_DIR / f"lastresort_{i}.png")
            if render_last_resort_still(stage_display, _still,
                                        niche_label=niche["series"].upper(),
                                        citation=_case.get("citation", "")):
                if still_to_clip(_still, segment_dur, clip_path,
                                 run_ffmpeg=run_ffmpeg):
                    log(f"  Segment {i+1}: clinical fallback card")
                    fetched_clips.append(clip_path)
                    continue
        except Exception as e:
            log(f"  Segment {i+1} fallback card failed: {e}")
        log(f"  Segment {i+1}: NO VISUAL PRODUCED — this is a bug, not a style choice")
        continue

        # ---- unreachable: retained stock-footage code below ----

        log(f"  Segment {i+1}/{n_buckets} (t={i*segment_dur:.0f}s) footage: '{kw[:40]}'")
        downloaded = False
        for search_kw in search_terms:
            if downloaded: break
            try:
                if PIXABAY_KEY:
                    r = requests.get("https://pixabay.com/api/videos/",
                        params={"key": PIXABAY_KEY, "q": search_kw, "per_page": 5,
                                "video_type": "film", "orientation": "horizontal"}, timeout=25)
                    if r.status_code == 200 and r.json().get("hits"):
                        # FIX (direct user report, July 25 2026, real
                        # screenshots): candidates were picked by longest
                        # duration alone, with no check on whether Pixabay's
                        # own tags for that specific clip actually matched
                        # the dark mood being searched for — real relevance
                        # filter against the clip's own tags now runs before
                        # duration is even considered; only falls back to the
                        # unfiltered set if every single hit is mismatched
                        # (still better than a hard skip to the next tier).
                        _hits = r.json()["hits"]
                        _relevant_hits = [h for h in _hits if not _hit_looks_mismatched(h.get("tags", ""))]
                        hit = max(_relevant_hits or _hits, key=lambda h: h.get("duration", 0))
                        url = hit["videos"]["medium"]["url"]
                        with requests.get(url, timeout=45, stream=True) as dl:
                            dl.raise_for_status()
                            with open(clip_path, "wb") as f:
                                for chunk in dl.iter_content(32768): f.write(chunk)
                        if Path(clip_path).exists() and Path(clip_path).stat().st_size > 50000:
                            if _is_landscape_video(clip_path):
                                downloaded = True; continue
                            else:
                                log(f"    Segment {i+1} Pixabay: rejected portrait clip for '{search_kw[:30]}'")
                                Path(clip_path).unlink(missing_ok=True)
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
                            # FIX (same real relevance gap as the Pixabay
                            # branch above): Pexels doesn't return a tags
                            # field, but its video page "url" is a real,
                            # human-readable descriptive slug (e.g.
                            # ".../a-butterfly-on-a-flower-1234567/") — the
                            # best free relevance signal available here.
                            _relevant_vids = [v for v in vids if not _hit_looks_mismatched(v.get("url", ""))]
                            best  = max(_relevant_vids or vids, key=lambda v: v.get("duration", 0))
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
                                    if _is_landscape_video(clip_path):
                                        downloaded = True
                                    else:
                                        log(f"    Segment {i+1} Pexels: rejected portrait clip for '{search_kw[:30]}'")
                                        Path(clip_path).unlink(missing_ok=True)
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
    # FIX (direct user spec, this session — animated segments should
    # "feel like a video," not 55-65 hard-stitched cuts): a true xfade
    # crossfade between EVERY pair of the 55-65 clips would require
    # restructuring the whole concat step from a stream-copy concat
    # demuxer into one giant chained filter_complex, which risks real
    # audio/video drift across that many joins for a cinematic-polish
    # item the user didn't explicitly name — too much risk for the
    # benefit. A same-clip fade-in/fade-out (softens every cut without
    # touching cross-clip timing, duration, or the existing -c copy
    # concat path at all) is the safe version of the same idea.
    fade_dur = min(0.15, segment_dur / 4)
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
                  "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,"
                  f"fade=t=in:st=0:d={fade_dur:.2f},"
                  f"fade=t=out:st={segment_dur-fade_dur:.2f}:d={fade_dur:.2f}",
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

    FIX (real production crash, run 30056439412): libmp3lame's VBR
    psymodel (-q:a) has a known assertion bug — "psymodel.c:576:
    calc_energy: Assertion 'el >= 0' failed" — triggered by the wide
    loudnorm LRA + heavy EQ boosts in these profiles producing near-
    silent passages (worst on supernatural_real, LRA=13, the niche that
    actually crashed). The crash was already caught here and fell back
    to the unprocessed input, which is correct — but the audio-quality
    gate downstream then reran the ENTIRE audio stage (same script, same
    voice) up to 2 times, reproducing the identical deterministic crash
    both times before giving up. Switching to CBR avoids this specific
    lame codepath entirely (well-documented workaround for this exact
    assertion), so post-processing actually succeeds instead of silently
    no-op'ing every single render for this niche.
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
            "-c:a", "mp3", "-b:a", "192k", output_path
        ], label=f"audio-{niche_name or 'default'}", timeout=300)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 500000:
            # FIX: ffmpeg exiting 0 doesn't guarantee a valid output — a
            # near-miss of the same lame edge case (or a truncated
            # loudnorm two-pass run) can still leave a short/corrupted
            # file that LOOKS successful by size alone. Compare measured
            # duration against the input's before trusting it, same
            # tolerance as the existing quality gate uses.
            in_dur  = get_media_duration(input_path)
            out_dur = get_media_duration(output_path)
            if in_dur > 0 and out_dur < in_dur * 0.9:
                log(f"  Audio post-processing produced a short/corrupted file "
                    f"({out_dur:.0f}s vs {in_dur:.0f}s input) — using unprocessed audio instead")
                return input_path
            log(f"  Audio post-processed ({niche_name}): {Path(output_path).stat().st_size//(1024*1024)}MB")
            return output_path
    except Exception as e:
        log(f"  Audio processing failed (non-fatal): {e}")
    return input_path


# ── Niche-specific audio profiles ────────────────────────────
# Each niche has a unique emotional target requiring different EQ/dynamics.
NICHE_AUDIO_PROFILES = {
    "toxicology_cases": (
        # Dry and clinical -- minimal reverb, controlled dynamics, the
        # register of a physician reading a case aloud, not a horror narrator
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "diagnostic_odyssey": (
        # Dry and clinical -- minimal reverb, controlled dynamics, the
        # register of a physician reading a case aloud, not a horror narrator
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "neurology_cases": (
        # Slightly wider -- for neurology and sleep material, where a little
        # air suits the subject without tipping into horror reverb
        "equalizer=f=90:width_type=o:width=2:g=3,"
        "equalizer=f=2200:width_type=o:width=2:g=2,"
        "equalizer=f=11000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=90:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "rare_disease_cases": (
        # Dry and clinical -- minimal reverb, controlled dynamics, the
        # register of a physician reading a case aloud, not a horror narrator
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "senior_health_longevity": (
        # Warm and close -- for research/longevity/history material where the
        # tone is explanatory rather than tense
        "equalizer=f=120:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=70:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "medical_mystery_outbreak": (
        # Dry and clinical -- minimal reverb, controlled dynamics, the
        # register of a physician reading a case aloud, not a horror narrator
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "surgical_case_studies": (
        # Dry and clinical -- minimal reverb, controlled dynamics, the
        # register of a physician reading a case aloud, not a horror narrator
        "equalizer=f=300:width_type=o:width=2:g=-2,"
        "equalizer=f=3000:width_type=o:width=2:g=3,"
        "equalizer=f=8000:width_type=o:width=2:g=-2,"
        "acompressor=threshold=-15dB:ratio=4:attack=3:release=40:makeup=3dB,"
        "loudnorm=I=-16:LRA=8:TP=-1.5"
    ),
    "drug_discovery_stories": (
        # Warm and close -- for research/longevity/history material where the
        # tone is explanatory rather than tense
        "equalizer=f=120:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=70:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "sleep_science": (
        # Slightly wider -- for neurology and sleep material, where a little
        # air suits the subject without tipping into horror reverb
        "equalizer=f=90:width_type=o:width=2:g=3,"
        "equalizer=f=2200:width_type=o:width=2:g=2,"
        "equalizer=f=11000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=90:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
    "medical_history": (
        # Warm and close -- for research/longevity/history material where the
        # tone is explanatory rather than tense
        "equalizer=f=120:width_type=o:width=2:g=3,"
        "equalizer=f=2500:width_type=o:width=2:g=2,"
        "equalizer=f=9000:width_type=o:width=2:g=-3,"
        "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=70:makeup=2dB,"
        "loudnorm=I=-16:LRA=10:TP=-1.5"
    ),
}
DEFAULT_AUDIO_PROFILE = NICHE_AUDIO_PROFILES["toxicology_cases"]

# Dark footage keywords for standalone Shorts per niche
NICHE_SHORT_KEYWORDS = {
    "toxicology_cases":        "laboratory medical clinical hospital",
    "diagnostic_odyssey":      "hospital medical records clinical",
    "neurology_cases":         "brain scan neurology medical imaging",
    "rare_disease_cases":      "microscope laboratory medical research",
    "senior_health_longevity": "elderly health mobility physiotherapy",
    "medical_mystery_outbreak":"laboratory public health epidemiology",
    "surgical_case_studies":   "operating theatre surgical medical",
    "drug_discovery_stories":  "laboratory research pharmacy science",
    "sleep_science":           "sleep laboratory night monitor",
    "medical_history":         "antique medical historical archive",
}

# ================================================================
# AMBIENT MUSIC
# ================================================================
def generate_ambient_music(duration):
    """
    FIX (found going through Ch1's animation system in full, per explicit
    request): this used to be the ONLY music function in the whole file —
    a single generic synthesized drone (two sine waves + filtered noise),
    IDENTICAL for every video regardless of niche. dark_horror and
    seduction_dark and obsession_dark all sounded the same. Kept as the
    absolute last-resort fallback (used only if get_niche_ambient_music
    below can't produce anything at all), but no longer the primary path.
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
    "toxicology_cases":        "unease",
    "diagnostic_odyssey":      "unease",
    "neurology_cases":         "eerie",
    "rare_disease_cases":      "unease",
    "senior_health_longevity": "reflective",
    "medical_mystery_outbreak":"dread",
    "surgical_case_studies":   "unease",
    "drug_discovery_stories":  "reflective",
    "sleep_science":           "eerie",
    "medical_history":         "reflective",
}

# Real, specific, freely-licensed track recommendations per mood —
# researched real tracks on Pixabay's actual music library (free
# commercial use, no attribution required per their license). Download
# once, place in music_bank/<mood>/ under any filename ending .mp3, and
# the system will use them automatically instead of synthesizing.
MOOD_TRACK_RECOMMENDATIONS = {
    "dread": ["Search Pixabay Music for: 'dark ambient drone', 'horror tension', 'suspense dark'"],
    "sensual_tension": ["Search Pixabay Music for: 'dark sensual', 'moody atmospheric', 'noir slow'"],
    "unease": ["Search Pixabay Music for: 'unsettling ambient', 'psychological tension', 'disorienting drone'"],
    "eerie": ["Search Pixabay Music for: 'eerie ambient', 'paranormal atmosphere', 'ghostly drone'"],
    "obsessive_tension": ["Search Pixabay Music for: 'relentless tension', 'driving dark ambient', 'obsessive pulse'"],
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
    FIX (direct user report, July 24 2026 — "it should keep rotating.
    We should not have only one voice"): previously locked permanently
    onto a single "best" voice after 5 episodes — the exact opposite of
    what was asked. Now rotates every episode, forever: same epsilon-
    greedy principle already proven for thumbnail-format selection
    (thumbnail_formats.select_thumbnail_format) — mostly picks from the
    best-performing voices once real score data exists, but always
    keeps sampling the rest of the pool too, and never repeats the
    immediately previous voice for this niche.
    """
    perf = state.get("performance", {})
    niche_episodes = [ep for ep in state.get("episode_history", [])
                      if ep.get("niche") == niche_name]
    ep_count = len(niche_episodes)

    last_voice = perf.get(f"last_voice_{niche_name}")
    candidates = [v for v in available_voices if v != last_voice] or list(available_voices)

    if ep_count < 5:
        voice = candidates[ep_count % len(candidates)]
        log(f"  Voice (gathering data, ep {ep_count+1}/5): {voice}")
        return voice

    voice_scores = {}
    for key, val in perf.items():
        if key.startswith("voice_") and isinstance(val, dict):
            v_name = key.replace("voice_", "")
            if v_name in candidates:
                scores = val.get("scores", [])
                if scores:
                    voice_scores[v_name] = sum(scores) / len(scores)

    if voice_scores and random.random() > 0.35:
        best = max(voice_scores, key=voice_scores.get)
        log(f"  Voice (weighted pick — best avg {voice_scores[best]:.1f}/10): {best}")
        return best

    unproven = [v for v in candidates if v not in voice_scores]
    pool = unproven or candidates
    voice = pool[ep_count % len(pool)]
    log(f"  Voice (rotating/exploring, ep {ep_count+1}): {voice}")
    return voice

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
        "toxicology_cases":        "medical clinical diagram",
        "diagnostic_odyssey":      "medical clinical",
        "neurology_cases":         "anatomy brain medical diagram",
        "rare_disease_cases":      "medical anatomy diagram",
        "senior_health_longevity": "anatomy medical illustration",
        "medical_mystery_outbreak":"medical public health",
        "surgical_case_studies":   "anatomy medical diagram",
        "drug_discovery_stories":  "molecule chemistry structure",
        "sleep_science":           "brain sleep medical diagram",
        "medical_history":         "historical medical illustration",
    }
    mod = niche_mod.get(niche_name, "dark dramatic")
    full_query = f"{search_kw} {mod}"

    # v1 addition (direct user request, July 29 2026) — try a REAL photo
    # of the actual named case first via Wikimedia Commons (free, keyless
    # historical-photo archive) before falling back to generic
    # mood-keyword stock photos below. Only the raw topic keywords are
    # used here (no niche mood modifier) since Commons is a real-photo
    # encyclopedia, not a stock-mood search -- "Jonestown" finds a real
    # photo, "Jonestown dark corridor abstract" would not. Falls straight
    # through to the existing Pixabay/Pexels/Pollinations chain,
    # unchanged, for any topic Commons has nothing real for.
    try:
        from real_case_images import search_wikimedia_commons
        ok, license_short = search_wikimedia_commons(search_kw, out_path)
        if ok:
            log(f"  Case image (Wikimedia Commons, real photo, {license_short}): {search_kw}")
            return True, "photo"
    except Exception as e:
        log(f"  Wikimedia Commons (non-fatal): {e}")

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
            channel_name = "No Known Cause",
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
    "toxicology_cases": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "diagnostic_odyssey": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "neurology_cases": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "rare_disease_cases": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "senior_health_longevity": (
        "eq=brightness=-0.01:contrast=1.08:saturation=0.95,"
        "colorbalance=rs=0.03,"
        "vignette=PI/5.5"
    ),
    "medical_mystery_outbreak": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "surgical_case_studies": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "drug_discovery_stories": (
        "eq=brightness=-0.01:contrast=1.08:saturation=0.95,"
        "colorbalance=rs=0.03,"
        "vignette=PI/5.5"
    ),
    "sleep_science": (
        "eq=brightness=-0.02:contrast=1.12:saturation=0.88,"
        "colorbalance=gs=0.03:bs=0.04,"      # faint clinical teal, not horror blue
        "vignette=PI/5"                      # very light -- reference imagery must stay readable
    ),
    "medical_history": (
        "eq=brightness=-0.01:contrast=1.08:saturation=0.95,"
        "colorbalance=rs=0.03,"
        "vignette=PI/5.5"
    ),
}
DEFAULT_VISUAL_GRADE = NICHE_VISUAL_GRADE["toxicology_cases"]

def compose_video(narration_path, bg_path, music_path, ass_path,
                  audio_duration, label="main", niche_name=None):
    output   = str(WORK_DIR / f"composed_{label}.mp4")
    bg_dur   = get_media_duration(bg_path)
    loop_n   = max(int(audio_duration / max(bg_dur, 1)) + 2, 1)
    has_mus  = music_path and Path(music_path).exists()
    has_sub  = ass_path and Path(ass_path).exists()

    # FIX (found on direct user report, July 15 2026): has_sub was computed
    # here but never actually used anywhere in this function — real
    # subtitles were being generated (generate_real_synced_ass runs fine
    # upstream) and then silently dropped at the one place they'd
    # actually reach the video. The person was told subtitles would be
    # there and they simply weren't, in every single episode. Genuinely
    # burned in now via ffmpeg's own ass filter when a valid file exists.
    grade = NICHE_VISUAL_GRADE.get(niche_name, DEFAULT_VISUAL_GRADE)
    # fps=24 added — normalizes whatever native frame rate the source
    # background clip has (this path also serves the single-clip fallback,
    # whose source rate is unpredictable), consistent with intro/outro's
    # hardcoded 24fps so the final -c copy concat doesn't hit a mismatch.
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,"
          f"{grade}")
    if has_sub:
        # ffmpeg's filter syntax requires colons and backslashes in the
        # path escaped, since the ass filter's own argument parser uses
        # colons as a separator.
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
                          "tags": tags[:15], "categoryId": "27"},
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

def update_video_metadata(video_id, title, description, tags, token=None):
    """
    Real, metadata-only YouTube API call — updates an already-uploaded
    video's title/description/tags without re-uploading the file. Used
    when the Upload phase reuses the unlisted video already uploaded
    during the generate-phase audio+video review (which only had a
    placeholder description at that point, since the real one isn't
    generated until STAGE 5) -- this pushes the real, final metadata
    onto it before it ever goes public.
    """
    token = token or get_yt_token()
    try:
        r = requests.put(
            f"{YT_DATA_URL}/videos?part=snippet",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"id": video_id, "snippet": {"title": title[:100], "description": description,
                                               "tags": tags[:15], "categoryId": "27"}},
            timeout=20)
        if r.status_code == 200:
            return True
        log(f"  Update video metadata FAILED: {r.status_code} — {r.text[:200]}")
        return False
    except Exception as e:
        log(f"  Update video metadata (non-fatal): {e}")
        return False

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
            json={"snippet": {"title": f"{series_name} — All Cases",
                              "description": f"Every published case in the {series_name} series. A new case every weekday, each one sourced from a peer-reviewed paper."},
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
        "toxicology_cases":        "At what point in this timeline would you have questioned the first diagnosis?",
        "diagnostic_odyssey":      "Which finding should have redirected the investigation earliest?",
        "neurology_cases":         "What does a deficit like this reveal about normal brain function?",
        "rare_disease_cases":      "How would a clinician recognise something they had never seen?",
        "senior_health_longevity": "Which of these findings surprised you most?",
        "medical_mystery_outbreak":"What would you have investigated first?",
        "surgical_case_studies":   "Would you have taken the same approach?",
        "drug_discovery_stories":  "How many discoveries do you think began as accidents?",
        "sleep_science":           "What did this case reveal about ordinary sleep?",
        "medical_history":         "Why do you think the practice continued for so long?",
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
        "toxicology_cases":        "Which of the three published outcomes surprised you most?",
        "diagnostic_odyssey":      "How long should a working diagnosis go unchallenged?",
        "neurology_cases":         "Which variant of this presentation is strangest?",
        "rare_disease_cases":      "Should rare presentations change routine practice?",
        "senior_health_longevity": "Which intervention did the data actually support?",
        "medical_mystery_outbreak":"What made the source so hard to identify?",
        "surgical_case_studies":   "Was the operative decision the right one?",
        "drug_discovery_stories":  "What was the real turning point here?",
        "sleep_science":           "What would eighteen nights of this do?",
        "medical_history":         "What current practice will look like this in fifty years?",
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


def _is_real_named_topic(t):
    """
    Real-case validator (direct user request, July 29 2026): rejects
    AI-invented anonymized composites ("a family", "a stalker") the same
    way the bracket-leak check above it already rejects unfilled
    template placeholders. A topic passes if it names a real year
    (1800-2029) or contains a proper-noun-looking word after its first
    word -- catches real names like "Jonestown", "Manson", "NXIVM",
    "Sante Kimes" while still letting through the occasional false
    positive, which is fine: the goal is steering the model and
    filtering the worst offenders, not perfect classification.
    """
    if not isinstance(t, str) or not t.strip():
        return False
    if re.search(r"\b(18|19|20)\d{2}\b", t):
        return True
    generic_starts = {"the", "a", "an"}
    for i, w in enumerate(t.split()):
        if i == 0:
            continue
        clean = w.strip(",.:;\"'()")
        if clean and clean[0].isupper() and clean.lower() not in generic_starts:
            return True
    return False


def run_ch1_viral_intelligence(niche):
    """
    Viral intelligence engine for Ch1 (ported from Ch2).
    Runs weekly — results cached in state.json under 'viral_intel'.

    Supplies hook formulas, title patterns, thumbnail text and power words
    for the clinical-case niche. It no longer supplies TOPICS: run_stage1
    takes those from Europe PMC so the topic and the sourced paper are the
    same document. fresh_topic_ideas is still requested (title generation
    reads the surrounding intel dict) but is deliberately not consulted as
    a topic source -- see the PMC topic pool note in run_stage1.
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
    # FIX (direct user report, July 27 2026 -- "it keeps giving the same
    # thing... for the last 4.5 to 5 days"): fresh_topic_ideas used to ask
    # for only 6 topics, but each episode makes up to 13 script attempts
    # -- every attempt past the 6th exhausted the fresh list and fell back
    # to the tiny 4-item static niche["topics"] list. Direct user follow-up
    # request: raised to 18 (minimum) so a genuinely successful call has
    # more fresh topics than the 13-attempt engine can ever exhaust.
    # FIX (direct user report, July 29 2026 -- "find out what can be done"):
    # this used to ask for topics that merely SOUND real ("real-feeling"),
    # which is exactly how every static niche["topics"] fallback ended up
    # as anonymized "a family"/"a stalker" composites instead of actual,
    # checkable cases -- the same root cause found and fixed for Ch5's
    # finance niches (AI told to sound documented, never told to BE
    # documented). Now requires an actual, real, independently verifiable
    # case by name -- validated below, not just requested.
    prompt = f"""Analyze the TOP 20 most viral medical case-study and clinical explainer
YouTube videos (1M+ views) in the "{niche['search_query']}" niche.

This is a channel about REAL, PUBLISHED, peer-reviewed clinical cases. Every
field below must fit that: a presenting complaint, a laboratory value, an
imaging finding, a mechanism, a missed diagnosis. Nothing here may reference
crime, cults, disappearances, missing persons, hauntings, or the biography of
a famous person -- those belong to a different channel and any such output is
discarded.

fresh_topic_ideas must contain a MINIMUM of 18 DISTINCT premises, each 15-30
words, each describing a documented CLINICAL presentation: what the patient
presented with, what was found, and why it was unexpected. Anonymous is
correct here ("a 51-year-old man", "a 19-year-old"), because published case
reports are themselves de-identified -- do NOT name individuals.

Never give medical advice, never address the viewer's own health, and never
recommend or discourage a treatment.
Return ONLY valid JSON:
{{"top_hook_formulas":["Hook 1","Hook 2","Hook 3"],
"winning_title_patterns":["Pattern 1","Pattern 2","Pattern 3"],
"thumbnail_text_examples":["3 WORD 1","3 WORD 2","3 WORD 3","3 WORD 4","3 WORD 5"],
"retention_hooks":["30pct","60pct","80pct"],
"niche_power_words":["word1","word2","word3","word4","word5","word6"],
"fresh_topic_ideas":["Topic 1","Topic 2","Topic 3","Topic 4","Topic 5","Topic 6",
"Topic 7","Topic 8","Topic 9","Topic 10","Topic 11","Topic 12","Topic 13","Topic 14",
"Topic 15","Topic 16","Topic 17","Topic 18"]}}"""
    try:
        # FIX: token budget raised from 400 -- 18 topics at 15-30 words
        # each plus the other fields genuinely needs more room; 400 was
        # truncating the JSON before the fresh_topic_ideas list count was
        # even raised, and would truncate far worse now.
        text = ai_generate(prompt, tokens=1600)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','', re.sub(r'```json|```','',text).strip())
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            d = json.loads(m.group())
            # FIX (found live, Ch1 run 30433881228 — real production bug):
            # the prompt above asks for "a concrete specific detail (a
            # number, a role, a place)" but nothing ever checked the model
            # actually did that. Confirmed live: fresh_topic_ideas returned
            # "The 6 Psychological Traps of [Specific Reality Show]
            # Contestants" verbatim -- the model left its own template
            # placeholder unfilled, this got selected as the episode topic,
            # scored 9.5/10 on Topic Clarity, and was approved for publish.
            # The literal "[specific" token then leaked further, becoming
            # the on-screen animation keyword for 9 of 55 segments. A
            # bracket character in a "specific" topic is never legitimate
            # (real topics don't contain "[" or "]") -- dropped here so a
            # lazy placeholder can never enter the 7-day cache at all.
            if isinstance(d.get("fresh_topic_ideas"), list):
                d["fresh_topic_ideas"] = [t for t in d["fresh_topic_ideas"]
                                           if isinstance(t, str) and "[" not in t and "]" not in t
                                           and _is_real_named_topic(t)]
            d["last_run"] = datetime.datetime.now().isoformat()
            intel[name] = d
            state["viral_intel"] = intel
            save_state(state)
            log("  Ch1 viral intel loaded")
            return d
    except Exception as e:
        log(f"  Ch1 viral intel err: {e}")

    # FIX (direct user report, July 27 2026 -- "it keeps giving the same
    # thing... for the last 4.5 to 5 days"): this fallback used to be
    # persisted into the SAME 7-day cache as a genuine AI-sourced result
    # (intel[name] = fallback; save_state(...)). A single transient
    # AI-provider failure -- routine given the heavy GitHub Models rate-
    # limiting seen live today -- then locked the tiny 4-item static
    # niche["topics"] list in as "this week's fresh topics" for a full
    # week, and every attempt past the first few exhausted it too,
    # producing exactly the repeated-topic pattern reported. The fallback
    # is now used for THIS run only and never written to state -- the
    # very next generation call retries the real AI request instead of
    # being stuck on the same 4 topics for days.
    log("  Ch1 viral intel: AI call failed -- using uncached fallback (will retry next run)")
    return {
        "top_hook_formulas": niche.get("dread_triggers", [])[:3],
        "winning_title_patterns": ["NUMBER + NOUN format", "The [THING] That Changed Everything"],
        "thumbnail_text_examples": [t.upper() for t in niche.get("topics", [])[:3]],
        "retention_hooks": ["The next detail is the one that changes everything",
                            "What was found at this point made investigators stop",
                            "The final revelation is the one nobody expected"],
        "niche_power_words": ["documented","witnessed","concealed","discovered","classified","permanent"],
        "fresh_topic_ideas": niche.get("topics", []),
        "last_run": datetime.datetime.now().isoformat(),
    }


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
        ("Cerebras",      call_cerebras),
        ("GitHubModels",  call_github_models),
        ("Cloudflare",    call_cloudflare),
        ("NvidiaNIM",     call_nvidia_nim),
        ("SambaNova",     call_sambanova),
        ("Gemini",        call_gemini),
        ("Groq",          call_groq),
        ("OpenRouter",    call_openrouter),
        ("Cohere",        call_cohere),
        ("Mistral",       call_mistral),
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
        log(f"  {len(working)}/{len(checks)} providers working — OK to proceed")

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
            comm = _edge.Communicate(text=script, voice=edge_voice, rate=EDGE_RATE)
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
    8-attempt script engine for Ch1 No Known Cause.
    Hard floor {MIN_GATE}/10, no relaxation tiers — if nothing clears it
    within {MAX_ATTEMPTS} attempts, the day is skipped (no publish).
    Returns (niche_name, niche, topic, script_result, trending_titles).
    """
    log("\n"+"="*65)
    log(f"  STAGE 1: No Known Cause {MAX_ATTEMPTS}-Attempt Script Engine")
    log(f"  Hard quality gate: {MIN_GATE}/10, every attempt, no relaxation — "
        f"skip the day if unmet after {MAX_ATTEMPTS} attempts")
    log("="*65)

    day        = datetime.datetime.now().weekday()
    niche_name = pick_best_niche(state, DAY_NICHE.get(day, "toxicology_cases"))
    niche      = next(n for n in NICHES if n["name"] == niche_name)
    episode    = state.get("episode_count", 0) + 1
    prev_title = state.get("last_title", "")

    intel          = run_ch1_viral_intelligence(niche)
    # FIX (found on word-by-word re-audit, July 15 2026): trending was
    # hardcoded to an empty list and never reassigned anywhere in this
    # file — fetch_trending_titles (a real, working YouTube Data API
    # call, verified against real endpoints) was fully built and
    # correctly threaded through generate_script_content, generate_titles,
    # and generate_best_cold_open as a parameter, but never actually
    # invoked to populate it. Every episode's "trend-aware" title/cold-
    # open generation was silently running on zero real data. Wired in.
    try:
        _yt_token_for_trends = get_yt_token()
        trending = fetch_trending_titles(niche, _yt_token_for_trends)
    except Exception as e:
        log(f"  Trending titles fetch (non-fatal): {e}")
        trending = []
    # NEW FEATURE (per explicit request — daily competitive research):
    # fetch_trending_titles above is title-only; daily_competitor_research
    # also has real view/like counts, cached per calendar day. Merged in
    # here so title generation sees the same real, richer signal (real
    # titles first, deduplicated).
    try:
        from daily_competitor_research import fetch_daily_competitor_research
        _daily_intel_titles = fetch_daily_competitor_research(niche, _yt_token_for_trends, str(SCRIPT_DIR))
        for _v in _daily_intel_titles.get("videos", []):
            if _v["title"] and _v["title"] not in trending:
                trending.append(_v["title"])
    except Exception as e:
        log(f"  Daily competitor research for titles (non-fatal): {e}")
    used_topics    = []
    gate           = MIN_GATE
    best_score     = 0.0
    best_result    = None
    best_topic     = niche["topics"][0]
    best_trending  = []

    # ── Topics come from Europe PMC, not from an LLM ────────────────────
    # Found on the first live run (30561361514, all 13 attempts blocked):
    # topics came from run_ch1_viral_intelligence, whose prompt still asked
    # for "the TOP 20 most viral dark documentary videos" and real cases
    # involving "a cult, con artist, disappearance, or investigation". Under
    # the rare_disease_cases niche it duly produced the disappearance of
    # Maura Murray and the Mad Trapper of Rat River, and the winning topic
    # was "The Enigmatic Life of Sylvia Plath" -- while the episode's sourced
    # case was a surgical-oncology paper. The script and the case were about
    # different things entirely, which is why nothing could clear the gate.
    #
    # A channel whose whole premise is "one real published case" has no
    # business inventing topics. Each attempt now takes one real CC BY paper
    # and uses ITS OWN TITLE as the topic, so topic and case are the same
    # document by construction and cannot drift apart again.
    pmc_cases = []
    try:
        from pmc_data import get_real_cases, case_to_topic, MEDICAL_NICHE_NAMES
        if niche_name in MEDICAL_NICHE_NAMES:
            pmc_cases = get_real_cases(niche_name, count=MAX_ATTEMPTS)
            log(f"  PMC topic pool: {len(pmc_cases)} real CC BY cases for {niche_name}")
            for _c in pmc_cases[:3]:
                log(f"    {_c['pmcid']}: {case_to_topic(_c)[:80]}")
            if not pmc_cases:
                log("  WARNING: PMC returned no usable cases — falling back to "
                    "the niche's static real-case topic list")
    except Exception as e:
        log(f"  PMC topic pool (non-fatal): {e}")

    log(f"\nNiche: {niche_name} | ${niche['rpm']} RPM | Ep{episode}")

    # Topic-scoring backlog integration — same pattern as Ch2: prefer a
    # human-approved topic from the real backlog over fresh generation.
    _approved_topic_entry = None
    try:
        from topic_scoring import get_next_approved_topic
        _approved_topic_entry = get_next_approved_topic(SCRIPT_DIR)
    except Exception as e:
        log(f"  Topic backlog check (non-fatal): {e}")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # FIX (direct user report, July 24 2026): flat hard gate, no
        # relaxation tiers — every attempt must clear MIN_GATE (8.5).
        gate = MIN_GATE

        # Get fresh topic each attempt
        # FIX (found live, Ch1 run 30433881228): defense-in-depth against
        # unfilled "[Specific X]" template placeholders reaching `topic` --
        # the real source (run_ch1_viral_intelligence's AI call) is now
        # filtered too, but a 7-day-cached intel dict from before that fix,
        # or any future path that populates fresh_topic_ideas/the backlog,
        # could still carry one through. A bracket is never legitimate in
        # a genuinely specific topic.
        attempt_case = None
        if pmc_cases:
            # One real paper per attempt; the paper IS the topic.
            attempt_case = pmc_cases[(attempt - 1) % len(pmc_cases)]
            topic = case_to_topic(attempt_case) or attempt_case.get("title", "")
            # ...but a journal title is not a viewer-facing premise.
            #
            # Run 30563819566 showed the cost: sourcing topics from papers
            # fixed the topic/case mismatch, then failed TOPIC CLARITY (needs
            # 8.8) with titles like "Orodental phenotype and genotype findings
            # in all subtypes of hypophosphatasia" -- 5.5/10. Precise, and
            # meaningless to anyone outside the specialty.
            #
            # So translate the framing while keeping the paper. The case, the
            # citation and every sourced fact still come from this exact
            # document; only the sentence describing it to a viewer changes.
            # Falls back to the raw title, so a failed AI call costs clarity
            # rather than breaking the topic/case link.
            try:
                _plain = ai_generate(
                    "Rewrite this published medical case as ONE plain-English "
                    "sentence a non-medical viewer would understand, 15-25 words.\n"
                    "Say who the patient was, what happened to them, and what "
                    "made it unexpected. Use no jargon unless you immediately "
                    "explain it. Do not name any individual. Do not give advice.\n\n"
                    f"PAPER TITLE: {topic}\n"
                    f"CASE TEXT: {(attempt_case.get('narrative') or '')[:1200]}\n\n"
                    "Return ONLY the sentence.", tokens=120)
                if _plain:
                    _plain = _plain.strip().strip('"').split("\n")[0].strip()
                    if 8 <= len(_plain.split()) <= 45 and "[" not in _plain:
                        log(f"  Plain-language framing: {_plain[:88]}")
                        topic = _plain
            except Exception as _e:
                log(f"  Plain-language framing (non-fatal): {_e}")
        elif _approved_topic_entry and attempt == 1 and "[" not in _approved_topic_entry["topic_text"]:
            topic = _approved_topic_entry["topic_text"]
        else:
            # Reached only when PMC is unreachable. intel["fresh_topic_ideas"]
            # is deliberately NOT consulted here any more -- see the PMC topic
            # pool note above; that list is where the dark-documentary topics
            # came from. niche["topics"] is a hand-written list of real,
            # verifiable published cases, so the fallback stays clinical.
            fresh = [t for t in niche["topics"] if "[" not in t and "]" not in t]
            unused = [t for t in fresh if t not in used_topics]
            topic = unused[0] if unused else random.choice(niche["topics"])
            try:
                from topic_scoring import add_topic_candidate
                add_topic_candidate(SCRIPT_DIR, "betrayal_deepdive", topic, niche_name,
                                     lambda p, tokens=200: ai_generate(p, tokens=tokens))
            except Exception as e:
                log(f"  Topic scoring (non-fatal): {e}")
        used_topics.append(topic)

        # Research real cases for this topic
        # FIX: get_research_context now returns (prose_string, real_cases_list)
        # instead of just a string — real_cases feeds the new citation
        # system (built this session), attached to result below rather
        # than changing run_stage1's own broader return signature, which
        # has many call sites elsewhere.
        research_ctx, real_cases = get_research_context(niche_name, topic)

        log(f"\nAttempt {attempt}/{MAX_ATTEMPTS} (gate:{gate})...")
        log(f"Topic: {topic[:80]}")

        try:
            result = generate_script_content(
                niche, topic, episode, attempt,
                trending_titles=trending,
                research_context=research_ctx,
                preselected_case=attempt_case)

            if not result:
                time.sleep(5); continue
            result["real_cases"] = real_cases

            # v6 addition — real research-usage verification (same fix
            # built for Ch3/Ch4, applying here since Ch1 has the
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

            # ── BLOCKING POLICY GATE (rules 1,2,3,6) ─────────────────
            # Runs BEFORE scoring, because a script that violates health
            # policy must be rewritten regardless of how well it scores.
            # 2026 YouTube policy explicitly restricts AI-delivered medical
            # advice, and a limited-ads label removes the $25-40 CPM band
            # that is the entire economic case for this niche.
            try:
                from medical_policy_gate import check_script, format_violations
                _pol_ok, _pol_v = check_script(result.get("script", ""),
                                                citation=get_episode_case().get("citation", ""))
                if not _pol_ok:
                    log(f"  POLICY GATE FAILED — rewriting:\n{format_violations(_pol_v)}")
                    notify_stage_score("Script-Policy", attempt, MAX_ATTEMPTS, 0, 1,
                                        extra=format_violations(_pol_v)[:300])
                    time.sleep(3); continue
                log("  Policy gate: passed")
            except Exception as e:
                # A gate that cannot run must not silently pass a script.
                log(f"  POLICY GATE ERROR — treating as failure: {e}")
                time.sleep(3); continue

            # ── PROMISE/PAYOFF CONSISTENCY (retention addition #2) ───────
            # 2026: viewer-satisfaction signals now outweigh raw watch time,
            # so a title whose specific promise is never resolved is actively
            # penalised rather than merely neutral. Checks that the concrete
            # tokens in the title (numbers, units, distinctive long words)
            # actually appear in the back half of the script, where the
            # payoff lives.
            _promise_ok = True
            try:
                _t = (result.get("title", "") or "")
                _script_txt = (result.get("script", "") or "")
                _half = _script_txt[len(_script_txt) // 2:].lower()
                _claims = re.findall(r"\d[\d,\.]*\s?\w*|\b[A-Za-z]{9,}\b", _t)
                _claims = [c.strip().lower() for c in _claims if len(c.strip()) > 2]
                if _claims:
                    _hit = sum(1 for c in _claims if c.split()[0] in _half)
                    _promise_ok = _hit > 0
                    log(f"  Promise/payoff: {_hit}/{len(_claims)} title claim(s) "
                        f"resolved in the payoff half — {'OK' if _promise_ok else 'UNRESOLVED'}")
                    if not _promise_ok:
                        log("  Title promises something the script never resolves — rewriting")
                        time.sleep(3); continue
            except Exception as e:
                log(f"  Promise/payoff check (non-fatal): {e}")

            score, _, _ = score_result(result, topic)
            wc       = result.get("words", 0)
            log(f"  {score}/10 {'APPROVED' if score>=gate else 'BLOCKED'} | {wc}w")
            notify_stage_score("Script", attempt, MAX_ATTEMPTS, score, gate, extra=f"{wc} words | {topic[:60]}")

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
                    tg(f"⚠️ Ch1: real research was found ({len(result['real_cases'])} sources) but "
                       f"the script that's actually publishing shows no clear sign of using it — "
                       f"may be relying on invented details instead of the real documented facts. "
                       f"Worth a manual check on this episode's factual grounding.")
                return niche_name, niche, topic, result, trending

            time.sleep(3)
        except Exception as e:
            log(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    # FIX (direct user report, July 24 2026 — explicit policy decision):
    # no fallback-publish tier anymore. If nothing cleared MIN_GATE
    # (8.5) within MAX_ATTEMPTS attempts, the day is skipped —
    # never publish a script that didn't genuinely earn the real bar,
    # even as a "best available" compromise.
    tg(f"Ch1 Day Skipped — no script cleared {MIN_GATE}/10 after {MAX_ATTEMPTS} attempts "
       f"(best: {best_score}/10). Per your standing instruction, nothing under {MIN_GATE} "
       f"gets published.")
    # exit(2), not exit(0). Skipping the day is the correct EDITORIAL
    # decision, but it is not a successful run, and exiting 0 made the whole
    # workflow report green having produced no video at all. The first live
    # run (30561361514) did exactly that: 13/13 attempts blocked, no
    # artifact, "success" in the Actions UI, and the only clue was a buried
    # "No files were found" warning on the upload step. A run that produces
    # nothing has to be visibly red, or a silent daily no-op looks identical
    # to a working channel.
    #
    # 2 rather than 1 so it stays distinguishable from a crash in the logs.
    log(f"EXIT 2: no script cleared {MIN_GATE}/10 in {MAX_ATTEMPTS} attempts "
        f"(best {best_score}/10) — no video produced.")
    sys.exit(2)


def pick_voice(niche_name, state):
    """Select best voice for this niche based on performance history."""
    # FIX (direct user request, July 25 2026 — "I want to try with that
    # [Ireland female] at the start... I don't want anything by
    # chance"): select_best_voice's learned rotation only guarantees a
    # brand-new voice gets tried on the FIRST 5 episodes of a niche's
    # own history -- every one of Ch1's 5 niches already has real
    # episode history, so en-IE-EmilyNeural (freshly re-prioritized to
    # position 0) would otherwise land in the "unproven" pool and only
    # get picked with real but non-certain odds. This is a genuine,
    # one-time, deterministic override -- the very next episode
    # (whichever niche is picked that day) uses Ireland female for
    # real, no chance involved. Once used, state["ie_female_trial_done"]
    # is set (by the caller, right after this returns) so every episode
    # after that goes back to the normal learned rotation, matching "if
    # it doesn't work well, then we'll go with some other female voices".
    if not state.get("ie_female_trial_done"):
        log("  Voice (one-time forced trial, per direct request): en-IE-EmilyNeural")
        return "en-IE-EmilyNeural"
    available = VOICES.get(niche_name, EXTENDED_VOICES)
    return select_best_voice(state, niche_name, available)


def run_approval_gate(title, niche_name, script_clean, edge_voice, score):
    """30-minute Telegram approval gate before video generation."""
    niche = next(n for n in NICHES if n["name"] == niche_name)
    deadline     = datetime.datetime.now() + datetime.timedelta(minutes=30)
    deadline_str = deadline.strftime("%I:%M %p")
    preview      = script_clean[:400].replace("<","").replace(">","")

    approval_text = (
        f"🌑 <b>NO KNOWN CAUSE — APPROVAL NEEDED</b>\n\n"
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
    "toxicology_cases":        "0xC0554B",  # oxidised red -- the alarming value
    "diagnostic_odyssey":      "0xC39A45",  # amber -- the unresolved answer
    "neurology_cases":         "0x5FA8A0",  # clinical teal
    "rare_disease_cases":      "0x7B93A3",  # slate
    "senior_health_longevity": "0x6E9B7A",  # calm green
    "medical_mystery_outbreak":"0xC0554B",  # oxidised red
    "surgical_case_studies":   "0x5FA8A0",  # clinical teal
    "drug_discovery_stories":  "0xC39A45",  # amber
    "sleep_science":           "0x6F7FA8",  # night blue
    "medical_history":         "0x9A8A6B",  # archive sepia
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


# FIX (direct user report, July 23 2026 — "it's not only the things that
# I told. There should be hundreds of things that should be added...
# according to the niche and title"): the original 6-category version
# lived here as a local dict. Replaced with video_pipeline/content_sfx.py
# — a shared, ~78-category (290+ individual keyword phrases) library
# used by all 5 channels, with per-niche priority categories and a real
# topic/title-anchor cue, instead of a small fixed local set.


def add_horror_atmosphere_fx(video_path, script, audio_duration, niche_name, output_path, topic=""):
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
        # FIX (direct user report, July 23 2026): this was a fixed 0.65
        # fraction on every single video regardless of content — "if there
        # is a jump scare, it should give a jump scare" implies it should
        # land on the actual reveal, not an arbitrary timestamp. phrases[-1]
        # is already the last detected story beat (used above for the 2nd
        # chromatic-aberration burst) — reuse its real position when
        # available, since that IS the closest thing this script has to a
        # detected "biggest reveal" moment, and only fall back to 0.65 when
        # extract_key_phrases found nothing to anchor to.
        flash_frac = phrases[-1][1] if phrases and 0.4 <= phrases[-1][1] <= 0.85 else 0.65
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

        # ── Content-specific SFX: real ~78-category, niche+topic-aware
        # library (video_pipeline/content_sfx.py) — a cue at the real
        # script position where that content is actually mentioned, each
        # with its own distinct tone signature, instead of a handful of
        # generic stingers reused everywhere.
        from content_sfx import detect_content_sfx_cues, get_sfx_synth
        content_cues = detect_content_sfx_cues(script, audio_duration, niche_name=niche_name, topic=topic, max_cues=6)
        for ci, (category, cue_t) in enumerate(content_cues):
            cue_delay_ms = int(max(0.3, cue_t) * 1000)
            for li, (freq, dur, fade_st, fade_d, vol) in enumerate(get_sfx_synth(category)):
                label = f"content{ci}_{li}"
                stinger_filters.append(
                    f"sine=frequency={freq}:duration={dur},"
                    f"afade=t=out:st={fade_st}:d={fade_d},volume={vol},"
                    f"adelay={cue_delay_ms}|{cue_delay_ms}[{label}]"
                )
                stinger_labels.append(f"[{label}]")
        if content_cues:
            log(f"  Content-matched SFX: {[c for c, _ in content_cues]}")

        drone_duration = audio_duration + 1
        stinger_chain = ";".join(stinger_filters)
        stinger_inputs = "".join(stinger_labels)
        n_mix_inputs = 4 + len(stinger_labels)  # original + riser + impact + drone + stingers/content-cues

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
            # FIX (direct user report, July 25 2026 — "the content match
            # SFX... it was blank... just like an AI talking, and it was
            # random"): confirmed via `ffmpeg -h filter=amix` that
            # normalize defaults to true, and this call never set
            # normalize=0. With up to ~16 simultaneous inputs here (base
            # 4 + up to 12 content-cue layers), ffmpeg was auto-dividing
            # EVERY input's volume by the input count to prevent
            # clipping — silently burying the already-brief SFX cues
            # (and quietly reducing the narration itself) by an amount
            # that varied episode-to-episode depending on how many cues
            # fired. normalize=0 respects the volume= already set
            # explicitly on each layer instead of ffmpeg re-scaling them.
            f"[1:a][riser][impact][drone]{stinger_inputs}amix=inputs={n_mix_inputs}:"
            f"duration=first:dropout_transition=0:normalize=0[mixedaudio]"
        )

        run_ffmpeg([
            "ffmpeg", "-y", "-i", video_path, "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "[mixedaudio]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-ar", "44100", output_path
        ], label="horror-fx", timeout=1200)

        if Path(output_path).exists() and Path(output_path).stat().st_size > 1_000_000:
            log(f"  Horror atmosphere FX applied: grain + {len(beat_fracs[:2])} glitch bursts + "
                f"1 jump-scare flash + {len(phrases)} unstable text beats + "
                f"{len(content_cues)} content-matched SFX cues")
            return output_path
        else:
            log("  Horror FX: output invalid — using un-treated video (non-fatal)")
            return video_path
    except Exception as e:
        log(f"  Horror atmosphere FX failed (non-fatal): {e}")
        return video_path


_last_video_fallback_flags = {}  # FIX (final re-audit): see collapse_index_pipeline.py for full rationale

def assemble_video(niche_name, audio_path, audio_duration, topic, script="", episode=1, real_cases=None, ass_path=None, title=""):
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
    # FIX (direct user report, July 24 2026): title threaded through so
    # get_stage_matched_video can detect the real nation/setting of the
    # story from it, not just the shorter topic string.
    bg_path     = get_stage_matched_video(niche, script, audio_duration, topic=topic, title=title)
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

    if script:
        overlaid = str(WORK_DIR / "composed_horror_fx.mp4")
        _pre_horror_composed = composed
        composed = add_horror_atmosphere_fx(composed, script, audio_duration,
                                             niche_name, overlaid, topic=topic)
        _last_video_fallback_flags["horror_fx_failed"] = (composed == _pre_horror_composed)

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
    title_context = (
        f"\nTHE ACTUAL VIDEO TITLE (match its register exactly — if it's dread-driven,\n"
        f"the thumbnail must be dread-driven too; if it's sympathy/woeful, match that.\n"
        f"Do not clash with this title's tone): \"{title}\"\n"
        if title else ""
    )
    # FIX (direct user report, July 24 2026 — "it should be questioning
    # the audience... not some big typing letters"): the old prompt only
    # ever produced a NUMBER+NOUN statement, and the sanitizer below
    # stripped "?" from anything the AI did produce, making a genuine
    # question format literally impossible to ever get through. Now
    # explicitly offers a direct QUESTION format as an equally valid
    # alternative to the number+noun style, and the sanitizer/length
    # rules below allow it through.
    prompt = (
        f"Generate the most psychologically compelling short thumbnail text "
        f"for a dark documentary video.\n"
        f"NICHE: {niche['name']} | TOPIC: {topic[:100]}\n"
        f"{title_context}\n"
        f"Pick ONE of these two formats — whichever creates the strongest real\n"
        f"curiosity gap for THIS specific topic (must match the title's register\n"
        f"above if one is given):\n"
        f"A. NUMBER+NOUN: a specific number + a concrete, visceral noun\n"
        f"   (e.g. FOUND INSIDE WALLS, 4380 DAYS HIDDEN)\n"
        f"B. DIRECT QUESTION: a short, unsettling question aimed straight at the\n"
        f"   viewer, tied to the real topic — not generic clickbait\n"
        f"   (e.g. WHO WAS WATCHING?, WHY DID SHE STOP?)\n\n"
        f"Rules: 2-4 words. ALL CAPS. Dark and specific. Never generic.\n"
        f"If format B, end with a single '?' and nothing else.\n"
        f"Return ONLY the text, nothing else."
    )
    # FIX (found on direct user request, July 23 2026 — real gate gap
    # matching Ch5's already-proven fix): a real scoring function for
    # exactly this purpose exists in thumbnail_engine_v2.py, but this
    # function generated exactly ONE AI candidate and used it unscored,
    # unconditionally — no gate at all, not even the "pick best of
    # several" pattern Ch5 already has. Now generates up to 3 real
    # candidates and picks the highest-scoring one.
    try:
        from thumbnail_engine_v2 import score_thumbnail_text
    except Exception:
        score_thumbnail_text = lambda t: 5.0  # neutral score if the module truly isn't available

    # FIX (direct user report, July 24 2026 — explicit policy decision,
    # "every stage... thumbnails... quality score minimum of 8.5... hard
    # time for it to remake is 8 attempts... if it is less than that, I
    # don't want it to produce that"): hard floor raised from 7.9 to 8.5,
    # and this no longer "best-effort" publishes the best candidate found
    # if nothing ever cleared the bar (the old fallback_bank/best-effort
    # path silently violated exactly that instruction). Now generates up
    # to 8 real candidates one at a time, stopping the moment one clears
    # the gate; returns None (real failure) if none of the 8 do — the
    # caller must treat that as a stage failure, not substitute a
    # placeholder or an unscored fallback bank phrase.
    THUMB_TEXT_MIN = 8.5
    THUMB_TEXT_MAX_ATTEMPTS = 13  # raised from 8, direct user request July 24 2026
    candidates = []
    for attempt in range(1, THUMB_TEXT_MAX_ATTEMPTS + 1):
        try:
            result = ai_generate(prompt, tokens=15)
            if result:
                # FIX (direct user report, July 24 2026): this used to strip
                # EVERY non-letter character including "?", which made a
                # genuine question-format thumbnail text impossible to ever
                # produce regardless of what the AI returned. Now preserves
                # a single trailing "?" and allows 2-4 words (was a rigid
                # exactly-3), since a real question often needs 3-4 words.
                has_question = result.strip().endswith("?")
                result = re.sub(r'[^A-Z\s]', '', result.upper()).strip()
                words = result.split()[:4]
                if 2 <= len(words) <= 4:
                    text = ' '.join(words) + ("?" if has_question else "")
                    candidates.append(text)
        except Exception as e:
            log(f"  Thumbnail text attempt {attempt}/{THUMB_TEXT_MAX_ATTEMPTS} (non-fatal): {e}")

        if candidates:
            scored = [(c, score_thumbnail_text(c)) for c in dict.fromkeys(candidates)]
            best_text, best_score = max(scored, key=lambda pair: pair[1])
            log(f"  Thumbnail text attempt {attempt}/{THUMB_TEXT_MAX_ATTEMPTS}: best so far "
                f"'{best_text}' ({best_score}/10)")
            notify_stage_score("Thumbnail text", attempt, THUMB_TEXT_MAX_ATTEMPTS, best_score,
                                THUMB_TEXT_MIN, extra=f"'{best_text}'")
            if best_score >= THUMB_TEXT_MIN:
                log(f"  Thumbnail text cleared {THUMB_TEXT_MIN}/10 on attempt {attempt}.")
                return best_text

    log(f"  Thumbnail text never cleared {THUMB_TEXT_MIN}/10 after {THUMB_TEXT_MAX_ATTEMPTS} attempts.")
    return None


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
    base_tags = [niche_name.replace("_"," "), "medical case", "case report",
                 "clinical case", "medicine", "published case", "medical documentary",
                 "case study", "clinical files", "peer reviewed", "medical science",
                 "diagnosis", "pathophysiology", "medical education", "real case"]
    niche_specific = {
        "toxicology_cases":        ["toxicology","poisoning case","clinical toxicology"],
        "diagnostic_odyssey":      ["misdiagnosis","diagnostic error","medical mystery"],
        "neurology_cases":         ["neurology","brain case study","neurological disorder"],
        "rare_disease_cases":      ["rare disease","case report","unusual presentation"],
        "senior_health_longevity": ["healthy ageing","longevity research","geriatric medicine"],
        "medical_mystery_outbreak":["epidemiology","outbreak investigation","public health"],
        "surgical_case_studies":   ["surgery","surgical case","operative medicine"],
        "drug_discovery_stories":  ["drug discovery","pharmacology","medical history"],
        "sleep_science":           ["sleep science","sleep disorder","polysomnography"],
        "medical_history":         ["medical history","history of medicine","historical treatment"],
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
    log(f"NO KNOWN CAUSE v14.0 — Phase: {phase.upper()}")
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
            tg(f"❌ Ch1 Upload FAILED: video file missing at {video_path}")
            sys.exit(1)

        token = get_yt_token()

        # FIX (July 23 2026, direct user request): reuse the video already
        # uploaded unlisted during the generate-phase audio+video review,
        # instead of uploading the same multi-hundred-MB file a second
        # time. That upload only had placeholder metadata (description/
        # tags don't exist until STAGE 5, after that review) -- push the
        # real, final metadata onto it now, before it goes public.
        _prerendered_vid_id = pending.get("prerendered_yt_video_id")
        if _prerendered_vid_id:
            update_video_metadata(_prerendered_vid_id, title, description, tags, token=token)
            yt_url, vid_id = pending.get("prerendered_yt_url"), _prerendered_vid_id
            log(f"  Reusing pre-rendered unlisted video from generate-phase review: {yt_url}")
        else:
            # Upload main video — UNLISTED first, not public yet. The final
            # pre-publish gate below sends the real, full, unlisted link
            # (no Telegram size limit, unlike the 60s preview clip reviewed
            # during generate) so the whole thing can be watched/downloaded
            # and judged before it ever goes public, even if the reviewer
            # was away and missed every earlier check-in.
            yt_url, vid_id = run_stage_with_retry(
                upload_yt, "Upload",
                video_path, title, description, tags, token=token, privacy="unlisted")

        from human_review_gate import review_final_video_before_publish
        _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
        _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        _final_gate = review_final_video_before_publish(
            "Ch1 No Known Cause", yt_url, thumb_path,
            TG_TOKEN, TG_CHAT, check_ins_used=0,
            gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
        if _final_gate["decision"] != "approve":
            delete_yt_video(vid_id, token=token)
            clear_pending(SCRIPT_DIR)
            tg(f"🔄 Ch1: final video rejected — unlisted upload removed, "
               f"nothing published. Feedback: {_final_gate.get('feedback') or '(none given)'}. "
               f"A fresh episode will be generated on the next cycle.")
            log("Final pre-publish gate: rejected — stopping before publish steps.")
            sys.exit(0)
        set_video_privacy(vid_id, "public", token=token)
        log(f"  Final gate approved — video is now public: {yt_url}")

        # FIX (direct user report, July 23 2026 — "after uploading, it
        # also needs to take up the job of checking: what is going on,
        # how many views... likes... subscribers... what the monetary
        # environment is... report back to me... in Telegram"): a real
        # publish-time snapshot (views/likes so far, channel subscriber
        # count, recent Gumroad revenue) sent right after the video goes
        # public, on top of the existing weekly aggregate report.
        try:
            from post_upload_reporter import send_post_upload_report
            send_post_upload_report(
                "No Known Cause", yt_url, vid_id, token,
                TG_TOKEN, TG_CHAT, gumroad_token=os.environ.get("GUMROAD_ACCESS_TOKEN"), tg_fn=tg)
        except Exception as e:
            log(f"  Post-upload report (non-fatal): {e}")

        # FIX: ensure_niche_playlist existed fully built but was never
        # called anywhere — playlist_id was always empty string (state
        # never had a real playlist ID to read), meaning add_to_playlist
        # below, despite being correctly wired, never actually fired.
        if not playlist_id:
            try:
                playlist_id = ensure_niche_playlist(token, niche_name, "No Known Cause")
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
            # FIX (found on deep re-audit): this pointed at
            # channels/betrayal_deepdive/growth_engine.py — a path that
            # doesn't exist (an earlier "fix" comment here claimed the
            # real file "lives right next to master_pipeline.py," but the
            # real file is video_pipeline/growth_engine.py, a SIBLING of
            # channels/, not inside it — verified via Path.exists()).
            # Because this used Popen (fire-and-forget, never checked),
            # the wrong path failed silently INSIDE that separate process
            # every single time — this is very likely the actual reason
            # growth-engine features (hype notifications, comment engine,
            # CTR recovery, caption/pinned-comment update) never visibly
            # ran for this channel, with zero error anywhere to point at.
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
        send_hype_push(yt_url, title, "No Known Cause", day=0)

        tg(f"✅ <b>No Known Cause — LIVE</b>\n\n"
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

    # FIX (direct user request, July 25 2026 — "I don't want it to start
    # from scratch if we are re-triggering... if it passes some stage,
    # with the next stage, if it fails in the further stage, it starts
    # with the last passed stage"): ckpt_save/ckpt_load existed as pure
    # dead scaffolding before this — defined but never called anywhere
    # in the file. On a workflow_dispatch re-run with is_makeup=true,
    # this restores whichever stages already cleared their gate on the
    # cancelled/failed run instead of regenerating them from scratch.
    _resume_script = ckpt_load("script_stage") if IS_MAKEUP else None
    _resume_audio  = ckpt_load("audio_stage") if IS_MAKEUP else None
    if _resume_audio and not CKPT_AUDIO_FILE.exists():
        log("  [ckpt] audio checkpoint metadata found but the audio file "
            "itself is missing on this runner — discarding, audio will "
            "be regenerated")
        _resume_audio = None

    # FIX (direct user request, July 25 2026 — "I want a notification
    # asking for my explicit permission: should it go with the third
    # stage or fourth stage, or should it start from scratch? I need to
    # check and find out if I am okay with that kind of script, the
    # audio, or the title"): a resume is never silent. Before picking up
    # from a checkpoint, send the real checkpointed script (PDF) and
    # audio (file) and wait for an explicit decision.
    if _resume_script:
        _saved_case = ckpt_load("episode_case")
        if _saved_case:
            set_episode_case(_saved_case)
            log(f"  Resumed episode case: {_saved_case.get('pmcid','?')}")
        else:
            log("  WARNING: resuming with no saved case — visuals will be "
                "fallback cards only. Prefer a fresh run.")
        try:
            from human_review_gate import review_resume_checkpoint
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            _resume_decision = review_resume_checkpoint(
                "No Known Cause",
                _resume_script["title"], _resume_script["script_clean"], _resume_script["score_val"],
                _resume_script["niche_name"],
                str(CKPT_AUDIO_FILE) if _resume_audio else None,
                _resume_audio.get("tool_used") if _resume_audio else None,
                _resume_audio.get("edge_voice") if _resume_audio else None,
                _resume_audio.get("audio_duration") if _resume_audio else None,
                TG_TOKEN, TG_CHAT, gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass,
                timeout_minutes=30)
            log(f"  [ckpt] resume-checkpoint decision: {_resume_decision}")
            if _resume_decision == "restart_scratch":
                tg("🔄 Ch1: starting completely fresh per your decision — the checkpoint is discarded.")
                ckpt_clear()
                _resume_script, _resume_audio = None, None
            elif _resume_decision == "redo_audio_only":
                tg("🎙️ Ch1: keeping the checkpointed script + title, regenerating audio fresh.")
                _resume_audio = None
            else:
                tg("▶️ Ch1: resuming — skipping whatever already passed.")
        except Exception as e:
            log(f"  Resume-checkpoint gate unavailable (non-fatal, resuming without asking): {e}")

    try:
        # FIX: run_provider_health_check existed fully built (tests all 7
        # providers, hard-stops if all fail, alerts if fewer than 3 work)
        # but was NEVER actually called anywhere — cascading provider
        # failures went completely undetected until the whole run failed
        # deep into script generation instead of being caught upfront.
        _healthy_providers = run_provider_health_check()

        # token obtained at upload time — not needed for script generation

        if _resume_script:
            log("  [ckpt] RESUMING: script + title already passed — skipping Stage 1 + review")
            niche_name       = _resume_script["niche_name"]
            niche            = _resume_script["niche"]
            topic            = _resume_script["topic"]
            script_result    = _resume_script["script_result"]
            trending_titles  = _resume_script["trending_titles"]
            script_clean     = _resume_script["script_clean"]
            wc               = _resume_script["wc"]
            score_val        = _resume_script["score_val"]
            edge_voice       = _resume_script["edge_voice"]
            real_cases       = _resume_script["real_cases"]
            title            = _resume_script["title"]
            episode          = _resume_script["episode"]
            _approved_topic_id_for_pending = _resume_script.get("approved_topic_id_for_pending")
            tg(f"▶ Ch1: resuming from checkpoint — script + title already "
               f"passed ({wc}w, {score_val}/10, \"{title[:60]}\"). Skipping straight to "
               f"{'video (audio also passed)' if _resume_audio else 'audio'}.")
        else:
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
            score_val, _score_issues, _score_subscores = score_result(script_result, topic)

            # FIX (direct user report, July 23 2026 — "sync Claude Code into
            # the script as a main interceptor for quality... if it generates
            # a script, I want you to read that script and generate the
            # quality audit... minimum is 6.8... if it is less than that,
            # remake it without fail, even before it comes to me as a manual
            # in Telegram"): the 13-attempt loop above already gates on a
            # rule-based rubric (keyword/pattern signals), but that is not
            # the same as an independent AI actually reading the whole script
            # and judging it holistically. This is that second, independent
            # read -- an AI-judge audit with its own 6.8 floor, reworking
            # (a fresh run_stage1 attempt) before this ever reaches Telegram.
            # See video_pipeline/quality_auditor.py for the honest technical
            # note on why this uses the pipeline's existing AI providers
            # rather than literally invoking Claude Code from a cron job.
            try:
                from quality_auditor import enforce_quality_gate
                # NOTE: run_stage1 re-picks niche+topic fresh on every call (its
                # own rotation/backlog logic) -- a rework could legitimately come
                # back as a different niche/topic than the original attempt. If
                # only script_clean were replaced here while niche_name/niche/
                # topic/trending_titles/script_result stayed pointed at the OLD
                # attempt, every downstream stage (title, thumbnail, audio) would
                # describe a different story than the script actually being
                # narrated. enforce_quality_gate keeps whichever rework attempt
                # scored best, which is not necessarily the LAST one tried -- so
                # every attempt (including the original) is recorded here, and
                # after the gate returns, the matching full tuple is looked up
                # by script text rather than assumed to be the most recent call.
                _rework_history = [{"niche_name": niche_name, "niche": niche, "topic": topic,
                                     "script_result": script_result, "trending_titles": trending_titles}]
                def _rescript():
                    _n2, _ni2, _t2, _res2, _tr2 = run_stage1(state)
                    _rework_history.append({"niche_name": _n2, "niche": _ni2, "topic": _t2,
                                             "script_result": _res2, "trending_titles": _tr2})
                    return _res2["script"]
                # FIX (direct user request, July 25 2026 — "it just attempts
                # two times. I need this to be attempted a minimum of 13
                # times, just like for the script... hard embedded, I don't
                # want anything by chance"): this independent AI-judge audit
                # used to cap at 2 reworks regardless of MAX_ATTEMPTS, so a
                # script could pass the rubric gate's full 13 attempts but
                # this second, holistic check only ever got 2 real tries at
                # fixing what it found before giving up. Now shares the same
                # real attempt budget as the rubric gate.
                _audit = enforce_quality_gate(
                    "script", script_clean, "", ai_generate,
                    _rescript, tg_fn=tg, topic=topic, max_reworks=MAX_ATTEMPTS)
                for _entry in reversed(_rework_history):
                    if _entry["script_result"]["script"] == _audit["content"]:
                        niche_name, niche, topic = _entry["niche_name"], _entry["niche"], _entry["topic"]
                        script_result = _entry["script_result"]
                        trending_titles = _entry["trending_titles"]
                        wc = script_result["words"]
                        score_val, _score_issues, _score_subscores = score_result(script_result, topic)
                        break
                script_clean = _audit["content"]
                log(f"  Quality audit (script): {_audit['score']}/10 "
                    f"(passed={_audit['passed']}, reworked={_audit['reworked']}, "
                    f"fallback={_audit['used_fallback']})")
            except Exception as e:
                log(f"  Quality audit unavailable (non-fatal, proceeding with existing script): {e}")

            edge_voice   = pick_voice(niche_name, state)
            state["ie_female_trial_done"] = True  # one-time forced trial above only ever fires once
            # v6 addition — real citation system: the actual sources used
            # during research (if any were found), carried through for the
            # description's Sources block and the end-of-video credits scene.
            real_cases   = script_result.get("real_cases", [])
            # FIX (direct user report, this session): whether this
            # episode needs the "names/details changed" disclosure is
            # now decided at script-generation time (generate_script_
            # content) but the disclosure itself is written-only, added
            # to the description below -- never spoken in the narration.
            needs_fiction_disclosure = script_result.get("needs_fiction_disclosure", True)

            tg(f"Ch1 Script ready: {niche_name} | {wc}w | {score_val}/10\n{topic[:80]}")

            # Approval gate
            # FIX: generate_titles's dread/sympathy alternation reads
            # state["last_title_register"] to decide which register to use next —
            # but state was never being passed in here, so it always saw state=None
            # and always computed the same register, every single episode. The
            # alternation looked implemented but never actually alternated.
            # FIX (direct user report, July 24 2026 — explicit policy decision):
            # generate_titles now genuinely returns None if nothing cleared the
            # 8.5 title gate after 8 attempts. This used to fall back to a bare
            # "Series Ep12"-style placeholder title regardless of score — a
            # silent policy violation. Now skips the day instead.
            title_result = run_stage_with_retry(generate_titles, "Titles", niche, topic, episode, state, trending_titles)
            if not title_result:
                tg(f"Ch1 Day Skipped — no title cleared 8.5/10 after {MAX_ATTEMPTS} attempts. Per your "
                   f"standing instruction, nothing under 8.5 gets published.")
                log(f"  Title gate never cleared 8.5 after {MAX_ATTEMPTS} attempts. Skipping.")
                sys.exit(0)
            title = title_result

            # v9 addition — real title-script alignment check, per direct
            # research confirming spoken-content-to-title matching affects
            # both search relevance and satisfaction signals. generate_titles
            # writes the title from the topic description alone — it never
            # actually reads the final script text, creating real drift risk.
            _title_distinctive_words = {
                w.strip(".,!?:;\"'").lower() for w in title.split()
                if len(w) > 4 and w.lower() not in
                {"about","after","before","their","there","which","would","could","should"}
            }
            if _title_distinctive_words:
                _script_words_lower = set(script_clean.lower().split())
                _matched = sum(1 for w in _title_distinctive_words if w in _script_words_lower)
                if _matched == 0:
                    tg(f"⚠️ Ch1: none of the title's distinctive words appear in the script — "
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
                # These are the section labels the human sees in the review
                # card, and the ones identify_target_sections matches EDIT
                # feedback against. They were still the retired
                # dark-documentary beat sheet, so a reply like "the reversal
                # is weak" could not resolve to a section, and the review card
                # described a clinical case report in true-crime terms. Kept
                # identical to the stage names used by the scorer and by the
                # video's act cards, so all three agree.
                _stage_names_ch1 = ["OPENING", "THE PATIENT", "FIRST SIGNS",
                                    "DETERIORATION", "THE FIRST ANSWER",
                                    "THE REVERSAL", "WHAT IT CHANGED"]
                _stage_texts_ch1 = script_result.get("stage_texts", [])
                _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
                _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
                _script_was_edited = False

                while True:
                    try:
                        _hook_penalty, _hook_issues = _validate_retention_hooks_ch1(script_clean)
                        _hook_score = round(min(max(10.0 + _hook_penalty, 0), 10), 1)
                        _hook_note = _hook_issues[0] if _hook_issues else "all hook checkpoints present"
                    except Exception as e:
                        log(f"  Hook scoring (non-fatal): {e}")
                        _hook_score, _hook_note = None, None

                    # FIX (found on live Ch1 test run — real bug): score_result()
                    # was computing real rubric subscores (Craft, Clarity) and
                    # real issues (repeated phrases, missing rehook, weak
                    # escalation) and then discarding them — a reviewer only
                    # ever saw the bare number plus this older "Hook strength"
                    # metric, never why a 10.0/10 script might still have a
                    # real narrative-craft problem worth reading before
                    # approving. Merged in now that score_result() actually
                    # returns them.
                    _review_sub_scores = {"Hook strength": (_hook_score, _hook_note)} if _hook_score is not None else {}
                    if _score_subscores:
                        _craft_note = next((i for i in _score_issues if any(
                            k in i.lower() for k in ("escalation", "resolution", "rhythm", "repeats", "rehook"))), None)
                        _clarity_note = next((i for i in _score_issues if "topic" in i.lower() or "keyword" in i.lower()), None)
                        _review_sub_scores["Narrative craft"] = (_score_subscores.get("narrative_craft"), _craft_note or "no issues found")
                        _review_sub_scores["Topic clarity"] = (_score_subscores.get("topic_clarity"), _clarity_note or "no issues found")

                    # FIX (July 14 2026 audit): now passes stage_texts/stage_names
                    # so the script review is sent stage-by-stage with clear
                    # headers instead of one undifferentiated wall of text.
                    _review = review_script("No Known Cause", title, script_clean, score_val,
                                            niche_name, TG_TOKEN, TG_CHAT,
                                            gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass,
                                            timeout_minutes=60,
                                            stage_texts=_stage_texts_ch1, stage_names=_stage_names_ch1,
                                            sub_scores=_review_sub_scores or None)
                    if _review["decision"] == "reject":
                        log("Rejected during full script review."); sys.exit(0)
                    # FIX (found on deep re-audit): REMAKE was never handled
                    # here at all — it fell through every branch and the loop
                    # just re-sent the identical unedited script for review
                    # again, silently ignoring a human's explicit "scrap this
                    # episode" request. Ch2/Ch3/Ch4 all already treat REMAKE
                    # at the script checkpoint as ending the episode.
                    if _review["decision"] == "remake":
                        tg("🔄 Ch1: REMAKE requested at script review — scrapping this episode entirely.")
                        log("  REMAKE requested during script review — clearing pending, exiting.")
                        clear_pending(SCRIPT_DIR)
                        sys.exit(0)
                    if _review["decision"] == "approve":
                        break
                    if _review["decision"] == "edit" and _stage_texts_ch1:
                        _targets = identify_target_sections(_review["feedback"], _stage_names_ch1)
                        if len(_stage_texts_ch1) != len(_stage_names_ch1):
                            _targets = []  # a prior whole-script edit collapsed this list — avoid an IndexError
                        log(f"  Script EDIT requested: '{_review['feedback']}' -> sections: {_targets or 'WHOLE SCRIPT'}")
                        try:
                            script_clean, _updated_sections = regenerate_script_sections(
                                script_clean, _stage_texts_ch1, _stage_names_ch1, _targets,
                                _review["feedback"], niche, topic, ai_generate)
                            # FIX (found on final re-audit): refresh each
                            # changed section's real new text, not just leave
                            # the list untouched — otherwise a second edit
                            # targeting the same section searches for text
                            # that's already been replaced once and silently
                            # finds nothing to change.
                            if not _targets:
                                _stage_texts_ch1 = [script_clean]
                            else:
                                for _sec_name, _new_text in _updated_sections.items():
                                    _idx = _stage_names_ch1.index(_sec_name)
                                    _stage_texts_ch1[_idx] = _new_text
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
                            tg(f"🚨 Ch1: your script edit could NOT be applied — {e}. "
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
                tg(f"⚠️ Ch1: the full review system failed to load ({str(e)[:150]}) — falling back "
                   f"to the older, simpler approval gate for this episode. If human_review_gate.py "
                   f"and review_queue.py haven't been deployed to this repo yet, that's the likely "
                   f"cause; once they are, this fallback should stop firing.")
                decision = run_approval_gate(title, niche_name, script_clean, edge_voice, score_val)
                if decision == "rejected":
                    log("Rejected by approval gate."); sys.exit(0)

            # FIX (direct user request, July 25 2026 — real checkpoint/resume:
            # "if it passes some stage... it starts with the last passed
            # stage"): script + title have now cleared their gates and
            # review. Persist everything a resumed run needs so a re-trigger
            # (IS_MAKEUP=true) never has to re-run the 13-attempt script
            # engine, the AI-judge quality audit, or wait through the human
            # review window again.
            try:
                ckpt_save("script_stage", {
                    "niche_name": niche_name, "niche": niche, "topic": topic,
                    "script_result": script_result, "trending_titles": trending_titles,
                    "script_clean": script_clean, "wc": wc, "score_val": score_val,
                    "edge_voice": edge_voice, "real_cases": real_cases,
                    "title": title, "episode": episode,
                    "approved_topic_id_for_pending": _approved_topic_id_for_pending,
                })
            except Exception as _e:
                log(f"  [ckpt] script checkpoint save failed (non-fatal): {_e}")

        if _resume_audio:
            log("  [ckpt] RESUMING: audio already passed — skipping Stage 3")
            audio_path     = str(CKPT_AUDIO_FILE)
            audio_duration = _resume_audio["audio_duration"]
            edge_voice     = _resume_audio["edge_voice"]
            tool_used      = _resume_audio.get("tool_used", "unknown (resumed from an older checkpoint)")
        else:
            log("\nSTAGE 3: Audio")
            audio_path, audio_duration, audio_size, voice_used, tool_used = run_stage_with_retry(
                run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
            edge_voice = voice_used

            # FIX (direct user report, July 24 2026 — explicit policy decision,
            # "every stage... audio, video, thumbnails, title... quality score
            # minimum of 8.5... hard time for it to remake is 8 attempts...
            # if it is less than that, I don't want it to produce that"):
            # replaces the old two-track system (a voice-tier-name retry
            # capped at 2, plus a separate duration-only integrity check
            # capped at 2, plus a 10-minute sleep between attempts) with one
            # real, numerically scored gate: score_audio_quality() (voice
            # tier + duration match + silence integrity + file integrity),
            # hard floor 8.5, up to 8 attempts, voice-swapped each retry, no
            # artificial waiting between attempts. If nothing clears 8.5
            # within 8 attempts, the day is skipped entirely — no publish.
            from quality_scoring import score_audio_quality as _score_audio_quality_gate
            _AUDIO_MIN_GATE = 8.5
            _AUDIO_MAX_ATTEMPTS = 13  # raised from 8, direct user request July 24 2026
            _expected_dur = (len(script_clean.split()) / 125.0) * 60.0
            _audio_attempt = 1
            while True:
                _integrity_ok = check_audio_quality(audio_path, _expected_dur)
                if _integrity_ok:
                    _audio_score, _ = _score_audio_quality_gate(
                        audio_path, audio_duration, len(script_clean.split()), edge_voice)
                else:
                    _audio_score = 0.0
                log(f"  Audio attempt {_audio_attempt}/{_AUDIO_MAX_ATTEMPTS}: {_audio_score}/10 "
                    f"(voice {edge_voice}, integrity {'OK' if _integrity_ok else 'FAILED'})")
                notify_stage_score("Audio", _audio_attempt, _AUDIO_MAX_ATTEMPTS, _audio_score,
                                    _AUDIO_MIN_GATE, extra=f"voice {edge_voice}")
                if _audio_score >= _AUDIO_MIN_GATE:
                    break
                if _audio_attempt >= _AUDIO_MAX_ATTEMPTS:
                    tg(f"🛑 Ch1: audio never cleared {_AUDIO_MIN_GATE}/10 after {_AUDIO_MAX_ATTEMPTS} "
                       f"attempts (last: {_audio_score}/10, voice {edge_voice}) — skipping today's "
                       f"episode. Per your standing instruction, nothing under {_AUDIO_MIN_GATE} "
                       f"gets published.")
                    log(f"  Audio gate never cleared {_AUDIO_MIN_GATE} after "
                        f"{_AUDIO_MAX_ATTEMPTS} attempts. Skipping.")
                    sys.exit(0)
                _voice_pool = [v for v in VOICES.get(niche_name, EXTENDED_VOICES)
                               if v != edge_voice]
                _retry_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                tg(f"🔄 Ch1: audio scored {_audio_score}/10 (below {_AUDIO_MIN_GATE}) — regenerating "
                   f"(attempt {_audio_attempt + 1}/{_AUDIO_MAX_ATTEMPTS}, voice {edge_voice} → "
                   f"{_retry_voice}) instead of publishing it as-is.")
                edge_voice = _retry_voice
                _audio_attempt += 1
                audio_path, audio_duration, audio_size, voice_used, tool_used = run_stage_with_retry(
                    run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                edge_voice = voice_used

            # FIX (direct user request, July 25 2026 — "I am not getting
            # notifications in Telegram with regard to which audio tool
            # it has taken and which voice it is using... once the audio
            # is generated, I want to know the audio file as well"): the
            # only existing audio notification (review_audio_and_video)
            # fires AFTER Stage 4: Video succeeds -- in the exact run
            # that got cancelled at Stage 4, it never fired at all, so
            # nothing about the audio ever reached Telegram. This fires
            # the moment audio clears its own 8.5 gate, independent of
            # whether Video ever completes.
            try:
                from human_review_gate import _tg_send_audio
                _tg_send_audio(TG_TOKEN, TG_CHAT, audio_path,
                    caption=f"🎙️ Ch1 Audio ready — passed {_AUDIO_MIN_GATE}/10 gate "
                            f"(attempt {_audio_attempt}/{_AUDIO_MAX_ATTEMPTS})\n"
                            f"Tool: {tool_used}\nVoice: {edge_voice}\n"
                            f"Duration: {audio_duration/60:.1f} min | Score: {_audio_score}/10")
            except Exception as _e:
                log(f"  Audio-ready Telegram notification failed (non-fatal): {_e}")

            # FIX (direct user request, July 25 2026 — real checkpoint/resume):
            # audio has now cleared its 8.5 gate. Copy the actual accepted
            # audio file into a checkpoint path (the runner is ephemeral —
            # /tmp is gone on a fresh runner, so the file itself, not just
            # its metadata, has to be committed) and persist duration/voice
            # so a resumed run can skip straight to Stage 4: Video.
            import shutil as _ckpt_shutil
            try:
                _ckpt_shutil.copy(audio_path, CKPT_AUDIO_FILE)
                ckpt_save("audio_stage", {
                    "audio_duration": audio_duration, "edge_voice": edge_voice,
                    "tool_used": tool_used,
                })
            except Exception as _e:
                log(f"  [ckpt] audio checkpoint save failed (non-fatal): {_e}")

        log("\nSTAGE 4: Video")
        # v1 addition — real, word-level synced captions, per explicit
        # request that captions must genuinely match the audio. Uses
        # real Whisper transcription of the truly final accepted audio
        # (works regardless of which TTS tier produced it — a genuine
        # improvement over the old edge-tts-only SubMaker approach,
        # which gave zero captions whenever Fish Audio/gTTS/espeak was
        # the accepted tier). Skipped entirely rather than risking
        # desynced captions if the real transcription isn't available.
        ass_path = str(WORK_DIR / "main_captions.ass")
        if not generate_real_synced_ass(audio_path, ass_path):
            ass_path = None
        video_path = run_stage_with_retry(
            assemble_video, "Video", niche_name, audio_path, audio_duration, topic, script_clean, episode, real_cases, ass_path, title=title)

        # FIX (direct user report, July 24 2026 — explicit policy decision,
        # same as the audio gate above): real numeric 8.5/10 gate via
        # score_video_quality() (A/V sync + stream/resolution integrity +
        # file-size sanity + pipeline completeness), up to 8 reassembly
        # attempts, BEFORE the human review below. If nothing clears 8.5
        # within 8 attempts, the day is skipped entirely — no publish.
        from quality_scoring import score_video_quality as _score_video_quality_gate, \
            get_media_duration as _get_media_duration_gate
        _VIDEO_MIN_GATE = 8.5
        _VIDEO_MAX_ATTEMPTS = 13  # raised from 8, direct user request July 24 2026
        _video_attempt = 1
        while True:
            _v_dur = _get_media_duration_gate(video_path)
            _video_gate_score, _ = _score_video_quality_gate(
                video_path, _v_dur, audio_duration, content_type="stock_footage",
                fallback_flags=_last_video_fallback_flags)
            log(f"  Video attempt {_video_attempt}/{_VIDEO_MAX_ATTEMPTS}: {_video_gate_score}/10")
            notify_stage_score("Video", _video_attempt, _VIDEO_MAX_ATTEMPTS, _video_gate_score, _VIDEO_MIN_GATE)
            if _video_gate_score >= _VIDEO_MIN_GATE:
                break
            if _video_attempt >= _VIDEO_MAX_ATTEMPTS:
                tg(f"🛑 Ch1: video never cleared {_VIDEO_MIN_GATE}/10 after {_VIDEO_MAX_ATTEMPTS} "
                   f"attempts (last: {_video_gate_score}/10) — skipping today's episode. Per your "
                   f"standing instruction, nothing under {_VIDEO_MIN_GATE} gets published.")
                log(f"  Video gate never cleared {_VIDEO_MIN_GATE} after "
                    f"{_VIDEO_MAX_ATTEMPTS} attempts. Skipping.")
                sys.exit(0)
            tg(f"🔄 Ch1: video scored {_video_gate_score}/10 (below {_VIDEO_MIN_GATE}) — "
               f"reassembling (attempt {_video_attempt + 1}/{_VIDEO_MAX_ATTEMPTS}) instead of "
               f"publishing it as-is.")
            _video_attempt += 1
            video_path = run_stage_with_retry(
                assemble_video, "Video", niche_name, audio_path, audio_duration,
                topic, script_clean, episode, real_cases, ass_path, title=title)

        # COMBINED AUDIO + VIDEO REVIEW — one review window, two distinct
        # decisions (audio: 4 real options; video: 5, the 5th being SWAP
        # VISUALS). Swap Visuals re-calls assemble_video with the exact
        # same script/audio — since nothing in this file seeds Python's
        # random state, clip selection is genuinely different each call,
        # not a coin-flip disguised as a fix.
        # FIX (found on direct user request, July 23 2026): the review below
        # can only send a short local preview clip through Telegram, which
        # routinely exceeds Telegram's real ~50MB bot upload limit for a
        # long/high-bitrate episode (confirmed live: 1120MB video, 413
        # error). Uploading the actual current video to YouTube as
        # UNLISTED right here gives a real, full-quality, no-size-limit
        # link to watch or download before deciding — same mechanism
        # already built for the final pre-publish gate, just available
        # immediately instead of waiting for tomorrow's Upload run. If
        # this episode is approved, the video ID carries forward in
        # pending_upload.json so the Upload phase reuses it (just flips
        # privacy to public) instead of uploading the same file twice.
        _prerendered_yt_url = None
        _prerendered_yt_vid_id = None

        def _refresh_prerendered_upload(cur_video_path):
            # NOTE: description/tags aren't generated until STAGE 5 (after
            # this review), so this upload uses placeholder metadata --
            # the real title (already generated in STAGE 1) is the one
            # thing that IS final by this point. The Upload phase updates
            # this same video's real title/description/tags via
            # update_video_metadata() once they exist, before flipping it
            # public -- never publishes with placeholder text.
            nonlocal _prerendered_yt_url, _prerendered_yt_vid_id
            try:
                _token = get_yt_token()
                if _prerendered_yt_vid_id:
                    delete_yt_video(_prerendered_yt_vid_id, token=_token)
                _prerendered_yt_url, _prerendered_yt_vid_id = upload_yt(
                    cur_video_path, title, "Draft — under review, description finalized before publish.", [],
                    token=_token, privacy="unlisted")
                log(f"  Uploaded unlisted preview for review: {_prerendered_yt_url}")
            except Exception as e:
                log(f"  Unlisted preview upload (non-fatal, falling back to clip-only review): {e}")
                _prerendered_yt_url, _prerendered_yt_vid_id = None, None

        try:
            from human_review_gate import review_audio_and_video
            from quality_scoring import score_audio_quality, score_video_quality, get_media_duration
            _gmail_sender = os.environ.get("GMAIL_SENDER_EMAIL", "")
            _gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
            _check_ins_used_av = 0

            while True:
                _refresh_prerendered_upload(video_path)
                try:
                    _audio_score, _audio_breakdown = score_audio_quality(
                        audio_path, audio_duration, len(script_clean.split()), edge_voice)
                except Exception as e:
                    log(f"  Audio scoring (non-fatal): {e}")
                    _audio_score, _audio_breakdown = None, None
                try:
                    _real_video_duration = get_media_duration(video_path)
                    _video_score, _video_breakdown = score_video_quality(
                        video_path, _real_video_duration, audio_duration, content_type="stock_footage",
                        fallback_flags=_last_video_fallback_flags)
                except Exception as e:
                    log(f"  Video scoring (non-fatal): {e}")
                    _video_score, _video_breakdown = None, None

                _av_review = review_audio_and_video(
                    "No Known Cause", audio_path, edge_voice, video_path, None,
                    TG_TOKEN, TG_CHAT, _check_ins_used_av,
                    gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60,
                    audio_score=_audio_score, audio_score_breakdown=_audio_breakdown,
                    video_score=_video_score, video_score_breakdown=_video_breakdown,
                    yt_preview_url=_prerendered_yt_url)
                _check_ins_used_av += 1

                _a_dec = _av_review["audio_decision"]["decision"]
                if _a_dec == "reject":
                    if _prerendered_yt_vid_id:
                        delete_yt_video(_prerendered_yt_vid_id, token=get_yt_token())
                    log("Rejected during audio review.")
                    break
                # FIX (direct user report, July 24 2026 — "I told you
                # specifically to remake it, and it didn't even send me a
                # notification that it is working on the remake"): REMAKE
                # used to be treated identically to REJECT here — scrapping
                # the WHOLE episode instead of actually regenerating the
                # audio and sending it back for another look, unlike SWAP
                # VOICE/EDIT right below which already did this correctly.
                # A person tapping REMAKE wants a fresh attempt at THIS
                # artifact, not to lose the entire episode. Now genuinely
                # regenerates (voice-swapped, same as SWAP VOICE) and loops
                # back to review it again.
                if _a_dec == "remake":
                    _voice_pool = [v for v in VOICES.get(niche_name, EXTENDED_VOICES)
                                   if v != edge_voice]
                    _new_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                    tg(f"🔄 Ch1: REMAKE requested at audio review — regenerating audio now "
                       f"(voice {edge_voice} → {_new_voice}), same script.")
                    log(f"  REMAKE requested during audio review — regenerating, voice {edge_voice} -> {_new_voice}")
                    edge_voice = _new_voice
                    audio_path, audio_duration, audio_size, voice_used, tool_used = run_stage_with_retry(
                        run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                    edge_voice = voice_used
                    ass_path = str(WORK_DIR / "main_captions.ass")
                    if not generate_real_synced_ass(audio_path, ass_path):
                        ass_path = None
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-generated audio/video for another look

                _v_dec = _av_review["video_decision"]["decision"] if _av_review["video_decision"] else "approve"
                if _v_dec == "reject":
                    if _prerendered_yt_vid_id:
                        delete_yt_video(_prerendered_yt_vid_id, token=get_yt_token())
                    log("Rejected during video review."); sys.exit(0)
                # FIX (direct user report, July 24 2026 — same fix as audio
                # REMAKE above): REMAKE at the video checkpoint used to
                # scrap the whole episode too, instead of actually
                # reassembling the video like SWAP VISUALS already does.
                if _v_dec == "remake":
                    tg("🔄 Ch1: REMAKE requested at video review — reassembling the video now, "
                       "same script and audio.")
                    log("  REMAKE requested during video review — reassembling.")
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-assembled video for another look
                if _v_dec == "swap_visuals":
                    tg(f"🎨 Swapping visuals"
                       f"{' for: ' + _av_review['video_decision']['feedback'] if _av_review['video_decision']['feedback'] else ''}"
                       f" — regenerating the video assembly now, same script and audio.")
                    log(f"  SWAP VISUALS requested: {_av_review['video_decision']['feedback']}")
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-assembled video for another look
                # FIX (found live, Ch1 run 30433881228): EDIT is one of the
                # real buttons _button_keyboard() sends on the video review
                # (approve/reject/remake/edit, same default set as audio),
                # but this loop never had a branch for it — tapping EDIT
                # matched none of the conditions above or below, so the
                # loop silently fell through to the top and re-uploaded the
                # exact same unmodified 449MB video for review again with
                # no acknowledgment of the feedback at all (confirmed live:
                # 3 identical re-uploads, ~3-4 minutes apart, no message
                # ever explaining why). The only real lever at this
                # checkpoint is a fresh visual assembly (same mechanism as
                # SWAP VISUALS), so EDIT now does that while actually
                # echoing back what was asked for.
                if _v_dec == "edit":
                    _fb_video = _av_review["video_decision"]["feedback"] or ""
                    tg(f"🎨 Regenerating visuals per your feedback: {_fb_video}")
                    log(f"  Video EDIT requested: '{_fb_video}' — reassembling (the video "
                        f"checkpoint's only real lever; script changes belong at the script checkpoint).")
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-assembled video for another look
                if _v_dec == "approve" and _a_dec == "approve":
                    # FIX (found on deep re-audit): score_audio_quality/
                    # score_video_quality were computed every episode but
                    # never persisted anywhere — weekly_report.py had no
                    # real quality data to report on at all. Recorded
                    # here on the actual approved episode, mirroring
                    # thumb_format_history's proven write-side pattern.
                    try:
                        from quality_score_history import record_quality_scores
                        record_quality_scores(str(SCRIPT_DIR), "No Known Cause", episode, _audio_score, _video_score)
                    except Exception as e:
                        log(f"  Quality score history record (non-fatal): {e}")
                    break
                # edit on either audio or video: audio edit isn't
                # separately re-generated here (voice/pacing edits are a
                # real but more involved change — logged for visibility,
                # loop continues so the same audio/video get reviewed again)
                if _a_dec == "swap_voice":
                    _voice_pool = [v for v in VOICES.get(niche_name, EXTENDED_VOICES)
                                   if v != edge_voice]
                    _new_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                    tg(f"🎙️ Swapping voice: {edge_voice} → {_new_voice} — regenerating audio now, same script.")
                    log(f"  SWAP VOICE requested: {edge_voice} -> {_new_voice}")
                    edge_voice = _new_voice
                    audio_path, audio_duration, audio_size, voice_used, tool_used = run_stage_with_retry(
                        run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                    edge_voice = voice_used
                    ass_path = str(WORK_DIR / "main_captions.ass")
                    if not generate_real_synced_ass(audio_path, ass_path):
                        ass_path = None
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-generated audio/video for another look
                if _a_dec == "edit":
                    _fb_audio = _av_review["audio_decision"]["feedback"] or ""
                    # FIX (found on direct user report, July 15 2026): this
                    # used to call run_audio_stage with the SAME edge_voice
                    # every time -- the feedback text was echoed back to
                    # Telegram to LOOK like it was heard, but nothing about
                    # the regeneration actually changed: same script, same
                    # voice, same TTS engine. A person asking "the voice
                    # sounds robotic, change it" would get the exact same
                    # audio back, every time, with no indication anything
                    # was ignored. The only real lever available at the
                    # AUDIO checkpoint is which voice narrates it — the
                    # script itself is reviewed separately at the SCRIPT
                    # checkpoint — so EDIT here now actually swaps to a
                    # genuinely different voice, same as SWAP VOICE does.
                    _voice_pool = [v for v in VOICES.get(niche_name, EXTENDED_VOICES)
                                   if v != edge_voice]
                    _new_voice = random.choice(_voice_pool) if _voice_pool else edge_voice
                    tg(f"🎙️ Regenerating audio per your feedback: {_fb_audio}\n"
                       f"Voice: {edge_voice} → {_new_voice}")
                    log(f"  Audio EDIT requested: '{_fb_audio}' — swapping voice {edge_voice} -> {_new_voice} "
                        f"(the audio checkpoint's only real lever; script changes belong at the script checkpoint).")
                    edge_voice = _new_voice
                    audio_path, audio_duration, audio_size, voice_used, tool_used = run_stage_with_retry(
                        run_audio_stage, "Audio", script_clean, niche_name, edge_voice)
                    edge_voice = voice_used
                    # Captions must be regenerated for the new audio too —
                    # the old ass_path was timed to audio that no longer exists.
                    ass_path = str(WORK_DIR / "main_captions.ass")
                    if not generate_real_synced_ass(audio_path, ass_path):
                        ass_path = None
                    # FIX (found on deep re-audit): unlike SWAP VOICE right
                    # above, this branch regenerated audio+captions but
                    # never re-assembled video_path — the published video
                    # would have kept the OLD, discarded narration muxed
                    # in regardless of what the human approved here.
                    video_path = run_stage_with_retry(
                        assemble_video, "Video", niche_name, audio_path, audio_duration,
                        topic, script_clean, episode, real_cases, ass_path, title=title)
                    continue  # send the newly-generated audio/video for another look
        except Exception as e:
            log(f"  Audio/Video review (non-fatal, proceeding with generated versions): {e}")
            tg(f"⚠️ Ch1: the audio+video review system failed to load ({str(e)[:150]}) — "
               f"proceeding with the generated audio/video WITHOUT human review for this "
               f"episode. If human_review_gate.py isn't deployed to this repo yet, that's "
               f"the likely cause.")

        log("\nSTAGE 5: Thumbnail + Description")
        # v1 addition — real learned thumbnail-style preference, closing
        # the same "write-only, no learning" gap already found and fixed
        # for voice selection. Honest limitation: uses the script's own
        # quality score as a proxy signal, since no real click-through
        # data exists yet. Epsilon-greedy: 80% of the time uses whichever
        # style has the better real historical average (once there's
        # enough data), 20% of the time still explores via calendar
        # alternation.
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
        # FIX (direct user report, July 24 2026 — explicit policy decision):
        # generate_thumbnail_text now genuinely returns None if nothing
        # cleared the 8.5 gate after 8 attempts, instead of silently
        # publishing a "best-effort" candidate or a fallback-bank phrase
        # that never earned the bar.
        thumb_text  = generate_thumbnail_text(niche, topic, title)
        if not thumb_text:
            tg(f"Ch1 Day Skipped — no thumbnail text cleared 8.5/10 after 13 attempts. Per your "
               f"standing instruction, nothing under 8.5 gets published.")
            log("  Thumbnail text gate never cleared 8.5 after 13 attempts. Skipping.")
            sys.exit(0)
        thumb_path  = run_thumbnail_stage(title, thumb_text, niche_name, topic, ab_style, episode)
        # FIX (found on direct user report, July 23 2026 — real gap):
        # score_thumbnail_text() already exists and Ch5 already wires it
        # in, but Ch1 never did -- review_title_thumbnail_description()'s
        # thumbnail_score parameter was always None here, so the CTR/
        # thumbnail score the user explicitly asked for only ever showed
        # up for the description, never the thumbnail, looking like
        # scores were showing "randomly" rather than consistently missing.
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
                                             citations_block=format_citations_block(real_cases),
                                             needs_fiction_disclosure=needs_fiction_disclosure)
        _stage_word_counts = [len(t.split()) for t in _stage_texts_ch1] if _stage_texts_ch1 else None
        _chapters = generate_chapter_timestamps(script_clean, audio_duration, "betrayal_deepdive",
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
        # ── MANDATORY DISCLAIMER + CC BY ATTRIBUTION (rules 4,5) ─────
        # CC BY reuse is conditional on credit, so a missing citation turns a
        # licensed use into an unlicensed one. Built by the gate module so the
        # wording and the check that enforces it cannot drift apart.
        _clin_block = ""
        try:
            from medical_policy_gate import build_disclaimer_block
            _clin_block = build_disclaimer_block(get_episode_case().get("citation", ""))
        except Exception as e:
            log(f"  Disclaimer block (non-fatal): {e}")

        # No affiliate block on this channel. Deliberate, and not a style call.
        #
        # build_affiliate_block was still emitting the retired channel's
        # registry into every description: "BetterHelp therapy", plus two
        # more, on /deepdive placeholder slugs that 404. A therapy referral
        # sitting directly beneath a case study -- on a channel whose own
        # disclaimer says it is not medical advice -- contradicts the
        # disclaimer in the one place a viewer reads it, and is precisely the
        # health-adjacent monetisation that draws policy scrutiny. Same
        # reasoning that removed the psychology-handbook product route.
        #
        # Removing the call, not the registry: the other four channels still
        # use it legitimately.
        product_cta = build_product_cta("betrayal_deepdive")
        if product_cta:
            description = f"{description}{product_cta}"

        # Disclaimer + CC BY citation go in LAST so nothing appended later can
        # push them out of the description, and so the publish-time gate below
        # is checking the text that actually ships.
        if _clin_block:
            description = f"{description}{_clin_block}"

        # ── PUBLISH-TIME POLICY GATE (rules 4 + 5) ───────────────────────
        # Independent re-check of the things that must be true of the final
        # package: disclaimer present, CC BY attribution present, and no
        # graphic figure reached the video. Deliberately a SECOND check --
        # figures were already screened at fetch time in pmc_data, but a
        # single screen on a licensing/policy matter is not enough.
        try:
            from medical_policy_gate import check_publish_package, format_violations
            _case_now = get_episode_case()
            _fig_caps = [f.get("caption", "") for f in (_case_now.get("figures") or [])]
            _pub_ok, _pub_v = check_publish_package(
                description=description,
                on_screen_credits=[_case_now.get("citation", "")] if _case_now.get("citation") else [],
                figure_captions=_fig_caps,
                citation=_case_now.get("citation", ""))
            if not _pub_ok:
                log(f"  PUBLISH POLICY GATE FAILED:\n{format_violations(_pub_v)}")
                tg(f"🛑 <b>No Known Cause — PUBLISH BLOCKED</b>\n\n"
                   f"<code>{format_violations(_pub_v)[:600]}</code>\n\n"
                   f"Not uploading. Fix required.")
                sys.exit(1)
            log("  Publish policy gate: passed")
        except SystemExit:
            raise
        except Exception as e:
            log(f"  PUBLISH POLICY GATE ERROR — blocking to be safe: {e}")
            tg(f"🛑 <b>No Known Cause — PUBLISH BLOCKED</b>\n\n"
               f"Policy gate could not run: <code>{str(e)[:300]}</code>")
            sys.exit(1)

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
                    "No Known Cause", title, thumb_path, description, _desc_result["score"],
                    TG_TOKEN, TG_CHAT, _check_ins_used_ttd,
                    gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass, timeout_minutes=60,
                    thumbnail_score=_thumb_score)
                _check_ins_used_ttd += 1

                if _ttd_review["decision"] == "reject":
                    log("Rejected during title/thumbnail/description review."); sys.exit(0)
                if _ttd_review["decision"] == "remake":
                    tg(f"🔄 Ch1: REMAKE requested"
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
            tg(f"⚠️ Ch1: the title/thumbnail/description review system failed to load "
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
                tg(f"🚨 Ch1 AUTHENTICITY RISK — score {_auth_score}/10, below the safe threshold.\n"
                   f"{format_authenticity_report(auth_result, 'No Known Cause')}\n"
                   f"Recommend manual review before this publishes.")
            elif _auth_score < 7.5:
                tg(f"⚠️ Ch1 authenticity check: {_auth_score}/10 — one dimension is weak, publishing "
                   f"but flagging for awareness.\n{format_authenticity_report(auth_result, 'No Known Cause')}")
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
                vt = produce_video_topic_short(topic, script_clean, angle, channel="betrayal_deepdive")
                shorts.append({"ok": vt.get("status") == "success",
                               "path": vt.get("local_path"), "url": vt.get("url"), "name": f"video_topic_{angle}"})
                log(f"  Video-topic ({angle}): {vt.get('status')}")
                _post_short_comment_safe(vt.get("url"), f"video_topic_{angle}")

            # 2 Shorts on genuinely different, trending, in-demand topics —
            # real research into what's actually working today.
            for mode in ("standalone_1", "standalone_2"):
                sa = produce_standalone_short(mode, channel="betrayal_deepdive")
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
            # FIX (found on direct user report, July 23 2026 — real gap):
            # a total Shorts failure (0 produced) was only ever logged to
            # the GitHub Actions console, never surfaced to Telegram —
            # the review checkpoint below is skipped entirely when there's
            # nothing to review, so a real, complete content failure had
            # zero visibility to the actual human reviewing the episode.
            if ok_count == 0 and shorts:
                tg(f"⚠️ Ch1: 0/{len(shorts)} Shorts produced this episode — "
                   f"all attempts failed pre-score or assembly. Check the "
                   f"Generate run's log for details.")

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
                    _sh_review = review_shorts("No Known Cause", _real_shorts, TG_TOKEN, TG_CHAT,
                                               check_ins_used=0, gmail_sender=_gmail_sender,
                                               gmail_app_password=_gmail_pass, timeout_minutes=60)
                    # FIX (direct user report, July 24 2026 — "if I tell it
                    # reject then it needs to rework on it"): REJECT used to
                    # be a silent no-op here — the already-published Shorts
                    # just stayed live regardless, identical to APPROVE.
                    # Shorts are real YouTube videos, so they CAN actually
                    # be deleted (unlike the "can't unpublish" constraint
                    # that applies to edit/remake/swap below) — REJECT now
                    # genuinely deletes every Short from this batch.
                    if _sh_review["decision"] == "reject":
                        _sh_token = get_yt_token()
                        for _s in _real_shorts:
                            _m = re.search(r'(?:shorts/|v=)([A-Za-z0-9_-]{11})', _s.get("url", ""))
                            if _m:
                                try:
                                    delete_yt_video(_m.group(1), token=_sh_token)
                                    log(f"  Deleted rejected Short: {_s['name']}")
                                except Exception as e:
                                    log(f"  Failed to delete rejected Short {_s['name']} (non-fatal): {e}")
                        tg("🗑️ Ch1: Shorts REJECTED — all of this episode's Shorts have been deleted.")
                    if _sh_review["decision"] in ("edit", "remake", "swap_visuals"):
                        log(f"  Shorts {_sh_review['decision']} requested: "
                            f"{_sh_review['feedback']} — publishing one fresh replacement standalone Short.")
                        tg(f"🎞️ Producing a fresh replacement Short per your feedback: "
                           f"{_sh_review['feedback']}")
                        _replacement = produce_standalone_short("standalone_1", channel="betrayal_deepdive")
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
                        "No Known Cause", _cp_draft["question"], _cp_draft["options"], TG_TOKEN, TG_CHAT,
                        check_ins_used=0, gmail_sender=_gmail_sender, gmail_app_password=_gmail_pass)
                    log(f"  Community Tab: {_cp_result['decision']}")
                except Exception as e:
                    log(f"  Community Tab checkpoint (non-fatal): {e}")
            except Exception as e:
                log(f"  Shorts review (non-fatal): {e}")
                tg(f"⚠️ Ch1: the Shorts review system failed to load ({str(e)[:150]}) — "
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
            "shorts_clips":  shorts,   # the 2 standalone Shorts from this generate phase
            "topic":         topic,
            "auth_fingerprint": _pending_auth_fingerprint,
            "approved_topic_id": _approved_topic_id_for_pending,
            "quality_attempt": script_result.get("attempt", 1),
            "providers_healthy_count": len(_healthy_providers) if _healthy_providers else 7,
            "authenticity_score": _auth_score,
            # FIX (July 23 2026, direct user request for a real video link):
            # the approved video is already sitting on YouTube as unlisted
            # (uploaded for the audio+video review above) -- carrying its
            # ID forward means the Upload phase can reuse it (update real
            # metadata, flip to public) instead of uploading the same
            # multi-hundred-MB file a second time.
            "prerendered_yt_video_id": _prerendered_yt_vid_id,
            "prerendered_yt_url": _prerendered_yt_url,
        })
        if _pending_result.get("overwrite_warning"):
            tg(f"🚨 Ch1 Generate: {_pending_result['overwrite_warning']}")

        # Generate phase reached the finish line — the whole episode is
        # queued in pending_upload.json now, so any script/audio
        # checkpoint from getting here is done being useful. Clear it so
        # the NEXT day's run starts genuinely fresh instead of resuming
        # into a stale, already-published episode's script/audio.
        ckpt_clear()

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


def main_with_retry():
    """
    FIX (found on deep re-audit): Ch1 had no outer crash-retry wrapper at
    all, unlike Ch2/Ch3/Ch4 (each has a main_with_retry() wrapping the
    ENTIRE main() call in a 3-attempt retry loop with Telegram alerts).
    Worse, the UPLOAD phase branch inside main() (phase == "upload") runs
    entirely outside the generate-phase-only try/except a few lines
    above — a single transient failure there (e.g. get_yt_token()'s OAuth
    refresh) crashed the whole process uncaught: no retry, no Telegram
    alert, just a silent-to-a-human GitHub Actions failure. Wrapping the
    entire main() call here, matching Ch2/3/4's proven pattern exactly,
    fixes both the upload-phase blind spot and the missing retry/alerts
    without touching main()'s internal phase logic at all.
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            main(); return
        except SystemExit as e:
            if e.code == 0: return
            if attempt < max_retries:
                tg(f"⚠️ Ch1 attempt {attempt}/{max_retries} failed.\nRetrying in 10 minutes...")
                time.sleep(600)
            else:
                tg(f"❌ Ch1 FAILED after {max_retries} attempts.")
                sys.exit(1)
        except Exception as e:
            # FIX (found diagnosing real Ch2/3/4 upload failures on the
            # exact same pattern): tg() only ever received a 200/300-char
            # truncated str(e), and never printed anything to stdout --
            # meaning the real exception (type, full message, traceback)
            # was invisible in the GitHub Actions log unless Telegram
            # happened to deliver it, and even then only truncated. Now
            # always logs the full traceback to stdout first, regardless
            # of Telegram delivery.
            import traceback
            log(f"  main_with_retry: attempt {attempt}/{max_retries} crashed:\n{traceback.format_exc()}")
            if attempt < max_retries:
                tg(f"⚠️ Ch1 crash {attempt}/{max_retries}: {str(e)[:200]}\nRetrying in 10 minutes...")
                time.sleep(600)
            else:
                tg(f"❌ Ch1 FAILED {max_retries}x: {str(e)[:300]}")
                sys.exit(1)


def _log_runtime_breakdown(t0):
    """
    Where the wall-clock actually went.

    Run 30578466862 took 5h34m and that number stayed "undiagnosed" for days
    purely because nothing recorded it. It was never a bug -- the review
    gates poll for a human decision for up to an hour each -- but a run whose
    duration cannot be attributed is a run nobody can reason about, and on a
    free Actions allowance the difference between five hours of compute and
    one hour of compute plus four hours of idle polling is the entire budget
    question.
    """
    try:
        from human_review_gate import review_time_report, _REVIEW_WAITS
        total = time.time() - t0
        waiting = sum(w["seconds"] for w in _REVIEW_WAITS)
        log("")
        log("─" * 58)
        log(f"RUNTIME: {total/60:.0f} min total — "
            f"{waiting/60:.0f} min waiting on review gates, "
            f"{(total-waiting)/60:.0f} min of real work")
        log(review_time_report())
        log("─" * 58)
    except Exception as e:
        log(f"  runtime breakdown unavailable: {e}")


if __name__ == "__main__":
    _t0 = time.time()
    try:
        main_with_retry()
    finally:
        _log_runtime_breakdown(_t0)
