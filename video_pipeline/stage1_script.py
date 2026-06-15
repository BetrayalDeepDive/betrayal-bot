#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE — STAGE 1: VIRAL INTELLIGENCE + MASTERPIECE SCRIPT ENGINE
TARGET: 1 Million subscribers across all channels by Month 6
STYLE:  Psychological dread INSIDE true crime investigation
AI:     Gemini 2.0 Flash primary | Groq fallback | rate-limit protected
GATE:   8.5 minimum | 15 max attempts | 5-title CTR scoring
NEW:    12 psychological dread triggers | SSML pacing injection
"""

import os, sys, json, re, time, random, datetime, requests
from pathlib import Path
from groq import Groq

GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_RUN_ID  = os.environ.get("GITHUB_RUN_ID", "manual")

groq_client = Groq(api_key=GROQ_API_KEY)
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OUTPUT_DIR  = Path("/tmp/pipeline_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUALITY_MIN = 8.5
MAX_RETRIES = 15
MIN_WORDS   = 2200
MAX_WORDS   = 2600

# 12 proven psychological dread mechanisms
DREAD_TRIGGERS = {
    "proximity":    "The threat is closer than anyone thinks — someone deeply trusted",
    "duration":     "This was happening far longer than anyone imagined possible",
    "scale":        "The number affected is staggering and keeps growing with every discovery",
    "institutional":"Every system designed to protect people failed completely",
    "invisibility": "Nobody saw it because nobody truly wanted to see it",
    "normality":    "It happened in ordinary settings to completely ordinary people",
    "complicity":   "Others knew and said nothing — making them partly responsible",
    "competence":   "The perpetrator was respected, trusted, admired by everyone",
    "detail":       "One specific small detail makes the horror utterly concrete and real",
    "reversal":     "Everything the audience believed was exactly backwards",
    "cost":         "What was destroyed can never be fully rebuilt or recovered",
    "repetition":   "It happened again and again while everyone around them looked away"
}


def call_gemini(prompt, temp=0.90, tokens=4000):
    for attempt in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temp, "maxOutputTokens": tokens, "topP": 0.95},
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                },
                timeout=120
            )
            if r.status_code == 200:
                cands = r.json().get("candidates", [])
                if cands:
                    return cands[0]["content"]["parts"][0]["text"]
            elif r.status_code == 429:
                time.sleep(60 * (attempt + 1))
            else:
                time.sleep(15)
        except Exception as e:
            print(f"   Gemini {attempt+1}: {str(e)[:60]}")
            time.sleep(20)
    raise Exception("Gemini failed")


def call_groq(prompt, temp=0.7, tokens=1200):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp, max_tokens=min(tokens, 2000)
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60 * (2 ** attempt))
            else:
                raise
    raise Exception("Groq rate limited")


def call_ai(prompt, temp=0.90, tokens=4000, prefer="gemini"):
    if prefer == "gemini":
        try:
            return call_gemini(prompt, temp, tokens)
        except:
            return call_groq(prompt, temp, min(tokens, 2000))
    else:
        try:
            return call_groq(prompt, temp, min(tokens, 2000))
        except:
            return call_gemini(prompt, temp, tokens)


def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except:
        pass


NICHES = [
    {
        "name": "betrayal", "rpm": 12.82, "weight": 3,
        "series": "The Betrayal Files", "watermark": "THE BETRAYAL FILES",
        "primary_trigger": "competence", "secondary_trigger": "duration",
        "topics": [
            "A CFO secretly redirected 4.7 million dollars to offshore accounts across six years. His CEO called him his closest friend at every board meeting.",
            "Two childhood best friends built a restaurant group together over 15 years. Security footage revealed one had been stealing from the till since opening day.",
            "A son forged his elderly parents signatures for eleven years to drain their retirement. He visited them every single Sunday for dinner.",
            "The mentor who took credit for her proteges decade of research. She was exposed live on stage at the worlds largest academic conference.",
            "A church treasurer stole 3.2 million in disaster relief donations over nine years while personally leading the Sunday collection every week.",
            "A business partner filed every patent in his own name the night before a 200 million dollar acquisition completed.",
            "An HR director fabricated performance reviews to destroy every career of every employee who ever filed a complaint against her.",
        ]
    },
    {
        "name": "legal_drama", "rpm": 16.50, "weight": 4,
        "series": "Justice Served", "watermark": "JUSTICE SERVED",
        "primary_trigger": "institutional", "secondary_trigger": "duration",
        "topics": [
            "A wrongful murder conviction lasted 22 years. It was overturned because one detective checked a timestamp every previous investigator had dismissed.",
            "A 23-year-old paralegal found a forged signature that 14 senior partners had each reviewed and missed in a billion dollar merger.",
            "Eight hundred ordinary people filed a class action that dismantled a pharmaceutical network and permanently rewrote federal drug law.",
            "A federal judge held undisclosed financial interests across 47 connected cases. Nobody checked for a decade because nobody thought to look.",
            "A corporate attorney secretly recorded 200 privileged client meetings across three years then played every tape in open court after switching sides.",
        ]
    },
    {
        "name": "finance_scandal", "rpm": 19.00, "weight": 4,
        "series": "Dark Money", "watermark": "DARK MONEY",
        "primary_trigger": "scale", "secondary_trigger": "invisibility",
        "topics": [
            "A penny stock ring extracted 470 million from retail investors over 7 years using a network of entirely fake financial analysts.",
            "A regional bank concealed 3.2 billion in non-performing loans through 40 shell companies across 6 countries before collapsing and destroying thousands.",
            "A rogue bond trader hid 900 million in losses across three years by exploiting a single overlooked flaw in his own banks risk system.",
            "A private wealth desk quietly moved client retirement funds into the firms own failing investments for five straight years with zero disclosure.",
        ]
    },
    {
        "name": "true_crime", "rpm": 10.50, "weight": 2,
        "series": "Dark Truth", "watermark": "DARK TRUTH",
        "primary_trigger": "invisibility", "secondary_trigger": "duration",
        "topics": [
            "An identity theft ring operated invisibly for 11 years targeting exclusively people who had died within the previous 30 days.",
            "A cold case murder solved 28 years later when a genealogy hobbyist uploaded her DNA and accidentally matched the killers nephew.",
            "A doctor defrauded Medicare of 8 million over 12 years while maintaining a perfect 5-star patient satisfaction rating throughout.",
        ]
    },
    {
        "name": "psych_thriller", "rpm": 11.50, "weight": 2,
        "series": "Mind Games", "watermark": "MIND GAMES",
        "primary_trigger": "competence", "secondary_trigger": "invisibility",
        "topics": [
            "The documented psychological sequence cult leaders use to make educated professionals completely surrender their identity in under 90 days.",
            "How clinical narcissists in executive roles systematically destroy the careers of every subordinate who shows potential to outperform them.",
            "The neuroscience of why intelligent people defend their abusers with greater intensity the more concrete evidence is presented.",
        ]
    },
    {
        "name": "business_fraud", "rpm": 13.00, "weight": 3,
        "series": "Corporate Crimes", "watermark": "CORPORATE CRIMES",
        "primary_trigger": "competence", "secondary_trigger": "scale",
        "topics": [
            "A SaaS company raised 340 million from 22 institutional investors. The product had been scripted and faked from the very first pitch.",
            "One developer pledged the same 12 properties as collateral to 9 different lenders simultaneously across 4 years. Not one lender checked.",
            "A Big Four auditing firm signed off on six years of fraudulent annual reports for a company it had internally flagged as critical risk.",
        ]
    },
    {
        "name": "ai_tech_dark", "rpm": 16.00, "weight": 3,
        "series": "Algorithm Exposed", "watermark": "ALGORITHM EXPOSED",
        "primary_trigger": "proximity", "secondary_trigger": "repetition",
        "topics": [
            "Leaked documents proved a major platform deliberately tuned its algorithm to maximize outrage after its own safety team formally objected.",
            "The data broker industry builds and sells detailed behavioral profiles on 300 million people. Not one gave consent.",
            "The documented 18-month pipeline through which recommendation algorithms move ordinary users toward extreme positions.",
        ]
    },
    {
        "name": "health_scandal", "rpm": 12.00, "weight": 2,
        "series": "Toxic Trust", "watermark": "TOXIC TRUST",
        "primary_trigger": "institutional", "secondary_trigger": "scale",
        "topics": [
            "Clinical data showing 340 percent increased cardiac risk was suppressed for 6 years while 40 million patients took the drug daily.",
            "A medical device company sold a spinal implant for 4 years after internal tests confirmed a 23 percent catastrophic failure rate.",
        ]
    },
]

VOICE_MAP = {
    "betrayal":       [{"id":"am_fenrir","lang":"a","desc":"Darkest US male — genuine chills"},
                       {"id":"bf_isabella","lang":"b","desc":"Haunting British female"},
                       {"id":"bm_lewis","lang":"b","desc":"Deep cinematic British male"}],
    "legal_drama":    [{"id":"bm_george","lang":"b","desc":"BBC documentary gravitas"},
                       {"id":"bf_emma","lang":"b","desc":"Sharp authoritative British female"},
                       {"id":"af_nova","lang":"a","desc":"Dark journalistic US female"}],
    "finance_scandal":[{"id":"bm_daniel","lang":"b","desc":"Cold measured British — financial authority"},
                       {"id":"am_adam","lang":"a","desc":"Deep commanding US male"},
                       {"id":"bm_lewis","lang":"b","desc":"Deep cinematic British male"}],
    "true_crime":     [{"id":"bm_fable","lang":"b","desc":"Master dark storyteller"},
                       {"id":"am_fenrir","lang":"a","desc":"Darkest US male"},
                       {"id":"af_nova","lang":"a","desc":"Dark journalistic US female"}],
    "psych_thriller": [{"id":"bf_isabella","lang":"b","desc":"Haunting intense British female"},
                       {"id":"am_michael","lang":"a","desc":"Intense investigative US male"},
                       {"id":"bm_fable","lang":"b","desc":"Dark storytelling British male"}],
    "business_fraud": [{"id":"am_puck","lang":"a","desc":"Urgent US male — relentless tension"},
                       {"id":"bm_daniel","lang":"b","desc":"Cold measured British male"},
                       {"id":"am_adam","lang":"a","desc":"Deep commanding US male"}],
    "ai_tech_dark":   [{"id":"am_adam","lang":"a","desc":"Deep authoritative US male"},
                       {"id":"bf_emma","lang":"b","desc":"Sharp British female"},
                       {"id":"am_michael","lang":"a","desc":"Intense investigative US male"}],
    "health_scandal": [{"id":"af_heart","lang":"a","desc":"Emotionally devastating US female"},
                       {"id":"bm_george","lang":"b","desc":"BBC documentary gravitas"},
                       {"id":"bm_fable","lang":"b","desc":"Dark storytelling British male"}],
}


# Day-of-week RPM mapping — max revenue per day
# Tue/Thu: highest ad spend days → highest RPM niches
DAY_NICHE_PRIORITY = {
    0: ["betrayal", "true_crime", "psych_thriller"],           # Monday
    1: ["finance_scandal", "legal_drama", "ai_tech_dark"],     # Tuesday — HIGH RPM
    2: ["business_fraud", "betrayal", "health_scandal"],       # Wednesday
    3: ["finance_scandal", "legal_drama", "ai_tech_dark"],     # Thursday — HIGH RPM
    4: ["true_crime", "psych_thriller", "business_fraud"],     # Friday
}

def get_state():
    """Load voice/niche state to avoid repeating yesterday"""
    state_file = OUTPUT_DIR / "channel_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except:
            pass
    return {"last_niche": "", "last_voice": "", "used_niches": [], "used_voices": [], "makeup_pending": False, "weekly_videos": []}

def save_state(state):
    state_file = OUTPUT_DIR / "channel_state.json"
    state_file.write_text(json.dumps(state, indent=2))

def get_niche():
    """
    RPM-optimised niche selection by day.
    Never repeats same niche as yesterday.
    Uses day-of-week priority for maximum revenue.
    """
    force_niche = os.environ.get("FORCE_NICHE", "").strip()
    if force_niche:
        match = next((n for n in NICHES if n["name"] == force_niche), None)
        if match:
            return match

    state = get_state()
    last_niche = state.get("last_niche", "")
    weekday = datetime.datetime.now().weekday()
    priority = DAY_NICHE_PRIORITY.get(weekday, [n["name"] for n in NICHES])

    # Pick highest priority niche that wasn't used yesterday
    for niche_name in priority:
        if niche_name != last_niche:
            match = next((n for n in NICHES if n["name"] == niche_name), None)
            if match:
                return match

    # Fallback: RPM-weighted pool excluding yesterday
    pool = []
    for n in NICHES:
        if n["name"] != last_niche:
            pool.extend([n] * n["weight"])
    return pool[datetime.datetime.now().timetuple().tm_yday % len(pool)]


def get_episode(niche_name):
    n = next(x for x in NICHES if x["name"] == niche_name)
    return (datetime.datetime.now().timetuple().tm_yday // n["weight"]) + 1


def get_voice(niche_name):
    """
    Select voice for niche — never repeats yesterday's voice.
    Rotates through all 12 voices over time for variety.
    """
    state = get_state()
    last_voice = state.get("last_voice", "")
    opts = VOICE_MAP.get(niche_name, [{"id": "bm_george", "lang": "b", "desc": "BBC gravitas"}])

    # Filter out yesterday's voice
    available = [v for v in opts if v["id"] != last_voice]
    if not available:
        available = opts  # All options same voice — just use any

    day = datetime.datetime.now().timetuple().tm_yday
    return available[day % len(available)]


def strip(text):
    """Double-pass markdown stripper — zero tolerance"""
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
        text = re.sub(r'_{1,3}([^_\n]+)_{1,3}', r'\1', text)
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+•·▪]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.)]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'`+[^`]*`+', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\([^)]*(?:narrator|music|sfx|pause|cut|scene)[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[#@$%^&*{}<>|\\~`]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def count_md(text):
    return len(re.findall(r'[#*_`\[\]{}<>\\]', text))


def inject_pacing(clean_script):
    """Ensure strategic pacing markers exist at right density for Kokoro TTS"""
    paragraphs = clean_script.split('\n\n')
    enhanced = []
    for i, para in enumerate(paragraphs):
        if not para.strip():
            continue
        stripped = para.rstrip()
        if stripped and stripped[-1] not in '.!?':
            para = stripped + '.'
        enhanced.append(para)
    return '\n\n'.join(enhanced)


def get_viral_patterns(niche):
    prompt = f"""You are a YouTube analytics expert who has studied the top 50 videos in the {niche['name']} niche — each with 2-50 million views.

