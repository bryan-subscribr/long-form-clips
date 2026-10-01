#!/usr/bin/env python3
"""Mechanical checks for a title + thumb-text package.

Usage:
  python3 check_package.py --title '"How Do I Land Rich Clients With Small Case Studies?"' --thumb 'Punch above your **class**' [--transcript file.txt]
  python3 check_package.py --file packages.txt        # lines: title ||| thumb

  In the long-form pipeline, gate each clip against its own window:
  python3 check_package.py --title "…" --thumb "…" --transcript WORKDIR/transcript.txt \
      --start 12:40 --end 21:05 --thumb-line "you are not broke, your mindset is" --ban "shelby,sapp"

Checks: content-word overlap (must be zero), title length 30–55, Title Case, banned words/names, quote style,
number token style, thumb word count 1–4 (5 allowed only if quoted), accent marked, and (with --transcript)
whether thumb words and title keywords are spoken and where.

--transcript  `start<TAB>end<TAB>text` lines (transcribe.py) or `[MM:SS] text` lines (the pipeline's fetch.py)
--start/--end the clip window in source time; only transcript lines inside it count
--thumb-line  the spoken line the thumbnail is built on; it MUST be found inside the window (hard check).
              A paraphrase thumb (the opposite or consequence of a line) passes as long as its line is spoken.
--ban         extra comma-separated names/words the title may not contain (the speaker's name)
Exit code 1 if any hard check fails.
"""
import argparse, datetime, re, sys

STOP = set("the a an to of and in you your i is it for on my how do what if with that this be are not can me we from at or by so will as was have has am should why who when they their there but into more get up out here what im dont cant its just like her his he she them us our it's you're i'm i'd".split())
BANNED = ["reveals", "explains", "shares", "describes", "reflects on", "insane", "shocking", "secret", "#1", "hormozi", "alex", "!"]
SMALL = set("a an the and or but of to in on at by for with vs".split())
THIS_YEAR = datetime.date.today().year

def content(s):
    s = s.lower().replace("’", "'").replace('**', '')
    words = (w.strip("'.") for w in re.findall(r"[a-z0-9$%'.]+", s))   # "start." and "start" are the same word
    return set(w for w in words if w and w not in STOP and len(w) > 1)

def stem(w):
    w = w.lower()
    for suf in ("'s", "ing", "ers", "er", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w

def stems(s):
    return {stem(w) for w in content(s)}

def title_case_ok(t):
    core = t.strip().strip('"“”')
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’\-]*", core)]
    if not words: return True
    caps = sum(1 for w in words if w[0].isupper() or w.lower() in SMALL)
    return caps / len(words) >= 0.8

def banned_in(text, banned):
    """Whole-word match for words and phrases ("alex" must not hit "Alexa"); plain match for symbols."""
    low = text.lower().replace("’", "'")
    hits = []
    for b in banned:
        b = b.lower().strip()
        if not b:
            continue
        if re.fullmatch(r"[\w' ]+", b):
            if re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", low):
                hits.append(b)
        elif b in low:
            hits.append(b)
    return hits

def to_sec(t):
    total = 0.0
    for part in str(t).strip().split(':'):
        total = total * 60 + float(part)
    return total

