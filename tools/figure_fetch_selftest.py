#!/usr/bin/env python3
"""
Exercise the REAL figure-fetch path against a local server.

WHY
---
pmc_data.download_figure() and prefetch_figures() are the code that makes
this channel's differentiator possible -- the actual published figure from
the actual paper. They had never been executed. The sandbox blocks
pmc.ncbi.nlm.nih.gov and europepmc.org, so "we cannot test it" became the
standing excuse across five production runs, while a whole visual register
silently depended on it.

The remote HOST cannot be tested from here. Everything else can: the URL
pattern loop, the fallback ordering, the retry-on-5xx, the Content-Type
check, the PIL decode, the resolution floor, the size floor, and
prefetch_figures pruning the case to what actually landed. A local HTTP
server serving controlled responses exercises every one of those for real,
with no mocking of the function under test.

What this does NOT prove: that
"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/bin/{fname}" is the correct
live URL shape. That is a fact about a remote service and only a real run
can settle it. Everything the code itself does is now proven.

Usage: python3 tools/figure_fetch_selftest.py
Exit:  0 all scenarios behaved correctly, 1 otherwise
"""
import io
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video_pipeline"))

from PIL import Image                      # noqa: E402
import pmc_data                            # noqa: E402


def _jpeg(w, h):
    b = io.BytesIO()
    img = Image.new("RGB", (w, h))
    # Noise so it does not compress to almost nothing and trip the size floor
    # for the wrong reason.
    px = img.load()
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            px[x, y] = ((x * 7) % 256, (y * 13) % 256, ((x + y) * 3) % 256)
    img.save(b, "JPEG", quality=95)
    return b.getvalue()


GOOD = _jpeg(900, 700)
TINY = _jpeg(100, 80)
HTML = b"<html><body>" + b"x" * 90000 + b"</body></html>"

# Each path maps to a scripted sequence of responses; the handler pops one
# per request so retry behaviour is observable.
SCRIPT = {}
HITS = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        HITS.append(self.path)
        seq = SCRIPT.get(self.path)
        if not seq:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"nope")
            return
        status, ctype, body = seq.pop(0) if len(seq) > 1 else seq[0]
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


RESULTS = []


