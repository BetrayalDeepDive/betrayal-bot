"""
GATE ROUNDS — one round of thirteen is one opinion, not a verdict.

WHY THIS EXISTS
---------------
The instruction was explicit, first for the title and now for the rest:

    "We have a quality score, which attempts three times, that is, 13 x 3.
     I want the same thing for the title as well. If, for the first time, it
     fails for 13 attempts, I want to redo it after 10 minutes. Research
     other title names and go ahead with the approval. If that doesn't work
     for the third time, then it skips for the day, not before that."

    "for the thumbnail, youtube shorts, editing etc I want it to be increased
     to three attempts, not only one attempt. The current rate is 1x13 i want
     it to be changed to 3x13."

Only the title had it. Thumbnail text, Shorts, the editing/quality audit, the
script, the audio and the video gates each ran a single round of thirteen and
then skipped the day. This module is that structure, written once, so the
same rule genuinely applies to every stage instead of being re-implemented
per gate and drifting.

WHAT A ROUND IS FOR
-------------------
A round that failed thirteen times has exhausted what it can get from
rewording its own output -- that is the whole lesson of the retry defects on
this channel: thirteen attempts with no source of variation is one attempt
billed thirteen times. So a round boundary is not a pause and a re-run. It
is: wait, fetch genuinely NEW input, and start the next thirteen from that.
The `between_rounds` hook is where the new input comes from, and a gate that
cannot supply one should say so rather than pretend three rounds are three
chances.

TIME
----
Rounds multiply cost by three, and the job dies at six hours. Every round
boundary asks the job clock whether the next round plus the finalisation
reserve actually fits, and stops early -- reporting honestly that it stopped
for time and not for quality -- rather than being cancelled mid-render with
everything discarded. A ten-minute pause that would push the job past the
wall is skipped, not slept through.
"""

import inspect
import time

DEFAULT_ROUNDS = 3
DEFAULT_PAUSE_SEC = 600  # 10 minutes, per the instruction


def _fits(cost_min):
    """
    Can the job still afford `cost_min` minutes? True when there is no job
    clock at all (running outside Actions), since a local run has no wall.
    """
    if not cost_min:
        return True
    try:
        from job_clock import can_afford
        return can_afford(cost_min)
    except Exception:
        return True


def _takes_seed(fn):
    """Does this gate want the material the previous round's research found?"""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    if any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in params.values()):
        return True
    return len([p for p in params.values()
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                              inspect.Parameter.POSITIONAL_OR_KEYWORD)]) >= 2


def _clock():
    try:
        from job_clock import status_line
        return status_line()
    except Exception:
        return "job clock unavailable"


def run_in_rounds(label, attempt_round, *, rounds=DEFAULT_ROUNDS,
                  pause_sec=DEFAULT_PAUSE_SEC, between_rounds=None,
                  round_cost_min=None, tg_fn=None, log_fn=None):
    """
    Run `attempt_round` up to `rounds` times, pausing and re-seeding between.

    attempt_round(round_no) -> result, where any falsy result means the whole
        round of attempts failed to clear its gate.
    between_rounds(round_no) -> optional fresh material handed to the next
        round. Called AFTER the pause, BEFORE the round it feeds.
    round_cost_min: rough minutes one round costs. Used to ask the job clock
        whether the next round fits; None means "cheap, always try".

    Returns (result, rounds_used, stopped_for_time).
    """
    log = log_fn or (lambda m: print(m))
    seed = None
    for rnd in range(1, rounds + 1):
        if rnd > 1:
            # Ask before spending. A round we cannot finish is worse than a
            # round we never start: the first loses everything already built.
            if not _fits(round_cost_min):
                msg = (f"{label}: rounds {rnd}-{rounds} skipped for TIME, not "
                       f"quality — another round needs ~{round_cost_min} min and "
                       f"the job cannot afford it ({_clock()}).")
                log(f"  {msg}")
                if tg_fn:
                    try:
                        tg_fn(f"⏱️ {msg}")
                    except Exception:
                        pass
                return None, rnd - 1, True
            wait = pause_sec if _fits((pause_sec / 60.0) + (round_cost_min or 0)) else 0
            msg = (f"{label}: round {rnd - 1} of {rounds} ended without clearing "
                   f"its gate. " +
                   (f"Waiting {wait // 60} minutes, then researching new "
                    f"material and trying again."
                    if wait else
                    "Retrying immediately — the 10-minute pause would not fit "
                    "in the job's remaining time.") +
                   f" The day is only skipped if round {rounds} also fails.")
            log(f"  {msg}")
            if tg_fn:
                try:
                    tg_fn(f"🔄 Ch1 {msg}")
                except Exception:
                    pass
            if wait:
                time.sleep(wait)
            if between_rounds:
                try:
                    seed = between_rounds(rnd)
                    if seed:
                        log(f"  {label} round {rnd}: new material gathered.")
                    else:
                        # Honest: without new input this round is a re-run of
                        # the last one, and saying so beats implying otherwise.
                        log(f"  {label} round {rnd}: no new material available — "
                            f"this round repeats the previous conditions.")
                except Exception as e:
                    log(f"  {label} round {rnd} research failed (non-fatal): {e}")
        log(f"  {label} ROUND {rnd}/{rounds}")
        # Decide arity by INSPECTION, not by catching TypeError: a TypeError
        # raised inside the gate itself would otherwise be swallowed and the
        # whole round silently re-run, hiding a real bug as a retry.
        result = attempt_round(rnd, seed) if _takes_seed(attempt_round) \
            else attempt_round(rnd)
        if result:
            log(f"  {label} cleared on round {rnd} of {rounds}.")
            return result, rnd, False
    log(f"  {label} failed all {rounds} rounds.")
    return None, rounds, False
