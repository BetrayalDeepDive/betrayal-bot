#!/usr/bin/env python3
"""
DeepDive Intelligence — Content Publisher
Publishes AI-generated articles to Dev.to daily
Also prepares articles for Medium (browser-based publishing)
Rotates across 13 niches, studies top earners, matches winning patterns
"""

import os
import json
import random
import requests
import datetime
from groq import Groq

# ── CREDENTIALS ──────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
DEVTO_API_KEY  = os.environ["DEVTO_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

groq_client = Groq(api_key=GROQ_API_KEY)

# ── 13 NICHES ─────────────────────────────────────────────────────────────────
NICHES = [
    {
        "name": "betrayal",
        "rpm": 12.82,
        "tags": ["psychology", "relationships", "life", "crime", "culture"],
        "devto_tags": ["psychology", "culture", "life", "motivation"],
        "angle": "real stories of betrayal, deception, and broken trust",
        "title_patterns": [
            "The {subject} Who Betrayed Everyone and Got Away With It",
            "I Trusted {subject} — The Betrayal Changed My Life Forever",
            "How {subject} Destroyed Lives Through Calculated Deception",
            "The Psychology Behind Why {subject} Betrayed the People Who Loved Them",
            "Warning Signs: How to Spot a Betrayer Before It's Too Late"
        ]
    },
    {
        "name": "legal_drama",
        "rpm": 15.00,
        "tags": ["law", "justice", "crime", "society", "politics"],
        "devto_tags": ["career", "productivity", "discuss", "news"],
        "angle": "shocking court cases, legal battles, and justice served or denied",
        "title_patterns": [
            "The {subject} Trial That Shocked the Nation",
            "Inside the Courtroom: How {subject} Almost Got Away",
            "The Legal Battle That Changed Everything About {subject}",
            "When Justice Failed: The {subject} Case Nobody Talks About",
            "The Lawyer Who Exposed {subject} and Paid the Price"
        ]
    },
    {
        "name": "true_crime",
        "rpm": 10.50,
        "tags": ["crime", "justice", "psychology", "society", "culture"],
        "devto_tags": ["discuss", "news", "culture", "psychology"],
        "angle": "true crime investigations, cold cases, and criminal psychology",
        "title_patterns": [
            "The {subject} Case: What Really Happened That Night",
            "Cold Case Solved: How {subject} Was Finally Caught After Years",
            "The Criminal Mind: Inside {subject}'s Psychology of Violence",
            "The Detective Who Never Gave Up on the {subject} Case",
            "Unsolved: The {subject} Mystery That Still Haunts Investigators"
        ]
    },
    {
        "name": "business_fraud",
        "rpm": 13.00,
        "tags": ["business", "finance", "crime", "entrepreneurship", "money"],
        "devto_tags": ["business", "career", "productivity", "discuss"],
        "angle": "corporate fraud, business scams, and financial deception exposed",
        "title_patterns": [
            "The {subject} Scam That Robbed Thousands of Investors",
            "How {subject} Built a Billion-Dollar Lie",
            "The Corporate Fraud That Nobody Saw Coming",
            "Inside the {subject} Ponzi Scheme: How It Worked",
            "The Whistleblower Who Exposed {subject}'s Massive Fraud"
        ]
    },
    {
        "name": "finance_scandal",
        "rpm": 18.00,
        "tags": ["finance", "money", "investing", "business", "economics"],
        "devto_tags": ["business", "career", "discuss", "news"],
        "angle": "financial scandals, market manipulation, and money crimes",
        "title_patterns": [
            "The {subject} Financial Scandal That Wiped Out Millions",
            "How Wall Street's {subject} Manipulated Markets for Years",
            "The Bank That Hid {subject} From Regulators for a Decade",
            "Inside the {subject} Collapse: Who Knew and When",
            "The Financial Crime of the Century: The {subject} Story"
        ]
    },
    {
        "name": "psych_thriller",
        "rpm": 11.00,
        "tags": ["psychology", "mentalhealth", "science", "behavior", "culture"],
        "devto_tags": ["psychology", "discuss", "motivation", "culture"],
        "angle": "dark psychology, manipulation tactics, and the human mind under pressure",
        "title_patterns": [
            "The Dark Psychology Behind {subject}'s Manipulation",
            "How {subject} Used These 7 Psychological Tricks on Everyone",
            "The Narcissist's Playbook: What {subject} Did to Control People",
            "Gaslighting at Scale: How {subject} Made Everyone Doubt Reality",
            "The Psychologist Who Studied {subject} and Couldn't Sleep After"
        ]
    },
    {
        "name": "ai_tech_dark",
        "rpm": 16.00,
        "tags": ["ai", "technology", "privacy", "future", "ethics"],
        "devto_tags": ["ai", "technology", "webdev", "discuss"],
        "angle": "dark side of AI and tech: surveillance, manipulation, and ethics",
        "title_patterns": [
            "The AI System That {subject} Used to Manipulate Millions",
            "How Big Tech's {subject} Algorithm Destroyed Mental Health",
            "The Dark Side of {subject}: What They Don't Want You to Know",
            "When AI Goes Wrong: The {subject} Disaster Nobody Prevented",
            "The Tech Billionaire Who Built {subject} and Then Ran Away"
        ]
    },
    {
        "name": "health_scandal",
        "rpm": 12.00,
        "tags": ["health", "medicine", "science", "crime", "society"],
        "devto_tags": ["discuss", "news", "culture", "health"],
        "angle": "medical fraud, pharma scandals, and health industry crimes",
        "title_patterns": [
            "The Drug Company That Hid {subject} from Patients for Years",
            "How {subject} Killed Thousands Before Anyone Acted",
            "The Doctor Who Exposed {subject} and Lost Everything",
            "Medical Fraud: The {subject} Scandal That Changed Healthcare",
            "The Clinical Trial Lie: How {subject} Faked the Data"
        ]
    },
    {
        "name": "personal_development",
        "rpm": 9.00,
        "tags": ["selfimprovement", "productivity", "mindset", "success", "motivation"],
        "devto_tags": ["motivation", "productivity", "career", "discuss"],
        "angle": "brutal truths about success, mindset, and personal transformation",
        "title_patterns": [
            "The {subject} Habit That Separates the Top 1% From Everyone Else",
            "I Tried {subject} for 30 Days and It Rewired My Brain",
            "Why {subject} Is the Only Productivity System That Actually Works",
            "The Hard Truth About {subject} Nobody Wants to Hear",
            "How {subject} Went From Zero to Extraordinary in 12 Months"
        ]
    },
    {
        "name": "productivity",
        "rpm": 8.50,
        "tags": ["productivity", "focus", "work", "systems", "mindset"],
        "devto_tags": ["productivity", "discuss", "career", "motivation"],
        "angle": "systems, focus, and productivity strategies that actually work",
        "title_patterns": [
            "The {subject} System Used by CEOs to Get 10x More Done",
            "Delete {subject} From Your Life and Watch Your Output Triple",
            "The Productivity Lie About {subject} You've Been Sold",
            "How to Use {subject} to Eliminate Distraction Forever",
            "The 2-Hour Work Block: Why {subject} Is the Secret"
        ]
    },
    {
        "name": "entrepreneurship",
        "rpm": 14.00,
        "tags": ["entrepreneurship", "startup", "business", "money", "success"],
        "devto_tags": ["business", "career", "productivity", "discuss"],
        "angle": "startup failures, founder betrayals, and brutal business lessons",
        "title_patterns": [
            "The Startup That {subject} Destroyed From the Inside",
            "How {subject} Raised $50M and Then Burned It All Down",
            "The Co-Founder Betrayal: How {subject} Lost Everything",
            "The Business Lesson From {subject} That Every Founder Must Learn",
            "Why {subject}'s Billion-Dollar Company Collapsed Overnight"
        ]
    },
    {
        "name": "relationships",
        "rpm": 8.00,
        "tags": ["relationships", "psychology", "love", "life", "culture"],
        "devto_tags": ["discuss", "culture", "motivation", "life"],
        "angle": "relationship betrayals, toxic dynamics, and emotional survival",
        "title_patterns": [
            "The Red Flags About {subject} That Everyone Ignored",
            "How {subject} Used Love as a Weapon Against Everyone They Knew",
            "The Relationship Pattern of {subject} That Destroys People",
            "I Escaped {subject}'s Toxic Cycle — Here's Exactly How",
            "The Science Behind Why We Stay With {subject} Types Too Long"
        ]
    },
    {
        "name": "mental_health",
        "rpm": 10.00,
        "tags": ["mentalhealth", "psychology", "wellness", "mindset", "healing"],
        "devto_tags": ["discuss", "motivation", "culture", "health"],
        "angle": "mental health truths, trauma recovery, and psychological resilience",
        "title_patterns": [
            "The Mental Health Crisis Nobody Talks About: {subject}",
            "How {subject} Trauma Rewires the Brain (And How to Heal)",
            "The Therapist Who Discovered {subject} Changes Everything",
            "Why {subject} Is the Hidden Cause of Most Mental Health Issues",
            "The Recovery Story: How I Survived {subject} and Built a New Life"
        ]
    }
]

# ── NICHE ROTATION ────────────────────────────────────────────────────────────
def get_todays_niche():
    """Rotate niches so no niche repeats within 13 days"""
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    index = day_of_year % len(NICHES)
    return NICHES[index]

# ── TOP EARNER RESEARCH ───────────────────────────────────────────────────────
def research_top_patterns(niche):
    """Use Groq to simulate top earner pattern research"""
    prompt = f"""You are a Medium/Dev.to analytics expert studying the top 10 highest-earning articles in the {niche['name']} niche.

Based on your deep knowledge of viral content patterns, provide a JSON object with:
{{
    "winning_title_structure": "description of what makes titles go viral in this niche",
    "optimal_word_count": number between 1000-1500,
    "hook_style": "first paragraph style that gets most reads",
    "content_structure": ["section1", "section2", "section3", "section4", "section5"],
    "emotional_triggers": ["trigger1", "trigger2", "trigger3"],
    "trending_subtopics": ["subtopic1", "subtopic2", "subtopic3"],
    "best_posting_time": "time in UTC",
    "top_performing_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Return ONLY the JSON, no other text."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "winning_title_structure": "Number + Power Word + Specific Outcome",
            "optimal_word_count": 1200,
            "hook_style": "shocking statistic or counter-intuitive claim",
            "content_structure": ["Hook", "The Problem", "The Deep Dive", "Real Examples", "Key Takeaways"],
            "emotional_triggers": ["shock", "curiosity", "fear", "hope"],
            "trending_subtopics": niche["tags"][:3],
            "best_posting_time": "07:00",
            "top_performing_tags": niche["tags"]
        }

# ── ARTICLE GENERATION ────────────────────────────────────────────────────────
def generate_article(niche, pattern):
    """Generate a high-quality article using winning patterns"""
    
    # Pick a title template and fill it
    title_template = random.choice(niche["title_patterns"])
    subjects = {
        "betrayal": ["Best Friend", "Business Partner", "Spouse", "Mentor", "Colleague"],
        "legal_drama": ["CEO", "Celebrity", "Politician", "Doctor", "Hedge Fund Manager"],
        "true_crime": ["Killer", "Con Artist", "Serial Fraudster", "Kidnapper", "Mastermind"],
        "business_fraud": ["Startup Founder", "Investment Firm", "Tech Giant", "Bank Executive", "Hedge Fund"],
        "finance_scandal": ["Trading Firm", "Crypto Exchange", "Investment Bank", "Hedge Fund", "CEO"],
        "psych_thriller": ["Cult Leader", "Narcissist", "Master Manipulator", "Corporate Psychopath", "Con Artist"],
        "ai_tech_dark": ["Facebook", "TikTok Algorithm", "Surveillance AI", "Deepfake Tech", "Data Broker"],
        "health_scandal": ["Pharmaceutical Giant", "Supplement Company", "Hospital Chain", "Drug Company", "Medical Device Maker"],
        "personal_development": ["Morning Routine", "Deep Work", "Digital Minimalism", "Cold Exposure", "Journaling"],
        "productivity": ["Time Blocking", "Single-Tasking", "Inbox Zero", "Weekly Review", "Deep Work"],
        "entrepreneurship": ["Series A Startup", "SaaS Founder", "E-commerce Brand", "Tech Unicorn", "Agency Owner"],
        "relationships": ["Narcissistic Partner", "Toxic Friend", "Controlling Parent", "Covert Abuser", "Love Bomber"],
        "mental_health": ["Childhood Trauma", "Burnout", "Anxiety Spiral", "Imposter Syndrome", "People Pleasing"]
    }
    subject = random.choice(subjects.get(niche["name"], ["Subject"]))
    title = title_template.replace("{subject}", subject)
    
    structure = " > ".join(pattern["content_structure"])
    triggers = ", ".join(pattern["emotional_triggers"])
    
    prompt = f"""You are a world-class investigative journalist writing for DeepDive Intelligence publication.

Write a {pattern['optimal_word_count']}-word article for Dev.to and Medium with this exact structure:

TITLE: {title}

NICHE: {niche['name']} — {niche['angle']}

STRUCTURE TO FOLLOW: {structure}

EMOTIONAL TRIGGERS TO USE: {triggers}

HOOK STYLE: {pattern['hook_style']}

CRITICAL RULES:
1. Start with a SHOCKING hook — a statistic, story, or counter-intuitive claim
2. Use subheadings (## for H2, ### for H3) throughout
3. Include at least 2 real-world examples or case studies
4. Use short paragraphs (2-3 sentences max)
5. Include a "Key Takeaways" section at the end with 3-5 bullet points
6. End with a strong call-to-action to follow DeepDive Intelligence
7. Write in a gripping, page-turner style — like a true crime documentary
8. Add internal tension and suspense throughout
9. Format in proper Markdown
10. Do NOT use generic AI phrases like "In conclusion" or "It's worth noting"

The article must feel like it was written by a seasoned investigative journalist, not an AI.
Return ONLY the article in Markdown format, starting directly with the title."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

# ── SEO OPTIMIZATION ──────────────────────────────────────────────────────────
def optimize_seo(article, niche, pattern):
    """Generate SEO-optimized metadata"""
    prompt = f"""Given this article about {niche['name']}, generate SEO metadata as JSON:

Article preview: {article[:500]}

Return ONLY this JSON:
{{
    "seo_title": "SEO optimized title under 60 chars",
    "meta_description": "compelling description under 160 chars",
    "canonical_url": "",
    "main_image_alt": "descriptive alt text for main image"
}}"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=300
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "seo_title": article.split('\n')[0][:60].replace('#', '').strip(),
            "meta_description": f"Investigative deep dive into {niche['name']} stories that will shock you.",
            "canonical_url": "",
            "main_image_alt": f"DeepDive Intelligence - {niche['name']} investigation"
        }

# ── PUBLISH TO DEV.TO ─────────────────────────────────────────────────────────
def publish_to_devto(title, article, niche, seo_meta):
    """Publish article to Dev.to via API"""
    
    # Add YouTube channel link at the end
    article_with_cta = article + f"""

---

*🎬 Watch our video investigations on [The Betrayal DeepDive YouTube Channel](https://www.youtube.com/@BetrayalDeepDive)*

*Follow DeepDive Intelligence for daily investigations into betrayal, fraud, legal drama, and the dark side of human nature.*"""

    tags = niche["devto_tags"][:4]  # Dev.to allows max 4 tags
    
    payload = {
        "article": {
            "title": title,
            "body_markdown": article_with_cta,
            "published": True,
            "tags": tags,
            "description": seo_meta["meta_description"],
            "canonical_url": seo_meta["canonical_url"] or None,
            "series": "DeepDive Intelligence"
        }
    }
    
    response = requests.post(
        "https://dev.to/api/articles",
        headers={
            "api-key": DEVTO_API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    if response.status_code == 201:
        data = response.json()
        return {
            "success": True,
            "url": data.get("url"),
            "id": data.get("id"),
            "title": data.get("title")
        }
    else:
        return {
            "success": False,
            "error": response.text,
            "status": response.status_code
        }

# ── SAVE FOR MEDIUM ───────────────────────────────────────────────────────────
def save_for_medium(title, article, niche):
    """Save article to file for Medium manual/browser publishing"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"medium_article_{niche['name']}_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# MEDIUM ARTICLE — {niche['name'].upper()}\n")
        f.write(f"# Tags: {', '.join(niche['tags'])}\n\n")
        f.write(article)
    
    return filename

# ── QUALITY SCORING ───────────────────────────────────────────────────────────
def score_article(article):
    """Score article quality 1-10"""
    score = 5.0
    
    # Length check
    word_count = len(article.split())
    if word_count >= 1000: score += 1.0
    if word_count >= 1200: score += 0.5
    
    # Structure checks
    if "##" in article: score += 0.5        # Has subheadings
    if "###" in article: score += 0.3       # Has sub-subheadings
    if "Key Takeaway" in article: score += 0.5  # Has takeaways
    if "---" in article: score += 0.2       # Has dividers
    
    # Hook strength
    first_para = article[:300]
    if any(word in first_para.lower() for word in ["shocking", "nobody", "secret", "truth", "warning"]):
        score += 0.5
    
    # CTA check
    if "follow" in article.lower() or "subscribe" in article.lower():
        score += 0.3
    
    # YouTube link
    if "youtube" in article.lower() or "betrayaldeepdive" in article.lower():
        score += 0.2
    
    return min(round(score, 1), 10.0)

# ── TELEGRAM NOTIFICATION ─────────────────────────────────────────────────────
def send_telegram(message):
    """Send notification to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT,
        "text": message,
        "parse_mode": "HTML"
    })

# ── EARNINGS FORECAST ─────────────────────────────────────────────────────────
def forecast_earnings(niche, quality_score):
    """Forecast article earnings over 30 days"""
    base_reads = {
        "betrayal": 800, "legal_drama": 600, "true_crime": 700,
        "business_fraud": 500, "finance_scandal": 400, "psych_thriller": 600,
        "ai_tech_dark": 900, "health_scandal": 500, "personal_development": 1200,
        "productivity": 1100, "entrepreneurship": 800, "relationships": 1000,
        "mental_health": 900
    }
    
    reads = base_reads.get(niche["name"], 500) * (quality_score / 10)
    # Dev.to pays approximately $0.01-0.05 per 1000 reads (bonus program)
    devto_earnings = (reads / 1000) * 0.03
    # Medium Partner Program (future) pays ~$4-8 per 1000 reads
    medium_future = (reads / 1000) * 6.0
    
    return {
        "estimated_reads_30d": int(reads),
        "devto_earnings_usd": round(devto_earnings, 4),
        "medium_future_usd": round(medium_future, 2)
    }

# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def main():
    print("🚀 DeepDive Intelligence Content Publisher Starting...")
    
    # Step 1: Get today's niche
    niche = get_todays_niche()
    print(f"📌 Today's niche: {niche['name']} (RPM: ${niche['rpm']})")
    
    # Step 2: Research top earner patterns
    print("🔍 Researching top earner patterns...")
    pattern = research_top_patterns(niche)
    
    # Step 3: Generate article
    print("✍️ Generating article...")
    article = generate_article(niche, pattern)
    
    # Extract title from article
    lines = article.strip().split('\n')
    title = lines[0].replace('#', '').strip()
    
    # Step 4: SEO optimization
    print("🔍 Optimizing SEO...")
    seo_meta = optimize_seo(article, niche, pattern)
    
    # Step 5: Score article
    quality_score = score_article(article)
    print(f"⭐ Quality Score: {quality_score}/10")
    
    # Step 6: Publish to Dev.to
    print("📤 Publishing to Dev.to...")
    devto_result = publish_to_devto(title, article, niche, seo_meta)
    
    # Step 7: Save for Medium
    medium_file = save_for_medium(title, article, niche)
    
    # Step 8: Forecast earnings
    forecast = forecast_earnings(niche, quality_score)
    
    # Step 9: Send Telegram notification
    if devto_result["success"]:
        status_icon = "✅"
        devto_status = f"Published: {devto_result['url']}"
    else:
        status_icon = "❌"
        devto_status = f"Failed: {devto_result.get('error', 'Unknown error')[:100]}"
    
    message = f"""
{status_icon} <b>DeepDive Intelligence — Daily Article</b>

📰 <b>Title:</b> {title[:80]}...
🎯 <b>Niche:</b> {niche['name']} (RPM: ${niche['rpm']})
⭐ <b>Quality:</b> {quality_score}/10
📊 <b>Word Count:</b> {len(article.split())} words

<b>Dev.to:</b> {devto_status}
<b>Medium:</b> Saved → apply Partner Program at Month 3

📈 <b>30-Day Forecast:</b>
• Estimated reads: {forecast['estimated_reads_30d']:,}
• Dev.to earnings: ${forecast['devto_earnings_usd']}
• Medium (Month 3+): ${forecast['medium_future_usd']}/article

🏷️ <b>Tags:</b> {', '.join(niche['devto_tags'])}
"""
    
    send_telegram(message)
    print("✅ Telegram notification sent")
    print(f"📄 Article saved for Medium: {medium_file}")
    print("🎉 Pipeline complete!")

if __name__ == "__main__":
    main()
