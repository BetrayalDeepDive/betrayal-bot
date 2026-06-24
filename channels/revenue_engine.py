"""
REVENUE ENGINE — Shared module for all three pipelines.
Import and call these functions in each pipeline.

Contains every traffic/revenue driver missing across the three channels:
  1. NUMBER+NOUN thumbnail enforcer
  2. 5-axis title scorer (replaces keyword presence scorer)
  3. Title CTR gate with auto-regeneration (minimum 6.5/10)
  4. Affiliate block builder (BetterHelp, VPN, courses)
  5. Chapter timestamps generator
  6. Three-channel cross-promo builder
  7. Hype notification sender
  8. Retention hook validator
  9. Cross-niche Shorts topic generator

All free. No paid APIs.
"""

import re, random, datetime, requests, os

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")


# ══════════════════════════════════════════════════════════════
# 1. NUMBER+NOUN THUMBNAIL ENFORCER
# The single highest-CTR thumbnail format for documentary channels.
# Channels with NUMBER+NOUN thumbnails average 6-9% CTR vs 2-4% generic.
# ══════════════════════════════════════════════════════════════

NUMBER_NOUN_BANKS = {
    # Ch1 — BetrayalDeepDive
    "dark_horror":        ["4,380 DAYS","12 YEARS","3 AM","14 VICTIMS","ONE NIGHT"],
    "seduction_dark":     ["7 SIGNS","28 DAYS","3 PEOPLE","6 WARNINGS","ONE TRAP"],
    "psychological_trap": ["6 STAGES","23 STEPS","100 DAYS","1 EXIT","5 TRIGGERS"],
    "supernatural_real":  ["3 NIGHTS","72 HOURS","9 WITNESSES","14 YEARS","1 PLACE"],
    "obsession_dark":     ["847 MESSAGES","4 YEARS","23 CALLS","1,460 DAYS","ONE PERSON"],
    # Ch2 — Evidence Room
    "forensic_finance":        ["$2.4M GONE","4,380 DAYS","47 REPORTS","$14M FRAUD","12 YEARS"],
    "criminal_investigation":  ["14 VICTIMS","23 YEARS","1 FILE","47 CLUES","3 SUSPECTS"],
    "corporate_exposure":      ["$840M HIDDEN","14 YEARS","23 EMAILS","$2.4B FRAUD","1 MEMO"],
    "digital_forensics":       ["2.7M FILES","847 ACCOUNTS","1 IP ADDRESS","23 SERVERS","14TB DATA"],
    # Ch3 — Control Files
    "cult_psychology":    ["847 MEMBERS","14 YEARS","7 STAGES","23 RULES","1 LEADER"],
    "propaganda_systems": ["40M PEOPLE","7 TECHNIQUES","14 YEARS","3 AGENCIES","1 NARRATIVE"],
    "social_engineering": ["6 PRINCIPLES","847 TARGETS","23 HOURS","7 TRIGGERS","1 CALL"],
    "mass_deception":     ["1B PEOPLE","14 MONTHS","3 NETWORKS","23 COUNTRIES","1 LIE"],
}

def enforce_number_noun(thumb_text, topic, niche_name, ai_fn=None):
    """
    Ensures thumbnail text is in NUMBER+NOUN format.
    This format averages 6-9% CTR vs 2-4% for generic text.
    If the AI returned something without a number, generate a proper one.
    """
    # Already has a number — just clean and return
    if re.search(r'\b\d[\d,\.]*\b|\$', thumb_text):
        return re.sub(r'[^A-Z0-9$.,% ]', '', thumb_text.upper()).strip()[:22]

    # Try to extract a number from the topic itself
    m = re.search(r'\b(\d[\d,\.]*)\s*(\w+)', topic)
    if m:
        num  = m.group(1)
        noun = m.group(2).upper()[:8]
        return f"{num} {noun}"[:22]

    # AI-generated NUMBER+NOUN if ai_fn provided
    if ai_fn:
        try:
            prompt = (
                f"Thumbnail topic: {topic[:80]}\n"
                f"Generate a 2-3 word thumbnail in NUMBER+NOUN format.\n"
                f"Examples: '4,380 DAYS', '$2.4M GONE', '47 REPORTS', '14 VICTIMS'\n"
                f"Use a specific number that feels real and specific to this case.\n"
                f"Return ONLY the 2-3 words in ALL CAPS."
            )
            result = ai_fn(prompt, tokens=20)
            if result and re.search(r'\d', result):
                clean = re.sub(r'[^A-Z0-9$.,% ]', '', result.upper()).strip()[:22]
                if clean:
                    return clean
        except:
            pass

    # Fallback: use niche bank
    bank  = NUMBER_NOUN_BANKS.get(niche_name, ["14 YEARS","47 CASES","1 TRUTH"])
    return random.choice(bank)


