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
_MAX_TOTAL_REVIEW_HOURS = 4.5  # ceiling; the real budget is whatever the job can still afford


def _review_budget_hours():
    """
    The 4.5 hours above is a POLICY ceiling, not a promise the job can keep.

    It used to be enforced as a flat 4.5 hours counted from the first review
    checkpoint -- with no knowledge of how much of the job's 6 hours
    generation had already burned getting there. Run 30688297894 spent
    1h50m on script and audio before the video stage, so "4.5 more hours of
    review" was arithmetic the runner could not honour: work + full review
    window overruns the 6-hour limit, and an overrun job is cancelled, which
    commits nothing and loses every artifact it built.

    The budget is now the smaller of the policy ceiling and what the job
    physically has left after its finalisation reserve. Early in a run the
    two are the same and nothing changes; late in a slow run the window
    closes early and on purpose, so review force-approves and the episode
    finishes instead of being killed mid-sentence.
    """
    try:
        from job_clock import review_budget_hours
        return review_budget_hours(_MAX_TOTAL_REVIEW_HOURS)
    except Exception:
        # Outside the pipeline (tests, ad-hoc use) fall back to the ceiling.
        return _MAX_TOTAL_REVIEW_HOURS


# EVERY GATE GETS A SHARE. THE FIRST ONE USED TO TAKE ALL OF IT.
#
# Run 31156373254's own timing report:
#
#     Review wait breakdown — 54 min across 6 gate(s):
#       54.1 min  script                          (timeout)
#        0.0 min  audio+video                     (timeout)
#        0.0 min  title+thumbnail+description     (timeout)
#        0.0 min  shorts                          (timeout)
#        0.0 min  community tab                   (timeout)
#
# One gate consumed the entire episode budget waiting for a reply, and the
# other five then returned instantly with "Total review time budget reached —
# auto-approving". They never waited a single second, so they could not have
# seen a button press however fast it came. That is exactly what was reported:
# "there were things that didn't work out with Telegram, where I did try to
# click on the option buttons."
#
# Buttons that are announced must be answerable. The budget is therefore
# divided by how many gates an episode has, so no gate can starve the ones
# behind it. A gate that finishes early hands its unused share back to the
# rest, so a fast reviewer still gets the full window at the later gates.
_GATES_PER_EPISODE = 6


# A WINDOW TOO SHORT TO USE IS NOT A REVIEW.
#
# Dividing the leftover budget evenly is fair but not sufficient: on a run
# where generation ran long, the arithmetic hands the last gates two or three
# minutes each. Nobody watches a video, judges a thumbnail and replies in two
# minutes — and a gate that announces buttons then closes before they can be
# pressed is worse than no gate, because it looks like review happened.
#
# Below this floor a gate does not pretend. It says plainly that there was not
# enough of the job left to review this stage properly, which is a fact the
# reviewer can act on, rather than "auto-approved" which reads like consent.
#
# ONE NUMBER, ONE PLACE.
#
# This floor and job_clock.MIN_GATE_MIN are the same policy seen from the two
# ends of the same problem: job_clock uses it to decide when GENERATION must
# stop, this module uses it to decide whether a gate can honestly OPEN. Two
# independent 12.0 literals would drift the moment either was tuned, and the
# failure would be quiet and asymmetric — generation reserving 72 minutes
# while the gates demanded 90 would recreate the exact "no buttons were sent"
# report this floor exists to prevent, with nothing in the logs to explain it.
# job_clock owns the value; this reads it.
try:
    from job_clock import MIN_GATE_MIN as MIN_USABLE_GATE_MINUTES
except Exception:
    # Standalone use (tests, ad-hoc) still needs a sane floor.
    MIN_USABLE_GATE_MINUTES = 12.0


def _gate_share_seconds():
    """Wall-clock this gate may spend, given what earlier gates already used.

    Returns 0.0 when the fair share has fallen below a window a person could
    actually use; callers treat that as "cannot review this stage honestly".
    """
    budget = _review_budget_hours() * 3600.0
    used = sum(w["seconds"] for w in _REVIEW_WAITS)
    left_gates = max(1, _GATES_PER_EPISODE - len(_REVIEW_WAITS))
    share = max(0.0, (budget - used) / left_gates)
    return share if share >= MIN_USABLE_GATE_MINUTES * 60.0 else 0.0


# The three ways a gate ends without a human decision. They are DIFFERENT
# things and the log now says which -- "timeout" means nobody replied within
# this gate's window, "share-spent" means this gate used its slice of the
# episode budget, "budget-exhausted" means the whole episode's review time is
# gone. Every caller treats all three the same way (proceed as generated), so
# they are compared through this helper rather than against one string, which
# is what made adding an honest name safe.
#
# "unreviewable-no-time" is the fourth. It means the gate never opened,
# because the window left was too short for anyone to answer in.
#
# FIX (direct user report, with screenshots): this comment used to end "Every
# caller still proceeds as generated -- there is nothing else it can do".
# That was wrong, and it was the whole bug. There IS something else: hold the
# episode exactly where it is, unlisted and unpublished, the way an
# undelivered review already does. Live, the reviewer received
#
#   "there was not enough of this job left to review this stage properly, so
#    no buttons were sent ... This stage PROCEEDED AS GENERATED"
#
# and, one second later, "60 min expired — auto-approved" for the same stage.
# Two contradictory messages about one gate, and the stage shipped anyway.
#
# The rule now: A GATE THAT NEVER ASKED CANNOT PRODUCE AN APPROVAL. If the
# question was never delivered -- no buttons sent, or the send failed -- the
# episode holds and the next run resumes it from checkpoint. Nothing is
# deleted and nothing is published. Only a gate that genuinely asked, and got
# silence, may auto-approve on timeout; that part is deliberate and stays,
# because the pipeline has to keep moving when the reviewer is asleep.
UNREVIEWABLE_NO_TIME = "unreviewable-no-time"

# Ends where a human WAS asked and simply did not answer. These may proceed.
_NO_REPLY = ("timeout", "share-spent", "budget-exhausted")

# Ends where the human was never asked at all. These must HOLD.
# The literal is used rather than HOLD_UNDELIVERED because that constant is
# defined further down this module; the assertion below keeps the two honest.
_NEVER_ASKED = (UNREVIEWABLE_NO_TIME, "hold-undelivered")


def _no_human_reply(decision):
    return decision in _NO_REPLY or decision in _NEVER_ASKED


def never_asked(decision):
    """True when this gate never actually put the question to a human."""
    return decision in _NEVER_ASKED


# A SILENT WINDOW MEANS TWO DIFFERENT THINGS.
#
# Auto-approving on timeout is deliberate and stays: the pipeline must keep
# moving when the reviewer is asleep. But it is only defensible if the
# reviewer was actually ASKED. When the Telegram send fails, nothing arrives,
# nobody can press anything, the window expires, and the old code read that
# identical silence as approval -- publishing an episode no human had seen.
# That is the reported "no buttons, auto-approved" in full.
#
# HOLD is not REJECT. A rejection deletes the upload and bins the work, which
# would be an absurd response to a 400 from Telegram. Hold leaves everything
# exactly where it is, unlisted and unpublished, and says so loudly.
HOLD_UNDELIVERED = "hold-undelivered"
assert HOLD_UNDELIVERED in _NEVER_ASKED, (
    "_NEVER_ASKED hardcodes this value; they must not drift apart")


def resolve_silent_window(delivered, tg_token, tg_chat, timeout_minutes,
                          what="this checkpoint"):
    """What an expired review window means. 'approve' only if we asked."""
    if delivered:
        _tg_send_message(tg_token, tg_chat,
                         f"⏱️ {timeout_minutes} min expired — auto-approved.")
        return "approve"
    _tg_send_message(
        tg_token, tg_chat,
        f"🚨 {what}: no reviewable question ever reached you — either the "
        f"message failed to send, or too little job time was left to open a "
        f"window anyone could answer in. Nobody was asked, so this is NOT "
        f"being auto-approved. The episode is held exactly where it is, "
        f"unlisted and unpublished, and the next run resumes it from the "
        f"checkpoint. Nothing has been deleted.")
    print(f"  {what}: undelivered review — holding instead of auto-approving.")
    return HOLD_UNDELIVERED


def _review_time_spent_hours():
    """How long this episode has actually spent WAITING FOR A HUMAN."""
    return sum(w["seconds"] for w in _REVIEW_WAITS) / 3600.0


def _total_review_time_exhausted():
    """Is the review window gone?

    THIS COMPARED THE WRONG TWO NUMBERS AND SILENTLY CANCELLED EVERY GATE.
    ------------------------------------------------------------------
    It used to measure wall-clock since the PROCESS started and compare that
    against the review budget. But the process starts when GENERATION starts,
    so every minute spent writing the script, rendering audio and assembling
    video counted against a budget that exists to cap how long we wait for a
    reply. Generation was spending the reviewer's time.

    Run 31257986626, worked through with its real numbers:

        script gate reached 2h47m in; budget 2.47h -> 2.78 >= 2.47 -> EXHAUSTED
        audio  gate reached 2h54m in; budget 2.35h -> 2.90 >= 2.35 -> EXHAUSTED
        video  gate reached 4h01m in; budget 0.97h -> 4.02 >= 0.97 -> EXHAUSTED

    Every gate returned "budget-exhausted" on its first check, before sending
    a single button, having waited zero seconds. All six of them. That is
    precisely the report: no buttons at any stage, everything auto-approved,
    and the one notification that did arrive was already dead when it landed.
    The budget was never actually spent on review -- it was spent on a slow
    script stage, which on that run was slow because the free AI quotas ran
    out and it retried for 2h43m.

    A budget for waiting must be measured in waiting. The recorded gate waits
    are exactly that, and they were already being tracked for the timing
    report -- nothing needed to be invented, only compared correctly.

    The job clock stays as a SEPARATE, physical check. That one is real: when
    the runner is genuinely minutes from being killed, review has to stop or
    the job dies mid-render and commits nothing. But it is a hard-deadline
    guard, not a budget, and conflating the two is what caused this.
    """
    if _review_time_spent_hours() >= _review_budget_hours():
        return True
    try:
        from job_clock import remaining_minutes, RESERVE_MIN
        return remaining_minutes() <= RESERVE_MIN
    except Exception:
        return False


# ── where the wall-clock actually goes ─────────────────────────────────
# Run 30578466862 took 5 hours 34 minutes and that number sat "undiagnosed"
# for days, because nothing anywhere recorded how long each review gate
# waited. It was never a bug: the gates poll for a human decision for up to
# 60 minutes each, three attempts, under a 4.5-hour episode-wide budget, so
# an unattended run spends most of its life waiting on a reply that is not
# coming and roughly an hour doing real work.
#
# That is a legitimate design, but a run whose duration cannot be attributed
# is a run nobody can reason about -- and on a free Actions allowance the
# difference between "five hours of compute" and "one hour of compute and
# four hours of idle polling" is the whole budget question. Every gate now
# records its own wait, and the pipeline prints the breakdown.
_REVIEW_WAITS = []


