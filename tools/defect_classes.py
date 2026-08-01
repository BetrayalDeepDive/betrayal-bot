"""
DEFECT-CLASS SCANNER — stop finding these one run at a time.

WHY THIS EXISTS
---------------
Every failure this channel has had for a week belongs to one of a small
number of classes, and each one was found the same expensive way: trigger a
run, wait hours, watch it die, read the log, fix that ONE instance, trigger
again. The classes, with the instances found so far:

  1. UNREACHABLE ACCEPTANCE -- a threshold set above the best score a
     correct answer can achieve. Found at the title scorer, the Shorts
     scorer, the audio gate, the title scorer again, the video gate, and
     then twelve separate AI calls whose prompts cap the answer below the
     100-character success floor. Six discoveries, six runs, ~20 hours.

  2. RETRY WITHOUT VARIATION -- N attempts that cannot differ. Thirteen
     identical titles (same provider, same prompt), thirteen identical 8.3
     audio renders (voice name swapped, engine unchanged), five identical
     7.8 video assemblies.

  3. PHANTOM DEPENDENCY -- importing a module that does not exist, inside a
     try/except that logs it as an empty cache. `competitive_research` never
     resolved once, and the log said "cached competitive data unavailable".

  4. WORK DISCARDED ON EXIT -- sys.exit() past a finished artifact that was
     never checkpointed, or a job cancelled at the wall with nothing saved.

  5. FORMAT LEAKAGE -- true-crime vocabulary surviving the conversion in the
     places a viewer actually sees: burned-in text, hashtags, topic pools,
     the research source itself.

  6. SUCCESS WITHOUT VERIFICATION -- reporting a stage changed something
     when nothing checked that it did.

Finding instance number seven of a class by running the pipeline for four
hours is the waste. This scans for the whole class, across every channel and
every shared module, in seconds.

READ THE OUTPUT AS LEADS, NOT VERDICTS. A static scanner cannot know that a
particular threshold is fine because the caller validates differently. Each
finding prints enough context to judge it in one look; triage is the point.
"""

import ast
import io
import pathlib
import re
import sys
import tokenize

ROOT = pathlib.Path(__file__).resolve().parent.parent
FINDINGS = []


def finding(cls, path, line, what, why):
    FINDINGS.append((cls, str(path), line, what, why))


def py_files():
    for sub in ("channels", "video_pipeline", "tools"):
        for p in sorted((ROOT / sub).rglob("*.py")):
            if "__pycache__" in p.parts or p.name == "defect_classes.py":
                continue
            yield p


def rel(p):
    return str(pathlib.Path(p).relative_to(ROOT))


def code_only(src):
    """Source with comments and docstrings removed (see audit's read_code)."""
    out, depth, prev = [], 0, tokenize.NEWLINE
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    for t in toks:
        if t.type == tokenize.COMMENT:
            continue
        if t.type == tokenize.OP:
            if t.string in "([{":
                depth += 1
            elif t.string in ")]}":
                depth = max(0, depth - 1)
        if (t.type == tokenize.STRING and depth == 0
                and prev in (tokenize.INDENT, tokenize.DEDENT,
                             tokenize.NEWLINE, tokenize.ENCODING)):
            prev = t.type
            continue
        if t.type not in (tokenize.NL, tokenize.NEWLINE,
                          tokenize.INDENT, tokenize.DEDENT):
            out.append((t.string, t.start[0]))
        if t.type != tokenize.NL:
            prev = t.type
    return out


# ── CLASS 1: UNREACHABLE ACCEPTANCE ───────────────────────────────────────
# An AI call whose PROMPT caps the output shorter than the length its own
# acceptance check demands. This is the class that disabled twelve calls.
_LEN_CAP = re.compile(
    r"(?i)\b(?:at most|no more than|under|max(?:imum)?|exactly)\s+(\d{1,3})\s*"
    r"(characters|chars|words)\b|\b(\d{1,3})\s*[-–]\s*(\d{1,3})\s*"
    r"(characters|chars|words)\b|\b(\d{1,2})\s*[-–]\s*(\d{1,2})\s+words?\b")


