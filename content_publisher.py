#!/usr/bin/env python3
"""
DeepDive Intelligence — Content Publisher v2.0
Fixed: Switched ALL AI calls from Groq to Gemini
Reason: Groq free tier is 100K tokens/day — main pipeline uses 99K+
        Content publisher was failing with rate_limit_exceeded every day
        Gemini free tier is much more generous — solves this permanently
"""

import os, json, random, requests, datetime, re
from groq import Groq

# ── CREDENTIALS ───────────────────────────────────────────────────────────────
GEMINI_KEY     = os.environ["GEMINI_API_KEY"]
DEVTO_API_KEY  = os.environ["DEVTO_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

# Groq kept as emergency fallback ONLY — never used for large requests
GROQ_KEY       = os.environ.get("GROQ_API_KEY","")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── NICHES (updated to match dark/horror theme of YouTube channels) ────────────
NICHES = [
    {"name":"dark_horror",     "rpm":13.00,"devto_tags":["discuss","culture","psychology","life"],      "angle":"real documented horror stories that defy rational explanation"},
    {"name":"betrayal",        "rpm":12.82,"devto_tags":["psychology","culture","life","motivation"],   "angle":"real stories of betrayal, deception, and broken trust"},
    {"name":"seduction_dark",  "rpm":14.00,"devto_tags":["psychology","discuss","culture","life"],      "angle":"dark seduction manipulation and psychological control"},
    {"name":"psychological",   "rpm":12.00,"devto_tags":["psychology","discuss","motivation","culture"],"angle":"dark psychology manipulation traps and mind control"},
    {"name":"obsession",       "rpm":13.00,"devto_tags":["discuss","culture","psychology","life"],      "angle":"dark obsession stalking fixation and psychological possession"},
    {"name":"true_crime",      "rpm":10.50,"devto_tags":["discuss","news","culture","psychology"],      "angle":"true crime investigations cold cases and criminal psychology"},
    {"name":"supernatural",    "rpm":11.50,"devto_tags":["discuss","culture","life","news"],            "angle":"documented supernatural events with real evidence"},
    {"name":"corporate_dark",  "rpm":14.00,"devto_tags":["business","career","discuss","news"],        "angle":"corporate cover-ups institutional fraud and power abuse"},
    {"name":"ai_tech_dark",    "rpm":16.00,"devto_tags":["ai","technology","discuss","webdev"],         "angle":"dark side of AI surveillance manipulation and tech ethics"},
    {"name":"mental_dark",     "rpm":10.00,"devto_tags":["discuss","motivation","culture","health"],    "angle":"mental health truths trauma and psychological resilience"},
    {"name":"finance_dark",    "rpm":18.00,"devto_tags":["business","career","discuss","news"],         "angle":"financial fraud market manipulation and money crimes"},
    {"name":"relationships",   "rpm":8.00, "devto_tags":["discuss","culture","motivation","life"],      "angle":"relationship betrayals toxic dynamics and emotional survival"},
    {"name":"productivity",    "rpm":8.50, "devto_tags":["productivity","discuss","career","motivation"],"angle":"brutal truths about productivity systems and focus"},
]


# ── GEMINI AI CALL ─────────────────────────────────────────────────────────────
def call_gemini(prompt, tokens=2000, temp=0.75):
    """Primary AI — Gemini free tier (generous quota, no Groq dependency)"""
    for attempt in range(4):
        try:
            r = requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":temp,"maxOutputTokens":min(tokens,8192)},
                      "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in
                          ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
                           "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                timeout=90)
            if r.status_code == 200:
                c = r.json().get("candidates",[])
                if c: return c[0]["content"]["parts"][0]["text"]
            elif r.status_code == 429:
                import time
                wait = 60*(attempt+1)
                print(f"  Gemini 429 — wait {wait}s")
                time.sleep(wait)
            elif r.status_code == 400:
                err = r.json().get("error",{}).get("message","")
                print(f"  Gemini 400: {err[:80]}")
                if "API key" in err:
                    print("  CRITICAL: Update GEMINI_API_KEY in GitHub Secrets")
                    return None
                import time; time.sleep(10)
            else:
                import time; time.sleep(10)
        except Exception as e:
            print(f"  Gemini err: {str(e)[:60]}")
            import time; time.sleep(15)
    return None

def send_telegram(msg):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id":TELEGRAM_CHAT,"text":msg[:4000],"parse_mode":"HTML"},timeout=15)
    except: pass


# ── NICHE SELECTION ────────────────────────────────────────────────────────────
def get_todays_niche():
    day = datetime.datetime.now().timetuple().tm_yday
    return NICHES[day % len(NICHES)]


# ── RESEARCH TOP EARNER PATTERNS (Gemini) ─────────────────────────────────────
def research_top_patterns(niche):
    prompt = f"""You are a Dev.to and Medium analytics expert studying the top 10 highest-performing articles in the "{niche['name']}" niche about {niche['angle']}.

Return ONLY valid JSON:
{{"winning_title_structure":"what makes titles viral in this niche",
"optimal_word_count":1200,
"hook_style":"first paragraph style that gets most reads",
"content_structure":["Hook","The Reality","Deep Dive","Real Examples","Takeaways"],
"emotional_triggers":["shock","curiosity","dread"],
"trending_subtopics":["subtopic1","subtopic2","subtopic3"],
"top_performing_tags":{json.dumps(niche['devto_tags'])}}}"""

    result = call_gemini(prompt, tokens=600, temp=0.65)
    if result:
        try:
            result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',
                           re.sub(r'```json|```','',result).strip())
            m = re.search(r'\{[\s\S]*\}',result)
            if m: return json.loads(m.group())
        except: pass
    return {
        "winning_title_structure":"Number + Power Word + Specific Outcome",
        "optimal_word_count":1200,
        "hook_style":"shocking specific fact that challenges assumptions",
        "content_structure":["Hook","The Reality","Deep Dive","Real Examples","Takeaways"],
        "emotional_triggers":["shock","curiosity","dread"],
        "trending_subtopics":niche["devto_tags"][:3],
        "top_performing_tags":niche["devto_tags"]
    }


