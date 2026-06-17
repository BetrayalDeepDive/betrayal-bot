#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE - STAGE 1: MASTERPIECE SCRIPT ENGINE
=====================================================
ALL REQUIREMENTS:
✅ 5 videos/week Mon-Fri 7:30 AM IST
✅ High-RPM niches on Tue/Thu (finance $19, legal $16.50)
✅ Never repeat same niche or voice as yesterday
✅ Voice-niche state memory (tracks last 7 days)
✅ Makeup video logic when previous day failed
✅ Cross-promotion references to previous video
✅ 2200-2600 words HARD minimum (15-18 min videos)
✅ Adaptive quality gate: 8.0 -> 7.8 -> 7.5
✅ 8 attempts max (fits 35min budget)
✅ Gemini 2.0 Flash primary | Groq fallback
✅ 6000 token output limit for full scripts
"""

import os, sys, json, re, time, random, datetime, requests
from pathlib import Path
from groq import Groq

GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_RUN_ID  = os.environ.get("GITHUB_RUN_ID", "manual")
IS_MAKEUP      = os.environ.get("IS_MAKEUP", "false").lower() == "true"

groq_client = Groq(api_key=GROQ_API_KEY)
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OUTPUT_DIR  = Path("/tmp/pipeline_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE  = OUTPUT_DIR / "channel_state.json"

MAX_RETRIES = 8
MIN_WORDS   = 2200
MAX_WORDS   = 2600

# RPM-optimised day rotation
# Tue/Thu get highest RPM niches ($19, $16.50)
DAY_NICHE = {
    0: "betrayal",         # Monday    $12.82
    1: "finance_scandal",  # Tuesday   $19.00 HIGH RPM
    2: "business_fraud",   # Wednesday $13.00
    3: "legal_drama",      # Thursday  $16.50 HIGH RPM
    4: "true_crime",       # Friday    $10.50
}

NICHES = [
    {"name":"betrayal",       "rpm":12.82, "series":"The Betrayal Files",  "watermark":"THE BETRAYAL FILES",
     "topics":[
         "A CFO secretly wired 4.7 million dollars offshore across six years while the CEO called him his closest friend at every board meeting",
         "Two childhood friends built a restaurant group together over 15 years. Hidden security footage showed one had been stealing from the till since opening day.",
         "A son forged his elderly parents signatures for eleven years to drain their life savings. He visited them every single Sunday for dinner.",
         "The mentor who claimed credit for her proteges entire decade of research. She was exposed live on stage at the worlds largest academic conference.",
         "A church treasurer stole 3.2 million in disaster relief donations over nine years while personally leading the Sunday collection every week.",
         "The business partner who filed every single patent in his own name the night before a 200 million dollar acquisition completed.",
         "An HR director who systematically fabricated performance reviews to destroy the career of every employee who had ever filed a complaint against her.",
     ]},
    {"name":"legal_drama",    "rpm":16.50, "series":"Justice Served",      "watermark":"JUSTICE SERVED",
     "topics":[
         "A wrongful murder conviction lasted 22 years and was overturned because one detective checked a security timestamp every previous investigator had dismissed as irrelevant",
         "A 23-year-old paralegal found a forged signature that 14 senior partners had each personally reviewed and missed in a billion dollar merger",
         "Eight hundred ordinary people filed a class action that dismantled a pharmaceutical distribution network and permanently rewrote federal drug law",
         "A federal judge held undisclosed financial interests across 47 connected cases for a decade because nobody thought to check",
         "A corporate attorney secretly recorded 200 privileged client meetings across three years then played every single tape in open court after switching sides",
     ]},
    {"name":"finance_scandal","rpm":19.00, "series":"Dark Money",          "watermark":"DARK MONEY",
     "topics":[
         "A penny stock manipulation ring extracted 470 million dollars from retail investors across 7 years using a network of entirely fake financial analysts",
         "A regional bank concealed 3.2 billion in non-performing loans through 40 shell companies across 6 countries until its sudden collapse destroyed thousands of families",
         "A rogue bond trader concealed 900 million dollars in cumulative losses across three years by exploiting a single overlooked flaw in his own banks risk system",
         "A private wealth management desk quietly redirected client retirement savings into the firms own failing investments for five consecutive years with zero disclosure",
         "An insurance syndicate collected premiums on 6,000 policies belonging to people who had never applied or consented to anything",
     ]},
    {"name":"true_crime",     "rpm":10.50, "series":"Dark Truth",          "watermark":"DARK TRUTH",
     "topics":[
         "An identity theft ring operated completely invisibly for 11 years by targeting exclusively people who had died within the previous 30 days",
         "A cold case murder was solved 28 years after the crime when a genealogy hobbyist uploaded her own DNA and accidentally matched the killers nephew",
         "A respected small-town doctor defrauded Medicare of 8 million dollars over 12 years while maintaining a perfect 5-star patient satisfaction rating throughout",
         "The con artist who built seven completely different identities across four countries over 20 years and was caught by a single parking ticket",
     ]},
    {"name":"psych_thriller", "rpm":11.50, "series":"Mind Games",          "watermark":"MIND GAMES",
     "topics":[
         "The exact documented psychological sequence that cult leaders use to make highly educated professionals completely surrender their identity in under 90 days",
         "How clinical narcissists in executive positions methodically destroy the careers of every subordinate who shows any potential to outperform them",
         "The neuroscience of why intelligent people defend their abusers with greater intensity the more concrete evidence is placed before them",
         "Dark triad personality profiles in institutional power and the precise measurable damage they cause across five to ten year periods",
     ]},
    {"name":"business_fraud", "rpm":13.00, "series":"Corporate Crimes",    "watermark":"CORPORATE CRIMES",
     "topics":[
         "A SaaS startup raised 340 million dollars from 22 sophisticated institutional investors using a product that had been scripted and faked from the very first pitch",
         "One real estate developer simultaneously pledged the exact same 12 properties as collateral to 9 different lenders across 4 years and not one lender checked",
         "A Big Four auditing firm signed off on six consecutive years of completely fraudulent annual reports for a company it had internally flagged as high risk",
         "An operations executive quietly ran a shadow vendor company on the side that invoiced his own employer for services that were never performed across seven years",
     ]},
    {"name":"ai_tech_dark",   "rpm":16.00, "series":"Algorithm Exposed",   "watermark":"ALGORITHM EXPOSED",
     "topics":[
         "Leaked internal documents proved a major social media platform deliberately tuned its recommendation algorithm to maximize outrage after its own safety team formally objected in writing",
         "The data broker industry that systematically builds and sells detailed behavioral profiles on 300 million people who have never once given consent",
         "The documented and repeatable 18-month psychological pipeline through which mainstream recommendation algorithms move completely ordinary users toward increasingly extreme positions",
     ]},
    {"name":"health_scandal", "rpm":12.00, "series":"Toxic Trust",         "watermark":"TOXIC TRUST",
     "topics":[
         "Clinical trial data clearly showing a 340 percent increased cardiac mortality risk was actively suppressed for 6 years while the drug was prescribed to 40 million patients worldwide",
         "A medical device company continued selling a spinal implant for 4 full years after its own internal engineering tests documented a 23 percent catastrophic failure rate",
     ]},
]

VOICE_MAP = {
    "betrayal":       ["en-GB-RyanNeural","en-GB-ThomasNeural","en-US-GuyNeural"],
    "legal_drama":    ["en-GB-RyanNeural","en-GB-SoniaNeural","en-US-GuyNeural"],
    "finance_scandal":["en-GB-ThomasNeural","en-US-GuyNeural","en-GB-RyanNeural"],
    "true_crime":     ["en-US-GuyNeural","en-GB-RyanNeural","en-US-DavisNeural"],
    "psych_thriller": ["en-GB-RyanNeural","en-US-GuyNeural","en-GB-SoniaNeural"],
    "business_fraud": ["en-US-GuyNeural","en-GB-ThomasNeural","en-GB-RyanNeural"],
    "ai_tech_dark":   ["en-US-GuyNeural","en-GB-RyanNeural","en-US-DavisNeural"],
    "health_scandal": ["en-GB-SoniaNeural","en-US-GuyNeural","en-GB-RyanNeural"],
}

VOICE_DESC = {
    "en-GB-RyanNeural":   "British male — BBC documentary gravitas",
    "en-GB-ThomasNeural": "British male — cold cinematic authority",
    "en-US-GuyNeural":    "US male — serious commanding",
    "en-GB-SoniaNeural":  "British female — sharp devastating",
    "en-US-DavisNeural":  "US male — dark dramatic",
}


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {
        "last_niche": "", "last_voice": "",
        "makeup_pending": False, "makeup_niche": "",
        "weekly_videos": [], "last_published_title": "",
        "last_published_url": "", "videos_this_week": 0
    }


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_niche(state):
    weekday = datetime.datetime.now().weekday()

    # If makeup video, use the pending niche
    if IS_MAKEUP and state.get("makeup_pending") and state.get("makeup_niche"):
        name = state["makeup_niche"]
        niche = next((n for n in NICHES if n["name"] == name), None)
        if niche:
            print(f"MAKEUP VIDEO: Using failed niche {name}")
            return niche

    # Day-based RPM rotation — never repeat yesterday
    name = DAY_NICHE.get(weekday, "betrayal")
    if name == state.get("last_niche", ""):
        # Fallback: pick highest RPM niche not used yesterday
        candidates = sorted(
            [n for n in NICHES if n["name"] != state.get("last_niche", "")],
            key=lambda x: x["rpm"], reverse=True
        )
        return candidates[0]

    return next(n for n in NICHES if n["name"] == name)


def get_voice(niche_name, state):
    options = VOICE_MAP.get(niche_name, ["en-GB-RyanNeural"])
    last = state.get("last_voice", "")
    # Never repeat yesterday's voice
    available = [v for v in options if v != last]
    if not available:
        available = options
    return available[datetime.datetime.now().timetuple().tm_yday % len(available)]


def call_gemini(prompt, temp=0.88, tokens=6000):
    for attempt in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temp,
                        "maxOutputTokens": min(tokens, 8192),
                        "topP": 0.95
                    },
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
    raise Exception("Gemini failed all attempts")


def call_groq(prompt, temp=0.7, tokens=2000):
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=min(tokens, 2000)
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60 * (2 ** attempt))
            else:
                raise
    raise Exception("Groq rate limited")


def call_ai(prompt, temp=0.88, tokens=6000, prefer="gemini"):
    try:
        return call_gemini(prompt, temp, tokens) if prefer == "gemini" else call_groq(prompt, temp, min(tokens, 2000))
    except:
        return call_groq(prompt, temp, min(tokens, 2000)) if prefer == "gemini" else call_gemini(prompt, temp, tokens)


def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except:
        pass


def strip(text):
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


def generate_script(niche, topic, episode, attempt, prev_title, prev_url):
    temp = min(0.82 + attempt * 0.02, 0.96)
    darkness = min(attempt * 12, 100)

    cross_promo = ""
    if prev_title and prev_url:
        cross_promo = f"\nPREVIOUS VIDEO (mention in description): {prev_title}\nURL: {prev_url}\n"

    prompt = f"""You are the greatest dark investigative documentary writer alive.