Primary psychological mechanism: {DREAD_TRIGGERS[niche['primary_trigger']]}
Secondary mechanism: {DREAD_TRIGGERS[niche['secondary_trigger']]}

Return ONLY this JSON:
{{
    "hook_formulas": [
        "Hook formula 1 used in 10M+ view videos in this exact niche",
        "Hook formula 2 alternative approach",
        "Hook formula 3 third approach"
    ],
    "title_formulas": [
        "Title formula 1 with [SUBJECT] [ACTION] placeholders",
        "Title formula 2",
        "Title formula 3"
    ],
    "emotional_arc": ["0-15%","15-40%","40-65%","65-85%","85-100%"],
    "power_words": ["word1","word2","word3","word4","word5","word6","word7","word8","word9","word10"],
    "sentence_rhythm": "exact pacing pattern",
    "twist_position": "percentage",
    "retention_hooks": ["2-min line","7-min line","12-min line"],
    "thumbnail_formula": "exact visual formula for 8%+ CTR",
    "forbidden_phrases": ["phrase1","phrase2","phrase3","phrase4","phrase5"],
    "psychological_escalation": "how to darken each paragraph beyond the last"
}}"""

    try:
        text = call_ai(prompt, temp=0.7, tokens=1000, prefer="groq")
        text = re.sub(r'```json|```', '', text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"   Patterns error: {e}")

    return {
        "hook_formulas": [
            "The number is the hook. [Amount]. Gone. In [timeframe]. Nobody saw it coming.",
            "For [X] years [person] was the most trusted [role] in [place]. That trust was the weapon.",
            "What investigators found in [location] on [day] was so unexpected they initially refused to believe it."
        ],
        "title_formulas": [
            "The [Role] Who [Action] [Amount] for [Duration] — Nobody Suspected",
            "How [Subject] [Action] [Number] People Without Anyone Noticing",
            "The [Duration] [Crime] That Destroyed [Number] [Families/Lives]"
        ],
        "emotional_arc": ["0-15%: shock","15-40%: dread","40-65%: horror","65-85%: revelation","85-100%: reckoning"],
        "power_words": ["exposed","destroyed","vanished","stolen","betrayed","silenced","buried","discovered","collapsed","manipulated"],
        "sentence_rhythm": "9-12 word sentences. Then one 4-word sentence. Then build again. Constant variation.",
        "twist_position": "65% through",
        "retention_hooks": [
            "What you are about to hear changed this investigation permanently.",
            "This is the moment investigators found what had been hidden from the very beginning.",
            "What was discovered next was so unexpected that even seasoned investigators went completely silent."
        ],
        "thumbnail_formula": "Pure black background, single face in extreme close-up showing terror or betrayal, 3-word blood-red text, no borders",
        "forbidden_phrases": ["in conclusion","it is worth noting","interestingly","moreover","to summarize"],
        "psychological_escalation": "Scale first, then personal detail, then institutional failure, then duration, then the thing that can never be undone"
    }


def generate_script(niche, topic, patterns, episode, attempt):
    series       = niche["series"]
    hook         = random.choice(patterns["hook_formulas"])
    power_words  = ", ".join(patterns["power_words"][:8])
    arc          = " | ".join(patterns["emotional_arc"])
    retention    = "\n".join([f"  {h}" for h in patterns["retention_hooks"]])
    forbidden    = ", ".join(patterns.get("forbidden_phrases", []))
    twist_pos    = patterns["twist_position"]
    rhythm       = patterns["sentence_rhythm"]
    escalation   = patterns.get("psychological_escalation", "")
    primary_t    = DREAD_TRIGGERS[niche["primary_trigger"]]
    secondary_t  = DREAD_TRIGGERS[niche["secondary_trigger"]]
    darkness     = min(attempt * 7, 100)
    temp         = min(0.82 + attempt * 0.02, 0.96)

    prompt = f"""You are the greatest dark investigative documentary writer alive.
