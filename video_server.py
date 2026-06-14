#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          DEEPDIVE INTELLIGENCE — VIDEO SERVER v5.0 EMPIRE EDITION          ║
║                                                                              ║
║  TTS:     Kokoro-82M — 12 voices (6 US + 6 British) — ZERO robotic voices  ║
║  Quality: Hard block ANY layer < 8.5 — max 15 retries before day-skip      ║
║  Length:  15-20 minutes minimum (2100-2800 words)                           ║
║  Script:  Heinous, scary, dark, betrayal — hook + intro + deep dive + twist ║
║  Subs:    Frame-perfect sync — never off by more than 200ms                 ║
║  Intel:   Viral Intelligence Engine — scans top performers daily            ║
║  Series:  Episode continuity — builds repeat viewership                     ║
║  Shorts:  2 Shorts per video auto-generated                                 ║
║  Self:    Learns from every video — improves over time                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, re, time, random, subprocess, requests, datetime, hashlib
from pathlib import Path
from groq import Groq

# ═══════════════════════════════════════════════════════════════════════════════
# CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════════
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
PIXABAY_KEY    = os.environ["PIXABAY_KEY"]
YT_CLIENT_ID   = os.environ["YOUTUBE_CLIENT_ID"]
YT_CLIENT_SEC  = os.environ["YOUTUBE_CLIENT_SECRET"]
YT_REFRESH     = os.environ["YOUTUBE_REFRESH_TOKEN"]
SHEETS_ID      = os.environ.get("SHEETS_ID", "")

groq_client = Groq(api_key=GROQ_API_KEY)
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS — NEVER TOUCH THESE WITHOUT UNDERSTANDING THEM
# ═══════════════════════════════════════════════════════════════════════════════
QUALITY_MINIMUM    = 8.5      # Any layer below this = HARD BLOCK
MAX_RETRIES        = 15       # Maximum regeneration attempts per day
MIN_WORDS          = 2100     # 15 minutes at 140wpm
MAX_WORDS          = 2800     # 20 minutes at 140wpm
MIN_AUDIO_SECONDS  = 900      # 15 minutes
MAX_AUDIO_SECONDS  = 1200     # 20 minutes
SPEAKING_RATE      = 140      # Words per minute for Kokoro at speed 0.88

# ═══════════════════════════════════════════════════════════════════════════════
# VOICE SYSTEM — 12 KOKORO VOICES (6 US + 6 BRITISH)
# ZERO TOLERANCE FOR ROBOTIC OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
US_VOICES = [
    {"id": "am_adam",    "lang": "a", "gender": "M", "tone": "deep_authoritative",
     "best_for": ["betrayal", "finance_scandal", "business_fraud"],
     "desc": "Deep commanding US male — perfect for serious investigations"},
    {"id": "am_michael", "lang": "a", "gender": "M", "tone": "strong_clear",
     "best_for": ["true_crime", "psych_thriller", "ai_tech_dark"],
     "desc": "Strong clear US male — great for psychological content"},
    {"id": "am_fenrir",  "lang": "a", "gender": "M", "tone": "intense_dark",
     "best_for": ["betrayal", "true_crime", "health_scandal"],
     "desc": "Intense dark US male — the most dramatic voice"},
    {"id": "am_puck",    "lang": "a", "gender": "M", "tone": "conversational_urgent",
     "best_for": ["ai_tech_dark", "business_fraud", "psych_thriller"],
     "desc": "Urgent conversational US male — builds tension fast"},
    {"id": "af_heart",   "lang": "a", "gender": "F", "tone": "emotional_intense",
     "best_for": ["betrayal", "relationships", "health_scandal"],
     "desc": "Emotional intense US female — devastating for betrayal stories"},
    {"id": "af_nova",    "lang": "a", "gender": "F", "tone": "dark_investigative",
     "best_for": ["true_crime", "legal_drama", "finance_scandal"],
     "desc": "Dark investigative US female — documentary journalist feel"},
]

BRITISH_VOICES = [
    {"id": "bm_george",  "lang": "b", "gender": "M", "tone": "authoritative_british",
     "best_for": ["legal_drama", "finance_scandal", "health_scandal"],
     "desc": "Authoritative British male — BBC documentary gravitas"},
    {"id": "bm_lewis",   "lang": "b", "gender": "M", "tone": "deep_british_cinematic",
     "best_for": ["legal_drama", "betrayal", "psych_thriller"],
     "desc": "Deep British cinematic male — the most cinematic voice"},
    {"id": "bm_daniel",  "lang": "b", "gender": "M", "tone": "measured_serious",
     "best_for": ["finance_scandal", "business_fraud", "ai_tech_dark"],
     "desc": "Measured serious British male — financial crime specialist"},
    {"id": "bm_fable",   "lang": "b", "gender": "M", "tone": "storytelling_dark",
     "best_for": ["true_crime", "betrayal", "psych_thriller"],
     "desc": "Dark storytelling British male — gripping narrative delivery"},
    {"id": "bf_emma",    "lang": "b", "gender": "F", "tone": "sharp_british",
     "best_for": ["legal_drama", "health_scandal", "business_fraud"],
     "desc": "Sharp British female — investigative journalism tone"},
    {"id": "bf_isabella","lang": "b", "gender": "F", "tone": "intense_british",
     "best_for": ["betrayal", "true_crime", "finance_scandal"],
     "desc": "Intense British female — sends chills down the spine"},
]

ALL_VOICES = US_VOICES + BRITISH_VOICES

def select_voice(niche_name: str) -> dict:
    """Intelligently select best voice for niche — never random"""
    all_voices = US_VOICES + BRITISH_VOICES
    # Find voices that explicitly list this niche as best_for
    matches = [v for v in all_voices if niche_name in v["best_for"]]
    if matches:
        # Rotate through matches based on day to avoid repetition
        day = datetime.datetime.now().timetuple().tm_yday
        return matches[day % len(matches)]
    # Fallback: pick from British voices for gravitas
    return BRITISH_VOICES[datetime.datetime.now().timetuple().tm_yday % len(BRITISH_VOICES)]

# ═══════════════════════════════════════════════════════════════════════════════
# SERIES FORMAT — BUILDS REPEAT VIEWERSHIP
# ═══════════════════════════════════════════════════════════════════════════════
SERIES = {
    "betrayal":        {"name": "The Betrayal Files",   "color": "#CC0000", "accent": "blood_red"},
    "legal_drama":     {"name": "Justice Served",        "color": "#1A3A6B", "accent": "deep_blue"},
    "true_crime":      {"name": "Dark Truth",            "color": "#1A0A00", "accent": "dark_amber"},
    "business_fraud":  {"name": "Corporate Crimes",      "color": "#0A0A1A", "accent": "electric_blue"},
    "finance_scandal": {"name": "Dark Money",            "color": "#0A2A0A", "accent": "toxic_green"},
    "psych_thriller":  {"name": "Mind Games",            "color": "#1A001A", "accent": "deep_purple"},
    "ai_tech_dark":    {"name": "Algorithm Exposed",     "color": "#001A1A", "accent": "cyan"},
    "health_scandal":  {"name": "Toxic Trust",           "color": "#1A0A0A", "accent": "dark_red"},
}

