#!/usr/bin/env python3
"""
Extract text from TikTok videos using:
1. Whisper for audio transcription
2. Tesseract OCR for text appearing in video frames
"""

import json
import os
import subprocess
import re
from pathlib import Path
from datetime import datetime
import cv2
import pytesseract
from PIL import Image
import whisper

# Configuration
VIDEO_DIR = "tiktok_videos"
OUTPUT_DIR = "extracted_text"
METADATA_FILE = "videos.json"
FRAME_INTERVAL = 2  # Extract frame every N seconds
PROGRESS_FILE = "extraction_progress.json"

# Whisper model size: 'tiny', 'base', 'small', 'medium', 'large'
# 'small' is a good balance - accurate but not too slow
WHISPER_MODEL = "small"

def setup():
    """Setup directories and load Whisper model."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Loading Whisper model (this may take a minute on first run)...")
    model = whisper.load_model(WHISPER_MODEL)
    return model

def load_video_metadata():
    """Load original video metadata."""
    with open(METADATA_FILE, 'r') as f:
        data = json.load(f)
    
    # Create lookup by video ID
    metadata = {}
    for video in data['entries']:
        metadata[video['id']] = video
    return metadata

def load_progress():
    """Load progress tracking."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"processed": []}

def save_progress(progress):
    """Save progress."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def has_audio_stream(video_path):
    """Check if video has an audio stream using ffprobe."""
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-select_streams', 'a', 
            '-show_entries', 'stream=index', 
            '-of', 'csv=p=0', 
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip()) > 0
    except Exception:
        return False

def transcribe_audio(video_path, model):
    """Transcribe audio using Whisper."""
    if not has_audio_stream(video_path):
        print(f"  ⚠ No audio stream found, skipping transcription")
        return ""

    print(f"  Transcribing audio...")
    try:
        result = model.transcribe(str(video_path))
        return result['text'].strip()
    except Exception as e:
        print(f"  ✗ Audio transcription failed: {e}")
        return ""

def extract_frames(video_path, interval=2):
    """Extract frames from video at specified intervals."""
    print(f"  Extracting frames (every {interval} seconds)...")
    frames = []
    
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval)
        
        frame_count = 0
        extracted_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frames.append(frame)
                extracted_count += 1
            
            frame_count += 1
        
        cap.release()
        print(f"  Extracted {extracted_count} frames")
        return frames
        
    except Exception as e:
        print(f"  ✗ Frame extraction failed: {e}")
        return []

def ocr_frame(frame):
    """Extract text from a single frame using OCR."""
    try:
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        # Perform OCR
        text = pytesseract.image_to_string(pil_image)
        return text.strip()
    except Exception as e:
        return ""

def frames_are_similar(frame1, frame2, threshold=30):
    """Check if two frames are similar using mean absolute difference."""
    if frame1 is None or frame2 is None:
        return False
    
    # Resize for faster comparison
    h, w = frame1.shape[:2]
    small_h, small_w = h // 4, w // 4
    f1_small = cv2.resize(frame1, (small_w, small_h))
    f2_small = cv2.resize(frame2, (small_w, small_h))
    
    # Convert to grayscale
    g1 = cv2.cvtColor(f1_small, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(f2_small, cv2.COLOR_BGR2GRAY)
    
    # Calculate difference
    diff = cv2.absdiff(g1, g2)
    mean_diff = cv2.mean(diff)[0]
    
    return mean_diff < threshold

def extract_text_from_frames(frames):
    """Extract text from all frames and combine, skipping similar frames."""
    print(f"  Running OCR on frames...")
    all_text = []
    last_processed_frame = None
    
    for i, frame in enumerate(frames):
        # Skip if similar to last processed frame
        if last_processed_frame is not None and frames_are_similar(frame, last_processed_frame):
            continue
            
        text = ocr_frame(frame)
        last_processed_frame = frame
        
        if text:
            all_text.append(text)
    
    # Combine and deduplicate
    # Remove exact duplicates in text list while preserving order
    unique_text = []
    seen = set()
    for t in all_text:
        if t not in seen:
            unique_text.append(t)
            seen.add(t)
            
    combined = "\n".join(unique_text)
    print(f"  Found text in {len(unique_text)} unique frames (from {len(frames)} total)")
    return combined

def extract_urls(text):
    """Extract URLs from text."""
    # Common URL patterns
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    
    # Also look for domain patterns (e.g., "example.com")
    domain_pattern = r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?\b'
    domains = re.findall(domain_pattern, text)
    
    # Clean and combine
    all_urls = set(urls)
    for domain in domains:
        if domain not in ['tiktok.com', 'youtube.com']:  # Filter out common platforms
            all_urls.add(domain)
    
    return list(all_urls)

def process_video(video_path, video_id, metadata, whisper_model):
    """Process a single video to extract all text."""
    print(f"\nProcessing {video_path.name}...")
    
    # Get original metadata
    video_meta = metadata.get(video_id, {})
    
    # Transcribe audio
    transcript = transcribe_audio(video_path, whisper_model)
    
    # Extract and OCR frames
    frames = extract_frames(video_path, FRAME_INTERVAL)
    ocr_text = extract_text_from_frames(frames)
    
    # Extract URLs from all text
    all_text = f"{transcript}\n{ocr_text}\n{video_meta.get('title', '')}\n{video_meta.get('description', '')}"
    urls = extract_urls(all_text)
    
    # Compile results
    result = {
        "video_id": video_id,
        "video_file": video_path.name,
        "original_url": video_meta.get('url', ''),
        "title": video_meta.get('title', ''),
        "description": video_meta.get('description', ''),
        "duration": video_meta.get('duration', 0),
        "view_count": video_meta.get('view_count', 0),
        "timestamp": video_meta.get('timestamp', 0),
        "audio_transcript": transcript,
        "ocr_text": ocr_text,
        "extracted_urls": urls,
        "processed_at": datetime.now().isoformat()
    }
    
    return result

def main():
    # Setup
    whisper_model = setup()
    metadata = load_video_metadata()
    progress = load_progress()
    
    # Find all video files
    video_dir = Path(VIDEO_DIR)
    video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.webm"))
    
    print(f"\nFound {len(video_files)} video files")
    print(f"Already processed: {len(progress['processed'])}")
    
    # Process each video
    all_results = []
    
    for i, video_path in enumerate(video_files):
        video_id = video_path.stem  # Filename without extension
        
        # Skip if already processed
        if video_id in progress['processed']:
            print(f"\n[{i+1}/{len(video_files)}] Skipping {video_id} (already processed)")
            # Load existing result
            result_file = Path(OUTPUT_DIR) / f"{video_id}.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    all_results.append(json.load(f))
            continue
        
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(video_files)}] {video_path.name}")
        print(f"{'='*60}")
        
        # Process video
        result = process_video(video_path, video_id, metadata, whisper_model)
        
        # Save individual result
        result_file = Path(OUTPUT_DIR) / f"{video_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        all_results.append(result)
        
        # Update progress
        progress['processed'].append(video_id)
        save_progress(progress)
        
        print(f"  ✓ Saved to {result_file}")
    
    # Save combined results
    combined_file = Path(OUTPUT_DIR) / "all_extracted_text.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"Processed {len(all_results)} videos")
    print(f"Results saved to {OUTPUT_DIR}/")
    print(f"Combined file: {combined_file}")
    
    # Summary statistics
    total_urls = sum(len(r['extracted_urls']) for r in all_results)
    print(f"\nTotal URLs found: {total_urls}")
    print(f"Average URLs per video: {total_urls/len(all_results):.1f}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted. Progress has been saved.")
        print("Run again to resume.")
