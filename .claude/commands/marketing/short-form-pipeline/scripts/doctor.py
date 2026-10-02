#!/usr/bin/env python3
"""
doctor.py — check this machine can run the clip pipeline (macOS, Windows, Linux).

Run it with the Python you will use for the pipeline (the repo's .venv when there is one):

  .venv/bin/python           .claude/commands/marketing/short-form-pipeline/scripts/doctor.py   # macOS / Linux
  .venv/Scripts/python.exe   .claude/commands/marketing/short-form-pipeline/scripts/doctor.py   # Windows

or `bash .../doctor.sh`, which finds that Python for you. The last lines are machine-readable;
the long-form workflow reads them and uses the values in every later command:

  PY=<interpreter to run the scripts with>
  ENCODER=<--encoder value: the fastest H.264 encoder that actually works here>
  X264_PRESET=<--x264-preset value>
  READY=yes|no

Exit 0 when everything required is present, 1 otherwise. Installs nothing.
"""

import datetime
import importlib
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]                     # <repo>/.claude/commands/marketing/short-form-pipeline/scripts
PKG = REPO / ".claude" / "skills" / "clip-packaging"
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

failures: list[str] = []
warnings: list[str] = []


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def warn(msg: str) -> None:
    print(f"  warn  {msg}")
    warnings.append(msg)


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    failures.append(msg)


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def install_hint(tool: str) -> str:
    if IS_WIN:
        return {"yt-dlp": "winget install yt-dlp.yt-dlp", "ffmpeg": "winget install Gyan.FFmpeg",
                "deno": "winget install DenoLand.Deno"}.get(tool, "")
    if IS_MAC:
        return {"yt-dlp": "brew install yt-dlp", "ffmpeg": "brew install ffmpeg", "deno": "brew install deno"}.get(tool, "")
    return {"yt-dlp": "pip install -U yt-dlp", "ffmpeg": "sudo apt install ffmpeg",
            "deno": "curl -fsSL https://deno.land/install.sh | sh"}.get(tool, "")