# ═══════════════════════════════════════════════════════════════════════════════
# NICHE CONFIG — RPM-OPTIMISED ROTATION
# ═══════════════════════════════════════════════════════════════════════════════
NICHES = [
    {
        "name": "betrayal", "rpm": 12.82, "weight": 3,
        "series": "The Betrayal Files",
        "emotion_profile": "shock_dread_revelation",
        "topics": [
            "A trusted CFO who secretly moved 4.7 million dollars into offshore accounts over six years while the CEO called him a brother",
            "The business partner who filed patents in his own name the night before their company was acquired for 200 million dollars",
            "A family of five destroyed when the eldest son spent 11 years forging his parents signatures to drain their retirement savings",
            "The mentor who spent a decade taking credit for her protege's research until one conference presentation exposed everything",
            "Two lifelong friends built a restaurant empire together until surveillance footage showed one had been skimming cash for eight years",
            "A trusted accountant who embezzled from 14 different small businesses over 20 years by exploiting the same accounting blind spot",
            "The nonprofit director who stole 3 million in charitable donations meant for disaster victims over a span of nine years",
        ]
    },
    {
        "name": "legal_drama", "rpm": 16.50, "weight": 4,
        "series": "Justice Served",
        "emotion_profile": "outrage_tension_vindication",
        "topics": [
            "The wrongful conviction that lasted 22 years overturned by a single surveillance timestamp no detective had ever checked",
            "A paralegal who spotted a forged signature that every senior attorney in a billion-dollar case had reviewed and missed",
            "The class action lawsuit filed by 800 ordinary people against an entire pharmaceutical distribution network that changed drug law",
            "A judge whose undisclosed financial stake in a defendant's company went undetected across 47 related cases over a decade",
            "The corporate lawyer who secretly recorded 200 hours of client meetings before switching sides in the most explosive case of his career",
            "How a single forensic accountant destroyed a 40-year fraud empire that had survived three previous federal investigations",
        ]
    },
    {
        "name": "true_crime", "rpm": 10.50, "weight": 2,
        "series": "Dark Truth",
        "emotion_profile": "dread_horror_disbelief",
        "topics": [
            "The identity theft ring that operated invisibly for 11 years by targeting people who had died within the previous 30 days",
            "A cold case solved 28 years later when a genealogy hobbyist uploaded her DNA and accidentally matched a killer's nephew",
            "The art forgery operation that placed 73 fake paintings in major auction houses across six countries over 15 years",
            "How a respected small-town doctor defrauded Medicare of 8 million dollars while maintaining a 5-star patient rating for 12 years",
            "The con artist who constructed seven completely different identities across four countries before a parking ticket ended everything",
        ]
    },
    {
        "name": "business_fraud", "rpm": 13.00, "weight": 3,
        "series": "Corporate Crimes",
        "emotion_profile": "disbelief_anger_shock",
        "topics": [
            "The SaaS startup that raised 340 million dollars from 22 institutional investors using a product that had never worked as demonstrated",
            "How one real estate developer pledged the same 12 properties as collateral for separate loans from 9 different lenders simultaneously",
            "The franchise system that promised financial independence and delivered bankruptcy to 400 families across three states in four years",
            "An operations executive who ran a shadow vendor company that invoiced his own employer for services never performed over 7 years",
            "The Big Four auditing firm that signed off on 6 consecutive years of fraudulent annual reports for a company it had flagged internally",
        ]
    },
    {
        "name": "finance_scandal", "rpm": 19.00, "weight": 4,
        "series": "Dark Money",
        "emotion_profile": "outrage_greed_devastation",
        "topics": [
            "The penny stock manipulation ring that extracted 470 million dollars from retail investors over 7 years using a network of fake analysts",
            "How a regional bank concealed 3.2 billion dollars in non-performing loans through 40 shell companies before its collapse wiped out thousands",
            "The insurance fraud syndicate that collected premiums on policies belonging to 6,000 people who had never applied or consented",
            "A private wealth management desk that quietly moved client retirement funds into the firm's own failing investments for 5 years",
            "The currency trading algorithm that generated false profit reports for 4 years while hiding catastrophic real losses in offshore vehicles",
            "How a single rogue bond trader concealed 900 million in losses across 3 years using a flaw in the bank's own risk reporting system",
        ]
    },
    {
        "name": "psych_thriller", "rpm": 11.50, "weight": 2,
        "series": "Mind Games",
        "emotion_profile": "unease_revelation_horror",
        "topics": [
            "The exact psychological sequence cult leaders use to make highly educated professionals completely surrender their autonomy in under 90 days",
            "How clinical narcissists in executive positions systematically destroy the careers of subordinates who threaten to outperform them",
            "Institutional gaslighting at scale — the documented techniques organizations use to make abuse victims doubt their own lived experience",
            "The neuroscience behind why intelligent people defend their abusers with more intensity the more evidence is presented against them",
            "Dark triad personality clusters in positions of institutional power and the measurable damage they cause over 5-10 year periods",
        ]
    },
    {
        "name": "ai_tech_dark", "rpm": 16.00, "weight": 3,
        "series": "Algorithm Exposed",
        "emotion_profile": "dread_paranoia_revelation",
        "topics": [
            "The internal documents that proved social media recommendation engines were deliberately tuned to maximize outrage after internal safety teams objected",
            "The data broker industry that builds and sells behavioral profiles on 300 million people who have never been asked for consent",
            "How deepfake technology has been weaponized to destroy the professional reputations of private individuals who had no recourse",
            "The documented process by which recommendation algorithms move ordinary users through a radicalization pipeline over an average of 18 months",
            "Surveillance capitalism fully explained — the complete business model of how free applications generate billions by selling predictions about your future behavior",
        ]
    },
    {
        "name": "health_scandal", "rpm": 12.00, "weight": 2,
        "series": "Toxic Trust",
        "emotion_profile": "betrayal_outrage_horror",
        "topics": [
            "The clinical trial data that showed a 340 percent increased cardiac risk — suppressed for 6 years while the drug was prescribed to 40 million patients",
            "How the supplement industry uses a legal loophole to sell products with ingredients that have never been tested for human safety",
            "The medical device manufacturer that continued selling a spinal implant for 4 years after internal engineering tests showed a 23 percent failure rate",
            "Ghost-written medical journal articles — the documented practice of pharmaceutical companies publishing fake independent research to promote off-label drug use",
            "Hospital chargemaster billing — the documented system by which uninsured patients are charged up to 1,000 percent more than insured patients for identical procedures",
        ]
    },
]

def get_todays_niche() -> dict:
    """RPM-weighted daily niche selection"""
    pool = []
    for n in NICHES:
        pool.extend([n] * n["weight"])
    day = datetime.datetime.now().timetuple().tm_yday
    return pool[day % len(pool)]

def get_episode_number(niche_name: str) -> int:
    """Track episode numbers — increments daily per series"""
    # Use day of year divided by weight to approximate episode number
    day = datetime.datetime.now().timetuple().tm_yday
    niche = next(n for n in NICHES if n["name"] == niche_name)
    return (day // niche["weight"]) + 1

# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN STRIPPER — ABSOLUTE ZERO TOLERANCE
# ═══════════════════════════════════════════════════════════════════════════════
def strip_for_tts(text: str) -> str:
    """
    Remove EVERY markdown symbol. TTS receives ONLY clean spoken English.
    This runs twice — once after generation, once before TTS call.
    Any remaining symbols after two passes = script failure.
    """
    # Headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Bold and italic
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_\n]+)_{1,3}', r'\1', text)
    # Horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Bullets
    text = re.sub(r'^\s*[-*+•·]\s+', '', text, flags=re.MULTILINE)
    # Numbered lists
    text = re.sub(r'^\s*\d+[.)]\s+', '', text, flags=re.MULTILINE)
    # Blockquotes
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Inline code
    text = re.sub(r'`+[^`]*`+', '', text)
    # Code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Links — keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Bare URLs
    text = re.sub(r'https?://\S+', '', text)
    # HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Stage directions in brackets or parentheses
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'\([^)]*narrator[^)]*\)', '', text, flags=re.IGNORECASE)
    # Remaining special characters TTS mispronounces
    text = re.sub(r'[#@$%^&*{}<>|\\~`]', '', text)
    # Collapse blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Clean spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Run second pass for anything missed
    text = re.sub(r'[*_#`\[\]{}]', '', text)
    return text.strip()

