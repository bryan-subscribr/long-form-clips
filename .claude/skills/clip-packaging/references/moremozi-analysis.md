# @MoreMozi packaging analysis — how titles and thumbnail text relate to what the clip says

Analysed 2026-09-22. Channel: MoreMozi (UCrvchO1h6lWZAuGaa1LqX9Q), Alex Hormozi's official clips channel ("Founder Acquisition.com, Co-Founder Skool.com"). Joined 12 Sep 2025. 139K subs, 58.6M total views, 6,528 uploads: **2,795 long-form clips** (20.7M views) and 3,722 Shorts (33.8M views).

Method: yt-dlp flat dump of every upload (titles, durations, views); all 2,795 long-form thumbnails downloaded at max resolution and OCR'd with macOS Vision (text, size, position, confidence), yellow-accent pixel detection; English auto-captions pulled for the long-form clips (transcript-based figures below state their sample size); Nexlev channel outliers (last 500 uploads) and VidIQ popular/breakout data for cross-checks.

---

## 1. What the channel is, mechanically

- **Volume.** ~7.6 long-form clips per day over the year; 20+ per day in the final week of the sample (2026-09-21: 24 uploads). Plus ~10 Shorts a day. This is an industrial clipping operation, not a curated one.
- **Length.** 3–5 min: 706 clips (median 2,050 views). 5–10 min: 1,083 (median 3,000). 10–20 min: 305 (median 5,100). 60+ min compilations: 60 (median 7,350). Longer clips earn more, the packaging rules do not change with length.
- **Distribution of outcomes.** Median 2,500 views, p75 6,300, p90 17,000, p10 578. Nexlev's rolling average over the last 500 uploads is 8,982. Winners are 40–200x the median (496K, 407K, 325K, 282K, 198K) and every one of the 40 Nexlev outliers (≥3x average) was uploaded Aug–Sep 2026 — after the text-thumbnail switch (section 4).
- **Five source formats**, recognisable from the first 20 seconds of transcript and from the frame:
  1. *Hot-seat workshop* — owner on stage: "I sell X to Y. We do $Z. What's stopping me is…" (32 thumbnails still carry the lower-third template text; 17% of transcripts open this way). Titles: `Helping a …` or the owner's question in quotes.
  2. *Audience Q&A* — someone asks, Alex answers (19% of transcripts open with a question).
  3. *Podcast guest* — Modern Wisdom (89 thumbnails carry the M|W watermark), Iced Coffee Hour, others. Longer, more story.
  4. *Solo studio monologue* — A-frame Acquisition.com logo backdrop, tank top or flannel; 52% of transcripts open on a statement cold-open.
  5. *Compilations* — 60–80 min, `| 1 Hour of Alex Hormozi on …`, red `1 HOUR` badge (39 thumbnails).

## 2. How the clips are cut (commonality across transcripts)

Sample: 2,760 clips with English captions (99% of the channel). Section 7 has the full table.

- **Opening.** 48% cold-open on a statement (often mid-idea — no "hey guys", no context). 20% open with the question being asked. 18% open with the hot-seat self-intro. 14% open mid-thought with a conjunction ("And so…", "Because…") — the editor cut into Alex already answering.
- **The title's material is front-loaded.** The transcript segment containing the most title keywords sits at a median of 2–7% into the clip; 64% (statements) to 75% (Helping-a) of clips have it inside the first 15%. Title keywords appear in the first 20 seconds for 34–41% of question clips vs 27% of statement clips and 16% of Helping-a clips.
- **The thumbnail's material is not front-loaded.** Of thumb texts traceable to a spoken line (71% of them), 39% come from the first fifth, median 31%, upper quartile 62%. The thumb is the payoff; the title is the setup. Editors clip so the setup lands immediately and the payoff is somewhere in the body.
- **Ending.** 48% end on the in-person workshop pitch ("we'll invite you out to Vegas and do this in person live"); 28% end on the scaling-roadmap CTA ("acquisition.com/roadmap, absolutely free… since you're a business owner, I appreciate you, enjoy"). The rest end on the last line of the answer. The CTA is appended to the clip, not spoken in context.
- **Titles are paraphrases of a real line 73–91% of the time**, never inventions. Examples (transcript → title):
  - "People obsessed with their morning routines make less money than people obsessed with making money" → `Morning routine obsessed people make less money`
  - "you don't find it, you create it" → `Why You Don't Find Your Passion, You Create It`
  - "traditionally small business owners will undercharge because they sell out of their own wallet" → `Why Small Business Owners Always Undercharge`
  - "If you can't sit still, ignore notifications, and focus on one task for eight hours straight, never expect to…" → `How to Train Your Brain to Focus for 8 Hours`
  - "how do I convince rich clients to hire me when my case studies are all from lower end small businesses" → `"How Do I Land Rich Clients With Small Case Studies?"`
  - "how do I train my perception to reach a higher price point… the most I have ever charged is 50,000" → `"How Do I Get Comfortable Charging More?"`
  - "Do you think Gen Z are still competent enough for business or are reliable workers?" → `"Is Gen Z Even Competent Enough to Hire?"` (sharpened: "Even")
  - Hot-seat: "We provide social media marketing… on pace for 2.7 million… biggest problem…" → `"I Run a Social Media Marketing Agency. How Do I Get Better Talent?"` (persona sentence + question sentence)

