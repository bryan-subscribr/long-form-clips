#!/usr/bin/env python3
"""First-pass extraction of packaging raw materials from a transcript.

Usage: python3 extract_materials.py <transcript.txt> [more.txt ...]
Input format: lines of "start\tend\ttext" (from transcribe.py) or "ms\ttext"; a plain paragraph after "# plain" is ignored.
Prints: opening (first 20 s), format guess, asked question(s), self-intro, numbers, candidate stinger lines (2-6 words),
first-person emotional lines, absolutes/contrasts, and the ending CTA check — each with mm:ss.
This is a heuristic first pass. Read the transcript; correct by hand.
"""
import re, sys

STOP = set("the a an to of and in you your i is it for on my how do what if with that this be are not can me we from at or by so will as was have has am should why who when they their there but into more get up out here what im dont cant its just like um uh".split())

def load(path):
    segs = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        if line.startswith('#'):
            if line.startswith('# plain'):
                break
            continue
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 3:
            try: st = float(parts[0]); txt = parts[2]
            except ValueError: continue
        elif len(parts) == 2:
            try: st = float(parts[0]) / (1000 if float(parts[0]) > 10000 else 1); txt = parts[1]
            except ValueError: continue
        else:
            continue
        if txt.strip():
            segs.append((st, txt.strip()))
    return segs

def ts(s):
    return f"{int(s)//60}:{int(s)%60:02d}"

def sentences(segs):
    """Join segments into sentences with the start time of the first segment."""
    out = []; buf = []; start = None
    for st, t in segs:
        if start is None: start = st
        buf.append(t)
        joined = ' '.join(buf)
        if re.search(r'[.!?]["”]?\s*$', t) or len(joined) > 220:
            out.append((start, re.sub(r'\s+', ' ', joined)))
            buf = []; start = None
    if buf: out.append((start, ' '.join(buf)))
    return out

