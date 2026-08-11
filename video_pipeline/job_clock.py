"""
JOB CLOCK — one wall-clock, shared by every loop that can spend an hour.

WHY THIS EXISTS
---------------
Run 30688297894 was not killed by a crash or a bad gate decision. It was
killed by GitHub Actions' 6-hour hosted-runner limit, at 5h58m, partway
through a sixth video reassembly. Everything it had built up to that point
-- an 8.9 script, an approved title, a 9.1 audio track, five finished
1080p videos -- died with the runner, because a cancelled job commits
nothing.

Nothing in the pipeline knew what time it was.

Each expensive loop had its own private notion of "how many attempts are
reasonable" and none of them had any notion of "how much of the job's
6 hours is left". The video gate was configured for 13 attempts at ~48
minutes each: 10.4 hours of work inside a 6-hour box. The review gate had
a 4.5-hour budget that started counting at the FIRST review checkpoint, so
however long generation had already taken, review still believed it owned
another 4.5 hours. Add ~1h50m of real work to a full review window and the
job is over the wall before the last checkpoint closes.

Both were locally sensible and jointly impossible. This module is the
missing shared fact: how long the job has been running, how long it has
left, and whether one more expensive thing fits.

THE CONTRACT
------------
  * `elapsed_minutes()` / `remaining_minutes()` -- against the real job
    limit, anchored to the job's own start (JOB_START_EPOCH, exported by
    the workflow) rather than to whenever some module happened to be
    imported.
  * `can_afford(minutes)` -- "is there room for one more attempt that
    costs about this much, AND still room to finish afterwards?" Called
    BEFORE starting the attempt, so the answer is actionable.
  * `review_budget_hours(cap)` -- the review window, shrunk by whatever
    generation has already spent. Never larger than the caller's cap.

Every number is overridable by environment variable so a TEST run does not
have to inherit production's six-hour arithmetic.

WHY A RESERVE
-------------
Clearing the video gate is not the end of the job. Thumbnails, title,
description, Shorts, artifact upload and the checkpoint commit all still
have to happen, and the checkpoint commit is the one that makes tomorrow's
make-up run cheap instead of starting from nothing. `can_afford` therefore
withholds RESERVE_MIN from every caller: a run that spends its last minute
on a sixth reassembly saves nothing, while a run that stops with 45 minutes
in hand keeps its script, title and audio and resumes straight into video.
"""

import datetime
import os
import time


def _env_float(name, default):
    try:
        v = float(os.environ.get(name, "").strip())
        return v if v > 0 else default
    except (TypeError, ValueError, AttributeError):
        return default


# The workflow's own `timeout-minutes: 360`, which is itself GitHub's
# hosted-runner ceiling. Kept in an env var so the two cannot drift apart
# silently: the workflow exports the same number it declares.
JOB_LIMIT_MINUTES = _env_float("JOB_LIMIT_MINUTES", 360.0)

# Withheld from every affordability question. Sized for what still has to
# happen after the last expensive gate clears: Shorts render, thumbnail
# variants, description, artifact upload, checkpoint commit.
RESERVE_MIN = _env_float("JOB_RESERVE_MIN", 45.0)

# THE REVIEW WINDOW IS NOT SPARE TIME. IT IS RESERVED TIME.
#
# FIX (direct user report, with screenshots): generation was allowed to run
# until only RESERVE_MIN remained, and RESERVE_MIN covers finalisation only —
# Shorts, thumbnail, description, artifact upload. Nothing was set aside for
# the human review gates at all. So a long generate phase left each gate a
# share of roughly zero, the gate refused to open ("no buttons were sent"),
# and the stage shipped unreviewed. The reviewer was then told the stage
# "PROCEEDED AS GENERATED and was NOT approved by you", which correctly
# describes a situation that should never have been reachable.
#
# A gate needs a window a person can actually answer in. Six gates at twelve
# minutes is 72 minutes, and generation must stop before it eats them, not
# after. Stopping early costs one run; shipping unreviewed costs trust.
MIN_GATE_MIN = _env_float("JOB_MIN_GATE_MIN", 12.0)
GATES_PER_EPISODE = _env_float("JOB_GATES_PER_EPISODE", 6.0)


def review_floor_minutes(gates_left=None):
    """Minutes that must survive generation so every remaining gate can open."""
    n = GATES_PER_EPISODE if gates_left is None else float(gates_left)
    return max(0.0, n) * MIN_GATE_MIN


def generation_may_continue(gates_left=None):
    """False once more generation would eat a gate's minimum window."""
    return remaining_minutes() > RESERVE_MIN + review_floor_minutes(gates_left)


def _job_start():
    """
    The real start of the JOB, not of this module.

    The pipeline imports its modules lazily -- human_review_gate is first
    imported at the script checkpoint, roughly an hour in -- so import time
    is a badly wrong anchor, and wrong in the dangerous direction: it makes
    every module believe the job is younger than it is. The workflow exports
    JOB_START_EPOCH in its first step; import time is only the fallback for
    running outside Actions.
    """
    raw = os.environ.get("JOB_START_EPOCH", "").strip()
    if raw:
        try:
            ts = float(raw)
            # Sanity: a stale or malformed value that claims the job started
            # days ago would make everything instantly "unaffordable" and
            # silently skip the episode. Only trust a plausible timestamp.
            age_min = (time.time() - ts) / 60.0
            if -5 <= age_min <= JOB_LIMIT_MINUTES + 120:
                return ts
        except (TypeError, ValueError):
            pass
    return _IMPORT_TIME


_IMPORT_TIME = time.time()


def elapsed_minutes():
    return max(0.0, (time.time() - _job_start()) / 60.0)


def remaining_minutes():
    """Minutes left before the job is killed. Can go negative; callers clamp."""
    return JOB_LIMIT_MINUTES - elapsed_minutes()


def can_afford(minutes, reserve=None):
    """
    True if an operation costing roughly `minutes` fits AND leaves the
    reserve intact. Ask before starting the work, not after.
    """
    r = RESERVE_MIN if reserve is None else reserve
    return remaining_minutes() - r >= float(minutes)


def review_budget_hours(cap):
    """
    How many hours of human-review waiting this episode can still afford.

    Never more than `cap` (the caller's own policy ceiling) and never more
    than the job physically has left after its reserve. Returns 0.0 rather
    than a negative number so callers can treat "no budget" as a plain
    falsy value.
    """
    physical = (remaining_minutes() - RESERVE_MIN) / 60.0
    return max(0.0, min(float(cap), physical))


def status_line():
    """One line for logs and Telegram, so the clock is never invisible again."""
    return (f"job clock: {elapsed_minutes():.0f} min elapsed, "
            f"{remaining_minutes():.0f} min left of {JOB_LIMIT_MINUTES:.0f} "
            f"(reserve {RESERVE_MIN:.0f} min)")


def deadline():
    """Absolute datetime the job is expected to be killed at."""
    return datetime.datetime.fromtimestamp(_job_start()) + \
        datetime.timedelta(minutes=JOB_LIMIT_MINUTES)