You write Episode {episode} of "{series}" for The Betrayal DeepDive.
Goal: 1 million YouTube subscribers across all channels by Month 6.

TOPIC: {topic}

WRITE: A {MIN_WORDS}-{MAX_WORDS} word spoken narration.
TONE: Psychological dread INSIDE a true crime investigation.
The viewer feels like they are uncovering something dangerous — something real — something that could happen to them or someone they love.
Darkness level: {darkness}%.

PRIMARY PSYCHOLOGICAL TRIGGER: {primary_t}
SECONDARY TRIGGER: {secondary_t}
ESCALATION METHOD: {escalation}

VIRAL INTELLIGENCE:
Hook formula: {hook}
Power words to weave naturally: {power_words}
Emotional arc: {arc}
Sentence rhythm: {rhythm}
Twist position: {twist_pos}
Retention hooks:
{retention}
Forbidden — using any of these fails the script: {forbidden}

ABSOLUTE RULES — VIOLATIONS REJECT THE SCRIPT:
1. ZERO markdown — no asterisks hashtags underscores brackets backticks
2. ZERO stage directions — no music pause cut to narrator
3. Pure spoken English only — every word must be speakable
4. MAX 13 words per sentence — never more
5. Never start 3 consecutive sentences with the same word
6. Every paragraph must escalate darker than the previous one
7. Specific numbers dates amounts — make it feel documented and real
8. Never use forbidden phrases ever