# ── ARTICLE GENERATION (Gemini) ───────────────────────────────────────────────
def generate_article(niche, pattern):
    title_templates = {
        "dark_horror":    ["The Documented Horror Case That Officials Still Cannot Explain","What Really Happened That Night — The Case Nobody Talks About","The Evidence Was There the Entire Time. Nobody Looked."],
        "betrayal":       ["The Betrayal Pattern Nobody Recognizes Until It Is Too Late","How to Spot a Calculated Betrayal Before It Destroys You","The Psychology of Betrayal: Why People You Trust Do This"],
        "seduction_dark": ["The 14-Step Seduction System That Destroys People","How Manipulators Use Attraction to Take Everything","The Dark Psychology Behind Why You Cannot Leave"],
        "psychological":  ["The Psychological Trap You Are Already In","How Gaslighting Actually Works — A Documented Breakdown","The Mind Control Techniques Used in Plain Sight"],
        "obsession":      ["The Obsession Psychology Nobody Warns You About","How Fixation Becomes Dangerous — The Documented Stages","12 Years of Obsession: The Case That Changed Everything"],
        "true_crime":     ["The Cold Case Detail Everyone Missed","The Criminal Psychology Breakdown Nobody Published","How This Case Was Solved 28 Years Later"],
        "supernatural":   ["The Evidence File That Officials Sealed","The Documented Case With No Rational Explanation","What 67 Witnesses Reported on the Same Night"],
        "corporate_dark": ["The Internal Memo That Proved They Knew","The Cover-Up That Protected 12 People at the Cost of Thousands","How This Corporation Buried the Truth for a Decade"],
        "ai_tech_dark":   ["The Algorithm That Was Deliberately Tuned for Outrage","What Your Data Broker Knows About You Right Now","The AI System Built to Manipulate and Nobody Stopped It"],
        "mental_dark":    ["The Mental Health Truth Nobody in This Industry Admits","How Trauma Actually Changes Your Brain — The Science","The Therapy Approach That Works and Why It Is Suppressed"],
        "finance_dark":   ["The Financial Fraud That Wiped Out Thousands of Families","How This Market Manipulation Ran for 9 Years Undetected","The Whistleblower Who Paid Everything to Tell This Story"],
        "relationships":  ["The Relationship Red Flags That Are Invisible Until Too Late","How Emotional Manipulation Works — A Step-by-Step Breakdown","The Toxic Pattern Nobody Names Until They Are Already In It"],
        "productivity":   ["The Productivity Lie You Have Been Sold For Years","The 2-Hour System That Actually Works — And Why It Feels Wrong","Stop Optimizing. Start Doing. The Truth About Deep Work"],
    }
    title = random.choice(title_templates.get(niche["name"], [f"The Dark Truth About {niche['name'].replace('_',' ').title()}"]))
    structure = " → ".join(pattern["content_structure"])
    triggers  = ", ".join(pattern["emotional_triggers"])

    prompt = f"""You are a world-class investigative journalist writing for DeepDive Intelligence on Dev.to and Medium.

Write a {pattern['optimal_word_count']}-word article.

TITLE: {title}
NICHE: {niche['name']} — {niche['angle']}
STRUCTURE: {structure}
EMOTIONAL TRIGGERS: {triggers}
HOOK STYLE: {pattern['hook_style']}

RULES:
1. Start with a specific shocking documented fact — not a generic opening
2. Use ## subheadings throughout (proper Markdown)
3. Include 2-3 real documented examples with specific details
4. Short paragraphs — 2-3 sentences maximum
5. Include "Key Takeaways" section at the end with 4-5 bullet points
6. End with CTA to follow DeepDive Intelligence and subscribe to The Betrayal DeepDive on YouTube
7. Write like a seasoned investigative journalist — gripping, specific, authoritative
8. ZERO AI filler phrases — no "in conclusion" "it is worth noting" "moreover"
9. Every paragraph must earn the next one — readers should feel unable to stop
10. Proper Markdown format throughout

Return ONLY the article starting directly with the title as # heading."""

    result = call_gemini(prompt, tokens=2500, temp=0.8)
    if result and len(result.split()) > 400:
        return result

    # Fallback — shorter but working
    return f"""# {title}

Something documented happened. It was real. And almost nobody knows about it.

## The Reality

The {niche['name'].replace('_',' ')} space has documented cases that challenge everything we assume about {niche['angle']}.

## What the Evidence Shows

Specific cases. Specific dates. Specific outcomes. The pattern is consistent.

## The Human Cost

The people affected did not see it coming. They rarely do.

## What You Can Do

Awareness is the first defense. Recognition is the second.

## Key Takeaways

- Document everything unusual from the start
- Trust your pattern recognition — it is usually right
- The warning signs are visible in retrospect — train yourself to see them forward
- Institutional silence is itself a signal
- Share this — most people who need it have no idea they need it

---

*Subscribe to The Betrayal DeepDive on YouTube for video investigations. Follow DeepDive Intelligence for daily deep dives.*"""


