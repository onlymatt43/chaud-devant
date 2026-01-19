import json
import sys
import os
import requests
from pathlib import Path

# Configuration Bunny (identique aux autres scripts)
API_KEY = "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27" # Stream API Key
LIB_ID = "581630"
SHOWCASE_FILE = Path(__file__).parent / "showcase.json"

def get_video_guid_from_url(url):
    # Extrait le GUID de l'URL : https://.../play/LIB_ID/VIDEO_ID
    if not url: return None
    return url.split("/")[-1]

def delete_from_bunny(guid):
    url = f"https://video.bunnycdn.com/library/{LIB_ID}/videos/{guid}"
    headers = {"AccessKey": API_KEY, "expect": "application/json"}
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            print(f"✅ Vidéo supprimée de Bunny Stream : {guid}")
            return True
        else:
            print(f"⚠️ Erreur suppression Bunny ({guid}) : {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur connexion Bunny : {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 delete_video.py <ID_DU_PROJET>")
        print("Exemple: python3 delete_video.py Ma_Super_Promo")
        
        # Affiche la liste des IDs disponibles
        if SHOWCASE_FILE.exists():
            print("\nProjets actuels :")
            try:
                data = json.loads(SHOWCASE_FILE.read_text())
                for item in data:
                    print(f" - {item.get('id')}")
            except:
                pass
        return

    target_id = sys.argv[1]
    
    if not SHOWCASE_FILE.exists():
        print("Fichier showcase.json introuvable.")
        return

    data = json.loads(SHOWCASE_FILE.read_text())
    
    # 1. Trouver le projet
    found_item = None
    new_data = []
    
    for item in data:
        if item.get("id") == target_id:
            found_item = item
        else:
            new_data.append(item)
    
    if not found_item:
        print(f"❌ Projet '{target_id}' introuvable dans showcase.json")
        return

    print(f"🗑 Suppression du projet : {target_id}")

    # 2. Supprimer les vidéos sur Bunny Stream
    urls = found_item.get("bunny_urls", {})
    for fmt, url in urls.items():
        guid = get_video_guid_from_url(url)
        if guid:
            print(f"   - Format {fmt}...")
            delete_from_bunny(guid)

    # 3. Mettre à jour showcase.json
    SHOWCASE_FILE.write_text(json.dumps(new_data, indent=2))
    print("✅ showcase.json mis à jour.")
    print("La vidéo ne sera plus visible sur le site web.")

    # 4. (Optionnel) Archiver ou supprimer le dossier local ?
    # Pour l'instant on ne touche pas aux fichiers locaux par sécurité
    print(f"ℹ️ Note : Les fichiers locaux dans 'production/{target_id}' n'ont pas été supprimés.")

if __name__ == "__main__":
    main()
