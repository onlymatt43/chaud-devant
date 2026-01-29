import time
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime
import config
from worker_v2 import process_video

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("watcher_v2.log"),
        logging.StreamHandler()
    ]
)

def is_file_stable(path, wait_time=5):
    """Vérifie si le fichier a fini d'être écrit (taille stable)."""
    if not path.exists(): return False
    
    # Si c'est un dossier, on regarde la taille cumulée des fichiers
    if path.is_dir():
        def get_dir_size(p):
            return sum(f.stat().st_size for f in p.glob('**/*') if f.is_file())
            
        size1 = get_dir_size(path)
        # Si vide, on donne une chande (DaVinci peut prendre qqs secondes pour créer le fichier)
        if size1 == 0:
             time.sleep(wait_time)
             size1 = get_dir_size(path)
             if size1 == 0: return False # Toujours vide -> pas prêt
             
        time.sleep(wait_time)
        size2 = get_dir_size(path)
        # On veut que ça soit stable ET > 0
        return size1 == size2 and size1 > 0
        
    else:
        # Fichier simple
        size1 = path.stat().st_size
        time.sleep(wait_time)
        if not path.exists(): return False # Peut avoir disparu entre temps
        size2 = path.stat().st_size
        return size1 == size2 and size1 > 0

def find_master_video(folder_path):
    """Trouve le fichier vidéo principal dans un dossier."""
    video_extensions = {".mp4", ".mov", ".mkv", ".mxf", ".avi"}
    candidates = []
    
    for f in folder_path.iterdir():
        if f.is_file() and f.suffix.lower() in video_extensions:
            # On ignore les fichiers systèmes cachés (type ._video.mov)
            if f.name.startswith("."): continue
            candidates.append(f)
            
    if not candidates: return None
    
    # On prend le plus gros fichier pour éviter les proxies ou fichiers temporaires
    best_candidate = max(candidates, key=lambda x: x.stat().st_size)
    return best_candidate

def main():
    logging.info("👀 WATCHER V3 (DIRECT-PROD) STARTED")
    logging.info(f"   Public Prod Area : {config.PRODUCTION_PUBLIC}")
    logging.info(f"   Private Prod Area: {config.PRODUCTION_PRIVATE}")
    
    # S'assurer que les dossiers existent
    config.PRODUCTION_PUBLIC.mkdir(parents=True, exist_ok=True)
    config.PRODUCTION_PRIVATE.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            # Check des deux zones de production directement
            for prod_area, is_private in [(config.PRODUCTION_PUBLIC, False), (config.PRODUCTION_PRIVATE, True)]:
                if not prod_area.exists(): continue
                
                # On scanne les PROJETS (dossiers)
                entries = sorted(list(prod_area.iterdir()), key=lambda x: x.stat().st_mtime)
                
                for project_dir in entries:
                    if project_dir.name.startswith("."): continue 
                    if not project_dir.is_dir(): continue

                    # 1. Check si déjà traité
                    if (project_dir / "status.json").exists():
                        continue 

                    # 2. Cherche une vidéo stable
                    video_master = find_master_video(project_dir)
                    
                    if video_master and is_file_stable(video_master):
                        project_id = project_dir.name
                        logging.info(f"✨ NEW DETECTED (V3): {project_id} | File: {video_master.name}")
                        
                        # 3. PROCESS DIRECT
                        logging.info(f"⚙️ Processing {project_id}...")
                        success = process_video(
                            project_id=project_id,
                            prod_dir=project_dir, # Le dossier EST le dossier de prod
                            video_path=video_master,
                            is_private=is_private
                        )
                        
                        if success:
                            logging.info(f"✅ DONE: {project_id}")
                        else:
                            logging.error(f"❌ FAILED: {project_id}")

        except Exception as e:
            logging.error(f"🔥 CRITICAL WATCHER ERROR: {e}")
            time.sleep(5) 
        
        time.sleep(2)

if __name__ == "__main__":
    main()
