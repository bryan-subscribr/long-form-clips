---
name: clip-packaging
description: Write the YouTube title and thumbnail text for a clipped or highlight video (talking-head, podcast, Q&A, hot-seat, keynote excerpt, compilation) using the packaging system reverse-engineered from Alex Hormozi's clips channel @MoreMozi — every one of its 2,795 long-form clips measured (titles, OCR'd thumbnail text, 2,760 transcripts, views). Use when the user sends a clipped video file, a YouTube link, a transcript, or a folder of clips and asks for a title, thumbnail text, thumbnail copy, "package this", "title this", or wants a batch packaged for a clipping/highlights channel. Also use to audit or re-package an existing clip. Speaker-agnostic: calibrated on Hormozi, with transfer rules for any authority-style speaker.
---

# clip-packaging

You receive a clip. You return **three ranked packages** (title + thumbnail text + design note + the timestamp of the spoken line the thumb comes from), then a recommendation. Batch mode returns one block per clip plus a summary table.

The system comes from measuring everything @MoreMozi published between Sep 2025 and Sep 2026. All numbers below are from that corpus. The full evidence is `references/moremozi-analysis.md`; the operating rules are here.

## The law

**Title = the viewer's situation. Thumb text = the speaker's payoff. They never say the same thing.**

- 91% of 779 text thumbnails share zero content words with their title (mean overlap 4%).
- The title's material is spoken 2–7% into the clip. The thumb's line is spoken at a median of 31% in, a quarter of the time after the 62% mark.
- Test: cover the thumb and read the title alone — you should want the answer. Cover the title and read the thumb alone — it should sound like something a person actually said, and make you want to know why.

Everything else is procedure.

## Files in this skill

| File | Use it for |
|---|---|
| `references/title-patterns.md` | 14 archetypes with templates, medians, 10+ real examples each, when/when-not, punctuation and number conventions |
| `references/thumb-text-patterns.md` | 7 thumb-text types with 15+ examples each, sourcing rules, title↔thumb pairing matrix, pixel-level design spec |
| `references/rewrite-drills.md` | 100+ real transcript→title and transcript→thumb rewrites with the reasoning |
| `references/worked-examples.md` | 6 complete walkthroughs, one per clip format, on real clips with real transcripts and the channel's actual result |
| `references/anti-patterns.md` | The channel's own floor (bottom 80 clips) sorted into 12 failure types |
| `references/scoring-rubric.md` | 100-point rubric for ranking packages |
| `references/speaker-adaptation.md` | Transfer rules for non-Hormozi speakers, with transformed examples |
| `references/batch-and-ledger.md` | Batch workflow, ledger schema, re-upload rules |
| `references/moremozi-analysis.md` | The full measured analysis |
| `references/examples-title-thumb-pairs.md` | All 779 title‖thumb pairs, by views |
| `scripts/transcribe.py` | Video/audio/URL → timestamped transcript |
| `scripts/extract_materials.py` | Transcript → candidate stinger lines, numbers, questions, self-intro, with timestamps |
| `scripts/check_package.py` | Mechanical checks: overlap, length, case, banned words, quote style |
| `scripts/thumb_preview.py` | Render the thumb text onto a frame in the channel's layout (Montserrat SemiBold, yellow accent) |

Read `worked-examples.md` before your first package in a session. Read `rewrite-drills.md` when a rewrite feels flat.

## Run order

### 0. Intake

Identify what you were given and what the user runs:

- **Input:** video file (mp4/mov), audio, YouTube URL, transcript text, or a folder (batch).
- **Speaker:** who talks, how famous, what register (blunt authority / warm coach / analyst / comedian). Default = Hormozi-class authority. If not Hormozi, read `speaker-adaptation.md` before step 4.
- **Channel context** if given: niche, current median views, whether text thumbnails are already in use, past titles (for the no-repeat check).

Do not ask the user for any of this if it can be inferred. Proceed.

### 1. Transcript

```
python3 scripts/transcribe.py <file-or-url> --out <slug>.transcript.txt
```