def record_review_wait(label, seconds, outcome):
    _REVIEW_WAITS.append({"gate": label, "seconds": round(seconds, 1),
                          "outcome": outcome})


def review_time_report():
    """Human-readable breakdown of every gate's wait. Safe to call anytime."""
    if not _REVIEW_WAITS:
        return "No review gates ran."
    total = sum(w["seconds"] for w in _REVIEW_WAITS)
    lines = [f"Review wait breakdown — {total/60:.0f} min across "
             f"{len(_REVIEW_WAITS)} gate(s):"]
    for w in sorted(_REVIEW_WAITS, key=lambda x: -x["seconds"]):
        lines.append(f"  {w['seconds']/60:6.1f} min  {w['gate']}  ({w['outcome']})")
    return "\n".join(lines)


# ── TELLING THE OWNER WHAT JUST HAPPENED ───────────────────────────────
# Direct request: after approving a stage by hand, say so and say what is
# happening next -- "so that I can be best in loop of things and not blind
# sided with just auto approvals and updates."
#
# The second half of that is the important half. Before this, a gate the
# owner answered and a gate that simply ran out of time both continued in
# exactly the same silence, so from the phone they were indistinguishable.
# A receipt that only ever said "approved" would make that WORSE, because
# it would put the owner's name on decisions the owner never made. So the
# receipt's first job is to state who decided, and an unanswered gate is
# reported in a visibly different register from an approval.
_STAGE_AFTER = {
    "script":                      "Stage 2 — Audio: narration, voice pick, music bed",
    "audio+video":                 "Stage 5 — Title, thumbnail and description",
    "title":                       "the thumbnail",
    "thumbnail":                   "the description",
    "title+thumbnail+description": "final assembly, then the pre-publish check",
    "shorts":                      "finalising the episode",
    "community tab":               "the end of the run",
    "final pre-publish":           "publishing",
    "resume confirmation":         "picking up from the last stage that passed",
}

# (headline, what it means for the episode)
_DECISION_WORDS = {
    "approve":      ("APPROVED",          "moving on"),
    "reject":       ("REJECTED",          "this episode stops here, nothing is published"),
    "edit":         ("EDIT REQUESTED",    "your notes go back in and it is rewritten"),
    "remake":       ("REMAKE REQUESTED",  "this stage is built again from scratch"),
    "swap_visuals": ("VISUALS SWAPPED",   "the picture is rebuilt, the audio is kept"),
    "swap_voice":   ("VOICE SWAPPED",     "re-narrated in a different voice"),
    "cancel":       ("CANCELLED",         "the run is stopping"),
}

_GATE_LEDGER = []


def _clock_left_line():
    """How much of the 6-hour job remains, when that is knowable."""
    try:
        from job_clock import remaining_minutes
        _m = remaining_minutes()
        if _m is None:
            return ""
        return "\n⏱ %d min left of this run's 6-hour budget." % _m
    except Exception:
        return ""


def send_decision_receipt(tg_token, tg_chat, label, decision, waited_s,
                          feedback=None):
    """
    Confirm, on Telegram, what was just decided at `label` and what happens
    next. Records the same facts in a ledger so the end of the run can show
    which decisions were the owner's and which were not.
    """
    _human = not _no_human_reply(decision)
    _nxt = _STAGE_AFTER.get(label, "the next stage")
    _mins = waited_s / 60.0
    _GATE_LEDGER.append({"gate": label, "decision": decision,
                         "by_owner": _human, "minutes": round(_mins, 1)})
    try:
        if never_asked(decision):
            # The question never reached a human. This must never read like
            # a decision -- nobody made one.
            _txt = ("⛔ <b>%s — COULD NOT REACH YOU</b>\n"
                    "The review never got to your phone, so <b>nothing was "
                    "approved</b>. The episode is being HELD exactly where it "
                    "is: not published, not deleted.\n"
                    "Fix the Telegram bot token/chat and the next run offers "
                    "it again." % label.upper())
        elif _human:
            _head, _means = _DECISION_WORDS.get(
                decision, (decision.upper(), "continuing"))
            _txt = ("✅ <b>%s — %s BY YOU</b>\n"
                    "%s.\n"
                    "You answered in %s.\n"
                    "▶️ Next: %s"
                    % (label.upper(), _head, _means.capitalize(),
                       ("%.0f sec" % waited_s) if _mins < 1
                       else ("%.0f min" % _mins), _nxt))
            if feedback:
                _txt += "\n📝 Your note, going in verbatim:\n<i>%s</i>" % (
                    _html_module.escape(str(feedback)[:400]))
        else:
            # Answered by the clock, not by a person. Say that plainly.
            _txt = ("⚠️ <b>%s — NO ANSWER FROM YOU</b>\n"
                    "Waited %.0f min and heard nothing, so the pipeline "
                    "proceeded on its own (<code>%s</code>).\n"
                    "<b>This was NOT your approval.</b>\n"
                    "▶️ Next: %s" % (label.upper(), _mins, decision, _nxt))
        _tg_send_message(tg_token, tg_chat, _txt + _clock_left_line())
    except Exception as e:
        print(f"  Decision receipt not sent (non-fatal): {e}")


def heads_up(tg_token, tg_chat, doing, minutes, next_question=None):
    """
    "Nothing needed from you for a while" — so the owner knows the silence
    is work rather than a stall, and roughly when to look again. A run that
    goes quiet for 25 minutes of rendering is indistinguishable from a run
    that has died, unless it says so.
    """
    try:
        _txt = ("🔧 <b>Working — nothing needed from you</b>\n"
                "%s (about %d min)." % (doing, minutes))
        if next_question:
            _txt += "\n🔔 Next thing I'll ask you about: %s" % next_question
        _tg_send_message(tg_token, tg_chat, _txt + _clock_left_line())
    except Exception as e:
        print(f"  Heads-up not sent (non-fatal): {e}")


def send_run_ledger(tg_token, tg_chat, outcome=""):
    """
    The end-of-run receipt: every gate, what was decided, and — the point —
    which of those were actually yours. Anything the clock decided is listed
    separately, so a run can never quietly end up "all approved" without the
    owner being told exactly which approvals were not theirs.
    """
    if not _GATE_LEDGER:
        return
    try:
        _mine = [g for g in _GATE_LEDGER if g["by_owner"]]
        _auto = [g for g in _GATE_LEDGER if not g["by_owner"]]
        _lines = ["🧾 <b>Run summary — who decided what</b>"]
        if outcome:
            _lines.append(outcome)
        _lines.append("\n<b>You decided %d of %d:</b>"
                      % (len(_mine), len(_GATE_LEDGER)))
        for g in _GATE_LEDGER:
            _lines.append("  %s %s — <b>%s</b>%s"
                          % ("✅" if g["by_owner"] else "⚠️",
                             g["gate"], g["decision"].upper(),
                             "" if g["by_owner"] else "  ← not you"))
        if _auto:
            _lines.append("\n⚠️ <b>%d gate(s) went ahead without you.</b> "
                          "If that is not what you wanted, reply sooner next "
                          "run or raise REVIEW_TIMEOUT_MIN." % len(_auto))
        else:
            _lines.append("\n👍 Every gate this run was decided by you.")
        _tg_send_message(tg_token, tg_chat, "\n".join(_lines))
    except Exception as e:
        print(f"  Run ledger not sent (non-fatal): {e}")


def gate_ledger():
    """The decisions so far, for the run's own logging."""
    return list(_GATE_LEDGER)


def default_review_timeout():
    """
    Per-gate poll timeout in minutes.

    Overridable with REVIEW_TIMEOUT_MIN so a TEST run does not cost four
    hours of idle polling to find out whether the visuals render. Every gate
    reads this instead of hard-coding 60.
    """
    try:
        v = int(os.environ.get("REVIEW_TIMEOUT_MIN", "60"))
        return max(1, min(180, v))
    except (TypeError, ValueError):
        return 60


import imaplib
import email as email_lib
import email.header  # noqa: F401  — needed for the subject decode below


def check_email_replies(sender_email, app_password, since_datetime=None,
                        channel_tag=None):
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

            # ONE INBOX, FIVE CHANNELS.
            #
            # GMAIL_SENDER_EMAIL / GMAIL_APP_PASSWORD are shared secrets: all
            # five pipelines send from, and poll, the SAME mailbox. Without a
            # filter, a reply meant for one channel's review is read by
            # whichever channel happens to poll next -- so an APPROVE typed
            # for Ch1 could approve a Ch3 script, and Ch1 would keep waiting
            # for a decision that has already been consumed. Every
            # notification subject starts with "[channel name]", and a reply
            # keeps it as "Re: [channel name] ...", so the tag is the
            # disambiguator.
            if channel_tag:
                try:
                    _subj = str(email_lib.header.make_header(
                        email_lib.header.decode_header(msg.get("Subject", ""))))
                except Exception:
                    _subj = msg.get("Subject", "") or ""
                if channel_tag.lower() not in _subj.lower():
                    continue

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

        # STOP. The word a person reaches for when they want it to stop.
        #
        # This was not in the list. On run 31156373254 the channel owner
        # typed "cancel" at the final pre-publish gate; "cancel" matched
        # nothing, fell through to the `break` below, returned (None, None),
        # and was therefore indistinguishable from having said nothing at
        # all -- and saying nothing at that gate means auto-approve. The
        # video went to YouTube after an explicit instruction not to publish
        # it. That is the worst failure this system can have, and it was one
        # missing keyword.
        #
        # Every word someone might actually type is here, not just the one
        # that was reported.
        if upper in ("CANCEL", "STOP", "ABORT", "HALT", "NO", "DON'T", "DONT",
                     "DO NOT", "DO NOT PUBLISH", "DONT PUBLISH", "HOLD",
                     "WAIT", "PAUSE", "KILL", "CANCELLED", "CANCELED"):
            return "cancel", None
        if upper.startswith("CANCEL") or upper.startswith("STOP") \
                or upper.startswith("DO NOT") or upper.startswith("DON'T"):
            reason = line.split(":", 1)[1].strip() if ":" in line else None
            return "cancel", reason
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


# PER-CHANNEL REVIEW INBOX.
#
# Every channel's review mail used to land in one shared inbox. Ch1 is a
# medical channel with its own identity and its own address, and everything
# about it is to go there and nowhere else. A channel sets this once at
# startup; channels that never call it keep the previous shared behaviour, so
# Ch2-Ch5 are untouched.
_REVIEW_RECIPIENT = [None]
_REVIEW_MAILBOX = [None]   # (address, app_password) whose INBOX holds replies
# Which channel this process is. Used to make sure a review only ever consumes
# ITS OWN emailed reply out of the one shared inbox.
_CURRENT_CHANNEL = [None]


