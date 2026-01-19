import os
import sys
import time

# Ajout du chemin des modules DaVinci pour macOS
RESOLVE_SCRIPT_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/"
if os.path.exists(RESOLVE_SCRIPT_API):
    sys.path.append(RESOLVE_SCRIPT_API)

# Configuration
EXPORT_PATH = "/Users/mathieucourchesne/exports_from_davinci"
RENDER_PRESET_NAME = "Pipeline Export" # Optional: if you have a preset
RENDER_FORMAT = "mp4"
RENDER_CODEC = "H264"

def get_resolve():
    try:
        import DaVinciResolveScript as bmd
        return bmd.scriptapp("Resolve")
    except ImportError:
        # Fallback for running outside of Resolve (e.g. testing)
        # This part assumes we are inside Resolve usually.
        return None

def main():
    resolve = get_resolve()
    if not resolve:
        print("Could not connect to DaVinci Resolve. Run this script from within Resolve.")
        return

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    
    if not project:
        print("No project is currently open.")
        return

    timeline = project.GetCurrentTimeline()
    if not timeline:
        print("No timeline is currently open.")
        return

    print(f"Exporting timeline: {timeline.GetName()}")

    # Determine Project Name
    project_name = project.GetName()
    timeline_name = timeline.GetName()
    
    # Use timeline name for the export folder/file to match auto_watch expectations
    # auto_watch expects: 
    # 1. file: Name.mp4
    # 2. folder: Name/video_master.mp4

    # We will use the folder approach to be safer with multiple renders
    target_folder = os.path.join(EXPORT_PATH, timeline_name)
    
    # Clean up target folder name (simple)
    target_folder = target_folder.strip()
    
    # Setup Render Settings
    project.SetRenderSettings({
        "TargetDir": target_folder,
        "CustomName": "video_master",
        "Format": RENDER_FORMAT,
        "VideoCodec": RENDER_CODEC,
        "ExportVideo": True,
        "ExportAudio": True,
    })
    
    # Add to Render Queue
    project.AddRenderJob()
    
    print(f"Added render job for '{timeline_name}' to '{target_folder}'")
    
    # Optional: Start Rendering immediately
    project.StartRendering() 
    print("Rendering started...")
    
    # Note: If you want to wait for render to complete, you need to poll IsRenderingInProgress()
    # while project.IsRenderingInProgress():
    #     time.sleep(1)
    # print("Rendering complete!")

if __name__ == "__main__":
    main()