def mmss(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"

_TS_LINE = re.compile(r"^\[(\d+:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(.*)$")

def load_transcript(path):
    """[(start, end, text)] from tab-separated or [MM:SS] lines; a paragraph ends where the next begins."""
    segs = []
    with open(path, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if line.startswith('# plain'):
                break
            line = line.rstrip('\n')
            p = line.split('\t')
            if len(p) >= 3:
                try:
                    segs.append([float(p[0]), float(p[1]), p[2]])
                    continue
                except ValueError:
                    pass
            m = _TS_LINE.match(line.strip())
            if m:
                segs.append([to_sec(m.group(1)), None, m.group(2)])
    for i, sg in enumerate(segs):
        if sg[1] is None:
            sg[1] = segs[i + 1][0] if i + 1 < len(segs) else sg[0] + 60.0
    return [tuple(sg) for sg in segs]

def best_span(segs, words, seconds=20.0):
    """(coverage 0..1, time) of the earliest stretch of <= `seconds` holding the most of `words`.

    Bounded by time, not line count: caption cues are 2-5 s, the pipeline's paragraphs ~45 s.
    The time returned is the first line of that stretch that contains one of the words.
    """
    target = {stem(w) for w in words}
    if not target or not segs:
        return 0.0, None
    best, at = 0.0, None
    for i, (s0, _, _) in enumerate(segs):
        have, first = set(), None
        for s1, _, t in segs[i:]:
            if s1 - s0 > seconds and have:
                break
            got = stems(t) & target
            if got and first is None:
                first = s1
            have |= got
        cov = len(have) / len(target)
        if cov > best:
            best, at = cov, first
            if cov == 1.0:
                break
    return best, at

def words_of(s):
    return re.sub(r"[^a-z0-9$%' ]+", " ", s.lower().replace("’", "'")).split()

def find_phrase(segs, phrase):
    """Start time of the line where `phrase` is spoken word for word (punctuation ignored), else None.

    Catches payoff lines made of short common words ("If they can do it, I can") that the
    content-word coverage below cannot see.
    """
    want = words_of(phrase)
    if not want:
        return None
    flat = [(w, s0) for s0, _, t in segs for w in words_of(t)]
    seq = [w for w, _ in flat]
    for i in range(len(seq) - len(want) + 1):
        if seq[i:i + len(want)] == want:
            return flat[i][1]
    return None

def check_full(title, thumb, transcript=None, start=None, end=None, thumb_line=None, ban=()):
    """(hard, soft, info) — info carries the measured positions for callers and tests."""
    hard, soft, info = [], [], {}
    t_clean = title.strip()
    th_clean = thumb.replace('**', '').strip()
    # overlap
    ov = {stem(a) for a in content(t_clean)} & {stem(b) for b in content(th_clean)}
    if ov: hard.append(f"OVERLAP title/thumb content words: {sorted(ov)}")
    # length
    n = len(t_clean)
    if n > 60: hard.append(f"title {n} chars (>60)")
    elif n > 55: soft.append(f"title {n} chars (>55; aim 35–48)")
    elif n < 25: soft.append(f"title {n} chars (<25; may be a label)")
    # case
    if not title_case_ok(t_clean): soft.append("title not Title Case")
    if re.search(r"\b[A-Z]{4,}\b", t_clean.replace('AI', '').replace('U.S.', '')): soft.append("ALL-CAPS word in title")
    # banned
    for b in banned_in(t_clean, BANNED + list(ban)):
        hard.append(f"banned in title: '{b}'")
    stale = [y for y in re.findall(r"\b(20\d\d)\b", t_clean) if 2010 <= int(y) < THIS_YEAR]
    if stale: hard.append(f"stale year in title: {', '.join(stale)}")
    if t_clean.endswith('...') or t_clean.endswith('…'): soft.append("trailing ellipsis")
    # quotes
    if t_clean.startswith(('“', '‘')): soft.append("curly opening quote; channel uses straight \"")
    if t_clean.startswith('"') and not t_clean.rstrip().endswith(('"', '”')): soft.append("opening quote without closing quote")
    if t_clean.startswith('"') and '?' in t_clean and not re.search(r'\?["”]\s*$', t_clean): soft.append("question mark should sit inside the closing quote")
    # numbers
    if re.search(r"\$\d{1,3},\d{3},\d{3}", t_clean): hard.append("use $1M / $100K tokens, not full dollars")
    if re.search(r"\$\d{2,3},\d{3}\b", t_clean): soft.append("$10,000+ should be $10K style")
    if re.search(r"\b(ninety|thirty|twenty|hundred|thousand|million) (days|hours|percent|dollars)\b", t_clean.lower()): soft.append("spell numbers as digits")
    # thumb
    tw = th_clean.split()
    quoted = th_clean.startswith(('"', '“', "'"))
    if len(tw) > 5 or (len(tw) == 5 and not quoted): hard.append(f"thumb {len(tw)} words (max 4; 5 only as a verbatim quote)")
    if len(tw) == 0: hard.append("empty thumb")
    if th_clean.count(',') > 1: soft.append("thumb has >1 comma")
    if '**' not in thumb: soft.append("no accent word marked (**word**)")
    if th_clean.istitle() and len(tw) >= 3: soft.append("thumb in Title Case reads as a headline; use Sentence case, lowercase, or CAPS")
    if len(th_clean) > 32: soft.append(f"thumb {len(th_clean)} chars; may not survive 320px")
    if th_clean.rstrip('.?!').lower() == t_clean.strip('"').rstrip('.?!').lower(): hard.append("thumb equals title")
    # transcript
    if transcript:
        segs = load_transcript(transcript)
        if not segs:
            hard.append(f"could not read {transcript}: expected 'start<TAB>end<TAB>text' or '[MM:SS] text' lines")
            return hard, soft, info
        lo = to_sec(start) if start is not None else segs[0][0]
        hi = to_sec(end) if end is not None else segs[-1][1]
        window = [sg for sg in segs if sg[1] > lo and sg[0] < hi]
        if not window:
            hard.append(f"no transcript lines inside {mmss(lo)}–{mmss(hi)}")
            return hard, soft, info
        dur = max(1.0, hi - lo)
        rel = lambda t: max(0.0, t - lo)   # noqa: E731 — seconds into the clip
        heard = set().union(*(stems(t) for _, _, t in window))
        thw = sorted(content(th_clean))
        hits = [w for w in thw if stem(w) in heard]
        cov, pos = best_span(window, thw)
        info.update(thumb_words=thw, thumb_hits=hits, thumb_pos=rel(pos) if pos is not None else None)
        where = f"; first co-occurrence at {mmss(rel(pos))} ({rel(pos) / dur:.0%})" if pos is not None and cov == 1.0 else ""
        print(f"  thumb words spoken: {len(hits)}/{len(thw)} {hits}{where}")
        if thw and not hits and not thumb_line:
            soft.append("no thumb word is spoken in the clip — fine only for a deliberate opposite/consequence; pass --thumb-line to prove the line it comes from")
        if thumb_line:
            line = re.sub(r"^\s*\[?\d+:\d{2}(?::\d{2})?\]?\s*", "", thumb_line).strip().strip('"“”\'')
            lw = sorted(content(line))
            exact = find_phrase(window, line)
            lcov, lpos = (1.0, exact) if exact is not None else best_span(window, lw)
            info.update(line_coverage=lcov, line_pos=rel(lpos) if lpos is not None else None)
            if lcov < 0.6:
                hard.append(f"thumb line not found in the clip window ({lcov:.0%} of its words; need 60%) — the thumbnail promises something the clip does not say")
            else:
                print(f"  thumb line spoken at {mmss(rel(lpos))} ({rel(lpos) / dur:.0%} into the clip, {lcov:.0%} of its words)")
                if rel(lpos) / dur > 2 / 3:
                    soft.append("thumb line lands after the two-thirds mark; viewers who click for it may leave first")
        tk = sorted(content(t_clean))
        early = set().union(*(stems(t) for s0, _, t in window if rel(s0) < 0.15 * dur))
        info.update(title_words_early=sum(1 for w in tk if stem(w) in early))
        print(f"  title keywords in the first 15% of the clip: {info['title_words_early']}/{len(tk)}; anywhere: {sum(1 for w in tk if stem(w) in heard)}/{len(tk)}")
    return hard, soft, info

def check(title, thumb, transcript=None):
    hard, soft, _ = check_full(title, thumb, transcript)
    return hard, soft

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--title'); ap.add_argument('--thumb'); ap.add_argument('--file'); ap.add_argument('--transcript')
    ap.add_argument('--start'); ap.add_argument('--end'); ap.add_argument('--thumb-line')
    ap.add_argument('--ban', default='', help='comma-separated extra banned words, e.g. the speaker\'s name')
    a = ap.parse_args()
    pairs = []
    if a.file:
        for line in open(a.file, encoding='utf-8-sig'):
            if '|||' in line:
                t, th = line.split('|||', 1); pairs.append((t.strip(), th.strip()))
    elif a.title and a.thumb:
        pairs.append((a.title, a.thumb))
    else:
        ap.error('give --title and --thumb, or --file')
    ban = [b for b in a.ban.split(',') if b.strip()]
    bad = 0
    for t, th in pairs:
        print(f"\nTITLE {t}\nTHUMB {th}   ({len(t)} chars / {len(th.replace('**','').split())} words)")
        hard, soft, _ = check_full(t, th, a.transcript, a.start, a.end, a.thumb_line, ban)
        for h in hard: print(f"  FAIL  {h}")
        for s in soft: print(f"  warn  {s}")
        if not hard and not soft: print("  ok")
        bad += bool(hard)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