STRUCTURE — seamless flowing paragraphs — zero section labels:

HOOK — 3 sentences:
The most disturbing sentence ever written about this topic.
A specific detail that makes it immediately worse.
A question that makes stopping physically impossible.

THE WORLD BEFORE — sentences 4-22:
The world as it appeared before it broke.
Make the audience care deeply about who will be destroyed.
Plant exactly 3 small specific details that seem ordinary now.
They become devastating at the twist.

RISING DREAD — 18-22% of script:
First signs something was wrong. Each explainable alone.
Together they form a pattern nobody wanted to name.
Never announce it — let the audience feel it assemble.

THE DESCENT — 28-32%:
Full scale of what was happening beneath the surface.
Specific. Documented. Amounts dates locations names.
Apply the PRIMARY TRIGGER here — make it visceral and physical.

RETENTION HOOK — exact 7-minute position — use the second hook above word for word.

THE MAJOR TWIST — at {twist_pos}:
One sentence that collapses everything understood so far.
Then a paragraph break — silence implied.
Reframe every planted detail through this devastating new lens.

THE HUMAN COST — 10-12%:
Not statistics. Specific people. What this did to their actual lives.
Apply the SECONDARY TRIGGER here. Peak emotional devastation.

THE AFTERMATH — 8%:
What the system did. What it catastrophically failed to do.
Most disturbing: what remains completely unchanged.

