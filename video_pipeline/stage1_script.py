#!/usr/bin/env python3
"""
DEEPDIVE EMPIRE - STAGE 1: SCRIPT + METADATA
Gemini 2.0 Flash primary | Groq fallback
8 smart attempts | Adaptive gate 8.0 -> 7.8 -> 7.5
Day-based niche rotation | RPM-optimised
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

MAX_RETRIES = 8
MIN_WORDS   = 2200
MAX_WORDS   = 2600

# RPM-optimised day mapping
DAY_NICHE = {
    0: "betrayal",        # Monday
    1: "finance_scandal", # Tuesday  - highest RPM
    2: "business_fraud",  # Wednesday
    3: "legal_drama",     # Thursday - highest RPM
    4: "true_crime",      # Friday
}

NICHES = [
    {"name":"betrayal",       "rpm":12.82,"weight":3,"series":"The Betrayal Files","watermark":"THE BETRAYAL FILES",
     "topics":[
         "A CFO secretly wired 4.7 million dollars offshore across six years while the CEO called him his closest friend",
         "Two friends built a restaurant group over 15 years. Security footage showed one had been stealing since opening day.",
         "A son forged his parents signatures for eleven years to drain their retirement. He visited every Sunday for dinner.",
         "The mentor who took credit for her proteges decade of research and was exposed live on stage at a global conference",
         "A church treasurer stole 3.2 million in charitable donations over nine years while leading the Sunday collection",
     ]},
    {"name":"legal_drama",    "rpm":16.50,"weight":4,"series":"Justice Served","watermark":"JUSTICE SERVED",
     "topics":[
         "A wrongful murder conviction lasted 22 years until one detective checked a timestamp every other investigator ignored",
         "A paralegal spotted a forged signature that 14 senior partners had each personally reviewed and missed",
         "A federal judge held financial interests across 47 connected cases for a decade and nobody checked",
         "A corporate attorney secretly recorded 200 privileged client meetings then played every tape in open court",
     ]},
    {"name":"finance_scandal","rpm":19.00,"weight":4,"series":"Dark Money","watermark":"DARK MONEY",
     "topics":[
         "A penny stock ring extracted 470 million from retail investors over 7 years using entirely fake financial analysts",
         "A regional bank concealed 3.2 billion in bad loans through 40 shell companies until its collapse destroyed thousands",
         "A rogue bond trader hid 900 million in losses across three years by exploiting a flaw in his own banks risk system",
         "A private wealth desk moved client retirement funds into the firms own failing investments for five years",
     ]},
    {"name":"true_crime",     "rpm":10.50,"weight":2,"series":"Dark Truth","watermark":"DARK TRUTH",
     "topics":[
         "An identity theft ring operated for 11 years by stealing exclusively from people who had died in the past 30 days",
         "A cold case murder solved 28 years later when a genealogy hobbyist uploaded DNA and matched the killers nephew",
         "A doctor defrauded Medicare of 8 million over 12 years while maintaining a perfect 5-star patient rating",
     ]},
    {"name":"psych_thriller", "rpm":11.50,"weight":2,"series":"Mind Games","watermark":"MIND GAMES",
     "topics":[
         "The documented sequence cult leaders use to make educated professionals surrender their identity in 90 days",
         "How clinical narcissists in executive roles destroy the careers of every subordinate who shows potential to outperform them",
     ]},
    {"name":"business_fraud", "rpm":13.00,"weight":3,"series":"Corporate Crimes","watermark":"CORPORATE CRIMES",
     "topics":[
         "A SaaS startup raised 340 million from 22 investors using a product that had been faked from the very first pitch",
         "One developer pledged the same 12 properties as collateral to 9 different lenders simultaneously across 4 years",
         "A Big Four auditing firm signed off on six years of fraudulent reports for a company it had internally flagged",
     ]},
    {"name":"ai_tech_dark",   "rpm":16.00,"weight":3,"series":"Algorithm Exposed","watermark":"ALGORITHM EXPOSED",
     "topics":[
         "Internal documents proved a platform deliberately tuned its algorithm to maximize outrage after safety teams formally objected",
         "The data broker industry builds and sells profiles on 300 million people who never gave consent",
     ]},
    {"name":"health_scandal", "rpm":12.00,"weight":2,"series":"Toxic Trust","watermark":"TOXIC TRUST",
     "topics":[
         "Clinical data showing 340 percent increased cardiac risk was suppressed for 6 years while 40 million patients took the drug",
         "A device manufacturer sold a spinal implant for 4 years after internal tests confirmed a 23 percent failure rate",
     ]},
]

VOICE_MAP = {
    "betrayal":       [{"id":"am_fenrir","lang":"a","desc":"Darkest US male"},{"id":"bf_isabella","lang":"b","desc":"Haunting British female"},{"id":"bm_lewis","lang":"b","desc":"Deep cinematic British"}],
    "legal_drama":    [{"id":"bm_george","lang":"b","desc":"BBC gravitas"},{"id":"bf_emma","lang":"b","desc":"Sharp British female"},{"id":"af_nova","lang":"a","desc":"Dark US female"}],
    "finance_scandal":[{"id":"bm_daniel","lang":"b","desc":"Cold British authority"},{"id":"am_adam","lang":"a","desc":"Deep commanding US male"},{"id":"bm_lewis","lang":"b","desc":"Cinematic British"}],
    "true_crime":     [{"id":"bm_fable","lang":"b","desc":"Dark storyteller"},{"id":"am_fenrir","lang":"a","desc":"Darkest US male"},{"id":"af_nova","lang":"a","desc":"Dark US female"}],
    "psych_thriller": [{"id":"bf_isabella","lang":"b","desc":"Haunting British female"},{"id":"am_michael","lang":"a","desc":"Intense US male"},{"id":"bm_fable","lang":"b","desc":"Dark British male"}],
    "business_fraud": [{"id":"am_puck","lang":"a","desc":"Urgent US male"},{"id":"bm_daniel","lang":"b","desc":"Cold British male"},{"id":"am_adam","lang":"a","desc":"Commanding US male"}],
    "ai_tech_dark":   [{"id":"am_adam","lang":"a","desc":"Deep authoritative US male"},{"id":"bf_emma","lang":"b","desc":"Sharp British female"},{"id":"am_michael","lang":"a","desc":"Intense US male"}],
    "health_scandal": [{"id":"af_heart","lang":"a","desc":"Devastating US female"},{"id":"bm_george","lang":"b","desc":"BBC gravitas"},{"id":"bm_fable","lang":"b","desc":"Dark British male"}],
}


def get_niche():
    weekday = datetime.datetime.now().weekday()
    name = DAY_NICHE.get(weekday, "betrayal")
    return next(n for n in NICHES if n["name"] == name)


def get_voice(niche_name):
    opts = VOICE_MAP.get(niche_name, [{"id":"bm_george","lang":"b","desc":"BBC gravitas"}])
    return opts[datetime.datetime.now().timetuple().tm_yday % len(opts)]


def call_gemini(prompt, temp=0.88, tokens=4000):
    for attempt in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type":"application/json"},
                json={
                    "contents":[{"parts":[{"text":prompt}]}],
                    "generationConfig":{"temperature":temp,"maxOutputTokens":tokens,"topP":0.95},
                    "safetySettings":[
                        {"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_NONE"},
                        {"category":"HARM_CATEGORY_HATE_SPEECH","threshold":"BLOCK_NONE"},
                        {"category":"HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold":"BLOCK_NONE"},
                        {"category":"HARM_CATEGORY_DANGEROUS_CONTENT","threshold":"BLOCK_NONE"}
                    ]
                },
                timeout=120
            )
            if r.status_code == 200:
                cands = r.json().get("candidates",[])
                if cands:
                    return cands[0]["content"]["parts"][0]["text"]
            elif r.status_code == 429:
                time.sleep(60*(attempt+1))
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
                messages=[{"role":"user","content":prompt}],
                temperature=temp, max_tokens=min(tokens,2000)
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                time.sleep(60*(2**attempt))
            else:
                raise
    raise Exception("Groq rate limited")


def call_ai(prompt, temp=0.88, tokens=4000, prefer="gemini"):
    try:
        return call_gemini(prompt,temp,tokens) if prefer=="gemini" else call_groq(prompt,temp,min(tokens,2000))
    except:
        return call_groq(prompt,temp,min(tokens,2000)) if prefer=="gemini" else call_gemini(prompt,temp,tokens)


def telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id":TELEGRAM_CHAT,"text":msg,"parse_mode":"HTML"},
            timeout=15
        )
    except: pass


def strip(text):
    for _ in range(2):
        text = re.sub(r'^#{1,6}\s+','',text,flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}',r'\1',text)
        text = re.sub(r'_{1,3}([^_\n]+)_{1,3}',r'\1',text)
        text = re.sub(r'^[-*_]{3,}\s*$','',text,flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+•·▪]\s+','',text,flags=re.MULTILINE)
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


def generate_script(niche, topic, episode, attempt):
    temp = min(0.82 + attempt*0.02, 0.96)
    darkness = min(attempt*12, 100)

    prompt = f"""You are the greatest dark investigative documentary writer alive.
