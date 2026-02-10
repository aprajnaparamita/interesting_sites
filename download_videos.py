#!/usr/bin/env python3
"""
Slowly download TikTok videos one at a time with progress tracking.
This script downloads videos with delays between each one to avoid rate limiting.
"""

import json
import subprocess
import time
import os
from datetime import datetime

# Configuration
VIDEO_JSON_FILE = "videos.json"  # Path to your videos.json file
OUTPUT_DIR = "tiktok_videos"  # Directory to save videos
DELAY_BETWEEN_DOWNLOADS = 30  # Seconds to wait between downloads (adjust as needed)
PROGRESS_FILE = "download_progress.json"  # Track which videos have been downloaded

def load_videos(json_file):
    """Load video metadata from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data['entries']

def load_progress():
    """Load progress tracking file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"downloaded": [], "failed": [], "last_index": -1}

def save_progress(progress):
    """Save progress tracking file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def download_video(url, output_dir):
    """Download a single video using yt-dlp."""
    try:
        cmd = [
            'yt-dlp',
            '--output', f'{output_dir}/%(id)s.%(ext)s',
            '--write-info-json',  # Also save metadata for each video
            url
        ]
        
        print(f"\n{'='*60}")
        print(f"Downloading: {url}")
        print(f"{'='*60}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load videos and progress
    print(f"Loading video list from {VIDEO_JSON_FILE}...")
    videos = load_videos(VIDEO_JSON_FILE)
    progress = load_progress()
    
    total_videos = len(videos)
    start_index = progress['last_index'] + 1
    
    print(f"\nTotal videos: {total_videos}")
    print(f"Already downloaded: {len(progress['downloaded'])}")
    print(f"Failed downloads: {len(progress['failed'])}")
    print(f"Starting from index: {start_index}")
    print(f"Remaining: {total_videos - start_index}")
    print(f"\nDelay between downloads: {DELAY_BETWEEN_DOWNLOADS} seconds")
    
    # Download videos one by one
    for i in range(start_index, total_videos):
        video = videos[i]
        video_id = video['id']
        video_url = video['url']
        
        # Skip if already downloaded
        if video_id in progress['downloaded']:
            print(f"\n[{i+1}/{total_videos}] Skipping {video_id} (already downloaded)")
            continue
        
        print(f"\n[{i+1}/{total_videos}] Processing video {video_id}")
        print(f"Title: {video.get('title', 'N/A')}")
        print(f"Duration: {video.get('duration', 'N/A')} seconds")
        print(f"Views: {video.get('view_count', 'N/A'):,}")
        
        # Download the video
        success = download_video(video_url, OUTPUT_DIR)
        
        # Update progress
        if success:
            progress['downloaded'].append(video_id)
        else:
            progress['failed'].append(video_id)
        
        progress['last_index'] = i
        save_progress(progress)
        
        # Wait before next download (except for the last one)
        if i < total_videos - 1:
            print(f"\nWaiting {DELAY_BETWEEN_DOWNLOADS} seconds before next download...")
            print(f"Progress: {len(progress['downloaded'])}/{total_videos} successful, "
                  f"{len(progress['failed'])} failed")
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
    
    # Final summary
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE!")
    print("="*60)
    print(f"Total videos: {total_videos}")
    print(f"Successfully downloaded: {len(progress['downloaded'])}")
    print(f"Failed: {len(progress['failed'])}")
    
    if progress['failed']:
        print("\nFailed video IDs:")
        for video_id in progress['failed']:
            print(f"  - {video_id}")
        print("\nYou can retry failed downloads by running this script again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user. Progress has been saved.")
        print("Run the script again to resume from where you left off.")
