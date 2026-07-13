# multi_api_engine.py
# Betrayal DeepDive - Multi API Engine for Freelance Content Generation

import os
import json
import time
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

GROQ_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
GEMINI_MODEL = "gemini-2.5-flash"
MISTRAL_MODEL = "mistral-large-latest"


def call_groq(prompt, system_prompt="You are an expert content writer.", max_tokens=4000):
    """Call Groq API with fallback models"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    for model in GROQ_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.8
            }
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq model {model} failed: {e}")
            continue
    return None


def call_gemini(prompt, system_prompt="You are an expert content writer."):
    """Call Gemini API"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
            "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.8}
        }
        response = requests.post(
            f"{url}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini failed: {e}")
    return None


def call_mistral(prompt, system_prompt="You are an expert content writer."):
    """Call Mistral API"""
    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MISTRAL_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.8
        }
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Mistral failed: {e}")
    return None


def generate_content(prompt, system_prompt="You are an expert content writer.", max_retries=3):
    """Main content generation with Groq -> Gemini -> Mistral fallback"""
    print("Trying Groq...")
    result = call_groq(prompt, system_prompt)
    if result:
        print("Groq succeeded!")
        return result, "groq"

    print("Groq failed. Trying Gemini...")
    result = call_gemini(prompt, system_prompt)
    if result:
        print("Gemini succeeded!")
        return result, "gemini"

    print("Gemini failed. Trying Mistral...")
    result = call_mistral(prompt, system_prompt)
    if result:
        print("Mistral succeeded!")
        return result, "mistral"

    print("All APIs failed!")
    return None, None


def generate_seo_article(topic, word_count=1200):
    """Generate SEO blog article"""
    prompt = f"""Write a {word_count}-word SEO-optimized blog article about: {topic}

Structure:
- Compelling H1 title with primary keyword
- Introduction with hook (150 words)
- 4-5 H2 sections with H3 subsections
- Each section 200-250 words
- Conclusion with CTA (100 words)
- Meta description (155 characters)
- 10 LSI keywords list

Make it engaging, informative, and optimized for search engines."""

    system = "You are an expert SEO content writer with 10 years of experience writing viral blog articles."
    return generate_content(prompt, system)


def generate_youtube_script(topic, duration_minutes=8):
    """Generate YouTube script"""
    prompt = f"""Write a {duration_minutes}-minute YouTube script about: {topic}

Structure:
- HOOK (0-30 seconds): Most shocking/interesting fact first
- INTRO (30-60 seconds): What viewers will learn
- MAIN CONTENT (5-6 sections, each 60-90 seconds)
- RE-ENGAGEMENT HOOK every 2 minutes
- OUTRO (30 seconds): Subscribe CTA

Add [PAUSE] for dramatic effect, [B-ROLL: description] for visuals.
Make it conversational, engaging, with pattern interrupts."""

    system = "You are a top YouTube scriptwriter who has written for channels with 10M+ subscribers."
    return generate_content(prompt, system)


def generate_social_media_pack(brand, niche, days=7):
    """Generate social media captions pack"""
    prompt = f"""Create {days} days of social media content for:
Brand: {brand}
Niche: {niche}

For each day provide:
- Instagram caption (150 words max) with 20 hashtags
- Twitter/X post (280 chars max)
- Facebook post (100 words)
- Best posting time

Make content engaging, varied, and on-brand."""

    system = "You are a social media expert who manages accounts with millions of followers."
    return generate_content(prompt, system)


def generate_intelligence_report(topic):
    """Generate deep intelligence report"""
    prompt = f"""Create a comprehensive intelligence report on: {topic}

Include:
1. Executive Summary (300 words)
2. Market Overview & Size
3. Key Players & Competitive Analysis
4. Trends & Opportunities
5. Threats & Challenges
6. Data & Statistics (cite sources)
7. Strategic Recommendations
8. Future Outlook (12-24 months)
9. Conclusion

Format professionally with headers and bullet points."""

    system = "You are a senior business intelligence analyst with expertise in market research."
    return generate_content(prompt, system)


if __name__ == "__main__":
    print("Multi API Engine Ready")
    print("Available functions:")
    print("- generate_seo_article(topic)")
    print("- generate_youtube_script(topic)")
    print("- generate_social_media_pack(brand, niche)")
    print("- generate_intelligence_report(topic)")
