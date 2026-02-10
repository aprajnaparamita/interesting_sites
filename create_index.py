#!/usr/bin/env python3
"""
Use Claude API to analyze extracted text and create an organized index of websites.
"""

import json
import os
from pathlib import Path
from anthropic import Anthropic

# Configuration
EXTRACTED_TEXT_FILE = "extracted_text/all_extracted_text.json"
OUTPUT_FILE = "website_index.json"

# Load environment variables from .env if present
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value.strip("'").strip('"')

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # Set this in your environment

# Initialize Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

ANALYSIS_PROMPT = """You are analyzing TikTok videos that feature interesting websites. For each video, I'll provide:
- The audio transcript
- Text extracted from the video (OCR)
- The video title/description
- Any URLs that were automatically detected

Your task:
1. Identify ALL websites mentioned or shown in the video (even if not in the detected URLs)
2. For each website, provide:
   - The website URL/name
   - A concise 1-2 sentence description of what the site does
   - A category (e.g., "Productivity", "Learning", "Design", "AI Tools", "Fun", "Research", etc.)

Return your analysis as a JSON object with this structure:
{{
  "websites": [
    {{
      "url": "example.com",
      "name": "Example Site",
      "description": "Brief description of what it does",
      "category": "Productivity"
    }}
  ],
  "confidence": "high" | "medium" | "low"
}}

If you can't identify any websites clearly, return an empty websites array.

Here's the video data:

TITLE: {title}
DESCRIPTION: {description}
DETECTED URLs: {urls}

AUDIO TRANSCRIPT:
{transcript}

OCR TEXT FROM VIDEO:
{ocr_text}
"""

def analyze_video_with_ai(video_data):
    """Use Claude to analyze a single video and extract website information."""
    
    # Prepare the prompt
    prompt = ANALYSIS_PROMPT.format(
        title=video_data.get('title', 'N/A'),
        description=video_data.get('description', 'N/A'),
        urls=', '.join(video_data.get('extracted_urls', [])) or 'None detected',
        transcript=video_data.get('audio_transcript', 'N/A'),
        ocr_text=video_data.get('ocr_text', 'N/A')[:2000]  # Limit OCR text length
    )
    
    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse response
        response_text = message.content[0].text
        
        # Extract JSON from response (Claude might wrap it in markdown)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        print(f"    ✗ AI analysis failed: {e}")
        return {"websites": [], "confidence": "error"}

def create_website_index(extracted_data):
    """Process all videos and create organized website index."""
    
    print(f"\nAnalyzing {len(extracted_data)} videos with Claude AI...")
    print("This may take a few minutes...\n")
    
    all_websites = []
    videos_with_websites = 0
    
    for i, video in enumerate(extracted_data):
        video_id = video.get('video_id', 'unknown')
        print(f"[{i+1}/{len(extracted_data)}] Analyzing video {video_id}...")
        
        # Analyze with AI
        analysis = analyze_video_with_ai(video)
        
        # Process results
        websites = analysis.get('websites', [])
        if websites:
            videos_with_websites += 1
            print(f"    ✓ Found {len(websites)} website(s)")
            
            # Add source video info to each website
            for site in websites:
                site['source_video'] = {
                    'video_id': video_id,
                    'title': video.get('title', ''),
                    'url': video.get('original_url', ''),
                    'views': video.get('view_count', 0)
                }
                all_websites.append(site)
        else:
            print(f"    - No websites found")
    
    print(f"\n{'='*60}")
    print(f"Analysis complete!")
    print(f"Videos with websites: {videos_with_websites}/{len(extracted_data)}")
    print(f"Total websites found: {len(all_websites)}")
    print(f"{'='*60}\n")
    
    return all_websites

def organize_by_category(websites):
    """Organize websites by category."""
    categories = {}
    
    for site in websites:
        category = site.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = []
        categories[category].append(site)
    
    # Sort categories by number of sites
    sorted_categories = dict(sorted(
        categories.items(),
        key=lambda x: len(x[1]),
        reverse=True
    ))
    
    return sorted_categories

def remove_duplicates(websites):
    """Remove duplicate websites (same URL)."""
    seen = {}
    unique = []
    
    for site in websites:
        url = site.get('url', '').lower().strip()
        if url and url not in seen:
            seen[url] = True
            unique.append(site)
    
    return unique

def main():
    # Check for API key
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set!")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # Load extracted text data
    print(f"Loading extracted text from {EXTRACTED_TEXT_FILE}...")
    with open(EXTRACTED_TEXT_FILE, 'r') as f:
        extracted_data = json.load(f)
    
    print(f"Loaded {len(extracted_data)} videos")
    
    # Analyze with AI
    all_websites = create_website_index(extracted_data)
    
    # Remove duplicates
    print("Removing duplicates...")
    unique_websites = remove_duplicates(all_websites)
    print(f"Unique websites: {len(unique_websites)}")
    
    # Organize by category
    print("Organizing by category...")
    categorized = organize_by_category(unique_websites)
    
    # Create final index
    index = {
        "total_websites": len(unique_websites),
        "total_categories": len(categorized),
        "generated_at": Path(EXTRACTED_TEXT_FILE).stat().st_mtime,
        "categories": categorized,
        "all_websites": unique_websites
    }
    
    # Save index
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"\n{'='*60}")
    print("INDEX CREATED!")
    print(f"{'='*60}")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"\nTotal unique websites: {len(unique_websites)}")
    print(f"Categories: {len(categorized)}")
    print("\nTop categories:")
    for i, (category, sites) in enumerate(list(categorized.items())[:10]):
        print(f"  {i+1}. {category}: {len(sites)} sites")
    
    # Also create a readable markdown version
    create_markdown_index(categorized, unique_websites)

def create_markdown_index(categorized, all_websites):
    """Create a human-readable markdown version of the index."""
    md_file = "website_index.md"
    
    with open(md_file, 'w') as f:
        f.write("# Website Index\n\n")
        f.write(f"Total websites: {len(all_websites)}\n\n")
        f.write("---\n\n")
        
        for category, sites in categorized.items():
            f.write(f"## {category} ({len(sites)} sites)\n\n")
            
            for site in sites:
                url = site.get('url', 'N/A')
                name = site.get('name', url)
                desc = site.get('description', 'No description')
                source = site.get('source_video', {})
                
                f.write(f"### {name}\n")
                f.write(f"**URL:** {url}\n\n")
                f.write(f"{desc}\n\n")
                f.write(f"*Source: [{source.get('title', 'Video')}]({source.get('url', '#')}) "
                       f"({source.get('views', 0):,} views)*\n\n")
                f.write("---\n\n")
    
    print(f"Markdown version saved to: {md_file}")

if __name__ == "__main__":
    main()
