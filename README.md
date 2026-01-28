# Chaud Devant - Workflow Vidéo Automatisé 🚀

Ce projet est une "machine de guerre" qui automatise tout le cycle de vie d'une vidéo : de l'export DaVinci Resolve jusqu'à sa publication sur un site web, en passant par l'amélioration audio et l'encodage.

## ✨ Fonctionnalités

*   **Double Pipeline (Public / Privé)** : Gestion séparée des projets publics (portfolio) et privés (clients/perso).
*   **Export DaVinci Automatique** : Scripts Python dans Resolve pour exporter et relancer le watch en un clic.
*   **Traitement Intelligent** :
    *   **Encodage** : Génération automatique des formats 16:9, 9:16 et 1:1.
    *   **Audio Pro** 🎚️ : Denoise, Enhance Speech et Normalisation (-16 LUFS) automatiques.
    *   **Branding** : Ajout automatique d'une outro (si configuré).
*   **Hébergement Bunny.net** : Upload sur la bonne librairie (Public ou Privé) automatiquement.
*   **Déploiement Continu** 🚀 : Push automatique sur GitHub à la fin du traitement pour mettre à jour le site Vercel.
*   **Gestion des versions** : Si un projet existe déjà, il crée automatiquement une `_v2`, `_v3`, etc.

---

## 🛠️ Installation & Prérequis

1.  **Python & FFmpeg** : Assurez-vous d'avoir Python 3.10+ et FFmpeg installés (`brew install ffmpeg`).
2.  **Dépendances** :
    ```bash
    pip install -r requirements.txt
    ```
3.  **Variables `.env`** :
    Créez un fichier `.env` avec vos accès Bunny.net :
    ```ini
    BUNNY_LIBRARY_ID=123456
    BUNNY_ACCESS_KEY=abcd-1234...
    ```

---

## 🚦 Le Pipeline Principal

### 1. Le Watchdog (Démarrage)
Tout commence ici. Lancez ce script pour surveiller les dossiers d'export.
Double-cliquez sur **`start_watcher.command`** ou exécutez :
```bash
./start_watcher.command
```
Cela ouvre un terminal qui surveille :
*   `~/exports_from_davinci/new` (Public)
*   `~/exports_from_davinci/private` (Privé)

### 2. Export depuis DaVinci
Dans DaVinci Resolve : `Workspace > Scripts > Comp > ...`

*   **`Export_PUBLIC`** : Exporte la timeline vers le dossier public. Applique la config par défaut.
*   **`Export_PRIVATE`** : Exporte vers le dossier privé. Applique la config privée (pas publiée sur le site principal).

*Le script DaVinci redémarre automatiquement le Watchdog s'il était éteint.*

### 3. Traitement (`process.py`)
Dès qu'un fichier arrive :
1.  Il est déplacé dans `production/` (avec gestion de version si doublon).
2.  L'audio est nettoyé et normalisé.
3.  Les sous-titres sont générés (Whisper).
4.  Les formats vidéo sont encodés.
5.  Les fichiers sont envoyés sur **Bunny.net** (Librairie Public ou Privé selon la source).
6.  Le fichier `inventory` et le site web sont mis à jour (Git Push).

---

## 🎵 Outil Bonus : Beat Sync

Pour créer des montages "glitch" qui changent de plan à chaque note de musique :

1.  Mettez votre vidéo (`.mp4`) et votre musique (`.mp3`) dans un même dossier.
2.  Copiez-y le fichier **`lanceur_beat_sync.command`**.
3.  Double-cliquez sur le lanceur.
4.  Le script génère `beat_synced_output.mp4` automatiquement.

---

## 🧹 Maintenance & Outils

*   **`start_watcher.command`** : Le lanceur principal (à utiliser tout le temps).
*   **`regenerate_all.py`** : Relance le traitement sur tous les dossiers existants dans `production/`.
*   **`delete_video.py`** : Pour supprimer proprement un projet (local + remote).
*   **`logs/startup.log`** : Vérifiez ce fichier dans chaque projet si le traitement ne semble pas démarrer.

---

## ⚙️ Configuration

*   **`config.default.json`** : Configuration pour les exports **Publics**.
*   **`config.private.json`** : Configuration pour les exports **Privés** (Library ID différent, options différentes).

Vous pouvez ajuster les réglages (audio, formats) dans ces fichiers.