Write Episode {episode} of "{niche['series']}" for The Betrayal DeepDive YouTube channel.

TOPIC: {topic}

Write a {MIN_WORDS}-{MAX_WORDS} word spoken narration.
Tone: Psychological dread inside a true crime investigation.
Darkness level: {darkness}%.

ABSOLUTE RULES - VIOLATING ANY = SCRIPT REJECTED:
1. ZERO markdown - no asterisks, hashtags, underscores, brackets, backticks
2. ZERO stage directions - no [music] [pause] [narrator]
3. Pure spoken English ONLY - every word must be speakable aloud
4. Maximum 13 words per sentence
5. Never start 3 consecutive sentences with the same word
6. Every paragraph must be darker than the previous one
7. Use specific amounts, dates, names to make it feel documented

STRUCTURE (seamless flowing paragraphs - zero section labels):

HOOK - first 3 sentences:
Most disturbing sentence ever written about this topic.
A specific detail that makes it immediately worse.
A question that makes stopping impossible.

THE WORLD BEFORE:
Establish the world as it appeared before it broke.
Make the audience care about who will be destroyed.
Plant 3 small details that become devastating later.

RISING DREAD (18-22% of script):
First signs something was wrong. Each explainable alone.
Together they form a pattern nobody wanted to name.

THE DESCENT (28-32% of script):
Full scale of what was happening. Specific. Documented.
Exact amounts, dates, locations where possible.