THE RECKONING — 5%:
Two paragraphs of hard truth about trust and power.
No moralizing. No advice. Just the plain unbearable truth.

SERIES CLOSE:
One haunting line connecting to next episode of {series}.
One natural sentence — subscribe to The Betrayal DeepDive.

RETURN ONLY THE NARRATION TEXT.
No labels. No markers. No explanations.
Every word exactly as the narrator will speak it."""

    raw   = call_ai(prompt, temp=temp, tokens=4000, prefer="gemini")
    clean = strip(strip(raw))
    clean = inject_pacing(clean)
    violations = count_md(clean)
    words = len(clean.split())

    return {
        "topic": topic, "raw": raw, "clean": clean,
        "words": words, "violations": violations,
        "attempt": attempt, "episode": episode, "series": series
    }


def generate_and_score_titles(niche, script, patterns, episode):
    """Generate 5 title variants. Score on CTR potential. Return winner."""
    prompt = f"""Generate 5 YouTube title variants for this dark investigative documentary.

Niche: {niche['name']} | Series: {niche['series']} | Episode: {episode}
Topic: {script['topic']}
Script opening: {script['clean'][:250]}
Title formulas: {json.dumps(patterns['title_formulas'])}

Rules for each title:
- Exactly 58-70 characters
- Contains at least one power word: {', '.join(patterns['power_words'][:6])}
- Creates instant morbid curiosity
- Factual — not clickbait
- References the specific topic