def scenario(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main():
    srv, port = start_server()
    base = f"http://127.0.0.1:{port}"
    # Point the real module at the local server. The PATTERN SHAPE is
    # preserved exactly, so the pattern-loop logic under test is unchanged.
    pmc_data.FIGURE_URL_PATTERNS = (
        base + "/primary/{pmcid}/bin/{fname}",
        base + "/secondary/{pmcid}/bin/{fname}",
        base + "/tertiary/{pmcid}/bin/{fname}",
    )
    out = Path("/tmp/figtest")
    out.mkdir(exist_ok=True)
    fig = {"pmcid": "PMC1", "filename": "f1.jpg"}

    # 1. First pattern serves a good image.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/f1.jpg"] = [(200, "image/jpeg", GOOD)]
    dest = out / "a.jpg"
    got = pmc_data.download_figure(fig, str(dest))
    scenario("a real image on the first pattern is accepted",
             got and dest.exists() and dest.stat().st_size > 5000)
    scenario("no fallback pattern is tried once one succeeds",
             len(HITS) == 1, f"{len(HITS)} requests")

    # 2. Primary 404s, secondary serves the image.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/secondary/PMC1/bin/f1.jpg"] = [(200, "image/jpeg", GOOD)]
    dest = out / "b.jpg"
    got = pmc_data.download_figure(fig, str(dest))
    scenario("a 404 on the first pattern falls through to the second",
             got and dest.exists())

    # 3. Transient 503 then success — the retry must actually retry.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/f1.jpg"] = [(503, "text/plain", b"busy"),
                                          (200, "image/jpeg", GOOD)]
    dest = out / "c.jpg"
    got = pmc_data.download_figure(fig, str(dest))
    scenario("a transient 503 is retried, not abandoned",
             got and dest.exists(),
             f"{HITS.count('/primary/PMC1/bin/f1.jpg')} attempts")

    # 4. A large HTML error page must NOT be written as a .jpg.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/f1.jpg"] = [(200, "text/html", HTML)]
    dest = out / "d.jpg"
    if dest.exists():
        dest.unlink()
    got = pmc_data.download_figure(fig, str(dest))
    scenario("a 90 KB HTML error page is rejected", not got and not dest.exists())

    # 5. Correct Content-Type but the bytes are not an image.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/f1.jpg"] = [(200, "image/jpeg", b"\x00" * 80000)]
    dest = out / "e.jpg"
    if dest.exists():
        dest.unlink()
    got = pmc_data.download_figure(fig, str(dest))
    scenario("bytes that do not decode are rejected even with image/jpeg",
             not got and not dest.exists(),
             "Content-Type is set by the server and can be wrong")

    # 6. A valid but thumbnail-sized image.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/f1.jpg"] = [(200, "image/jpeg", TINY)]
    dest = out / "f.jpg"
    if dest.exists():
        dest.unlink()
    got = pmc_data.download_figure(fig, str(dest))
    scenario("a 100x80 thumbnail is rejected", not got and not dest.exists(),
             "would render as a postage stamp in a 1080p frame")

    # 7. Every pattern fails.
    SCRIPT.clear(); HITS.clear()
    dest = out / "g.jpg"
    if dest.exists():
        dest.unlink()
    logs = []
    got = pmc_data.download_figure(fig, str(dest), log_fn=logs.append)
    scenario("total failure is reported, not silent", not got and len(logs) >= 3,
             f"{len(logs)} log lines")

    # 8. prefetch_figures prunes the case to what actually landed, and
    #    records where each surviving figure is on disk.
    SCRIPT.clear(); HITS.clear()
    SCRIPT["/primary/PMC1/bin/ok1.jpg"] = [(200, "image/jpeg", GOOD)]
    SCRIPT["/primary/PMC1/bin/ok2.jpg"] = [(200, "image/jpeg", GOOD)]
    case = {"figures": [
        {"pmcid": "PMC1", "filename": "ok1.jpg", "label": "Figure 1"},
        {"pmcid": "PMC1", "filename": "missing.jpg", "label": "Figure 2"},
        {"pmcid": "PMC1", "filename": "ok2.jpg", "label": "Figure 3"},
    ]}
    case = pmc_data.prefetch_figures(case, str(out / "pf"), log_fn=lambda m: None)
    kept = case["figures"]
    scenario("prefetch keeps only figures that really downloaded",
             len(kept) == 2, f"{len(kept)} of 3")
    scenario("prefetch records a real on-disk path for each survivor",
             all(Path(f["local_path"]).exists() for f in kept))
    scenario("survivors are renumbered contiguously",
             sorted(Path(f["local_path"]).name for f in kept)
             == ["pmcfig_0.jpg", "pmcfig_1.jpg"],
             "the renderer indexes figures by position")

    # 9. The quota must then see the pruned truth, not the metadata.
    sys.path.insert(0, str(ROOT / "video_pipeline"))
    from medical_register import available_from_case, new_quota
    empty = pmc_data.prefetch_figures(
        {"figures": [{"pmcid": "PMC1", "filename": "gone.jpg"}]},
        str(out / "pf2"), log_fn=lambda m: None)
    scenario("a paper whose figures all fail reports FIGURE unavailable",
             available_from_case(empty)["FIGURE"] is False)
    q = new_quota(54, figure_count=len(empty["figures"]), case=empty)
    picks = [q.pick("the patient deteriorated overnight") for _ in range(54)]
    scenario("no FIGURE segment is scheduled when nothing downloaded",
             "FIGURE" not in picks,
             "otherwise ~30% of the episode renders the fallback card")

    srv.shutdown()
    bad = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(bad)}/{len(RESULTS)} scenarios passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
