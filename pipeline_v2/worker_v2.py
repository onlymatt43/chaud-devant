import json
import subprocess
import requests
import logging
import pandas as pd
import shutil
import whisper
import warnings
from pathlib import Path
from datetime import datetime
import config

# Suppress Whisper warnings
warnings.filterwarnings("ignore")

# --- HELPERS ---

def write_subtitles(result, output_dir, file_stem):
    """Génère les fichiers SRT, VTT, TXT à partir du résultat Whisper."""
    # VTT
    vtt_path = output_dir / "captions" / f"{file_stem}.vtt"
    vtt_path.parent.mkdir(parents=True, exist_ok=True)
    
    def format_timestamp(seconds):
        ms = int((seconds % 1) * 1000)
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    # VTT Writer
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for segment in result["segments"]:
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip()
            f.write(f"{start} --> {end}\n{text}\n\n")
    
    # SRT Writer
    srt_path = output_dir / "captions" / f"{file_stem}.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(result["segments"], 1):
            start = format_timestamp(segment["start"]).replace('.', ',')
            end = format_timestamp(segment["end"]).replace('.', ',')
            text = segment["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    # TXT Writer
    txt_path = output_dir / "captions" / f"{file_stem}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(result["text"])
        
    return vtt_path, srt_path, txt_path

def process_audio_track(work_dir, video_path):
    """
    1. Extract Audio
    2. Denoise (afftdn)
    3. Normalize (loudnorm -16 LUFS)
    """
    raw_audio = work_dir / "raw_audio.wav"
    clean_audio = work_dir / "clean_audio.wav"
    
    # Export WAV
    cmd_extract = [
        config.FFMPEG, "-y", "-i", str(video_path), 
        "-vn", "-acodec", "pcm_s16le", "-ar", "48000", str(raw_audio)
    ]
    if not run_cmd(cmd_extract): return None

    # Process: Denoise + Normalize
    # afftdn: FFT based denoiser
    # loudnorm: EBU R128 normalization
    cmd_process = [
        config.FFMPEG, "-y", "-i", str(raw_audio),
        "-af", "afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le", "-ar", "48000", str(clean_audio)
    ]
    
    if run_cmd(cmd_process) and clean_audio.exists():
        return clean_audio
    return None

def update_inventory_excel(project_data):
    """Met à jour un fichier Excel global à la racine pour le suivi humain."""
    excel_path = config.BASE_DIR / "INVENTORY.xlsx"
    
    # Données à plat pour l'Excel
    flat_data = {
        "ID Projet": project_data["id"],
        "Date (UTC)": project_data["updated_at"],
        "Type": "Privé" if project_data["is_private"] else "Public",
        "Format": ", ".join(project_data["bunny_urls"].keys()),
        "Lien Bunny": next(iter(project_data["bunny_urls"].values()), "") # Premier lien dispo
    }
    
    df_new = pd.DataFrame([flat_data])
    
    if excel_path.exists():
        try:
            df_old = pd.read_excel(excel_path)
            # On supprime l'ancienne ligne de ce projet si elle existe
            df_old = df_old[df_old["ID Projet"] != project_data["id"]]
            # On ajoute la nouvelle en haut
            df_final = pd.concat([df_new, df_old], ignore_index=True)
        except Exception as e:
            logging.warning(f"   ⚠️ Excel read error ({e}), creating new.")
            df_final = df_new
    else:
        df_final = df_new
        
    try:
        df_final.to_excel(excel_path, index=False)
        logging.info("   📊 Inventory Excel updated.")
    except Exception as e:
        logging.error(f"   ❌ Inventory Excel update failed: {e}")

def run_cmd(cmd_list):
    """Exécute une commande système de manière sécurisée."""
    cmd_str = " ".join([str(x) for x in cmd_list])
    logging.info(f"   RUN: {cmd_str}")
    try:
        subprocess.run(cmd_list, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"   ❌ CMD ERROR: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        logging.error(f"   ❌ TOOL MISSING: {cmd_list[0]}")
        return False

def update_db(project_data):
    """Met à jour le fichier JSON global pour Vercel."""
    db_path = config.DB_FILE
    data = []
    if db_path.exists():
        try:
            data = json.loads(db_path.read_text())
        except:
            data = []
    
    # Upsert : On supprime l'ancien si existe, on met le nouveau en haut
    data = [d for d in data if d["id"] != project_data["id"]]
    data.insert(0, project_data)
    
    db_path.write_text(json.dumps(data, indent=2))
    logging.info(f"   💾 Database updated ({len(data)} items)")

# --- CORE ---

def bunny_get_or_create(title, api_key, lib_id):
    """Cherche une vidéo par titre, ou la crée si elle n'existe pas. Retourne l'GUID."""
    headers = {"AccessKey": api_key, "Content-Type": "application/json"}
    
    # 1. Search
    try:
        url = f"https://video.bunnycdn.com/library/{lib_id}/videos?search={title}"
        resp = requests.get(url, headers=headers)
        if resp.ok:
            for item in resp.json().get("items", []):
                if item["title"] == title:
                    logging.info(f"   🐰 Found existing video: {item['guid']}")
                    return item["guid"]
    except Exception as e:
        logging.warning(f"   ⚠️ Bunny search fail: {e}")

    # 2. Create
    try:
        url = f"https://video.bunnycdn.com/library/{lib_id}/videos"
        resp = requests.post(url, headers=headers, json={"title": title})
        if resp.ok:
            guid = resp.json()["guid"]
            logging.info(f"   🐰 Created new video: {guid}")
            return guid
    except Exception as e:
        logging.error(f"   ❌ Bunny create fail: {e}")
        return None
    return None

def process_video(project_id, prod_dir, video_path, is_private):
    """Pipeline complet V3: Audio Clean -> AI Subs -> Remux -> Upload."""
    
    # Config adaptée (Public vs Private)
    API_KEY = config.API_KEY_PRIVATE if is_private else config.API_KEY_PUBLIC
    LIB_ID = config.LIB_PRIVATE if is_private else config.LIB_PUBLIC
    PULL_ZONE = config.PULL_ZONE_PRIVATE if is_private else config.PULL_ZONE_PUBLIC
    
    # Dossiers de sortie
    out_dir = prod_dir / "output"
    formats_dir = out_dir / "formats"
    captions_dir = out_dir / "captions"
    tmp_dir = prod_dir / "temp"
    
    formats_dir.mkdir(parents=True, exist_ok=True)
    captions_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    result_data = {
        "id": project_id,
        "is_private": is_private,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "bunny_urls": {},
        "pipeline_steps": []
    }

    # 1. AUDIO PROCESSING (DSP)
    # -------------------------
    logging.info(f"   🔊 Processing Audio (Denoise + Norm)...")
    clean_audio_path = process_audio_track(tmp_dir, video_path)
    if not clean_audio_path:
        logging.warning("   ⚠️ Audio processing failed. Using original audio.")
        audio_source_arg = ["-c:a", "aac", "-b:a", "192k"]
        whisper_source = video_path # Fallback for whisper
    else:
        # On utilisera cet audio pour le mix final
        audio_source_arg = ["-i", str(clean_audio_path), "-c:a", "aac", "-b:a", "192k", "-map", "0:v", "-map", "1:a"]
        whisper_source = clean_audio_path
        logging.info("   ✅ Audio Optimized (-16 LUFS)")

    # 2. AI SUBTITLES (Whisper)
    # -------------------------
    logging.info(f"   🧠 Generating Subtitles (Whisper)...")
    try:
        model = whisper.load_model("base") # "base" est un bon compromis vitesse/précision
        result = model.transcribe(str(whisper_source))
        write_subtitles(result, out_dir, "video_optimized")
        logging.info("   ✅ Subtitles Generated (SRT/VTT/TXT)")
    except Exception as e:
        logging.error(f"   ❌ Whisper failed: {e}")

    # 3. VIDEO ANALYSIS & ENCODING
    # ----------------------------
    detected_format = "16x9"
    try:
        res = subprocess.run([
            config.FFPROBE, "-v", "error", "-select_streams", "v:0", 
            "-show_entries", "stream=width,height", "-of", "json", str(video_path)
        ], capture_output=True, text=True)
        meta = json.loads(res.stdout)["streams"][0]
        w, h = int(meta["width"]), int(meta["height"])
        ratio = w / h
        
        if 0.9 <= ratio <= 1.1: detected_format = "1x1"
        elif ratio < 0.9:       detected_format = "9x16"
        else:                   detected_format = "16x9"
        
        logging.info(f"   📐 Ratio {ratio:.2f} -> Mode: {detected_format}")
    except Exception as e:
        logging.error(f"   ⚠️ Analysis failed ({e}), defaulting to 16x9")

    target_file = formats_dir / f"{detected_format}.mp4"
    
    # Paramètres de scale avec "pad" pour s'assurer d'avoir des dimensions paires (requis pour H264)
    scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" 
    if detected_format == "9x16":
        scale_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    elif detected_format == "1x1":
        scale_filter = "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2"

    # Construction de la commande finale (Video Source + Clean Audio Source)
    # Note: audio_source_arg gère le mapping
    cmd_encode = [
        config.FFMPEG, "-y", "-i", str(video_path)
    ]
    
    if clean_audio_path:
        # input 0 is video, input 1 is audio. map 0:v, map 1:a
        cmd_encode.extend(["-i", str(clean_audio_path), "-map", "0:v", "-map", "1:a"])
    else:
        # input 0 only. use default audio
        pass 

    cmd_encode.extend([
        "-vf", f"{scale_filter},setsar=1",
        "-c:v", "libx264", "-b:v", "8M", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(target_file)
    ])
    
    logging.info(f"   ⚙️ Encoding Final Master...")
    if not run_cmd(cmd_encode):
        return False

    # 4. UPLOAD BUNNY STREAM
    # ----------------------
    import re
    clean_title = re.sub(r'_v\d+$', '', project_id)
    bunny_title = f"{clean_title} ({detected_format})"
    
    guid = bunny_get_or_create(bunny_title, API_KEY, LIB_ID)
    if guid:
        try:
            url = f"https://video.bunnycdn.com/library/{LIB_ID}/videos/{guid}"
            headers = {
                "AccessKey": API_KEY,
                "Content-Type": "application/octet-stream" # FIX CRITIQUE V2
            }
            with open(target_file, "rb") as f:
                logging.info(f"   ☁️ Uploading to Bunny ({detected_format})...")
                u_resp = requests.put(url, headers=headers, data=f)
                
            if u_resp.ok:
                final_url = f"{PULL_ZONE}/{guid}/play_720p.mp4"
                result_data["bunny_urls"][detected_format] = final_url
                logging.info(f"   ✅ Published: {final_url}")
            else:
                logging.error(f"   ❌ Upload failed: {u_resp.status_code} - {u_resp.text}")
                return False 
        except Exception as e:
            logging.error(f"   ❌ Upload network error: {e}")
            return False

    # 5. CLEANUP & FINISH
    # -------------------
    try:
        shutil.rmtree(tmp_dir) # On vire les wav temporaires
    except: pass

    # Status marker
    with open(prod_dir / "status.json", "w") as f:
        json.dump(result_data, f, indent=2)

    # Global Updates
    if result_data["bunny_urls"]:
        update_db(result_data)
        update_inventory_excel(result_data)
        return True
    
    return False
