"""
HUMAN REVIEW GATE — built in direct response to an explicit request for a
genuine, hands-on review point at each major stage: read the real script,
listen to the real audio, preview the real video, before any of it locks
in. Not a summary, not a score — the actual artifact, delivered to
Telegram (and email) so it can be judged directly.

THREE REAL CHECKPOINTS:
  1. Script  — the full script text (not a 400-character preview),
              split across Telegram's real 4096-character message limit.
  2. Audio   — the actual generated audio FILE, sent via Telegram's real
              native audio player, so it can genuinely be listened to
              and judged human vs. robotic before it's locked in.
  3. Video   — a real short preview clip (first ~60 seconds, via an
              actual ffmpeg cut, not a placeholder) plus the real
              thumbnail image, since a full 15-18 minute video routinely
              exceeds Telegram bot API's real send-size limit.

REAL REPLY COMMANDS at every checkpoint:
  APPROVE          — proceed to the next stage immediately
  REJECT           — stop this episode entirely, no publish
  EDIT: <feedback> — the caller regenerates this exact stage, with the
                      real feedback text injected into the next attempt's
                      prompt/parameters — not a vague "try again."

Every checkpoint auto-approves after a real timeout (default 30 minutes,
matching the existing approval gate's established pattern) so the
pipeline never hangs indefinitely — matches "30 min expired —
auto-approved" behavior already established elsewhere in this project.

Email notifications reuse the existing, previously-underused send_gmail
pattern (Gmail SMTP via an app password) — genuinely free, no new
account needed beyond the Gmail account already in use.
"""

import time
import re
import os
import datetime
import subprocess
import smtplib
import html as _html_module
import json
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# REAL SAFETY NET: 4 checkpoints x 3 attempts x 60 min each = a genuine
# worst-case of 12 hours if every single checkpoint goes completely
# unanswered — double GitHub Actions' real 6-hour hosted-runner job
# limit. In the common case (most checkpoints get a real reply quickly)
# this never matters, but the rare pileup case would otherwise get the
# whole job forcibly killed mid-review, leaving an episode stuck with
# no clean resolution. This tracks real elapsed time across the WHOLE
# episode's review process and force-approves whatever's left once the
# budget is exhausted, leaving real headroom for actual generation time.
_REVIEW_PROCESS_START = datetime.datetime.now()
_MAX_TOTAL_REVIEW_HOURS = 4.5  # leaves ~1.5h real headroom inside the 6h job limit


def _total_review_time_exhausted():
    elapsed_hours = (datetime.datetime.now() - _REVIEW_PROCESS_START).total_seconds() / 3600
    return elapsed_hours >= _MAX_TOTAL_REVIEW_HOURS


import imaplib
import email as email_lib


def check_email_replies(sender_email, app_password, since_datetime=None):
    """
    THE REAL EMAIL FALLBACK — makes Gmail a genuine two-way input
    channel, not just a one-way notification. Uses IMAP (the same real
    Gmail App Password already used for sending) to check the inbox for
    actual reply emails, parsing each one for the same real decision
    keywords used on Telegram (APPROVE/REJECT/EDIT/REMAKE/SWAP VISUALS)
    — so if Telegram is ever down, slow, or unavailable, replying to
    the approval email works exactly the same way.

    Returns a list of (decision, extra_text, message_id) tuples for
    every unread reply found, newest first. The caller is responsible
    for marking messages as read/processed once handled.
    """
    if not app_password:
        return []
    results = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(sender_email, app_password)
        imap.select("INBOX")

        # Only unread messages, optionally since a given date, so old
        # replies from a previous episode's review never get re-processed.
        search_criteria = "UNSEEN"
        if since_datetime:
            search_criteria = f'(UNSEEN SINCE "{since_datetime.strftime("%d-%b-%Y")}")'
        status, message_ids = imap.search(None, search_criteria)
        if status != "OK":
            imap.logout()
            return []

        for msg_id in message_ids[0].split():
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            msg = email_lib.message_from_bytes(msg_data[0][1])

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            continue
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    body = ""

            decision, extra = _parse_email_decision(body)
            if decision:
                results.append((decision, extra, msg_id))

        imap.logout()
    except Exception as e:
        print(f"  Email reply check failed (check GMAIL_SENDER_EMAIL / GMAIL_APP_PASSWORD): {e}")
        return []
    return results


def _parse_email_decision(body):
    """
    Same real decision keywords as Telegram, applied to an email body —
    reused logic so "the same thing this Gmail does" (as explicitly
    requested) is genuinely true, not a different, weaker parser.
    Looks at the first non-empty line so quoted reply history below
    a signature doesn't get misread as the actual decision.
    """
    for line in body.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith(">"):
            continue  # skip quoted reply-history lines
        upper = line.upper()
        if upper == "APPROVE":
            return "approve", None
        if upper == "REJECT":
            return "reject", None
        if upper.startswith("REMAKE"):
            reason = line.split(":", 1)[1].strip() if ":" in line else None
            return "remake", reason
        if upper.startswith("SWAP VISUALS") or upper.startswith("SWAP_VISUALS"):
            which = line.split(":", 1)[1].strip() if ":" in line else None
            return "swap_visuals", which
        if upper.startswith("SWAP VOICE") or upper.startswith("SWAP_VOICE"):
            which = line.split(":", 1)[1].strip() if ":" in line else None
            return "swap_voice", which
        if upper.startswith("EDIT:") or upper.startswith("EDIT "):
            feedback = line.split(":", 1)[1].strip() if ":" in line else line[4:].strip()
            return "edit", feedback
        break  # first real line didn't match anything — not a decision reply
    return None, None