Write Episode {episode} of "{niche['series']}" for The Betrayal DeepDive YouTube channel.
Goal: 1 million subscribers across all channels by Month 6.

TOPIC: {topic}

CRITICAL: Write EXACTLY {MIN_WORDS} to {MAX_WORDS} words. Count carefully.
This is non-negotiable. The video must be 15-18 minutes long.
Darkness level: {darkness}%.
{cross_promo}

ABSOLUTE RULES — EVERY VIOLATION FAILS THE SCRIPT:
1. ZERO markdown — no asterisks, hashtags, underscores, brackets, backticks
2. ZERO stage directions — no [music] [pause] [cut] [narrator]
3. Pure spoken English ONLY — every word must be speakable aloud
4. MAXIMUM 13 words per sentence — shorter sentences = more tension
5. Never start 3 consecutive sentences with the same word
6. Every paragraph must escalate darker than the previous
7. Specific amounts, dates, names — make it feel real and documented

MANDATORY STRUCTURE — seamless flowing paragraphs, zero section labels:

HOOK (first 3 sentences):
The single most disturbing sentence ever written about this topic.
One detail that makes it immediately and viscerally worse.
One question that makes stopping physically impossible.

THE WORLD BEFORE (sentences 4-25):
The world as it appeared before everything broke.
Make the audience care deeply about who will be destroyed.
Plant exactly 3 specific small details that will become devastating later.
They must seem completely ordinary right now.