## 3. Title system

Full archetype table with medians in `title-patterns.md`. The load-bearing findings:

1. **Two frames.** Viewer-frame titles (quoted first-person questions, `If You're …`, `Helping a …`) describe the viewer's situation. Speaker-frame titles (`You …` verdicts, `Why …`, `The … That …`, `If I Wanted …, I'd …`) state the speaker's claim. Both work; the highest medians are speaker-frame conditionals (`If I Wanted …, I'd …` 6,950; `If You …, Do This` 5,500; `You [verdict]` 4,000) and the lowest are generic diagnoses (`Helping a … Scale` 2,000; unquoted questions 1,600).
2. **Quoted questions are the workhorse (18.5%)** and they are always rewritten into the viewer's first person (80% contain I/My). The rewrite keeps the stake and the number, drops the asker's context, and adds an edge word where possible ("Even", "Actually", "Still", "Way Too Little").
3. **Specificity is the difference between floor and ceiling inside every archetype.** `How to Get More Customers` 92 views vs `How to Find the Price People Will Actually Pay` 124K. `Helping a Marketing Agency Scale` (6 uploads, floor) vs `Helping an Agency Owner Stuck at $90K Scale to $900K` 23K.
4. **Length.** Median 43 chars / 8 words; the 30–40 char band has the best median (2,800). Nothing above 50 chars outperforms.
5. **Numbers help, dollar signs alone don't.** Digit-bearing titles median 3,000 vs 2,400; `$`-bearing titles median 2,200 because most `$` titles are Helping-a recaps. Use numbers as stakes or timeframes (`90 Days`, `8 Hours`, `200 Cold Calls`, `1 Habit`, `99% of People`).
6. **Re-upload proven packages.** 108 titles appear 2–7 times; 73 are the same clip re-uploaded. `You Can Have Everything You Want in 90 Days` ran three times: 496K (Sep 2025, thumb *Just Start.*), 407K (Aug 2026, thumb *17 hour work days*), 104K (Sep 2026 as `If You Want Everything, Give It 90 Days`, thumb *it compounds daily*). Same clip, new thumb line each time.
7. **Shorts use a different system** (3,722 items, median 1,300, best 559K): the title is the first sentence of the clip, lowercase, no question (6% have `?`), often long ("You can either do what's convenient and become acceptable or you can do what's required and bec…"). Do not port Shorts titles to long-form.

## 4. Thumbnail-text system

Full pattern list in `thumb-text-patterns.md`. Load-bearing findings:

