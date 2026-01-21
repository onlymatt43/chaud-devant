#!/bin/bash
cd "$(dirname "$0")"
echo "🎵 Lancement de la synchronisation musicale..."
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/mathieucourchesne/chaud-devant/beat_sync_video.py
echo " "
read -p "Appuie sur Entrée pour fermer..."