Faster-whisper `small.en` (≈1× realtime on CPU); `--model base.en` for speed on long clips; YouTube URLs use auto-captions when they exist (seconds, not minutes). Output: `start\tend\ttext` lines plus a plain paragraph. Read the whole transcript. Clips are 1–15 minutes; a compilation is 60–80 and you read the first 10 minutes plus each segment's first minute.

### 2. Classify the clip

The first 20 seconds tell you the format, and the format picks the default title archetype.

| Format | Signature in transcript | Frame | Default archetype | Fallback |
|---|---|---|---|---|
| **Hot-seat** | "I sell X to Y. We do $Z. What's stopping me is…" or host reads "top line 20K a month… what are you selling?" | stage + owner at mic, or Hormozi Hotline call | `Helping a [$Rev] [Niche] [Scale/Fix/Get] [to $Goal]` | Owner's problem as quoted first-person Q with persona sentence |
| **Audience question** | A question in the first 20s, then the speaker answers; often "Alex, how do I…" or a read-aloud submitted question | podium or desk | Quoted first-person question | `If You…, Do This` conditional |
| **Podcast answer** | Host prompt, speaker riffs; story-heavy; watermark (Modern Wisdom, Iced Coffee Hour) | two-shot or guest close-up | `Why …` / `The … That …` / `You …` verdict | `I …` story |
| **Solo monologue** | No question; speaker teaching or arguing from line one; studio logo backdrop | single, centred | `How to …` / `You …` / `If You're …, Do This` / `Stop …` | Free-form claim |
| **Hypothetical prompt** | "If you had to go from zero to $100K in 3 months, how would you do it?" | any | `If I Wanted …, I'd …` / `How I'd …` | `If You …` |
| **Compilation** | Multiple segments, 60–80 min | any | `[Lead question or how-to] \| 1 Hour of [Speaker] on [Topic]` | `[Speaker]'s Best Advice on [Topic] \| 1 Hour Compilation` |

Openings across the corpus: statement cold-open 48%, question first 20%, hot-seat self-intro 18%, mid-thought ("And so…") 14%. Mid-thought and statement openings are usually solo or podcast; the editor cut into the answer.

### 3. Mine the raw materials

Run `python3 scripts/extract_materials.py <slug>.transcript.txt` to get a first pass (short punchy lines, numbers, questions, self-intro, first-person emotional lines, all with timestamps). Then read and correct it by hand. You need seven things written down before drafting:

