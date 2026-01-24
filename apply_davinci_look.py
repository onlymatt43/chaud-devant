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
                result = False
                
                # ESSAI 1 : Méthode Standard TimelineItem
                if hasattr(item, "ApplyGradeFromDRX"):
                    print("👉 Essai 1 : TimelineItem.ApplyGradeFromDRX")
                    result = item.ApplyGradeFromDRX(BASE_LOOK_PATH, 1) # 1 = Wipe (Replace)

                # ESSAI 2 : Méthode MediaPoolItem (Si Essai 1 échoue)
                if not result:
                     media_pool_item = item.GetMediaPoolItem()
                     if media_pool_item and hasattr(media_pool_item, "ApplyGradeFromDRX"):
                         print("👉 Essai 2 : MediaPoolItem.ApplyGradeFromDRX")
                         # Attention: ceci change le clip source (donc toutes ses instances)
                         result = media_pool_item.ApplyGradeFromDRX(BASE_LOOK_PATH, 1)

                # ESSAI 3 : Méthode Gallery (La plus robuste si le fichier ne passe pas)
                # Nécessite que le DRX soit déjà dans la galerie, un peu complexe à scripter sans Gallery API
                
                if not result:
                    print(f"⚠️ Échec : Impossible d'appliquer le grade sur {item.GetName()}.")
                    # On évite le spam debug pour l'instant
                else:
                    applied_count += 1
                    print(f"✅ Grade appliqué avec succès !")
                    print(f"✅ Grade appliqué sur : {item.GetName()}")
                else:
                    print(f"⚠️ Échec sur : {item.GetName()}")

    print(f"Terminé ! Look appliqué sur {applied_count} clips.")
    print("⚠️ N'oubliez pas de lancer l'analyse (Tracking) si vous avez des effets de Face Refinement.")

if __name__ == "__main__":
    main()
