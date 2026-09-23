#!/usr/bin/env python3
"""Mechanical checks for a title + thumb-text package.

Usage:
  python3 check_package.py --title '"How Do I Land Rich Clients With Small Case Studies?"' --thumb 'Punch above your **class**' [--transcript file.txt]
  python3 check_package.py --file packages.txt        # lines: title ||| thumb

Checks: content-word overlap (must be zero), title length 30–55, Title Case, banned words/names, quote style,
number token style, thumb word count 1–4 (5 allowed only if quoted), accent marked, and (with --transcript)
whether thumb words and title keywords are spoken and where.
Exit code 1 if any hard check fails.
"""
import argparse, re, sys

STOP = set("the a an to of and in you your i is it for on my how do what if with that this be are not can me we from at or by so will as was have has am should why who when they their there but into more get up out here what im dont cant its just like her his he she them us our it's you're i'm i'd".split())
BANNED = ["reveals", "explains", "shares", "describes", "reflects on", "insane", "shocking", "secret", "#1", "hormozi", "alex", "!"]
SMALL = set("a an the and or but of to in on at by for with vs".split())

def content(s):
    s = s.lower().replace("’", "'").replace('**', '')
    return set(w.strip("'") for w in re.findall(r"[a-z0-9$%'.]+", s) if w.strip("'.") and w.strip("'.") not in STOP and len(w.strip("'.")) > 1)

def stem(w):
    w = w.lower()
    for suf in ("'s", "ing", "ers", "er", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w

def title_case_ok(t):
    core = t.strip().strip('"“”')
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’\-]*", core)]
    if not words: return True
    caps = sum(1 for w in words if w[0].isupper() or w.lower() in SMALL)
    return caps / len(words) >= 0.8

def check(title, thumb, transcript=None):
    hard, soft = [], []
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
    low = t_clean.lower()
    for b in BANNED:
        if b in low: hard.append(f"banned in title: '{b}'")
    if re.search(r"\b20(1\d|2[0-5])\b", t_clean): hard.append("stale year in title")
    if t_clean.endswith('...') or t_clean.endswith('…'): soft.append("trailing ellipsis")
    # quotes
    if t_clean.startswith(('“', '‘')): soft.append("curly opening quote; channel uses straight \"")
    if t_clean.startswith('"') and not t_clean.rstrip().endswith(('"', '”')): soft.append("opening quote without closing quote")
    if t_clean.startswith('"') and '?' in t_clean and not re.search(r'\?["”]\s*$', t_clean): soft.append("question mark should sit inside the closing quote")
    # numbers
    if re.search(r"\$\d{1,3},\d{3},\d{3}", t_clean): hard.append("use $1M / $100K tokens, not full dollars")
    if re.search(r"\$\d{2,3},\d{3}\b", t_clean): soft.append("$10,000+ should be $10K style")
    if re.search(r"\b(ninety|thirty|twenty|hundred|thousand|million) (days|hours|percent|dollars)\b", low): soft.append("spell numbers as digits")
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
        segs = []
        for line in open(transcript, encoding='utf-8', errors='ignore'):
            if line.startswith('# plain'): break
            p = line.rstrip('\n').split('\t')
            if len(p) >= 3:
                try: segs.append((float(p[0]), p[2].lower()))
                except ValueError: pass
        if segs:
            dur = segs[-1][0] + 5
            full = ' '.join(t for _, t in segs)
            thw = [w for w in content(th_clean)]
            hits = [w for w in thw if w in full]
            pos = None
            for st, t in segs:
                if all(w in t for w in thw if len(thw) <= 2) and thw:
                    pos = st; break
            print(f"  thumb words spoken: {len(hits)}/{len(thw)} {hits}" + (f"; first co-occurrence at {int(pos)//60}:{int(pos)%60:02d} ({pos/dur:.0%})" if pos is not None else ""))
            tk = [w for w in content(t_clean)]
            first20 = ' '.join(t for st, t in segs if st < 20)
            print(f"  title keywords in first 20s: {sum(1 for w in tk if w in first20)}/{len(tk)}; anywhere: {sum(1 for w in tk if w in full)}/{len(tk)}")
    return hard, soft

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title'); ap.add_argument('--thumb'); ap.add_argument('--file'); ap.add_argument('--transcript')
    a = ap.parse_args()
    pairs = []
    if a.file:
        for line in open(a.file):
            if '|||' in line:
                t, th = line.split('|||', 1); pairs.append((t.strip(), th.strip()))
    elif a.title and a.thumb:
        pairs.append((a.title, a.thumb))
    else:
        ap.error('give --title and --thumb, or --file')
    bad = 0
    for t, th in pairs:
        print(f"\nTITLE {t}\nTHUMB {th}   ({len(t)} chars / {len(th.replace('**','').split())} words)")
        hard, soft = check(t, th, a.transcript)
        for h in hard: print(f"  FAIL  {h}")
        for s in soft: print(f"  warn  {s}")
        if not hard and not soft: print("  ok")
        bad += bool(hard)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
