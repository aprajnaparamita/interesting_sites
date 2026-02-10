#!/usr/bin/env python3
import json
import os
import subprocess
import time

# Configuration
VIDEO_JSON_FILE = "videos.json"
OUTPUT_DIR = "tiktok_videos"
EXTRACTED_TEXT_DIR = "extracted_text"
EXTRACTION_PROGRESS_FILE = "extraction_progress.json"

# List of video IDs with missing audio
MISSING_AUDIO_IDS = [
    "7551106613814267167",
    "7551594453220248862",
    "7554122304159026462",
    "7555637603752480030",
    "7559005539485764894",
    "7566836700186545438",
    "7576396825993743647",
    "7599566303392763166",
    "7601744057492147486",
    "7603367646813277471",
    "7605224276228148511"
]

def load_videos(json_file):
    """Load video metadata from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return {v['id']: v['url'] for v in data['entries']}

def load_progress():
    """Load extraction progress tracking file."""
    if os.path.exists(EXTRACTION_PROGRESS_FILE):
        with open(EXTRACTION_PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"processed": []}

def save_progress(progress):
    """Save extraction progress tracking file."""
    with open(EXTRACTION_PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def download_video(url, output_dir):
    """Download a single video using yt-dlp."""
    try:
        # Use shell=True with the command string to match manual behavior
        # Force "best" format which usually implies video+audio
        cmd = f'yt-dlp --output "{output_dir}/%(id)s.%(ext)s" --write-info-json --force-overwrites -f "best" "{url}"'
        
        print(f"Downloading: {url}")
        print(f"Command: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Download successful")
            return True
        else:
            print(f"✗ Download failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error downloading video: {e}")
        return False

def main():
    print("Loading video URLs...")
    video_map = load_videos(VIDEO_JSON_FILE)
    
    print("Loading extraction progress...")
    progress = load_progress()
    
    processed_set = set(progress.get('processed', []))
    
    for video_id in MISSING_AUDIO_IDS:
        print(f"\nProcessing {video_id}...")
        
        if video_id not in video_map:
            print(f"⚠ Video ID {video_id} not found in {VIDEO_JSON_FILE}")
            continue
            
        url = video_map[video_id]
        
        # 1. Delete existing video file
        video_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
        if os.path.exists(video_path):
            print(f"Removing existing video: {video_path}")
            os.remove(video_path)
            
        # 2. Download video again
        if download_video(url, OUTPUT_DIR):
            # 3. Remove from extraction progress
            if video_id in processed_set:
                print(f"Removing {video_id} from extraction progress")
                processed_set.remove(video_id)
            else:
                print(f"{video_id} was not in processed set")
                
            # 4. Remove extracted text JSON
            json_path = os.path.join(EXTRACTED_TEXT_DIR, f"{video_id}.json")
            if os.path.exists(json_path):
                print(f"Removing extracted text: {json_path}")
                os.remove(json_path)
        else:
            print(f"⚠ Failed to download {video_id}, skipping cleanup")
            
    # Save updated progress
    progress['processed'] = list(processed_set)
    save_progress(progress)
    
    print("\nDone! You can now run 'python3 extract_text.py' to re-process these videos.")

if __name__ == "__main__":
    main()
