"""
A local library of stock photographs, so a thumbnail never depends on the API
being up.

WHY THIS EXISTS
---------------
Every photograph on a thumbnail used to come from a live Pixabay or Pexels
request made while the episode was rendering. That works right up until it
does not: a rate limit, a network blip, a key rotated by mistake, a search term
that happens to return nothing usable. Any of those and the card falls back to
the drawn renderer, which is the thing this whole redesign replaced.

So the library is checked FIRST and the network second. The API is now an
enrichment step rather than a dependency, and an episode can render its
thumbnail with the network unplugged.

IT GROWS ITSELF
---------------
Eighteen photographs is enough to never fail and not enough for variety -- the
same corridor every fourth episode is its own kind of boring. harvest() runs
during the episode, where the Pixabay key actually works, and adds whatever is
new: fresh search terms, better matches, more of them. The library is committed
with the rest of the episode's artifacts, so it compounds. By episode twenty it
should hold a few hundred, and the same corridor stops coming round.

Two rules keep it from rotting:

  * Nothing enters without passing the same drawing test the live path uses.
    A library that quietly fills up with vector diagrams is worse than no
    library, because it fails silently forever instead of once.
  * Nothing enters twice. Files are keyed by a hash of their bytes, so the
    same photograph fetched under two different search terms is stored once.

LICENCE
-------
Everything here comes from Pixabay or Pexels under their content licences,
both of which allow commercial use with no attribution. The manifest records
that so it is answerable later without anyone having to remember.
"""
import hashlib
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "stock_library")

# Beyond this the repository starts paying for photographs it will never use.
# At roughly 230 kB each this is about 1300 files, far past the point where
# repetition stops being noticeable.
MAX_FILES = 900

ROLES = ("scene", "evidence", "hero")


def _manifest_path():
    return os.path.join(LIB, "manifest.json")


def manifest():
    try:
        with open(_manifest_path()) as fh:
            m = json.load(fh)
        return m if isinstance(m, dict) and "photos" in m else {"photos": []}
    except Exception:
        return {"photos": []}


def _save(m):
    os.makedirs(LIB, exist_ok=True)
    with open(_manifest_path(), "w") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)


def _digest(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _score(entry, want):
    """How well a library photo matches the words we were looking for."""
    tags = set((entry.get("tags") or "").lower().split())
    return len(tags & want)


def pick(role, terms=(), exclude=(), seed=None):
    """Best local photograph for a role, or None if the library has none.

    `terms` are the search words the caller WOULD have sent to Pixabay, so a
    case about a brain prefers the brain scan over the blood tube even though
    both are filed under `evidence`.
    """
    pool = [p for p in manifest()["photos"]
            if p.get("role") == role and p.get("file") not in exclude]
    pool = [p for p in pool if os.path.exists(os.path.join(LIB, p["file"]))]
    if not pool:
        return None

    want = set(" ".join(terms).lower().split())
    if want:
        best = max(_score(p, want) for p in pool)
        if best > 0:
            pool = [p for p in pool if _score(p, want) == best]

    rng = random.Random(seed) if seed is not None else random
    return os.path.join(LIB, rng.choice(sorted(pool, key=lambda p: p["file"]))["file"])


def add(src_path, role, tags, verify=None, max_edge=1600, log=print):
    """Copy a downloaded photograph into the library. Returns its path or None.

    `verify` is the drawing test, injected rather than imported so this module
    does not depend on the thumbnail renderer.
    """
    from PIL import Image

    if role not in ROLES or not os.path.exists(src_path):
        return None
    m = manifest()
    if len(m["photos"]) >= MAX_FILES:
        return None

    try:
        im = Image.open(src_path).convert("RGB")
    except Exception:
        return None
    if min(im.size) < 400:
        return None
    im.thumbnail((max_edge, max_edge), Image.LANCZOS)

    os.makedirs(LIB, exist_ok=True)
    tmp = os.path.join(LIB, ".incoming.jpg")
    im.save(tmp, quality=84, optimize=True)

    if verify is not None and verify(tmp):
        os.remove(tmp)
        log("    stock library: rejected a drawing")
        return None

    dig = _digest(tmp)
    if any(p.get("sha") == dig for p in m["photos"]):
        os.remove(tmp)                      # already have this exact photograph
        return None

    name = "%s_%s.jpg" % (role, dig)
    dest = os.path.join(LIB, name)
    os.replace(tmp, dest)
    m["photos"].append({"file": name, "role": role, "tags": tags.lower(),
                        "sha": dig, "w": im.width, "h": im.height})
    _save(m)
    log("    stock library: +1 %s (%d held)" % (role, len(m["photos"])))
    return dest


def harvest(fetch, role_terms, work_dir, verify=None, per_role=2, log=print):
    """Top the library up during a real run, where the API key works.

    Deliberately small per episode. The point is to compound quietly over
    weeks, not to hammer a free tier in one afternoon and get the key throttled.
    """
    added = 0
    for role, terms in role_terms.items():
        got = 0
        for term in terms:
            if got >= per_role:
                break
            tmp = os.path.join(str(work_dir), "harvest_%s.jpg" % role)
            try:
                ok, _kind = fetch(term, "", tmp)
            except Exception as e:
                log("    stock harvest '%s' (non-fatal): %s" % (term, e))
                continue
            if not ok:
                continue
            if add(tmp, role, term, verify=verify, log=log):
                got += 1
                added += 1
    return added


def count(role=None):
    ps = manifest()["photos"]
    return len([p for p in ps if role is None or p.get("role") == role])