def set_review_recipient(email, app_password=None):
    """
    Route this channel's review mail to `email`.

    app_password is the App Password for THAT mailbox. It matters because the
    email fallback is two-way: notifications are SENT to the recipient, and
    replies are READ back over IMAP. If the recipient's own credentials are
    supplied, both halves use the same mailbox and replying to the mail works.
    Without them, mail still goes to the right place but replies have to be
    read from the sending account's inbox instead -- so the caller is told.
    """
    _REVIEW_RECIPIENT[0] = (email or "").strip() or None
    _REVIEW_MAILBOX[0] = ((email or "").strip(), app_password) if (email and app_password) else None
    return _REVIEW_RECIPIENT[0]


def review_recipient():
    return _REVIEW_RECIPIENT[0] or os.environ.get("REVIEW_EMAIL") or "nextlayermediallc@gmail.com"


def reply_mailbox(default_sender, default_password):
    """
    Which mailbox to poll for emailed decisions.

    Must be the mailbox the notification was DELIVERED to -- polling a
    different inbox than the one receiving the mail is how an emailed
    decision silently never registers.

    In the normal setup the sending account IS the review inbox (the channel
    mails itself), so the default credentials already point at the right
    mailbox and nothing extra is needed.
    """
    if _REVIEW_MAILBOX[0]:
        return _REVIEW_MAILBOX[0]
    return default_sender, default_password


def reply_mailbox_is_correct(default_sender):
    """
    True when the inbox we poll is the inbox the mail lands in.

    False means an emailed reply will be sitting in a mailbox nothing reads --
    worth saying out loud rather than discovering when a decision is ignored.
    """
    want = review_recipient()
    have = (_REVIEW_MAILBOX[0][0] if _REVIEW_MAILBOX[0] else default_sender) or ""
    return have.strip().lower() == (want or "").strip().lower()


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
    # Was hardcoded to the retired channel's address. Env first so it is
    # configurable, then the account actually in use.
    # A channel that has claimed its own inbox (set_review_recipient) wins
    # over the shared default.
    recipient_email = recipient_email or review_recipient()
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
    # Remember this notification's "[channel] " tag so the reply poller only
    # consumes a reply to THIS mail. Set at send time, so it is automatically
    # correct for every gate without touching a single call site.
    _tag = re.match(r"\s*(\[[^\]]{1,80}\])", subject)
    if _tag:
        _CURRENT_CHANNEL[0] = _tag.group(1)
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


