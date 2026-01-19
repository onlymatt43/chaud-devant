#!/usr/bin/env python3
"""
Script de nettoyage pour Bunny Stream.
Permet de lister, supprimer les doublons ou tout supprimer.
"""
import os
import requests
import argparse
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

LIBRARY_ID = os.getenv("BUNNY_LIBRARY_ID")
ACCESS_KEY = os.getenv("BUNNY_ACCESS_KEY")

if not LIBRARY_ID or not ACCESS_KEY:
    print("❌ Erreur: Identifiants Bunny manquants dans .env")
    exit(1)

BASE_URL = f"https://video.bunnycdn.com/library/{LIBRARY_ID}/videos"
HEADERS = {
    "AccessKey": ACCESS_KEY,
    "accept": "application/json"
}

def get_all_videos():
    print("🔍 Récupération de la liste des vidéos...")
    videos = []
    page = 1
    while True:
        url = f"{BASE_URL}?page={page}&itemsPerPage=100&orderBy=date"
        resp = requests.get(url, headers=HEADERS)
        if not resp.ok:
            print(f"❌ Erreur API: {resp.status_code} - {resp.text}")
            break
        
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
            
        videos.extend(items)
        if len(items) < 100:
            break
        page += 1
    
    print(f"✅ {len(videos)} vidéos trouvées.")
    return videos

def delete_video(video_id, title):
    url = f"{BASE_URL}/{video_id}"
    resp = requests.delete(url, headers=HEADERS)
    if resp.ok:
        print(f"🗑️  Supprimé: {title} ({video_id})")
        return True
    else:
        print(f"❌ Échec suppression {title}: {resp.text}")
        return False

def analyze_duplicates(videos):
    groups = defaultdict(list)
    for v in videos:
        groups[v['title']].append(v)
    
    duplicates = []
    for title, v_list in groups.items():
        if len(v_list) > 1:
            # Sort by date descending (newest first)
            v_list.sort(key=lambda x: x['dateUploaded'], reverse=True)
            # Keep the first (newest), mark others for deletion
            duplicates.extend(v_list[1:])
            
    return duplicates

def main():
    parser = argparse.ArgumentParser(description="Clean up Bunny Stream videos")
    parser.add_argument("--delete-all", action="store_true", help="Delete ALL videos")
    parser.add_argument("--delete-duplicates", action="store_true", help="Delete duplicate titles (keep newest)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    
    args = parser.parse_args()
    
    videos = get_all_videos()
    
    if not videos:
        print("Rien à nettoyer.")
        return

    if args.delete_all:
        print(f"⚠️  ATTENTION: Vous allez supprimer {len(videos)} vidéos.")
        if not args.dry_run:
            confirm = input("Êtes-vous sûr ? (oui/non): ")
            if confirm.lower() != "oui":
                print("Annulé.")
                return

        for v in videos:
            if args.dry_run:
                print(f"Would delete: {v['title']} ({v['guid']})")
            else:
                delete_video(v['guid'], v['title'])
                
    elif args.delete_duplicates:
        duplicates = analyze_duplicates(videos)
        print(f"⚠️  Trouvé {len(duplicates)} doublons à supprimer.")
        
        for v in duplicates:
            if args.dry_run:
                print(f"Would delete (older duplicate): {v['title']} ({v['guid']}) - Date: {v['dateUploaded']}")
            else:
                delete_video(v['guid'], v['title'])
    else:
        print("\n📊 Analyse de la bibliothèque:")
        groups = defaultdict(list)
        for v in videos:
            groups[v['title']].append(v)
            
        for title, v_list in groups.items():
            print(f"- {title}: {len(v_list)} versions")
            for v in v_list:
                print(f"  • {v['guid']} ({v['width']}x{v['height']}) - {v['dateUploaded']}")
        
        print("\nUtilisation:")
        print("  python cleanup_bunny.py --delete-duplicates  (Supprime les anciennes versions)")
        print("  python cleanup_bunny.py --delete-all         (Supprime TOUT)")
        print("  python cleanup_bunny.py --dry-run ...        (Simulation)")

if __name__ == "__main__":
    main()