Return ONLY this JSON:
{{
    "titles": [
        {{"title": "Title 1", "ctr_score": 8.5, "reason": "why this gets clicks"}},
        {{"title": "Title 2", "ctr_score": 7.8, "reason": "why"}},
        {{"title": "Title 3", "ctr_score": 9.1, "reason": "why"}},
        {{"title": "Title 4", "ctr_score": 8.2, "reason": "why"}},
        {{"title": "Title 5", "ctr_score": 7.5, "reason": "why"}}
    ]
}}"""

    try:
        text = call_ai(prompt, temp=0.75, tokens=800, prefer="groq")
        text = re.sub(r'```json|```', '', text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            data = json.loads(m.group())
            titles = data.get("titles", [])
            if titles:
                best = max(titles, key=lambda x: x.get("ctr_score", 0))
                print(f"   Best title (CTR {best['ctr_score']}): {best['title']}")
                return best["title"]
    except Exception as e:
        print(f"   Title scoring error: {e}")

    return f"{niche['series']} Ep{episode}: The Investigation That Changed Everything"


def generate_metadata(niche, script, patterns, episode, best_title):
    prompt = f"""Generate complete YouTube metadata for Episode {episode} of "{niche['series']}".

Title (use exactly): {best_title}
Niche: {niche['name']} | RPM: ${niche['rpm']}
Topic: {script['topic']}
Script preview: {script['clean'][:300]}
Thumbnail formula: {patterns['thumbnail_formula']}

