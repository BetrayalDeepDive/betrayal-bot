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
| Handle | `@NoKnownCause` (fallback if taken: `@NoKnownCauseTV`) |
| Category (per video) | Education |
| Language | English |
| Country | (your own) |
| Made for kids | **No** — set at channel level AND leave the per-video default at "No" |

If the handle falls back to `@NoKnownCauseTV`, the code must change too —
it is referenced in Short watermarks and in all four other channels'
cross-promo blocks. One command, but it has to happen before the run.

---

## 2. Channel description (About tab)

YouTube's limit is 1000 characters. This is 986.

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

Settings → Channel → Basic info → Keywords. 500-character limit; this is 476.
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

- Title/description: leave blank — the pipeline writes both
- Visibility: **Private** for the first run, so nothing publishes while testing
- Category: Education
- License: Standard YouTube License
- Comments: **Hold potentially inappropriate comments for review** (raise to
  "Hold all comments" if self-diagnosis comments become a problem — medical
  content attracts them, and an unreviewed thread of strangers diagnosing each
  other under your video is a real moderation liability)
- Allow embedding: on
- Publish to subscriptions feed: on
- Altered/synthetic content: the pipeline already declares this per-upload via
  `containsSyntheticMedia=True`. Do not also toggle it manually.

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