def send_with_keyboard(tg_token, tg_chat, text, keyboard):
    """ONE path for every button message. Returns True only if it arrived.

    Two gates built their own keyboards and posted them with a bare
    requests.post: the Community Tab prompt and the resume checkpoint. That
    meant the hardening applied to the main sender -- confirm delivery,
    retry as plain text -- covered most buttons but not all of them, and
    "most" is the wrong answer for a review system. Both now come through
    here, so there is a single place where a button message can fail and a
    single behaviour when it does.
    """
    for attempt, payload in enumerate((
            {"chat_id": tg_chat, "text": text, "parse_mode": "HTML",
             "reply_markup": keyboard},
            {"chat_id": tg_chat, "text": text, "reply_markup": keyboard})):
        try:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                              json=payload, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                if attempt:
                    print("  Buttons delivered on the plain-text retry "
                          "(the HTML version was rejected).")
                return True
            print(f"  Telegram sendMessage (buttons) failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"  Telegram sendMessage (buttons) failed: {e}")
    print("  THE REVIEWER WAS NEVER ASKED — no auto-approval may follow this.")
    return False


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

    THIS RETURNS WHETHER THE ASK ACTUALLY ARRIVED, AND THAT MATTERS.

    It used to return nothing. Every one of its call sites fired it and went
    straight to polling for a decision, so a message Telegram REJECTED was
    indistinguishable from a message nobody answered -- and the timeout
    branch of every content gate reads "no reply" as APPROVE. A single 400
    therefore published an episode that no human had been shown. That is the
    reported failure in its original words: "no buttons, auto-approved".

    A non-200 is not an exception, so nothing raised; the old code printed a
    line into a log nobody reads at 3am and carried on.

    On failure it retries once as plain text. The likeliest cause of a
    rejection here is an HTML parse error from dynamic content that slipped
    past _esc(), and losing the formatting is obviously better than losing
    the review. Buttons survive the retry -- reply_markup is independent of
    parse_mode.
    """
    if fifth_option is None and include_swap_visuals:
        fifth_option = ("🎨 SWAP VISUALS", "swap_visuals")
    keyboard = _button_keyboard(fifth_option=fifth_option)
    for attempt, payload in enumerate((
            {"chat_id": tg_chat, "text": text, "parse_mode": "HTML",
             "reply_markup": keyboard},
            {"chat_id": tg_chat, "text": text, "reply_markup": keyboard})):
        try:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                              json=payload, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                if attempt:
                    print("  Review buttons delivered on the plain-text retry "
                          "(the HTML version was rejected).")
                return True
            print(f"  Telegram sendMessage (buttons) failed (check the bot token/chat ID): "
                  f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"  Telegram sendMessage (buttons) failed (check the bot token/chat ID): {e}")
    print("  THE REVIEWER WAS NEVER ASKED — no auto-approval may follow this.")
    return False


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


def _tg_send_document(tg_token, tg_chat, doc_path, caption="", reply_markup=None):
    """
    Real Telegram document send (PDF/Word/etc.) — built in direct
    response to explicit feedback that a long wall of chunked text
    messages for the script is unreadable. A proper file attachment
    opens in the reader's own PDF/Word viewer instead.
    """
    try:
        data = {"chat_id": tg_chat, "caption": caption}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        with open(doc_path, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendDocument",
                          data=data, files={"document": f}, timeout=120)
        if r.status_code != 200:
            print(f"  Telegram sendDocument failed (check bot token/chat ID): {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  Telegram sendDocument failed: {e}")
        return False


def export_script_to_pdf(channel_name, title, niche_name, score, full_script,
                          stage_texts=None, stage_names=None, thumbnail_text=None,
                          tags=None, output_path=None):
    """
    Real, properly formatted PDF of the script for review — built in
    direct response to explicit feedback that a long wall of chunked
    Telegram text messages ("cutting down the paragraphs") is unreadable
    and doesn't invite anyone to actually read it. Uses reportlab, the
    same library already proven in video_pipeline/monetization.py for
    product manuscript PDFs. Returns the output path on success, None on
    any failure (caller falls back to the existing chunked-text send,
    so a missing reportlab install or a render error never blocks the
    actual review from happening).
    """
    if output_path is None:
        output_path = "/tmp/script_review.pdf"
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors

        doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                                 topMargin=0.9*inch, bottomMargin=0.9*inch,
                                 leftMargin=0.9*inch, rightMargin=0.9*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ScriptTitle", fontSize=20, leading=26,
                                   spaceAfter=6, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#14161a")))
        styles.add(ParagraphStyle(name="ScriptMeta", fontSize=10.5, leading=15,
                                   spaceAfter=18, textColor=colors.grey))
        styles.add(ParagraphStyle(name="StageHead", fontSize=13, leading=17,
                                   spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#7d6b45")))
        styles.add(ParagraphStyle(name="ScriptBody", fontSize=11, leading=16,
                                   spaceAfter=8))

        def _esc_pdf(text):
            return _html_module.escape(str(text), quote=False).replace("\n", "<br/>")

        story = [Paragraph(_esc_pdf(title), styles["ScriptTitle"]),
                 Paragraph(f"{channel_name} | {niche_name} | Score: {score}/10 | "
                           f"{len(full_script.split())} words", styles["ScriptMeta"])]

        if stage_texts and stage_names and len(stage_texts) == len(stage_names):
            for name, text in zip(stage_names, stage_texts):
                story.append(Paragraph(_esc_pdf(name.upper()), styles["StageHead"]))
                story.append(Paragraph(_esc_pdf(text), styles["ScriptBody"]))
        else:
            story.append(Paragraph(_esc_pdf(full_script), styles["ScriptBody"]))

        if thumbnail_text or tags:
            story.append(Spacer(1, 12))
            story.append(Paragraph("METADATA", styles["StageHead"]))
            if thumbnail_text:
                story.append(Paragraph(f"Thumbnail text: {_esc_pdf(thumbnail_text)}", styles["ScriptBody"]))
            if tags:
                tags_str = ", ".join(tags) if isinstance(tags, (list, tuple)) else str(tags)
                story.append(Paragraph(f"Tags: {_esc_pdf(tags_str)}", styles["ScriptBody"]))

        doc.build(story)
        return output_path
    except Exception as e:
        print(f"  Script PDF export failed (falling back to chunked text): {e}")
        return None


# Set by each gate before it polls, so the wait can be attributed to a name
# rather than showing up as an unexplained hour of wall-clock.
_CURRENT_GATE = ["review"]


def set_current_gate(label):
    _CURRENT_GATE[0] = label or "review"


def _poll_for_decision(tg_token, tg_chat, timeout_minutes=None, max_attempts=3,
                       gmail_sender=None, gmail_app_password=None):
    """
    Timed wrapper. Every exit path is recorded against the gate that was
    waiting, so review_time_report() can account for the whole run.
    """
    if timeout_minutes is None:
        timeout_minutes = default_review_timeout()
    _t0 = time.time()
    label = _CURRENT_GATE[0]
    try:
        decision, feedback = _poll_for_decision_inner(
            tg_token, tg_chat, timeout_minutes, max_attempts,
            gmail_sender, gmail_app_password)
    finally:
        pass
    _waited = time.time() - _t0
    record_review_wait(label, _waited, decision)
    # Every gate in this module returns through here, so the receipt is sent
    # once, from one place. Wiring it into each gate separately is how a gate
    # ends up silently missing one.
    send_decision_receipt(tg_token, tg_chat, label, decision, _waited, feedback)
    return decision, feedback


def _poll_for_decision_inner(tg_token, tg_chat, timeout_minutes=60, max_attempts=3,
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
    # Anything the human typed that could not be parsed. Mutable so the
    # nested poll loop can set it. Its only job is to make auto-approve
    # impossible once a person has demonstrably been at the other end.
    spoke_up = [None]
    _gate_label = _CURRENT_GATE[0] or "review"
    _getupdates_error_logged = [False]  # mutable so the nested loop below can set it once
    awaiting_edit_text = False  # FIX (July 14 2026): EDIT is now a real
    # button (see _button_keyboard). A tap can't carry free-form text, so
    # tapping it prompts for what to change, then the very next text
    # reply — whatever its wording — is taken as that edit content,
    # rather than re-parsed as a fresh decision keyword.

    # FIX (real production bug, Ch1 run 30106640227): offset starts at
    # None on every single call -- each GitHub Actions run is a fresh
    # process/container, so nothing persists it. getUpdates with no
    # offset returns EVERY update Telegram still has queued, including
    # any button tap or text reply left over from a completely
    # different, earlier review checkpoint that already resolved (by
    # timeout or a real decision) before that reply ever arrived. A
    # script review here was rejected 18 seconds after its message was
    # sent -- far too fast for a real read, and traced to exactly this:
    # a stale queued update from an unrelated earlier checkpoint was
    # consumed as if it were this review's decision. Drain whatever is
    # already queued once, advancing past it without treating any of it
    # as a real decision, so only updates that arrive AFTER this
    # specific review was posted can ever resolve it.
    try:
        _drain = requests.get(f"https://api.telegram.org/bot{tg_token}/getUpdates",
                              params={"timeout": 0}, timeout=15)
        _drain_updates = _drain.json().get("result", []) if _drain.status_code == 200 else []
        if _drain_updates:
            offset = _drain_updates[-1]["update_id"] + 1
            print(f"  Discarded {len(_drain_updates)} stale Telegram update(s) queued "
                  f"before this review started.")
    except Exception as e:
        print(f"  Stale-update drain (non-fatal): {e}")

    # This gate's own slice of the episode budget, so it cannot spend the
    # window the gates behind it still need. Never longer than the per-gate
    # timeout that was asked for.
    _share_min = _gate_share_seconds() / 60.0

    # BUTTONS THAT DIE IN SIXTY SECONDS ARE WORSE THAN NO BUTTONS.
    #
    # The clamp below used to be `max(1.0, min(timeout, share))`. When the
    # share had collapsed to seconds, that floor of 1.0 did not protect the
    # reviewer -- it guaranteed a ONE MINUTE window. The gate announced its
    # buttons, the reviewer opened Telegram, pressed one, and got "1 min
    # expired — auto-approved", because the window had already closed while
    # the notification was still arriving. Reported exactly that way: "I did
    # receive that, but post that, in a few seconds, it told me that the thing
    # had expired."
    #
    # A share below the usable floor now means the gate does not open at all.
    # It says so, in words that do not read like consent, and the timing
    # report records it as unreviewable rather than approved.
    if _share_min <= 0.0:
        # The wrapper records this gate's wait from _CURRENT_GATE on the way
        # out, so recording here as well would double-count it in the report.
        _tg_send_message(
            tg_token, tg_chat,
            "⚠️ %s: there was not enough of this job left to review this stage "
            "properly, so no buttons were sent — a window under %.0f minutes "
            "closes before anyone can answer it. This stage PROCEEDED AS "
            "GENERATED and was NOT approved by you. Generation ran long this "
            "run; that is the thing to fix, not this message."
            % (_gate_label, MIN_USABLE_GATE_MINUTES))
        return "unreviewable-no-time", None

    _gate_deadline = datetime.datetime.now() + datetime.timedelta(minutes=_share_min)
    timeout_minutes = max(1.0, min(float(timeout_minutes), _share_min))

    for attempt in range(1, max_attempts + 1):
        if _total_review_time_exhausted():
            _tg_send_message(tg_token, tg_chat,
                             "⏱️ Total review time budget for this episode reached — "
                             "auto-approving to keep this run within GitHub Actions' real "
                             "job time limit. Whatever hasn't been decided yet proceeds as generated.")
            return "budget-exhausted", None
        if datetime.datetime.now() >= _gate_deadline:
            # This gate's share is spent; the remaining gates keep theirs.
            return "share-spent", None
        deadline = min(datetime.datetime.now() + datetime.timedelta(minutes=timeout_minutes),
                       _gate_deadline)
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
                return "budget-exhausted", None

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
                    # "resume"/"restart_scratch"/"redo_audio_only": the
                    # real checkpoint-resume gate's own decisions (see
                    # review_resume_checkpoint below) — added to this
                    # same whitelist rather than a separate poll loop so
                    # that gate gets the same proven reminders/email-
                    # fallback/time-budget handling every other checkpoint
                    # already relies on.
                    if cb_data in ("approve", "reject", "remake", "swap_visuals", "swap_voice",
                                   "resume", "restart_scratch", "redo_audio_only"):
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

                # A HUMAN TYPED SOMETHING AND IT WAS THROWN AWAY IN SILENCE.
                #
                # Unrecognised text used to fall through this loop with no
                # reply, no log line, and no effect -- byte-for-byte the same
                # outcome as never touching the phone. The person is left
                # believing they answered while the gate counts down to
                # auto-approve. That is how "cancel" became a published video.
                #
                # Two things now happen. They are told immediately that the
                # word was not understood, with the words that do work. And
                # the gate remembers that a human is HERE -- see spoke_up
                # below, which removes auto-approve from the table entirely.
                # Whatever they meant, they did not mean "publish it while I
                # am not looking".
                spoke_up[0] = text
                print(f"  Unrecognised review reply kept the gate open: {text[:80]!r}")
                _tg_send_message(
                    tg_token, tg_chat,
                    f"⚠️ I did not understand “{text[:60]}”, so nothing has "
                    f"been decided yet.\n\nThis will NOT auto-publish now — a reply "
                    f"I could not read still counts as you being here.\n\n"
                    f"Tap a button above, or type one of:\n"
                    f"APPROVE · REJECT · REMAKE · CANCEL · EDIT: your change")

            # Check email every ~4th cycle (roughly every 60s given the 15s sleep)
            email_check_counter += 1
            # Poll the mailbox the notification was DELIVERED to. When a
            # channel has claimed its own review inbox, reading the sending
            # account's inbox instead would mean an emailed decision silently
            # never registers -- the reply is sitting in a mailbox nothing
            # looks at.
            _reply_addr, _reply_pass = reply_mailbox(gmail_sender, gmail_app_password)
            if _reply_pass and email_check_counter % 4 == 0:
                email_replies = check_email_replies(_reply_addr, _reply_pass,
                                                     since_datetime=review_start_time,
                                                     channel_tag=_CURRENT_CHANNEL[0])
                if email_replies:
                    decision, extra, _msg_id = email_replies[0]  # most recent real reply
                    return decision, extra

        # This attempt's 60-minute window expired with no reply on either channel
        if attempt < max_attempts:
            _tg_send_message(tg_token, tg_chat,
                             f"⏰ Reminder ({attempt}/{max_attempts}): still waiting on your "
                             f"decision. {max_attempts - attempt} more 60-minute window(s) "
                             f"before this "
                             + ("HOLDS (you replied, so it will not auto-publish)."
                                if spoke_up[0] else "auto-approves."))

    # SILENCE AND A MISUNDERSTOOD REPLY ARE NOT THE SAME THING.
    #
    # Timing out means "nobody was there", and for a routine gate that is a
    # reasonable thing to treat as consent. But if a human typed ANYTHING
    # during this window, they were there. Publishing over the top of that
    # is the failure that put an unwanted video on the channel, and no
    # keyword list is a complete defence -- there will always be a word I
    # did not anticipate. So the rule is about presence, not vocabulary:
    # a person who spoke gets a hold, whatever they said.
    if spoke_up[0]:
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Time is up, but you DID reply during this review and I could "
                         "not read it — so this is being HELD, not published.\n\n"
                         f"What you sent: “{spoke_up[0][:120]}”\n\n"
                         "Nothing goes public on a reply I failed to understand.")
        return "cancel", spoke_up[0]
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
                                         timeout_minutes=60, thumbnail_score=None,
                                         thumbnail_issues=None):
    """
    THE COMBINED CHECKPOINT — title, thumbnail, and description reviewed
    together in one message, per the explicit request to reduce total
    review time. Shows the real description quality score so "why does
    this description look different from usual" has a concrete number
    behind it, not a black box.

    thumbnail_score is the score of the RENDERED PICTURE — measured on the
    pixels of the exact file attached to this message. It used to be the score
    of the headline STRING, which is how a card reading "8 0" with a ring
    around an empty floor was presented for review as 10.0/10. A number next to
    a picture has to be about that picture.

    thumbnail_issues is the list of specific, measured reasons behind any
    deduction, shown verbatim, so a low score says what is wrong rather than
    leaving the reviewer to guess.
    """
    set_current_gate("title+thumbnail+description")
    schedule_line = get_schedule_line(check_ins_used)
    thumb_score_line = ""
    if thumbnail_score is not None:
        thumb_score_line = f"Thumbnail picture score: {thumbnail_score}/10\n"
        for _why in (thumbnail_issues or []):
            thumb_score_line += f"   • {_why}\n"
    caption = (f"🖼️🏷️📝 {channel_name} — TITLE + THUMBNAIL + DESCRIPTION REVIEW\n\n"
              f"{schedule_line}\n\n"
              f"Title: {title}\n"
              f"{thumb_score_line}"
              f"Description quality score: {description_score}/10\n\n"
              f"Tap a button below — EDIT will ask what to change")
    # FIX (found on direct user report, July 23 2026 — real bug): this
    # checkpoint's decision BUTTONS are attached to the thumbnail photo
    # message — but the send's return value was never checked, unlike
    # (now) every other checkpoint in this file. A failed photo send
    # (bad path, oversized image, a transient Telegram error) meant the
    # reviewer got literally nothing for this checkpoint: no photo, no
    # buttons, no text, nothing indicating a decision was even expected
    # — while the pipeline sat waiting out the full timeout regardless.
    # This is very likely why a real reviewer reported seeing only the
    # script and audio checkpoints and nothing past them.
    _ttd_photo_sent = _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption=caption,
                   reply_markup=_button_keyboard())
    if not _ttd_photo_sent:
        _delivered = _tg_send_message_with_buttons(tg_token, tg_chat,
            f"⚠️ Could not send the thumbnail image (missing file, too large, or a "
            f"Telegram error) — review the title/description below and decide anyway.\n\n{caption}")
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
                     f"{'<p>Thumbnail picture score: ' + str(thumbnail_score) + '/10</p>' if thumbnail_score is not None else ''}"
                     f"{'<ul>' + ''.join('<li>' + _esc(w) + '</li>' for w in (thumbnail_issues or [])) + '</ul>' if thumbnail_issues else ''}"
                     f"<p>Description score: {description_score}/10</p>"
                     f"<pre style='white-space:pre-wrap'>{_esc(description)}</pre>")
        send_email_notification(f"[{channel_name}] Title/Thumbnail/Description ready for review",
                                 html_body, gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "cancel":
        # CANCEL means stop, at every gate, not just the final one. It is
        # never folded into approve and never treated as a soft "reject" that
        # quietly carries on to the next stage.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. This episode is being abandoned — nothing "
                         "further is generated and nothing is published.")
        return {"decision": "cancel", "feedback": feedback}
    if _no_human_reply(decision):
        decision = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what=_CURRENT_GATE[0] or "this checkpoint")
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
    # Four calls to the same function with the same arguments is one
    # description generated four times, not four attempts. A provider that
    # answers deterministically returns the identical text every time, and
    # the loop then reports "4 attempts" for one piece of work.
    #
    # An identical answer is no longer counted or scored. That is the honest
    # half of the fix. The dishonest half would be pretending this module can
    # rotate the provider: set_ai_variant lives in the channel pipeline, not
    # here, and generate_fn's signature is fixed by every caller -- a first
    # version of this imported a module that does not exist, which the
    # surrounding try/except would have swallowed silently while appearing
    # to work. Real variation between description attempts has to come from
    # the caller passing a variant-aware generator -- which Ch1 now does
    # (_desc_gen rotates set_ai_variant per call, in clinical_pipeline). This
    # side of it is the backstop: a caller that does not rotate, or a rotation
    # that lands on the same provider, still cannot report one description
    # as four.
    _seen_desc = set()
    _real = 0                       # attempts that were genuinely different
    for _call in range(1, max_attempts + 1):
        desc = generate_fn(niche, topic, title, episode, chapters_text, audio_duration)
        if not desc:
            continue
        _norm = " ".join(str(desc).lower().split())
        if _norm in _seen_desc:
            print("  Description call %d returned the same text — not a "
                  "new attempt." % _call)
            continue
        _seen_desc.add(_norm)
        _real += 1
        score, missing = score_description(desc, title, niche_name)
        if score > best_score:
            best_desc, best_score, best_missing = desc, score, missing
        if score >= min_score:
            return {"description": desc, "score": score, "missing": [],
                    "hit_target": True, "attempts": _real}
    # Report the attempts really made. Returning max_attempts here was the
    # same false progress the repeat-skip above exists to stop: one
    # description generated four times logged as "4 attempts".
    return {"description": best_desc, "score": best_score, "missing": best_missing,
            "hit_target": False, "attempts": _real}


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
    set_current_gate("shorts")
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
    _delivered = _tg_send_message_with_buttons(tg_token, tg_chat, "\n".join(lines), include_swap_visuals=True)

    if gmail_app_password:
        html_body = f"<p>{schedule_line}</p><p>Shorts published:</p><ul>" + \
                    "".join(f"<li>{s['name']}"
                            f"{' — quality score: ' + str(s['score']) + '/10' if s.get('score') is not None else ''}"
                            f": {s['url']}</li>" for s in shorts_list) + "</ul>"
        send_email_notification(f"[{channel_name}] Shorts ready for review", html_body,
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "cancel":
        # CANCEL means stop, at every gate, not just the final one. It is
        # never folded into approve and never treated as a soft "reject" that
        # quietly carries on to the next stage.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. This episode is being abandoned — nothing "
                         "further is generated and nothing is published.")
        return {"decision": "cancel", "feedback": feedback}
    if _no_human_reply(decision):
        decision = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what=_CURRENT_GATE[0] or "this checkpoint")
    return {"decision": decision, "feedback": feedback}


def _community_tab_keyboard():
    """
    Real inline keyboard for the COMMUNITY_TAB checkpoint — deliberately
    NOT the shared APPROVE/REJECT labels from _button_keyboard, since this
    checkpoint isn't approving generated content, it's confirming a real-
    world manual action. Reuses the same callback_data values ("approve"/
    "reject") _poll_for_decision already recognizes, so no change to that
    shared polling logic is needed.
    """
    return {"inline_keyboard": [[
        {"text": "✅ POSTED IT", "callback_data": "approve"},
        {"text": "⏭️ SKIP THIS EPISODE", "callback_data": "reject"},
    ]]}


COMMUNITY_POST_MIN = 7.5
COMMUNITY_POST_ATTEMPTS = 13


def score_community_post(question, options, topic, title):
    """
    Score a Community Tab draft. There was NO gate on this at all.

    Direct report after run 30717615638: "it's quite generic, not up to the
    mark, and didn't even clear that quality score." There was no quality
    score to clear — the draft was generated once, unscored, and sent
    straight to the review checkpoint. This is that score.

    What earns points is being about THIS case: a question that borrows a
    concrete detail from the topic, real candidate options rather than
    reaction words, and the diagnostic framing that makes a case poll worth
    voting on. What loses points is the filler this replaces.
    """
    q = (question or "").strip()
    opts = [o for o in (options or []) if str(o).strip()]
    if not q:
        return 0.0, ["no question"]
    issues = []
    sc = 3.0

    # THE OLD SCORE COULD REACH 9/10 ON A QUESTION WITH NOTHING IN IT.
    #
    # Run 31156373254's post scored 9.0 on the first attempt and cleared the
    # bar, and the reply was "I had requested that you give me the proper
    # details, yet I see that it's generic or vague." Both are true, because
    # the old rubric handed out +2.0 for sharing ANY word longer than four
    # characters with the topic -- and the topic is a whole clinical case, so
    # "patient", "diagnosis" or "symptoms" cleared it. Add a digit anywhere, a
    # question mark, two options, and a post that says nothing scored nine.
    #
    # What a case poll needs is an ANCHOR: a number with a unit, a length of
    # time, a named test, a specific finding. Something a viewer could not
    # have written without watching. That is what is measured now.
    GENERIC = ("what's your take", "what do you think", "drop your theory",
               "let us know", "comment below", "how do you feel",
               "which was most shocking", "did you know", "who else",
               "can you believe", "your thoughts", "sound off", "agree?",
               "what would you do", "have you ever", "crazy right",
               "what surprised you", "which part")
    if any(g in q.lower() for g in GENERIC):
        sc -= 3.0
        issues.append("generic filler question")

    # A concrete anchor, in the question or in the options -- either is fine,
    # a poll is read as one object.
    blob = " ".join([q] + [str(o) for o in opts]).lower()
    anchors = 0
    if re.search(r"\d+\s*(mg|ml|mmol|mcg|g/dl|mm|cm|kg|%|hours?|days?|weeks?|"
                 r"months?|years?|beats|degrees)", blob):
        anchors += 2                       # a real measured value
    elif re.search(r"\b\d+\b", blob):
        anchors += 1                       # a bare number: better than none
    NAMED = ("ct", "mri", "biopsy", "ecg", "eeg", "ultrasound", "x-ray",
             "endoscopy", "culture", "serology", "panel", "scan", "bloods",
             "lumbar", "angiogram", "histology", "marrow", "genetic")
    if any(re.search(r"\b%s\b" % t, blob) for t in NAMED):
        anchors += 1
    if anchors == 0:
        issues.append("nothing concrete — no value, no duration, no named test")
    sc += min(3.0, anchors * 1.2)

    # And it still has to be about THIS case, not clinical medicine generally.
    stop = {"the","a","an","and","or","of","in","on","for","with","was","were",
            "had","has","after","from","that","this","which","who","what",
            "patient","patients","doctor","doctors","case","cases","medical",
            "symptom","symptoms","diagnosis","diagnosed","hospital","test",
            "tests","clinical","treatment","condition","disease"}
    topic_words = {w.strip(".,:;()").lower() for w in f"{topic} {title}".split()
                   if len(w) > 4 and w.lower() not in stop}
    shared = topic_words & {w.strip(".,:;()?").lower() for w in blob.split()}
    if shared:
        sc += 1.5
    else:
        issues.append("shares no distinctive term with this case "
                      "(common clinical words do not count)")

    if q.rstrip().endswith("?"):
        sc += 0.5
    if len(q) <= 100:
        sc += 0.5
    else:
        issues.append("question over 100 chars")

    if len(opts) >= 2:
        sc += 1.0
        if all(len(str(o)) <= 30 for o in opts):
            sc += 0.5
        else:
            issues.append("an option is over 30 chars")
        if len(set(str(o).lower() for o in opts)) < len(opts):
            sc -= 1.0
            issues.append("duplicate options")
        # Options must be candidate ANSWERS, not reactions. "Shocking" and
        # "Unbelievable" are not things anyone was considering in the room.
        REACTION = ("shocking", "unbelievable", "wow", "crazy", "sad", "scary",
                    "amazing", "terrible", "awful", "insane", "other",
                    "not sure", "no idea", "don't know", "all of the above")
        if any(str(o).strip().lower() in REACTION for o in opts):
            sc -= 1.5
            issues.append("an option is a reaction, not a candidate answer")
    else:
        issues.append("fewer than 2 poll options")

    return round(max(0.0, min(10.0, sc)), 1), issues


def draft_community_post(topic, niche_name, title, ai_fn):
    """
    Drafts a YouTube Community Tab post/poll for this episode via the
    channel's own AI provider chain (passed in as ai_fn, same convention
    as add_topic_candidate elsewhere in this codebase) — a short
    engagement question plus up to 4 poll options, grounded in the real
    episode topic rather than generic "what do you think?" filler.

    Returns {"question": str, "options": [str, ...]}, or {} when there is
    nothing worth posting.

    THE FALLBACK WAS THE THING THE GATE EXISTS TO REJECT.
    -----------------------------------------------------
    What used to sit here, used whenever ai_fn was missing, the drafting
    threw, or all thirteen attempts came back unparseable:

        "What's your take on <title>? Drop your theory below."

    score_community_post lists BOTH "what's your take" and "drop your
    theory" in its GENERIC filler list. Scored against a real case it
    returns 4.4/10 against a 7.5 bar. So the one draft that could never
    clear the gate was also the only draft that never had to face it --
    and being the failure path, it is what shipped precisely on the bad
    days. That is the generic Community post being reported.

    Nothing is a valid answer here. Unlike a video, this post is pasted by
    hand, so a skipped episode costs one optional post; a generic one is
    published under the channel's name and stays there.
    """
    if not ai_fn:
        return {}

    # THIRTEEN ATTEMPTS, ONE QUESTION.
    #
    # The loop below was already a real gate -- scored, budgeted, honest about
    # its best draft. What it was not was thirteen ATTEMPTS: _generate_once
    # took no varying input, so every pass sent byte-identical text to the
    # provider and got the provider's most likely answer back, which is the
    # answer that just failed. Exactly the shape that produced thirteen
    # identical 5.5/10 lines in the thumbnail gate. The ledger is what makes
    # attempt two different from attempt one: the rejected question goes into
    # the next prompt by name, and a draft that comes back the same anyway
    # does not get to spend one of the attempts.
    #
    # Imported here rather than at module scope, matching how job_clock is
    # imported throughout this file: video_pipeline is a directory on
    # sys.path, not a package, so a sibling import only resolves once the
    # caller has set the path up. Deliberately NOT wrapped in a try/except --
    # a missing ledger must be a loud failure, not a gate that quietly goes
    # back to asking the same question thirteen times.
    from retry_variation import AttemptLedger
    _post_ledger = AttemptLedger(label="community post", near=0.8)

    def _generate_once(avoid=""):
        raw = ai_fn(
            f"""Write ONE YouTube Community Tab poll for a published clinical
