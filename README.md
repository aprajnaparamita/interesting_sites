# TikTok Website Extractor - Complete Guide

This project downloads TikTok videos, extracts text from audio and video, and uses AI to create an organized index of websites.

I made this as a repository for my own reference and intend to try every tool and make a report on it. See the final index [here](website_index.md).

## Installation

### 1. Install System Dependencies

**macOS:**
```bash
brew install tesseract ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr ffmpeg
```

**Windows:**
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Install ffmpeg: https://ffmpeg.org/download.html

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up API Key

Get your Anthropic API key from https://console.anthropic.com/

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## Usage - Complete Workflow

### Step 1: Get Video List (Already Done!)
```bash
yt-dlp --flat-playlist --dump-single-json https://www.tiktok.com/@username > videos.json
```

### Step 2: Download Videos
```bash
python3 download_videos.py
```

This will:
- Download all 93 videos slowly (30 second delays)
- Save to `tiktok_videos/` directory
- Track progress in case of interruption
- Take ~45-60 minutes total

### Step 3: Extract Text from Videos
```bash
python3 extract_text.py
```

This will:
- Transcribe audio using Whisper AI
- Extract text from video frames using OCR
- Find URLs in both sources
- Save results to `extracted_text/` directory
- Take ~2-5 minutes per video (~3-8 hours total for 93 videos)

**Note:** This is the slowest step. Consider:
- Running overnight
- Using a cloud GPU instance (RunPod/Vast.ai) to speed up
- Using smaller Whisper model ('tiny' or 'base') for faster processing

### Step 4: Create Website Index with AI
```bash
python3 create_index.py
```

This will:
- Analyze all extracted text with Claude AI
- Identify websites and descriptions
- Categorize everything
- Create both JSON and Markdown outputs
- Take ~5-15 minutes (depends on API speed)

**Output files:**
- `website_index.json` - Complete structured data
- `website_index.md` - Human-readable version

## File Structure

```
your-project/
├── videos.json                      # Video metadata from TikTok
├── download_videos.py               # Step 2 script
├── extract_text.py                  # Step 3 script
├── create_index.py                  # Step 4 script
├── requirements.txt                 # Python dependencies
├── tiktok_videos/                   # Downloaded videos
│   ├── 7605224276228148511.mp4
│   └── ...
├── extracted_text/                  # Extracted text data
│   ├── all_extracted_text.json      # Combined results
│   ├── 7605224276228148511.json     # Individual results
│   └── ...
└── website_index.json               # Final output!
```

## Tips & Troubleshooting

### Speed Up Processing
- Use a smaller Whisper model in `extract_text.py`:
  - Change `WHISPER_MODEL = "tiny"` (fastest, less accurate)
  - Default is `"small"` (balanced)
  - Or `"medium"` (slower, more accurate)

### If Script Gets Interrupted
All scripts save progress automatically. Just run them again and they'll resume where they left off.

### Check Progress
Each script creates a progress file:
- `download_progress.json`
- `extraction_progress.json`

### Reduce API Costs
The Claude API calls cost approximately $0.01-0.03 per video. For 93 videos, expect $1-3 total.

### OCR Not Working Well?
Adjust `FRAME_INTERVAL` in `extract_text.py`:
- Lower number = more frames = better capture but slower
- Current: 2 seconds (good default)
- Try: 1 second for dense text videos

## Expected Results

From 93 videos with ~3 websites each:
- **~280 total websites** (with duplicates)
- **~200-250 unique websites** (after deduplication)
- **15-25 categories** (e.g., Productivity, Learning, AI Tools, Design, etc.)

## Cost Estimates

- **Compute:** Free if running locally, or $3-10 for cloud GPU
- **API calls:** ~$1-3 for Claude API
- **Time:** 4-9 hours total (mostly automated)

## Next Steps After Creating Index

1. Browse `website_index.md` in any text editor
2. Import `website_index.json` into a database
3. Create a searchable web interface
4. Share on GitHub or a blog post!
