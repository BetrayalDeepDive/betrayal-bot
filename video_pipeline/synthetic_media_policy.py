"""
Whether to declare "Altered or synthetic content" on a YouTube upload.

WHY THIS EXISTS AS A MODULE RATHER THAN A BOOLEAN IN FIVE UPLOAD PAYLOADS
------------------------------------------------------------------------
It was a boolean in five upload payloads. Every one of them read

    "containsSyntheticMedia": True   # mandatory AI disclosure since Mar 2024

and that comment is wrong. Nothing about this format makes it mandatory. The
cost was real and measurable: every video on the first channel carried the
"Made with AI" label, on the player rather than tucked in the description,
because health is one of the sensitive categories that gets the louder
treatment. The label was self-inflicted, not imposed.

Proven on 2026-08-02 by uploading a private probe with the flag false and
reading it in Studio: YouTube stores what we declare and does not add the
label on its own for this kind of content. So the declaration is entirely
our decision — which makes it worth making deliberately, in one place, with
the reasoning attached.

WHAT THE POLICY ACTUALLY REQUIRES
---------------------------------
Disclosure is for REALISTIC content — content a viewer "could easily mistake
for a real person, place, scene, or event". The test is realism plus
deception potential, and Studio's own three bullets say the same thing:

    * makes a real person appear to say or do something they didn't
    * alters footage of a real event or place
    * generates a realistic-looking scene that didn't actually occur

EXPLICITLY EXEMPT, and this is the list that covers our formats:
    * AI voiceover over illustrations / animated faceless content
    * generative AI for production assistance — scripts, ideas, titles,
      descriptions, captions
    * content that is clearly unrealistic or animated
    * changes that are inconsequential

WHAT EACH CHANNEL SHIPS, AND THEREFORE WHY IT IS EXEMPT
-------------------------------------------------------
All five are AI narration over graphics. None synthesises a person, a real
voice, or footage of a real event:

    betrayal_deepdive  charts, timelines, differential boards, text cards,
                       and real figures from the real CC BY paper
    evidence_room      motion graphics and real stock footage inserts
    control_files      motion graphics and real stock footage inserts
    archive            motion graphics, maps, and real stock footage
    collapse_index     charts, maps, and real stock footage

Stock footage is real footage used unaltered — that is not synthetic media,
and using it does not become synthetic because the narration next to it is.

ONE THING THAT IS NOT SETTLED, WRITTEN DOWN RATHER THAN QUIETLY ASSUMED
----------------------------------------------------------------------
Channels 2-5 generate their THUMBNAIL backgrounds with an AI image model,
and some of those prompts ask for photoreal results (collapse_index asks for
"cinematic documentary"). This field, and Studio's question, are about the
VIDEO — all three bullets describe footage and scenes, not the thumbnail. So
this does not change the answer here. It is flagged because it is the nearest
thing to a grey area in this decision, and because a future change to how
thumbnails are made should get a fresh look rather than inherit this one.

THE TRIP-WIRES
--------------
Set the env var to true for a channel the moment ANY of these becomes true of
it, because then the content really is what the policy is aimed at:

    * a photoreal AI-generated image or video of a person, place or event is
      used in the VIDEO as anything other than an obvious illustration
    * a real person's voice or likeness is synthesised
    * footage of a real event is altered
    * a scene is generated that a viewer could take for documentary footage

Consistently failing to disclose when disclosure IS required risks content
removal and YPP suspension. This is a judgement to revisit whenever the
visual system changes — not a setting to forget.

USAGE
-----
    from synthetic_media_policy import declare_synthetic_media
    DECLARE_SYNTHETIC_MEDIA = declare_synthetic_media("evidence_room")

Turn it back on without touching code by setting either the channel-specific
or the global env var:

    DECLARE_SYNTHETIC_MEDIA_EVIDENCE_ROOM=true
    DECLARE_SYNTHETIC_MEDIA=true          # applies to every channel
"""
import os

_TRUE = ("1", "true", "yes", "on")


def declare_synthetic_media(channel: str) -> bool:
    """False unless this channel (or every channel) has been switched back on.

    Checks the channel-specific var first so one channel can start declaring
    without dragging the other four with it — the trip-wires above fire per
    channel, since the five formats differ in what they render.
    """
    specific = os.environ.get(
        f"DECLARE_SYNTHETIC_MEDIA_{channel.upper()}", "")
    if specific.strip().lower() in _TRUE:
        return True
    return os.environ.get(
        "DECLARE_SYNTHETIC_MEDIA", "false").strip().lower() in _TRUE
