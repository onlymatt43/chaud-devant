import os
import sys

# Configuration
# Le chemin vers votre fichier de "Grade" exporté (.drx)
# Vous devez créer ce fichier une fois dans DaVinci (Grab Still -> Export)
BASE_LOOK_PATH = os.path.join(os.path.dirname(__file__), "templates", "base_look.drx")

def get_resolve():
    try:
        import DaVinciResolveScript as bmd
        return bmd.scriptapp("Resolve")
    except ImportError:
        return None

def main():
    resolve = get_resolve()
    if not resolve:
        print("❌ Impossible de se connecter à DaVinci Resolve.")
        return

    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    
    if not timeline:
        print("❌ Aucune timeline ouverte.")
        return

    print(f"🎨 Application du Look sur : {timeline.GetName()}")

    if not os.path.exists(BASE_LOOK_PATH):
        print(f"❌ Fichier de Look introuvable : {BASE_LOOK_PATH}")
        print("👉 Veuillez exporter un 'Still' depuis la page Color (.drx) et le placer ici.")
        return

    # Parcourir tous les clips vidéos
    track_count = timeline.GetTrackCount("video")
    
    applied_count = 0
    
    for track_index in range(1, track_count + 1):
        items = timeline.GetItemListInTrack("video", track_index)
        for item in items:
            # On vérifie si c'est bien un clip vidéo (pas un titre ou un audio)
            if item.GetMediaPoolItem(): 
                # Mode 1 = Copy Grade : Remplace le grade existant
                # Mode 2 = Append Grade : Ajoute à la fin (Plus sûr si vous avez déjà travaillé)
                # Malheureusement l'API Python est limitée ici, ApplyGradeFromDRX remplace souvent.
                
                # Astuce : On applique le DRX
                result = item.ApplyGradeFromDRX(BASE_LOOK_PATH, 1)
                
                if result:
                    applied_count += 1
                    print(f"✅ Grade appliqué sur : {item.GetName()}")
                else:
                    print(f"⚠️ Échec sur : {item.GetName()}")

    print(f"Terminé ! Look appliqué sur {applied_count} clips.")
    print("⚠️ N'oubliez pas de lancer l'analyse (Tracking) si vous avez des effets de Face Refinement.")

if __name__ == "__main__":
    main()