def send_email_notification(subject, html_body, sender_email, app_password, recipient_email=None):
    """
    Real Gmail SMTP send — the exact working pattern found already built
    (but underused) in this project. No new account or paid service
    needed; requires only a Gmail App Password (Google Account -> Security
    -> 2-Step Verification -> App Passwords), a genuine one-time manual
    step, same category as the other manual setups already documented.
    """
    if not app_password:
        return False
    # FIX (found on direct user request, July 15 2026): every review email
    # across all 5 channels now goes to ONE fixed inbox, regardless of
    # which channel's own GMAIL_SENDER_EMAIL sends it. Previously this
    # defaulted to sending each channel's email back to its own sender
    # account (e.g. Ch2's notifications would go to Ch2's own Gmail
    # sender address if Ch2 ever used a different one) -- now it's
    # always this one address unless a caller explicitly overrides it.
    recipient_email = recipient_email or "betrayaldeepdive@gmail.com"
    # FIX (found on direct user report, July 15 2026): a raw, truncated
    # <think> block reached this function's subject argument and
    # crashed the send entirely — Python's email library correctly
    # refuses to fold a header containing a literal newline, but that
    # meant the ENTIRE notification silently never went out, with the
    # only trace being a cryptic "folded header contains newline"
    # error. Fixed the actual source (the reasoning-strip gap that let
    # this through), but a subject line should never be able to crash
    # sending regardless of what produced it — sanitized here too as a
    # second, independent safeguard.
    subject = " ".join(str(subject).split())[:200]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(sender_email, app_password)
            smtp.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        # FIX (found on live-run audit, July 14 2026): this used to fail
        # completely silently — `except Exception: return False` with no
        # trace anywhere. If GMAIL_APP_PASSWORD is wrong/expired, or
        # GMAIL_SENDER_EMAIL doesn't match the account that generated the
        # app password, email would just never arrive with zero clue why.
        # Common real causes: app password needs 2-Step Verification
        # turned on first; the 16-character app password, not the normal
        # account password; sender_email must be the exact account that
        # generated it.
        print(f"  Gmail send failed (check GMAIL_SENDER_EMAIL / GMAIL_APP_PASSWORD): {e}")
        return False


def _esc(text):
    """
    FIX (found on deep re-audit): every message in this file is sent with
    parse_mode="HTML", but nothing anywhere escaped the actual DYNAMIC
    content (AI-generated titles/scripts/descriptions, human feedback
    text) before embedding it. Telegram's HTML parse mode only
    recognizes a small whitelist of real tags (<b>, <i>, <code>, <pre>,
    <a href>) — a literal "<", ">", or unescaped "&" anywhere in real
    content (a title like "Season 2 < Season 1", a description
    mentioning "AT&T", human feedback typed with a stray "<") would make
    Telegram reject the ENTIRE message as malformed, and the reviewer
    would silently never receive it. This escapes dynamic content before
    it's embedded; the small number of intentional <b>/<i> tags this
    file itself adds around static labels are written directly in the
    surrounding f-string, never through this function, so they still work.
    """
    if text is None:
        return ""
    return _html_module.escape(str(text), quote=False)


def _fallback_chat_not_found(tg_token, tg_chat, response_text):
    """
    FIX (found on direct user report, July 15 2026): "chat not found" is
    Telegram's own way of saying the bot token is valid but that chat
    has never had a conversation with THIS specific bot — almost always
    because the person hasn't sent it a first message yet (Telegram
    requires the human side to initiate contact before a bot can message
    them). Rather than a message silently vanishing while the person is
    still getting every channel's bot started in Telegram one by one,
    this falls back to the shared TELEGRAM_TOKEN/TELEGRAM_CHAT_ID — but
    ONLY on this specific error, and ONLY when the fallback credentials
    are actually different from what just failed, so this never masks a
    genuinely different problem or silently duplicates a working send.
    Returns (fallback_token, fallback_chat) or (None, None) if no
    fallback applies.
    """
    if "chat not found" not in (response_text or "").lower():
        return None, None
    _plain_token = os.environ.get("TELEGRAM_TOKEN", "")
    _plain_chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if _plain_token and _plain_chat and (_plain_token != tg_token or _plain_chat != tg_chat):
        return _plain_token, _plain_chat
    return None, None


