import os
import json
import random
import asyncio
from pathlib import Path

import requests
import edge_tts
from google import genai


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)


# =========================
# 1. GENERATE SCRIPT
# =========================

def generate_script():
    prompt = """
Write a motivational speech in natural English.

Requirements:
- Length: around 3 minutes.
- Strong emotional and inspirational tone.
- Suitable for a YouTube motivational video.
- Natural spoken English.
- No headings.
- No bullet points.
- No emojis.
- Focus on perseverance, discipline, failure, confidence and success.
- Make it sound like a real motivational speaker.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    script = response.text.strip()

    if not script:
        raise RuntimeError("Gemini did not return a script.")

    return script


# =========================
# 2. GENERATE ENGLISH VOICE
# =========================

async def generate_voice(script):
    output_file = TEMP_DIR / "voice.mp3"

    communicate = edge_tts.Communicate(
        script,
        config["voice"],
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(str(output_file))

    if not output_file.exists():
        raise RuntimeError("Voice generation failed.")

    return output_file


# =========================
# 3. SEARCH PEXELS VIDEOS
# =========================

def search_videos(query):
    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "per_page": 15,
        "orientation": "landscape"
    }

    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    videos = data.get("videos", [])

    if not videos:
        raise RuntimeError(f"No videos found for: {query}")

    return videos


# =========================
# 4. PICK VIDEO
# =========================

def select_video(videos):
    valid = []

    for video in videos:
        files = video.get("video_files", [])

        for file in files:
            width = file.get("width", 0)
            height = file.get("height", 0)
            link = file.get("link")

            if link and width >= 1280 and height >= 720:
                valid.append(file)

    if not valid:
        raise RuntimeError("No suitable HD video found.")

    return random.choice(valid)


# =========================
# 5. DOWNLOAD VIDEO
# =========================

def download_video(url, output_file):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    with open(output_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    return output_file


# =========================
# MAIN
# =========================

def main():
    print("====================================")
    print(" AI MOTIVATIONAL VIDEO BOT")
    print("====================================")

    print("[1/4] Generating English script...")
    script = generate_script()

    print("\nSCRIPT:\n")
    print(script)

    print("\n[2/4] Generating English voice...")
    voice_file = asyncio.run(generate_voice(script))
    print(f"Voice saved: {voice_file}")

    print("\n[3/4] Searching motivational videos...")

    query = "motivational success person running training"

    videos = search_videos(query)

    selected = select_video(videos)

    video_file = TEMP_DIR / "clip.mp4"

    print("[4/4] Downloading video...")
    download_video(selected["link"], video_file)

    print("\nDONE")
    print(f"Voice: {voice_file}")
    print(f"Video: {video_file}")


if __name__ == "__main__":
    main()
