import json
import shutil
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
PROD = BASE / "production"
SHOWCASE_FILE = BASE / "showcase.json"
PROCESS_PY = BASE / "process.py"

def load_json(path):
    if not path.exists(): return []
    try:
        return json.loads(path.read_text())
    except:
        return []

def main():
    print("🔄 SYNC PRODUCTION: 'Dossiers Locaux' -> 'Site Web' + 'Bunny'")
    
    # 1. Lister les projets valides dans production/ (Ceux qui ont un status.json)
    if not PROD.exists():
        print("Dossier production/ introuvable.")
        return

    local_projects = {}
    for entry in PROD.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            local_projects[entry.name] = entry

    print(f"📁 Projets trouvés en local: {len(local_projects)}")

    # 2. Nettoyer showcase.json (Retirer ce qui n'existe plus en local)
    current_showcase = load_json(SHOWCASE_FILE)
    cleaned_showcase = []
    ids_in_showcase = set()
    
    deleted_count = 0
    for item in current_showcase:
        vid_id = item.get("id")
        if vid_id in local_projects:
            cleaned_showcase.append(item)
            ids_in_showcase.add(vid_id)
        else:
            print(f"❌ SUPPRESSION: Le projet '{vid_id}' n'est plus dans production/. Retrait du site.")
            # Note: Pour une suppression complète, on pourrait aussi appeler l'API Bunny ici pour supprimer le fichier distant.
            # Pour l'instant, on nettoie juste le site vitrine.
            # Si vous voulez aussi supprimer de Bunny, décommentez ceci:
            # subprocess.run([sys.executable, "delete_video.py", vid_id])
            deleted_count += 1
    
    if deleted_count > 0:
        SHOWCASE_FILE.write_text(json.dumps(cleaned_showcase, indent=2))
        print(f"✅ {deleted_count} entrée(s) supprimée(s) de showcase.json.")
    else:
        print("✅ showcase.json est propre.")

    # 3. Ajouter/Régénérer ce qui manque (Present en local mais absent de showcase)
    #    On peut aussi relancer le process si on veut être sûr que tout est à jour.
    
    for pid, ppath in local_projects.items():
        if pid not in ids_in_showcase:
            print(f"⚠️ MANQUANT: Le projet '{pid}' n'est pas dans le showcase. Régénération...")
            subprocess.run([sys.executable, str(PROCESS_PY), str(ppath)])
        else:
            # Optionnel: Vérifier si toutes les URLs sont là (ex: format carré manquant)
            # Sinon on peut laisser faire.
            pass

    print("\n🎉 Synchronisation terminée.")

if __name__ == "__main__":
    main()