case documentary titled "{title}".

THE CASE: {topic}

The poll must be about THIS case, not about the channel and not about
documentaries in general. "What's your take?" and "Which was most shocking?"
are the generic filler this is replacing — a viewer who has not watched the
episode should still find the question interesting, and a viewer who has
should feel it was worth voting on.

The strongest form for a case report is the DIAGNOSTIC one: put the reader in
the room before the answer was known, and let the options be the candidates
that were genuinely on the table.

Good shapes:
  "Every scan was normal. What would you have tested next?"
  "Twelve days, four specialists, no diagnosis. Where would you have looked?"
  "Which of these was the finding that finally explained it?"

Rules:
- Options are real clinical possibilities from THIS case, not jokes.
- No medical advice, and nothing a viewer could act on for themselves.
- Never suggest anyone concealed, neglected or mishandled anything.
- Do not reveal the answer in the question.

Format your response EXACTLY as:
QUESTION: <under 100 chars, specific to this case>
OPTION1: <short option, under 30 chars>
OPTION2: <short option, under 30 chars>
OPTION3: <short option, under 30 chars — or blank if only 2 make sense>
OPTION4: <short option, under 30 chars — or blank>

No markdown, no extra commentary — just those lines.{avoid}""",
            min_chars=40,
        )
        if not raw:
            return None
        question = ""
        options = []
        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("QUESTION:"):
                question = line.split(":", 1)[1].strip()[:100]
            elif line.upper().startswith("OPTION"):
                val = line.split(":", 1)[1].strip()[:30] if ":" in line else ""
                if val:
                    options.append(val)
        if not question:
            return None
        return {"question": question, "options": options[:4]}

    try:
        # ONE ATTEMPT AND ONE REWORK IS NOT A GATE.
        #
        # This drafted once, ran an AI-judge read, and if that failed tried
        # exactly once more — then used whatever it had, scored or not. Run
        # 30717615638's post was generic and, in the reporter's words,
        # "didn't even clear that quality score". It did not have to: nothing
        # here could reject it. Now it is scored on every attempt against a
        # real bar, keeps the best draft seen, and only falls back to the
        # template after the full budget is spent.
        best, best_score, best_issues = None, -1.0, []
        _attempt = 0
        _wasted = 0          # repeats, which do not count as attempts
        _MAX_WASTED = 6      # but cannot loop forever either
        while _attempt < COMMUNITY_POST_ATTEMPTS:
            result = _generate_once(_post_ledger.avoid_clause(what="poll question"))
            if not result:
                _attempt += 1
                continue
            _q = result.get("question") or ""
            if _post_ledger.is_repeat(_q):
                _wasted += 1
                print("  Community post: same question as one already "
                      f"rejected — not counting it as an attempt ({_wasted}/"
                      f"{_MAX_WASTED}).")
                if _wasted >= _MAX_WASTED:
                    print("  Community post: the provider keeps returning the "
                          "same question — stopping instead of burning the "
                          "budget on one draft.")
                    break
                continue
            _attempt += 1
            _sc, _issues = score_community_post(result.get("question"),
                                                result.get("options"),
                                                topic, title)
            if _sc > best_score:
                best, best_score, best_issues = result, _sc, _issues
            print(f"  Community post attempt {_attempt}/"
                  f"{COMMUNITY_POST_ATTEMPTS}: {_sc}/10"
                  + (f" — {'; '.join(_issues[:2])}" if _issues else ""))
            if _sc >= COMMUNITY_POST_MIN:
                # An independent judge on top of the mechanical score, kept
                # from the previous implementation but no longer the only
                # thing standing between a generic post and the channel.
                try:
                    from quality_auditor import audit_content
                    _content = result["question"] + (
                        " | " + " / ".join(result["options"])
                        if result["options"] else "")
                    _audit = audit_content("community_post", _content, "",
                                           ai_fn, topic=topic)
                    if not _audit["passed"]:
                        print("  Community post cleared the score but the "
                              "AI judge disagreed — trying again.")
                        _post_ledger.note(_q, _sc)
                        continue
                except Exception:
                    pass
                print(f"  Community post cleared {COMMUNITY_POST_MIN}/10 on "
                      f"attempt {_attempt}.")
                return result
            # Below the bar: name it in the next prompt, so the next attempt
            # is asked for a different question rather than the same one.
            _post_ledger.note(_q, _sc)
        if best is not None:
            # Report the attempts REALLY made, not the budget. Saying "13
            # attempts" when the provider gave one draft twelve times over is
            # the same false progress the ledger exists to stop.
            print(f"  Community post never cleared {COMMUNITY_POST_MIN}/10 in "
                  f"{_attempt} attempts (best {best_score}/10: "
                  f"{'; '.join(best_issues[:3])}). Sending the best draft to "
                  f"review, flagged, rather than a template.")
            best["below_bar"] = True
            best["score"] = best_score
            best["issues"] = best_issues[:3]
            return best
        print("  Community post: nothing usable in "
              f"{COMMUNITY_POST_ATTEMPTS} attempts — skipping the post rather "
              "than sending generic filler to be published.")
        return {}
    except Exception as e:
        print(f"  Community post drafting failed ({e}) — skipping.")
        return {}


def review_community_tab(channel_name, question, options, tg_token, tg_chat,
                          check_ins_used=0, gmail_sender=None, gmail_app_password=None,
                          timeout_minutes=60, below_bar=False, score=None,
                          issues=()):
    """
    THE COMMUNITY TAB CHECKPOINT.

    HONEST CONSTRAINT, stated plainly: YouTube's public Data API v3 has no
    endpoint to create a Community Tab post or poll, or to read poll
    responses — verified directly against Google's own API reference,
    not assumed. There is no way for this pipeline to post it directly.

    Per explicit decision on how to handle that gap: this drafts the real
    post/poll content and sends it to Telegram with the exact text to
    post, asking the person to post it to the Community tab themselves
    and tap POSTED IT once done (or SKIP THIS EPISODE to skip). This is a
    genuine gate, not a fire-and-forget notification — the pipeline
    actually waits on the reply, the same way every other checkpoint in
    this file does.

    Deliberately does NOT auto-"POSTED" on timeout the way content
    checkpoints auto-approve — posting to the Community tab is a real
    real-world action nobody can confirm happened just because time ran
    out, so a timeout here resolves to "skip" instead.

    Returns {"decision": "posted"|"skip", "feedback": None}.
    """
    set_current_gate("community tab")
    schedule_line = get_schedule_line(check_ins_used)
    lines = [f"📢 {channel_name} — COMMUNITY TAB POST\n\n{schedule_line}\n"]
    # SAY SO WHEN THE DRAFT FAILED ITS OWN GATE.
    #
    # draft_community_post sets below_bar/score on a draft that never
    # cleared COMMUNITY_POST_MIN, and this function never had a parameter
    # to receive them -- the call site read "question" and "options" and
    # dropped the rest. The reviewer was asked to publish a draft the
    # pipeline had already judged inadequate, with nothing on screen
    # saying so, which makes the flag worse than useless: it looks like
    # the post was checked.
    if below_bar:
        _det = " (best of %d attempts: %s/10, bar %s)" % (
            COMMUNITY_POST_ATTEMPTS,
            score if score is not None else "?", COMMUNITY_POST_MIN)
        lines.append("⚠️ <b>THIS DRAFT DID NOT PASS THE QUALITY GATE</b>"
                     + _esc(_det))
        if issues:
            lines.append("Why: " + _esc("; ".join(str(i) for i in issues)))
        lines.append("Post it only if you think it is good enough. "
                     "SKIP is the safe choice.\n")
    lines += ["Post this to the Community tab now:\n",
              f"<b>{_esc(question)}</b>"]
    if options:
        lines.append("Poll options:")
        lines.extend(f"  {i+1}. {_esc(o)}" for i, o in enumerate(options))
    else:
        lines.append("(text post — no poll options, ask people to reply in comments)")
    lines.append("\nTap POSTED IT once it's live on the Community tab, or SKIP THIS EPISODE to skip.")
    text = "\n".join(lines)

    _delivered = send_with_keyboard(tg_token, tg_chat, text,
                                    _community_tab_keyboard())

    if gmail_app_password:
        html_body = f"<p>{schedule_line}</p><p>Post this to the Community tab:</p><p><b>{_esc(question)}</b></p>"
        if options:
            html_body += "<ul>" + "".join(f"<li>{_esc(o)}</li>" for o in options) + "</ul>"
        send_email_notification(f"[{channel_name}] Community Tab post ready", html_body,
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes,
                                             gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision in ("approve",):
        decision = "posted"
    else:
        # timeout, reject, or anything else this checkpoint doesn't
        # recognize — all resolve to "skip" rather than assuming success.
        if _no_human_reply(decision):
            _tg_send_message(tg_token, tg_chat,
                              f"⏱️ {timeout_minutes} min expired — treating as skipped "
                              f"(can't confirm a real-world post happened).")
        decision = "skip"
    return {"decision": decision, "feedback": feedback}


def review_thumbnail(channel_name, thumbnail_path, title, tg_token, tg_chat,
                      gmail_sender=None, gmail_app_password=None, timeout_minutes=60):
    """
    Real checkpoint: sends the actual generated thumbnail image. EDIT
    feedback here gets passed straight back to the caller, which
    regenerates the thumbnail with that feedback folded into the real
    AI image prompt — not a cosmetic re-roll, an actual instructed retry.
    """
    set_current_gate("thumbnail")
    # FIX (direct user report, July 24 2026 — "the Telegram options and
    # buttons... are not clickable right now"): this checkpoint sent a
    # plain photo with instructions to TYPE a reply and never mentioned
    # REMAKE at all — no real tappable buttons, unlike the script/audio/
    # video checkpoints which all have them. If this was the checkpoint
    # the user was on, there was no button to tap in the first place.
    # Now uses the same real inline-keyboard buttons as everywhere else.
    caption = f"🖼️ {channel_name} — THUMBNAIL REVIEW\nTitle: {title}"
    _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption=caption,
                   reply_markup=_button_keyboard())

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Thumbnail ready for review",
                                 f"<p>Thumbnail for: <b>{_esc(title)}</b><br>Check Telegram to view it.</p>",
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "cancel":
        # CANCEL means stop, at every gate, not just the final one. It is
        # never folded into approve and never treated as a soft "reject" that
        # quietly carries on to the next stage.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. This episode is being abandoned — nothing "
                         "further is generated and nothing is published.")
        return {"decision": "cancel", "feedback": feedback}
    if _no_human_reply(decision):
        decision = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what=_CURRENT_GATE[0] or "this checkpoint")
    return {"decision": decision, "feedback": feedback}


def review_title(channel_name, title, alternate_titles, tg_token, tg_chat,
                  gmail_sender=None, gmail_app_password=None, timeout_minutes=60):
    """
    Real checkpoint for the title specifically — shows the winning title
    plus the real runner-up options that were actually scored, so EDIT
    feedback can reference something concrete ("use option 2 instead" is
    directly actionable) rather than guessing blind.
    """
    set_current_gate("title")
    # FIX (direct user report, July 24 2026 — same fix as review_thumbnail
    # above): this checkpoint had no real buttons either — plain text
    # only, and REMAKE wasn't even mentioned as an option.
    alt_text = "\n".join(f"  {i+1}. {_esc(t)}" for i, t in enumerate(alternate_titles[:3]))
    text = (f"🏷️ {channel_name} — TITLE REVIEW\n\nSelected: {_esc(title)}\n\n"
            f"Other real options that were scored:\n{alt_text}\n\n"
            f"Or tap EDIT and reply with which option to use (e.g. \"use option 2\")")
    _delivered = _tg_send_message_with_buttons(tg_token, tg_chat, text)

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Title ready for review",
                                 f"<p>Selected: <b>{_esc(title)}</b></p><p>Alternatives:<br>{alt_text}</p>",
                                 gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if decision == "cancel":
        # CANCEL means stop, at every gate, not just the final one. It is
        # never folded into approve and never treated as a soft "reject" that
        # quietly carries on to the next stage.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. This episode is being abandoned — nothing "
                         "further is generated and nothing is published.")
        return {"decision": "cancel", "feedback": feedback}
    if _no_human_reply(decision):
        decision = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what=_CURRENT_GATE[0] or "this checkpoint")
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
        # FIX (direct user report, July 25 2026 — real bug found via
        # fingerprint_history.json: a past episode's logged opening
        # sentence was literally "Stage 4: The Investigation Deepens...").
        # The normal Stage 1 generation path (master_pipeline.py's
        # run_stage1) always strips leaked "Stage N: <title>" headers via
        # strip_all_leaked_stage_headers before script_clean is used
        # anywhere -- this human-feedback EDIT path never did, because it
        # returns the AI's raw rewrite untouched. An LLM asked to "rewrite
        # the entire script" from a script that itself still shows visible
        # stage structure readily echoes a header back verbatim, and here
        # nothing ever caught it -- a genuinely broken, generic-sounding
        # opening could reach the real narration whenever a whole-script
        # EDIT was used.
        from script_scoring import strip_all_leaked_stage_headers
        return strip_all_leaked_stage_headers(new_script.strip()), {}

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
        # FIX (direct user report, July 25 2026 — same real leaked-header
        # bug as the whole-script path above): a per-section rewrite is
        # just as capable of echoing "SECTION BEING REWRITTEN: Stage 4"
        # back into its own output as the whole-script path is.
        from script_scoring import strip_all_leaked_stage_headers
        new_section = strip_all_leaked_stage_headers(new_section.strip())
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
    set_current_gate("script")
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
    _delivered = _tg_send_message_with_buttons(tg_token, tg_chat, header)

    # FIX (found on direct user report, July 23 2026): a long wall of
    # chunked text messages ("cutting down the paragraphs") is genuinely
    # unreadable and doesn't invite anyone to actually read the script.
    # A real PDF is the primary experience now — opens in the reader's
    # own PDF viewer, properly formatted with stage headers. The old
    # chunked-text send only runs as a fallback if the PDF export or
    # send fails for any reason (e.g. reportlab not installed), so the
    # actual script is never silently withheld from review either way.
    pdf_path = export_script_to_pdf(channel_name, title, niche_name, score, full_script,
                                     stage_texts=stage_texts, stage_names=stage_names,
                                     thumbnail_text=thumbnail_text, tags=tags)
    pdf_sent = False
    if pdf_path:
        pdf_sent = _tg_send_document(tg_token, tg_chat, pdf_path,
                                      caption=f"📄 Full script — {title} ({len(full_script.split())} words)")
    if not pdf_sent:
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
    if decision == "cancel":
        # CANCEL means stop, at every gate, not just the final one. It is
        # never folded into approve and never treated as a soft "reject" that
        # quietly carries on to the next stage.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. This episode is being abandoned — nothing "
                         "further is generated and nothing is published.")
        return {"decision": "cancel", "feedback": feedback}
    if _no_human_reply(decision):
        decision = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what=_CURRENT_GATE[0] or "this checkpoint")
    return {"decision": decision, "feedback": feedback}


def review_audio_and_video(channel_name, audio_path, voice_used, video_path, thumbnail_path,
                            tg_token, tg_chat, check_ins_used=0, gmail_sender=None,
                            gmail_app_password=None, timeout_minutes=60, preview_seconds=60,
                            audio_score=None, audio_score_breakdown=None,
                            video_score=None, video_score_breakdown=None,
                            yt_preview_url=None):
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

    FIX (found on direct user request, July 23 2026): yt_preview_url,
    when given, is the real full-length YouTube link for this exact
    video (the caller uploads it unlisted right before calling this,
    same pattern as the final pre-publish gate) — included directly in
    the video caption. This is the ONLY way to genuinely watch the whole
    thing at this checkpoint: the 60s preview clip below is still
    attempted for a quick in-Telegram look, but a long or high-bitrate
    video routinely exceeds Telegram's real ~50MB bot upload limit even
    for just those 60 seconds (confirmed live), while the real YouTube
    link has no such limit.
    """
    set_current_gate("audio+video")
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
    # THE AUDIO GATE USED TO DISAPPEAR ENTIRELY WHEN THE FILE WAS BIG.
    #
    # The decision buttons ride on the sendAudio call. If that send failed --
    # and an eighteen-minute narration routinely exceeds Telegram's ~50MB bot
    # upload limit -- the old code sent a plain notice with NO buttons and
    # then set the decision to "approve" without polling at all. Not a
    # timeout, not a fallback: the audio review simply did not happen, and
    # the reviewer never saw a single button for it. Reported exactly that
    # way: no workable buttons for the audio stage.
    #
    # The video half of this same function already solved this correctly a
    # while ago -- trim a preview, and if that cannot be sent either, fall
    # back to a TEXT message that still carries the buttons. Audio never got
    # the same treatment. It does now, and there is no path here that
    # approves anything without a human tapping something.
    sent = _tg_send_audio(tg_token, tg_chat, audio_path, caption=audio_caption,
                          reply_markup=_button_keyboard(fifth_option=("🎙️ SWAP VOICE", "swap_voice")))
    _delivered = bool(sent)
    if not sent:
        # 1. A short excerpt is usually sendable even when the full file is
        #    not, and hearing 90 seconds of the voice is the whole point of
        #    this checkpoint.
        _clip = str(Path(audio_path).parent / "review_audio_excerpt.mp3")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-t", "90",
                            "-c:a", "libmp3lame", "-b:a", "96k", _clip],
                           capture_output=True, timeout=180)
            _clip_ok = (Path(_clip).exists()
                        and 10_000 < Path(_clip).stat().st_size < 45_000_000)
        except Exception:
            _clip_ok = False
        if _clip_ok:
            sent = _tg_send_audio(
                tg_token, tg_chat, _clip,
                caption="⚠️ The full narration was too large for Telegram — "
                        "here is the first 90 seconds.\n\n" + audio_caption,
                reply_markup=_button_keyboard(
                    fifth_option=("🎙️ SWAP VOICE", "swap_voice")))
            _delivered = bool(sent)
    if not sent:
        # 2. Still no audio. Send the BUTTONS anyway on a text message, so
        #    the decision is always available to a human even when the file
        #    is not. Approving without hearing it is a choice the reviewer
        #    is allowed to make; it is not one the pipeline may make for
        #    them.
        _delivered = _tg_send_message_with_buttons(
            tg_token, tg_chat,
            f"⚠️ {channel_name} — AUDIO REVIEW (no playable file)\n\n"
            f"{schedule_line}\n\nThe narration could not be sent to Telegram "
            f"even as a 90-second excerpt — it is too large, or the send "
            f"failed.\n\nVoice tier: {voice_used}\n{audio_score_line}"
            f"Decide from the score, or REJECT/SWAP VOICE if you would "
            f"rather not approve audio you have not heard.",
            fifth_option=("🎙️ SWAP VOICE", "swap_voice"))
    # The reviewer now always has buttons in front of them, whichever
    # of the three delivery routes above succeeded.
    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Audio ready for review",
                                 f"<p>{schedule_line}</p><p>Voice tier: <b>{voice_used}</b></p>"
                                 f"{'<p>Audio quality score: ' + str(audio_score) + '/10</p>' if audio_score is not None else ''}"
                                 f"<p>Listen via Telegram — audio isn't emailed directly.</p>",
                                 gmail_sender, gmail_app_password)
    d, fb = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if _no_human_reply(d):
        d = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what="Audio review")
    audio_decision = {"decision": d, "feedback": fb}

    # ONLY AN EXPLICIT APPROVAL MAY OPEN THE VIDEO REVIEW.
    #
    # THIS IS THE "I DIDN'T GET THE AUDIO, IT DIRECTLY TOOK ME TO THE VIDEO"
    # BUG, AND IT WAS RIGHT HERE.
    #
    # The old test was a blocklist: stop for reject/remake/swap_voice, carry on
    # for anything else. But "anything else" includes hold-undelivered -- the
    # value resolve_silent_window returns when all three audio sends failed and
    # NOBODY WAS EVER ASKED. That is not in the blocklist, so the audio stage
    # fell through and the next thing the reviewer saw was the video gate. The
    # audio review had not been declined; it had never happened.
    #
    # A blocklist of decisions that stop is the wrong shape for this. Every new
    # decision value defaults to "proceed", so the failure mode of forgetting to
    # update it is silently skipping a checkpoint. Inverted: the gate proceeds
    # on approve and on nothing else, so a decision nobody anticipated holds the
    # episode instead of waving it through.
    if audio_decision["decision"] != "approve":
        if never_asked(audio_decision["decision"]):
            _tg_send_message(
                tg_token, tg_chat,
                "⛔ The audio review never reached you, so the video review is "
                "NOT being opened — you would have been approving a video "
                "built on narration you were never asked about. The episode is "
                "held at the audio stage and resumes from there.")
        return {"audio_decision": audio_decision, "video_decision": None}

    # VIDEO — real 5-option decision, the 5th being SWAP VISUALS
    preview_path = str(Path(video_path).parent / "review_preview_clip.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-t", str(preview_seconds),
                        "-c", "copy", preview_path], capture_output=True, timeout=120)
        # FIX (found on live Ch1 run — real bug): a 60s "-c copy" trim's
        # real size scales with the source's bitrate, not just its
        # duration — a long, high-bitrate final video (seen live: 1120MB
        # for ~16min, ~70MB for just the first 60s) can still land well
        # over Telegram's real ~50MB bot-upload cap even after a
        # genuinely correct trim. The old check only verified the file
        # existed and wasn't suspiciously tiny (>10KB) — never that it
        # was actually small enough to SEND. That guaranteed a doomed
        # _tg_send_video call (confirmed live: HTTP 413 Request Entity
        # Too Large) on any episode with an unusually large final video.
        _preview_size = Path(preview_path).stat().st_size if Path(preview_path).exists() else 0
        preview_ready = 10_000 < _preview_size < 45_000_000
    except Exception:
        preview_ready = False

    video_score_line = f"Video quality score: {video_score}/10{_breakdown_line(video_score_breakdown)}\n\n" if video_score is not None else ""
    yt_link_line = f"🔗 Full video (unlisted, watch/download anytime): {yt_preview_url}\n\n" if yt_preview_url else ""
    video_caption = (f"🎬 {channel_name} — VIDEO REVIEW\n\nFirst {preview_seconds}s preview below"
                     f"{' (or use the real link for the whole thing)' if yt_preview_url else ''}\n\n"
                     f"{yt_link_line}"
                     f"{video_score_line}"
                     f"Tap a button below — EDIT will ask what to change, "
                     f"SWAP VISUALS regenerates just the visuals, same script and audio")
    _video_sent = False
    if preview_ready:
        _video_sent = _tg_send_video(tg_token, tg_chat, preview_path, caption=video_caption,
                       reply_markup=_button_keyboard(fifth_option=("🎨 SWAP VISUALS", "swap_visuals")))
    # FIX (found on live Ch1 run — real bug): _tg_send_video's return
    # value was never checked here, unlike the equivalent audio path a
    # few lines above (which already has this exact safety net). Since
    # the decision BUTTONS are attached to this same sendVideo call, a
    # failed send (whether from the size check above or a genuine
    # Telegram-side rejection at send time) used to leave the reviewer
    # with only a bare thumbnail and zero way to tap a decision —
    # silently waiting out the full timeout on a message that was never
    # delivered, with no visible sign anything was expected of them.
    if not preview_ready or not _video_sent:
        _delivered = _tg_send_message_with_buttons(tg_token, tg_chat,
                         f"⚠️ {channel_name}: could not send a video preview "
                         f"(too large for Telegram's upload limit, or the send failed) "
                         f"— sending thumbnail only. Full video review happens at the "
                         f"final pre-publish gate before this goes public.\n\n{video_caption}",
                         include_swap_visuals=True)
    if thumbnail_path and Path(thumbnail_path).exists():
        _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption="Final thumbnail")

    if gmail_app_password:
        send_email_notification(f"[{channel_name}] Video ready for review",
                                 f"<p>Video assembled — preview sent to Telegram "
                                 f"({'clip attached' if _video_sent else 'clip unavailable, thumbnail only'}).</p>"
                                 f"{'<p>Video quality score: ' + str(video_score) + '/10</p>' if video_score is not None else ''}",
                                 gmail_sender, gmail_app_password)

    d, fb = _poll_for_decision(tg_token, tg_chat, timeout_minutes, gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if _no_human_reply(d):
        d = resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what="Video review")
    video_decision = {"decision": d, "feedback": fb}

    return {"audio_decision": audio_decision, "video_decision": video_decision}


