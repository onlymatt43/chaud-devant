import os
import shutil
from pathlib import Path

# --- CHEMINS ---
BASE_DIR = Path(__file__).parent.parent
# EXPORTS_DIR supprimé (V3 Direct)
PRODUCTION_BASE_DIR = BASE_DIR / "production"
PRODUCTION_PUBLIC = PRODUCTION_BASE_DIR / "public"
PRODUCTION_PRIVATE = PRODUCTION_BASE_DIR / "private"

# --- SYSTEME ---
# Détection automatique des outils pour éviter les erreurs "Command not found"
def get_tool(name):
    path = shutil.which(name)
    if path: return path
    common = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        f"/Library/Frameworks/Python.framework/Versions/3.13/bin/{name}"
    ]
    for p in common:
        if os.path.exists(p): return p
    return name # Retourne le nom par défaut si non trouvé (pourra planter plus loin, mais on essaie)

FFMPEG = get_tool("ffmpeg")
FFPROBE = get_tool("ffprobe")
WHISPER = get_tool("whisper")

# --- BUNNY.NET ---
# Stream Library IDs
LIB_PUBLIC = "581630"
LIB_PRIVATE = "552081"

# API Keys (Récupérées de l'ancien système)
API_KEY_PUBLIC = "7b43d33b-576e-4890-8fb1dae4d73d-9663-4f27"
API_KEY_PRIVATE = "202d4df5-5617-4738-9c82a7cae508-e3c5-48ef" # Key from config.private.json

# Pull Zones (Pour lecture Web)
PULL_ZONE_PUBLIC = "https://vz-72668a20-6b9.b-cdn.net"
PULL_ZONE_PRIVATE = "https://vz-c69f4e3f-963.b-cdn.net"

# --- VERCEL / DATA ---
# Le fichier JSON central qui sert de base de données pour le site
# NOTE : On va utiliser un seul fichier "showcase.json" qui contiendra tout (public et privé)
# avec un flag "is_private". Cela simplifie grandement la logique Vercel.
DB_FILE = BASE_DIR / "showcase_v2.json"

# --- WORKER SETTINGS ---
# Formats à générer (Standard Web)
FORMATS = ["16x9", "9x16", "1x1"]
DEFAULT_LANGS = ["fr", "en"]