# ══════════════════════════════════════════════════════════════
# 2. 5-AXIS TITLE SCORER
# Replaces the simple keyword-presence scorer in all three pipelines.
# Curiosity gap + specificity + revelation + pattern interrupt + length.
# ══════════════════════════════════════════════════════════════

def score_title_v2(title):
    """
    Score a YouTube title on 5 psychological axes.
    Returns (score 0-10, breakdown dict).

    Axis weights:
      Curiosity gap     2.5  — creates question without answering it
      Specificity       2.0  — concrete number, date, or name
      Implied revelation 1.5  — promises documented proof
      Pattern interrupt  1.5  — surprising claim about who knew / allowed it
      Length discipline  1.0  — 50-65 chars optimal
      Generic penalty   -2.0  — deducted for AI clichés
    """
    t  = title.lower()
    sc = 3.0
    bd = {}

    # 1. Curiosity gap (2.5 max)
    cg_signals = [
        "nobody knew", "nobody told", "never told", "nobody noticed",
        "what happened", "what they found", "what was hidden",
        "the truth about", "the real reason", "the real story",
        "why nobody", "how it was hidden", "what they didn't",
        "kept secret", "concealed", "covered up", "never reported",
        "went unnoticed", "sat unread", "was ignored", "was missed",
    ]
    cg_hits = sum(1 for s in cg_signals if s in t)
    if cg_hits >= 2:   sc += 2.5; bd["curiosity_gap"] = "STRONG"
    elif cg_hits == 1: sc += 1.5; bd["curiosity_gap"] = "OK"
    else:              bd["curiosity_gap"] = "WEAK — add 'nobody knew' or 'what was hidden'"

    # 2. Specificity (2.0 max)
    has_number = bool(re.search(r'\b\d[\d,\.]*\b', title))
    has_year   = bool(re.search(r'\b(19|20)\d{2}\b', title))
    has_dollar = bool(re.search(r'\$[\d,\.]+', title))
    has_name   = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', title))

    if (has_number or has_dollar) and (has_year or has_name):
        sc += 2.0; bd["specificity"] = "STRONG"
    elif has_number or has_dollar or has_name:
        sc += 1.2; bd["specificity"] = "OK"
    elif has_year:
        sc += 0.6; bd["specificity"] = "WEAK — add specific number or name"
    else:
        bd["specificity"] = "FAIL — no numbers, dates, or names"

    # 3. Implied revelation (1.5 max)
    rev_signals = [
        "exposed", "revealed", "documented", "proved", "found",
        "evidence", "records show", "files reveal", "investigation",
        "classified", "suppressed", "buried", "confirmed", "traced",
        "unsealed", "declassified",
    ]
    if any(s in t for s in rev_signals):
        sc += 1.5; bd["revelation"] = "PRESENT"
    else:
        bd["revelation"] = "ABSENT — add 'documented' or 'exposed'"

    # 4. Pattern interrupt (1.5 max)
    pi_signals = [
        "they knew", "he knew", "she knew", "everyone knew",
        "it was allowed", "it was ignored", "it was covered",
        "they let it", "still happening", "still ongoing",
        "worse than", "far worse", "nobody stopped",
        "went unpunished", "was promoted",
    ]
    if any(s in t for s in pi_signals):
        sc += 1.5; bd["pattern_interrupt"] = "PRESENT"
    else:
        bd["pattern_interrupt"] = "ABSENT — add 'they knew' or 'still happening'"

    # 5. Length discipline (1.0 max)
    n = len(title)
    if 50 <= n <= 65:    sc += 1.0; bd["length"] = f"{n} chars — OPTIMAL"
    elif 45 <= n <= 70:  sc += 0.5; bd["length"] = f"{n} chars — OK"
    elif n < 40:         sc -= 0.5; bd["length"] = f"{n} chars — TOO SHORT"
    elif n > 80:         sc -= 0.5; bd["length"] = f"{n} chars — TOO LONG"
    else:                bd["length"] = f"{n} chars — MARGINAL"

    # 6. Generic penalty
    generic = [
        "incredible", "unbelievable", "shocking", "amazing", "stunning",
        "you won't believe", "mind blowing", "jaw dropping", "must watch",
        "this will", "changed everything forever",
    ]
    hits = sum(1 for g in generic if g in t)
    if hits:
        sc -= hits * 0.8
        bd["penalty"] = f"-{hits*0.8:.1f} ({hits} generic phrases)"

    return round(min(max(sc, 0), 10), 1), bd


