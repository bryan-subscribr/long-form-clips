#!/usr/bin/env python3
"""Transcribe a local clip (mp4/mov/mp3/wav) or a YouTube URL into a timestamped transcript.

Usage:
  python3 transcribe.py <video-or-audio-or-youtube-url> [--out transcript.txt] [--model small.en]

Output: one line per segment, "<start_s>\t<end_s>\t<text>", plus a plain paragraph at the end.
Order of engines tried: faster-whisper (cached models), whisper-cli (whisper.cpp), yt-dlp auto-subs (URL only).
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)

def fetch_youtube(url, tmp):
    """Return (audio_path, subtitle_segments_or_None). Tries auto-subs first (fast), audio second."""
    vid_json = run(['yt-dlp', '--skip-download', '--write-auto-subs', '--sub-langs', 'en', '--sub-format', 'json3',
                    '-o', os.path.join(tmp, 'clip.%(ext)s'), '--print', '%(title)s', url]).stdout.strip()
    subs = [f for f in os.listdir(tmp) if f.endswith('.json3')]
    segs = None
    if subs:
        j = json.load(open(os.path.join(tmp, subs[0])))
        segs = []
        for ev in j.get('events', []):
            if 'segs' not in ev:
                continue
            t = ''.join(s.get('utf8', '') for s in ev['segs']).replace('\n', ' ').strip()
            if t:
                st = ev.get('tStartMs', 0) / 1000
                segs.append((st, st + ev.get('dDurationMs', 0) / 1000, t))
    return vid_json, segs

def to_wav(src, tmp):
    wav = os.path.join(tmp, 'audio.wav')
    run(['ffmpeg', '-y', '-i', src, '-ac', '1', '-ar', '16000', '-vn', wav])
    return wav

def faster_whisper(wav, model):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device='cpu', compute_type='int8')
    segments, _ = m.transcribe(wav, vad_filter=True)
    return [(s.start, s.end, s.text.strip()) for s in segments]

def whisper_cli(wav, model):
    cli = shutil.which('whisper-cli')
    if not cli:
        raise RuntimeError('whisper-cli not found')
    candidates = [os.path.expanduser(f'~/yt-wizards-transcribe/models/ggml-{model}.bin'),
                  os.path.expanduser(f'~/.cache/whisper/ggml-{model}.bin')]
    mp = next((c for c in candidates if os.path.exists(c)), None)
    if not mp:
        raise RuntimeError('no ggml model found for whisper-cli')
    out = run([cli, '-m', mp, '-f', wav, '-oj', '-of', wav[:-4]]).stdout
    j = json.load(open(wav[:-4] + '.json'))
    segs = []
    for s in j.get('transcription', []):
        segs.append((s['offsets']['from'] / 1000, s['offsets']['to'] / 1000, s['text'].strip()))
    return segs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--out', default=None)
    ap.add_argument('--model', default='small.en')
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix='clip-packaging-')
    title = None
    segs = None
    src = a.source
    if re.match(r'https?://', src):
        title, segs = fetch_youtube(src, tmp)
        if segs is None:
            run(['yt-dlp', '-f', 'bestaudio', '-o', os.path.join(tmp, 'clip.%(ext)s'), src])
            src = next(os.path.join(tmp, f) for f in os.listdir(tmp) if f.startswith('clip.'))
    if segs is None:
        wav = to_wav(src, tmp)
        try:
            segs = faster_whisper(wav, a.model)
        except Exception as e:
            sys.stderr.write(f'faster-whisper failed ({e}); trying whisper-cli\n')
            segs = whisper_cli(wav, a.model)
    out = a.out or (os.path.splitext(os.path.basename(a.source))[0] if not title else re.sub(r'[^\w\- ]', '', title)) + '.transcript.txt'
    with open(out, 'w') as f:
        if title:
            f.write(f'# source title: {title}\n')
        for st, en, t in segs:
            f.write(f'{st:.2f}\t{en:.2f}\t{t}\n')
        f.write('\n# plain\n' + ' '.join(t for _, _, t in segs) + '\n')
    dur = segs[-1][1] if segs else 0
    print(f'wrote {out}  segments={len(segs)}  duration={dur:.0f}s  words={sum(len(t.split()) for _,_,t in segs)}')

if __name__ == '__main__':
    main()