RETENTION HOOK at 7-minute mark:
One sentence: what you are about to hear changed this investigation permanently.

THE MAJOR TWIST at 65% through:
One sentence that destroys everything the audience understood.
Then reframe every planted detail through this new lens.

THE HUMAN COST (10-12%):
Specific people. What this did to their actual lives.
Peak emotional devastation here.

THE AFTERMATH (8%):
What the system did. What it failed to do.
The most disturbing: what remains unchanged.

THE RECKONING (5%):
Hard truth about trust and power. No moralizing. Just facts.

SERIES CLOSE:
Haunting line connecting to next episode of {niche['series']}.
Natural call to subscribe to The Betrayal DeepDive.

RETURN ONLY THE NARRATION TEXT. No labels. No markers."""

    raw = call_ai(prompt, temp=temp, tokens=4000, prefer="gemini")
    clean = strip(strip(raw))
    violations = len(re.findall(r'[#*_`\[\]{}<>\\]', clean))
    words = len(clean.split())
    return {"topic":topic,"clean":clean,"words":words,"violations":violations,"attempt":attempt,"episode":episode}


def generate_metadata(niche, script, episode):
    prompt = f"""Generate YouTube metadata for Episode {episode} of "{niche['series']}".
Topic: {script['topic']}
Script opening: {script['clean'][:300]}

