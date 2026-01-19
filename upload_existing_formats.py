#!/usr/bin/env python3
"""
Script pour uploader les formats existants vers Bunny Stream
sans avoir à retraiter les vidéos.
"""
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

def log_event(f, p):
    import datetime
    p["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    with f.open("a") as fh: fh.write(json.dumps(p) + "\n")

def bunny_stream_upload(file_path, stream_cfg, log, title=None):
    """Upload vers Bunny Stream"""
    if not stream_cfg: return None
    try:
        headers = {"AccessKey": stream_cfg["access_key"], "Content-Type": "application/json"}
        # 1. Créer l'entrée vidéo
        video_title = title if title else file_path.name
        create_url = f"https://video.bunnycdn.com/library/{stream_cfg['library_id']}/videos"
        resp = requests.post(create_url, headers=headers, json={"title": video_title})
        resp.raise_for_status()
        video_id = resp.json()["guid"]

        # 2. Upload du fichier
        upload_url = f"https://video.bunnycdn.com/library/{stream_cfg['library_id']}/videos/{video_id}"
        with open(file_path, "rb") as f:
            t = time.time()
            resp = requests.put(upload_url, headers={"AccessKey": stream_cfg["access_key"]}, data=f)
            resp.raise_for_status()
            dur = round(time.time() - t, 2)
            log_event(log, {"step": "bunny_stream_upload", "video_id": video_id, "title": video_title, "status": "ok", "dur": dur})

        # Retourne l'URL de lecture
        return f"https://iframe.mediadelivery.net/play/{stream_cfg['library_id']}/{video_id}"
    except Exception as e:
        log_event(log, {"step": "bunny_stream_upload", "file": file_path.name, "status": "fail", "err": str(e)})
        print(f"❌ Erreur upload {file_path.name}: {e}")
        return None

def upload_project_formats(project_folder):
    """Upload tous les formats d'un projet"""
    project = Path(project_folder)
    config_file = project / "config.json"
    status_file = project / "status.json"
    formats_dir = project / "output" / "formats"
    
    if not config_file.exists():
        print(f"❌ Config non trouvée: {config_file}")
        return
    
    # Charger la config
    with open(config_file) as f:
        config = json.load(f)
    
    # Charger le status
    status = {}
    if status_file.exists():
        with open(status_file) as f:
            status = json.load(f)
    
    # Préparer la config Bunny Stream
    stream_cfg = config.get("bunny_stream", {})
    if os.getenv("BUNNY_LIBRARY_ID"):
        stream_cfg["library_id"] = os.getenv("BUNNY_LIBRARY_ID")
    if os.getenv("BUNNY_ACCESS_KEY"):
        stream_cfg["access_key"] = os.getenv("BUNNY_ACCESS_KEY")
    
    if not stream_cfg.get("library_id") or not stream_cfg.get("access_key"):
        print(f"❌ Config Bunny Stream manquante pour {project.name}")
        return
    
    # Créer le dossier logs
    logs_dir = project / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "upload_formats.jsonl"
    
    project_id = config.get("id", project.name)
    
    # Scanner les formats disponibles
    if not formats_dir.exists():
        print(f"❌ Aucun format trouvé dans {formats_dir}")
        return
    
    format_files = list(formats_dir.glob("web_*.mp4"))
    if not format_files:
        print(f"❌ Aucun fichier web_*.mp4 trouvé dans {formats_dir}")
        return
    
    print(f"\n📦 Traitement de: {project_id}")
    print(f"   Formats trouvés: {len(format_files)}")
    
    # Initialiser bunny_urls dans le status
    if "bunny_urls" not in status:
        status["bunny_urls"] = {}
    
    # Upload chaque format
    for format_file in format_files:
        # Extraire le nom du format (ex: web_16x9.mp4 -> 16x9)
        format_name = format_file.stem.replace("web_", "")
        
        # Vérifier si déjà uploadé
        if format_name in status["bunny_urls"]:
            print(f"   ⏭️  {format_name}: Déjà uploadé ({status['bunny_urls'][format_name]})")
            continue
        
        print(f"   ⬆️  Upload {format_name}...", end=" ", flush=True)
        
        # Upload vers Bunny Stream
        title = f"{project_id} ({format_name})"
        url = bunny_stream_upload(format_file, stream_cfg, log_file, title=title)
        
        if url:
            status["bunny_urls"][format_name] = url
            print(f"✅ {url}")
        else:
            print(f"❌ Échec")
    
    # Sauvegarder le status mis à jour
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)
    
    print(f"   💾 Status sauvegardé")
    
    # Mettre à jour l'inventaire
    update_inventory(project, config, status)

def update_inventory(project, config, status):
    """Met à jour le fichier inventory.json"""
    inventory_dir = project / "output" / "inventory"
    inventory_dir.mkdir(parents=True, exist_ok=True)
    inventory_file = inventory_dir / "inventory.json"
    
    inventory = {
        "id": config.get("id", project.name),
        "captions": [k for k, v in status.get("captions", {}).items() if v == "done"],
        "formats_generated": [k for k, v in status.get("formats", {}).items() if v == "done"],
        "bunny_urls": status.get("bunny_urls", {}),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=2)

def main():
    """Upload tous les formats de tous les projets"""
    production_dir = Path(__file__).parent / "production"
    
    if not production_dir.exists():
        print(f"❌ Dossier production non trouvé: {production_dir}")
        return
    
    # Lister tous les projets
    projects = [d for d in production_dir.iterdir() if d.is_dir() and (d / "config.json").exists()]
    
    if not projects:
        print("❌ Aucun projet trouvé")
        return
    
    print(f"🚀 Upload des formats vers Bunny Stream")
    print(f"   Projets trouvés: {len(projects)}")
    print(f"   Library ID: {os.getenv('BUNNY_LIBRARY_ID')}")
    
    for project in projects:
        try:
            upload_project_formats(project)
        except Exception as e:
            print(f"❌ Erreur sur {project.name}: {e}")
    
    print("\n✅ Traitement terminé!")

if __name__ == "__main__":
    main()
