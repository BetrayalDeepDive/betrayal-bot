"""
PUBLISHING ARCHIVE — one of the 5 "single source of truth" homes from
the Media Empire operating model (Topic Database, Production Queue,
Publishing Archive, Product Library, CEO Dashboard). This is the
Publishing Archive: a durable, per-channel record of every episode
actually published, used for real cross-linking (companion pages linking
to genuinely related past episodes) and for building resource pages
(clustering real published episodes by theme, not a guess).

Free-tier: one JSON file per channel, same persistence pattern as
everything else (state.json, topic_database.json, fingerprint_history.json).
"""

import json
import datetime
from pathlib import Path

MAX_ARCHIVE_DISPLAY = 200  # sanity ceiling on in-memory list size for clustering ops


def _archive_file(channel_dir):
    return Path(channel_dir) / "publishing_archive.json"


def load_archive(channel_dir):
    f = _archive_file(channel_dir)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def add_archive_entry(channel_dir, entry: dict):
    """
    entry should contain: episode_number, title, video_url, niche_name,
    topic, companion_page_url, published_at (auto-filled if missing).
    Call this ONLY after confirmed real publish success — same timing
    discipline as fingerprint logging and topic-marking.
    """
    archive = load_archive(channel_dir)
    entry = dict(entry)
    entry.setdefault("published_at", datetime.datetime.now().isoformat())
    archive.append(entry)
    try:
        # FIX: was missing this — if channel_dir didn't already exist, the
        # write below failed silently (caught by the broad except), and the
        # archive entry was never actually persisted. In real pipeline runs
        # this directory always exists already, but this is a real
        # robustness gap regardless — found via a test that silently lost
        # data because of exactly this.
        Path(channel_dir).mkdir(parents=True, exist_ok=True)
        _archive_file(channel_dir).write_text(json.dumps(archive, indent=2))
    except Exception:
        pass
    return entry


def get_related_episodes(channel_dir, niche_name, exclude_episode_number, limit=4):
    """
    Real cross-linking data — returns the most recent OTHER episodes in
    the same niche, for the "Related Cases" section on a companion page.
    Returns [] gracefully if there's no archive yet (a channel's first
    few episodes genuinely have nothing to link to).
    """
    archive = load_archive(channel_dir)
    same_niche = [e for e in archive
                  if e.get("niche_name") == niche_name
                  and e.get("episode_number") != exclude_episode_number]
    same_niche.sort(key=lambda e: e.get("published_at", ""), reverse=True)
    return [{"title": e["title"], "url": e["companion_page_url"]} for e in same_niche[:limit]]


def get_niche_clusters(channel_dir, min_cluster_size=3):
    """
    Groups published episodes by niche for resource-page generation.
    Returns {niche_name: [episode entries]} — only includes niches with
    at least min_cluster_size episodes, since a resource page for a
    2-episode niche isn't a genuine evergreen cluster yet.
    """
    archive = load_archive(channel_dir)
    clusters = {}
    for e in archive:
        clusters.setdefault(e.get("niche_name", "unknown"), []).append(e)
    return {niche: episodes for niche, episodes in clusters.items()
            if len(episodes) >= min_cluster_size}