def check_python() -> str:
    v = sys.version_info
    if v < (3, 10):
        fail(f"Python {v.major}.{v.minor} — need 3.10 or newer (3.12 recommended)")
    else:
        ok(f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    venv_py = REPO / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")
    if venv_py.exists() and not in_venv:
        warn(f"this repo has a .venv but doctor is not running in it — rerun with {venv_py.relative_to(REPO).as_posix()}")
    # Commands run from the repo root, so a path inside the repo is printed relative (no spaces, no drive letter).
    exe = Path(sys.executable)
    try:
        return exe.relative_to(REPO).as_posix()
    except ValueError:
        return exe.as_posix()


def check_location() -> bool:
    """A cloud-synced folder hangs the pipeline with no message.

    iCloud (Desktop & Documents) and OneDrive (Files On-Demand) offload files they think are
    unused; reading one later waits for the download. In a .venv that is thousands of files,
    so the next `import` simply stops. Seen on a Mac: 28,195 of 28,278 venv files offloaded
    overnight. Returns False when the folder is synced (the package imports would hang too).
    """
    root = REPO.resolve()
    home = Path.home().resolve()
    synced = None
    if IS_WIN:
        for var in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
            base = os.environ.get(var)
            if base and str(root).lower().startswith(str(Path(base).resolve()).lower()):
                synced = "OneDrive"
    elif IS_MAC:
        if str(root).startswith(str(home / "Library" / "Mobile Documents")):
            synced = "iCloud Drive"
        for top in ("Documents", "Desktop"):
            d = (home / top).resolve()
            if synced is None and (root == d or str(root).startswith(str(d) + os.sep)):
                p = run(["xattr", "-p", "com.apple.file-provider-domain-id", str(d)])
                if p and p.returncode == 0 and "CloudDocs" in p.stdout:
                    synced = "iCloud Drive (Desktop & Documents)"
        offloaded = 0
        venv = REPO / ".venv"
        if venv.exists():
            for i, f in enumerate(f for f in venv.rglob("*") if f.is_file()):
                if i >= 400:
                    break
                if getattr(os.lstat(f), "st_flags", 0) & 0x40000000:   # SF_DATALESS: content lives in the cloud
                    offloaded += 1
        if offloaded and synced is None:
            synced = "a cloud file provider"
        if offloaded:
            synced += f", {offloaded} of the first 400 .venv files already offloaded"
    if synced:
        target = r"C:\Users\<you>\long-form-clips" if IS_WIN else "~/long-form-clips"
        fail(f"this folder is synced by {synced}: offloaded files make runs hang with no message. "
             f"Clone the repo again into {target} (outside Documents, Desktop and OneDrive) and use that copy")
        return False
    ok("folder is not cloud-synced")
    return True


def check_encoding() -> None:
    enc = locale.getpreferredencoding(False).lower()
    if sys.flags.utf8_mode or enc in ("utf-8", "utf8"):
        ok(f"text encoding {'UTF-8 mode' if sys.flags.utf8_mode else enc}")
    elif IS_WIN:
        warn(f"text encoding is {enc}: run  setx PYTHONUTF8 1  once, then open a new terminal "
             "(the scripts are UTF-8 safe; this covers third-party tools too)")
    else:
        warn(f"text encoding is {enc}; set LANG=en_US.UTF-8")


def check_binaries() -> None:
    for tool in ("yt-dlp", "ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if path:
            ok(f"{tool} ({path})")
        else:
            fail(f"{tool} missing — {install_hint('ffmpeg' if tool == 'ffprobe' else tool)}")
    # fetch.py prefers a yt-dlp installed in this Python's environment over the one on PATH.
    try:
        import yt_dlp.version
        version, where = yt_dlp.version.__version__, "in this Python (fetch.py uses this one)"
        update = "pip install -U yt-dlp  (with this .venv's pip)"
    except ImportError:
        p = run(["yt-dlp", "--version"]) if shutil.which("yt-dlp") else None
        version, where = (p.stdout.strip() if p else ""), "on PATH"
        update = "winget upgrade yt-dlp.yt-dlp" if IS_WIN else "brew upgrade yt-dlp" if IS_MAC else "pip install -U yt-dlp"
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", version)
    if m:
        age = (datetime.date.today() - datetime.date(*map(int, m.groups()))).days
        msg = f"yt-dlp {version} {where}, {age} days old"
        if age > 45:
            warn(f"{msg} — YouTube breaks old builds (HTTP 403 on the video). Update: {update}")
        else:
            ok(msg)
    if shutil.which("deno") or shutil.which("node"):
        ok(f"JavaScript runtime for yt-dlp ({'deno' if shutil.which('deno') else 'node'})")
    else:
        warn(f"no JavaScript runtime — recent yt-dlp needs one for many YouTube videos ({install_hint('deno')})")


def check_ffmpeg() -> tuple[str, str]:
    """Report decode/filter support and pick the fastest encoder that really encodes here."""
    if not shutil.which("ffmpeg"):
        return "libx264", "veryfast"
    dec = run(["ffmpeg", "-hide_banner", "-decoders"])
    if dec and re.search(r"\b(libdav1d|av1)\b", dec.stdout):
        ok("ffmpeg decodes AV1 (YouTube's default download)")
    else:
        warn("this ffmpeg cannot decode AV1; install a full build (Gyan.FFmpeg / Homebrew ffmpeg)")
    flt = run(["ffmpeg", "-hide_banner", "-filters"])
    if flt and re.search(r"^\s*\S+\s+ass\s", flt.stdout, re.M):
        ok("ffmpeg can burn captions (ass filter)")
    else:
        warn("ffmpeg has no ass filter — burned-in captions unavailable (horizontal clips ship without them anyway)")

    listed = run(["ffmpeg", "-hide_banner", "-encoders"])
    names = listed.stdout if listed else ""
    order = (["h264_videotoolbox"] if IS_MAC else []) + ["h264_nvenc", "h264_qsv", "h264_amf"]
    for enc in order:
        if not re.search(rf"\b{enc}\b", names):
            continue
        # Being listed proves nothing (nvenc ships in every Windows build); encode one second to be sure.
        probe = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                     "color=c=black:s=1280x720:d=1", "-c:v", enc, "-b:v", "2M", "-f", "null", "-"], timeout=60)
        if probe and probe.returncode == 0:
            ok(f"hardware encoder {enc} works — renders run several times faster than libx264")
            return enc, "medium"
    if re.search(r"\blibx264\b", names):
        ok("no hardware H.264 encoder; libx264 with the veryfast preset (about half the time of medium)")
        return "libx264", "veryfast"
    fail("ffmpeg has no libx264 — install a full build (Gyan.FFmpeg / Homebrew ffmpeg)")
    return "libx264", "veryfast"


