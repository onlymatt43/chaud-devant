import os
import sys
import requests
import re
from pathlib import Path

# Configuration (identiques aux autres scripts)
API_KEY = "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27"
LIB_ID = "581630"
PROD_DIR = Path(__file__).parent / "production"

if not PROD_DIR.exists():
    print("❌ Dossier production introuvable.")
    sys.exit(1)

def get_local_projects():
    projects = set()
    for entry in PROD_DIR.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            projects.add(entry.name)
    return projects

def get_bunny_videos():
    # On récupère tout (jusqu'à 1000 vidéos)
    url = f"https://video.bunnycdn.com/library/{LIB_ID}/videos?itemsPerPage=1000"
    headers = {"AccessKey": API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Erreur API Bunny: {resp.status_code}")
        return []
    return resp.json().get("items", [])

def delete_video(guid, title):
    url = f"https://video.bunnycdn.com/library/{LIB_ID}/videos/{guid}"
    headers = {"AccessKey": API_KEY}
    resp = requests.delete(url, headers=headers)
    if resp.status_code == 200:
        print(f"✅ Supprimé: {title}")
    else:
        print(f"❌ Erreur suppression {title}: {resp.status_code}")

def main():
    print("--- SYNCHRONISATION BUNNY STREAM ---")
    print("But: Supprimer de Bunny TOUT ce qui n'est pas dans le dossier 'production/' local.\n")
    
    # 1. Projets Locaux
    local_ids = get_local_projects()
    print(f"📂 Projets locaux ({len(local_ids)}) : {', '.join(sorted(local_ids))}")
    
    # 2. Vidéos Bunny
    print("☁️  Récupération des vidéos sur Bunny...")
    videos = get_bunny_videos()
    print(f"☁️  {len(videos)} vidéos trouvées en ligne.")
    
    to_delete = []
    kept_count = 0
    
    # 3. Comparaison
    for vid in videos:
        title = vid.get("title", "")
        guid = vid.get("guid")
        
        # Le titre est formaté comme "ProjectID (Format)" ex: "my-video (16x9)"
        # Regex pour capturer ce qu'il y a avant la dernière parenthèse de format
        match = re.match(r"^(.*) \(\d+x\d+\)$", title)
        
        if match:
            project_id = match.group(1)
        else:
            # Si le format n'est pas standard (vieux uploads), on prend le titre brut
            project_id = title

        # Vérification stricte
        if project_id in local_ids:
            kept_count += 1
        else:
            to_delete.append((guid, title, project_id))

    print(f"✅ Vidéos valides conservées : {kept_count}")

    if not to_delete:
        print("\n✨ Votre bibliothèque est parfaitement synchronisée ! Rien à supprimer.")
        return

    print(f"\n🗑  {len(to_delete)} vidéos orphelines trouvées sur Bunny (à supprimer) :")
    for guid, title, pid in to_delete:
        print(f"  - [ ] {title}")
        # print(f"        (ID détecté: '{pid}' non trouvé en local)")
    
    print("\n⚠️  ATTENTION: Ces vidéos n'existent plus sur votre disque.")
    confirm = input("🔥 Tapez 'oui' pour confirmer la suppression définitive : ")
    
    if confirm.lower() == "oui":
        print("\n🚀 Démarrage du nettoyage...")
        for guid, title, pid in to_delete:
            delete_video(guid, title)
        print("🧹 Nettoyage terminé.")
    else:
        print("❌ Opération annulée.")

if __name__ == "__main__":
    main()