def review_resume_checkpoint(channel_name, title, script_clean, score, niche_name,
                              audio_path, tool_used, voice_used, audio_duration,
                              tg_token, tg_chat, gmail_sender=None, gmail_app_password=None,
                              timeout_minutes=30):
    """
    Real human-in-the-loop gate for a checkpoint RESUME (workflow re-
    triggered with is_makeup=true after a cancelled/failed run). Per
    direct user request ("I need to check and find out if I am okay
    with that kind of script, the audio, or the title... I want a
    notification asking for my explicit permission"): a resume is never
    silent. This sends the real checkpointed script (as a PDF, same
    export_script_to_pdf already used for the normal script review) and
    the real accepted audio file (if a audio checkpoint exists too), then
    asks for one of three genuine decisions rather than just picking up
    automatically:
      - "resume": skip whatever already passed, continue to the next stage
      - "redo_audio_only": keep the checkpointed script+title, but
        discard the checkpointed audio and regenerate it fresh (only
        offered when an audio checkpoint exists)
      - "restart_scratch": discard the whole checkpoint, generate a
        brand new episode from Stage 1

    On timeout, defaults to "resume" — the least destructive option
    (keeps whatever already genuinely passed its own quality gate,
    consistent with every other gate in this file defaulting toward not
    discarding already-approved work).
    """
    set_current_gate("resume confirmation")
    has_audio = bool(audio_path and Path(audio_path).exists())
    lines = [
        f"⏸️ <b>{channel_name} — RESUMING FROM A PREVIOUS RUN</b>",
        "",
        "The last run got this far before stopping:",
        f"• Script + title: PASSED ({score}/10) — \"{title}\"",
    ]
    if has_audio:
        lines.append(f"• Audio: PASSED — tool: {tool_used}, voice: {voice_used}, "
                      f"{(audio_duration or 0)/60:.1f} min")
        lines.append("")
        lines.append("Review the script (PDF below) and audio (file below), then choose:")
    else:
        lines.append("")
        lines.append("Review the script (PDF below), then choose:")
    text = "\n".join(lines)

    pdf_path = None
    try:
        pdf_path = export_script_to_pdf(channel_name, title, niche_name, score, script_clean)
    except Exception as e:
        print(f"  Resume-checkpoint PDF export failed (non-fatal): {e}")
    if pdf_path and Path(pdf_path).exists():
        _tg_send_document(tg_token, tg_chat, pdf_path, caption=f"Checkpointed script: {title[:80]}")
    if has_audio:
        _tg_send_audio(tg_token, tg_chat, audio_path,
                       caption=f"Checkpointed audio — {tool_used}, voice {voice_used}")

    buttons = [[{"text": "▶️ RESUME (skip passed stages)", "callback_data": "resume"}]]
    if has_audio:
        buttons.append([{"text": "🎙️ REDO AUDIO ONLY (keep script+title)", "callback_data": "redo_audio_only"}])
    buttons.append([{"text": "🔄 RESTART FROM SCRATCH", "callback_data": "restart_scratch"}])

    _delivered = send_with_keyboard(tg_token, tg_chat, text,
                                    {"inline_keyboard": buttons})

    d, _ = _poll_for_decision(tg_token, tg_chat, timeout_minutes, max_attempts=2,
                              gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if _no_human_reply(d):
        _tg_send_message(tg_token, tg_chat,
                         f"⏱️ No decision within the review window — resuming automatically "
                         f"from the checkpoint (the least destructive option) so this "
                         f"doesn't sit stalled indefinitely.")
        return "resume"
    if d not in ("resume", "restart_scratch", "redo_audio_only"):
        return "resume"  # shouldn't happen given the whitelist, but fail safe
    return d


def review_final_video_before_publish(channel_name, yt_url, thumbnail_path,
                                       tg_token, tg_chat, check_ins_used=0,
                                       gmail_sender=None, gmail_app_password=None,
                                       timeout_minutes=60):
    """
    THE REAL FINAL GATE — built in direct response to the explicit request
    that nothing goes public without a chance to actually watch the whole
    thing first, even when the reviewer is away and never checks in time.

    HONEST DESIGN NOTE: the earlier review_audio_and_video() checkpoint
    only ever sent a 60-second preview clip, because Telegram's bot API
    has a real ~50MB upload cap — the full 15-18 minute video routinely
    exceeds that. There is no way to send the actual video FILE through
    Telegram at full length. The real fix: the caller uploads the
    finished video to YouTube as UNLISTED first (viewable/downloadable
    by anyone with the exact link, not searchable, not public yet) —
    this sends that real link so the whole thing can be watched or
    downloaded and judged in full, with zero size limit, before it ever
    goes public. Approving here does not re-upload anything — the
    caller flips the same already-uploaded video's privacyStatus to
    "public" via a metadata-only YouTube API call.

    Real decision handling:
      APPROVE (or the {timeout_minutes}-min timeout) -> caller flips the
        video to public, exactly as-is.
      REJECT / REMAKE / EDIT -> all treated the same at this final
        stage (there's no more text left to "edit", the video is fully
        rendered) -- the caller deletes the unlisted upload and produces
        a genuinely fresh episode on the next cycle instead, carrying
        forward any real feedback text given.

    Returns {"decision": "approve"|"regenerate", "feedback": str or None}.
    """
    set_current_gate("final pre-publish")
    schedule_line = get_schedule_line(check_ins_used)
    caption = (f"🎬 {channel_name} — FINAL VIDEO, READY TO GO PUBLIC\n\n{schedule_line}\n\n"
               f"Full video (unlisted — not public yet, viewable/downloadable "
               f"by anyone with this exact link):\n{yt_url}\n\n"
               f"Watch or download the whole thing, then decide:\n"
               f"Tap a button below — auto-approves and goes PUBLIC in "
               f"{timeout_minutes} min if untouched")
    _delivered = _tg_send_message_with_buttons(tg_token, tg_chat, caption)
    if thumbnail_path and Path(thumbnail_path).exists():
        _tg_send_photo(tg_token, tg_chat, thumbnail_path, caption="Final thumbnail")

    if gmail_app_password:
        html_body = (f"<p>{schedule_line}</p>"
                     f"<p>Full unlisted video, ready to review before it goes public:<br>"
                     f"<a href='{yt_url}'>{yt_url}</a></p>")
        send_email_notification(f"[{channel_name}] Final video ready — approve to publish",
                                 html_body, gmail_sender, gmail_app_password)

    decision, feedback = _poll_for_decision(tg_token, tg_chat, timeout_minutes,
                                             gmail_sender=gmail_sender, gmail_app_password=gmail_app_password)
    if _no_human_reply(decision):
        # The last gate before the world sees it. If the ask never landed,
        # holding is the only defensible reading of silence.
        return {"decision": resolve_silent_window(
            locals().get("_delivered", False), tg_token, tg_chat,
            timeout_minutes, what="Final pre-publish review"),
            "feedback": None}
    if decision == "approve":
        return {"decision": "approve", "feedback": None}
    if decision == "cancel":
        # The exact instruction this gate failed to honour on run
        # 31156373254. Cancel is not "make me another one" -- it is stop.
        _tg_send_message(tg_token, tg_chat,
                         "🛑 Cancelled. The unlisted upload is being deleted and "
                         "NOTHING will be published. No replacement episode is "
                         "generated — you asked for it to stop, so it stops.")
        return {"decision": "cancel", "feedback": feedback}
    _tg_send_message(tg_token, tg_chat,
                     "🔄 Not approved — this unlisted upload is being removed. "
                     "A fresh episode will be generated on the next cycle instead.")
    return {"decision": "regenerate", "feedback": feedback}

# FIX (found on re-audit, before building anything on top of this file):
# the lines that used to follow here were dead, unreachable code —
# leftover from a copy-paste, sitting after the real `return` above.
# Removed; they never executed and pyflakes-style analysis wouldn't
# catch this specific class of mistake (unreachable-but-valid code),
# only a real line-by-line read does.


def notify_degraded(what, detail):
    """
    Tell the human that this episode is missing something, before they
    approve it.

    A degraded episode used to be indistinguishable from a healthy one at
    the review checkpoint. Run 30717615638 reported SUCCESS while shipping
    with ZERO of its case report's real figures -- the FIGURE register, the
    largest share of the visual mix, had silently failed on every episode
    this channel has ever produced -- and the only evidence was one line in
    a 2400-line console log that nobody reads during an approval.

    Whoever taps Approve should know what they are approving.
    """
    msg = (f"⚠️ DEGRADED: {what}\n\n{detail}\n\n"
           f"The episode still completed; this is a heads-up about what it "
           f"is missing, not a failure.")
    try:
        tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "")
        if tg_token and tg_chat:
            _tg_send_message(tg_token, tg_chat, msg)
    except Exception as e:
        print(f"  Degraded-notice send failed (non-fatal): {e}")
    print(f"  DEGRADED — {what}: {detail}")