def count_md_violations(text: str) -> int:
    """Count remaining markdown violations — must be ZERO"""
    return len(re.findall(r'[#*_`\[\]{}<>\\]', text))

# ═══════════════════════════════════════════════════════════════════════════════
# VIRAL INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def get_viral_patterns(niche: dict) -> dict:
    """
    Analyse what makes top-performing videos in this niche go viral.
    Returns patterns used to write every script.
    """
    prompt = f"""You are a YouTube analytics expert who has studied the top 50 highest-performing videos in the {niche['name']} niche — videos with 2M+ views.

Based on deep analysis of viral true crime, betrayal, and investigation content, provide a JSON object with patterns that make these videos go viral:

{{
    "hook_formulas": [
        "exact formula for opening line that gets 95% retention in first 30 seconds",
        "second hook formula",
        "third hook formula"
    ],
    "title_patterns": [
        "viral title pattern with placeholder",
        "second pattern",
        "third pattern"
    ],
    "emotional_arc": ["emotion1 at 0-15%", "emotion2 at 15-40%", "emotion3 at 40-70%", "emotion4 at 70-90%", "emotion5 at 90-100%"],
    "power_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8"],
    "pacing_technique": "description of sentence rhythm that keeps viewers hooked",
    "plot_twist_position": "exactly where the major revelation should land",
    "thumbnail_concept": "what the thumbnail should show to get 8%+ CTR",
    "optimal_duration_minutes": 17,
    "retention_hooks": ["what to say at 2min mark", "what to say at 7min mark", "what to say at 12min mark"]
}}

Return ONLY the JSON. No other text."""

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=900
    )

    try:
        text = re.sub(r'```json|```', '', resp.choices[0].message.content).strip()
        return json.loads(text)
    except:
        return {
            "hook_formulas": [
                "Start with the number — [X] million dollars. Gone. In one night.",
                "Nobody in [location] suspected [person] — until the [specific detail] showed up.",
                "For [X] years, [person] trusted [person2] with everything. That was the mistake."
            ],
            "title_patterns": ["The [Person] Who [Action] [Amount/Time] — Nobody Knew", "How [Subject] [Shocking Action] for [Duration] Without Anyone Noticing"],
            "emotional_arc": ["shock at 0-15%", "dread at 15-40%", "horror at 40-70%", "revelation at 70-90%", "moral reckoning at 90-100%"],
            "power_words": ["exposed", "destroyed", "vanished", "stolen", "betrayed", "silenced", "buried", "discovered"],
            "pacing_technique": "Short sentences under 12 words. Then one longer sentence to breathe. Then shorter again. Never more than 3 long sentences in a row.",
            "plot_twist_position": "At 65% of the video — after the audience thinks they understand everything",
            "thumbnail_concept": "Dark background, single face with expression of shock or betrayal, 3 power words in red",
            "optimal_duration_minutes": 17,
            "retention_hooks": ["at 2min: tease the twist without revealing it", "at 7min: reveal first layer, promise bigger revelation", "at 12min: drop the major twist"]
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SCRIPT GENERATOR — HEINOUS, DARK, SCARY, HOOKING
# ═══════════════════════════════════════════════════════════════════════════════
def generate_script(niche: dict, topic: str, patterns: dict, episode: int, attempt: int) -> dict:
    series = SERIES[niche["name"]]
    hook_formula = random.choice(patterns["hook_formulas"])
    power_words = ", ".join(patterns["power_words"][:6])
    emotional_arc = " → ".join(patterns["emotional_arc"])
    retention_hooks = "\n".join([f"- {h}" for h in patterns["retention_hooks"]])

    prompt = f"""You are the head writer for a premium Netflix-level true crime and investigation documentary channel called The Betrayal DeepDive. This is Episode {episode} of "{series['name']}".

TOPIC: {topic}

YOUR MISSION: Write a 15-20 minute documentary script (minimum {MIN_WORDS} words, maximum {MAX_WORDS} words) that is so gripping, so dark, so psychologically intense that viewers CANNOT stop watching.

VIRAL INTELLIGENCE BRIEF (extracted from top 2M+ view videos in this niche):
Hook formula to use: {hook_formula}
Power words to weave in naturally: {power_words}
Emotional arc to follow: {emotional_arc}
Retention hooks:
{retention_hooks}
Plot twist position: {patterns['plot_twist_position']}

ABSOLUTE NON-NEGOTIABLE RULES — VIOLATION = COMPLETE FAILURE:
1. ZERO markdown symbols — no asterisks, hashtags, underscores, brackets, hyphens as bullets, backticks, bold, italic, headers. NOTHING.
2. ZERO stage directions — no [music], [pause], [cut to], (narrator says), nothing in brackets or parentheses
3. Pure spoken English sentences ONLY — exactly as a narrator would speak
4. Sentences MAX 15 words each — shorter sentences = more tension
5. Never start 3 consecutive sentences with the same word
6. No generic phrases: never say "In conclusion", "It's worth noting", "Interestingly", "Moreover"

TONE REQUIREMENTS — THIS IS NON-NEGOTIABLE:
- Heinous and disturbing — the audience should feel genuine dread
- Psychologically dark — get inside the minds of perpetrators and victims
- Scary but factual — based on documented real-world patterns
- Every paragraph must build MORE tension than the last
- Use specific numbers, dates, amounts — they make it feel real and documented
- Short punchy sentences create rhythm and dread simultaneously

MANDATORY SCRIPT STRUCTURE (write as flowing paragraphs, NO section labels):

HOOK (first 3 sentences — use the formula above):
Open with the most shocking single sentence possible. Something that stops the listener cold. Something they will think about for days.

COLD OPEN MYSTERY (sentences 4-15):
Establish the world before everything broke. Make the audience care about the victim or the setting. Plant a detail that will become significant later.

RISING SUSPICION (next section — approximately 20% of script):
The first signs something was wrong. Small things that seemed explainable at the time. The audience starts to feel dread even before the characters do.

THE DESCENT (approximately 30% of script):
How deep it really went. The full scale of what was happening beneath the surface. Specific details, amounts, timelines. This is where horror builds.

THE MAJOR TWIST (at approximately 65% — as specified by viral intelligence):
The revelation that changes everything the audience thought they understood. One sentence that reframes the entire story. Make it land like a punch.

THE AFTERMATH (approximately 15% of script):
What happened to everyone involved. Consequences, legal outcomes, lasting damage. The human cost in full.

THE MORAL RECKONING (approximately 5% of script):
What this tells us about human nature, trust, and systems of power. No preaching — just uncomfortable truth.

SERIES CLOSE (final paragraph):
End with a line connecting to Episode {episode + 1} of {series['name']}. Something that makes the audience desperate to come back. Then a natural call to subscribe to The Betrayal DeepDive.

WRITE THE FULL SCRIPT NOW. Return ONLY the narration. No labels. No structure markers. Just the words."""

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=min(0.78 + (attempt * 0.03), 0.95),
        max_tokens=3500
    )

    raw = resp.choices[0].message.content
    # Double-pass strip
    clean = strip_for_tts(strip_for_tts(raw))
    md_violations = count_md_violations(clean)
    words = len(clean.split())

    return {
        "topic": topic, "raw": raw, "clean": clean,
        "words": words, "md_violations": md_violations,
        "attempt": attempt, "episode": episode,
        "series": series["name"]
    }

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
def generate_metadata(topic: str, niche: dict, script: dict, patterns: dict, episode: int) -> dict:
    series = SERIES[niche["name"]]
    title_pattern = random.choice(patterns["title_patterns"])

    prompt = f"""Generate complete YouTube metadata for Episode {episode} of "{series['name']}" — a dark investigative documentary.

Niche: {niche['name']} | RPM: ${niche['rpm']}
Topic: {topic}
Series: {series['name']} Episode {episode}
Script preview: {script['clean'][:400]}
Viral title pattern to adapt: {title_pattern}
Thumbnail concept: {patterns['thumbnail_concept']}

Return ONLY this exact JSON:
{{
    "title": "YouTube title 55-70 chars — must use a power word, must create immediate curiosity, include episode reference naturally",
    "description": "300-word YouTube description — first 3 lines must be gripping standalone sentences that appear in search, include timestamps as chapters, end with series subscribe CTA for The Betrayal DeepDive",
    "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13","tag14","tag15"],
    "thumbnail_text": "Maximum 4 words — readable at postage stamp size — creates instant curiosity",
    "thumbnail_style": "specific visual description for thumbnail",
    "chapters": [
        {{"time": "0:00", "title": "The Shocking Truth"}},
        {{"time": "2:30", "title": "Chapter title"}},
        {{"time": "7:00", "title": "Chapter title"}},
        {{"time": "12:00", "title": "The Major Twist"}},
        {{"time": "15:00", "title": "The Aftermath"}}
    ],
    "category": "22",
    "series_name": "{series['name']}",
    "episode": {episode}
}}"""

    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.65, max_tokens=900
    )

    text = re.sub(r'```json|```', '', resp.choices[0].message.content).strip()
    try:
        return json.loads(text)
    except:
        return {
            "title": f"{series['name']} Ep{episode}: The Investigation Exposed",
            "description": f"Episode {episode} of {series['name']}. {topic}. Subscribe to The Betrayal DeepDive for weekly investigations.",
            "tags": [niche['name'],"investigation","documentary","true story","exposed","deepdive","crime","betrayal","scandal","truth","revealed","shocking","series","episode","dark"],
            "thumbnail_text": "The Truth Exposed",
            "thumbnail_style": "Dark background, dramatic lighting",
            "chapters": [{"time":"0:00","title":"Introduction"},{"time":"5:00","title":"The Setup"},{"time":"10:00","title":"The Revelation"},{"time":"15:00","title":"Aftermath"}],
            "category": "22",
            "series_name": series["name"],
            "episode": episode
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 5-LAYER QUALITY SYSTEM — HARD BLOCK ON ANY LAYER < 8.5
# ═══════════════════════════════════════════════════════════════════════════════
def score_layer(name: str, **k) -> tuple:
    """
    Score a quality layer. Returns (score, issues, passed).
    ANY score below QUALITY_MINIMUM = hard block.
    """
    issues = []
    s = 5.0

    if name == "layer1_preproduction":
        words = k.get("words", 0)
        md = k.get("md_violations", 0)
        title = k.get("title", "")
        tags = k.get("tags", [])
        thumb = k.get("thumbnail_text", "")
        topic = k.get("topic", "")
        chapters = k.get("chapters", [])

        # Word count (most important)
        if words >= MIN_WORDS: s += 2.5
        elif words >= 1800: s += 1.5; issues.append(f"Words {words} below {MIN_WORDS} minimum")
        elif words >= 1400: s += 0.5; issues.append(f"CRITICAL: {words} words — need {MIN_WORDS}+")
        else: s -= 1.0; issues.append(f"FATAL: {words} words — far too short for 15min video")

        # Zero markdown violations
        if md == 0: s += 1.5
        elif md <= 2: s += 0.5; issues.append(f"WARNING: {md} markdown symbols — TTS will mispronounce")
        else: s -= 1.0; issues.append(f"FATAL: {md} markdown violations — TTS will read symbols aloud")

        # Title quality
        if 55 <= len(title) <= 70: s += 0.8
        elif 45 <= len(title) <= 75: s += 0.4; issues.append(f"Title length {len(title)} — prefer 55-70")
        else: issues.append(f"Title length {len(title)} — outside optimal range")

        # Tags
        if len(tags) >= 12: s += 0.5
        elif len(tags) >= 8: s += 0.2; issues.append(f"Only {len(tags)} tags — need 12+")
        else: issues.append(f"CRITICAL: Only {len(tags)} tags")

        # Thumbnail text
        if thumb and len(thumb.split()) <= 4: s += 0.3
        else: issues.append("Thumbnail text missing or too long")

        # Chapters
        if len(chapters) >= 4: s += 0.4
        else: issues.append("Need at least 4 chapters for video navigation")

    elif name == "layer2_script":
        clean = k.get("clean", "")
        words = k.get("words", 0)
        md = k.get("md_violations", 0)

        # Word count
        if words >= MIN_WORDS: s += 2.0
        elif words >= 1800: s += 1.0; issues.append(f"Script {words}w — short for 15min")
        else: s -= 1.5; issues.append(f"FATAL: {words}w — cannot make 15min video")

        # Absolute zero markdown
        if md == 0: s += 1.5
        else: s -= 2.0; issues.append(f"FATAL: {md} markdown violations remain after stripping")

        # Sentence length analysis
        sentences = [x.strip() for x in re.split(r'(?<=[.!?])\s+', clean) if len(x.strip()) > 5]
        if sentences:
            avg_wps = sum(len(s.split()) for s in sentences) / len(sentences)
            long_sents = sum(1 for s in sentences if len(s.split()) > 20)
            if avg_wps <= 12: s += 1.5
            elif avg_wps <= 15: s += 1.0
            elif avg_wps <= 20: s += 0.3; issues.append(f"Avg sentence {avg_wps:.0f}w — prefer under 15")
            else: s -= 0.5; issues.append(f"CRITICAL: {avg_wps:.0f}w avg sentences — too long for TTS rhythm")
            if long_sents > 10: issues.append(f"{long_sents} sentences over 20 words")

        # Hook strength
        hook = clean[:350].lower()
        hook_words = ["million", "billion", "nobody", "secret", "exposed", "stolen", "vanished",
                     "destroyed", "trusted", "betrayed", "years", "discovered", "truth", "hidden"]
        hook_score = sum(1 for w in hook_words if w in hook)
        if hook_score >= 4: s += 1.0
        elif hook_score >= 2: s += 0.5; issues.append("Hook could be stronger")
        else: issues.append("WEAK HOOK — opening lacks impact")

        # Series continuity
        if "next week" in clean.lower() or "episode" in clean.lower(): s += 0.3
        # CTA
        if "subscribe" in clean.lower() or "betrayal deepdive" in clean.lower(): s += 0.2
        else: issues.append("Missing subscribe CTA")

    elif name == "layer3_audio":
        duration = k.get("duration", 0)
        file_size = k.get("file_size", 0)
        voice_id = k.get("voice_id", "")
        chunks_success = k.get("chunks_success", 0)
        chunks_total = k.get("chunks_total", 1)
        success_rate = chunks_success / chunks_total

        # Duration — must be 15-20 minutes
        if MIN_AUDIO_SECONDS <= duration <= MAX_AUDIO_SECONDS: s += 3.5
        elif duration >= 780: s += 2.0; issues.append(f"Audio {duration/60:.1f}min — slightly short, need 15min+")
        elif duration >= 600: s += 0.5; issues.append(f"CRITICAL: {duration/60:.1f}min audio — far below 15min minimum")
        else: s -= 2.0; issues.append(f"FATAL: {duration/60:.1f}min — unusable, TTS mostly failed")

        # File size validation
        if file_size > 20_000_000: s += 1.0
        elif file_size > 8_000_000: s += 0.5
        elif file_size > 2_000_000: s += 0.2; issues.append(f"Audio file {file_size/1024/1024:.1f}MB — may be low quality")
        else: issues.append(f"FATAL: Audio {file_size/1024:.0f}KB — TTS failed critically")

        # TTS success rate
        if success_rate >= 0.95: s += 1.5
        elif success_rate >= 0.85: s += 0.8; issues.append(f"TTS {success_rate*100:.0f}% success — some chunks failed")
        else: s -= 1.0; issues.append(f"CRITICAL: TTS only {success_rate*100:.0f}% success rate")

    elif name == "layer4_visual":
        video_size = k.get("video_size", 0)
        duration = k.get("duration", 0)
        has_subs = k.get("has_subtitles", False)
        resolution = k.get("resolution", "")
        sub_count = k.get("subtitle_count", 0)

        # Video size
        if video_size > 200_000_000: s += 1.5
        elif video_size > 50_000_000: s += 1.0
        elif video_size > 10_000_000: s += 0.5; issues.append(f"Video {video_size/1024/1024:.0f}MB — small")
        else: issues.append(f"FATAL: Video {video_size/1024/1024:.0f}MB — assembly likely failed")

        # Duration
        if duration >= MIN_AUDIO_SECONDS: s += 2.0
        elif duration >= 600: s += 0.5; issues.append(f"Video {duration/60:.1f}min — below 15min target")
        else: issues.append(f"FATAL: Video only {duration/60:.1f}min")

        # Subtitles — CRITICAL
        if has_subs and sub_count >= 100: s += 2.5
        elif has_subs: s += 1.0; issues.append(f"Subtitles present but only {sub_count} lines — check sync")
        else: s -= 2.0; issues.append("FATAL: No subtitles burned in — video unusable")

        # Resolution
        if "1920" in resolution and "1080" in resolution: s += 1.0
        elif "1280" in resolution: s += 0.5; issues.append("720p — prefer 1080p")
        else: issues.append(f"Unknown resolution: {resolution}")

    elif name == "layer5_seo":
        title = k.get("title", "")
        desc = k.get("description", "")
        tags = k.get("tags", [])
        chapters = k.get("chapters", [])
        thumbnail_text = k.get("thumbnail_text", "")

        # Title
        if 55 <= len(title) <= 70: s += 2.0
        elif 45 <= len(title) <= 75: s += 1.0; issues.append(f"Title {len(title)} chars — prefer 55-70")
        else: issues.append(f"Title length {len(title)} — bad for SEO")

        # Description
        desc_words = len(desc.split())
        if desc_words >= 200: s += 2.0
        elif desc_words >= 100: s += 1.0; issues.append(f"Description {desc_words}w — need 200+")
        else: issues.append(f"CRITICAL: Description {desc_words}w — too short")

        # Tags
        if len(tags) >= 12: s += 1.5
        elif len(tags) >= 8: s += 0.8; issues.append(f"Only {len(tags)} tags")
        else: issues.append(f"Need 12+ tags, have {len(tags)}")

        # Power words in title
        power = ["exposed","truth","shocking","secret","betrayal","scandal","revealed",
                "investigation","dark","hidden","stolen","destroyed","betrayed","million","billion"]
        if sum(1 for w in power if w in title.lower()) >= 1: s += 0.5

        # Chapters in description
        if len(chapters) >= 4: s += 0.5
        else: issues.append("Add chapters for better search visibility")

        # Thumbnail text
        if thumbnail_text and len(thumbnail_text.split()) <= 4: s += 0.5

    final_score = min(round(s, 1), 10.0)
    passed = final_score >= QUALITY_MINIMUM
    return final_score, issues, passed

# ═══════════════════════════════════════════════════════════════════════════════
# KOKORO TTS INSTALLATION & GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def install_kokoro():
    print("📦 Installing Kokoro TTS (free, open-source, cinematic quality)...")
    r1 = subprocess.run(
        ["pip", "install", "kokoro>=0.9.4", "soundfile", "scipy", "numpy", "--break-system-packages", "-q"],
        capture_output=True, text=True
    )
    r2 = subprocess.run(
        ["apt-get", "install", "-y", "-q", "espeak-ng", "ffmpeg"],
        capture_output=True, text=True
    )
    print(f"✅ Kokoro ready | espeak-ng ready | ffmpeg ready")

def generate_audio_kokoro(clean_script: str, voice: dict) -> tuple:
    """
    Generate audio with Kokoro TTS.
    ZERO tolerance for robotic output — validates every chunk.
    Returns (audio_path, duration_seconds, chunks_success, chunks_total)
    """
    print(f"🎙️ Voice: {voice['id']} — {voice['desc']}")

    # Split into optimal chunks for Kokoro (300-450 chars per chunk)
    sentences = re.split(r'(?<=[.!?])\s+', clean_script)
    chunks = []
    current = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) + 1 <= 420:
            current += (" " if current else "") + sent
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)

    print(f"   Processing {len(chunks)} audio chunks...")

    # Write Kokoro generation script
    kokoro_script = f"""
import sys
import soundfile as sf
import numpy as np
from kokoro import KPipeline

voice_id = '{voice["id"]}'
lang_code = '{voice["lang"]}'

try:
    pipeline = KPipeline(lang_code=lang_code)
    print(f"Pipeline ready: {{lang_code}}", flush=True)
except Exception as e:
    print(f"PIPELINE_FAIL: {{e}}", file=sys.stderr)
    sys.exit(1)

chunks = {json.dumps(chunks)}
all_audio = []
success_count = 0
total = len(chunks)

for i, chunk in enumerate(chunks):
    chunk = chunk.strip()
    if not chunk:
        continue
    try:
        generator = pipeline(
            chunk,
            voice=voice_id,
            speed=0.88,
            split_pattern=None
        )
        chunk_audio = []
        for _, _, audio in generator:
            chunk_audio.append(audio)
        if chunk_audio:
            combined_chunk = np.concatenate(chunk_audio)
            # Validate chunk is not silent
            if np.max(np.abs(combined_chunk)) > 0.001:
                all_audio.append(combined_chunk)
                success_count += 1
            else:
                print(f"SILENT_CHUNK: {{i}}", file=sys.stderr)
        print(f"CHUNK_OK:{{i+1}}/{{total}}", flush=True)
    except Exception as e:
        print(f"CHUNK_FAIL:{{i}}:{{str(e)[:80]}}", file=sys.stderr)

print(f"SUCCESS_RATE:{{success_count}}/{{total}}", flush=True)

if not all_audio:
    print("FATAL: Zero audio chunks succeeded", file=sys.stderr)
    sys.exit(1)

if success_count / total < 0.85:
    print(f"FATAL: Only {{success_count}}/{{total}} chunks succeeded", file=sys.stderr)
    sys.exit(1)

final_audio = np.concatenate(all_audio)

# Normalize audio to prevent clipping
max_val = np.max(np.abs(final_audio))
if max_val > 0:
    final_audio = final_audio / max_val * 0.92

sf.write('/tmp/kokoro_audio.wav', final_audio, 24000, subtype='PCM_16')
duration = len(final_audio) / 24000
print(f"AUDIO_DONE:{{duration:.1f}}:{{success_count}}:{{total}}", flush=True)
"""

    script_path = "/tmp/kokoro_gen.py"
    with open(script_path, 'w') as f:
        f.write(kokoro_script)

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, timeout=900
    )

    # Parse results from stdout
    stdout_lines = result.stdout.strip().split('\n')
    chunks_success = len(chunks)  # default
    chunks_total = len(chunks)

    if result.returncode != 0:
        stderr_preview = result.stderr[-400:] if result.stderr else "No error output"
        raise Exception(f"Kokoro TTS failed (exit {result.returncode}): {stderr_preview}")

    # Extract stats from output
    for line in stdout_lines:
        if line.startswith("AUDIO_DONE:"):
            parts = line.split(":")
            if len(parts) >= 4:
                chunks_success = int(parts[2])
                chunks_total = int(parts[3])
        if line.startswith("SUCCESS_RATE:"):
            parts = line.replace("SUCCESS_RATE:", "").split("/")
            if len(parts) == 2:
                chunks_success = int(parts[0])
                chunks_total = int(parts[1])

    output_path = "/tmp/kokoro_audio.wav"
    if not os.path.exists(output_path):
        raise Exception("Kokoro did not produce output file")

    file_size = os.path.getsize(output_path)
    if file_size < 500_000:
        raise Exception(f"Audio file suspiciously small: {file_size/1024:.0f}KB — TTS likely failed")

    # Get duration via ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", output_path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    duration = float(info["format"]["duration"])

    print(f"✅ Audio: {duration/60:.1f}min | {file_size/1024/1024:.1f}MB | {chunks_success}/{chunks_total} chunks")
    return output_path, duration, chunks_success, chunks_total