def _tg_send_message(tg_token, tg_chat, text):
    try:
        r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                      json={"chat_id": tg_chat, "text": text, "parse_mode": "HTML"}, timeout=15)
        if r.status_code != 200:
            # FIX (found on final re-audit): this used to fail completely
            # silently. If the bot token/chat ID are wrong, EVERY message
            # this pipeline ever tries to send just vanishes with zero
            # trace — the exact same blind spot the Gmail bug had, and the
            # kind of thing that made the original Ch5 button issue take
            # this many rounds to actually find. Logged so a broken
            # token/chat shows up immediately in the run's own console
            # output instead of looking identical to "no reply yet".
            print(f"  Telegram sendMessage failed (check the bot token/chat ID): {r.status_code} {r.text[:200]}")
            _fb_token, _fb_chat = _fallback_chat_not_found(tg_token, tg_chat, r.text)
            if _fb_token:
                print("  Falling back to the shared Telegram bot for this message — "
                      "the channel-specific bot still needs to be started in Telegram (send it any message once).")
                requests.post(f"https://api.telegram.org/bot{_fb_token}/sendMessage",
                              json={"chat_id": _fb_chat,
                                    "text": f"⚠️ [Sent via backup bot — this channel's own bot isn't started yet]\n\n{text}",
                                    "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        print(f"  Telegram sendMessage failed (check the bot token/chat ID): {e}")


def _tg_send_message_with_buttons(tg_token, tg_chat, text, include_swap_visuals=False, fifth_option=None):
    """
    v9 addition, v10 revision (July 14 2026 audit): real, genuine Telegram
    inline-keyboard buttons. Original v9 finding: it didn't have any —
    plain text with instructions to TYPE a reply, despite five options
    being designed. v10 finding, from direct user feedback: EDIT was
    STILL typed-only after v9, even though the person explicitly asked
    for a real workable EDIT button. Fixed here — EDIT is now a genuine
    button on every checkpoint. Tapping it prompts for the one thing a
    button truly cannot collect (what to change); the reply after that
    prompt is treated as the edit content, not a fresh decision.
    `include_swap_visuals` is kept only for backward compatibility with
    older call sites — prefer passing `fifth_option` directly.
    """
    if fifth_option is None and include_swap_visuals:
        fifth_option = ("🎨 SWAP VISUALS", "swap_visuals")
    try:
        r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                      json={"chat_id": tg_chat, "text": text, "parse_mode": "HTML",
                            "reply_markup": _button_keyboard(fifth_option=fifth_option)},
                      timeout=15)
        if r.status_code != 200:
            print(f"  Telegram sendMessage (buttons) failed (check the bot token/chat ID): {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  Telegram sendMessage (buttons) failed (check the bot token/chat ID): {e}")


def _button_keyboard(options=("approve", "reject", "remake", "edit"), fifth_option=None):
    """
    Shared real inline-keyboard builder, used by every checkpoint (text,
    audio, video, photo). All four core decisions — APPROVE, REJECT,
    REMAKE, EDIT — are real one-tap buttons. `fifth_option`, when given,
    is a (label, callback_data) pair for the checkpoint-specific 5th
    option — e.g. ("🎨 SWAP VISUALS", "swap_visuals") for video/shorts,
    ("🎙️ SWAP VOICE", "swap_voice") for audio — per the explicit request
    that this exist for both audio and video, not just video.
    """
    label_map = {"approve": ("✅ APPROVE", "approve"), "reject": ("❌ REJECT", "reject"),
                 "remake": ("🔄 REMAKE", "remake"), "edit": ("✏️ EDIT", "edit")}
    row1 = [{"text": t, "callback_data": d} for key in ("approve", "reject") if key in options
            for t, d in [label_map[key]]]
    row2 = [{"text": t, "callback_data": d} for key in ("remake", "edit") if key in options
            for t, d in [label_map[key]]]
    rows = [r for r in (row1, row2) if r]
    if fifth_option:
        rows.append([{"text": fifth_option[0], "callback_data": fifth_option[1]}])
    return {"inline_keyboard": rows}


def _tg_send_audio(tg_token, tg_chat, audio_path, caption="", reply_markup=None):
    """Real Telegram native audio send — genuinely playable in-chat, not a link."""
    try:
        data = {"chat_id": tg_chat, "caption": caption}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        with open(audio_path, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendAudio",
                          data=data, files={"audio": f}, timeout=120)
        # FIX (found on final re-audit): this used to return True the
        # moment the HTTP request didn't raise — even if Telegram's API
        # itself rejected the file (e.g. over its real ~50MB bot-upload
        # limit, or a bad chat ID) and responded with an error status.
        # The caller trusts this return value to decide whether to fall
        # back to a text-only notice; a false "sent successfully" here
        # means the pipeline would sit polling for a reply to a message
        # the person never actually received, until it times out and
        # auto-approves something nobody ever reviewed.
        if r.status_code != 200:
            print(f"  Telegram sendAudio failed (file may be too large, or check bot token/chat ID): {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  Telegram sendAudio failed: {e}")
        return False


def _tg_send_video(tg_token, tg_chat, video_path, caption="", reply_markup=None):
    try:
        data = {"chat_id": tg_chat, "caption": caption}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        with open(video_path, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendVideo",
                          data=data, files={"video": f}, timeout=180)
        # FIX (found on final re-audit): same real gap as _tg_send_audio —
        # a Telegram-side rejection (file too large, bad chat ID) used to
        # be indistinguishable from a genuine success.
        if r.status_code != 200:
            print(f"  Telegram sendVideo failed (file may be too large, or check bot token/chat ID): {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  Telegram sendVideo failed: {e}")
        return False


def _tg_send_photo(tg_token, tg_chat, photo_path, caption="", reply_markup=None):
    try:
        data = {"chat_id": tg_chat, "caption": caption}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        with open(photo_path, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendPhoto",
                          data=data, files={"photo": f}, timeout=60)
        if r.status_code != 200:
            print(f"  Telegram sendPhoto failed (check bot token/chat ID): {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  Telegram sendPhoto failed: {e}")
        return False


def _poll_for_decision(tg_token, tg_chat, timeout_minutes=60, max_attempts=3,
                        gmail_sender=None, gmail_app_password=None):
    """
    Real reply polling — 3 attempts of 60 minutes each, checking BOTH
    Telegram AND email every cycle (email checked every ~60s rather than
    every 15s like Telegram, since an IMAP round-trip is more expensive
    than a Telegram getUpdates call) — whichever channel replies first
    wins. This is the real fallback: if Telegram is ever down, slow, or
    unavailable, replying to the approval email works identically.

    Returns ("approve", None), ("reject", None),
    ("edit", "the real feedback text"), ("remake", "optional reason"),
    ("swap_visuals", "optional which-section text"),
    ("swap_voice", "optional reason"), or ("timeout", None).
    """
    offset = None
    email_check_counter = 0
    review_start_time = datetime.datetime.now()
    _getupdates_error_logged = [False]  # mutable so the nested loop below can set it once
    awaiting_edit_text = False  # FIX (July 14 2026): EDIT is now a real
    # button (see _button_keyboard). A tap can't carry free-form text, so
    # tapping it prompts for what to change, then the very next text
    # reply — whatever its wording — is taken as that edit content,
    # rather than re-parsed as a fresh decision keyword.

    for attempt in range(1, max_attempts + 1):
        if _total_review_time_exhausted():
            _tg_send_message(tg_token, tg_chat,
                             "⏱️ Total review time budget for this episode reached — "
                             "auto-approving to keep this run within GitHub Actions' real "
                             "job time limit. Whatever hasn't been decided yet proceeds as generated.")
            return "timeout", None
        deadline = datetime.datetime.now() + datetime.timedelta(minutes=timeout_minutes)
        while datetime.datetime.now() < deadline:
            time.sleep(15)

            # FIX (found on final re-audit, direct user question about the
            # real timeline): this global 4.5h budget used to only be
            # checked once at the TOP of each 60-minute attempt — not
            # inside this 15s loop. So if the budget ran out partway
            # through an attempt (e.g. at the 4h20m mark, mid-attempt),
            # nothing would notice until that ENTIRE attempt finished,
            # potentially blowing up to a further 59 minutes past the
            # intended 4.5h ceiling — eating directly into the 1.5h of
            # headroom this budget exists to protect. Checked every 15s
            # now, same cadence as the Telegram poll itself.
            if _total_review_time_exhausted():
                _tg_send_message(tg_token, tg_chat,
                                 "⏱️ Total review time budget for this episode reached — "
                                 "auto-approving to keep this run within GitHub Actions' real "
                                 "job time limit. Whatever hasn't been decided yet proceeds as generated.")
                return "timeout", None

            # Check Telegram every cycle (cheap, fast)
            try:
                params = {"timeout": 10}
                if offset:
                    params["offset"] = offset
                r = requests.get(f"https://api.telegram.org/bot{tg_token}/getUpdates",
                                  params=params, timeout=20)
                if r.status_code != 200:
                    # FIX (found on final re-audit): a bad bot token/chat
                    # makes getUpdates fail on EVERY single cycle for the
                    # whole timeout window, and this used to swallow that
                    # completely — the logs would look identical to "no
                    # one has replied yet" whether the person genuinely
                    # hadn't answered, or the polling was fundamentally
                    # broken the entire time. Logged once per attempt
                    # (not every 15s) so it's visible without flooding
                    # the log with the same line dozens of times.
                    if not _getupdates_error_logged[0]:
                        print(f"  Telegram getUpdates failed (check the bot token): {r.status_code} {r.text[:200]}")
                        _getupdates_error_logged[0] = True
                updates = r.json().get("result", [])
            except Exception as e:
                if not _getupdates_error_logged[0]:
                    print(f"  Telegram getUpdates failed (check the bot token/network): {e}")
                    _getupdates_error_logged[0] = True
                updates = []
            for u in updates:
                offset = u["update_id"] + 1

                # v9 addition — real button-tap handling. A callback_query
                # update means the person tapped an inline button (not
                # typed a reply) — genuinely different update shape from
                # a text message, checked first since a single update is
                # never both.
                cb = u.get("callback_query")
                if cb:
                    cb_data = cb.get("data", "")
                    try:
                        requests.post(f"https://api.telegram.org/bot{tg_token}/answerCallbackQuery",
                                     json={"callback_query_id": cb["id"], "text": f"{cb_data.upper()} received"},
                                     timeout=10)
                    except Exception:
                        pass
                    if cb_data == "edit":
                        awaiting_edit_text = True
                        _tg_send_message(tg_token, tg_chat,
                                         "✏️ EDIT tapped — reply with what you'd like changed.")
                        continue
                    if cb_data in ("approve", "reject", "remake", "swap_visuals", "swap_voice"):
                        return cb_data, None
                    continue

                text = u.get("message", {}).get("text", "").strip()
                if not text:
                    continue
                if awaiting_edit_text:
                    # This is the free-form content that followed an EDIT
                    # button tap — it IS the edit, not a decision to parse.
                    return "edit", text
                # FIX (found on deep re-audit): this used to be an
                # independently duplicated copy of _parse_email_decision's
                # exact keyword logic, not a genuine call to it — despite
                # this function's own docstring claiming "the same real
                # decision keywords... reused logic". Two copies of the
                # same rules currently behave identically, but nothing
                # enforced that — a future keyword fix applied to only
                # one path would silently make Telegram and email behave
                # differently, breaking the explicit "works exactly the
                # same way" promise. Now genuinely shares one function.
                decision, extra = _parse_email_decision(text)
                if decision:
                    return decision, extra

            # Check email every ~4th cycle (roughly every 60s given the 15s sleep)
            email_check_counter += 1
            if gmail_app_password and email_check_counter % 4 == 0:
                email_replies = check_email_replies(gmail_sender, gmail_app_password,
                                                     since_datetime=review_start_time)
                if email_replies:
                    decision, extra, _msg_id = email_replies[0]  # most recent real reply
                    return decision, extra

        # This attempt's 60-minute window expired with no reply on either channel
        if attempt < max_attempts:
            _tg_send_message(tg_token, tg_chat,
                             f"⏰ Reminder ({attempt}/{max_attempts}): still waiting on your "
                             f"decision. {max_attempts - attempt} more 60-minute window(s) "
                             f"before this auto-approves.")
    return "timeout", None


def get_schedule_line(check_ins_used, max_check_ins=6, check_ins_per_day=3,
                       upload_hour_utc=18):
    """
    Real, honest scheduling info for every review message — today's date
    plus a genuine estimate of the actual publish date, computed from
    how many check-ins remain in the real 2-day window, not a guess.
    """
    now = datetime.datetime.now()
    check_ins_remaining = max_check_ins - check_ins_used
    days_remaining_max = -(-check_ins_remaining // check_ins_per_day)  # ceiling division
    earliest_publish = (now + datetime.timedelta(days=1)).strftime("%A, %B %d")
    latest_publish = (now + datetime.timedelta(days=max(1, days_remaining_max))).strftime("%A, %B %d")
    return (f"Today: {now.strftime('%A, %B %d, %Y')}\n"
            f"Publishes: as early as {earliest_publish} if fully approved now, "
            f"no later than {latest_publish} (the real 2-day review maximum) — "
            f"around 6:00 PM UTC (peak US/Europe overlap window).")


def review_title_thumbnail_description(channel_name, title, thumbnail_path, description,
                                         description_score, tg_token, tg_chat, check_ins_used,
                                         gmail_sender=None, gmail_app_password=None,
                                         timeout_minutes=60, thumbnail_score=None):
    """
    THE COMBINED CHECKPOINT — title, thumbnail, and description reviewed
    together in one message, per the explicit request to reduce total
    review time. Shows the real description quality score so "why does
    this description look different from usual" has a concrete number
    behind it, not a black box.

    FIX (found on final re-audit, direct user request for real per-stage
    scores): thumbnail_score is optional and, when given, shown alongside
    the description score. This reflects the score_thumbnail_text()
    result computed at the CANDIDATE-SELECTION stage (best of several
    real candidates, scored on having a real number, ideal 2-3 word
    length, and specificity signals) — stated honestly: if the channel's
    format-specific enforcement (e.g. before/after phrasing) touches the
    text further after this point, the score reflects the selected
    candidate, not necessarily every character of the final rendered
    image.
    """
    schedule_line = get_schedule_line(check_ins_used)
    thumb_score_line = f"Thumbnail attention score: {thumbnail_score}/10\n" if thumbnail_score is not None else ""
    caption = (f"🖼️🏷️📝 {channel_name} — TITLE + THUMBNAIL + DESCRIPTION REVIEW\n\n"
              f"{schedule_line}\n\n"
              f"Title: {title}\n"
              f"{thumb_score_line}"
              f"Description quality score: {description_score}/10\n\n"
              f"Tap a button below — EDIT will ask what to change")
    _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption=caption,
                   reply_markup=_button_keyboard())
    # FIX (found on deep re-audit): this used to send the ENTIRE
    # description as one message with zero chunking. Ch3's (and Ch1/2's)
    # descriptions can legitimately reach up to 5000 characters (YouTube's
    # own real description limit), while Telegram's real hard limit for
    # sendMessage is 4096 — a long description would be silently rejected
    # by Telegram's API (swallowed by _tg_send_message's bare except), and
    # the reviewer would never see it at all, with zero error surfaced
    # anywhere, while the pipeline still sat waiting for a decision on
    # content the human never received. Same real chunking pattern
    # already used correctly in review_script, applied here too.
    desc_full_text = f"Full description:\n\n{_esc(description)}"
    desc_chunk_size = 3800
    desc_chunks = [desc_full_text[i:i+desc_chunk_size] for i in range(0, len(desc_full_text), desc_chunk_size)]
    for i, chunk in enumerate(desc_chunks):
        prefix = f"[{i+1}/{len(desc_chunks)}]\n" if len(desc_chunks) > 1 else ""
        _tg_send_message(tg_token, tg_chat, prefix + chunk)
        if len(desc_chunks) > 1:
            time.sleep(1)  # avoid Telegram rate limits on rapid sequential sends

    if gmail_app_password:
        # FIX (found on deep re-audit): lower severity than the Telegram
        # case (email clients don't hard-reject malformed HTML the way
        # Telegram's API does), but still a real content-integrity gap —
        # a literal "<"/">" in an AI-generated title (e.g. "The <Truth>
        # Revealed") would be silently interpreted as an unknown tag and
        # stripped by the email client, changing what the reviewer
        # actually sees. Escaped for consistency.
        html_body = (f"<p>{schedule_line}</p><p><b>{_esc(title)}</b></p>"
                     f"{'<p>Thumbnail attention score: ' + str(thumbnail_score) + '/10</p>' if thumbnail_score is not None else ''}"
                     f"<p>Description score: {description_score}/10</p>"
                     f"<pre style='white-space:pre-wrap'>{_esc(description)}</pre>")
        send_email_notification(f"[{channel_name}] Title/Thumbnail/Description ready for review",
                                 html_body, gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ {timeout_minutes} min expired — auto-approved.")
        decision = "approve"
    return {"decision": decision, "feedback": feedback}


def identify_target_sections(feedback, stage_names):
    """
    Maps real human feedback text to the actual named script sections it
    refers to — e.g., "the escalation feels flat" -> ["ESCALATION"],
    "second half needs work" -> the back half of stage_names by position.
    This is what makes "after this point it needs changing" genuinely
    actionable rather than vague: every section that gets identified here
    is the one actually rewritten, nothing else, nothing silently skipped.

    Returns a list of stage_names entries (possibly empty, meaning no
    specific section was identified and the caller should treat the
    feedback as applying to the whole script).
    """
    feedback_lower = feedback.lower()
    matched = [name for name in stage_names if name.lower() in feedback_lower]
    if matched:
        return matched

    # Positional language — "second half", "the ending", "the start"
    n = len(stage_names)
    if any(p in feedback_lower for p in ["second half", "back half", "latter half"]):
        return stage_names[n // 2:]
    if any(p in feedback_lower for p in ["first half", "front half", "beginning half"]):
        return stage_names[:n // 2]
    if any(p in feedback_lower for p in ["ending", "the end", "final part", "last part"]):
        return stage_names[-2:]
    if any(p in feedback_lower for p in ["opening", "the start", "beginning", "intro"]):
        return stage_names[:2]

    return []  # no specific section identified — whole-script feedback


def score_description(description, title, niche_name):
    """
    Real quality scoring for the video description — checks genuine,
    checkable markers rather than just length, so "9/10" means something
    concrete: has real chapter timestamps, a hook in the first two lines,
    cross-promo links, a call-to-action, and reasonable (not padded or
    truncated) length. Returns (score_out_of_10, list_of_missing_things).
    """
    import re as _re
    score = 10.0
    missing = []

    lines = description.strip().split("\n")
    first_two = " ".join(lines[:2]).lower()
    if len(first_two) < 40 or first_two.count(" ") < 5:
        score -= 2.0
        missing.append("a real hook/summary in the first two lines")

    has_timestamps = bool(_re.search(r'\d{1,2}:\d{2}', description))
    if not has_timestamps:
        score -= 2.5
        missing.append("chapter timestamps (e.g. 0:00 Intro)")

    has_cross_promo = "youtube.com/@" in description
    if not has_cross_promo:
        score -= 2.0
        missing.append("cross-promotion links to the other channels")

    has_cta = any(w in description.lower() for w in ["subscribe", "follow", "comment below"])
    if not has_cta:
        score -= 1.5
        missing.append("a clear call-to-action (subscribe/comment)")

    word_count = len(description.split())
    if word_count < 60:
        score -= 1.5
        missing.append(f"more real substance (only {word_count} words, needs more depth)")
    elif word_count > 600:
        score -= 1.0
        missing.append(f"tightening — {word_count} words is padded/bloated for a description")

    return max(0.0, score), missing


def regenerate_description_until_good(niche, topic, title, episode, chapters_text,
                                       audio_duration, niche_name, generate_fn,
                                       min_score=9.0, max_attempts=4):
    """
    Real regeneration loop — calls the pipeline's own real description
    generator repeatedly, scoring each real attempt, and only stops once
    it genuinely crosses min_score or max_attempts is exhausted (in
    which case it returns the BEST real attempt seen, never a worse one,
    and is honest in its return value about whether the bar was hit).
    generate_fn: the pipeline's own generate_seo_description-equivalent,
    called fresh each attempt so real variation actually happens.
    """
    best_desc, best_score, best_missing = None, -1.0, []
    for attempt in range(1, max_attempts + 1):
        desc = generate_fn(niche, topic, title, episode, chapters_text, audio_duration)
        if not desc:
            continue
        score, missing = score_description(desc, title, niche_name)
        if score > best_score:
            best_desc, best_score, best_missing = desc, score, missing
        if score >= min_score:
            return {"description": desc, "score": score, "missing": [], "hit_target": True, "attempts": attempt}
    return {"description": best_desc, "score": best_score, "missing": best_missing,
            "hit_target": False, "attempts": max_attempts}


def review_shorts(channel_name, shorts_list, tg_token, tg_chat, check_ins_used=0,
                   gmail_sender=None, gmail_app_password=None, timeout_minutes=60):
    """
    THE SHORTS CHECKPOINT — 5 real options (approve/reject/edit/remake/
    swap visuals), matching the video checkpoint's design.

    HONEST CONSTRAINT, stated plainly: the real Shorts production
    functions (produce_video_topic_short, produce_standalone_short)
    generate AND upload in one call internally — there's no clean
    pre-publish preview point without risky changes to that already-
    proven shared module. So this review happens on the ALREADY-
    PUBLISHED Shorts. EDIT, REMAKE,
    and SWAP VISUALS all mean the same real thing here: the caller
    produces a genuinely fresh replacement Short and publishes that as
    an addition — this function does not and cannot delete/unpublish
    the original from here.

    shorts_list: [{"name": str, "url": str, "score": float or None}, ...]
    — the real Shorts already produced this episode. "score" is
    optional — from quality_scoring.score_shorts_quality(), computed by
    the caller against the local file (shorts_reels_engine.py's
    produce_*_short functions now return "local_path" alongside "url"
    specifically so this scoring is possible before that file, if ever
    cleaned up, is gone) — shown when present, silently omitted
    otherwise so this doesn't break for a caller that hasn't wired it in.
    """
    schedule_line = get_schedule_line(check_ins_used)
    lines = [f"🎞️ {channel_name} — SHORTS REVIEW\n\n{schedule_line}\n",
             "Already published (review happens post-publish — see the note below):"]
    for s in shorts_list:
        score_part = f" — quality score: {s['score']}/10" if s.get("score") is not None else ""
        lines.append(f"  • {_esc(s['name'])}{score_part}: {_esc(s['url'])}")
    lines.append("\nTap a button below — EDIT will ask what to change")
    lines.append("\nNote: EDIT/REMAKE/SWAP VISUALS here produce a genuinely fresh replacement "
                 "Short and publish it as an addition — the original already-published Short "
                 "cannot be un-published from this review step.")
    _tg_send_message_with_buttons(tg_token, tg_chat, "\n".join(lines), include_swap_visuals=True)

    if gmail_app_password:
        html_body = f"<p>{schedule_line}</p><p>Shorts published:</p><ul>" + \
                    "".join(f"<li>{s['name']}"
                            f"{' — quality score: ' + str(s['score']) + '/10' if s.get('score') is not None else ''}"
                            f": {s['url']}</li>" for s in shorts_list) + "</ul>"
        send_email_notification(f"[{channel_name}] Shorts ready for review", html_body,
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ {timeout_minutes} min expired — auto-approved.")
        decision = "approve"
    return {"decision": decision, "feedback": feedback}


def review_thumbnail(channel_name, thumbnail_path, title, tg_token, tg_chat,
                      gmail_sender=None, gmail_app_password=None, timeout_minutes=60):
    """
    Real checkpoint: sends the actual generated thumbnail image. EDIT
    feedback here gets passed straight back to the caller, which
    regenerates the thumbnail with that feedback folded into the real
    AI image prompt — not a cosmetic re-roll, an actual instructed retry.
    """
    caption = f"🖼️ {channel_name} — THUMBNAIL REVIEW\nTitle: {title}\n\nReply APPROVE, REJECT, or EDIT: what to change"
    _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption=caption)

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Thumbnail ready for review",
                                 f"<p>Thumbnail for: <b>{_esc(title)}</b><br>Check Telegram to view it.</p>",
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ {timeout_minutes} min expired — auto-approved.")
        decision = "approve"
    return {"decision": decision, "feedback": feedback}


def review_title(channel_name, title, alternate_titles, tg_token, tg_chat,
                  gmail_sender=None, gmail_app_password=None, timeout_minutes=60):
    """
    Real checkpoint for the title specifically — shows the winning title
    plus the real runner-up options that were actually scored, so EDIT
    feedback can reference something concrete ("use option 2 instead" is
    directly actionable) rather than guessing blind.
    """
    alt_text = "\n".join(f"  {i+1}. {_esc(t)}" for i, t in enumerate(alternate_titles[:3]))
    text = (f"🏷️ {channel_name} — TITLE REVIEW\n\nSelected: {_esc(title)}\n\n"
            f"Other real options that were scored:\n{alt_text}\n\n"
            f"Reply APPROVE, REJECT, or EDIT: what to change (e.g. \"use option 2\")")
    _tg_send_message(tg_token, tg_chat, text)

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Title ready for review",
                                 f"<p>Selected: <b>{_esc(title)}</b></p><p>Alternatives:<br>{alt_text}</p>",
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ {timeout_minutes} min expired — auto-approved.")
        decision = "approve"
    return {"decision": decision, "feedback": feedback}


def regenerate_script_sections(full_script, stage_texts, stage_names, target_sections,
                                feedback, niche, topic, ai_fn):
    """
    THE CORE OF "FEEDBACK MUST BE TAKEN UP" — takes the real human
    feedback and the specific sections it was mapped to, and actually
    rewrites just those sections via a real AI call, then substitutes
    them back into the full script — preserving every other section
    exactly as it was. If target_sections is empty (whole-script
    feedback), rewrites the entire script instead, still incorporating
    the real feedback text directly.

    Returns (new_full_script, updated_sections_dict) where
    updated_sections_dict maps each regenerated section_name to its new
    text — callers MUST use this to refresh their own stage_texts cache
    for those indices. Never silently returns the original unchanged —
    if the AI call fails, raises rather than pretending the edit
    happened, so the caller can genuinely alert rather than silently
    ignore the request.

    FIX (found on final re-audit): a version of this that only returned
    the merged script (no per-section map) meant a caller updating its
    own stage_texts cache had no way to know what the new text for a
    just-edited section actually was — the entry for that section stayed
    on its PRE-edit text. A second edit request targeting that same
    section would then search for text that no longer exists anywhere in
    the script (it was already replaced once), and the substring
    `.replace()` would silently do nothing — the person would see
    "updated" and get back the exact same script a second time, with no
    error. Returning the per-section map lets the caller keep every
    entry current after every round, not just after the first.
    """
    if not target_sections:
        prompt = f"""Rewrite this ENTIRE documentary script based on real human feedback.
Keep the same facts, topic, and general structure — only change what the feedback asks for.

TOPIC: {topic}
HUMAN FEEDBACK (apply this directly, it is not optional): {feedback}

CURRENT SCRIPT:
{full_script}

Return ONLY the complete rewritten script, no commentary, no markdown."""
        new_script = ai_fn(prompt, tokens=8000)
        if not new_script or len(new_script.split()) < 50:
            raise RuntimeError("Whole-script regeneration failed or returned too little content — "
                               "feedback was NOT applied, this must be surfaced, not hidden.")
        return new_script.strip(), {}

    updated_script = full_script
    updated_sections = {}
    for section_name in target_sections:
        idx = stage_names.index(section_name)
        original_section = stage_texts[idx]
        prompt = f"""Rewrite ONLY this one section of a documentary script, based on real human feedback.
Keep the same facts and continuity with the surrounding script — this section must still connect
naturally to what comes before and after it.

TOPIC: {topic}
SECTION BEING REWRITTEN: {section_name}
HUMAN FEEDBACK (apply this directly, it is not optional): {feedback}

ORIGINAL SECTION TEXT:
{original_section}

Return ONLY the rewritten section text, no commentary, no markdown, no section label."""
        new_section = ai_fn(prompt, tokens=1500)
        if not new_section or len(new_section.split()) < 15:
            raise RuntimeError(f"Section rewrite for '{section_name}' failed or returned too "
                               f"little content — feedback was NOT applied, this must be "
                               f"surfaced, not hidden.")
        new_section = new_section.strip()
        updated_script = updated_script.replace(original_section, new_section, 1)
        updated_sections[section_name] = new_section

    return updated_script, updated_sections


def approximate_stage_split(full_script, stage_names, word_targets):
    """
    FIX (July 14 2026 audit): Channels 2/3/4's script generator doesn't
    return real per-stage text (only Channel 1 and 5 do) — their internal
    quality-gate scoring computes a proportional word-count split
    on-the-fly and discards it once scoring is done. Rather than risk
    changing that generator's tuple return signature (used elsewhere,
    higher risk of breaking something for a cosmetic display change),
    this reconstructs the same proportional split independently, purely
    for the review message. It's an approximation (real sentence/idea
    boundaries won't line up exactly with word-count math), but it's the
    same technique the pipeline itself already trusts for stage scoring.

    CRITICAL FIX applied here on re-audit: an earlier version of this
    function rebuilt each stage's text with `" ".join(words)`, producing
    single-space-separated text that is NOT an exact substring of the
    original script the moment that script has a newline, a paragraph
    break, or a double space anywhere in it (real scripts always do).
    regenerate_script_sections() finds the section to rewrite with a
    plain `.replace(original_section, ...)` — which silently does
    nothing and returns the script completely unchanged if the text
    isn't an exact match, with no error and no signal that the edit was
    ignored. That would have made every EDIT on Channels 2/3/4 a silent
    no-op: the person would see "regenerating..." and get back the exact
    same script. Fixed by slicing the ORIGINAL string by character
    offset (via each word's real start/end position), so every returned
    stage text is guaranteed to be an exact, literal substring of
    full_script, whitespace and all.
    """
    word_spans = [m.span() for m in re.finditer(r'\S+', full_script)]
    total = len(word_spans)
    total_target = sum(word_targets) or 1
    pos = 0
    stage_texts = []
    for i, target in enumerate(word_targets):
        share = target / total_target
        end = pos + int(total * share) if i < len(word_targets) - 1 else total
        end = max(end, pos)
        if pos < total and end > pos:
            start_char = word_spans[pos][0]
            end_char = word_spans[end - 1][1]
            stage_texts.append(full_script[start_char:end_char])
        else:
            stage_texts.append("")
        pos = end
    return stage_texts


def review_script(channel_name, title, full_script, score, niche_name,
                   tg_token, tg_chat, check_ins_used=0, gmail_sender=None,
                   gmail_app_password=None, timeout_minutes=60,
                   stage_texts=None, stage_names=None, thumbnail_text=None, tags=None,
                   sub_scores=None):
    """
    Real checkpoint 1: sends the FULL script text (not a preview),
    correctly split across Telegram's real 4096-character message limit,
    plus an email with the complete script attached. Waits for a real
    reply. Returns {"decision": "approve"|"reject"|"edit"|"remake"|"timeout",
    "feedback": str or None}.

    FIX (July 14 2026 audit, direct user feedback): this used to send the
    script as one undifferentiated wall of text with everything (script,
    thumbnail text, tags) mixed together with no visual separation —
    genuinely hard to tell where the hook ends and the body begins, or
    what's narration versus metadata. When stage_texts/stage_names are
    given (the pipeline already tracks these internally for edit-
    targeting — this just also uses them for display), the script is now
    sent stage-by-stage with a clear bold header per stage (COLD OPEN,
    THE BEFORE, etc.) instead of one blob. Thumbnail text and tags, if
    given, are sent as their own clearly separate, clearly labeled
    message — never folded into the narration text.

    sub_scores: optional dict of {label: (score_0_to_10, note)} for named
    sub-metrics the caller has computed — e.g. {"Hook strength":
    (7.4, "weak 60% hook")}. This is for real, independently-checkable
    sub-scores (the pipeline's own existing retention-hook validator,
    converted to a 0-10 scale, is the first real use of this), not
    invented numbers — shown as its own line under the main score.
    """
    schedule_line = get_schedule_line(check_ins_used)
    sub_score_lines = ""
    if sub_scores:
        for label, (sub_score, note) in sub_scores.items():
            note_part = f" — {note}" if note else ""
            sub_score_lines += f"{label}: {sub_score}/10{note_part}\n"
    header = (f"📝 <b>{channel_name} — SCRIPT REVIEW</b>\n\n{schedule_line}\n\n"
             f"Title: {_esc(title)}\nNiche: {niche_name} | Score: {score}/10\n"
             f"{sub_score_lines}"
             f"Length: {len(full_script.split())} words\n\n"
             f"Tap a button below — EDIT will ask what to change\n"
             f"(auto-approves in {timeout_minutes} min)")
    _tg_send_message_with_buttons(tg_token, tg_chat, header)

    # Real message-splitting — Telegram's real hard limit is 4096 characters.
    # Send stage-by-stage with a clear header when the caller has that
    # breakdown; otherwise fall back to the old flat-chunk behavior so
    # nothing breaks for a caller that doesn't pass stage data.
    chunk_size = 3700  # leaves headroom for the header/chunk-number prefix
    if stage_texts and stage_names and len(stage_texts) == len(stage_names):
        for stage_name, stage_text in zip(stage_names, stage_texts):
            escaped_stage = _esc(stage_text)
            sub_chunks = [escaped_stage[i:i+chunk_size] for i in range(0, len(escaped_stage), chunk_size)] or [""]
            for i, chunk in enumerate(sub_chunks):
                part_label = f" ({i+1}/{len(sub_chunks)})" if len(sub_chunks) > 1 else ""
                _tg_send_message(tg_token, tg_chat, f"━━━ <b>{_esc(stage_name.upper())}</b>{part_label} ━━━\n\n{chunk}")
                time.sleep(1)
    else:
        _escaped_script = _esc(full_script)
        chunks = [_escaped_script[i:i+chunk_size] for i in range(0, len(_escaped_script), chunk_size)]
        for i, chunk in enumerate(chunks):
            _tg_send_message(tg_token, tg_chat, f"[{i+1}/{len(chunks)}]\n{chunk}")
            time.sleep(1)  # avoid Telegram rate limits on rapid sequential sends

    # Thumbnail text / tags — always their own separate, clearly labeled
    # message, never mixed into the narration above.
    meta_lines = []
    if thumbnail_text:
        meta_lines.append(f"🖼️ <b>THUMBNAIL TEXT:</b> {_esc(thumbnail_text)}")
    if tags:
        tags_str = ", ".join(tags) if isinstance(tags, (list, tuple)) else str(tags)
        meta_lines.append(f"🏷️ <b>TAGS:</b> {_esc(tags_str)}")
    if meta_lines:
        _tg_send_message(tg_token, tg_chat, "━━━ <b>METADATA (not part of the script)</b> ━━━\n\n" + "\n\n".join(meta_lines))

    if gmail_app_password:
        if stage_texts and stage_names and len(stage_texts) == len(stage_names):
            body_html = "".join(
                f"<h4>{_esc(name.upper())}</h4><pre style='white-space:pre-wrap'>{_esc(text)}</pre>"
                for name, text in zip(stage_names, stage_texts))
        else:
            body_html = f"<pre style='white-space:pre-wrap'>{_esc(full_script)}</pre>"
        meta_html = ""
        if thumbnail_text:
            meta_html += f"<p><b>Thumbnail text:</b> {_esc(thumbnail_text)}</p>"
        if tags:
            meta_html += f"<p><b>Tags:</b> {_esc(', '.join(tags) if isinstance(tags, (list, tuple)) else str(tags))}</p>"
        html_body = (f"<p>{schedule_line}</p><h3>{_esc(title)}</h3>"
                     f"<p>Score: {score}/10 | {len(full_script.split())} words</p>"
                     f"{meta_html}<hr>{body_html}")
        send_email_notification(f"[{channel_name}] Script ready for review: {title}",
                                 html_body, gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ {timeout_minutes} min expired — auto-approved.")
        decision = "approve"
    return {"decision": decision, "feedback": feedback}


def review_audio_and_video(channel_name, audio_path, voice_used, video_path, thumbnail_path,
                            tg_token, tg_chat, check_ins_used=0, gmail_sender=None,
                            gmail_app_password=None, timeout_minutes=60, preview_seconds=60,
                            audio_score=None, audio_score_breakdown=None,
                            video_score=None, video_score_breakdown=None):
    """
    THE COMBINED AUDIO+VIDEO CHECKPOINT — sent together in one review
    window, per the explicit decision to keep this inside a single
    check-in. But audio (4 real options: approve/reject/edit/remake)
    and video (5 real options, the 5th being SWAP VISUALS) are genuinely
    distinct decisions, so this asks for them one after another within
    the same overall time budget, not merged into one ambiguous reply.

    Returns {"audio_decision": {...}, "video_decision": {...}}. If the
    audio decision is "reject" or "remake", the video step is skipped
    entirely (there's nothing left to review) and video_decision is None.

    FIX (found on final re-audit, direct user request for real per-stage
    scores): audio_score/video_score are optional 0-10 scores from
    quality_scoring.py's score_audio_quality()/score_video_quality() —
    real, independently-checkable signals (voice tier, A/V duration
    match, silence-gap detection via ffmpeg, resolution/stream
    integrity, file-size sanity), not estimates. When given, shown
    directly in the review message with a one-line breakdown so a low
    score is explainable, not just a number.
    """
    schedule_line = get_schedule_line(check_ins_used)

    def _breakdown_line(breakdown):
        if not breakdown:
            return ""
        parts = [f"{k.replace('_', ' ')}: {v.get('score')}/10" for k, v in breakdown.items()]
        return "\n(" + " | ".join(parts) + ")"

    # AUDIO — real 4-option decision
    audio_score_line = f"Audio quality score: {audio_score}/10{_breakdown_line(audio_score_breakdown)}\n\n" if audio_score is not None else ""
    audio_caption = (f"🎙️ {channel_name} — AUDIO REVIEW\n\n{schedule_line}\n\n"
                     f"Voice tier: {voice_used}\n"
                     f"{audio_score_line}"
                     f"Tap a button below — EDIT prompts you for what to change, "
                     f"SWAP VOICE regenerates with a different voice tier")
    sent = _tg_send_audio(tg_token, tg_chat, audio_path, caption=audio_caption,
                          reply_markup=_button_keyboard(fifth_option=("🎙️ SWAP VOICE", "swap_voice")))
    if not sent:
        _tg_send_message(tg_token, tg_chat,
                         f"⚠️ {channel_name}: could not send audio file for review "
                         f"(may be too large for Telegram) — proceeding on quality-gate score alone.")
        audio_decision = {"decision": "approve", "feedback": None}
    else:
        if gmail_app_password:
            send_email_notification(f"[{channel_name}] Audio ready for review",
                                     f"<p>{schedule_line}</p><p>Voice tier: <b>{voice_used}</b></p>"
                                     f"{'<p>Audio quality score: ' + str(audio_score) + '/10</p>' if audio_score is not None else ''}"
                                     f"<p>Listen via Telegram — audio isn't emailed directly.</p>",
                                     gmail_sender, gmail_app_password)
        d, fb = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
        if d == "timeout":
            _tg_send_message(tg_token, tg_chat, f"⏱️ Audio: {timeout_minutes} min expired — auto-approved.")
            d = "approve"
        audio_decision = {"decision": d, "feedback": fb}

    if audio_decision["decision"] in ("reject", "remake", "swap_voice"):
        return {"audio_decision": audio_decision, "video_decision": None}

    # VIDEO — real 5-option decision, the 5th being SWAP VISUALS
    preview_path = str(Path(video_path).parent / "review_preview_clip.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-t", str(preview_seconds),
                        "-c", "copy", preview_path], capture_output=True, timeout=120)
        preview_ready = Path(preview_path).exists() and Path(preview_path).stat().st_size > 10000
    except Exception:
        preview_ready = False

    video_score_line = f"Video quality score: {video_score}/10{_breakdown_line(video_score_breakdown)}\n\n" if video_score is not None else ""
    video_caption = (f"🎬 {channel_name} — VIDEO REVIEW\n\nFirst {preview_seconds}s preview\n\n"
                     f"{video_score_line}"
                     f"Tap a button below — EDIT will ask what to change, "
                     f"SWAP VISUALS regenerates just the visuals, same script and audio")
    if preview_ready:
        _tg_send_video(tg_token, tg_chat, preview_path, caption=video_caption,
                       reply_markup=_button_keyboard(fifth_option=("🎨 SWAP VISUALS", "swap_visuals")))
    else:
        _tg_send_message_with_buttons(tg_token, tg_chat,
                         f"⚠️ {channel_name}: could not cut a preview clip — sending thumbnail only.\n\n{video_caption}",
                         include_swap_visuals=True)
    if thumbnail_path and Path(thumbnail_path).exists():
        _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption="Final thumbnail")

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Video ready for review",
                                 f"<p>Video assembled — preview sent to Telegram "
                                 f"({'clip attached' if preview_ready else 'clip unavailable'}).</p>"
                                 f"{'<p>Video quality score: ' + str(video_score) + '/10</p>' if video_score is not None else ''}",
                                 gmail_sender, gmail_app_password)

    d, fb = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if d == "timeout":
        _tg_send_message(tg_token, tg_chat, f"⏱️ Video: {timeout_minutes} min expired — auto-approved.")
        d = "approve"
    video_decision = {"decision": d, "feedback": fb}

    return {"audio_decision": audio_decision, "video_decision": video_decision}

# FIX (found on re-audit, before building anything on top of this file):
# the lines that used to follow here were dead, unreachable code —
# leftover from a copy-paste, sitting after the real `return` above.
# Removed; they never executed and pyflakes-style analysis wouldn't
# catch this specific class of mistake (unreachable-but-valid code),
# only a real line-by-line read does.
