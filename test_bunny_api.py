#!/usr/bin/env python3
"""Test de l'API Bunny pour voir les vidéos disponibles"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

library_id = os.getenv("BUNNY_LIBRARY_ID")
access_key = os.getenv("BUNNY_ACCESS_KEY")

print(f"🔍 Test API Bunny Stream")
print(f"   Library ID: {library_id}")
print(f"   Access Key: {'*' * 20}{access_key[-8:] if access_key else 'None'}")
print()

url = f"https://video.bunnycdn.com/library/{library_id}/videos?itemsPerPage=50&orderBy=date"

response = requests.get(
    url,
    headers={
        "AccessKey": access_key,
        "accept": "application/json"
    }
)

print(f"Status: {response.status_code}")

if response.ok:
    data = response.json()
    print(f"✅ Nombre de vidéos: {data['totalItems']}")
    print()
    
    for video in data['items'][:10]:  # Top 10
        print(f"📹 {video['title']}")
        print(f"   ID: {video['guid']}")
        print(f"   Taille: {video['width']}x{video['height']}")
        print(f"   Date: {video['dateUploaded']}")
        print(f"   URL: https://iframe.mediadelivery.net/play/{library_id}/{video['guid']}")
        print()
else:
    print(f"❌ Erreur: {response.text}")
