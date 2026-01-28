#!/usr/bin/env python3
import time, shutil, json, subprocess, sys
from pathlib import Path

BASE = Path(__file__).parent
EXPORTS = Path.home() / "exports_from_davinci"
INBOX_PUBLIC = EXPORTS / "new"
INBOX_PRIVATE = EXPORTS / "private"
PROD = BASE / "production"
PIPE = BASE / "process.py"
TPL_PUBLIC = BASE / "config.default.json"
TPL_PRIVATE = BASE / "config.private.json"

SEEN = set()
DELAY = 5

def stable(p):
    s = p.stat().st_size
    time.sleep(5)
    return s == p.stat().st_size

EXPORTS.mkdir(exist_ok=True)
INBOX_PUBLIC.mkdir(exist_ok=True)
INBOX_PRIVATE.mkdir(exist_ok=True)
PROD.mkdir(exist_ok=True)

# Sources à surveiller : (Dossier, Template Config)
SOURCES = [
    (INBOX_PUBLIC, TPL_PUBLIC),
    (INBOX_PRIVATE, TPL_PRIVATE)
]

print("👀 Surveillance active sur :")
print(f"  - {INBOX_PUBLIC} (Public)")
print(f"  - {INBOX_PRIVATE} (Privé)")

while True:
    try:
        for inbox, tpl in SOURCES:
            if not inbox.exists(): continue
            
            for entry in inbox.iterdir():
                if entry.name in SEEN or entry.name.startswith("."):
                    continue

                master = None
                target_name = None

                # CAS 1 : Un fichier direct
                if entry.is_file() and entry.suffix.lower() in [".mp4", ".mov"]:
                    master = entry
                    target_name = entry.stem 
                
                # CAS 2 : Un dossier
                elif entry.is_dir():
                    mp4 = entry / "video_master.mp4"
                    mov = entry / "video_master.mov"
                    if mp4.exists(): master = mp4
                    elif mov.exists(): master = mov
                    target_name = entry.name

                if not master or not target_name:
                    continue

                if not stable(master):
                    continue
                
                # Suffixe pour le nom de dossier si source privée pour éviter collisions ?
                # Pour l'instant on garde le même nom, mais on log la source
                is_private = inbox == INBOX_PRIVATE
                source_label = "PRIVÉ" if is_private else "PUBLIC"

                print(f"👀 Nouveau projet détecté ({source_label}) : {target_name}")


                # Gestion des collisions : on incrémente si le dossier existe déjà (ex: Projet_v2, Projet_v3...)
                original_target_name = target_name
                counter = 2
                while (PROD / target_name).exists():
                    target_name = f"{original_target_name}_v{counter}"
                    counter += 1
                
                if target_name != original_target_name:
                    print(f"⚠️ Collision détectée ! Renommé en : {target_name}")

                dst = PROD / target_name
                dst.mkdir(parents=True, exist_ok=True)
                shutil.move(str(master), dst / master.name)

                # Chargement de la bonne config
                try:
                    cfg_content = tpl.read_text()
                    cfg = json.loads(cfg_content)
                except Exception as e:
                    print(f"❌ Erreur lecture config {tpl}: {e}")
                    cfg = {}

                cfg["id"] = target_name
                (dst / "config.json").write_text(json.dumps(cfg, indent=2))
                (dst / "status.json").write_text("{}")

                print(f"🚀 Lancement du process pour {target_name}...")
                
                # Création du dossier logs pour capturer les erreurs de démarrage
                (dst / "logs").mkdir(exist_ok=True)
                with open(dst / "logs" / "startup.log", "w") as sl:
                    subprocess.Popen(
                        [sys.executable, str(PIPE), str(dst)],
                        stdout=sl,
                        stderr=subprocess.STDOUT
                    )

                SEEN.add(entry.name)

    except Exception as e:
        print(f"Erreur dans la boucle de surveillance : {e}")

    time.sleep(DELAY)
