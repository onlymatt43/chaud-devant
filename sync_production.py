import json
import shutil
import sys
import subprocess
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

BASE = Path(__file__).parent
PROD = BASE / "production"

# Configs
PUBLIC_CONF = {
    "file": BASE / "showcase.json",
    "api_key": "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27",
    "lib_id": "581630"
}

PRIVATE_CONF = {
    "file": BASE / "showcase_private.json",
    "config_file": BASE / "config.private.json", # Pour lire la clé
    "api_key": None, # Will be loaded
    "lib_id": "552081"
}

def load_private_key():
    try:
        if PRIVATE_CONF["config_file"].exists():
            data = json.loads(PRIVATE_CONF["config_file"].read_text())
            # On cherche dans bunny_stream
            return data.get("bunny_stream", {}).get("access_key")
    except:
        pass
    return None

def delete_from_bunny(guid, api_key, lib_id):
    if not guid or not api_key: return False
    url = f"https://video.bunnycdn.com/library/{lib_id}/videos/{guid}"
    headers = {"AccessKey": api_key, "expect": "application/json"}
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200 or response.status_code == 404:
            print(f"   ✅ Bunny ({lib_id}) Delete OK: {guid}")
            return True
        else:
            print(f"   ⚠️ Bunny ({lib_id}) Error {response.status_code}: {guid}")
            return False
    except Exception as e:
        print(f"   ❌ Network Error: {guid}")
        return False

def extract_guid(url):
    try:
        parts = url.split("/")
        if len(parts) >= 2:
            return parts[-2]
    except:
        pass
    return None

def load_json(path):
    if not path.exists(): return []
    try:
        return json.loads(path.read_text())
    except:
        return []

def process_sync(conf, local_projects):
    json_path = conf["file"]
    api_key = conf["api_key"]
    lib_id = conf["lib_id"]
    
    if not json_path.exists():
        return False

    print(f"\n🔍 Syncing {json_path.name} (Lib: {lib_id})...")

    current_showcase = load_json(json_path)
    cleaned_showcase = []
    guids_to_delete = []
    
    deleted_count = 0
    
    for item in current_showcase:
        vid_id = item.get("id")
        if vid_id in local_projects:
            cleaned_showcase.append(item)
        else:
            print(f"❌ MARKED FOR DELETE: {vid_id}")
            urls = item.get("bunny_urls", {})
            for fmt, url in urls.items():
                guid = extract_guid(url)
                if guid: guids_to_delete.append(guid)
            deleted_count += 1
    
    # Batch Deletion
    if guids_to_delete:
        if not api_key or "REMPLACER" in api_key:
             print(f"⚠️ Clé API manquante ou invalide pour {lib_id}. Suppression Bunny ignorée.")
        else:
            print(f"🔥 Suppression de {len(guids_to_delete)} vidéos sur Bunny...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                # On passe les args fixes via lambda ou partial
                # map attend une fonction à 1 argument
                list(executor.map(lambda g: delete_from_bunny(g, api_key, lib_id), guids_to_delete))

    if deleted_count > 0:
        json_path.write_text(json.dumps(cleaned_showcase, indent=2))
        print(f"✅ {deleted_count} projet(s) retiré(s) de json.")
        return True
    else:
        print("✅ Aucun nettoyage nécessaire.")
        return False

def main():
    print("🔄 SYNC PRODUCTION (Public & Private)...")
    
    if not PROD.exists():
        print("Dossier production/ introuvable.")
        return

    local_projects = {entry.name for entry in PROD.iterdir() if entry.is_dir() and not entry.name.startswith(".")}
    print(f"📁 Projets locaux: {len(local_projects)} {local_projects}")

    # Load Private Key
    PRIVATE_CONF["api_key"] = load_private_key()

    changes_public = process_sync(PUBLIC_CONF, local_projects)
    changes_private = process_sync(PRIVATE_CONF, local_projects)
    
    if changes_public or changes_private:
        try:
            print("☁️ Mise à jour Vercel...")
            subprocess.run(["git", "add", "showcase.json", "showcase_private.json"], check=False)
            subprocess.run(["git", "commit", "-m", f"Sync Prod: Cleanup"], check=False)
            subprocess.run(["git", "push"], check=True)
            print("🚀 Site web mis à jour !")
        except Exception as e:
            print(f"⚠️ Git Error: {e}")
    else:
        print("✅ Tout est déjà synchro.")

if __name__ == "__main__":
    main()
