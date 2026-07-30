# No Known Cause — YouTube Studio setup

Copy-paste source of truth for the Ch1 channel's Studio fields. Kept in the
repo (not just in chat) so the About text, the on-screen label, the spoken
CTAs and the video-description block can be checked against each other.

Regenerate the art with:

    python3 tools/build_channel_branding.py branding

---

## 1. Basic info

| Field | Value |
|---|---|
| Channel name | `No Known Cause` |
| Handle | `@NoKnownCauseTV` — claimed |
| Category (per video) | Education |
| Language | English |
| Country | (your own) |
| Made for kids | **No** — set at channel level AND leave the per-video default at "No" |

The handle is not just an About-tab field: it is burned into every Short's
watermark and printed in all four other channels' cross-promo blocks. If it
ever changes again, the code has to change in the same commit, or Ch2-Ch5
start advertising a handle that resolves to nothing.

---

## 2. Channel description (About tab)

YouTube's limit is 1000 characters. This is 988.

```
Every episode is one real medical case, taken from a published, peer-reviewed paper in the open-access literature.

A patient arrives with something that does not fit. The first answer is wrong. We follow the actual clinical course — the real test results, the real imaging, the real timeline — up to the finding that finally explains it.

No dramatisations. No composite patients. No invented details. Every episode names the paper it came from, and every figure on screen is reproduced from that paper under its Creative Commons licence, credited where it appears.

Covering toxicology, diagnostic odysseys, rare disease, neurology, outbreak investigations, surgical cases, drug discovery, sleep medicine, longevity research, and the history of medicine.

New case every weekday.

This channel is educational commentary on published medical literature. It is not medical advice, diagnosis, or treatment guidance. Always consult a qualified healthcare professional about your own health.
```

The last paragraph is not optional. YouTube's 2026 guidance treats an AI
presenter giving medical guidance as a restricted category; the channel-level
disclaimer plus the per-video one is what keeps this on the commentary side of
that line. The same wording is enforced per-video by
`medical_policy_gate.build_disclaimer_block()`.

---

## 3. Keywords

Settings → Channel → Basic info → Keywords. 500-character limit; this is 435.
Comma-separated, no hashes.

```
medical case study, case report, clinical case, medical mystery, diagnosis, differential diagnosis, misdiagnosis, toxicology, poisoning case, rare disease, neurology case, medical documentary, peer reviewed research, open access medicine, medical education, clinical medicine, medical history, drug discovery, sleep medicine, outbreak investigation, epidemiology, surgical case, patient case study, hospital case, published case report
```

---

## 4. Banner links (max 5, shown over the banner)

Order matters — the first is the most prominent.

1. `Europe PMC — our sources` → https://europepmc.org/
2. `The Evidence Room` → https://youtube.com/@TheEvidenceRoom
3. `The Control Files` → https://youtube.com/@TheControlFiles
4. `The Archive` → https://youtube.com/@TheArchiveFiles
5. `The Collapse Index` → https://youtube.com/@TheCollapseIndex

Linking the source database first is deliberate. It is the fastest way for a
sceptical viewer to confirm the channel's central claim, and no competing
channel in this space can copy it without also sourcing real papers.

---

## 5. Artwork

| Asset | Size | File |
|---|---|---|
| Banner | 2048×1152 | `branding/banner_2048x1152.png` |
| Profile picture | 800×800 | `branding/profile_800x800.png` |
| Video watermark | reuse the profile picture | — |

`_safe_area_check.png` is a diagnostic overlay showing YouTube's three crop
regions. Do not upload it.

Set the watermark to display **"Custom start time" at 00:00:20**, not "entire
video" — a permanent overlay competes with the burned-in figure attributions,
which are legally required and must stay legible.

---

## 6. Upload defaults

Settings → Upload defaults.

**Read this before filling anything in:** upload defaults apply to *manual*
uploads only. The pipeline sets title, description, tags, privacy and category
explicitly on every API upload, so those five Studio defaults are silently
overridden and cannot be used to control automated behaviour.

Two consequences worth being clear about:

- Setting "Education" here does **not** make uploads Education. That is
  `categoryId` in `upload_yt()`, now `27`.
- Setting visibility "Private" here does **not** protect a test run. The
  pipeline uploads `privacy="unlisted"` and only flips to public after the
  human review gate passes.

- Title: **leave blank.** A stale default title is worse than none — it will
  silently attach itself to any manual upload you forget to retitle.
- Description: set (see below) — additive, and useful on a manual upload.
- License: Standard YouTube License
- Comments: **Hold potentially inappropriate comments for review** (raise to
  "Hold all comments" if self-diagnosis comments become a problem — medical
  content attracts them, and an unreviewed thread of strangers diagnosing each
  other under your video is a real moderation liability)
- Allow embedding: on
- Publish to subscriptions feed: on
- Altered/synthetic content: the pipeline already declares this per-upload via
  `containsSyntheticMedia=True`. Do not also toggle it manually.

### Default description (manual uploads only)