def scan_unreachable_acceptance():
    for p in py_files():
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fname = ""
            if isinstance(node.func, ast.Name):
                fname = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            if fname not in ("ai_generate", "ai_fn", "llm", "call_ai_fn"):
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            has_min = "min_chars" in kw
            tokens_val = None
            for key in ("tokens", "max_tokens"):
                v = kw.get(key)
                if isinstance(v, ast.Constant) and isinstance(v.value, int):
                    tokens_val = v.value
            # The prompt text, as far as it can be read statically.
            seg = "\n".join(lines[max(0, node.lineno - 1):
                                  min(len(lines), node.end_lineno or node.lineno)])
            cap_chars = None
            # "5 titles, 50-65 characters each" caps the RESPONSE near 300, not
            # 50. Treating the per-ITEM length as the response length made the
            # title generator read as broken when it is correct.
            n_items = 1
            mi = re.search(r"(?i)\b(?:return|generate|list|write)\s+(?:only\s+)?"
                           r"(\d{1,2})\s+(?:new\s+|different\s+)?"
                           r"(?:titles|angles|hooks|options|hashtags|ideas|"
                           r"lines|sentences|variants)\b", seg)
            if mi:
                n_items = max(1, int(mi.group(1)))
            m = _LEN_CAP.search(seg)
            if m:
                nums = [int(g) for g in m.groups() if g and g.isdigit()]
                unit = next((g for g in m.groups() if g and not g.isdigit()), "")
                if nums:
                    lo = min(nums)
                    cap_chars = lo * (6 if "word" in (unit or "") else 1) * n_items
            if has_min:
                continue
            if cap_chars is not None and cap_chars < 100:
                finding("1-unreachable-acceptance", rel(p), node.lineno,
                        f"{fname}(...) prompt caps output near {cap_chars} chars",
                        "the default success floor is 100 chars — a correct "
                        "answer would be discarded and the provider marked dead")
            elif tokens_val is not None and tokens_val <= 25:
                finding("1-unreachable-acceptance", rel(p), node.lineno,
                        f"{fname}(..., tokens={tokens_val}) with no min_chars",
                        f"~{tokens_val * 4} chars max output vs a 100-char floor")


def scan_gate_ceilings():
    """
    A numeric gate whose components cannot sum to the bar.

    Only flags the shape that has bitten repeatedly: a MIN/gate constant
    compared against a score built from weighted parts, where the weights
    are visible constants in the same file.
    """
    for p in py_files():
        src = p.read_text()
        for m in re.finditer(r"^\s*(\w*(?:MIN|GATE|FLOOR)\w*)\s*=\s*([\d.]+)\s*$",
                             src, re.M):
            name, val = m.group(1), float(m.group(2))
            # Not every constant with MIN in its name is a /10 gate: MIN_WORDS
            # is a word count, _ASSEMBLY_COST_MIN is minutes, *_SEC is seconds.
            # Flagging those is the noise that teaches you to ignore a scanner,
            # which is worse than not having one.
            if re.search(r"(?i)WORDS|SEC|COST|SIZE|BYTES|CHARS|COUNT|"
                         r"HOURS|MINUTES|_MS$|DAYS", name):
                continue
            if val > 10:
                finding("1-unreachable-acceptance", rel(p),
                        src[:m.start()].count("\n") + 1,
                        f"{name} = {val} on what looks like a /10 scale",
                        "no score can clear a bar above the scale's maximum")


# ── CLASS 2: RETRY WITHOUT VARIATION ──────────────────────────────────────
def scan_retry_without_variation():
    """
    A retry loop whose body contains no call that could change the outcome.

    Heuristic and deliberately loose: flags loops that re-invoke the SAME
    generator with arguments that are all loop-invariant, and that contain
    no variation hook (set_ai_variant, a seed change, a provider/voice/engine
    swap, or feedback threaded into the next attempt).
    """
    VARY = ("set_ai_variant", "random.choice", "random.shuffle", "seed",
            "feedback", "_SKIP_", "variant", "rotate", "angles", "prev_score",
            "reject", "tried", "_STUCK", "round_no")
    for p in py_files():
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            body = "\n".join(lines[node.lineno - 1:(node.end_lineno or node.lineno)])
            if not re.search(r"(?i)\battempt|retry|remake|rework\b", body):
                continue
            if len(body.splitlines()) < 6:
                continue
            if any(v in body for v in VARY):
                continue
            if not re.search(r"(?i)\b(generate|produce|render|assemble|call_|score)\w*\(",
                             body):
                continue
            finding("2-retry-without-variation", rel(p), node.lineno,
                    "retry loop with no visible source of variation",
                    "N attempts that cannot differ is one attempt billed N times")


