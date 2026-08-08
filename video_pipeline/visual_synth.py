"""
Make the frame a brief asks for, when no real photograph exists for it.

WHY GENERATE AT ALL
-------------------
Roughly half of a clinical script is beats that no stock library can serve and
no chart can draw: a clot moving, a vessel closing, eleven weeks of waiting,
nobody being able to explain it. Those were the beats that got another
procedural diagram, and they are most of why the episode read as generic.

They are also the beats a documentary editor would cut interpretive imagery
into, which is exactly what this makes.

THE HARD LINE
-------------
Generation is allowed to be INTERPRETIVE and never EVIDENTIARY.

A generated CT slice, ECG trace, histology field or lab report is a claim about
what was found in a real, named, published patient. Making one up is
fabricating medical evidence inside a factual programme. It would also be
realistic synthetic media depicting a real event, which carries a disclosure
obligation the channel should not want.

`refuse()` below is a hard gate, not advice. It runs on every prompt, it is
tested, and there is no flag that turns it off. A brief whose intent is
`evidence` or `value` never reaches a generator at all -- visual_brief routes
those to the paper's own figure or to a chart of the paper's own numbers --
and this is the second lock on the same door.

Every frame that IS generated is recorded in a manifest with its prompt, its
route and the beat it serves, so what the episode contains is answerable
afterwards without anyone having to remember.

ROUTES
------
  1. Cloudflare Workers AI   -- the account is already configured for text;
                                the same token reaches its image models.
  2. Pollinations            -- no key at all.
  3. Procedural, drawn here  -- no network, no key, cannot fail. Not as good,
                                and infinitely better than a blank frame.

The last one is why this module has no failure mode. A run with everything
unreachable still returns a frame that belongs to the beat.
"""
import hashlib
import json
import os
import re
import time

W, H = 1920, 1080

# Prompts that would produce a claim about this patient. Matched loosely on
# purpose: "a CT of the brain", "brain CT scan" and "ct-scan" must all fail.
_EVIDENTIARY = (
    r"\bct\b", r"\bmri\b", r"\bx[- ]?ray\b", r"\bradiograph", r"\bultrasound\b",
    r"\becg\b", r"\bekg\b", r"\belectrocardiogram\b", r"\beeg\b",
    r"\bangiogram\b", r"\bmammogram\b", r"\bendoscop",
    r"\bhistolog", r"\bbiopsy\b", r"\bpathology slide\b", r"\bmicroscope\b",
    r"\bblood (?:test |work)?(?:result|report)", r"\blab(?:oratory)? report\b",
    r"\bmedical record\b", r"\bpatient chart\b", r"\bprescription\b",
    r"\btest result", r"\bscan\b", r"\bradiolog",
    # A real person is a separate problem from a real finding.
    r"\bphotograph of (?:a |the )?(?:patient|man|woman|child|doctor|nurse)\b",
    r"\bportrait\b", r"\bselfie\b", r"\breal person\b", r"\bface of\b",
)

# And the style must not drift back toward looking like a photograph.
_PHOTOREAL = (r"\bphotorealistic\b", r"\bhyper[- ]?real", r"\b8k photo\b",
              r"\bdslr\b", r"\bshot on\b", r"\braw photo\b", r"\bstock photo\b")


def refuse(prompt):
    """Why this prompt must not be generated, or None if it may be.

    Returns a reason string so the caller can log WHICH rule fired rather than
    a bare False, which is indistinguishable from a network failure.
    """
    low = " " + (prompt or "").lower() + " "
    for pat in _EVIDENTIARY:
        if re.search(pat, low):
            return ("would fabricate clinical evidence (/%s/) — this belongs to "
                    "the paper's own figure, not to a generator" % pat)
    for pat in _PHOTOREAL:
        if re.search(pat, low):
            return ("asks for a photographic look (/%s/) — a generated frame "
                    "that passes for a photograph of this case is exactly what "
                    "must not ship" % pat)
    return None


# ── manifest ───────────────────────────────────────────────────────────
def _manifest_path(work_dir):
    return os.path.join(str(work_dir), "generated_visuals.json")


def record(work_dir, entry):
    """Append one generated frame to this episode's manifest."""
    path = _manifest_path(work_dir)
    try:
        with open(path) as fh:
            data = json.load(fh)
    except Exception:
        data = {"frames": []}
    data["frames"].append(entry)
    try:
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
    except Exception:
        pass
    return data


