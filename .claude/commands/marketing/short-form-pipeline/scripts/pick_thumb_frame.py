#!/usr/bin/env python3
"""
pick_thumb_frame.py — choose a thumbnail frame where the speaker looks composed.

Grabbing the frame at the exact second a line is spoken usually lands mid-word:
mouth open, hands blurred, eyes half shut. This samples a window around the
target time and ranks frames on what makes a face read as "impressive" in a
1280x720 thumbnail:

  * big face (close-up beats the wide two-shot)
  * single subject (or the face on the requested side of a two-shot)
  * low motion vs neighbouring frames (composed pose, not mid-gesture)
  * sharp (Laplacian variance), eyes detected (open, facing camera)
  * mouth region still (approximates "not mid-word")

Heuristics rank; a human (or Claude reading the contact sheet) confirms. The
script always writes a contact sheet of the top candidates for that review.

Usage:
  python3 pick_thumb_frame.py SOURCE.mp4 --at 77:58 --out frame.jpg \
      [--window 10] [--step 0.5] [--side right|left|any] [--top 6] \
      [--sheet candidates.jpg] [--cand-dir DIR] [--pick N]

  --at        centre time (MM:SS or seconds) — the spoken thumb line
  --side      which face to favour in a two-shot (guest usually sits one side)
  --ref IMG   a frame of the RIGHT speaker; candidates whose face+hair+shoulders
              colour histogram doesn't match are dropped (stops close-ups of the
              host being picked when the guest's line lands on a reaction shot)
  --crop-bottom F  drop the bottom fraction F of every frame (0.15 = 15%) and rescale to
              1280x720 — for sources with burned-in captions or a lower-third band, so the
              thumb text lands on clean pixels. Applied to candidates and the output.
  --zoom-below F   if the chosen face is smaller than F of the frame area (default 0.035,
              i.e. a wide single-camera shot), crop a 16:9 box around the speaker so the
              face reads large, then rescale to 1280x720. 0 disables. Output + candidates.
  --pick N    skip scoring; take candidate N from a previous run's --cand-dir
Prints the chosen time and score; exit 1 if no face found anywhere in the window.
"""

import argparse
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeutil import parse_time_to_seconds as to_sec  # noqa: E402

CASCADE = cv2.data.haarcascades
FACE = cv2.CascadeClassifier(CASCADE + "haarcascade_frontalface_default.xml")
EYES = cv2.CascadeClassifier(CASCADE + "haarcascade_eye.xml")


def mmss(s: float) -> str:
    return f"{int(s) // 60:02d}:{s % 60:04.1f}"


def frame_vf(crop_bottom: float = 0.0) -> str:
    vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
    if crop_bottom > 0:
        keep = 1.0 - crop_bottom
        # keep the top (1-F) of the height, then crop width to 16:9 around centre, then scale
        vf = f"crop=iw:ih*{keep:.4f}:0:0,crop=min(iw\\,ih*16/9):ih:(iw-min(iw\\,ih*16/9))/2:0," + vf
    return vf


def extract_frames(src: str, start: float, duration: float, step: float, out_dir: str, crop_bottom: float = 0.0):
    """One ffmpeg call for the whole window (instead of one seek per sample).

    Returns [(time, path), ...]. Frame k is taken at start + k*step.
    """
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", src,
         "-vf", f"fps=1/{step:.4f},{frame_vf(crop_bottom)}", "-q:v", "2", os.path.join(out_dir, "f%04d.jpg")],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"WARN frame extraction: {proc.stderr.strip()[-300:]}", file=sys.stderr)
    paths = sorted(p for p in os.listdir(out_dir) if p.startswith("f") and p.endswith(".jpg"))
    return [(start + k * step, os.path.join(out_dir, p)) for k, p in enumerate(paths)]


def faces_in(gray, top_frac: float = 0.55):
    """Haar faces whose centre sits in the top `top_frac` of the frame.

    On wide shots Haar happily calls clasped hands or a knee a "face"; real heads
    live in the upper half of a talking-head frame, so anything lower is dropped.
    """
    h = gray.shape[0]
    faces = FACE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60))
    return [f for f in faces if (f[1] + f[3] / 2) < h * top_frac]


