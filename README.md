# Chaud Devant - Workflow Video Automatisé

Ce projet automatise le traitement vidéo depuis l'export DaVinci Resolve jusqu'à la publication sur le web (Bunny.net).

## Le Flow Complet

1. **DaVinci Resolve (Montage & Export)**
   - Faites votre montage dans Resolve.
   - Utilisez le script `davinci_export_pipeline.py` pour exporter automatiquement vers le dossier surveillé.
   - Le script va exporter la timeline active en `H.264` (`.mp4`) dans `~/exports_from_davinci`.

2. **Surveillance & Ingestion (`auto_watch.py`)**
   - Lancez le script de surveillance : `python3 auto_watch.py`
   - Il détecte les nouveaux fichiers dans `~/exports_from_davinci`.
   - Il déplace les fichiers dans `production/` et crée la structure du projet.
   - Il lance le traitement (`process.py`).

3. **Traitement (`process.py`)**
   - **Captions** : Génère les sous-titres avec Whisper/OpenAI (si activé).
   - **Branding** : Ajoute l'outro (si activée).
   - **Formats** : Convertit en 16:9, 9:16, etc.
   - **Upload** : Envoie les fichiers sur Bunny Stream.
   - **Inventory** : Met à jour `showcase.json` et `status.json`.

4. **Frontend (`index.html`)**
   - La vitrine web récupère les vidéos via l'API Bunny Stream (via `api/get-videos.js`).

## Installation

### 1. Prérequis Python
Installez les dépendances :
```bash
pip install -r requirements.txt
```
Assurez-vous d'avoir `ffmpeg` et `whisper` installés sur le système.

### 2. Configuration DaVinci Resolve
Pour utiliser le script d'export dans Resolve :
1. Ouvrez DaVinci Resolve.
2. Allez dans `Workspace` > `Console`.
3. Choisissez `Py 3`.
4. Vous pouvez exécuter le script directement, ou le copier dans le dossier des scripts de Resolve :
   - Mac : `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/`
   - Ou exécuter via le terminal système si Resolve est ouvert (nécessite configuration PYTHONPATH).
   
*Le plus simple est d'ouvrir `davinci_export_pipeline.py` dans un éditeur externe et de copier-coller dans la console Resolve ou de le lancer via "Script" menu si placé au bon endroit.*

### 3. Variables d'Environnement (.env)
Créez un fichier `.env` à la racine avec vos clés Bunny.net :
```
BUNNY_LIBRARY_ID=...
BUNNY_ACCESS_KEY=...
```