1. **The asked question, verbatim**, with the asker's self-description. ("I'm 21, broke, supporting my mom with cold calls I hate." "We do $2.5M, I'd like to be at $12M.")
2. **The core claim**: the one sentence the clip exists to deliver. It is almost always inside the first 15%. If two claims compete, note both; one goes to the title, the other may go to the thumb.
3. **Stinger lines**: every 1–5 word phrase that stands alone as a caption. Include the asker's words. Note the timestamp. Typical yield: 6–15 per clip. ("you sound poor" · "two hands, no excuses" · "it's supposed to hurt" · "sucking sucks" · "punched above his weight class" · "the work needs doing")
4. **Numbers and stakes**: dollars, counts, timeframes, percentages, ages. ("$100 for a hat" · "17 hour days" · "100 DMs a day" · "0.71 correlation" · "lost 30% of clients")
5. **The counterintuitive verdict**: what the viewer would not expect this speaker to say. ("Don't change your selling model." "Do it for free." "You need less variety than you think." "Quit.")
6. **The persona**: who the viewer will identify as. (agency owner stuck at $90K · 37-year-old asking if it's too late · firefighter with a $1.2M side business)
7. **The emotional beat**, if any: the asker's raw line or the speaker's confession. ("Now she's gone." · "I feel bad" · "I ruled by fear")

If the clip has none of 3–5, it is a weak clip; say so and package it anyway with the best available.

### 4. Titles: write 5, keep 3

Read the archetype table in `title-patterns.md` and pick candidates from at least three different archetypes. Constraints, all measured:

- **30–55 characters**, target 35–48. Channel median 43 / 8 words. The 30–40 band has the best median views (2,800); over 50 characters never outperforms.
- **Title Case** (83% of corpus). Lowercase-start titles exist (0.9%) but read as accidents.
- **Straight double quotes** for viewer questions (475 straight vs 43 curly). Question mark inside the closing quote. No trailing period on questions.
- **Viewer frame for questions**: first person, 80% contain I/My/Me. Keep the stake and the number, delete the asker's context, add one edge word where the speaker's answer earns it: *Even, Actually, Still, Really, Way Too, Only, Ever, Just*. (`"Is Gen Z Even Competent Enough to Hire?"` · `"Why Am I Still Broke?"` · `"Am I Actually Working Hard Enough?"`)
- **Speaker frame for claims**: absolutes stay (*Always, Never, Most, Nobody, Everyone, 99%*). `Why Small Business Owners Always Undercharge`, not `Why Some Business Owners Undercharge`.
- **Numbers**: `$1M`, `$100K`, `$2.4M` (never `$1,000,000`; `$2,000` only when under $10K). `90 Days`, `8 Hours`, `28 Hours a Week`, `99% of People`. Digits, not words, except idiomatic `One Thing`, `One Hour`, `Five Clients`.
- **Two-sentence titles** (7%) carry persona + question or claim + consequence: `"I Have 150K Followers. Why Am I Still Broke?"`, `You Don't Need 10 Years. You Need One Hour.` Period after the first sentence, Title Case both.
- **Parentheticals** are rare (2%) and only as a payoff hint: `(Do This Instead)`, `(and How to Fix It)`, `(You're Distracted)`.
- **Specific beats generic in every archetype.** Before keeping a title ask: could this title sit on 50 other clips? If yes, add the niche, the number, the stage, or the tension. `Helping a Marketing Agency Scale` (floor, 6 uploads) vs `Helping an Agency Owner Stuck at $90K Scale to $900K` (23K).
- **Never**: speaker's name in the title (except compilations), `Reveals/Explains/Shares/Describes` (the channel's oldest floor: `Alex Hormozi Reveals The MOST Powerful Marketing Strategy` 63 views), ALL CAPS words, "insane/shocking/secret", `#1`, emoji, trailing `...` unless the clip is literally a one-liner, `2023`-style stale years, generic nouns as the whole title (`Take Responsibility`, `Act with Urgency`, `The Overnight Success`: 225, 28, 28 views).
- At least one candidate must be a straight rewrite of what the clip *is* (the question, or the claim). At least one must take a side (`You …`, `Why …`, `Stop …`).

### 5. Thumb text: write 5, keep 3

Read `thumb-text-patterns.md`. Constraints:

- **1–4 words**, median 3, median 17 characters. Distribution: 1 word 17%, 2 words 13%, 3 words 29%, 4 words 37%, 5+ 6%. Five words only as a verbatim quote that needs them.
- **Zero content-word overlap with the paired title.** Run `scripts/check_package.py`. Stopwords don't count; everything else does, including the title's noun.
- **From the clip.** 12% exact, 25% two-word fragment, 35% key words of a spoken line, 29% tight paraphrase. Prefer spoken. When you paraphrase, it must be the *opposite* or the *consequence* of something said (`You Need to Sell Stories.` → *Nobody Buys Spreadsheets*).
- **Mix types across candidates**: verdict phrase (34%), 1–2 word label (26%), number (15%), contrast (13%: `X but Y` / `X, not Y` / `all X, no Y` / `Two hands. No excuses.`), raw quote in quotes (5%), command (4%), you-verdict (2%).
- **Quotes**: curly `"…"` only when it is the asker's or speaker's literal words and the quotation is the point (`"I feel bad"`, `"40% is too much"`, `"I am inevitable"`). Verdicts rendered as captions take no quotes.
- **Case**: Sentence case default; lowercase start for a casual spoken feel (`it compounds daily`, `nobody's watching`); ALL CAPS for ≤3-word commands and number slabs (`ONE SKILL ONLY`, `$10K A DAY`, `STOP WAITING`). Period only for a blunt verdict (`Just Start.`, `Sucking sucks.`, `They ghosted me.`).
- **Mark the accent word** in `**bold**`: the noun that carries the pain, or the number. 55% of text thumbs have one yellow word; it is almost always the last content word. (*Price is the **signal*** · *Famous but **poor*** · *All growth, no **profit*** · ***$300** a month forever*.)
- **Must read at 320 px wide**: no clause structure, no commas except in a contrast pair, no words over 12 letters unless alone.

