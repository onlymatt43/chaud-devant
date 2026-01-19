import json
import shutil
from pathlib import Path

BASE = Path(__file__).parent
PROD = BASE / "production"
DEFAULT_CFG = BASE / "config.default.json"

def main():
    print("🔧 Mise à jour des configurations de projets...")
    
    if not DEFAULT_CFG.exists():
        print("❌ config.default.json introuvable.")
        return

    default_data = json.loads(DEFAULT_CFG.read_text())
    
    for project_dir in PROD.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue
            
        cfg_file = project_dir / "config.json"
        status_file = project_dir / "status.json"
        
        # 1. Update Config (Merge keys)
        # On ne veut pas écraser l'ID du projet, mais on veut mettre à jour les clés API
        project_data = {}
        if cfg_file.exists():
            try:
                project_data = json.loads(cfg_file.read_text())
            except:
                pass
        
        # On force la config bunny_stream du défaut
        project_data["bunny_stream"] = default_data["bunny_stream"]
        project_data["formats"] = default_data["formats"] # On active aussi le 1x1 partout
        if "audio" in default_data:
            project_data["audio"] = default_data["audio"] # Add audio config
        
        cfg_file.write_text(json.dumps(project_data, indent=2))
        print(f"✅ Config mise à jour pour : {project_dir.name}")
        
        # 2. Reset Status (Pour forcer le re-upload)
        # On supprime la section "bunny_urls" pour être sûr
        if status_file.exists():
            try:
                st = json.loads(status_file.read_text())
                if "bunny_urls" in st:
                    del st["bunny_urls"]
                
                # On force aussi le re-check des formats pour déclencher l'upload loop
                # Si on laisse "done", le script process.py va skipper TOUT le bloc.
                # Donc on va supprimer "formats" du status.
                if "formats" in st:
                    del st["formats"]
                
                # Force audio regen
                if "audio" in st:
                    del st["audio"]
                    
                status_file.write_text(json.dumps(st, indent=2))
                print(f"🔄 Status réinitialisé pour : {project_dir.name}")
            except:
                pass

    print("\n🚀 Prêt pour la régénération avec les bonnes clés !")

if __name__ == "__main__":
    main()
