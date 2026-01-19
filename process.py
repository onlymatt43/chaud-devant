#!/usr/bin/env python3
import json, subprocess, datetime, time, requests, os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv() # Charge les variables de .env

def load_json(p, d): return json.loads(p.read_text()) if p.exists() else d
def save_json(p, d): p.write_text(json.dumps(d, indent=2, ensure_ascii=False))

def log_event(f, p):
    p["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    with f.open("a") as fh: fh.write(json.dumps(p) + "\n")

def bunny_upload(file_path, bunny_cfg, log):
    if not bunny_cfg: return None
    try:
        filename = file_path.name
        # structure: https://{region}.storage.bunnycdn.com/{storage_zone}/{path}/{filename}
        region_prefix = f"{bunny_cfg['region']}." if bunny_cfg.get('region') and bunny_cfg['region'] != 'de' else ""
        url = f"https://{region_prefix}storage.bunnycdn.com/{bunny_cfg['storage_zone']}/{bunny_cfg.get('path', '')}/{filename}"
        
        with open(file_path, "rb") as f:
            t = time.time()
            resp = requests.put(url, data=f, headers={
                "AccessKey": bunny_cfg["access_key"],
                "Content-Type": "application/octet-stream"
            }, timeout=300)
            resp.raise_for_status()
            
            dur = round(time.time() - t, 2)
            log_event(log, {"step": "bunny_upload", "file": filename, "status": "ok", "dur": dur})
            
            # Construct public URL
            base_url = bunny_cfg.get("pull_zone_url", "").rstrip("/")
            path = bunny_cfg.get("path", "").strip("/")
            full_path = f"{path}/{filename}" if path else filename
            return f"{base_url}/{full_path}"
    except Exception as e:
        log_event(log, {"step": "bunny_upload", "file": file_path.name, "status": "fail", "err": str(e)})
        return None

def bunny_stream_upload(file_path, stream_cfg, log, title=None):
    if not stream_cfg: return None
    try:
        headers = {"AccessKey": stream_cfg["access_key"], "Content-Type": "application/json"}
        # 1. Créer l'entrée vidéo (Utilise le titre du projet si fourni)
        video_title = title if title else file_path.name
        create_url = f"https://video.bunnycdn.com/library/{stream_cfg['library_id']}/videos"
        resp = requests.post(create_url, headers=headers, json={"title": video_title})
        video_id = resp.json()["guid"]

        # 2. Upload du fichier
        upload_url = f"https://video.bunnycdn.com/library/{stream_cfg['library_id']}/videos/{video_id}"
        with open(file_path, "rb") as f:
            t = time.time()
            requests.put(upload_url, headers={"AccessKey": stream_cfg["access_key"]}, data=f)
            dur = round(time.time() - t, 2)
            log_event(log, {"step": "bunny_stream", "video_id": video_id, "status": "ok", "dur": dur})

        # Retourne l'URL direct MP4 si possible, sinon Embed
        # NOTE: Nécessite que l'option "MP4 Fallback" soit activée dans Bunny Stream
        # URL Format: https://{pull_zone_url}/{video_id}/play_720p.mp4
        
        pull_zone = stream_cfg.get("pull_zone_url", "https://vz-INVALID.b-cdn.net")
        # On enlève le slash de fin s'il existe
        if pull_zone.endswith("/"): pull_zone = pull_zone[:-1]
        
        return f"{pull_zone}/{video_id}/play_720p.mp4"
    except Exception as e:
        log_event(log, {"step": "bunny_stream", "file": file_path.name, "status": "fail", "err": str(e)})
        return None

def run(cmd, log, step, retries=0, backoff=[5,30,120]):
    a=0
    while True:
        try:
            t=time.time()
            subprocess.run(cmd, check=True)
            log_event(log, {"step":step,"status":"ok","cmd":" ".join(cmd),"dur":round(time.time()-t,2)})
            return True
        except subprocess.CalledProcessError as e:
            log_event(log, {"step":step,"status":"fail","cmd":" ".join(cmd),"err":str(e),"attempt":a+1})
            if a>=retries: return False
            time.sleep(backoff[min(a,len(backoff)-1)])
            a+=1

def update_global_showcase(new_inv, root_path):
    showcase_path = root_path / "showcase.json"
    showcase = load_json(showcase_path, [])
    # Remove existing entry with same ID and add new one at the top
    showcase = [item for item in showcase if item.get("id") != new_inv["id"]]
    showcase.insert(0, new_inv)
    save_json(showcase_path, showcase)

def process(folder):
    f=Path(folder)
    cfg=load_json(f/"config.json",{})
    st=load_json(f/"status.json",{})

    # Injection des secrets depuis l'environnement
    bunny_stream_cfg = cfg.get("bunny_stream", {})
    if os.getenv("BUNNY_LIBRARY_ID"):
        bunny_stream_cfg["library_id"] = os.getenv("BUNNY_LIBRARY_ID")
    if os.getenv("BUNNY_ACCESS_KEY"):
        bunny_stream_cfg["access_key"] = os.getenv("BUNNY_ACCESS_KEY")
    if bunny_stream_cfg: cfg["bunny_stream"] = bunny_stream_cfg

    (f/"logs").mkdir(exist_ok=True)
    out=f/"output"; out.mkdir(exist_ok=True)
    (out/"captions").mkdir(exist_ok=True)
    (out/"formats").mkdir(exist_ok=True)
    (out/"inventory").mkdir(exist_ok=True)
    log=f/"logs"/"pipeline.log"
    
    # Recherche automatique du fichier master (Premier fichier mp4 ou mov trouvé)
    # On cherche le fichier master (souvent video_master.mp4 venant de DaVinci)
    candidates = list(f.glob("*.mp4")) + list(f.glob("*.mov"))
    # On trie pour être déterministe
    candidates.sort()
    
    master = candidates[0] if candidates else None
    
    if not master:
        log_event(log, {"step": "init", "status": "fail", "err": "Aucun fichier master (.mp4 ou .mov) trouvé"})
        return

    # --- AUDIO OPTIMIZATION ---
    # Si activé, on génère un 'video_optimized.mp4' qui devient le master pour la suite
    if cfg.get("audio", {}).get("enabled"):
        optimized_master = out / "video_optimized.mp4"
        # On refait si pas fait OU si le master a changé (pas implémenté ici pour simplicité status check)
        if st.get("audio") != "done" or not optimized_master.exists():
            filters = []
            if cfg["audio"].get("denoise"):
                filters.append("afftdn=nf=-25") # Noise reduction (FFT)
            if cfg["audio"].get("enhance_speech"):
                filters.append("highpass=f=80") # Remove low frequency rumble
                filters.append("acompressor=threshold=-12dB:ratio=2:attack=5:release=50") # Gentle Compression
            if cfg["audio"].get("normalize"):
                filters.append("loudnorm=I=-16:TP=-1.5:LRA=11") # Web Standard Normalization
            
            af_string = ",".join(filters) if filters else "anull"

            ok = run([
                "ffmpeg", "-y", "-i", str(master),
                "-c:v", "copy", # On ne touche pas à l'image ici pour aller vite
                "-af", af_string,
                str(optimized_master)
            ], log, "audio_optimization")
            
            if ok:
                st["audio"] = "done"
                master = optimized_master # Le reste du script utilisera cette version
                save_json(f/"status.json", st)
            else:
                st["audio"] = "fail"
                log_event(log, {"step": "audio", "status": "warning", "err": "Audio optimization failed, using original"})
        else:
            # Si déjà fait, on utilise le fichier optimisé
            if optimized_master.exists():
                master = optimized_master
    # --------------------------
        
    branded=out/"video_branded.mp4"

    if cfg.get("captions",{}).get("enabled"):
        st.setdefault("captions",{})
        for l in cfg.get("languages",[]):
            if st["captions"].get(l)=="done": continue
            ok=run(["whisper",str(master),"--language","French","--output_dir",str(out/"captions")],log,f"captions_{l}")
            st["captions"][l]="done" if ok else "warning"

    if cfg.get("branding",{}).get("enabled"):
        if st.get("branding")!="done":
            outro=Path(cfg["branding"]["outro"])
            if not outro.exists():
                log_event(log, {"step":"branding","status":"warning","err":"Fichier outro manquant, branding annulé"})
                st["branding"]="missing_outro"
            else:
                ok=run([
                    "ffmpeg","-y","-i",str(master),"-i",str(outro),
                    "-filter_complex","[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1",
                    "-c:v","h264_videotoolbox",
                    "-b:v","20M",
                    str(branded)
                ],log,"branding")
                st["branding"]="done" if ok else "warning"
    else:
        st["branding"]="skipped"

    src=branded if branded.exists() else master
    st.setdefault("formats",{})
    st.setdefault("bunny_urls",{})
    scales={"16x9":"1920:1080","9x16":"1080:1920","1x1":"1080:1080"}
    for k,v in cfg.get("formats",{}).items():
        if not v: st["formats"][k]="skipped"; continue
        if st["formats"].get(k)=="done": continue
        
        output_file = out/"formats"/f"web_{k}.mp4"
        
        # Smart scaling: Fit within box + Pad with black bars (No distortion)
        # scale=w:h:force_original_aspect_ratio=decrease
        # pad=w:h:(ow-iw)/2:(oh-ih)/2
        w, h = scales[k].split(":")
        vf_filter = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        
        ok=run([
            "ffmpeg","-y","-i",str(src),
            "-vf",vf_filter,
            "-c:v","h264_videotoolbox",
            "-b:v","12M",
            "-profile:v","high",
            str(output_file)
        ],log,f"format_{k}")
        
        if ok:
            st["formats"][k]="done"
            # Priorité au Stream si configuré, sinon Storage classique
            if cfg.get("bunny_stream"):
                # On passe l'ID du projet comme titre pour Bunny
                title = f"{cfg.get('id', 'video')} ({k})"
                url = bunny_stream_upload(output_file, cfg["bunny_stream"], log, title=title)
                if url: st["bunny_urls"][k] = url
            elif cfg.get("bunny"):
                url = bunny_upload(output_file, cfg["bunny"], log)
                if url: st["bunny_urls"][k] = url
        else:
            st["formats"][k]="warning"

    inv={
        "id":cfg.get("id"),
        "captions":[k for k,v in st.get("captions",{}).items() if v=="done"],
        "formats_generated":[k for k,v in st.get("formats",{}).items() if v=="done"],
        "bunny_urls": st.get("bunny_urls", {}),
        "updated_at":datetime.datetime.utcnow().isoformat()+"Z"
    }
    save_json(out/"inventory"/"inventory.json",inv)
    pd.DataFrame([inv]).to_csv(out/"inventory"/"inventory.csv",index=False)
    try:
        pd.DataFrame([inv]).to_excel(out/"inventory"/"inventory.xlsx",index=False)
    except Exception as e:
        # Ce n'est pas grave si l'Excel échoue, on continue
        print(f"⚠️ Pas d'export Excel : {e}")

    st["last_update"]=inv["updated_at"]
    save_json(f/"status.json",st)
    
    # Update central showcase
    update_global_showcase(inv, Path(__file__).parent)

    if st.get("bunny_urls"):
        print("\n--- Bunny.net URLs ---")
        for k, url in st["bunny_urls"].items():
            print(f"{k}: {url}")

if __name__=="__main__":
    import sys
    process(sys.argv[1])