### 6. Pair, check, rank

Build the 3×3 grid of kept titles × kept thumbs; keep the three pairs that pass:

1. **Complement**: title asks, thumb answers — or title claims, thumb proves (number) or sharpens (harder verdict). If both say the same idea in different words, fail.
2. **Standalone**: the thumb makes sense with the title hidden.
3. **Delivered**: the thumb's line is spoken in the clip, ideally before the two-thirds mark. Paraphrase is allowed; invention is not.
4. **Zero overlap**: mechanical.
5. **Not used before** on this channel (check the ledger if one exists; the channel re-uses titles deliberately, but only proven ones).

Score with `scoring-rubric.md` (archetype ceiling 25, specificity 20, thumb strength 20, complement 15, brevity 10, deliverability 10). Rank.

### 7. Output

```
## Package 1 (recommended)
Title:  "How Do I Land Rich Clients With Small Case Studies?"   (51 chars · Quoted-Q)
Thumb:  Punch above your **class**
Line:   1:22 "he punched way above his weight class because he made a truly risk-free offer"
Why:    viewer-frame question carrying the exact objection; thumb is the speaker's verdict, zero overlap, spoken at 48%
Design: white Montserrat SemiBold, bottom-left, "class" in #FEF731, speaker mid-gesture frame from ~1:20

## Package 2
…
## Package 3
…

Pull-quotes considered (mm:ss → line): 0:18 "people don't buy because of risk, period" · 0:34 "sink the price to zero" · 1:22 "punched above his weight class" · 2:26 "then you can charge the premium prices"
Rejected titles: … (one reason each)
```

Then one line: which to ship and why. If the user says "just give me the title and thumb", give Package 1 as two lines.

Optional: `python3 scripts/thumb_preview.py <frame.jpg> "Punch above your **class**" -o preview.jpg` to show the layout. Optional: `vidiq_score_title` on the three titles if the VidIQ MCP is connected; it catches clarity misses but does not know the overlap rule — never let it override.

### 8. Batch mode

Folder or list of URLs → transcribe all first (`transcribe.py` per file; parallel is fine), then package each, then a summary table `clip · format · title · thumb · accent word · pull-quote timestamp`. Enforce **no duplicate archetype more than 40% of a batch** and **no repeated thumb word across the batch** unless the user runs a series. Append to the ledger (`batch-and-ledger.md`).

### 9. Audit / re-package mode

Given an existing title+thumb: score it with the rubric, name the failing rule with the channel's own floor example of the same failure (`anti-patterns.md`), then produce three replacements. If the clip previously did well, propose a re-upload package with a *different* thumb line and the same or near-same title — that is what the channel does (108 titles re-used; the 496K clip ran three times).

## Adapting to another speaker

Read `speaker-adaptation.md`. Short version: the two-frame law and the design system transfer as-is; the *authority register* does not. A less established or warmer speaker moves verdicts out of the title into the thumb, leans on quoted viewer questions and `If You're …, Here's What …`, and never uses the speaker's name. Numbers only if spoken.

## Never

- A thumb that is the title shortened.
- A stat, quote, or dollar figure the speaker did not say.
- A title that could sit on 50 other clips.
- The speaker's name, "Reveals/Explains", ALL CAPS, or a stale year in a title.
- Fewer or more than three packages unless asked.
- Skipping the transcript read because the title "is obvious".