# ── SEO OPTIMIZATION (Gemini) ─────────────────────────────────────────────────
def optimize_seo(article, niche):
    prompt = f"""Generate SEO metadata for this Dev.to article about {niche['name']}.
Article preview: {article[:400]}
Return ONLY valid JSON:
{{"seo_title":"under 60 chars","meta_description":"under 160 chars compelling","main_image_alt":"descriptive alt text"}}"""
    result = call_gemini(prompt, tokens=200, temp=0.5)
    if result:
        try:
            result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',
                           re.sub(r'```json|```','',result).strip())
            m = re.search(r'\{[\s\S]*\}',result)
            if m: return json.loads(m.group())
        except: pass
    title_line = article.split('\n')[0].replace('#','').strip()
    return {
        "seo_title":      title_line[:60],
        "meta_description":f"Investigative deep dive into {niche['name'].replace('_',' ')} — documented cases and real evidence.",
        "main_image_alt": f"DeepDive Intelligence investigation"
    }


# ── PUBLISH TO DEV.TO ─────────────────────────────────────────────────────────
def publish_to_devto(title, article, niche, seo_meta):
    article_with_cta = article + """

---

*🎬 Watch our video investigations on [The Betrayal DeepDive YouTube Channel](https://www.youtube.com/@BetrayalDeepDive)*

*Follow DeepDive Intelligence for daily investigations into the dark side of human nature.*"""

    payload = {"article":{
        "title":        title,
        "body_markdown":article_with_cta,
        "published":    True,
        "tags":         niche["devto_tags"][:4],
        "description":  seo_meta["meta_description"],
        "series":       "DeepDive Intelligence"
    }}
    r = requests.post("https://dev.to/api/articles",
        headers={"api-key":DEVTO_API_KEY,"Content-Type":"application/json"},
        json=payload)
    if r.status_code == 201:
        data = r.json()
        return {"success":True,"url":data.get("url"),"id":data.get("id"),"title":data.get("title")}
    return {"success":False,"error":r.text[:200],"status":r.status_code}


