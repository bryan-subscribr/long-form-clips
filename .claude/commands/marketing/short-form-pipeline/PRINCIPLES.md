# Short-Form Repurposing Principles

These are the viral short-form principles the pipeline is built around, distilled
from a reference podcast with a top short-form creator. The segmentation prompt in
`scripts/shortform_pipeline.py` encodes them directly; the deterministic guard in
`guard_and_clamp()` and `AD_MARKERS` enforce the non-negotiable ones.

## Hooks (the highest-leverage lever)

- **"The best hooks don't have a hook."** Don't open on a preamble/wind-up
  ("I'm about to ask the craziest question", "you won't believe what happens").
  Start the clip *on* the shocking line, question, or claim. The video should feel
  like it already started.
- **A great hook does three things:**
  1. **Shock** — throws the viewer off ("wait, what did I just hear/see?").
     Ideally *visual*, because people see faster than they hear.
  2. **Clear expectation** — the viewer immediately knows what they'll get.
  3. **Open loop** — a reason to watch to the end.
- **Curiosity formula:** be *specific about WHAT* is going to happen, but withhold
  *HOW* it happens. Vague teasing ("you won't believe the end") does not work.
- It must feel like a **human conversation**, never a robot.

## Editing / repurposing

- **Cut ALL the fluff.** A repurposed clip must be edited to stand alone as a native
  Short — not a raw clip. **Sponsor reads and subscribe asks never belong in a clip.**
- **One complete idea per clip.** One framework, story, claim, or revelation.
- **End on a complete thought** — never mid-sentence.

## YouTube-native

- YouTube rewards **storytelling / narrative / journey**.
- Output is **9:16 vertical, 1080×1920** — native to Shorts.
- More "edited" feel than raw TikTok.

## Titles, captions, comments

- **Thumbnails don't matter on Shorts** (views come from the feed). **Titles matter
  "kind of"** — keep them short (< ~40 chars), complement the video, hint at the
  payoff. Not clickbait.
- **Design the comment section.** A strong pinned comment / comment-bait (an
  (un)popular-opinion or Easter-egg angle) that sparks emotion drives replies — and
  replies pull viewers back into the app, which the algorithm rewards. Never offensive.
- **Spark controversy without being controversial** — a relatable unpopular opinion,
  not an offensive take.

## Linking long-form (optional)

- You *can* link the long-form from a Short, but conversion is low (~0.1–1%), so it's
  off by default — a soft reference, not a hard CTA.

---

The full source transcript lives in `data/fixtures/reference-transcript.txt`.

---

# Horizontal (Long-Form Clip) Mode — `--aspect 16:9`

Same brain, different container. A 20–100 min piece becomes **standalone 16:9
clips of 4–5 minutes or longer** for the speaker's channel. Rendered with
`render_clips.py --aspect 16:9`. What changes vs Shorts:

## Length & count

- **Target 4–5 min or longer per clip.** One throughline, several beats
  (story → framework → payoff). A 2–3 min clip is fine *occasionally* when the
  idea is a natural unit (a rapid-fire game, a single story), not the default.
  Hard ceiling 15 min. Anything under ~90s is a Short — cut it vertical instead.
