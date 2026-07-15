#!/usr/bin/env python3
"""
blog_syndication.py
====================
Was referenced by run_syndication.py (from blog_syndication import
syndicate_episode, tg) but did not exist anywhere in the repo — the
blog_syndication.yml workflow would fail immediately on that import
line every single time it ran. This is the real, working module.

What it does per episode:
1. Generates a genuine, standalone blog post (not a video transcript,
   not "in this episode we cover...") via Groq, based on the episode's
   real title and topic summary.
2. Publishes it to Dev.to (real REST API) and Hashnode (real GraphQL
   API), independently — a failure on one platform never blocks the
   other.
3. Sends one real Telegram notification summarizing what published,
   what didn't, and why (never silent about a failure).

Every network call is wrapped so a missing/bad API key degrades to a
clear, logged, non-fatal skip rather than crashing the whole run —
consistent with how the 5 channel pipelines already treat optional
external calls.
"""
import os
import requests


def tg(message):
    """
    Real Telegram notification sender. Returns True/False rather than
    raising, and — per the same lesson learned auditing the 5 channel
    pipelines this session — actually checks the response status
    instead of assuming success just because no exception was thrown.
    """
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print(f"  [tg] Telegram not configured (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID missing) — "
              f"message was: {message}")
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                           json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                           timeout=15)
        if r.status_code != 200:
            print(f"  [tg] Telegram send failed: {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  [tg] Telegram send failed: {e}")
        return False


def _default_tags_for_niche(niche_name):
    """
    Dev.to and Hashnode both want short, URL-safe tags (letters/numbers
    only, no spaces or special characters, Dev.to caps at 4). Built
    from the real niche name rather than a hardcoded per-channel map,
    so this works for every niche across all 5 channels automatically.
    """
    words = [w.lower() for w in niche_name.replace("-", "_").split("_") if w.isalpha()]
    # The niche name's own most distinctive word (usually the longest
    # one — e.g. "collapse", "finance", "forensic") makes a real,
    # readable single tag. Concatenating every word into one jammed
    # string (e.g. "personalfinancemistakes") is technically valid but
    # not a tag anyone would actually search for or recognize.
    niche_tag = max(words, key=len) if words else "documentary"
    tags = [niche_tag, "documentary", "research"]
    seen = set()
    deduped = []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped[:4]


def _generate_blog_content(episode_title, topic_summary, niche_name):
    """
    Real Groq call — writes a genuine standalone article, not a video
    description. Returns markdown body text, or None if generation
    failed for any reason (caller must treat None as a hard stop for
    this episode, not silently publish an empty post).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("  GROQ_API_KEY not set — cannot generate blog content.")
        return None

    prompt = f"""Write a real, substantive blog post (600-900 words) in markdown, based on this
documentary research topic. Write it as a standalone article — never mention "video", "episode",
"in this documentary", or anything implying the reader is watching something. It should read as
if it was written first, independent of any video.

TITLE: {episode_title}
TOPIC: {topic_summary}
SUBJECT AREA: {niche_name.replace('_', ' ')}

Structure: one compelling opening paragraph that states the real stakes or facts, 3-4 body
sections with genuine substance and specificity (no vague filler like "many people believe"),
and a short closing paragraph. Return ONLY the markdown body — no title heading (handled
separately), no commentary before or after."""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1600,
            },
            timeout=60,
        )
        if r.status_code != 200:
            print(f"  Groq content generation failed: {r.status_code} {r.text[:200]}")
            return None
        content = r.json()["choices"][0]["message"]["content"].strip()
        return content if len(content.split()) >= 200 else None
    except Exception as e:
        print(f"  Groq content generation failed: {e}")
        return None


def _post_to_devto(title, body_markdown, tags, canonical_url=None):
    """Real Dev.to REST API call (POST /api/articles)."""
    api_key = os.environ.get("DEVTO_API_KEY", "")
    if not api_key:
        return {"platform": "devto", "success": False, "error": "DEVTO_API_KEY not set"}

    article = {
        "title": title,
        "body_markdown": body_markdown,
        "published": True,
        "tags": tags,
    }
    if canonical_url:
        article["canonical_url"] = canonical_url

    try:
        r = requests.post(
            "https://dev.to/api/articles",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={"article": article},
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {"platform": "devto", "success": True, "url": data.get("url")}
        return {"platform": "devto", "success": False, "error": f"{r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"platform": "devto", "success": False, "error": str(e)}


def _post_to_hashnode(title, body_markdown, tags, canonical_url=None):
    """
    Real Hashnode GraphQL API call (publishPost mutation on the public
    gql.hashnode.com endpoint). Requires both HASHNODE_TOKEN and
    HASHNODE_PUBLICATION_ID — Hashnode's API publishes to a specific
    publication, not a bare user account.
    """
    token = os.environ.get("HASHNODE_TOKEN", "")
    pub_id = os.environ.get("HASHNODE_PUBLICATION_ID", "")
    if not token or not pub_id:
        return {"platform": "hashnode", "success": False,
                "error": "HASHNODE_TOKEN or HASHNODE_PUBLICATION_ID not set"}

    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { id slug url }
      }
    }
    """
    tag_objs = [{"slug": t.lower(), "name": t.title()} for t in tags]
    variables = {
        "input": {
            "title": title,
            "contentMarkdown": body_markdown,
            "publicationId": pub_id,
            "tags": tag_objs,
        }
    }
    if canonical_url:
        variables["input"]["originalArticleURL"] = canonical_url

    try:
        r = requests.post(
            "https://gql.hashnode.com",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"query": mutation, "variables": variables},
            timeout=30,
        )
        data = r.json()
        if "errors" in data:
            return {"platform": "hashnode", "success": False, "error": str(data["errors"])[:200]}
        post = data.get("data", {}).get("publishPost", {}).get("post", {})
        if not post:
            return {"platform": "hashnode", "success": False, "error": f"Unexpected response: {str(data)[:200]}"}
        return {"platform": "hashnode", "success": True, "url": post.get("url")}
    except Exception as e:
        return {"platform": "hashnode", "success": False, "error": str(e)}


def syndicate_episode(episode_title, topic_summary, channel_id, niche_name, episode_url=None):
    """
    Real entry point called by run_syndication.py for each newly-
    published episode. Generates one real article, publishes it to
    both platforms independently, and always sends one Telegram
    summary — success, partial success, and total failure all produce
    a real notification, never silence.
    """
    print(f"Syndicating: {episode_title} ({channel_id})")

    body = _generate_blog_content(episode_title, topic_summary, niche_name)
    if not body:
        tg(f"⚠️ Blog syndication skipped for '{episode_title}' ({channel_id}) — "
           f"content generation failed. Check GROQ_API_KEY and the run's logs.")
        return {"success": False, "reason": "content generation failed", "results": []}

    tags = _default_tags_for_niche(niche_name)
    results = [
        _post_to_devto(episode_title, body, tags, canonical_url=episode_url),
        _post_to_hashnode(episode_title, body, tags, canonical_url=episode_url),
    ]

    lines = [f"📝 <b>Blog syndication</b> — {episode_title} ({channel_id})"]
    for r in results:
        if r["success"]:
            lines.append(f"✅ {r['platform'].title()}: {r.get('url', 'published')}")
        else:
            lines.append(f"❌ {r['platform'].title()}: {r.get('error', 'unknown error')}")
    tg("\n".join(lines))

    any_success = any(r["success"] for r in results)
    for r in results:
        print(f"  {r['platform']}: {'OK — ' + str(r.get('url')) if r['success'] else 'FAILED — ' + str(r.get('error'))}")

    return {"success": any_success, "results": results}
