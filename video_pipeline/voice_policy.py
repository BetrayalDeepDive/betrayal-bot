"""One list of voices allowed to speak on any channel.

Direct instruction: "I don't want anything related to robotic voice, only
humanic voices."

WHY THIS IS A MODULE AND NOT A DELETED FUNCTION
-----------------------------------------------
The robotic routes were already unable to publish, and that was already
known and written down. The audio gate weights voice tier at 40% against
an 8.5 floor, so a route's ceiling is tier*0.4 + 6.0:

    gTTS   tier 4.0 -> ceiling 7.6   cannot pass
    espeak tier 1.5 -> ceiling 6.6   cannot pass

And yet a real Short went live on the channel narrated by espeak. The
arithmetic was correct and it did not help, because the Shorts scorer was
a different scorer with a different bar, and the route was still wired in
and still reachable. A synthesiser that is installed and called will
eventually be heard.

So the rule is not arithmetic any more. These routes are removed from
every chain, and this module is the single place that says which names
are allowed to reach an audience. Anything not named here is refused
outright, whatever it scores.
"""

# Every route that produces a human-sounding voice. Names match what the
# pipelines record in edge_voice / LAST_TTS_ROUTE and what quality_scoring
# reads back, so a rename cannot silently create a hole.
HUMAN_ROUTES = frozenset({
    "kokoro", "kokoro-local",
    "edge-tts", "edge-tts-ssml",
    "groq-orpheus",
    "elevenlabs",
    "fish-audio", "fish-audio-backup",
    "piper", "piper-local",
})

# Removed from every chain. Kept by name so that if one is ever
# reintroduced by accident, is_human() rejects it rather than defaulting
# to allow, and the preflight check below has something concrete to test.
ROBOTIC_ROUTES = frozenset({
    "gtts", "gtts-fallback",
    "espeak", "espeak-ng", "espeak-offline-lastresort",
})


def is_human(route) -> bool:
    """True only for routes cleared to reach an audience.

    Unknown names are refused. A new synthesiser has to be added here
    deliberately, which is the point -- the espeak Short reached YouTube
    because nothing anywhere had to approve it first.
    """
    name = str(route or "").strip().lower()
    if not name:
        return False
    if name in ROBOTIC_ROUTES:
        return False
    if name in HUMAN_ROUTES:
        return True
    # An edge-tts voice id ("en-GB-RyanNeural") is the route, recorded
    # verbatim by the per-voice fallback loop. Neural voice ids are the one
    # family that cannot be enumerated ahead of time.
    return name.endswith("neural")


def refuse_reason(route) -> str:
    """Human-readable reason a route is not allowed, for logs and Telegram."""
    name = str(route or "").strip().lower()
    if not name:
        return "no voice route was recorded"
    if name in ROBOTIC_ROUTES:
        return "%s is a robotic synthesiser and is not allowed to publish" % name
    return "%s is not a recognised human voice route" % name