def person_hist(img, face):
    """HSV histogram of the face + hair + shoulders box — cheap speaker identity."""
    x, y, fw, fh = face
    h, w = img.shape[:2]
    x0, x1 = max(0, int(x - fw * 0.4)), min(w, int(x + fw * 1.4))
    y0, y1 = max(0, int(y - fh * 0.5)), min(h, int(y + fh * 2.2))
    crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([crop], [0, 1], None, [30, 32], [0, 180, 0, 256])
    return cv2.normalize(hist, hist).flatten()


def ref_hist(path):
    img = cv2.imread(path)
    if img is None:
        sys.exit(f"cannot read --ref {path}")
    faces = faces_in(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), top_frac=1.0)
    if len(faces) == 0:
        sys.exit("no face in --ref image")
    # The reference face is the HIGHEST detection (the head), not the largest box.
    return person_hist(img, min(faces, key=lambda f: f[1]))


def score_frame(img, prev_gray, side: str, ref=None, ref_min=0.85):
    """Return (score, details) for one frame. Higher is better."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    faces = faces_in(gray)
    if len(faces) == 0:
        return -1.0, {"faces": 0}, gray

    # Pick the subject face: requested side in a two-shot, else the largest.
    if len(faces) > 1 and side in ("left", "right"):
        cands = [f for f in faces if ((f[0] + f[2] / 2) > w / 2) == (side == "right")]
        faces = cands or list(faces)
    faces = sorted(faces, key=lambda f: -(f[2] * f[3]))
    single_bonus = 0.15 if len(faces) == 1 else 0.0     # judged BEFORE the identity filter narrows to one
    ident = None
    if ref is not None:
        # Keep the best-matching face; drop the frame if nobody matches the reference.
        matched = [(cv2.compareHist(ref, person_hist(img, f), cv2.HISTCMP_CORREL), f) for f in faces]
        matched.sort(key=lambda m: -m[0])
        ident, best_face = matched[0]
        if ident < ref_min:
            return -1.0, {"faces": int(len(faces)), "ident": round(float(ident), 2)}, gray
        faces = [best_face]
    x, y, fw, fh = faces[0]

    face_ratio = (fw * fh) / (w * h)                      # ~0.01 wide shot, ~0.06+ close-up
    size_score = min(face_ratio / 0.05, 1.0)             # saturate at a clean close-up

    roi = gray[y:y + fh, x:x + fw]
    eyes = EYES.detectMultiScale(roi[: int(fh * 0.6)], scaleFactor=1.1, minNeighbors=8, minSize=(15, 15))
    eye_score = 0.2 if len(eyes) >= 2 else (0.08 if len(eyes) == 1 else 0.0)

    sharp = cv2.Laplacian(roi, cv2.CV_64F).var()
    sharp_score = min(sharp / 400.0, 1.0) * 0.2

    motion_score = 0.2
    mouth_score = 0.15
    if prev_gray is not None:
        diff = cv2.absdiff(gray, prev_gray)
        motion = float(diff[y:y + fh, x:x + fw].mean())          # whole face + a little context
        motion_score = max(0.0, 0.2 - min(motion / 40.0, 1.0) * 0.2)
        mouth = float(diff[y + int(fh * 0.6):y + fh, x + int(fw * 0.25):x + int(fw * 0.75)].mean())
        mouth_score = max(0.0, 0.15 - min(mouth / 30.0, 1.0) * 0.15)

    # Face not cut off by the caption band (bottom ~28% is where thumb text sits).
    band_penalty = 0.15 if (y + fh) > h * 0.72 else 0.0

    ident_score = 0.0 if ident is None else 0.2 * float(ident)
    face_box = (int(x), int(y), int(fw), int(fh))
    total = size_score * 0.5 + single_bonus + eye_score + sharp_score + motion_score + mouth_score + ident_score - band_penalty
    return total, {"faces": int(len(faces)), "face_ratio": round(float(face_ratio), 3), "eyes": int(len(eyes)),
                   "sharp": round(float(sharp), 1), "motion": round(motion_score, 2), "mouth": round(mouth_score, 2),
                   "ident": None if ident is None else round(float(ident), 2), "box": face_box}, gray


def zoom_to_face(img, box, target_face_w=0.20):
    """Crop a 16:9 window around the face so the face is ~target_face_w of the width,
    face centre at ~38% height (room for text at the bottom). Returns 1280x720."""
    H, W = img.shape[:2]
    x, y, fw, fh = box
    cw = int(min(W, max(fw / target_face_w, W * 0.45)))
    ch = int(cw * 9 / 16)
    if ch > H:
        ch = H; cw = int(H * 16 / 9)
    cx, cy = x + fw / 2, y + fh / 2
    x0 = int(min(max(0, cx - cw / 2), W - cw))
    y0 = int(min(max(0, cy - ch * 0.38), H - ch))
    crop = img[y0:y0 + ch, x0:x0 + cw]
    return cv2.resize(crop, (1280, 720), interpolation=cv2.INTER_CUBIC)


def contact_sheet(paths, labels, out, cols=3, cell=(426, 240)):
    rows = (len(paths) + cols - 1) // cols
    sheet = np.zeros((rows * (cell[1] + 28), cols * cell[0], 3), dtype=np.uint8)
    for i, (p, lab) in enumerate(zip(paths, labels)):
        img = cv2.imread(p)
        if img is None:
            continue
        img = cv2.resize(img, cell)
        r, c = divmod(i, cols)
        y0, x0 = r * (cell[1] + 28), c * cell[0]
        sheet[y0:y0 + cell[1], x0:x0 + cell[0]] = img
        cv2.putText(sheet, lab, (x0 + 8, y0 + cell[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(out, sheet)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--at", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", type=float, default=10.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--side", choices=["left", "right", "any"], default="any")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--cand-dir", default=None)
    ap.add_argument("--pick", type=int, default=None)
    ap.add_argument("--ref", default=None, help="frame of the correct speaker (colour-histogram identity)")
    ap.add_argument("--crop-bottom", type=float, default=0.0, help="drop this fraction of the frame bottom (burned-in captions)")
    ap.add_argument("--zoom-below", type=float, default=0.035, help="auto zoom-crop when face area ratio is below this (0 = off)")
    ap.add_argument("--ref-min", type=float, default=0.85, help="min histogram correlation to count as the same person (guest 0.85-0.99, hosts 0.6-0.8 in testing)")
    args = ap.parse_args()
    ref = ref_hist(args.ref) if args.ref else None

    cand_dir = args.cand_dir or tempfile.mkdtemp(prefix="thumbcand_")
    os.makedirs(cand_dir, exist_ok=True)

    if args.pick is not None:
        src = os.path.join(cand_dir, f"cand{args.pick}.jpg")
        if not os.path.exists(src):
            sys.exit(f"no candidate {args.pick} in {cand_dir}")
        cv2.imwrite(args.out, cv2.imread(src))
        print(f"picked candidate {args.pick} -> {args.out}")
        return

    centre = to_sec(args.at)
    start = max(0.0, centre - args.window)
    scored = []
    prev_gray = None
    with tempfile.TemporaryDirectory() as td:
        for t, fp in extract_frames(args.source, start, 2 * args.window, args.step, td, args.crop_bottom):
            img = cv2.imread(fp)
            if img is None:
                continue
            s, det, gray = score_frame(img, prev_gray, args.side, ref, args.ref_min)
            prev_gray = gray
            if s >= 0:
                scored.append((s, float(t), fp, det, img))

        if not scored:
            sys.exit("no face found in window")

        scored.sort(key=lambda r: -r[0])
        top = scored[: args.top]
        paths, labels = [], []
        for n, (s, t, fp, det, img) in enumerate(top, 1):
            if args.zoom_below > 0 and det.get("face_ratio", 1.0) < args.zoom_below and det.get("box"):
                img = zoom_to_face(img, det["box"])
                top[n - 1] = (s, t, fp, {**det, "zoomed": True}, img)
            cp = os.path.join(cand_dir, f"cand{n}.jpg")
            cv2.imwrite(cp, img)
            paths.append(cp)
            labels.append(f"#{n} {mmss(t)} s={s:.2f} face={det['face_ratio']} eyes={det['eyes']} id={det.get('ident')}{' Z' if det.get('zoomed') else ''}")
        cv2.imwrite(args.out, top[0][4])
        if args.sheet:
            contact_sheet(paths, labels, args.sheet)

    best = top[0]
    print(f"picked {mmss(best[1])} score={best[0]:.2f} {best[3]} -> {args.out}")
    print(f"candidates: {cand_dir}" + (f"  sheet: {args.sheet}" if args.sheet else ""))


if __name__ == "__main__":
    main()
