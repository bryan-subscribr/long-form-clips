#!/usr/bin/env python3
"""Render thumbnail text onto a frame in the MoreMozi layout.

Usage:
  python3 thumb_preview.py frame.jpg "Famous but **poor**" -o out.jpg [--align left|center] [--size 104] [--badge "1 HOUR"] [--darken 0.5]

Layout defaults (re-measured 22 Sep 2026 against the channel's current top-12): 1280x720 output; Montserrat ExtraBold
(the channel's weight reads as Bold/ExtraBold, SemiBold looks thin next to it); white fill with a 4 px black stroke and a soft
drop shadow — the frame itself is NOT darkened; text block CENTRED, last-line baseline ≈ 90% of height (single line) with
tight 1.0 line spacing; **word** rendered in #FEF731; optional red "1 HOUR" pill top-RIGHT (the channel moved it there).
Fonts searched: Montserrat-ExtraBold, Montserrat-Bold, Poppins-Bold, then Arial Bold. --align left restores the old anchor.
"""
import argparse, os, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

YELLOW = (254, 247, 49)
_HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = [os.path.join(_HERE, '..', 'assets', 'fonts', 'Montserrat-ExtraBold.ttf'),   # vendored (OFL) so the team renders in the channel typeface
         os.path.expanduser('~/Library/Fonts/Montserrat-ExtraBold.ttf'), os.path.expanduser('~/Library/Fonts/Montserrat-Bold.ttf'),
         os.path.expanduser('~/Library/Fonts/Poppins-Bold.ttf'), os.path.expanduser('~/Library/Fonts/Montserrat-SemiBold.ttf'),
         '/System/Library/Fonts/Supplemental/Arial Bold.ttf']

def font(size):
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()

def tokens(text):
    """Split into (word, accent) keeping spaces; **word** marks accent."""
    out = []
    for part in re.split(r'(\*\*[^*]+\*\*)', text):
        if not part: continue
        if part.startswith('**'):
            out.append((part[2:-2], True))
        else:
            out.append((part, False))
    return out

def wrap(toks, fnt, maxw, draw):
    """Greedy wrap on spaces; returns list of lines, each a list of (word, accent).
    Punctuation that follows an accent word without a space (e.g. **life**") is glued to that word."""
    words = []
    for txt, acc in toks:
        if not acc and words and txt and not txt[0].isspace() and re.match(r'^[^\w\s$]+', txt):
            m = re.match(r'^([^\w\s$]+)(.*)$', txt)
            pw, pa = words[-1]; words[-1] = (pw + m.group(1), pa); txt = m.group(2)
        for i, w in enumerate(txt.split(' ')):
            if w == '' and i == 0: continue
            if w: words.append((w, acc))
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        width = draw.textlength(' '.join(x for x, _ in trial), font=fnt)
        if width > maxw and cur:
            lines.append(cur); cur = [w]
        else:
            cur = trial
    if cur: lines.append(cur)
    return lines

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('frame'); ap.add_argument('text'); ap.add_argument('-o', '--out', default='thumb_preview.jpg')
    ap.add_argument('--align', choices=['left', 'center'], default='center'); ap.add_argument('--size', type=int, default=112)
    ap.add_argument('--badge', default=None); ap.add_argument('--darken', type=float, default=0.0,
                    help='bottom-gradient darkening 0-1; the channel does not darken, default off')
    ap.add_argument('--stroke', type=int, default=4, help='black outline width in px (channel ≈ 4-6 at 1280 wide)')
    ap.add_argument('--baseline', type=float, default=0.90, help='last-line baseline as a fraction of height')
    ap.add_argument('--maxw', type=float, default=0.86, help='max text width as a fraction of frame width')
    a = ap.parse_args()
    im = Image.open(a.frame).convert('RGB').resize((1280, 720))
    if a.darken > 0:
        grad = Image.new('L', (1, 720))
        for y in range(720):
            v = 0 if y < 390 else int(255 * a.darken * (y - 390) / 330)
            grad.putpixel((0, y), min(255, v))
        grad = grad.resize((1280, 720))
        im = Image.composite(Image.new('RGB', (1280, 720), (0, 0, 0)), im, grad)
    draw = ImageDraw.Draw(im)
    fnt = font(a.size)
    lines = wrap(tokens(a.text), fnt, int(1280 * a.maxw), draw)
    # Shrink to fit if a single word is wider than the box (rare, long words).
    while any(draw.textlength(' '.join(w for w, _ in ln), font=fnt) > 1280 * a.maxw for ln in lines) and a.size > 72:
        a.size -= 6; fnt = font(a.size); lines = wrap(tokens(a.text), fnt, int(1280 * a.maxw), draw)
    # Short thumbs (≤4 words) stay on one line like the channel's: shrink before wrapping.
    n_words = sum(len(ln) for ln in lines)
    while len(lines) > 1 and n_words <= 4 and a.size > 88:
        a.size -= 4; fnt = font(a.size); lines = wrap(tokens(a.text), fnt, int(1280 * a.maxw), draw)
    ascent, descent = fnt.getmetrics()
    line_h = int(a.size * 1.02)                       # channel sets lines tight
    baseline_last = int(720 * a.baseline)
    y_top_last = baseline_last - ascent
    ys = [y_top_last - (len(lines) - 1 - li) * line_h for li in range(len(lines))]

    def x_for(text_line):
        lw = draw.textlength(text_line, font=fnt)
        return 64 if a.align == 'left' else int((1280 - lw) / 2)

    # soft drop shadow under the stroke
    shadow = Image.new('RGBA', im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    for li, line in enumerate(lines):
        text_line = ' '.join(w for w, _ in line)
        sd.text((x_for(text_line) + 4, ys[li] + 7), text_line, font=fnt, fill=(0, 0, 0, 190),
                stroke_width=a.stroke, stroke_fill=(0, 0, 0, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    im = Image.alpha_composite(im.convert('RGBA'), shadow).convert('RGB')
    draw = ImageDraw.Draw(im)
    for li, line in enumerate(lines):
        text_line = ' '.join(w for w, _ in line)
        x = x_for(text_line)
        for w, acc in line:
            draw.text((x, ys[li]), w, font=fnt, fill=YELLOW if acc else (255, 255, 255),
                      stroke_width=a.stroke, stroke_fill=(0, 0, 0))
            x += draw.textlength(w + ' ', font=fnt)
    if a.badge:
        bf = font(30); pad = 18; ico = 26
        bw = int(draw.textlength(a.badge, font=bf)) + 2 * pad + ico + 10
        bx = 1280 - 40 - bw                      # channel now places the pill top-right
        draw.rounded_rectangle((bx - 4, 36, bx + bw + 4, 100), radius=32, fill=(255, 255, 255))
        draw.rounded_rectangle((bx, 40, bx + bw, 40 + 56), radius=28, fill=(229, 57, 53))
        cx, cy = bx + pad + ico // 2, 40 + 28
        draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), outline=(255, 255, 255), width=3)
        draw.line((cx, cy, cx, cy - 7), fill=(255, 255, 255), width=3); draw.line((cx, cy, cx + 5, cy), fill=(255, 255, 255), width=3)
        draw.text((bx + pad + ico + 10, 40 + 11), a.badge, font=bf, fill=(255, 255, 255))
    im.save(a.out, quality=90)
    print(f"wrote {a.out}  lines={len(lines)}  font={a.size}px  align={a.align}")

if __name__ == '__main__':
    main()