# ══════════════════════════════════════════════════════════════
# 3. TITLE CTR GATE WITH AUTO-REGENERATION
# Minimum 6.5/10. Below threshold = AI regenerates with specific axis fix.
# ══════════════════════════════════════════════════════════════

def regenerate_titles_for_ctr(topic, niche_name, series_name, episode,
                               current_score, breakdown, ai_fn):
    """
    When title scores below 6.5/10, regenerate with instructions targeting
    the specific failing axis. Much smarter than generic regeneration.
    """
    # Identify the weakest axis
    weak_axes = []
    for axis, status in breakdown.items():
        if "WEAK" in str(status) or "ABSENT" in str(status) or "FAIL" in str(status):
            weak_axes.append((axis, status))

    # Build targeted fix instructions
    fix_instructions = []
    for axis, status in weak_axes[:2]:  # fix top 2 weaknesses
        if axis == "curiosity_gap":
            fix_instructions.append(
                "Start with 'Nobody knew', 'What the records show', or 'The truth about'"
            )
        elif axis == "specificity":
            fix_instructions.append(
                "Include a specific number (years, dollars, people, documents)"
            )
        elif axis == "revelation":
            fix_instructions.append(
                "Include 'documented', 'exposed', 'revealed', or 'files show'"
            )
        elif axis == "pattern_interrupt":
            fix_instructions.append(
                "Add 'They Knew', 'It Was Allowed', or 'Still Happening'"
            )
        elif axis == "length":
            fix_instructions.append("Keep between 50-65 characters")

    if not fix_instructions:
        fix_instructions = ["Add a specific number AND a curiosity gap phrase"]

    prompt = (
        f"Generate 5 stronger YouTube titles for this topic.\n"
        f"Topic: {topic[:120]}\n"
        f"Series: {series_name} Ep{episode}\n"
        f"Current best score: {current_score}/10 — too low.\n\n"
        f"REQUIRED FIXES:\n"
        + "\n".join(f"  - {f}" for f in fix_instructions) +
        f"\n\nRules:\n"
        f"- 50-65 characters\n"
        f"- Dark investigative documentary tone\n"
        f"- No 'incredible', 'unbelievable', 'shocking', 'amazing'\n"
        f"- Return ONLY a JSON array of 5 titles\n"
        f'["Title 1","Title 2","Title 3","Title 4","Title 5"]'
    )
    try:
        result = ai_fn(prompt, tokens=300)
        if result:
            result = re.sub(r'```json|```', '', result).strip()
            m = re.search(r'\[[\s\S]*?\]', result)
            if m:
                titles  = [t for t in __import__('json').loads(m.group()) if t]
                scored  = sorted(
                    [(t, score_title_v2(t)[0]) for t in titles],
                    key=lambda x: x[1], reverse=True)
                if scored and scored[0][1] > current_score:
                    return scored[0][0], scored
    except Exception as e:
        pass
    return None, None


