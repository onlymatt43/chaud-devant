# Chaud Devant - Workflow Vidéo Automatisé 🚀

Ce projet est une "machine de guerre" qui automatise tout le cycle de vie d'une vidéo : de l'export DaVinci Resolve jusqu'à sa publication sur un site web, en passant par l'amélioration audio et l'encodage.

## ✨ Fonctionnalités

*   **Export DaVinci Automatique** : Script Python pour exporter la timeline active sans clic.
*   **Traitement Intelligent** :
    *   **Encodage** : Génération automatique des formats 16:9, 9:16 et 1:1.
    *   **Audio Pro** 🎚️ : Denoise (réduction de bruit), Enhance Speech (boost vocal) et Normalisation (-16 LUFS) automatiques.
    *   **Branding** : Ajout automatique d'une outro (si configuré).
*   **Hébergement Bunny.net** : Upload direct sur le CDN vidéo streaming.
*   **Déploiement Continu** 🚀 : Push automatique sur GitHub à la fin du traitement pour mettre à jour le site Vercel.
*   **Bonus "Beat Sync"** 🎵 : Un outil séparé pour caler des coupures vidéo sur le rythme d'une musique.

---

## 🛠️ Installation & Prérequis

1.  **Python & FFmpeg** : Assurez-vous d'avoir Python 3.10+ et FFmpeg installés (`brew install ffmpeg`).
2.  **Dépendances** :
    ```bash
    pip install -r requirements.txt
    pip install moviepy librosa soundfile openpyxl
    ```
3.  **Variables `.env`** :
    Créez un fichier `.env` avec vos accès Bunny.net :
    ```ini
    BUNNY_LIBRARY_ID=581630
    BUNNY_ACCESS_KEY=7b43d3...
    ```

---

## 🚦 Le Pipeline Principal

### 1. Export depuis DaVinci
Dans DaVinci Resolve : `Workspace > Scripts > Comp > davinci_export_pipeline`
*   Cela exporte la timeline courante dans `~/exports_from_davinci`.

### 2. Le Watchdog (`auto_watch.py`)
Ce script doit tourner en arrière-plan sur votre Mac. Il surveille le dossier d'export.
```bash
python3 auto_watch.py
```
Dès qu'un fichier arrive :
1.  Il le déplace dans `production/`.
2.  Il lance `process.py`.
3.  Il améliore le son, encode les vidéos, et upload sur Bunny.
4.  Il met à jour `showcase.json`.
5.  Il fait un `git push` pour mettre à jour le site web.

### 3. Le Site Web
Le fichier `index.html` est votre vitrine.
*   Design style "Macaron" / Badges ronds.
*   Thème clair animé.
*   Lecture directe MP4 optimisée.

---

## 🎵 Outil Bonus : Beat Sync

Pour créer des montages "glitch" qui changent de plan à chaque note de musique :

1.  Mettez votre vidéo (`.mp4`) et votre musique (`.mp3`) dans un même dossier.
2.  Copiez-y le fichier **`lanceur_beat_sync.command`**.
3.  Double-cliquez sur le lanceur.
4.  Le script génère `beat_synced_output.mp4` automatiquement.

---

## 🧹 Maintenance & Outils

*   **`regenerate_all.py`** : Relance le traitement (audio + vidéo) sur tous les dossiers existants dans `production/`.
*   **`fix_configs.py`** : Met à jour les fichiers de config de tous les projets avec les derniers réglages (audio, clés API).
*   **`sync_bunny_library.py`** : Compare votre dossier local avec Bunny.net et supprime les vidéos orphelines en ligne.
*   **`delete_video.py`** : Pour supprimer proprement un projet (local + remote).

---

## ⚙️ Configuration (`config.default.json`)

Vous pouvez ajuster les réglages par défaut ici :
```json
{
  "audio": {
    "enabled": true,
    "denoise": true,     // Réduction de bruit
    "enhance_speech": true, // EQ + Compression voix
    "normalize": true    // Standard web -16 LUFS
  },
  "formats": {
    "16x9": true,
    "9x16": true,
    "1x1": true
  }
}
```