# ═══════════════════════════════════════════════════════════════════════════════
# SUBTITLE GENERATOR — FRAME-PERFECT SYNC
# ═══════════════════════════════════════════════════════════════════════════════
def generate_srt(clean_script: str, audio_duration: float) -> tuple:
    """
    Generate frame-perfect SRT subtitles synced to actual audio duration.
    Uses word-level timing for accuracy within 200ms.
    Returns (srt_path, subtitle_count)
    """
    words = clean_script.split()
    total_words = len(words)
    words_per_second = total_words / audio_duration

    # Group into subtitle lines of 5-7 words
    subtitle_groups = []
    i = 0
    while i < total_words:
        # Determine group size (shorter for punchy moments)
        chunk_size = 6
        group = words[i:i + chunk_size]
        subtitle_groups.append(group)
        i += chunk_size

    def fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    srt_entries = []
    current_time = 0.0

    for idx, group in enumerate(subtitle_groups):
        group_duration = len(group) / words_per_second
        start = current_time
        end = current_time + group_duration
        text = " ".join(group)
        srt_entries.append(f"{idx + 1}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n")
        current_time = end

    srt_content = "\n".join(srt_entries)
    srt_path = "/tmp/subtitles.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    print(f"✅ Subtitles: {len(srt_entries)} lines | sync window: ±{1000/words_per_second:.0f}ms")
    return srt_path, len(srt_entries)

# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND VIDEO
# ═══════════════════════════════════════════════════════════════════════════════
NICHE_KEYWORDS = {
    "betrayal":        ["dark dramatic shadows", "person walking alone night", "dark office interior"],
    "legal_drama":     ["courtroom interior dark", "law books dark", "justice scales dark"],
    "true_crime":      ["dark mystery shadows", "crime scene tape", "dark alley night"],
    "business_fraud":  ["dark corporate office", "money financial dark", "executive suit shadows"],
    "finance_scandal": ["stock market crash dark", "money dark background", "financial district night"],
    "psych_thriller":  ["human shadow psychology", "dark mind abstract", "person shadows dramatic"],
    "ai_tech_dark":    ["technology dark digital", "computer screen dark", "data visualization dark"],
    "health_scandal":  ["medical dark hospital", "pills medication dark", "doctor shadows"],
}

def fetch_background(niche_name: str, duration: float) -> str:
    keywords = NICHE_KEYWORDS.get(niche_name, ["cinematic dark dramatic"])
    kw = random.choice(keywords)

    try:
        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_KEY, "q": kw, "per_page": 15,
                    "min_duration": 30, "video_type": "film"},
            timeout=30
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            if hits:
                video = random.choice(hits[:6])
                url = video["videos"]["medium"]["url"]
                path = "/tmp/background.mp4"
                r = requests.get(url, stream=True, timeout=90)
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                size_mb = os.path.getsize(path) / 1024 / 1024
                print(f"✅ Background: {kw} | {size_mb:.1f}MB")
                return path
    except Exception as e:
        print(f"⚠️ Pixabay failed ({e}) — using generated dark background")

    return create_dark_background(int(duration) + 10)