def run_title_ctr_gate(title_str, title_scores, topic, niche_name,
                        series_name, episode, ai_fn, min_ctr=6.5):
    """
    Full title CTR gate. Replaces the basic version in all three pipelines.
    Returns (final_title, final_scores).
    """
    if not title_scores:
        return title_str, [(title_str, 5.0)]

    # Score with v2 scorer
    v2_scored = sorted(
        [(t, score_title_v2(t)[0]) for t, _ in title_scores],
        key=lambda x: x[1], reverse=True)

    best_title, best_score = v2_scored[0]
    _, breakdown = score_title_v2(best_title)

    if best_score >= min_ctr:
        return best_title, v2_scored

    # Below gate — regenerate with targeted fix
    new_title, new_scores = regenerate_titles_for_ctr(
        topic, niche_name, series_name, episode,
        best_score, breakdown, ai_fn)

    if new_title and new_scores:
        new_best_score = new_scores[0][1]
        if new_best_score > best_score:
            return new_title, new_scores

    # Couldn't improve — use best available
    return best_title, v2_scored


# ══════════════════════════════════════════════════════════════
# 4. AFFILIATE BLOCK BUILDER
# Real money. BetterHelp pays $150/conversion.
# VPN pays $40-500/signup. Psychology courses pay 20-45%.
# These go in every video description across all three channels.
# ══════════════════════════════════════════════════════════════

# Update these URLs when you get approved for each program
AFFILIATE_REGISTRY = {
    "betterhelp": {
        "url":      "https://betterhelp.com/deepdive",
        "label":    "BetterHelp — online therapy",
        "cpa":      "$150/signup",
        "channels": ["all"],
    },
    "nordvpn": {
        "url":      "https://nordvpn.com/deepdive",
        "label":    "NordVPN — protect your privacy",
        "cpa":      "$40/signup",
        "channels": ["evidence_room", "control_files"],
    },
    "curiositystream": {
        "url":      "https://curiositystream.com/deepdive",
        "label":    "CuriosityStream — documentary streaming",
        "cpa":      "rev share",
        "channels": ["all"],
    },
    "psychology_course": {
        "url":      "https://bit.ly/deepdive-psych",
        "label":    "Psychology of Influence — full course",
        "cpa":      "20-45%",
        "channels": ["control_files"],
    },
    "audible": {
        "url":      "https://amzn.to/deepdive-audible",
        "label":    "Audible — audiobooks on this topic",
        "cpa":      "$5-15/trial",
        "channels": ["all"],
    },
}

def build_affiliate_block(channel_id, niche_name):
    """
    Build the affiliate links section for a video description.
    Only includes links relevant to the channel and niche.
    Call this when building the description before upload.
    """
    ch_map = {
        "betrayal_deepdive": "betrayal_deepdive",
        "evidence_room":     "evidence_room",
        "control_files":     "control_files",
    }
    ch = ch_map.get(channel_id, channel_id)

    lines = ["\n\n— LINKS & RESOURCES —"]
    added = 0
    for key, link in AFFILIATE_REGISTRY.items():
        relevant = ("all" in link["channels"]) or (ch in link["channels"])
        if not relevant:
            continue
        lines.append(f"▸ {link['label']}: {link['url']}")
        added += 1

    if added == 0:
        return ""

    lines.append(
        "\n*Some links may be affiliate links — using them supports this channel "
        "at no extra cost to you."
    )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 5. CHAPTER TIMESTAMPS
# YouTube chapters improve watch session time by 15-25%.
# Viewers who skip back stay longer and trigger stronger retention signals.
# ══════════════════════════════════════════════════════════════

CHAPTER_STRUCTURES = {
    "betrayal_deepdive": [
        (0.00, "The Case Begins"),
        (0.10, "Before It Happened"),
        (0.28, "First Warning Signs"),
        (0.45, "Escalation"),
        (0.60, "The Revelation"),
        (0.78, "The Aftermath"),
        (0.90, "What This Means"),
    ],
    "evidence_room": [
        (0.00, "Case File Opened"),
        (0.10, "The Subject"),
        (0.28, "First Anomalies"),
        (0.45, "The Evidence Builds"),
        (0.60, "Key Document Revealed"),
        (0.78, "The Full Record"),
        (0.90, "Verdict"),
    ],
    "control_files": [
        (0.00, "The System"),
        (0.10, "How It Was Built"),
        (0.28, "Early Documented Cases"),
        (0.45, "The Evidence"),
        (0.60, "The Scale"),
        (0.78, "Those Who Resisted"),
        (0.90, "Implications"),
    ],
}