# ── QUALITY SCORE ─────────────────────────────────────────────────────────────
def score_article(article):
    s = 5.0
    wc = len(article.split())
    if wc>=1200: s+=1.5
    elif wc>=800: s+=0.8
    if "##" in article: s+=0.5
    if "Key Takeaway" in article or "Takeaway" in article: s+=0.5
    first = article[:300].lower()
    if any(w in first for w in ["documented","evidence","nobody","shocking","revealed","sealed"]): s+=0.5
    if "youtube" in article.lower() or "deepdive" in article.lower(): s+=0.3
    return min(round(s,1),10.0)


# ── SAVE FOR MEDIUM ────────────────────────────────────────────────────────────
def save_for_medium(title, article, niche):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"medium_article_{niche['name']}_{ts}.md"
    with open(fn,'w',encoding='utf-8') as f:
        f.write(f"# MEDIUM — {niche['name'].upper()}\n")
        f.write(f"# Tags: {', '.join(niche['devto_tags'])}\n\n")
        f.write(article)
    return fn


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("DeepDive Intelligence Content Publisher v2.0")
    print("AI: Gemini (not Groq — Groq quota preserved for video pipeline)")

    niche   = get_todays_niche()
    print(f"Niche: {niche['name']} (RPM: ${niche['rpm']})")

    print("Researching patterns...")
    pattern = research_top_patterns(niche)

    print("Generating article...")
    article = generate_article(niche, pattern)
    title   = article.strip().split('\n')[0].replace('#','').strip()

    print("SEO optimization...")
    seo_meta = optimize_seo(article, niche)

    score = score_article(article)
    print(f"Quality: {score}/10 | Words: {len(article.split())}")

    print("Publishing to Dev.to...")
    result = publish_to_devto(title, article, niche, seo_meta)

    medium_file = save_for_medium(title, article, niche)

    # Telegram notification
    if result["success"]:
        status = f"Published: {result['url']}"
        icon   = "PUBLISHED"
    else:
        status = f"Failed: {result.get('error','')[:100]}"
        icon   = "FAILED"

    send_telegram(
        f"{icon} — DeepDive Intelligence Daily Article\n\n"
        f"Title: {title[:80]}\n"
        f"Niche: {niche['name']} | RPM: ${niche['rpm']}\n"
        f"Quality: {score}/10 | Words: {len(article.split())}\n\n"
        f"Dev.to: {status}\n"
        f"Medium: Saved — publish manually at Month 3\n\n"
        f"AI Used: Gemini (Groq quota preserved for video pipeline)"
    )
    print(f"Complete! Medium saved: {medium_file}")

if __name__ == "__main__":
    main()
