"""
Measure whether a model running ON THE BUILD MACHINE is fast enough to be useful.

WHY THIS IS WORTH KNOWING
-------------------------
This repository is public, which means GitHub gives it build machines free and
without a monthly limit -- 4 processors and 16 GB of memory, unmetered. A small
model can be downloaded and run directly on that machine.

It would be far too slow to write a full script. But roughly half the AI calls
an episode makes are tiny: a title, a six-word thumbnail line, a set of
hashtags, a yes/no judgement. For those, a small local model is plausible.

What makes it worth the trouble is not speed, it is that it CANNOT FAIL THE WAY
EVERYTHING ELSE HAS. No API key to expire, no quota to exhaust, no model for a
provider to retire, no account for anyone to deny. Every incident this project
has had for a month -- 401s, 404s, 410 Gone, exhausted daily allowances -- is
structurally impossible for a file on local disk.

WHY IT IS NOT ENABLED YET
-------------------------
Because nobody has measured it, including me. I proposed it in the plan as an
idea worth testing and said so explicitly. This script is that test. It must
run on a real runner: the development sandbox blocks huggingface.co by policy,
so the model cannot even be fetched there, and a benchmark on different
hardware would not answer the question anyway.

VERDICT
-------
Writes local_model_verdict.json and prints a plain-language answer. The bar:
a short call must complete in under ~20 seconds to be worth having as a
last-resort provider. Slower than that and it would hold up a gate retry loop
for longer than simply failing would.

Run on a runner:  python tools/bench_local_model.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "video_pipeline" / "local_model_verdict.json"
MODEL_DIR = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "localmodel"

# A 0.5B model quantised to about 400 MB. Deliberately the smallest thing that
# can still follow a short instruction: the job is titles and yes/no answers,
# not prose, and every extra billion parameters is seconds per call on a CPU.
MODEL_URL = ("https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/"
             "resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf")
MODEL_FILE = MODEL_DIR / "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# The real short-call shapes from the pipeline, not invented ones.
PROMPTS = [
    ("thumbnail line",
     "Write ONLY a 4-word phrase for a video thumbnail about a patient whose "
     "mystery illness was traced to their tap water. No quotes, no explanation."),
    ("yes/no judgement",
     "Answer with one word, YES or NO. Does this sentence contain a specific "
     "medical claim? Sentence: 'She had been unwell for nine months.'"),
    ("hashtags",
     "List exactly 5 hashtags for a medical mystery documentary. "
     "Output only the hashtags on one line."),
    ("title",
     "Write ONE video title, under 60 characters, for a documentary about a "
     "misdiagnosis that took four years to correct. Output only the title."),
]

SHORT_CALL_BUDGET_S = 20.0     # above this it is not worth having


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def setup():
    print("Installing llama-cpp-python (from PyPI, which is reachable)...")
    r = sh(f"{sys.executable} -m pip install llama-cpp-python -q")
    if r.returncode:
        print("  could not install:", (r.stderr or "")[-500:])
        return False
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_FILE.exists() and MODEL_FILE.stat().st_size > 100_000_000:
        print(f"  model already present ({MODEL_FILE.stat().st_size/1e6:.0f} MB)")
        return True
    print(f"Downloading the model (~400 MB) from Hugging Face...")
    t0 = time.time()
    r = sh(f'curl -sSL --fail -o "{MODEL_FILE}" "{MODEL_URL}"')
    if r.returncode or not MODEL_FILE.exists():
        print("  download failed:", (r.stderr or "")[-500:])
        return False
    print(f"  {MODEL_FILE.stat().st_size/1e6:.0f} MB in {time.time()-t0:.0f}s")
    return True


def bench():
    from llama_cpp import Llama
    print("\nLoading the model...")
    t0 = time.time()
    llm = Llama(model_path=str(MODEL_FILE), n_ctx=2048,
                n_threads=os.cpu_count() or 4, verbose=False)
    load_s = time.time() - t0
    print(f"  loaded in {load_s:.1f}s on {os.cpu_count()} threads")

    results = []
    for label, prompt in PROMPTS:
        t0 = time.time()
        out = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64, temperature=0.7)
        dt = time.time() - t0
        text = (out["choices"][0]["message"]["content"] or "").strip()
        ntok = out.get("usage", {}).get("completion_tokens", 0) or 1
        results.append({"call": label, "seconds": round(dt, 2),
                        "tokens": ntok, "tok_per_s": round(ntok / dt, 1),
                        "answer": text[:120]})
        print(f"\n  {label:<18} {dt:5.1f}s  {ntok/dt:5.1f} tok/s")
        print(f"  {'':<18} -> {text[:100]}")
    return load_s, results


def main():
    if not setup():
        print("\nCANNOT MEASURE HERE. This needs a machine that can reach "
              "huggingface.co — the dev sandbox blocks it by policy.")
        return 2

    load_s, results = bench()
    worst = max(r["seconds"] for r in results)
    median = sorted(r["seconds"] for r in results)[len(results) // 2]
    viable = worst <= SHORT_CALL_BUDGET_S

    print("\n" + "=" * 68)
    print("VERDICT")
    print("=" * 68)
    print(f"  model load        : {load_s:.1f}s (once per run)")
    print(f"  slowest short call: {worst:.1f}s")
    print(f"  typical           : {median:.1f}s")
    print(f"  budget            : {SHORT_CALL_BUDGET_S:.0f}s")
    print()
    if viable:
        print("  USABLE. Fast enough for titles, thumbnail lines, hashtags and")
        print("  yes/no judgements — about half the calls an episode makes.")
        print("  Worth enabling as the last-resort provider: it has no key, no")
        print("  quota and nothing anyone can decommission, so it is the one")
        print("  provider that can never appear in a morning report as dead.")
        print()
        print("  To enable: set LOCAL_MODEL_ENABLED=true in the workflow env.")
    else:
        print("  NOT WORTH IT on this hardware. A short call takes longer than")
        print("  the budget, so it would hold up gate retry loops for longer")
        print("  than simply failing would. Leave it disabled.")
        print()
        print("  This is a real answer, not a failure — the idea was proposed")
        print("  as untested and this is the test saying no.")
    print("=" * 68)

    VERDICT.parent.mkdir(parents=True, exist_ok=True)
    VERDICT.write_text(json.dumps({
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cpu_count": os.cpu_count(),
        "model": MODEL_FILE.name,
        "load_seconds": round(load_s, 1),
        "slowest_short_call_s": round(worst, 2),
        "median_short_call_s": round(median, 2),
        "budget_s": SHORT_CALL_BUDGET_S,
        "viable": viable,
        "calls": results,
    }, indent=2))
    print(f"\n  written: {VERDICT.relative_to(ROOT)}")
    return 0 if viable else 1


if __name__ == "__main__":
    sys.exit(main())
