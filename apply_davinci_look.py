import os
import sys

# Configuration
# Chemin absolu vers le projet (plus robuste dans DaVinci)
PROJECT_ROOT = "/Users/mathieucourchesne/chaud-devant"
BASE_LOOK_PATH = os.path.join(PROJECT_ROOT, "templates", "base_look.drx")

def get_resolve():
    try:
        # 1. Essai standard (Fonctionne souvent dans la console interne)
        return resolve
    except NameError:
        try:
            # 2. Essai module (Fonctionne pour les scripts externes ou studio)
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
                print(f"🔍 Analyse de : {item.GetName()}")
                
                # DIAGNOSTIC POUR DAVINCI 20
                if not hasattr(item, "ApplyGradeFromDRX") or item.ApplyGradeFromDRX is None:
                    print(f"⚠️ La commande 'ApplyGradeFromDRX' n'est pas disponible pour ce clip.")
                    # On tente une méthode alternative si elle existe
                    if hasattr(item, "LoadGradeFromDRX") and item.LoadGradeFromDRX:
                        print(f"👉 Tentative avec LoadGradeFromDRX (Alternative)...")
                        result = item.LoadGradeFromDRX(BASE_LOOK_PATH, 1)
                    else:
                        # DIAGNOSTIC COMPLET (DUMP)
                        debug_file = os.path.join(PROJECT_ROOT, "debug_methods.txt")
                        with open(debug_file, "w") as df:
                            df.write(f"Type de l'objet item: {type(item)}\n")
                            df.write("Méthodes disponibles:\n")
                            for method in dir(item):
                                df.write(f"{method}\n")
                        
                        print(f"🛑 ÉCHEC. Liste des commandes sauvegardée dans : {debug_file}")
                        print("👉 Veuillez me copier le contenu de ce fichier ou me dire s'il contient 'Apply' ou 'Still'.")
                        return # On arrête tout de suite pour ne pas spammer
                else:
                    # Méthode standard
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