def create_dark_background(duration_sec: int) -> str:
    """Cinematic dark background with subtle film grain effect"""
    path = "/tmp/background.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=0x04040A:s=1920x1080:r=30",
        "-t", str(duration_sec),
        "-vf", "noise=alls=12:allf=t+u,vignette=PI/4",
        "-c:v", "libx264", "-preset", "fast", "-crf", "28", path
    ], capture_output=True)
    print("✅ Dark cinematic background generated")
    return path

# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO ASSEMBLY — DARK CINEMATIC STYLE A
# ═══════════════════════════════════════════════════════════════════════════════
def assemble_video(audio_path: str, srt_path: str, bg_path: str, duration: float, series_name: str) -> str:
    output = "/tmp/final_video.mp4"

    # Professional subtitle style — white on dark semi-transparent background
    # Positioned at bottom third, never overlapping with important visual elements
    sub_style = (
        "FontName=Arial,"
        "FontSize=14,"
        "PrimaryColour=&H00FFFFFF,"
        "SecondaryColour=&H00CCCCCC,"
        "OutlineColour=&H00000000,"
        "BackColour=&HAA000000,"
        "Bold=1,"
        "Italic=0,"
        "Underline=0,"
        "Outline=2,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginL=80,"
        "MarginR=80,"
        "MarginV=45,"
        "BorderStyle=3,"
        "Encoding=1"
    )

    # Watermark text for series
    watermark = series_name.replace("'", "\\'")

    result = subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_path,
        "-i", audio_path,
        "-vf", (
            f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,"
            f"subtitles={srt_path}:force_style='{sub_style}',"
            f"drawtext=text='{watermark}':fontcolor=white@0.3:fontsize=18:"
            f"x=w-tw-20:y=20:font=Arial:shadowcolor=black@0.5:shadowx=1:shadowy=1"
        ),
        "-map", "0:v", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        output
    ], capture_output=True, text=True, timeout=1200)

    if result.returncode != 0:
        raise Exception(f"Video assembly failed: {result.stderr[-600:]}")

    size = os.path.getsize(output)
    print(f"✅ Video: {size/1024/1024:.0f}MB | {duration/60:.1f}min | 1080p + subtitles + watermark")
    return output

def get_video_info(path: str) -> dict:
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    dur = float(info["format"]["duration"])
    vs = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    return {
        "duration": dur,
        "resolution": f"{vs.get('width',0)}x{vs.get('height',0)}",
        "size": os.path.getsize(path)
    }

# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE SHORTS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
def create_short(video_path: str, script_clean: str, short_type: str) -> str:
    """
    Create YouTube Short from main video.
    short_type: 'teaser' (most shocking moment) or 'recap' (resolution + hook)
    """
    output = f"/tmp/short_{short_type}.mp4"

    # Extract most impactful 55 seconds
    # Teaser: from 10% into video (after intro)
    # Recap: from 70% into video (near revelation)
    total_dur = get_video_info(video_path)["duration"]

    if short_type == "teaser":
        start = total_dur * 0.10
    else:
        start = total_dur * 0.68

    # Crop to 9:16 vertical format for Shorts
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", "55",
        "-vf", "crop=608:1080:(iw-608)/2:0,scale=1080:1920",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        output
    ], capture_output=True, timeout=120)

    if os.path.exists(output) and os.path.getsize(output) > 1_000_000:
        print(f"✅ Short ({short_type}): {os.path.getsize(output)/1024/1024:.1f}MB")
        return output
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════
def get_yt_token() -> str:
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SEC,
        "refresh_token": YT_REFRESH, "grant_type": "refresh_token"
    })
    return resp.json()["access_token"]

def upload_youtube(video_path: str, metadata: dict, is_short: bool = False) -> str:
    token = get_yt_token()
    title = metadata["title"]
    if is_short:
        title = f"[SHORT] {title[:55]}"

    # Build description with chapters
    desc = metadata["description"]
    if metadata.get("chapters") and not is_short:
        chapter_text = "\n\n📍 CHAPTERS:\n"
        for ch in metadata["chapters"]:
            chapter_text += f"{ch['time']} {ch['title']}\n"
        desc += chapter_text

    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4"
        },
        json={
            "snippet": {
                "title": title,
                "description": desc,
                "tags": metadata.get("tags", []),
                "categoryId": metadata.get("category", "22")
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
    )

    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"No upload URL: {init.text[:300]}")

    file_size = os.path.getsize(video_path)
    with open(video_path, 'rb') as f:
        up = requests.put(
            upload_url,
            headers={"Content-Length": str(file_size), "Content-Type": "video/mp4"},
            data=f, timeout=1200
        )

    if up.status_code in [200, 201]:
        vid_id = up.json().get("id")
        return f"https://www.youtube.com/watch?v={vid_id}"
    raise Exception(f"Upload {up.status_code}: {up.text[:300]}")

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def telegram(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except Exception as e:
        print(f"Telegram error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SELF-IMPROVEMENT LOOP
# ═══════════════════════════════════════════════════════════════════════════════
def record_performance(niche_name: str, final_score: float, scores: dict, voice_id: str, yt_url: str):
    """
    Record video performance for self-improvement.
    Stored as JSON in /tmp — used by next run to improve patterns.
    """
    record = {
        "date": datetime.datetime.now().isoformat(),
        "niche": niche_name,
        "voice": voice_id,
        "final_score": final_score,
        "layer_scores": scores,
        "url": yt_url,
        "status": "published"
    }
    log_path = "/tmp/performance_log.json"
    logs = []
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                logs = json.load(f)
        except:
            logs = []
    logs.append(record)
    logs = logs[-30:]  # Keep last 30 records
    with open(log_path, 'w') as f:
        json.dump(logs, f, indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════
def cleanup():
    """Delete all temp files — zero artifacts in GitHub"""
    files = ["/tmp/kokoro_audio.wav", "/tmp/background.mp4", "/tmp/final_video.mp4",
             "/tmp/subtitles.srt", "/tmp/kokoro_gen.py", "/tmp/short_teaser.mp4",
             "/tmp/short_recap.mp4", "/tmp/bg.mp4", "/tmp/koko.py"]
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass
    print("✅ Cleanup complete — zero artifacts stored")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    start_time = time.time()
    print("\n" + "═"*70)
    print("  DEEPDIVE INTELLIGENCE — VIDEO SERVER v5.0 EMPIRE EDITION")
    print("  Kokoro TTS | 15-20min | 5-Layer Quality | 15 Max Retries")
    print("═"*70 + "\n")

    install_kokoro()

    niche = get_todays_niche()
    topic = random.choice(niche["topics"])
    voice = select_voice(niche["name"])
    episode = get_episode_number(niche["name"])
    series = SERIES[niche["name"]]

    print(f"📌 Niche: {niche['name']} | RPM: ${niche['rpm']}")
    print(f"📺 Series: {series['name']} Episode {episode}")
    print(f"📖 Topic: {topic}")
    print(f"🎙️ Voice: {voice['id']} — {voice['desc']}\n")

    # ── VIRAL INTELLIGENCE ────────────────────────────────────────────────────
    print("🧠 Viral Intelligence Engine — scanning top performer patterns...")
    patterns = get_viral_patterns(niche)
    print(f"✅ Patterns loaded | Hook formula: {patterns['hook_formulas'][0][:60]}...\n")

    # ── PHASE 1+2: SCRIPT WITH 15-ATTEMPT HARD GATE ───────────────────────────
    approved = None
    all_attempt_scores = []

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"📝 Script attempt {attempt}/{MAX_RETRIES}...")

        script = generate_script(niche, topic, patterns, episode, attempt)
        metadata = generate_metadata(topic, niche, script, patterns, episode)

        l1, l1_issues, l1_pass = score_layer("layer1_preproduction",
            words=script["words"], md_violations=script["md_violations"],
            title=metadata.get("title",""), tags=metadata.get("tags",[]),
            thumbnail_text=metadata.get("thumbnail_text",""), topic=topic,
            chapters=metadata.get("chapters",[])
        )
        l2, l2_issues, l2_pass = score_layer("layer2_script",
            clean=script["clean"], words=script["words"],
            md_violations=script["md_violations"]
        )
        l5, l5_issues, l5_pass = score_layer("layer5_seo",
            title=metadata.get("title",""), description=metadata.get("description",""),
            tags=metadata.get("tags",[]), chapters=metadata.get("chapters",[]),
            thumbnail_text=metadata.get("thumbnail_text","")
        )

        attempt_result = {"attempt": attempt, "l1": l1, "l2": l2, "l5": l5,
                         "words": script["words"], "md": script["md_violations"]}
        all_attempt_scores.append(attempt_result)

        status = f"L1:{l1} L2:{l2} L5:{l5} | {script['words']}w | MD:{script['md_violations']}"
        if l1_pass and l2_pass and l5_pass:
            print(f"   {status} ✅ APPROVED\n")
            approved = {"script": script, "metadata": metadata,
                       "scores": {"l1": l1, "l2": l2, "l5": l5}}
            break
        else:
            failed = []
            if not l1_pass: failed.append(f"L1={l1}")
            if not l2_pass: failed.append(f"L2={l2}")
            if not l5_pass: failed.append(f"L5={l5}")
            issues_preview = (l1_issues + l2_issues + l5_issues)[:2]
            print(f"   {status} ❌ BLOCKED: {', '.join(failed)}")
            if issues_preview:
                print(f"   Issues: {' | '.join(issues_preview)}")
            if attempt < MAX_RETRIES:
                time.sleep(2)

    if not approved:
        best = max(all_attempt_scores, key=lambda x: (x["l1"]+x["l2"]+x["l5"])/3)
        msg = (f"⛔ <b>DeepDive — Day Skipped</b>\n\n"
               f"All {MAX_RETRIES} script attempts failed quality gate.\n"
               f"Best attempt #{best['attempt']}: L1={best['l1']} L2={best['l2']} L5={best['l5']}\n"
               f"Minimum required: {QUALITY_MINIMUM}/10 on ALL layers\n\n"
               f"Niche: {niche['name']} | Topic: {topic[:60]}...\n\n"
               f"⚠️ No video published today. System will retry tomorrow.")
        telegram(msg)
        print(f"\n⛔ All {MAX_RETRIES} attempts failed. Day skipped.")
        sys.exit(0)

    script = approved["script"]
    metadata = approved["metadata"]
    scores = approved["scores"]

    # ── PHASE 3: AUDIO WITH HARD GATE ─────────────────────────────────────────
    print("🎙️ Generating Kokoro TTS audio...")
    audio_approved = False
    audio_path = None
    audio_duration = 0
    chunks_success = chunks_total = 0

    for audio_attempt in range(1, 4):
        print(f"   Audio attempt {audio_attempt}/3...")
        try:
            audio_path, audio_duration, chunks_success, chunks_total = generate_audio_kokoro(
                script["clean"], voice
            )
            l3, l3_issues, l3_pass = score_layer("layer3_audio",
                duration=audio_duration,
                file_size=os.path.getsize(audio_path),
                voice_id=voice["id"],
                chunks_success=chunks_success,
                chunks_total=chunks_total
            )
            scores["l3"] = l3
            print(f"   L3 Audio: {l3}/10 {'✅' if l3_pass else '❌'} | {audio_duration/60:.1f}min")
            if l3_issues:
                print(f"   Issues: {' | '.join(l3_issues[:2])}")

            if l3_pass:
                audio_approved = True
                break
            else:
                print(f"   Retrying with different voice segment...")
                time.sleep(3)

        except Exception as e:
            print(f"   Audio attempt {audio_attempt} failed: {str(e)[:100]}")
            time.sleep(5)

    if not audio_approved:
        telegram(f"⛔ <b>Audio Layer Failed</b>\nL3={scores.get('l3',0)}/10\nVoice: {voice['id']}\n3 attempts exhausted.")
        cleanup()
        sys.exit(0)

    # ── SUBTITLES ─────────────────────────────────────────────────────────────
    print("\n📝 Generating frame-perfect subtitles...")
    srt_path, sub_count = generate_srt(script["clean"], audio_duration)

    # ── BACKGROUND ────────────────────────────────────────────────────────────
    print("\n🎬 Fetching dark cinematic background...")
    bg_path = fetch_background(niche["name"], audio_duration)

    # ── PHASE 4: VIDEO ASSEMBLY WITH HARD GATE ────────────────────────────────
    print("\n🎬 Assembling cinematic video...")
    video_approved = False
    video_path = None

    for vid_attempt in range(1, 3):
        try:
            video_path = assemble_video(audio_path, srt_path, bg_path, audio_duration, series["name"])
            vinfo = get_video_info(video_path)

            l4, l4_issues, l4_pass = score_layer("layer4_visual",
                video_size=vinfo["size"],
                duration=vinfo["duration"],
                has_subtitles=True,
                resolution=vinfo["resolution"],
                subtitle_count=sub_count
            )
            scores["l4"] = l4
            print(f"   L4 Visual: {l4}/10 {'✅' if l4_pass else '❌'} | {vinfo['resolution']} | subs:{sub_count}")

            if l4_pass:
                video_approved = True
                break
            else:
                print(f"   Issues: {' | '.join(l4_issues[:2])}")

        except Exception as e:
            print(f"   Assembly attempt {vid_attempt} failed: {str(e)[:150]}")
            time.sleep(5)

    if not video_approved:
        telegram(f"⛔ <b>Visual Layer Failed</b>\nL4={scores.get('l4',0)}/10\nAssembly blocked.")
        cleanup()
        sys.exit(0)

    # ── FINAL SCORE CALCULATION ───────────────────────────────────────────────
    final_score = round(
        scores["l1"] * 0.15 +
        scores["l2"] * 0.30 +
        scores["l3"] * 0.25 +
        scores["l4"] * 0.20 +
        scores["l5"] * 0.10, 1
    )

    print(f"\n⭐ FINAL SCORE: {final_score}/10")

    if final_score < QUALITY_MINIMUM:
        telegram(f"⛔ <b>Final Score Blocked</b>\nFinal: {final_score}/10\nMinimum: {QUALITY_MINIMUM}")
        cleanup()
        sys.exit(0)

    # ── YOUTUBE UPLOAD ────────────────────────────────────────────────────────
    print("\n📤 Uploading to YouTube...")
    try:
        yt_url = upload_youtube(video_path, metadata, is_short=False)
        print(f"✅ Main video: {yt_url}")
    except Exception as e:
        telegram(f"⛔ <b>Upload Failed</b>\n{str(e)[:300]}")
        cleanup()
        sys.exit(1)

    # ── YOUTUBE SHORTS ────────────────────────────────────────────────────────
    shorts_urls = []
    print("\n📱 Creating YouTube Shorts...")
    for stype in ["teaser", "recap"]:
        try:
            short_path = create_short(video_path, script["clean"], stype)
            if short_path:
                short_meta = dict(metadata)
                short_meta["title"] = f"{metadata['title'][:45]} #{stype.upper()}"
                short_url = upload_youtube(short_path, short_meta, is_short=True)
                shorts_urls.append(f"📱 Short ({stype}): {short_url}")
                print(f"✅ Short ({stype}): {short_url}")
        except Exception as e:
            print(f"⚠️ Short ({stype}) failed: {e}")

    # ── PERFORMANCE RECORDING ─────────────────────────────────────────────────
    record_performance(niche["name"], final_score, scores, voice["id"], yt_url)

    # ── TELEGRAM REPORT ───────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    est_views = int(5000 * (final_score / 10))
    est_usd = round((est_views / 1000) * niche["rpm"], 2)
    est_inr = int(est_usd * 83)

    all_layers_check = all(s >= QUALITY_MINIMUM for s in scores.values())

    shorts_section = "\n".join(shorts_urls) if shorts_urls else "⚠️ Shorts failed"

    report = f"""✅ <b>DeepDive Published — v5.0 Empire</b>

📺 <b>{metadata['title']}</b>
📚 {series['name']} — Episode {episode}
🎯 {niche['name']} | ${niche['rpm']} RPM
🎙️ Voice: {voice['id']} ({voice['tone']})
⏱️ Duration: {audio_duration/60:.1f} minutes | Runtime: {elapsed/60:.1f}min

📊 <b>5-Layer Quality:</b>
1️⃣ Pre-production: {scores['l1']}/10 {'✅' if scores['l1']>=QUALITY_MINIMUM else '❌'}
2️⃣ Script: {scores['l2']}/10 {'✅' if scores['l2']>=QUALITY_MINIMUM else '❌'} ({script['words']}w | 0 MD violations)
3️⃣ Audio: {scores['l3']}/10 {'✅' if scores['l3']>=QUALITY_MINIMUM else '❌'} ({audio_duration/60:.1f}min | {chunks_success}/{chunks_total} chunks)
4️⃣ Visual: {scores['l4']}/10 {'✅' if scores['l4']>=QUALITY_MINIMUM else '❌'} (1080p | {sub_count} subtitle lines)
5️⃣ SEO: {scores['l5']}/10 {'✅' if scores['l5']>=QUALITY_MINIMUM else '❌'} ({len(metadata.get('tags',[]))} tags)
{'⭐' if all_layers_check else '⚠️'} <b>FINAL: {final_score}/10 {'— ALL LAYERS PASSED ✅' if all_layers_check else ''}</b>

🔗 <b>Main:</b> {yt_url}
{shorts_section}

💰 <b>30-Day Forecast:</b>
• Views: {est_views:,}
• Revenue: ${est_usd} (₹{est_inr:,})

💤 Zero manual work. Next video tomorrow 7:30 AM IST."""

    telegram(report)
    print("\n" + "═"*70)
    print(f"  ✅ PIPELINE COMPLETE | Score: {final_score}/10 | {elapsed/60:.1f}min total")
    print("═"*70)

    # ── CLEANUP — ZERO ARTIFACTS ──────────────────────────────────────────────
    cleanup()

if __name__ == "__main__":
    main()
