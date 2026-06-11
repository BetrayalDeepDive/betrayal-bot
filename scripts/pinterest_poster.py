"""
pinterest_poster.py
====================
Posts 5 pins per day to Pinterest automatically.
Pinterest is a SEARCH ENGINE — pins get discovered for YEARS.
This builds passive affiliate income with zero ongoing work.

Monetization strategy:
- Each pin links to affiliate products (Amazon, ClickBank)
- Or links back to YouTube channel (drives subscribers)
- Or links to newsletter (builds email list)

Free tools: Pinterest API v5 (free), Pillow for image creation, Groq for text

ENV VARS:
  PINTEREST_ACCESS_TOKEN  (get from developers.pinterest.com — free)
  PINTEREST_BOARD_ID      (your board ID)
  GROQ_API_KEY
"""

import os, json, re, requests, logging, textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PIN] %(message)s")
log = logging.getLogger(__name__)

GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
PIN_TOKEN     = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
PIN_BOARD_ID  = os.environ.get("PINTEREST_BOARD_ID", "")
OUTPUT_DIR    = os.environ.get("OUTPUT_DIR", "/tmp/empire_output")
CHANNEL_NAME  = "BETRAYAL DEEPDIVE"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PINTEREST_API = "https://api.pinterest.com/v5"

# Pin templates — different styles for variety
PIN_STYLES = [
    {"bg": (15, 15, 25),    "text": (255, 255, 255), "accent": (220, 50, 50)},   # dark red
    {"bg": (10, 10, 20),    "text": (255, 255, 255), "accent": (50, 150, 220)},  # dark blue
    {"bg": (20, 10, 10),    "text": (255, 230, 200), "accent": (255, 150, 50)},  # dark orange
    {"bg": (5, 20, 15),     "text": (220, 255, 220), "accent": (50, 200, 100)},  # dark green
    {"bg": (20, 10, 25),    "text": (240, 220, 255), "accent": (180, 100, 255)}, # dark purple
]

# Affiliate link topics that earn money on Pinterest
MONETIZABLE_TOPICS = [
    "psychology books that explain dark human behavior",
    "true crime documentary recommendations Netflix",
    "self defense tips every woman should know India",
    "how to detect if someone is lying to you",
    "red flags in relationships you should never ignore",
    "financial fraud protection tips India",
    "best crime thriller books 2024 2025",
    "how to protect yourself from narcissists",
    "signs your business partner is stealing from you",
    "emotional intelligence books recommendations",
]


def groq_text(prompt: str, max_tokens: int = 500) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile",
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": 0.7},
        timeout=30
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def generate_pin_content(topic: str, yt_channel_url: str = "") -> dict:
    """Generate pin title, description, and image text."""
    prompt = f"""Create Pinterest pin content for topic: {topic}

Pinterest audience: people interested in psychology, true crime, relationships, self-improvement.
Our brand: BETRAYAL DEEPDIVE — true crime and betrayal stories.

Return ONLY valid JSON:
{{
  "title": "Pin title (max 100 chars, keyword-rich for Pinterest SEO)",
  "description": "2-3 sentences describing the pin. Include 5-10 relevant hashtags at end.",
  "image_headline": "Short punchy text for the image (max 8 words)",
  "image_subtext": "Supporting text (max 12 words)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}"""

    raw = groq_text(prompt)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return {
            "title": topic[:100],
            "description": f"Shocking story about {topic}. Follow for more.",
            "image_headline": topic[:40],
            "image_subtext": "Follow for more stories",
            "keywords": ["betrayal", "truecrime", "psychology"],
        }