- **Prefer merging adjacent beats over splitting them.** If two neighbouring
  segments share a throughline the host bridges ("what about…", "so how do
  you…"), cut them as one longer clip rather than two 3-minute ones.
- **Count follows the content, not a quota.** 30 min → typically 3–5 clips;
  84 min → 6–9. Never pad to hit a number. Every clip must pass the standalone
  test below.
- **Zero overlap between clips.** Each clip is a different idea. If two
  candidates share a story or framework, merge or pick one.

## The standalone test (every clip must pass all five)

1. **Cold viewer understands it.** Zero context of the long-form needed. Names,
   acronyms, and "as I said earlier" references are either explained inside the
   clip window or the window moves to include the explanation.
2. **Starts ON the shock / question / claim.** No host intro, no "so anyway",
   no "let's talk about", no wind-up. Cut on the first word of the line that
   makes a viewer sit up.
3. **One complete arc: setup → tension → payoff.** One story, one framework,
   or one argument. Not two half-ideas.
4. **Ends on the payoff or punchline** — a complete sentence, ideally the
   strongest line — never mid-sentence, never on a trailing "yeah", "right?",
   or the start of the next topic.
5. **No fluff inside the window.** Sponsor reads, subscribe/like asks,
   self-promo, housekeeping, inside jokes, tangents that don't pay off — cut or
   skip the clip. `AD_MARKERS` is the deterministic backstop.

## Cutting mechanics

- Cut on **sentence boundaries** from the transcript. Pad ≤0.3s so the first
  word isn't clipped; don't pad into the previous speaker's sentence.
- Source stays uncropped: **1920×1080, H.264 + AAC**, letterboxed if the source
  isn't 16:9. No face-tracking, no zoom.
- **Captions are optional** for horizontal. Default ON (bottom, 3-word
  continuous highlight). Use `--no-captions` for a clean master and let
  YouTube CC handle it.

## Packaging (thumbnails matter here — unlike Shorts)

Title + thumbnail text come from the **`clip-packaging` skill**
(`~/.claude/skills/clip-packaging/SKILL.md`), measured on all 2,795 @MoreMozi
clips. That skill is the source of truth; the summary:

- **The law:** title = the viewer's situation, thumb text = the speaker's spoken
  payoff, **zero content-word overlap** (91% of top clips). Cover the thumb,
  read the title → you want the answer. Cover the title, read the thumb → sounds
  like something a person said.
- **Title:** 30–55 chars (target 35–48), Title Case, straight double quotes for
  viewer questions, digits not words (`$100K`, `90 Days`). Never the speaker's
  name, never `Reveals/Explains`, no ALL CAPS, no stale year, never a title that
  could sit on 50 other clips.
- **Thumb text:** 1–4 words (median 3), lifted or tightly paraphrased from a line
  spoken in the clip (ideally before the two-thirds mark), one accent word in
  `**bold**` → yellow `#FEF731`, must read at 320 px.
- **Speaker register:** not Hormozi → read `speaker-adaptation.md` first. A
  warmer or less famous speaker moves verdicts out of the title into the thumb
  and leads with quoted viewer questions / `If You're …, Here's What …`.
- **Plain beats clever.** Bryan's feedback on the first batch: `The $1.6M Pitch
  That Fooled a Sales Queen` "feels super AI". Constructions like *The X That
  Y'd a Z*, third-person epithets (*Sales Queen*, *She Doesn't Post Online*),
  and stacked modifiers read as machine-written. Prefer the clip's own words:
  `The Best Sales Pitch Ever Done on Me`, `Every Sales Objection Handled in
  6 Minutes`, `The Sales Trick I Never Post Online`.
- **On the speaker's own channel, write in their first person.** *I / Me / My*
  and *How I …* are right; *She / Her* is wrong (it's her channel). Quoted
  viewer questions still work.
- **Every number in a title is literally true of the clip.** `in 6 Minutes`
  only on a ~6-minute clip; `$1.6M` only if the clip says $1.6M; never a
  figure the speaker didn't say, and never claim an outcome that didn't happen
  (`This Pitch Made Me $1.6M` when the pitch was done *to* her).
- **Cut to fit the honest title.** If the strongest plain title only describes
  the first half of a long clip, split the clip rather than stretch the title.
- **Mechanical gate:** every shipped pair passes
  `python3 ~/.claude/skills/clip-packaging/scripts/check_package.py --title … --thumb … --transcript …`
  with exit 0 (overlap, length, case, banned words, thumb words spoken).
- **Batch rule:** no title archetype above 40% of the batch; no repeated thumb
  word across the batch.
- **Description:** most creators run one fixed channel boilerplate (masterclass
  link, origin story, sign-off). Ask for it once, save it as
  `CHANNEL_DESCRIPTION.txt`, and pass `--description-file` to
  `finalize_delivery.py` so every clip gets it verbatim. Only when no
  boilerplate exists: first line restates the payoff, then 3–5 hashtags.
  **Pinned comment** sparks replies (a relatable unpopular opinion or a "which
  one are you?" prompt). Never offensive.

## Per-clip fields in `clips.json`

`start`, `end` (MM:SS), `title`, `hook_line`, `open_loop`, `thumbnail_text`
(with `**accent**`), `thumb_line` (the spoken line + timestamp it comes from),
`thumb_frame_at` (absolute MM:SS of the spoken thumb line — the renderer runs
`pick_thumb_frame.py` over ±10 s of it and writes the best 1280×720 frame plus a
contact sheet of the top 6), `thumb_side` (`left|right|any`: where the speaker
sits in the two-shot), `caption`, `pinned_comment`. `render_clips.py` writes
them into `METADATA.md`.

## Thumbnail frame rule

The speaker must look **composed and impressive**: eyes open, mouth closed or
mid-smile, face large in frame, not mid-gesture, not caught between two
expressions. Never grab the frame at the exact second the line is spoken — that
lands mid-word. `pick_thumb_frame.py` ranks a ±10 s window on face size, single
subject, low motion, sharpness, eyes detected, and a still mouth region, then
writes `*.thumb-candidates.jpg`. On a two-person podcast pass `thumb_ref` (any
clean frame of the speaker) so the picker drops the host's reaction close-ups —
face-size alone cannot tell them apart. **Always look at the contact sheet**
before shipping; heuristics rank, eyes decide. Re-pick with `--pick N` if the
top score still looks off. If the **source has burned-in captions** or a
lower-third band, set `thumb_crop_bottom` (e.g. `0.15`) on the clip so the
picker crops that band off the frame before the thumb text goes on; the MP4
itself is never cropped. On a **single wide camera** the picker auto zoom-crops
around the speaker when the face is small (`--zoom-below`, default on) so the
face reads at MoreMozi size; hands and knees are ignored as face candidates
(only detections in the upper 55% of the frame count).