Return ONLY valid JSON:
{{"title":"YouTube title 58-68 chars with power word","description":"400 word description with 5 chapter timestamps and subscribe CTA","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12"],"thumbnail_text":"3 WORDS MAX ALL CAPS","chapters":[{{"time":"0:00","title":"The Opening Shock"}},{{"time":"3:30","title":"Chapter 2"}},{{"time":"7:00","title":"The Discovery"}},{{"time":"11:00","title":"The Major Twist"}},{{"time":"14:30","title":"The Full Truth"}}],"category":"22"}}"""

    try:
        text = call_ai(prompt, temp=0.65, tokens=1200, prefer="groq")
        text = re.sub(r'```json|```','',text).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"   Metadata error: {e}")

    return {
        "title": f"{niche['series']} Ep{episode}: The Investigation Exposed",
        "description": f"Episode {episode} of {niche['series']}. {script['topic']}. Subscribe to The Betrayal DeepDive.",
        "tags": [niche['name'],"investigation","documentary","exposed","deepdive","crime","betrayal","scandal","dark","truth","revealed","shocking"],
        "thumbnail_text": "NOBODY KNEW",
        "chapters": [{"time":"0:00","title":"The Opening Shock"},{"time":"3:30","title":"The Setup"},{"time":"7:00","title":"The Discovery"},{"time":"11:00","title":"The Twist"},{"time":"14:30","title":"The Aftermath"}],
        "category": "22"
    }


def score_script(script, meta):
    issues = []
    s = 5.0
    w = script["words"]
    md = script["violations"]
    clean = script["clean"]

    if w >= MIN_WORDS: s += 2.8
    elif w >= 1800: s += 1.5; issues.append(f"Words {w} below {MIN_WORDS}")
    else: s -= 1.5; issues.append(f"FATAL: {w} words too short")

    if md == 0: s += 2.2
    elif md <= 3: s += 0.5; issues.append(f"WARNING: {md} markdown symbols")
    else: s -= 1.5; issues.append(f"FATAL: {md} markdown violations")

    sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+', clean) if len(x.strip())>5]
    if sents:
        avg = sum(len(x.split()) for x in sents)/len(sents)
        if avg <= 12: s += 1.3
        elif avg <= 16: s += 0.8
        else: s -= 0.3; issues.append(f"Avg sentence {avg:.0f}w — prefer under 13")

    hook = clean[:400].lower()
    hook_score = sum(1 for word in ["million","billion","nobody","secret","exposed","stolen","destroyed","trusted","betrayed","discovered","truth","hidden","years","deceived"] if word in hook)
    if hook_score >= 4: s += 1.0
    elif hook_score >= 2: s += 0.5; issues.append("Hook needs stronger words")
    else: issues.append("Weak hook")

    close = clean[-400:].lower()
    if "subscribe" in close or "betrayal deepdive" in close: s += 0.3

    title = meta.get("title","")
    if 50 <= len(title) <= 75: s += 0.4

    if len(meta.get("tags",[])) >= 10: s += 0.2
    if len(meta.get("description","").split()) >= 150: s += 0.2

    score = min(round(s,1), 10.0)
    return score, issues


def main():
    print("\n" + "="*60)
    print("  STAGE 1: Script + Metadata")
    print("  8 smart attempts | Adaptive gate | Gemini + Groq")
    print("="*60 + "\n")

    niche   = get_niche()
    topic   = random.choice(niche["topics"])
    voice   = get_voice(niche["name"])
    episode = (datetime.datetime.now().timetuple().tm_yday // niche["weight"]) + 1

    print(f"Niche: {niche['name']} | ${niche['rpm']} RPM")
    print(f"Series: {niche['series']} — Episode {episode}")
    print(f"Topic: {topic}")
    print(f"Voice: {voice['id']} — {voice['desc']}\n")

    approved    = None
    best_score  = 0
    last_script = None
    last_meta   = None
    gate        = 8.0

    for attempt in range(1, MAX_RETRIES+1):
        # Adaptive gate
        if attempt >= 5 and best_score >= 7.5: gate = 7.5
        elif attempt >= 3 and best_score >= 7.8: gate = 7.8

        print(f"Attempt {attempt}/{MAX_RETRIES} (gate: {gate})...")
        try:
            script = generate_script(niche, topic, episode, attempt)
            meta   = generate_metadata(niche, script, episode)
            score, issues = score_script(script, meta)
            passed = score >= gate
            best_score = max(best_score, score)

            if score >= best_score:
                last_script = script
                last_meta   = meta

            icon = "APPROVED" if passed else f"BLOCKED (need {gate})"
            print(f"  Score: {score}/10 [{icon}] | {script['words']}w | MD:{script['violations']}")
            if issues and not passed:
                print(f"  Issues: {' | '.join(issues[:2])}")

            if passed:
                print(f"\nScript APPROVED — Attempt {attempt} | {score}/10\n")
                approved = {"script":script,"meta":meta,"score":score}
                break

            time.sleep(2)

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            time.sleep(15)

    if not approved:
        # Save best attempt anyway
        if last_script:
            pipeline_skip = {
                "run_id":GITHUB_RUN_ID,"niche":niche,"topic":topic,"voice":voice,
                "episode":episode,"script_clean":last_script["clean"],
                "script_words":last_script["words"],"script_series":last_script.get("series",""),
                "script_attempt":last_script["attempt"],"meta":last_meta or {},
                "score_stage1":best_score,"status":"day_skipped",
                "start_time":datetime.datetime.now().isoformat()
            }
            with open(OUTPUT_DIR/"pipeline.json","w") as f:
                json.dump(pipeline_skip,f,indent=2)
            with open(OUTPUT_DIR/"script.txt","w",encoding="utf-8") as f:
                f.write(last_script["clean"])

        telegram(f"<b>Stage 1 — Day Skipped</b>\n\nAll {MAX_RETRIES} attempts failed.\nBest: {best_score}/10\nNiche: {niche['name']}\nRetrying tomorrow.")
        gho = os.environ.get("GITHUB_OUTPUT","")
        if gho:
            with open(gho,"a") as f:
                f.write("approved=false\n")
        sys.exit(0)

    pipeline = {
        "run_id":GITHUB_RUN_ID,"niche":niche,"topic":topic,"voice":voice,
        "episode":episode,"script_clean":approved["script"]["clean"],
        "script_words":approved["script"]["words"],
        "script_series":approved["script"].get("episode",""),
        "script_attempt":approved["script"]["attempt"],
        "meta":approved["meta"],"score_stage1":approved["score"],
        "start_time":datetime.datetime.now().isoformat()
    }

    with open(OUTPUT_DIR/"pipeline.json","w") as f:
        json.dump(pipeline,f,indent=2)
    with open(OUTPUT_DIR/"script.txt","w",encoding="utf-8") as f:
        f.write(approved["script"]["clean"])

    gho = os.environ.get("GITHUB_OUTPUT","")
    if gho:
        with open(gho,"a") as f:
            f.write(f"approved=true\n")
            f.write(f"run_id={GITHUB_RUN_ID}\n")

    telegram(
        f"<b>Stage 1 Complete</b>\n\n"
        f"Niche: {niche['name']} | ${niche['rpm']} RPM\n"
        f"Series: {niche['series']} Ep{episode}\n"
        f"Words: {approved['script']['words']} | Score: {approved['score']}/10\n"
        f"Voice: {voice['id']} — {voice['desc']}\n"
        f"Title: {approved['meta'].get('title','')}\n\n"
        f"Stage 2: Audio starting..."
    )
    print("Stage 1 complete")


if __name__ == "__main__":
    main()