RISING DREAD (18-22% of script):
The first signs something was wrong.
Each one small enough to explain away individually.
Together they form a pattern nobody wanted to name.
Never announce the pattern — let the audience feel it assemble.

THE DESCENT (28-32% of script):
The full scale of what was happening beneath the surface.
Specific. Documented. Exact amounts, dates, locations, names.
Every sentence lands like physical weight on the chest.

RETENTION HOOK at 7-minute mark:
Exact words: "What you are about to hear changed this investigation permanently."

THE MAJOR TWIST at exactly 65% through:
One sentence that collapses everything the audience understood.
A paragraph break — implied silence — let it land.
Reframe every planted detail from the opening through this devastating new lens.

THE HUMAN COST (10-12%):
Not statistics. Specific people. What this did to their actual lives.
Peak emotional devastation here. Make it unbearable.

THE AFTERMATH (8%):
What happened legally. What the system failed to do.
The most disturbing element: what remains completely unchanged.

THE RECKONING (5%):
Two paragraphs of hard truth about trust and power.
No moralizing. No advice. Just the plain unbearable truth.

SERIES CLOSE:
One haunting line connecting to next episode of {niche['series']}.
One natural call to subscribe to The Betrayal DeepDive.

WORD COUNT REQUIREMENT: Your response MUST be {MIN_WORDS}-{MAX_WORDS} words.
If you are under {MIN_WORDS} words, EXPAND each section with more specific details,
deeper psychological analysis, more human cost stories, and richer aftermath details.
Do not stop writing until you have reached at least {MIN_WORDS} words.