def manifest(work_dir):
    try:
        with open(_manifest_path(work_dir)) as fh:
            return json.load(fh)
    except Exception:
        return {"frames": []}


# ── route 1: Cloudflare Workers AI ─────────────────────────────────────
CF_MODELS = (
    "@cf/black-forest-labs/flux-1-schnell",
    "@cf/stabilityai/stable-diffusion-xl-base-1.0",
    "@cf/bytedance/stable-diffusion-xl-lightning",
)


def _cloudflare(prompt, out_path, log=print, timeout=90):
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not token or not account:
        return False
    import base64
    import requests
    for model in CF_MODELS:
        url = ("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s"
               % (account, model))
        try:
            r = requests.post(url, headers={"Authorization": "Bearer " + token},
                              json={"prompt": prompt}, timeout=timeout)
        except Exception as e:
            log("    generate: cloudflare %s (%s)" % (model.split("/")[-1], e))
            continue
        if r.status_code != 200:
            log("    generate: cloudflare %s -> %s"
                % (model.split("/")[-1], r.status_code))
            continue
        # flux returns base64 JSON; the SD models return raw image bytes.
        data = None
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "json" in ctype:
            try:
                b64 = (r.json().get("result") or {}).get("image")
                data = base64.b64decode(b64) if b64 else None
            except Exception:
                data = None
        elif "image" in ctype:
            data = r.content
        if data and len(data) > 20000:
            with open(out_path, "wb") as fh:
                fh.write(data)
            log("    generate: cloudflare %s OK" % model.split("/")[-1])
            return True
    return False


# ── route 2: Pollinations ──────────────────────────────────────────────
def _pollinations(prompt, out_path, log=print, timeout=75, seed=0):
    import urllib.parse
    import requests
    url = ("https://image.pollinations.ai/prompt/%s"
           "?width=%d&height=%d&nologo=true&seed=%d"
           % (urllib.parse.quote(prompt[:900]), W, H, abs(seed) % 99999))
    try:
        r = requests.get(url, timeout=timeout)
    except Exception as e:
        log("    generate: pollinations (%s)" % e)
        return False
    if r.status_code == 200 and len(r.content) > 20000:
        with open(out_path, "wb") as fh:
            fh.write(r.content)
        log("    generate: pollinations OK")
        return True
    log("    generate: pollinations -> %s" % r.status_code)
    return False


