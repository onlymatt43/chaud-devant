import sys
import os

# Ajout du chemin des modules DaVinci pour macOS si nécessaire
RESOLVE_SCRIPT_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/"
if os.path.exists(RESOLVE_SCRIPT_API):
    sys.path.append(RESOLVE_SCRIPT_API)

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("❌ Impossible de trouver le module DaVinciResolveScript.")
    # Fallback: essaie de charger via l'environnement standard si dispo
    try:
        import imp
        dvr_script = imp.load_source('DaVinciResolveScript', RESOLVE_SCRIPT_API + "DaVinciResolveScript.py")
    except:
        print("Assurez-vous d'avoir configuré le PYTHONPATH ou de lancer ce script via DaVinci Resolve.")
        sys.exit(1)

def super_setup():
    try:
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            print("Could not connect to DaVinci Resolve.")
            return
            
        project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()

    # 1. CRÉATION DES DOSSIERS (BINS)
    folders = ["01_RUSH_CAMERAS", "02_AUDIO", "03_GRAPHICS", "04_RENDER_OUTPUT"]
    for folder_name in folders:
        media_pool.AddSubFolder(root_folder, folder_name)

    # 2. CONFIGURATION DE LA QUALITÉ (COLOR MANAGEMENT)
    # Active la gestion des couleurs automatique pour un look pro immédiat
    project.SetSetting("colorScienceMode", "davinciYRGBColorManaged")
    project.SetSetting("inputColorSpaceDefault", "Rec.709 (Scene)")
    
    # 3. CRÉATION DES TIMELINES MULTIFORMATS
    formats = [
        ("MASTER_4K_HORIZ", 3840, 2160),
        ("VERTICAL_SOCIAL", 1080, 1920),
        ("SQUARE_INSTA", 1080, 1080)
    ]

    for name, width, height in formats:
        timeline = media_pool.CreateEmptyTimeline(name)
        if timeline:
            timeline.SetSetting("timelineResolutionWidth", str(width))
            timeline.SetSetting("timelineResolutionHeight", str(height))
            # Optimisation du redimensionnement pour le 4K
            timeline.SetSetting("timelineMismatchResolutionMode", "scaleFullFrameWithCrop")

    # 4. CONFIGURATION DE L'EXPORT (AUTOMATISATION)
    # Configure le chemin par défaut vers le dossier surveillé par auto_watch.py
    import os
    export_path = os.path.expanduser("~/exports_from_davinci")
    
    # Création du dossier s'il n'existe pas
    if not os.path.exists(export_path):
        try:
            os.makedirs(export_path)
        except OSError:
            pass

    # On pré-configure les settings de rendu pour pointer vers le dossier surveillé
    project.SetRenderSettings({
        "TargetDir": export_path,
        "CustomName": "video_master",
        "Format": "mp4",
        "VideoCodec": "H264",
        "ExportVideo": True,
        "ExportAudio": True
    })

    project_manager.SaveProject()
    print(f"Super Setup Pro déployé ! Export configuré vers : {export_path}")

if __name__ == "__main__":
    super_setup()