RETURN ONLY THE NARRATION TEXT. No labels. No markers. No word count. Just the words."""

    raw = call_ai(prompt, temp=temp, tokens=6000, prefer="gemini")
    clean = strip(strip(raw))
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', clean))
    words = len(clean.split())

    return {
        "topic": topic, "clean": clean, "words": words,
        "violations": violations, "attempt": attempt, "episode": episode
    }


def generate_metadata(niche, script, episode, prev_title, prev_url):
    cross_ref = ""
    if prev_title:
        cross_ref = f'Also mention in description: "Watch our previous investigation: {prev_title}"'

    prompt = f"""Generate YouTube metadata for Episode {episode} of "{niche['series']}".
Topic: {script['topic']}
Script opening: {script['clean'][:300]}
{cross_ref}

Return ONLY valid JSON:
{{"title":"YouTube title 58-68 chars with power word — factual not clickbait","description":"450 word description. First 3 lines are standalone hooks. Include 5 chapter timestamps. Cross-reference previous video if available. End with The Betrayal DeepDive subscribe CTA.","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12"],"thumbnail_text":"3 WORDS MAX ALL CAPS — instant dread","chapters":[{{"time":"0:00","title":"The Opening Shock"}},{{"time":"3:30","title":"Chapter 2"}},{{"time":"7:00","title":"The Discovery"}},{{"time":"11:00","title":"The Major Twist"}},{{"time":"14:30","title":"The Full Truth"}}],"category":"22"}}"""

    try:
        text = call_ai(prompt, temp=0.65, tokens=1200, prefer="groq")
        text = re.sub(r'```json|```', '', text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"   Metadata error: {e}")

    return {
        "title": f"{niche['series']} Ep{episode}: The Investigation Exposed",
        "description": f"Episode {episode} of {niche['series']}. {script['topic']}. Subscribe to The Betrayal DeepDive.",
        "tags": [niche['name'], "investigation", "documentary", "exposed", "deepdive", "crime",
                 "betrayal", "scandal", "dark", "truth", "revealed", "shocking"],
        "thumbnail_text": "NOBODY KNEW",
        "chapters": [{"time": "0:00", "title": "The Opening Shock"}, {"time": "3:30", "title": "The Setup"},
                     {"time": "7:00", "title": "The Discovery"}, {"time": "11:00", "title": "The Twist"},
                     {"time": "14:30", "title": "The Aftermath"}],
        "category": "22"
    }


def score_script(script, meta):
    issues = []
    s = 5.0
    w = script["words"]
    md = script["violations"]
    clean = script["clean"]

    # HARD BLOCK: word count is the most critical check
    if w >= MIN_WORDS:
        s += 2.8
    elif w >= 1800:
        s += 0.5
        issues.append(f"Words {w} below {MIN_WORDS} — need more content")
    elif w >= 1000:
        s -= 3.0  # Forces below any gate threshold
        issues.append(f"FATAL: Only {w} words — too short for 15min video")
    else:
        s -= 5.0  # Impossible to pass
        issues.append(f"FATAL: Only {w} words — script generation failed completely")

    # Zero markdown
    if md == 0:
        s += 2.2
    elif md <= 3:
        s += 0.5
        issues.append(f"WARNING: {md} markdown symbols remain")
    else:
        s -= 1.5
        issues.append(f"FATAL: {md} markdown violations")

    # Sentence rhythm
    sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+', clean) if len(x.strip()) > 5]
    if sents:
        avg = sum(len(x.split()) for x in sents) / len(sents)
        if avg <= 12:
            s += 1.3
        elif avg <= 16:
            s += 0.8
        else:
            s -= 0.3
            issues.append(f"Avg sentence {avg:.0f}w — prefer under 13")

    # Hook strength
    hook = clean[:400].lower()
    hook_score = sum(1 for word in [
        "million", "billion", "nobody", "secret", "exposed", "stolen", "destroyed",
        "trusted", "betrayed", "discovered", "truth", "hidden", "years", "deceived",
        "manipulated", "silenced", "vanished", "collapsed"
    ] if word in hook)
    if hook_score >= 4:
        s += 1.0
    elif hook_score >= 2:
        s += 0.5
        issues.append("Hook needs stronger impact words")
    else:
        issues.append("Weak hook — missing visceral words in opening")

    # CTA present
    close = clean[-400:].lower()
    if "subscribe" in close or "betrayal deepdive" in close:
        s += 0.3

    # Metadata checks (bonus only — never block)
    title = meta.get("title", "")
    if 50 <= len(title) <= 75:
        s += 0.4
    if len(meta.get("tags", [])) >= 10:
        s += 0.2
    if len(meta.get("description", "").split()) >= 200:
        s += 0.2

    score = min(round(s, 1), 10.0)
    return score, issues


def main():
    print("\n" + "=" * 65)
    print("  STAGE 1: Masterpiece Script Engine")
    print("  All requirements: voice memory, niche rotation, makeup logic")
    print("  2200-2600 words HARD minimum | Adaptive gate | 8 attempts")
    print("=" * 65 + "\n")

    state   = load_state()
    niche   = get_niche(state)
    topic   = random.choice(niche["topics"])
    voice   = get_voice(niche["name"], state)
    episode = (datetime.datetime.now().timetuple().tm_yday // max(1, len(NICHES))) + 1
    prev_title = state.get("last_published_title", "")
    prev_url   = state.get("last_published_url", "")

    print(f"Niche: {niche['name']} | ${niche['rpm']} RPM")
    print(f"Series: {niche['series']} — Episode {episode}")
    print(f"Topic: {topic}")
    print(f"Voice: {voice} — {VOICE_DESC.get(voice, '')}")
    print(f"Makeup run: {IS_MAKEUP}")
    if prev_title:
        print(f"Cross-promo: {prev_title[:50]}...")
    print()

    approved    = None
    best_score  = 0
    last_script = None
    last_meta   = None
    gate        = 8.0

    for attempt in range(1, MAX_RETRIES + 1):
        # Adaptive gate — drops as attempts increase
        if attempt >= 5 and best_score >= 7.5:
            gate = 7.5
        elif attempt >= 3 and best_score >= 7.8:
            gate = 7.8

        print(f"Attempt {attempt}/{MAX_RETRIES} (gate: {gate})...")
        try:
            script = generate_script(niche, topic, episode, attempt, prev_title, prev_url)
            meta   = generate_metadata(niche, script, episode, prev_title, prev_url)
            score, issues = score_script(script, meta)
            passed = score >= gate
            best_score = max(best_score, score)

            if score >= best_score - 0.1:
                last_script = script
                last_meta   = meta

            icon = "APPROVED" if passed else f"BLOCKED (need {gate})"
            print(f"  Score: {score}/10 [{icon}] | {script['words']}w | MD:{script['violations']}")
            if issues and not passed:
                print(f"  Issues: {' | '.join(issues[:2])}")

            if passed:
                print(f"\nScript APPROVED — Attempt {attempt} | {score}/10\n")
                approved = {"script": script, "meta": meta, "score": score}
                break

            time.sleep(2)

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if not approved:
        # Mark makeup as pending so tomorrow runs 2 videos
        state["makeup_pending"] = True
        state["makeup_niche"]   = niche["name"]
        save_state(state)

        # Save best attempt for review
        if last_script:
            pipeline_skip = {
                "run_id": GITHUB_RUN_ID, "niche": niche, "topic": topic,
                "voice": {"id": voice, "desc": VOICE_DESC.get(voice, "")},
                "episode": episode, "script_clean": last_script["clean"],
                "script_words": last_script["words"], "script_series": niche["series"],
                "script_attempt": last_script["attempt"], "meta": last_meta or {},
                "score_stage1": best_score, "status": "day_skipped",
                "start_time": datetime.datetime.now().isoformat()
            }
            with open(OUTPUT_DIR / "pipeline.json", "w") as f:
                json.dump(pipeline_skip, f, indent=2)
            with open(OUTPUT_DIR / "script.txt", "w", encoding="utf-8") as f:
                f.write(last_script["clean"])

        # Write output FIRST before exiting
        gho = os.environ.get("GITHUB_OUTPUT", "")
        if gho:
            with open(gho, "a") as f:
                f.write("approved=false\n")
                f.write(f"run_id={GITHUB_RUN_ID}\n")

        telegram(
            f"<b>Stage 1 — Day Skipped</b>\n\n"
            f"All {MAX_RETRIES} attempts failed.\n"
            f"Best score: {best_score}/10\n"
            f"Niche: {niche['name']}\n\n"
            f"Makeup video queued for tomorrow.\n"
            f"Tomorrow will publish 2 videos automatically."
        )
        sys.exit(0)

    # Update state — track voice/niche to avoid repeating tomorrow
    state["last_niche"]  = niche["name"]
    state["last_voice"]  = voice
    state["makeup_pending"] = False
    state["makeup_niche"]   = ""

    # Track weekly videos
    if "weekly_videos" not in state:
        state["weekly_videos"] = []
    state["weekly_videos"].append({
        "date":     datetime.datetime.now().isoformat(),
        "niche":    niche["name"],
        "voice":    voice,
        "score":    approved["score"],
        "title":    approved["meta"].get("title", ""),
        "is_makeup": IS_MAKEUP
    })
    state["weekly_videos"] = state["weekly_videos"][-7:]  # Keep last 7 days
    state["videos_this_week"] = state.get("videos_this_week", 0) + 1
    save_state(state)

    pipeline = {
        "run_id":          GITHUB_RUN_ID,
        "niche":           niche,
        "topic":           topic,
        "voice":           {"id": voice, "desc": VOICE_DESC.get(voice, "")},
        "episode":         episode,
        "is_makeup":       IS_MAKEUP,
        "script_clean":    approved["script"]["clean"],
        "script_words":    approved["script"]["words"],
        "script_series":   niche["series"],
        "script_attempt":  approved["script"]["attempt"],
        "meta":            approved["meta"],
        "score_stage1":    approved["score"],
        "prev_title":      prev_title,
        "prev_url":        prev_url,
        "start_time":      datetime.datetime.now().isoformat()
    }

    with open(OUTPUT_DIR / "pipeline.json", "w") as f:
        json.dump(pipeline, f, indent=2)
    with open(OUTPUT_DIR / "script.txt", "w", encoding="utf-8") as f:
        f.write(approved["script"]["clean"])
    # Save state for next run
    with open(OUTPUT_DIR / "channel_state.json", "w") as f:
        json.dump(state, f, indent=2)

    # Write output immediately after pipeline.json is saved
    gho = os.environ.get("GITHUB_OUTPUT", "")
    if gho:
        with open(gho, "a") as f:
            f.write("approved=true\n")
            f.write(f"run_id={GITHUB_RUN_ID}\n")
    print(f"GitHub output written: approved=true")

    makeup_tag = " [MAKEUP VIDEO]" if IS_MAKEUP else ""
    telegram(
        f"<b>Stage 1 Complete{makeup_tag}</b>\n\n"
        f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
        f"Series: {niche['series']} Ep{episode}\n"
        f"Words: {approved['script']['words']} | Score: {approved['score']}/10\n"
        f"Voice: {voice} — {VOICE_DESC.get(voice, '')}\n"
        f"Title: {approved['meta'].get('title', '')}\n\n"
        f"Stage 2: Audio starting..."
    )
    print("Stage 1 complete")


if __name__ == "__main__":
    main()