# ── CLASS 3: PHANTOM DEPENDENCY ───────────────────────────────────────────
def scan_phantom_imports():
    import importlib.util
    sys.path.insert(0, str(ROOT / "video_pipeline"))
    stdlib = set(sys.stdlib_module_names)
    # Installed at runtime by the workflows, not present in this sandbox.
    RUNTIME_OK = {"gtts", "kokoro", "soundfile", "reportlab", "bpy", "torch",
                  "edge_tts", "PIL", "numpy", "whisper", "docx"}
    for p in py_files():
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                if mod in stdlib or mod in RUNTIME_OK:
                    continue
                try:
                    if importlib.util.find_spec(mod) is not None:
                        continue
                except (ImportError, ValueError, ModuleNotFoundError):
                    pass
                finding("3-phantom-dependency", rel(p), node.lineno,
                        f"imports '{mod}', which does not resolve",
                        "inside a try/except this logs as a missing cache, not "
                        "a missing module, and the feature silently never runs")


# ── CLASS 4: WORK DISCARDED ON EXIT ───────────────────────────────────────
def scan_exit_discards_work():
    """
    sys.exit() reached after an expensive artifact exists, with no checkpoint
    save and no pending-upload write anywhere in the enclosing function.
    """
    for p in py_files():
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = "\n".join(lines[fn.lineno - 1:(fn.end_lineno or fn.lineno)])
            if "sys.exit" not in body:
                continue
            builds = re.search(r"(?i)\b(assemble_video|run_audio_stage|"
                               r"upload_yt|final\.mp4|narration\.mp3)\b", body)
            saves = re.search(r"(?i)\b(ckpt_save|save_pending|checkpoint)\b", body)
            if builds and not saves:
                finding("4-work-discarded-on-exit", rel(p), fn.lineno,
                        f"{fn.name}() exits after building an artifact, "
                        f"with no checkpoint in the function",
                        "an ephemeral runner loses anything not committed")


# ── CLASS 5: FORMAT LEAKAGE (Ch1 only — it is the converted channel) ──────
CRIME = ("truecrime", "true crime", "darkpsychology", "dark psychology",
         "murder", "killer", "victim", "homicide", "perpetrator", "suspect",
         "crime scene", "detective", "betrayal", "cover-up", "covered up")

# Internal identifiers, not viewer-facing prose: the channel's own directory
# key, its GitHub org, a scorer's metric name, and the URL inside the retired
# research function. Matching these buried the real hits under 20 lines of
# noise, which is how a scanner trains you to stop reading it.
CRIME_EXEMPT = ("betrayal_deepdive", "betrayaldeepdive", "killer_hook",
                "r/truecrime")

# A crime word inside a PROHIBITION is the thing keeping the format clean:
# "NEVER use VICTIMS", "there is no betrayal in", "NEVER allege ... a
# cover-up". Flagging those inverts the check.
NEGATION_NEAR = ("never", "not ", "no ", "forbidden", "do not", "don't",
                 "avoid", "instead of", "rather than", "used to", "removed")


def scan_format_leakage():
    ch1 = ROOT / "channels/betrayal_deepdive/clinical_pipeline.py"
    if not ch1.exists():
        return
    # A BANLIST OF CRIME WORDS IS THE DEFENCE, NOT THE DEFECT. The title
    # scorer holds `accusatory = ["covered up", "cover-up", ...]` precisely so
    # those phrasings are penalised. Reading its contents as leakage would
    # report the guard as the thing it guards against.
    src_lines = ch1.read_text().splitlines()
    banlist_lines = set()
    for i, l in enumerate(src_lines, 1):
        if re.search(r"(?i)\b(accusatory|forbidden|banned|blocklist|"
                     r"blacklist|_BAD_|penal\w*)\b\s*=?\s*[\[(]", l):
            for j in range(i, min(i + 12, len(src_lines) + 1)):
                banlist_lines.add(j)
                if "]" in src_lines[j - 1] or ")" in src_lines[j - 1]:
                    break
    for tok, ln in code_only(ch1.read_text()):
        if ln in banlist_lines:
            continue
        low = tok.lower()
        if not (low.startswith(("'", '"', "f'", 'f"')) and len(tok) > 6):
            continue
        if any(e in low for e in CRIME_EXEMPT):
            continue
        for w in CRIME:
            if w in low:
                around = low[max(0, low.index(w) - 130):low.index(w)]
                if any(n in around for n in NEGATION_NEAR):
                    break
                finding("5-format-leakage", rel(ch1), ln,
                        f"live string contains {w!r}: {tok[:70]}",
                        "Ch1 publishes clinical case reports; crime vocabulary "
                        "in a live string reaches a viewer")
                break