def check_packages() -> None:
    required = [("cv2", "opencv-python", "thumbnail frame picker"), ("numpy", "numpy", "thumbnail frame picker"),
                ("PIL", "Pillow", "thumbnail text renderer")]
    for mod, pkg, why in required:
        try:
            m = importlib.import_module(mod)
        except ImportError:
            fail(f"python package {pkg} missing ({why}) — pip install -r requirements.txt")
            continue
        if mod == "cv2" and not hasattr(m, "CascadeClassifier"):
            fail(f"opencv-python {m.__version__} has no CascadeClassifier (removed in OpenCV 5) — "
                 'pip install "opencv-python>=4.8,<5"')
            continue
        ok(f"{pkg} {getattr(m, '__version__', '')}".rstrip())
    try:
        importlib.import_module("whisper")
        ok("openai-whisper (transcript fallback when YouTube withholds captions)")
    except ImportError:
        warn("openai-whisper missing — needed when YouTube rate-limits captions (common) and for local files: "
             "pip install openai-whisper")


def check_repo() -> None:
    if (PKG / "scripts" / "thumb_preview.py").exists():
        ok("clip-packaging skill (in this repo)")
    else:
        fail(f"clip-packaging skill missing at {PKG}")
    if (PKG / "assets" / "fonts" / "Montserrat-ExtraBold.ttf").exists():
        ok("Montserrat ExtraBold (bundled thumbnail font)")
    else:
        warn("bundled Montserrat ExtraBold missing; thumbnails fall back to Arial Bold")


def check_disk() -> None:
    cache = Path.home() / ".cache" / "short-form-repurposing"
    target = cache if cache.exists() else Path.home()
    free_gb = shutil.disk_usage(target).free / 1e9
    used = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file()) / 1e9 if cache.exists() else 0.0
    note = f"; work folders hold {used:.1f} GB in {cache.as_posix()}" if used >= 1 else ""
    if free_gb < 20:
        warn(f"{free_gb:.0f} GB free — a 2-hour 1080p source plus its clips needs ~10 GB{note}")
    else:
        ok(f"{free_gb:.0f} GB free{note}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(f"== clip pipeline doctor — {platform.system()} {platform.release()} ({platform.machine()}) ==")
    py = check_python()
    local = check_location()
    check_encoding()
    check_binaries()
    encoder, preset = check_ffmpeg()
    if local:
        check_packages()
    else:
        print("  skip  python packages (importing them from a synced folder is what hangs)")
    check_repo()
    check_disk()
    print()
    if failures:
        print(f"NOT READY — fix the {len(failures)} FAIL line(s) above; TEAM-SETUP.md has the install steps.")
    elif warnings:
        print("Ready (see the warn lines above).")
    else:
        print("All good — ready to run.")
    print(f"PY={py}")
    print(f"ENCODER={encoder}")
    print(f"X264_PRESET={preset}")
    print(f"READY={'no' if failures else 'yes'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