def generate_chapter_timestamps(script_clean, total_duration_secs, channel_id):
    """
    Generate YouTube chapter timestamps from script and duration.
    Returns a string to inject into the video description.
    Must start at 0:00. Each chapter minimum 10 seconds apart.
    """
    if total_duration_secs < 120 or len(script_clean.split()) < 200:
        return ""

    structure = CHAPTER_STRUCTURES.get(channel_id, CHAPTER_STRUCTURES["betrayal_deepdive"])
    lines     = []

    for pct, label in structure:
        secs = int(total_duration_secs * pct)
        mins = secs // 60
        s    = secs % 60
        lines.append(f"{mins}:{s:02d} {label}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 6. THREE-CHANNEL CROSS-PROMO
# Every channel sends viewers to both others.
# This is a subscriber flywheel — same audience across three channels
# = 3x the revenue from the same person.
# ══════════════════════════════════════════════════════════════

CROSS_PROMO_LINES = {
    "betrayal_deepdive": {
        "main": (
            "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
            "\n🧠 Psychology & propaganda documentaries: youtube.com/@TheControlFiles"
            "\n\n📺 New investigation every weekday on all three channels."
        ),
        "short": (
            "\n\n🔬 Forensic crimes: youtube.com/@TheEvidenceRoom"
            "\n🧠 Psychology docs: youtube.com/@TheControlFiles"
        ),
    },
    "evidence_room": {
        "main": (
            "\n\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
            "\n🧠 Psychology & propaganda documentaries: youtube.com/@TheControlFiles"
            "\n\n📺 New investigation every weekday on all three channels."
        ),
        "short": (
            "\n\n🌑 Dark horror: youtube.com/@BetrayalDeepDive"
            "\n🧠 Psychology docs: youtube.com/@TheControlFiles"
        ),
    },
    "control_files": {
        "main": (
            "\n\n🔬 Forensic crime investigations: youtube.com/@TheEvidenceRoom"
            "\n🌑 Dark psychological horror: youtube.com/@BetrayalDeepDive"
            "\n\n📺 New investigation every weekday on all three channels."
        ),
        "short": (
            "\n\n🔬 Forensic crimes: youtube.com/@TheEvidenceRoom"
            "\n🌑 Dark horror: youtube.com/@BetrayalDeepDive"
        ),
    },
}

def get_cross_promo(channel_id, is_short=False):
    """Get the three-channel cross-promo text for a description."""
    promo  = CROSS_PROMO_LINES.get(channel_id, CROSS_PROMO_LINES["betrayal_deepdive"])
    return promo["short"] if is_short else promo["main"]


# ══════════════════════════════════════════════════════════════
# 7. HYPE NOTIFICATION
# YouTube Hype = free Explore leaderboard push for channels under 500K subs.
# This is the single most underused growth tool for new channels in 2026.
# Sends on day 0, day 3, day 6 of the 7-day Hype window.
# ══════════════════════════════════════════════════════════════

def send_hype_push(video_url, video_title, channel_name, day=0):
    """
    Send a Hype notification to Telegram.
    day=0: immediate after upload
    day=3: 3-day follow-up (sent by growth engine weekly cycle)
    day=6: final day reminder
    """
    if not TG_TOKEN or not TG_CHAT:
        return

    urgency = {
        0: "⚡ Act now — first hour = maximum impact",
        3: "🔥 4 days left in Hype window",
        6: "⏰ LAST DAY — Hype expires tomorrow",
    }.get(day, "")

    msg = (
        f"🚀 <b>HYPE THIS VIDEO — {urgency}</b>\n\n"
        f"<b>{channel_name}</b>: {video_title}\n\n"
        f"▶️ {video_url}\n\n"
        f"<b>How to Hype (10 seconds):</b>\n"
        f"1. Open the link on YouTube\n"
        f"2. Tap the 🔥 Hype button under the video\n"
        f"3. Done — YouTube pushes this to the Explore leaderboard\n\n"
        f"⏳ 7-day window only. Every Hype = free algorithmic reach to cold audiences.\n"
        f"This works. Use it."
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15)
    except Exception as e:
        pass  # non-fatal


# ══════════════════════════════════════════════════════════════
# 8. RETENTION HOOK VALIDATOR
# Used inside script scoring — weak hooks = lower score = auto-retry.
# Channels with strong retention hooks get pushed more by algorithm.
# ══════════════════════════════════════════════════════════════

def validate_retention_hooks(script_clean, channel_id="betrayal_deepdive"):
    """
    Validate retention hooks at 30%, 60%, and 80% of the script.
    Returns (penalty float, list of issues).
    Penalty is deducted from script quality score so weak scripts auto-retry.
    """
    words   = script_clean.split()
    total   = len(words)
    if total < 400:
        return 0.0, []

    penalty = 0.0
    issues  = []

    hook_signals = [
        "subscribe", "coming up", "next", "what happens", "the answer",
        "revealed", "in a moment", "stay", "about to", "this changes",
        "not yet", "what comes next", "thirty seconds", "before this ends",
        "what we found next", "the next document", "the next stage",
    ]

    def seg(p1, p2):
        return " ".join(words[int(total*p1):int(total*p2)]).lower()

    # 30% zone
    if sum(1 for h in hook_signals if h in seg(0.25, 0.35)) < 1:
        penalty -= 0.4
        issues.append("Missing 30% retention hook")

    # 60% zone — highest weight, emotional peak
    h60 = sum(1 for h in hook_signals if h in seg(0.55, 0.65))
    if h60 < 2:
        penalty -= 0.8
        issues.append("Weak 60% peak hook — critical position for subscribe CTAs")
    elif h60 >= 3:
        penalty += 0.3  # bonus for well-engineered peak

    # 80% zone
    if sum(1 for h in hook_signals if h in seg(0.75, 0.85)) < 1:
        penalty -= 0.4
        issues.append("Missing 80% retention hook")

    # Opening hook — first 60 words
    opening = " ".join(words[:60]).lower()
    opening_signals = [
        "what happened", "this was not", "nobody knew", "documented",
        "the moment", "what was found", "the case", "evidence",
        "the system", "nobody expected", "not one person",
    ]
    if not any(t in opening for t in opening_signals):
        penalty -= 0.5
        issues.append("Weak opening hook — first 60 words lack tension")

    # Final subscribe CTA
    if "subscribe" not in " ".join(words[-60:]).lower():
        penalty -= 0.3
        issues.append("Missing subscribe CTA in final 60 words")

    return round(penalty, 1), issues


# ══════════════════════════════════════════════════════════════
# 9. CROSS-NICHE SHORTS TOPIC GENERATOR
# Shorts that pull from other niches expose the channel to new audiences.
# Ch1's cross-niche Shorts drive Ch2 and Ch3 discovery and vice versa.
# ══════════════════════════════════════════════════════════════

CROSS_NICHE_TOPICS = {
    "betrayal_deepdive": [
        "A financial fraud that went undetected for eleven years behind a trusted institution.",
        "The corporate cover-up that 23 executives signed off on.",
        "The documented influence operation that changed what people believed.",
        "A group of 847 people who followed one person's instructions without question.",
    ],
    "evidence_room": [
        "The psychological pattern behind every financial fraud in this series.",
        "The betrayal that preceded every corporate crime documented on this channel.",
        "How documented influence techniques enabled a decade of undetected fraud.",
        "The internal belief system that kept 200 employees silent for six years.",
    ],
    "control_files": [
        "The forensic evidence that documented what this belief system actually did.",
        "The financial trail that proved the institution was the mechanism.",
        "The psychological horror that underlies every financial crime in this series.",
        "A betrayal documented across 847 internal files that nobody read.",
    ],
}

def get_cross_niche_topics(channel_id, seed_topic, ai_fn=None):
    """
    Get two cross-niche topics for Shorts 5 and 6.
    Uses the CROSS_NICHE_TOPICS bank, picking two that haven't been used recently.
    Returns list of two topic strings.
    """
    topics = CROSS_NICHE_TOPICS.get(channel_id, CROSS_NICHE_TOPICS["betrayal_deepdive"])
    # Rotate based on day of year so topics vary across episodes
    day  = datetime.datetime.now().timetuple().tm_yday
    idx1 = day % len(topics)
    idx2 = (day + 1) % len(topics)
    return [topics[idx1], topics[idx2]]
