#!/usr/bin/env python3
import os
import json
import subprocess
import sys
from pathlib import Path

PROD = Path("production")

def get_status(folder):
    s_file = folder / "status.json"
    if not s_file.exists():
        return None
    try:
        return json.loads(s_file.read_text())
    except:
        return None

def is_stuck(folder):
    st = get_status(folder)
    # If status is None or Empty dict, it failed at startup
    if st is None or st == {}:
        return True
    return False

print("🔍 Recherche des projets coincés...")
stuck_list = []
for item in PROD.iterdir():
    if item.is_dir() and not item.name.startswith("."):
        if is_stuck(item):
            print(f"   ⚠️  Coincé : {item.name}")
            stuck_list.append(item)

if not stuck_list:
    print("✅ Aucun projet coincé détecté.")
    sys.exit(0)

print(f"\n🚀 Relance de {len(stuck_list)} projets...")

for folder in stuck_list:
    print(f"\n---------------------------------------------")
    print(f"▶️  Traitement de : {folder.name}")
    print(f"---------------------------------------------")
    
    # Run process.py
    # We use the same python that runs this script
    cmd = [sys.executable, "process.py", str(folder)]
    
    ret = subprocess.call(cmd)
    
    if ret == 0:
        print(f"✅ Succès pour {folder.name}")
    else:
        print(f"❌ Échec pour {folder.name} (Code {ret})")

print("\n✨ Terminé.")
