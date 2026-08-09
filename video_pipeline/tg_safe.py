"""Telegram sending that cannot corrupt or silently drop a link.

WHY THIS EXISTS
---------------
Direct report: the Short links "don't open at all".

Every Telegram sender in this repo posted with parse_mode "Markdown", and
YouTube video ids are base64url -- eleven characters drawn from an alphabet
that includes the underscore. In legacy Markdown an underscore opens italic.
So of the four Shorts that went live on run 31257986626:

    zNvuOykr_vk   1 underscore   Telegram rejects the whole message, 400
    nsx-3TKavBc   0              fine
    DnHi98fcoYg   0              fine
    Jz-Pm_qrbGQ   1 underscore   Telegram rejects the whole message, 400

Two of four. And the failure was invisible from this side: requests.post
does not raise on a 400, so the sender returned normally, logged nothing,
and the message simply never arrived.

The second failure mode is worse because it looks like success. An id with
TWO underscores parses cleanly -- Telegram accepts the message, treats the
middle as italic, and CONSUMES both underscores. The link is delivered
looking almost right and pointing at a video id that does not exist. That
is a link that does not open, with a 200 OK behind it.

An LLM-written title in the same message can do the same thing with a stray
* or _ or [.

WHAT THIS DOES
--------------
Formatting is worth having, but never at the cost of the link. So:

  1. If Markdown would damage the message, it is sent as plain text.
     Telegram clients auto-linkify bare URLs, so a plain-text send loses
     the bold header and keeps the thing the message exists to deliver.
  2. If Telegram rejects it anyway, it is resent as plain text.
  3. The result is reported back, so a caller can log a real failure
     instead of assuming delivery.
"""

import re

import requests

_URL = re.compile(r"https?://\S+")
# The characters legacy Markdown treats as markup.
_MARKUP = "_*`["


def markdown_would_break(msg: str) -> bool:
    """True when Markdown parsing would reject or silently damage `msg`."""
    text = msg or ""

    # A URL carrying any markup character is the dangerous case: either the
    # message is rejected outright, or the character is eaten and the link
    # quietly becomes a different link.
    for url in _URL.findall(text):
        if any(c in url for c in _MARKUP):
            return True

    # An unpaired _ or * anywhere is a 400 for the whole message.
    for c in "_*`":
        if text.count(c) % 2:
            return True
    return False


def send(token: str, chat: str, msg: str, prefer_markdown: bool = True) -> bool:
    """Deliver `msg`. Returns True only when Telegram confirms it.

    Falls back to plain text rather than letting a message go missing.
    """
    if not token or not chat:
        return False

    modes = []
    if prefer_markdown and not markdown_would_break(msg):
        modes.append("Markdown")
    modes.append(None)  # plain text: no parse mode, nothing to misparse

    for mode in modes:
        payload = {"chat_id": chat, "text": msg}
        if mode:
            payload["parse_mode"] = mode
        try:
            r = requests.post(
                "https://api.telegram.org/bot%s/sendMessage" % token,
                json=payload, timeout=15)
        except Exception:
            continue
        # A 400 is not an exception. It has to be read off the response, or
        # the message is lost in exactly the silence that hid this bug.
        try:
            if r.status_code == 200 and r.json().get("ok"):
                return True
        except Exception:
            pass
    return False
