#!/usr/bin/env python3
"""
Script pour régénérer tous les formats vidéos (après correction du bug d'aspect ratio)
et les ré-uploader.
"""
import shutil
import json
import logging
from pathlib import Path
from process import process, load_json, save_json

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def regenerate_project(project_path):
    p = Path(project_path)
    if not p.is_dir() or not (p / "config.json").exists():
        return

    print(f"♻️  Régénération de : {p.name}")
    
    # 1. Nettoyer les fichiers générés (formats)
    formats_dir = p / "output" / "formats"
    if formats_dir.exists():
        shutil.rmtree(formats_dir)
        formats_dir.mkdir(parents=True)
        print("   ✅ Dossier formats vidé")

    # 2. Reset Status
    status_file = p / "status.json"
    status = load_json(status_file, {})
    
    # On supprime les entrées qui empêchent le retraitement
    if "formats" in status:
        del status["formats"]
    if "bunny_urls" in status:
        del status["bunny_urls"]
        
    save_json(status_file, status)
    print("   ✅ Status réinitialisé")

    # 3. Relancer le process
    print("   ▶️  Lancement du traitement...")
    try:
        process(str(p))
        print("   ✅ Traitement terminé avec succès")
    except Exception as e:
        print(f"   ❌ Erreur durant le traitement: {e}")

def main():
    root = Path(__file__).parent / "production"
    
    # Lister les projets
    projects = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    print(f"🚀 Début de la régénération massive ({len(projects)} projets)")
    
    for proj in projects:
        regenerate_project(proj)

    print("\n🏁 Tout est terminé !")

if __name__ == "__main__":
    main()