def create_pin_image(headline: str, subtext: str, style: dict,
                     channel: str, out_path: str) -> str:
    """Creates a 1000x1500 Pinterest image using Pillow."""
    W, H = 1000, 1500
    img  = Image.new("RGB", (W, H), color=style["bg"])
    draw = ImageDraw.Draw(img)

    # Background gradient effect (simple dark-to-slightly-lighter)
    for y in range(H):
        alpha = int(y / H * 30)
        r_val = min(255, style["bg"][0] + alpha)
        g_val = min(255, style["bg"][1] + alpha)
        b_val = min(255, style["bg"][2] + alpha)
        draw.line([(0, y), (W, y)], fill=(r_val, g_val, b_val))

    # Accent bar at top
    draw.rectangle([(0, 0), (W, 8)], fill=style["accent"])
    draw.rectangle([(0, H-8), (W, H)], fill=style["accent"])

    # Channel name (top)
    try:
        font_large  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        font_brand  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        font_large  = ImageFont.load_default()
        font_medium = font_large
        font_small  = font_large
        font_brand  = font_large

    # Brand name
    draw.text((W//2, 60), channel, fill=style["accent"],
              font=font_brand, anchor="mm")

    # Decorative line
    draw.rectangle([(80, 100), (W-80, 103)], fill=style["accent"])

    # Main headline (word-wrapped)
    wrapped = textwrap.fill(headline.upper(), width=18)
    lines   = wrapped.split("\n")
    y_start = H // 2 - (len(lines) * 70 // 2)
    for line in lines:
        draw.text((W//2, y_start), line, fill=style["text"],
                  font=font_large, anchor="mm")
        y_start += 70

    # Subtext
    wrapped_sub = textwrap.fill(subtext, width=30)
    sub_lines   = wrapped_sub.split("\n")
    y_sub = y_start + 40
    for line in sub_lines:
        draw.text((W//2, y_sub), line, fill=(*style["accent"], 200),
                  font=font_medium, anchor="mm")
        y_sub += 50

    # Bottom CTA
    draw.text((W//2, H - 80), "Follow for more shocking stories",
              fill=style["text"], font=font_small, anchor="mm")

    img.save(out_path, "JPEG", quality=90)
    return out_path


def upload_pin_image_to_github(image_path: str) -> str:
    """
    Uploads pin image to GitHub Releases as public CDN.
    Pinterest requires a public URL for the image.
    Returns public URL.
    """
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo  = os.environ.get("GITHUB_REPOSITORY", "")

    if not github_token or not github_repo:
        log.warning("No GitHub token — cannot upload pin image")
        return ""

    from datetime import date
    tag  = f"pin-assets-{date.today().strftime('%Y-%m-%d')}"
    name = f"Pin Assets {date.today().strftime('%Y-%m-%d')}"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept":        "application/vnd.github+json",
    }

    # Get or create release
    r = requests.get(
        f"https://api.github.com/repos/{github_repo}/releases/tags/{tag}",
        headers=headers, timeout=20
    )
    if r.status_code == 200:
        release_id = r.json()["id"]
    else:
        r2 = requests.post(
            f"https://api.github.com/repos/{github_repo}/releases",
            headers=headers,
            json={"tag_name": tag, "name": name, "draft": False},
            timeout=20
        )
        if r2.status_code not in (200, 201):
            return ""
        release_id = r2.json()["id"]

    # Upload image
    filename  = os.path.basename(image_path)
    file_size = os.path.getsize(image_path)
    upload_url = f"https://uploads.github.com/repos/{github_repo}/releases/{release_id}/assets?name={filename}"

    with open(image_path, "rb") as f:
        r3 = requests.post(
            upload_url,
            headers={**headers, "Content-Type": "image/jpeg",
                     "Content-Length": str(file_size)},
            data=f, timeout=60
        )
    if r3.status_code in (200, 201):
        return r3.json().get("browser_download_url", "")
    return ""


def post_pin(title: str, description: str, image_url: str,
             link: str = "") -> dict:
    """Posts a pin to Pinterest using the API v5."""
    if not PIN_TOKEN or not PIN_BOARD_ID:
        log.warning("Pinterest credentials not set — skipping pin")
        return {"success": False, "error": "No credentials"}

    payload = {
        "board_id":   PIN_BOARD_ID,
        "title":      title[:100],
        "description": description[:500],
        "media_source": {
            "source_type": "image_url",
            "url":         image_url,
        },
    }
    if link:
        payload["link"] = link

    r = requests.post(
        f"{PINTEREST_API}/pins",
        headers={
            "Authorization": f"Bearer {PIN_TOKEN}",
            "Content-Type":  "application/json",
        },
        json=payload, timeout=30
    )

    if r.status_code in (200, 201):
        pin_id  = r.json().get("id", "")
        pin_url = f"https://pinterest.com/pin/{pin_id}"
        log.info("✅ Pin posted: %s", pin_url)
        return {"success": True, "pin_id": pin_id, "url": pin_url}
    else:
        log.error("Pin failed %d: %s", r.status_code, r.text[:200])
        return {"success": False, "error": r.text[:200]}


def create_daily_pins(topics: list, yt_channel_url: str = "",
                      n_pins: int = 5) -> list:
    """Creates and posts n_pins Pinterest pins per day."""
    results  = []
    styles   = PIN_STYLES * 3  # repeat styles if needed

    for i, topic in enumerate(topics[:n_pins]):
        log.info("Creating pin %d: %s", i+1, topic[:50])

        # Generate content
        content   = generate_pin_content(topic, yt_channel_url)
        style     = styles[i % len(styles)]
        img_path  = os.path.join(OUTPUT_DIR, f"pin_{i+1}.jpg")

        # Create image
        create_pin_image(
            content["image_headline"],
            content["image_subtext"],
            style,
            CHANNEL_NAME,
            img_path
        )

        # Upload image to public CDN
        image_url = upload_pin_image_to_github(img_path)
        if not image_url:
            log.warning("Could not get public URL for pin image — skipping")
            continue

        # Post to Pinterest
        result = post_pin(
            title=content["title"],
            description=content["description"],
            image_url=image_url,
            link=yt_channel_url,
        )
        result["topic"] = topic
        results.append(result)

    log.info("Pinterest: %d/%d pins posted", sum(1 for r in results if r.get("success")), n_pins)
    return results


if __name__ == "__main__":
    topics = MONETIZABLE_TOPICS[:5]
    results = create_daily_pins(topics)
    print(json.dumps(results, indent=2))
