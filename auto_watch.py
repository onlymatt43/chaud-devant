#!/usr/bin/env python3
import time, shutil, json, subprocess
from pathlib import Path

EXPORTS = Path.home() / "exports_from_davinci"
PROD = Path.home() / "chaud-devant" / "production"
PIPE = Path.home() / "chaud-devant" / "process.py"
TPL = Path.home() / "chaud-devant" / "config.default.json"

SEEN = set()
DELAY = 5

def stable(p):
    s = p.stat().st_size
    time.sleep(5)
    return s == p.stat().st_size

EXPORTS.mkdir(exist_ok=True)
PROD.mkdir(exist_ok=True)

while True:
    for d in EXPORTS.iterdir():
        if not d.is_dir():
            continue
        if d.name in SEEN:
            continue

        mp4 = d / "video_master.mp4"
        mov = d / "video_master.mov"

        if not (mp4.exists() or mov.exists()):
            continue

        master = mp4 if mp4.exists() else mov
        if not stable(master):
            continue

        dst = PROD / d.name
        dst.mkdir(parents=True, exist_ok=True)
        shutil.move(str(master), dst / master.name)

        cfg = json.loads(TPL.read_text())
        cfg["id"] = d.name
        (dst / "config.json").write_text(json.dumps(cfg, indent=2))
        (dst / "status.json").write_text("{}")

        subprocess.Popen(
            ["python3", str(PIPE), str(dst)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        SEEN.add(d.name)

    time.sleep(DELAY)
