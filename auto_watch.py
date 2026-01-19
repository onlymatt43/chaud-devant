#!/usr/bin/env python3
import time, shutil, json, subprocess, sys
from pathlib import Path

BASE = Path(__file__).parent
EXPORTS = Path.home() / "exports_from_davinci"
INBOX = EXPORTS / "new"
PROD = BASE / "production"
PIPE = BASE / "process.py"
TPL = BASE / "config.default.json"

SEEN = set()
DELAY = 5

def stable(p):
    s = p.stat().st_size
    time.sleep(5)
    return s == p.stat().st_size

EXPORTS.mkdir(exist_ok=True)
INBOX.mkdir(exist_ok=True)
PROD.mkdir(exist_ok=True)

while True:
    try:
        for entry in INBOX.iterdir():
            if entry.name in SEEN or entry.name.startswith("."):
                continue

            master = None
            target_name = None

            # CAS 1 : Un fichier direct (ex: Ma_Video_Dingo.mp4)
            if entry.is_file() and entry.suffix.lower() in [".mp4", ".mov"]:
                master = entry
                target_name = entry.stem # Le titre sera le nom du fichier
            
            # CAS 2 : Un dossier (ex: Projet_Alpha/video_master.mp4)
            elif entry.is_dir():
                # On supporte les dossiers s'ils sont déposés dans new/
                mp4 = entry / "video_master.mp4"
                mov = entry / "video_master.mov"
                if mp4.exists(): master = mp4
                elif mov.exists(): master = mov
                target_name = entry.name

            if not master or not target_name:
                continue

            if not stable(master):
                continue

            print(f"👀 Nouveau projet détecté : {target_name}")

            dst = PROD / target_name
            if dst.exists():
                print(f"⚠️ Le dossier {dst} existe déjà. On écrase ? (Non, on skip pour l'instant)")
                # Pour éviter d'écraser, on pourrait suffixer, mais ici on skip ou on log
                # SEEN.add(entry.name)
                # continue
                pass # On laisse faire pour l'écrasement ou la fusion

            dst.mkdir(parents=True, exist_ok=True)
            shutil.move(str(master), dst / master.name)

            cfg = json.loads(TPL.read_text())
            cfg["id"] = target_name
            (dst / "config.json").write_text(json.dumps(cfg, indent=2))
            (dst / "status.json").write_text("{}")

            print(f"🚀 Lancement du process pour {target_name}...")
            subprocess.Popen(
                [sys.executable, str(PIPE), str(dst)],
                # stdout=subprocess.DEVNULL,
                # stderr=subprocess.DEVNULL
            )

            SEEN.add(entry.name)
    except Exception as e:
        print(f"Erreur dans la boucle de surveillance : {e}")

    time.sleep(DELAY)