# ── CLASS 6: SUCCESS WITHOUT VERIFICATION ─────────────────────────────────
def scan_unverified_success():
    """
    A function that reports a change happened without comparing before/after.
    Targets the exact shape behind "Edit: change the title returned the same
    script and reported success".
    """
    for p in py_files():
        src = p.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = fn.name.lower()
            if not re.search(r"retitle|rewrite|regenerat|remake|swap|edit", name):
                continue
            body = "\n".join(lines[fn.lineno - 1:(fn.end_lineno or fn.lineno)])
            compares = re.search(r"!=\s*\w|==\s*\w|\.lower\(\)\s*!=|"
                                 r"is not\s+\w|_old|previous|original", body)
            if not compares:
                finding("6-success-without-verification", rel(p), fn.lineno,
                        f"{fn.name}() never compares its output to its input",
                        "a rewrite that returns the original still reports "
                        "success — this is the Edit-button failure")


BASELINE = ROOT / "tools/defect_classes_baseline.txt"


def _key(cls, path, what):
    """
    Identity of a lead, deliberately WITHOUT the line number.

    A baseline keyed on line numbers goes stale the moment anything above it
    is edited, and a stale baseline either fails every run or gets deleted --
    both of which end with nobody running the check.
    """
    normalised = re.sub(r"\d+", "N", what)
    return f"{cls}|{path}|{normalised}"


def main():
    argv = sys.argv[1:]
    for fn in (scan_unreachable_acceptance, scan_gate_ceilings,
               scan_retry_without_variation, scan_phantom_imports,
               scan_exit_discards_work, scan_format_leakage,
               scan_unverified_success):
        try:
            fn()
        except Exception as e:
            print(f"  scanner {fn.__name__} crashed: {type(e).__name__}: {e}")

    # --update-baseline records today's triaged-and-accepted leads.
    # --check fails ONLY on leads that are not in that record, which is the
    # whole point: the six classes above have each been found the expensive
    # way (trigger a run, wait hours, watch it die). A NEW instance now fails
    # in seconds, before the run, instead of after it.
    if "--update-baseline" in argv:
        keys = sorted({_key(c, p, w) for c, p, _l, w, _y in FINDINGS})
        BASELINE.write_text(
            "# Triaged, accepted leads. Anything NOT here fails the preflight.\n"
            "# Regenerate deliberately: python tools/defect_classes.py "
            "--update-baseline\n" + "\n".join(keys) + "\n")
        print(f"baseline written: {len(keys)} accepted lead(s) -> {rel(BASELINE)}")
        return 0

    if "--check" in argv:
        known = set()
        if BASELINE.exists():
            known = {l.strip() for l in BASELINE.read_text().splitlines()
                     if l.strip() and not l.startswith("#")}
        new = [(c, p, l, w, y) for c, p, l, w, y in FINDINGS
               if _key(c, p, w) not in known]
        if not new:
            print(f"defect-class check: OK — {len(FINDINGS)} known lead(s), "
                  f"0 new.")
            return 0
        print(f"defect-class check: {len(new)} NEW lead(s) — these are the "
              f"failure modes that have each cost a full run before:\n")
        for c, p, l, w, y in new:
            print(f"  [{c}] {p}:{l}\n      {w}\n      why: {y}")
        print("\nFix them, or accept them deliberately with "
              "`python tools/defect_classes.py --update-baseline`.")
        return 1

    by_class = {}
    for cls, path, line, what, why in FINDINGS:
        by_class.setdefault(cls, []).append((path, line, what, why))

    total = 0
    for cls in sorted(by_class):
        rows = by_class[cls]
        total += len(rows)
        print(f"\n{'=' * 74}\n{cls}  —  {len(rows)} lead(s)\n{'=' * 74}")
        for path, line, what, why in rows[:40]:
            print(f"  {path}:{line}\n      {what}\n      why: {why}")
        if len(rows) > 40:
            print(f"  ... {len(rows) - 40} more")
    print(f"\n{total} lead(s) across {len(by_class)} class(es). "
          f"These are leads, not verdicts — triage each.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