1. **Adoption flipped in Aug 2026.** Text on 3–9% of thumbnails Feb–Jul 2026 (after a text-heavy launch month), 84% in Aug, 95% in Sep. In the newest 280 clips text thumbs median 5,600 vs 3,350 without (1.7x); next 280: 2,500 vs 1,350 (1.9x). 33 of the 40 current outliers have designed text.
2. **The text never repeats the title.** 91% of the 779 text thumbnails share zero content words with their title (mean overlap 4%). This is the strongest single rule in the corpus.
3. **It is the payoff line, in the speaker's voice.** 34% verdict phrases (*Price is the signal*, *Nobody Buys Spreadsheets*), 26% one/two-word labels (*Just Start.*, *CLOSER.*), 15% numbers (*17 hour work days*, *10,000x more input*, *100 DMs a day*), 13% contrasts (*Famous but poor*, *All growth, no profit*, *Sell outcomes, not sessions*), 5% raw quotes in quotation marks (*"I feel bad"*, *"40% is too much"*), 4% commands, 2% you-verdicts (*You sound poor*).
4. **Traceable to the transcript** (756 clips with both). 12% exact, 25% two-word fragment, 35% key words of a spoken line, 29% paraphrase. The quote type is used when the asker's own words are the hook (*"I can't find good people.."*, *"Lost my fiancée"*).
5. **Geometry.** 1–4 words (median 3, 17 chars); single line 79%; text block centred 15% from the bottom (82% in the bottom third); centred horizontally 64%, left-anchored 52%; line height 12–17% of frame; text spans ~68% of width. White geometric semibold sans (Poppins/Montserrat class) over a darkened frame; **one accent word in yellow #FEF731** in 55% of text thumbs (71% of the most recent 400) — the accent is the noun that carries the pain or the number. Face always visible; text never crosses the face. Red `⏱ 1 HOUR` pill top-left for compilations; small source watermark bottom-left for podcast clips.
6. **Pairing logic** (title → thumb):
   - question → verdict: `"How Do You Know How Wealthy Someone Really Is?"` → *You sound poor*
   - open conditional → the answer: `If I Wanted to Learn a Real Skill in 2026, I'd Do This` → *ONE SKILL ONLY*; `If I Wanted to Get Ahead of 99% of People, I'd Do This` → *while everyone sleeps*
   - verdict → proof number: `200 Cold Calls a Day Isn't Leverage` → *10,000x more input*; `You Can Have Everything You Want in 90 Days` → *17 hour work days*
   - verdict → sharper verdict: `You Need to Sell Stories.` → *Nobody Buys Spreadsheets*; `Why Most Ambitious People Waste Their 20s` → *Every Year Compounds*
   - situation → the asker's raw emotion: `A Client Owes Me $14K and Won't Answer. What Do I Do?` → *They ghosted me.*; `"I Have 150K Followers. Why Am I Still Broke?"` → *Famous but poor*

## 5. Top-40 outliers (Nexlev, ≥3x channel average) — title || thumb text

45.3x You Can Have Everything You Want in 90 Days || 17 hour work days · 36.2x How I'd Make $100K in 90 Days From Scratch || Two hands. No excuses. · 14.9x You're Not Ready for the Next Phase of Social Media || The Shift Already Started · 12.1x You Need to Prepare Before Social Media Changes Forever || (none) · 11.6x If You Want Everything, Give It 90 Days || it compounds daily · 10.9x You Decide You Want to Go Pro. || (none) · 9.7x Why Most Ambitious People Waste Their 20s || Every Year Compounds · 9.7x 200 Cold Calls a Day Isn't Leverage || 10,000x more input · 9.6x If I Needed More Customers in 2026, I'd Study This for 1 Hour || VALUE OVER VOLUME · 9.0x You Don't Need a Job First || (none) · 7.9x You Don't Need 10 Years. You Need One Hour. || Stop Waiting · 7.7x How to Reverse Engineer Any Skill You Want || 100 DMs a day · 7.6x If Prospects Keep Saying They'll Think About It, Ask This Instead || STOP BEING A NINNY · 7.0x If I Wanted to Learn a Real Skill in 2026, I'd Do This || ONE SKILL ONLY · 7.0x If I Wanted to Get Ahead of 99% of People, I'd Do This || while everyone sleeps · 6.3x If Your Offer Isn't Converting, Here's What to Fix First. || SKIP THE FREEBIE TRAP · 5.9x Is This a Battle Worth Fighting, or Should I Look for a New Job? || Sleeping with my rep · 5.8x How to Train Your Brain to Focus for 8 Hours || Embrace the suck · 5.7x The Ruthless Focus That Got Me to My First Million || Just say no · 5.5x "I Have a Small YouTube Channel, How Do I Make Money?" || nobody's watching · 5.3x You Have to Keep Going When It Feels Pointless || it's supposed to hurt · 4.9x The One Sentence That Shrinks Any Message by 5X || 5X LESS WORDS · 4.6x "Why Is Everything Taking So Long?" || Days turn into weeks. · 4.5x If I Wanted to Outwork My Excuses, I'd Work 28 Hours a Week || YOU'RE 1 IN 25 · 4.3x If You're Under $1M a Year, Here's What I'd Do in 2026 || $10K A DAY · 4.3x "Why Can't I Focus Long Enough to Get Anything Done?" || Sucking sucks. · 4.3x "How Do I Land Rich Clients With Small Case Studies?" || Punch above your class · 4.0x "I Raised Prices 40% and Lost Clients. Did I Mess Up?" || "40% is too much" · 4.0x "Why Do I Keep Missing My Goals?" || GOALS HAVE A PRICE · 3.9x Why I Refuse to Say I Have ADHD || (none) · 3.7x "Why Is Business So Hard, and How Do You Actually Win?" || it's supposed to hurt · 3.3x If I Were Paying Salespeople, I'd Do a 50/50 Split || $200K SKILL LEVEL · 3.3x How to Get Leads Without Being Salesy || MARKETING BEATS · 3.2x How to Decide What to Focus on When Everything Feels Urgent || Let it burn · 3.2x "What Am I Doing Wrong?" || "Just volume, bro" · 3.1x If You're Under 30 With No Kids, Work as Hard as You Can in 2026 || "I am inevitable" · 3.0x If I Needed More Customers in 2026, I'd Do This \| 1 Hour || 150 DMS A DAY · 3.0x Boring B2B Beats a Sexy Consumer Brand || $4.5M and flat · 3.0x "Why Am I the Only One Who Believes in Me?" || Don't lose the spark

Pattern in the top 40: 14 conditional/hypothetical titles (`If …`), 9 `You …` verdicts, 9 quoted questions, 6 how-to/the-X, 2 free-form. Every thumb is ≤5 words; 0 of 33 repeat a title word; 12 carry a number; 4 are raw quotes.

## 6. What transfers to another clipping channel

- The two-frame rule (title = situation, thumb = payoff, zero overlap) is speaker-independent.
- The archetype ceilings are Hormozi-calibrated. A less established speaker should lean on quoted viewer questions and `If You're …, Here's What …` conditionals and put the blunt verdicts in the thumb.
- The visual system (bottom-anchored white semibold, one yellow word, face visible, 1–4 words) is a generic high-legibility template; keep it.
- Volume + re-upload of proven packages is part of why the channel's outliers exist. A clipping channel should keep a ledger of packages and their results and re-run winners with a fresh thumb line.

## 7. Transcript-sample status — refreshed on 2,760 of 2,795 clips (99%)

English auto-captions were obtained for 2,760 long-form clips; the remaining 35 were unavailable (deleted or private). Final numbers, which supersede any smaller-sample figure above:

| Measure | Value (n) |
|---|---|
| Opening: statement cold open / question first / hot-seat self-intro / mid-thought | 48% / 20% / 18% / 14% (2,760) |
| Title keywords in first 20s — quoted Q / unquoted Q / statement / Helping-a | 34% / 41% / 27% / 16% |
| Title keywords anywhere in clip — quoted Q / unquoted Q / statement / Helping-a | 87% / 91% / 84% / 73% |
| Position of the title's best-matching line (median, share within first 15%) | 2–7% into the clip; 64–75% within the first 15% |
| Ending: in-person workshop pitch / free roadmap CTA | 48% / 28% |
| Thumb text vs transcript (756 clips with both): exact / 2-word fragment / key words present / paraphrase | 12% / 25% / 35% / 29% |
| Position of the thumb's source line (verbatim + fragment cases) | median 31% into the clip; 39% in first fifth; upper quartile 62% |

Monthly view from upload metadata (2,686 clips with dates):

| Month | Uploads | Text thumbs | Median views | Median (text) | Median (no text) |
|---|---|---|---|---|---|
| 2025-09 | 17 | 82% | 14,976 | 16,439 | 12,543 |
| 2025-10 | 44 | 66% | 6,554 | 5,665 | 7,192 |
| 2025-11 | 40 | 5% | 5,418 | — | 5,296 |
| 2026-01 | 57 | 9% | 8,252 | — | 8,534 |
| 2026-02 | 290 | 6% | 2,314 | 1,930 | 2,359 |
| 2026-03 | 499 | 7% | 2,142 | 2,220 | 2,141 |
| 2026-04 | 246 | 5% | 2,153 | — | 2,182 |
| 2026-05 | 314 | 3% | 2,108 | — | 2,122 |
| 2026-06 | 230 | 9% | 1,304 | — | 1,359 |
| 2026-07 | 292 | 8% | 2,604 | 2,080 | 2,647 |
| 2026-08 | 378 | **84%** | 2,575 | **2,747** | 1,578 |
| 2026-09 (to 22nd) | 274 | **95%** | 5,696 | **5,717** | 3,251 |

Reading: the channel launched (Sep–Oct 2025) with text thumbnails on a handful of hand-picked clips, dropped to a no-text, 250–500-uploads-a-month firehose from Feb to Jul 2026 (median views fell to ~2,100), then in Aug 2026 kept the volume *and* put designed text on almost every thumbnail. Median views doubled within six weeks and 39 of the 40 current outliers come from this period. Within Aug–Sep, text thumbs out-earn no-text thumbs 1.7–1.8x at equal age; like-rate is identical (1.4% vs 1.5%), so the gain is click-through, not audience quality.