# ── route 3: drawn here, from the brief ────────────────────────────────
def _abstracted(brief, out_path, log=print, used=None):
    """Build the frame from a REAL photograph, treated until it is imagery.

    THE FIRST VERSION OF THIS DREW EVERYTHING FROM NOTHING and it was the
    "abstract glow" rejection again: three mechanism beats came out as the same
    channel with the same blob in the same place, three state beats as the same
    tunnel, all of it floating in an empty frame. Vector shapes drawn by hand
    have exactly as much variety as the hand that drew them, which is why that
    approach failed here twice.

    A photograph has variety already. Crop it hard, push it to the channel's
    two colours, blur the motion into it and lay one drawn mark over the top,
    and the result is imagery rather than a diagram -- rooted in something real,
    different every time because the source is different every time, and
    unmistakably not a documentary photograph of this patient.

    The mark is what makes it a MECHANISM shot rather than a mood: a real
    trajectory drawn across a real texture.
    """
    import math
    import random

    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    import medical_figure_render as mfr

    seed = hashlib.sha1((brief.get("text") or str(brief.get("index", 0)))
                        .encode()).hexdigest()
    rng = random.Random(int(seed[:8], 16))

    # A real photograph to build on. The matcher first, so the texture at least
    # comes from the right part of the world.
    # SCENE AND HERO ONLY. NEVER THE EVIDENCE SHELF.
    #
    # The evidence photographs are scans, films and lab glassware. Abstracted
    # into an interpretive frame they are still legible as scans -- the first
    # render of this put readable MRI slices, patient labels and all, under a
    # mechanism shot. Nothing was fabricated (it is a generic stock MRI, not
    # this patient's) and it would still read to a viewer as this patient's
    # scan, which is the exact impression the whole policy exists to prevent.
    #
    # Evidence photographs belong on the evidence register, where they are
    # captioned as what they are. Interpretive frames are built on places and
    # textures.
    src = None
    try:
        import stock_match as smatch
        src, _why, _role = smatch.best_any(brief.get("text") or "",
                                           used=used or (),
                                           roles=("scene", "hero"))
    except Exception:
        src = None
    if not src:
        try:
            import stock_library as sl
            src = sl.pick(rng.choice(("scene", "hero")),
                          seed=int(seed[8:12], 16))
        except Exception:
            src = None
    if not src or not os.path.exists(src):
        return _drawn(brief, out_path, log=log)

    try:
        im = Image.open(src).convert("RGB")
    except Exception:
        return _drawn(brief, out_path, log=log)

    # CROP HARD. A 12-25% window of the source, placed differently every time,
    # so the same photograph never yields the same frame twice.
    fw = 0.12 + rng.random() * 0.13
    fh = fw * (H / float(W))
    cw, ch = max(64, int(im.width * fw)), max(36, int(im.height * fh))
    cx = rng.randint(0, max(0, im.width - cw))
    cy = rng.randint(0, max(0, im.height - ch))
    im = im.crop((cx, cy, cx + cw, cy + ch)).resize((W, H), Image.LANCZOS)

    a = np.asarray(im).astype(np.float32)
    # Directional blur, so it reads as movement rather than as a bad crop.
    # Blur scales with how much of the source the crop kept: a tight crop is
    # already unrecognisable, a wide one still has readable signage in it. The
    # first render left "Flur 10" legible across a mechanism frame -- real
    # signage that means nothing to the audience and reads as a mistake.
    im = Image.fromarray(a.astype("uint8")).filter(
        ImageFilter.GaussianBlur(rng.uniform(4.0, 8.0) + fw * 46.0))
    a = np.asarray(im).astype(np.float32)

    # DUOTONE into the channel's palette. Everything the channel generates
    # shares one grade, which is what stops forty frames reading as a mood
    # board -- and it is also what makes them plainly not photographs.
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32)) / 255.0
    lum = np.clip((lum - lum.min()) / max(1e-3, lum.max() - lum.min()), 0, 1)
    lum = lum ** rng.uniform(1.15, 1.7)
    dark = np.array(mfr.BG, np.float32)
    lite = np.array(mfr.ACCENT, np.float32) * rng.uniform(0.85, 1.15)
    a = dark[None, None, :] + (lite - dark)[None, None, :] * lum[:, :, None]

    # A vignette, so the eye lands where the mark will be.
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W * 0.5) / (W * 0.62)) ** 2 +
                ((yy - H * 0.5) / (H * 0.62)) ** 2)
    a *= np.clip(1.18 - 0.55 * r, 0.24, 1.1)[:, :, None]
    a += np.random.default_rng(int(seed[12:18], 16)).normal(0, 3.0, a.shape)
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
    d = ImageDraw.Draw(im, "RGBA")

    if brief.get("intent") == "mechanism":
        # ONE TRAJECTORY, drawn across the real texture. A curve from somewhere
        # to somewhere, and the thing that stops at the end of it. Every
        # parameter is drawn from this beat's own seed, so no two mechanism
        # frames share a composition.
        x0, y0 = W * rng.uniform(0.04, 0.20), H * rng.uniform(0.18, 0.82)
        x1, y1 = W * rng.uniform(0.62, 0.90), H * rng.uniform(0.18, 0.82)
        bend = rng.uniform(-0.42, 0.42)
        pts = []
        for i in range(101):
            t = i / 100.0
            mx = (x0 + x1) / 2 + (y1 - y0) * bend
            my = (y0 + y1) / 2 - (x1 - x0) * bend
            px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1
            py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1
            pts.append((px, py))
        for w, col in ((26, (95, 168, 160, 40)), (12, (150, 214, 206, 110)),
                       (5, (226, 244, 240, 230))):
            d.line(pts, fill=col, width=w, joint="curve")
        # The obstruction, at the end of the run.
        rr = H * rng.uniform(0.055, 0.095)
        ox, oy = pts[-1]
        d.ellipse([ox - rr * 1.1, oy - rr, ox + rr * 1.1, oy + rr],
                  fill=(150, 46, 44, 210), outline=(226, 96, 88, 255), width=6)
        for _ in range(26):
            ang, rad = rng.random() * 6.283, rng.random() ** 0.5 * rr * 0.72
            d.ellipse([ox + math.cos(ang) * rad * 1.1 - 5,
                       oy + math.sin(ang) * rad - 5,
                       ox + math.cos(ang) * rad * 1.1 + 5,
                       oy + math.sin(ang) * rad + 5], fill=(184, 64, 58, 170))
    else:
        # A state beat: one quiet mark, off centre, so the frame has a subject
        # without claiming to depict one.
        cxp, cyp = W * rng.uniform(0.24, 0.76), H * rng.uniform(0.26, 0.74)
        rr = H * rng.uniform(0.12, 0.22)
        # Heavier than it first was. At 60/95/150 alpha over a blurred plate
        # the rings vanished and the frame read as empty -- a state beat still
        # needs something for the eye to land on.
        for k, alpha, wdt in ((1.0, 110, 3), (0.70, 165, 4), (0.42, 235, 5)):
            d.ellipse([cxp - rr * k, cyp - rr * k, cxp + rr * k, cyp + rr * k],
                      outline=(150, 214, 206, alpha), width=wdt)
        d.line([(cxp - rr * 1.5, cyp), (cxp - rr * 1.12, cyp)],
               fill=(150, 214, 206, 200), width=4)
        d.line([(cxp + rr * 1.12, cyp), (cxp + rr * 1.5, cyp)],
               fill=(150, 214, 206, 200), width=4)

    im.save(out_path, quality=94)
    log("    generate: abstracted from %s (%s)"
        % (os.path.basename(src), brief.get("intent")))
    return os.path.exists(out_path)