```
Every episode of No Known Cause is one real medical case, taken from a published, peer-reviewed paper in the open-access literature. The source is named in full, and every figure on screen is reproduced from that paper under its Creative Commons licence.

New case every weekday.

Our sources: https://europepmc.org/

More from this network:
The Evidence Room — https://youtube.com/@TheEvidenceRoom
The Control Files — https://youtube.com/@TheControlFiles
The Archive — https://youtube.com/@TheArchiveFiles
The Collapse Index — https://youtube.com/@TheCollapseIndex

———
This video is educational commentary on published medical literature. It is not medical advice, diagnosis, or treatment guidance. Always consult a qualified healthcare professional about your own health.
```

### Default tags

```
medical case study, case report, clinical case, medical mystery, diagnosis, differential diagnosis, medical documentary, peer reviewed, open access research, medical education
```

---

## 6b. Community moderation

Settings → Community → Automated filters.

**Blocked words hold a comment for review — they do not delete it.** That is
exactly the behaviour wanted here: on a medical channel the dangerous comment
is not the rude one, it is the sincere one asking to be diagnosed, or the
confident stranger telling someone to stop their medication. Both need a human
to see them before the public does.

Also switch **Block links: ON**. Links in comments under medical content are
overwhelmingly supplement sales and misinformation, and there is no
counterbalancing benefit — a viewer with a real citation can name the paper.

**Tier 1 — advice-seeking (the liability tier).** Paste all of these:

```
do i have, do you think i have, what do i have, diagnose me, can you diagnose, am i dying, is this normal, should i be worried, should i see a doctor, my symptoms, i have these symptoms, i have the same, what should i take, what should i do about, is it serious, my doctor said, what medication, how do i treat, please help me, is this cancer
```

**Tier 2 — dangerous advice from other commenters.** These matter more than
Tier 1: a wrong answer left standing under your video is worse than an
unanswered question.

```
stop taking, don't take your, quit your meds, off my meds, throw away your, cure for, cures cancer, cured my, miracle cure, natural cure, big pharma, doctors won't tell you, doctors don't want you, detox your, alkaline, colloidal silver, black salve, apricot kernel, miracle mineral, hydrogen peroxide cure, bleach cure
```

**Tier 3 — pharmacy, supplement and controlled-substance spam.**

```
no prescription, online pharmacy, buy now, order now, dm me, message me on, whatsapp, telegram me, wa.me, t.me, click here, link in bio, check my profile, discount code, cialis, viagra, xanax, adderall, oxycodone, tramadol, percocet, vicodin, weight loss pills, get ripped
```

**Tier 4 — generic scam and engagement spam.**

```
crypto, bitcoin, forex, binary options, investment opportunity, earn money, make money online, financial freedom, sub4sub, sub for sub, subscribe to me, check out my channel, free giveaway, you have won, claim your prize, congratulations you
```

Two honest caveats:

- Tier 2 will occasionally hold a legitimate comment, because a real
  toxicology episode may genuinely discuss hydrogen peroxide or a detox
  protocol. Holding is cheap; a public thread of strangers giving each other
  treatment advice is not.
- Review the held queue in the first weeks. If Tier 1 is holding too much
  ordinary curiosity, cut `is this normal` and `i have the same` first — they
  are the broadest phrases in the list.

If the queue ever becomes unmanageable, escalate the **Defaults → Comments on
new videos** setting to "Hold all comments for review" rather than adding more
blocked words.

---

## 6c. Channel guidelines + welcome message

Settings → Community → Defaults. YouTube allows **up to 3** guidelines, shown
to a viewer before they comment for the first time (mobile for comments and
Community posts; desktop and mobile for live chat). Keep each to one line —
the field is short.

**Guideline 1**
```
Ask about the medicine, not about yourself — we can't diagnose anyone.
```

**Guideline 2**
```
Disagreeing is welcome. Cite the paper and we'll pin a good correction.
```

**Guideline 3**
```
No treatments, supplements, cures or links. Those get removed.
```

**Welcome message**
```
Welcome. Every video here is one real published case — same paper you can look up yourself, cited in the description. The best comments here catch something we missed or add a source. The one thing we can't do is tell you what's wrong with you, so please don't ask us to.
```

Guideline 2 is doing real work. A channel built on cited sources will attract
clinicians, and a pinned correction from one of them is the single strongest
credibility signal available — it proves the citations are being read.

---

## 7. Playlists

Do not create these by hand. `ensure_niche_playlist()` creates one playlist per
niche on first upload, which is what feeds the session-contribution signal the
2026 ranking model rewards.

Expected after the first few weeks, one per niche:
toxicology, diagnostic odysseys, rare disease, senior health & longevity,
outbreak investigations, surgical cases, neurology, medical history,
drug discovery, sleep science.

---

## 8. Not yet done

- **Channel trailer** — needs a real published episode first.
- **Product / merch shelf** — deliberately empty. The old Ch1 product was a
  psychology handbook, removed rather than repointed; a monetised medical
  channel up-selling a health-adjacent product is a trust and policy problem.
  Any replacement should be a non-medical product (e.g. a research-methods
  guide) or none at all.
