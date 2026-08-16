"""
Checks the production timetable is internally consistent.

Cron day-of-week arithmetic is quietly error-prone: 0 is Sunday, the offset
between "generate" and "upload" crosses midnight UTC, and a schedule that is
wrong by one day does not fail loudly -- it just publishes into an empty slot
or generates an episode nothing collects. Every rule below is one of those
silent failures.

Run: python tools/test_schedule.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

CHANNELS = {
    "ch1": "No Known Cause  (medical)",
    "ch2": "Evidence Room   (true crime)",
    "ch3": "Control Files   (cults/propaganda)",
    "ch4": "The Archive     (history)",
    "ch5": "Collapse Index  (finance)",
}

# RULE 5: anything that can stop and wait for you runs while you are awake.
# 03:30-09:30 UTC is 09:00-15:00 IST.
WAKING_START, WAKING_END = 3 * 60 + 30, 9 * 60 + 30

FAIL = []


def fail(msg):
    FAIL.append(msg)
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


def crons(path):
    """Every cron in a workflow, commented or not. Returns [(minutes, {days})]."""
    out = []
    for m in re.finditer(r"cron:\s*'(\S+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)'",
                         path.read_text()):
        minute, hour, dow = m.groups()
        days = set()
        for part in dow.split(","):
            if "-" in part:
                a, b = part.split("-")
                days.update(range(int(a), int(b) + 1))
            elif part != "*":
                days.add(int(part))
            else:
                days.update(range(7))
        out.append((int(hour) * 60 + int(minute), days))
    return out


gen, up = {}, {}
for ch in CHANNELS:
    gen[ch] = crons(WF / f"{ch}_generate.yml")
    up[ch] = crons(WF / f"{ch}_upload.yml")

print("Every channel writes three times a week and publishes three times")
for ch, name in CHANNELS.items():
    g = sum(len(d) for _t, d in gen[ch])
    u = sum(len(d) for _t, d in up[ch])
    if g != 3:
        fail(f"{ch} {name}: generates {g} times a week, expected 3")
    elif u != 3:
        fail(f"{ch} {name}: uploads {u} times a week, expected 3")
    else:
        ok(f"{ch} {name}: 3 writes, 3 uploads")

total_g = sum(sum(len(d) for _t, d in gen[ch]) for ch in CHANNELS)
print(f"        {total_g} episodes a week across five channels")

print()
print("RULE 6: every episode is written the day BEFORE it publishes")
for ch, name in CHANNELS.items():
    gen_days = {d for _t, ds in gen[ch] for d in ds}
    up_days = {d for _t, ds in up[ch] for d in ds}
    expected = {(d + 1) % 7 for d in gen_days}
    if expected != up_days:
        fail(f"{ch}: writes {sorted(DAYS[d] for d in gen_days)} so should "
             f"publish {sorted(DAYS[d] for d in expected)}, "
             f"but publishes {sorted(DAYS[d] for d in up_days)}")
    else:
        ok(f"{ch} writes {','.join(DAYS[d] for d in sorted(gen_days))} "
           f"-> publishes {','.join(DAYS[d] for d in sorted(up_days))}")

print()
print("RULE 5: writing starts while you are awake (09:00-15:00 IST)")
for ch, name in CHANNELS.items():
    for t, _d in gen[ch]:
        if not (WAKING_START <= t <= WAKING_END):
            fail(f"{ch} writes at {t//60:02d}:{t%60:02d} UTC — outside the "
                 f"window where you can answer a review gate")
    else:
        ok(f"{ch} writes at " + ", ".join(
            f"{t//60:02d}:{t%60:02d} UTC" for t, _d in gen[ch]))

print()
print("RULE 2: no two channels start writing at the same moment")
slots = {}
for ch in CHANNELS:
    for t, days in gen[ch]:
        for d in days:
            slots.setdefault((d, t), []).append(ch)
clash = {k: v for k, v in slots.items() if len(v) > 1}
if clash:
    for (d, t), chs in sorted(clash.items()):
        fail(f"{DAYS[d]} {t//60:02d}:{t%60:02d} UTC — {', '.join(chs)} "
             f"all start together")
else:
    ok("every writing slot is used by exactly one channel")

busiest = max((len([1 for (d, _t), v in slots.items() if d == day])
               for day in range(7)))
print(f"        busiest day writes {busiest} episodes")
if busiest > 3:
    fail(f"{busiest} channels write on one day — the plan allows at most 3")

print()
print("No two channels publish in the same minute either")
uslots = {}
for ch in CHANNELS:
    for t, days in up[ch]:
        for d in days:
            uslots.setdefault((d, t), []).append(ch)
uclash = {k: v for k, v in uslots.items() if len(v) > 1}
if uclash:
    for (d, t), chs in sorted(uclash.items()):
        fail(f"{DAYS[d]} {t//60:02d}:{t%60:02d} UTC — {', '.join(chs)} "
             f"publish together")
else:
    ok("every publishing slot is used by exactly one channel")

print()
print("The writing week")
for day in range(7):
    entries = sorted((t, ch) for (d, t), chs in slots.items() if d == day
                     for ch in chs)
    line = ", ".join(f"{ch} {t//60:02d}:{t%60:02d}" for t, ch in entries)
    print(f"        {DAYS[day]}  {line or '-'}")

print()
if FAIL:
    print(f"FAILED — {len(FAIL)} problem(s) with the timetable")
    sys.exit(1)
print("Timetable is consistent.")