def _drawn(brief, out_path, log=print):
    """Absolute last resort: no photograph on hand at all.

    Kept deliberately plain. It exists so `make()` has no failure mode, not
    because a hand-drawn channel-and-blob is good television.
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    import medical_figure_render as mfr

    im = Image.new("RGB", (W, H), mfr.BG)
    d = ImageDraw.Draw(im)
    vx, vy = W * 0.44, H * 0.47
    for i in range(-9, 10):
        d.line([(W * 0.5 + i * W * 0.14, H), (vx, vy)], fill=(24, 40, 44), width=3)
        d.line([(W * 0.5 + i * W * 0.14, 0), (vx, vy)], fill=(20, 33, 36), width=3)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [vx - H * 0.14, vy - H * 0.14, vx + H * 0.14, vy + H * 0.14],
        fill=(70, 128, 122))
    glow = glow.filter(ImageFilter.GaussianBlur(H * 0.06))
    a = np.asarray(im).astype(np.float32) + np.asarray(glow).astype(np.float32)
    Image.fromarray(np.clip(a, 0, 255).astype("uint8")).save(out_path)
    log("    generate: drawn (no photograph available)")
    return os.path.exists(out_path)


# ── the entry point ────────────────────────────────────────────────────
def make(brief, out_path, work_dir=None, log=print, allow_network=True,
         used=None):
    """Render the frame this brief asks for. Returns (ok, route).

    Never raises and never returns without a frame unless the procedural
    fallback itself fails, which would mean PIL is broken.
    """
    prompt = brief.get("prompt") or ""
    why = refuse(prompt) if prompt else "no prompt on this brief"
    if prompt and why:
        # This is the lock. A brief should never have carried such a prompt --
        # visual_brief routes evidentiary beats away from generation -- so if
        # one arrives it is a defect worth shouting about, not a quiet skip.
        log("  REFUSED to generate: %s" % why)
        prompt = ""

    started = time.time()
    route = None
    if prompt and allow_network:
        for name, fn in (("cloudflare", _cloudflare), ("pollinations", _pollinations)):
            try:
                ok = (fn(prompt, out_path, log=log, seed=brief.get("index", 0))
                      if name == "pollinations" else fn(prompt, out_path, log=log))
            except Exception as e:
                log("    generate: %s raised (%s)" % (name, e))
                ok = False
            if ok:
                route = name
                break

    if route is None:
        try:
            if _abstracted(brief, out_path, log=log, used=used):
                route = "abstracted"
        except Exception as e:
            log("  generate: procedural failed (%s)" % e)
            return False, None

    if route and work_dir:
        record(work_dir, {
            "index": brief.get("index"),
            "intent": brief.get("intent"),
            "subject": brief.get("subject"),
            "route": route,
            "prompt": prompt or None,
            "refused": why if (brief.get("prompt") and why) else None,
            "beat": (brief.get("text") or "")[:180],
            "seconds": round(time.time() - started, 1),
        })
    return bool(route), route