def analyse(path):
    segs = load(path)
    if not segs:
        print(f"{path}: no segments"); return
    dur = segs[-1][0] + 5
    sents = sentences(segs)
    print(f"\n===== {path}  ({ts(dur)}, {len(sents)} sentences)")
    opening = ' '.join(t for st, t in segs if st < 20)
    print(f"\nOPENING (0:00–0:20): {opening[:400]}")
    o = opening.lower()
    if re.search(r"\b(i sell|we sell|i own|we own|i run|we run|i provide|we provide|my name is|partnered with|we do \$?\d|we did \$?\d|revenue|i have (a|an|two|three) (business|company|agency|clinic|gym|shop|store)|what's stopping me)\b", o[:600]):
        fmt = 'HOT-SEAT (self-intro) → Helping a … / owner\'s question quoted'
    elif '?' in opening[:200] or re.match(r'^(how|what|why|should|do you|is it|can i|when|alex|hey)', o):
        fmt = 'AUDIENCE QUESTION → quoted first-person question'
    elif re.match(r'^(and|so|but|because|like|which|the thing is)', o):
        fmt = 'MID-THOUGHT cold open (answer already running) → statement archetypes'
    else:
        fmt = 'STATEMENT cold open → How to / You … / If You…, Do This / Why …'
    if 'if you had to' in o or 'how would you' in o or 'if you were' in o:
        fmt += '  [hypothetical prompt → If I Wanted…, I\'d… / How I\'d…]'
    print(f"FORMAT GUESS: {fmt}")

    print("\nQUESTIONS ASKED (first 25% of clip):")
    for st, s in sents:
        if st < dur * 0.25 and '?' in s:
            print(f"  {ts(st)}  {s[:260]}")

    print("\nSELF-INTRO / PERSONA LINES:")
    for st, s in sents:
        if re.search(r"\b(i sell|i own|i run|i'm a|i am a|we do|my name is|i have (a|two|three)|i'm \d\d|i am \d\d|i make|i built|i started)\b", s.lower()):
            print(f"  {ts(st)}  {s[:220]}")

    print("\nNUMBERS (with context):")
    for st, s in sents:
        for m in re.finditer(r"(\$\s?\d[\d,.]*\s?(?:k|m|million|thousand|billion|bucks|grand)?|\b\d+(?:\.\d+)?\s?%|\b\d+\s?(?:x|hours?|days?|weeks?|months?|years?|minutes?|clients?|people|calls?|dms?|reps?|locations?|employees?|cohorts?|times)\b|\b(?:one|two|three|five|ten|hundred|thousand|million)\s+(?:hours?|days?|clients?|things?|years?|people|dollars?|million|thousand)\b)", s, re.I):
            i = m.start(); ctx = s[max(0, i-50): i+70].replace('\n', ' ')
            print(f"  {ts(st)}  …{ctx}…")

    print("\nCANDIDATE STINGERS (short punchy sentences or clauses, 2–6 words):")
    seen = set()
    for st, s in sents:
        for clause in re.split(r'[.!?;:]|,\s|\s—\s|\s-\s|\s(?=(?:and|but|so|because|which)\s)', s):
            c = clause.strip().strip('"“”').strip()
            w = c.split()
            if 2 <= len(w) <= 7 and len(c) >= 8 and c.lower() not in seen:
                lw = c.lower()
                if re.match(r'^(and|so|um|uh|yeah|okay|all right|alright|right|like|you know|i mean|mhm|got it|cool|number (one|two|three))\b', lw): continue
                if sum(1 for x in w if x.lower() in STOP) / len(w) > 0.6: continue
                if 3 <= len(w) <= 6 and re.search(r"\b(is|are|was|were|isn't|aren't|don't|doesn't|won't|can't|need|needs|make|makes|get|gets|pay|pays|buy|buys|sell|sells|want|wants|tell|show|give|take|keep|stop|start)\b", lw):
                    seen.add(lw); print(f"  {ts(st)}  {c}"); continue
                if re.search(r"\b(not|no|never|nobody|nothing|isn't|won't|can't|don't|but|only|just|every|everyone|all|zero|dead|die|broke|poor|rich|free|hate|love|scared|afraid|terrif|sick|period|ridiculous|excuse|stop|start|quit|story|stories|sell|buy|buys|pay|paid|price|money|repeat|less|more|need|nothing|sexy|boring|hard|easy|wrong|right|worth|meaning|trust|risk|work|works|matter|matters)\b", lw) or re.search(r'\d', lw):
                    seen.add(lw); print(f"  {ts(st)}  {c}")

    print("\nFIRST-PERSON EMOTIONAL LINES (asker or speaker confessions):")
    for st, s in sents:
        if re.search(r"\b(i feel|i'm scared|i'm afraid|i hate|i love|i lost|i can't|i don't know|i'm broke|i'm stuck|i quit|i failed|i'm terrified|i'm tired|i'm burned|i'm burnt|i'm miserable|i cried|makes me sick|i'll know|i know)\b", s.lower()):
            print(f"  {ts(st)}  {s[:200]}")

    print("\nABSOLUTES / CONTRASTS (verdict material):")
    for st, s in sents:
        if re.search(r"\b(always|never|nobody|no one|everyone|everybody|most people|the only|period|full stop|not .{1,25}, (it's|it is) .{1,25}|isn't .{1,20}, it's|the difference between)\b", s.lower()) and len(s) < 200:
            print(f"  {ts(st)}  {s}")

    tail = ' '.join(t for st, t in segs[-8:]).lower()
    cta = 'roadmap CTA' if ('roadmap' in tail or 'absolutely free' in tail) else ('workshop pitch' if ('vegas' in tail or 'in person' in tail) else 'none detected')
    print(f"\nENDING: {cta}  — last line: {segs[-1][1][:120]}")

if __name__ == '__main__':
    for p in sys.argv[1:]:
        analyse(p)
