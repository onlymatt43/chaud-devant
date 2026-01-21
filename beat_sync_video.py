#!/usr/bin/env python3
import sys
import os
import random
import librosa
import numpy as np
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

def main():
    video_path = None
    audio_path = None
    output_path = "beat_synced_output.mp4"
    min_seg = 0.0
    max_jump = 60.0

    if len(sys.argv) < 3:
        print("🕵️‍♂️ Mode Auto-détection (aucun argument fourni)...")
        files = os.listdir(".")
        # Exclure les fichiers de sortie potentiels pour ne pas se mordre la queue
        videos = [f for f in files if f.lower().endswith(('.mp4', '.mov', '.avi')) and "beat_synced" not in f]
        audios = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.m4a'))]

        if not videos:
            print("❌ Erreur: Aucune vidéo (.mp4, .mov) trouvée dans ce dossier.")
            return
        if not audios:
            print("❌ Erreur: Aucun fichier audio (.mp3, .wav) trouvé dans ce dossier.")
            return
            
        video_path = videos[0]
        audio_path = audios[0]
        
        print(f"   🎥 Vidéo trouvée : {video_path}")
        print(f"   🎵 Audio trouvé  : {audio_path}")
        print("   (Pour choisir d'autres fichiers, lancez la commande avec les noms : python3 script.py video.mp4 audio.mp3)")
        
    else:
        video_path = sys.argv[1]
        audio_path = sys.argv[2]
        if len(sys.argv) > 3: output_path = sys.argv[3]
        if len(sys.argv) > 4: min_seg = float(sys.argv[4])
        if len(sys.argv) > 5: max_jump = float(sys.argv[5])

    print(f"🎬 Chargement de la vidéo : {video_path}")
    try:
        video = VideoFileClip(video_path)
    except Exception as e:
        print(f"Erreur chargement vidéo : {e}")
        return

    print(f"🎵 Analyse du rythme de : {audio_path}")
    try:
        # Load audio for analysis
        y, sr = librosa.load(audio_path)
        # Detect onsets (attacks/notes)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # Load audio for editing (MoviePy)
        audio = AudioFileClip(audio_path)
    except Exception as e:
        print(f"Erreur chargement audio : {e}")
        return

    print(f"⏱️  Notes détectées : {len(onset_times)}")
    
    clips = []
    
    # On veut parcourir la vidéo source plus ou moins en entier pdt la chanson
    # Ratio d'accélération moyen nécessaire
    # Si video=100s, audio=10s, ratio=10.
    ratio = video.duration / audio.duration
    
    current_video_time = 0.0
    
    # On ajoute la fin de la chanson comme dernier point
    beat_times = list(onset_times)
    if beat_times[-1] < audio.duration:
        beat_times.append(audio.duration)
        
    start_time = 0.0
    
    for i, end_time in enumerate(beat_times):
        duration = end_time - start_time
        
        # Si le segment est trop court, on le saute (ou on l'accumule) pour éviter l'épilepsie
        if duration < min_seg and i < len(beat_times)-1:
            continue
            
        # Calcul du point de départ dans la vidéo
        # Option A : Avancée proportionnelle (Time Stretch logique)
        # Option B : Avancée aléatoire (Glitch/Saccadé pur)
        # Option C : Avancée séquentielle avec sauts (Saccadé narratif) valis par 'max_jump'
        
        # Ici on fait Option C : On avance dans la vidéo d'une quantité proportionnelle + bruit
        step = duration * ratio
        
        # On définit le segment vidéo
        vid_start = current_video_time
        vid_end = vid_start + duration
        
        # Sécurité fin de vidéo
        if vid_end >= video.duration:
            # Loopback au début si on dépasse
            current_video_time = 0.0
            vid_start = 0.0
            vid_end = duration
        
        sub = video.subclipped(vid_start, vid_end)
        clips.append(sub)
        
        # Sauté Saccadé : On déplace le curseur vidéo pour le prochain clip
        # On saute un peu plus loin que juste la fin du clip actuel
        jump = step * random.uniform(0.8, 1.2) # Variation de rythme
        current_video_time += jump
        
        # Update pour prochaine boucle
        start_time = end_time

    print(f"✂️  Assemblage de {len(clips)} segments...")
    final_clip = concatenate_videoclips(clips, method="compose") # 'compose' supporte mix codecs
    
    # Mettre l'audio original
    final_clip = final_clip.with_audio(audio)
    
    # Trim final si dépassement (arrondi)
    if final_clip.duration > audio.duration:
        final_clip = final_clip.subclipped(0, audio.duration)
        
    print(f"💾 Export vers : {output_path}")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    print("✅ Terminé !")

if __name__ == "__main__":
    main()