Return ONLY valid JSON — no other text:
{{
    "title": "{best_title}",
    "description": "450-word YouTube description. First 3 lines are standalone gripping hooks for Google search. Include 5 timestamp chapters. End with The Betrayal DeepDive subscribe CTA. Include search keywords naturally throughout.",
    "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13","tag14","tag15"],
    "thumbnail_text": "3 WORDS MAX ALL CAPS — creates instant dread",
    "thumbnail_concept": "Exact visual: subject expression colors text placement — achieves 8% plus CTR",
    "chapters": [
        {{"time": "0:00",  "title": "The Opening Shock"}},
        {{"time": "3:30",  "title": "Chapter 2 title"}},
        {{"time": "7:00",  "title": "The Discovery"}},
        {{"time": "11:00", "title": "The Major Twist"}},
        {{"time": "14:30", "title": "The Full Truth"}}
    ],
    "category": "22"
}}"""

    try:
        text = call_ai(prompt, temp=0.65, tokens=1200, prefer="groq")
        text = re.sub(r'```json|```', '', text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            data = json.loads(m.group())
            data["title"] = best_title
            return data
    except Exception as e:
        print(f"   Metadata error: {e}")

    return {
        "title": best_title,
        "description": f"Episode {episode} of {niche['series']}. {script['topic']}. Subscribe to The Betrayal DeepDive for weekly investigations.",
        "tags": [niche['name'], "investigation", "documentary", "exposed", "deepdive", "crime", "betrayal", "scandal", "dark", "truth", "revealed", "series", "shocking", "justice", "mystery"],
        "thumbnail_text": "NOBODY KNEW",
        "thumbnail_concept": "Black background, face extreme close-up showing terror, blood red text at bottom",
        "chapters": [{"time": "0:00", "title": "The Opening Shock"}, {"time": "3:30", "title": "The Setup"}, {"time": "7:00", "title": "The Discovery"}, {"time": "11:00", "title": "The Twist"}, {"time": "14:30", "title": "The Aftermath"}],
        "category": "22"
    }


def score_script(script, meta):
    """
    CALIBRATED SCORING — weights only what actually matters for YouTube success.
    Primary gates: word count + zero markdown + hook strength + tone
    Secondary (bonus only): title length, tags, description — never block on these
    """
    issues = []
    s = 5.0
    w = script["words"]
    md = script["violations"]
    clean = script["clean"]
    title = meta.get("title", "")
    tags = meta.get("tags", [])
    desc = meta.get("description", "")

    # GATE 1 — Word count (most important — determines video length)
    if w >= MIN_WORDS:
        s += 2.8
    elif w >= 1800:
        s += 1.5
        issues.append(f"Words {w} below {MIN_WORDS} — slightly short")
    elif w >= 1400:
        s += 0.5
        issues.append(f"Script {w}w — will produce under 15min video")
    else:
        s -= 1.5
        issues.append(f"FATAL: {w} words — too short")

    # GATE 2 — Zero markdown (hard requirement — symbols reach TTS)
    if md == 0:
        s += 2.2
    elif md <= 3:
        s += 0.8
        issues.append(f"WARNING: {md} markdown symbols — may reach TTS")
    else:
        s -= 1.5
        issues.append(f"FATAL: {md} markdown violations")

    # GATE 3 — Sentence rhythm (determines TTS quality and tension)
    sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+', clean) if len(x.strip()) > 5]
    if sents:
        avg = sum(len(x.split()) for x in sents) / len(sents)
        if avg <= 12:
            s += 1.3
        elif avg <= 16:
            s += 0.8
        elif avg <= 20:
            s += 0.3
            issues.append(f"Avg sentence {avg:.0f}w — prefer under 13")
        else:
            issues.append(f"Sentences too long: {avg:.0f}w average")

    # GATE 4 — Hook strength (determines click-through and retention)
    hook = clean[:500].lower()
    hook_score = sum(1 for word in [
        "million", "billion", "nobody", "secret", "exposed", "stolen", "destroyed",
        "trusted", "betrayed", "discovered", "truth", "hidden", "collapsed",
        "years", "deceived", "manipulated", "silenced", "vanished", "fraud",
        "corruption", "evidence", "records", "never", "years"
    ] if word in hook)
    if hook_score >= 4:
        s += 1.0
    elif hook_score >= 2:
        s += 0.6
        issues.append("Hook could be stronger")
    else:
        s += 0.1
        issues.append("Weak hook — few impact words in opening")

    # GATE 5 — Psychological dread + investigation tone (your unique style)
    full_lower = clean.lower()
    dread_words = ["discovered", "realized", "found", "revealed", "exposed",
                   "evidence", "records", "files", "documents", "investigation",
                   "investigators", "uncovered", "hidden", "concealed"]
    dread_count = sum(1 for word in dread_words if word in full_lower)
    if dread_count >= 4:
        s += 0.8
    elif dread_count >= 2:
        s += 0.4
    else:
        issues.append("Needs more investigation-style vocabulary")

    # BONUS — CTA present (adds 0.3 max — never blocks)
    close = clean[-500:].lower()
    if "subscribe" in close or "betrayal deepdive" in close:
        s += 0.3

    # BONUS — Title quality (never blocks — bonus only)
    if 50 <= len(title) <= 75:
        s += 0.4
    elif len(title) > 20:
        s += 0.2

    # BONUS — Tags and description (never block — small bonus)
    if len(tags) >= 10:
        s += 0.2
    if len(desc.split()) >= 150:
        s += 0.2

    score = min(round(s, 1), 10.0)
    # Gate: 8.0 minimum — achievable with good script, strict on critical elements
    return score, issues, score >= 8.0


def main():
    print("\n" + "=" * 65)
    print("  STAGE 1: Viral Intelligence + Masterpiece Script Engine")
    print("  Target: 1M subscribers by Month 6")
    print("  Style: Psychological dread inside true crime investigation")
    print("=" * 65 + "\n")

    niche   = get_niche()
    topic   = random.choice(niche["topics"])
    voice   = get_voice(niche["name"])
    episode = get_episode(niche["name"])

    print(f"Niche: {niche['name']} | ${niche['rpm']} RPM")
    print(f"Series: {niche['series']} — Episode {episode}")
    print(f"Topic: {topic}")
    print(f"Voice: {voice['id']} — {voice['desc']}")
    print(f"Triggers: {niche['primary_trigger']} + {niche['secondary_trigger']}\n")

    print("Loading viral intelligence patterns...")
    patterns = get_viral_patterns(niche)
    print("Patterns loaded\n")

    approved    = None
    best_score  = 0
    last_script = None
    last_meta   = None
    last_title  = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Attempt {attempt}/{MAX_RETRIES}...")
        try:
            script     = generate_script(niche, topic, patterns, episode, attempt)
            best_title = generate_and_score_titles(niche, script, patterns, episode)
            meta       = generate_metadata(niche, script, patterns, episode, best_title)
            score, issues, passed = score_script(script, meta)
            best_score = max(best_score, score)

            icon = "APPROVED" if passed else "BLOCKED"
            print(f"  Score: {score}/10 [{icon}] | {script['words']}w | MD:{script['violations']}")
            if issues and not passed:
                print(f"  Issues: {' | '.join(issues[:2])}")

            # Always track the best attempt for fallback
            if score >= best_score:
                last_script = script
                last_meta   = meta
                last_title  = best_title

            if passed:
                print(f"\nScript APPROVED — Attempt {attempt} | {score}/10\n")
                approved = {"script": script, "meta": meta, "score": score, "best_title": best_title}
                break

            time.sleep(3)

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            time.sleep(20)

    if not approved:
        # Even when day is skipped, save the best script attempt for review
        if last_script and last_meta:
            pipeline_skip = {
                "run_id": GITHUB_RUN_ID, "niche": niche, "topic": topic,
                "voice": voice, "episode": episode,
                "script_clean": last_script["clean"],
                "script_words": last_script["words"],
                "script_series": last_script["series"],
                "script_attempt": last_script["attempt"],
                "meta": last_meta, "best_title": last_title or "",
                "score_stage1": best_score,
                "start_time": datetime.datetime.now().isoformat(),
                "status": "day_skipped"
            }
            with open(OUTPUT_DIR / "pipeline.json", "w") as f:
                json.dump(pipeline_skip, f, indent=2)
            with open(OUTPUT_DIR / "script.txt", "w", encoding="utf-8") as f:
                f.write(last_script["clean"])

        # Mark makeup as pending so tomorrow runs 2 videos
        state = get_state()
        state["makeup_pending"] = True
        state["makeup_niche"] = niche["name"]
        save_state(state)

        telegram(
            f"<b>Stage 1 — Day Skipped</b>\n\n"
            f"All {MAX_RETRIES} attempts failed.\n"
            f"Best score: {best_score}/10\n"
            f"Niche: {niche['name']}\n\n"
            f"MAKEUP VIDEO queued for tomorrow.\n"
            f"Tomorrow will publish 2 videos to make up for today.\n"
            f"Best script saved to artifact for your review."
        )
        gho = os.environ.get("GITHUB_OUTPUT", "")
        if gho:
            with open(gho, "a") as f:
                f.write("approved=false\n")
        sys.exit(0)

    # Check if this is a makeup video run
    is_makeup = os.environ.get("IS_MAKEUP", "false").lower() == "true"

    # Save state to avoid repeating niche/voice tomorrow
    state = get_state()
    state["last_niche"] = niche["name"]
    state["last_voice"] = voice["id"]
    state["makeup_pending"] = False
    if "weekly_videos" not in state:
        state["weekly_videos"] = []
    state["weekly_videos"].append({
        "date": datetime.datetime.now().isoformat(),
        "niche": niche["name"],
        "voice": voice["id"],
        "score": approved["score"],
        "title": approved["best_title"],
        "is_makeup": is_makeup
    })
    # Keep only last 7 days
    state["weekly_videos"] = state["weekly_videos"][-7:]
    save_state(state)

    pipeline = {
        "run_id":         GITHUB_RUN_ID,
        "niche":          niche,
        "topic":          topic,
        "voice":          voice,
        "episode":        episode,
        "is_makeup":      is_makeup,
        "script_clean":   approved["script"]["clean"],
        "script_words":   approved["script"]["words"],
        "script_series":  approved["script"]["series"],
        "script_attempt": approved["script"]["attempt"],
        "meta":           approved["meta"],
        "best_title":     approved["best_title"],
        "score_stage1":   approved["score"],
        "start_time":     datetime.datetime.now().isoformat()
    }

    with open(OUTPUT_DIR / "pipeline.json", "w") as f:
        json.dump(pipeline, f, indent=2)
    with open(OUTPUT_DIR / "script.txt", "w", encoding="utf-8") as f:
        f.write(approved["script"]["clean"])

    gho = os.environ.get("GITHUB_OUTPUT", "")
    if gho:
        with open(gho, "a") as f:
            f.write(f"approved=true\n")
            f.write(f"run_id={GITHUB_RUN_ID}\n")

    makeup_tag = " [MAKEUP VIDEO]" if is_makeup else ""
    telegram(
        f"<b>Stage 1 Complete{makeup_tag}</b>\n\n"
        f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
        f"Series: {niche['series']} Ep{episode}\n"
        f"Words: {approved['script']['words']} | Score: {approved['score']}/10\n"
        f"Triggers: {niche['primary_trigger']} + {niche['secondary_trigger']}\n"
        f"Voice: {voice['id']} — {voice['desc']}\n"
        f"Title: {approved['best_title']}\n\n"
        f"Stage 2: Audio generation starting..."
    )
    print("Stage 1 complete")


if __name__ == "__main__":
    main()
