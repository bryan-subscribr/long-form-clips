# Batch mode and the packaging ledger

The channel's volume (7.6 long-form uploads a day, 20+ in peak weeks) and its re-upload habit (108 titles used 2–7 times) mean packaging is a *portfolio* activity. Two tools: a batch procedure and a ledger.

## Batch procedure

1. **Transcribe everything first.** `for f in *.mp4; do python3 scripts/transcribe.py "$f" --out "${f%.mp4}.transcript.txt" & done; wait` (4 at a time on a laptop). URLs with captions take seconds.
2. **Materials pass.** `python3 scripts/extract_materials.py *.transcript.txt` — one materials block per clip. Correct by hand.
3. **Classify all clips** before packaging any. Note the format mix; a batch of ten hot-seats and zero solo clips is a signal to vary archetypes deliberately.
4. **Package each** with the normal procedure.
5. **Batch constraints:**
   - No single archetype over 40% of the batch (the channel's mix: quoted Q 18%, free-form 18%, Helping-a 12%, How-to 12%, The-X 8%, You 8%, Why 6%, rest under 5% each).
   - No repeated thumb *content word* within the batch, unless the user is running a numbered series.
   - No two titles with the same first two words in the batch.
   - At least one `If I Wanted…`/`If You…` conditional per ten clips when the material allows — highest medians, under-used by the channel itself (2.7% of uploads).
6. **Summary table:** `# · file · format · title (chars) · thumb (accent) · pull-quote mm:ss · rubric score`.
7. **Ledger append.**

## Ledger schema (CSV or sheet)

```
date_packaged, clip_id_or_file, source, format, duration_s,
title, title_archetype, title_chars,
thumb_text, thumb_type, accent_word, thumb_line_timestamp,
unused_stingers (pipe-separated, with timestamps),
status (packaged | published | re-run),
published_date, views_7d, views_30d, ctr_if_known,
notes
```

Why each column exists:
- `unused_stingers` — the raw material for re-uploads. Every clip with three good stingers is three uploads over three months.
- `title_archetype`, `thumb_type` — to keep the batch mix and to learn which shells work for *this* speaker (the medians in this skill are Hormozi's).
- `views_7d/30d` — the channel's own outliers show within 3 weeks; 7-day and 30-day are enough to decide a re-run.

## Re-run rules (from the channel's re-uploads)

- A clip that beat 3x the channel's rolling average is a re-run candidate after 30–90 days.
- Keep the title or move it one archetype (`You Can Have Everything…` → `If You Want Everything, Give It 90 Days`).
- **Always change the thumb line**, pulling the next stinger from `unused_stingers`. Same-thumb re-uploads are not in the corpus; different-thumb re-runs earned 40–85% of the first run (407K vs 496K; 325K vs 282K — the second run *beat* the first when the first had no text).
- A proven *title shell* can go on a new clip (`You Need to Focus` × 7, `Helping a Marketing Agency Scale` × 6) but this is the channel's floor behaviour; do it only with specific titles.
- Never re-run a clip under the channel median. Re-runs amplify winners; they do not rescue losers.

## Monthly review
1. Sort the ledger by `views_30d`. Read the top 10 titles and thumbs aloud; name the archetype and thumb type of each.
2. Update the speaker's own archetype medians (replace this skill's Hormozi numbers in your head with the channel's).
3. Mark re-run candidates.
4. Read the bottom 10 against `anti-patterns.md` and name the failure type. If one type repeats, add a check to your step 4.
