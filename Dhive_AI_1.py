
from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import requests
import json
import os
from datetime import datetime
from pathlib import Path
import urllib.request

app = Flask(__name__)

class SunoMusicGenerator:
    def __init__(self):
        self.suno_api_key = os.environ.get('SUNO_API_KEY')
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.base_url = "https://api.sunoapi.org"
        self.gemini_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.1, api_key=self.gemini_api_key)

    def generate_lyrics(self, theme, genre, mood, verse_count=2):
        prompt = PromptTemplate(
            template="""
            Create original song lyrics with the following specifications:
            - Theme: {theme}
            - Genre: {genre}
            - Mood: {mood}
            - Structure: {verse_count} verses, chorus, bridge
            Format the lyrics with proper structure tags:
            [Intro]
            [Verse 1]
            [Chorus]
            [Verse 2]
            [Chorus]
            [Bridge]
            [Chorus]
            [Outro]
            Make the lyrics creative, original, and emotionally engaging.
            Keep verses to 4-6 lines and chorus to 3-4 lines.
            """,
            input_variables=["theme", "genre", "mood", "verse_count"])

        chain = prompt | self.gemini_model | StrOutputParser()
        response = chain.invoke({
            "theme": theme,
            "genre": genre,
            "mood": mood,
            "verse_count": verse_count
        })
        return response

    def generate_music(self, lyrics, style, title, callback_url=None, custom_mode=True, instrumental=False):
        headers = {
            "Authorization": f"Bearer {self.suno_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "customMode": custom_mode,
            "instrumental": instrumental,
            "prompt": lyrics,
            "style": style,
            "title": title,
            "model": "V4"
        }

        if callback_url:
            payload["callback_url"] = callback_url

        response = requests.post(
            f"{self.base_url}/api/v1/generate", headers=headers, json=payload)

        return response.json(), response.status_code

    def check_status(self, task_id):
        headers = {
            "Authorization": f"Bearer {self.suno_api_key}",
            'Accept': 'application/json'
        }

        data = requests.get(
            f"{self.base_url}/api/v1/generate/record-info?taskId={task_id}", headers=headers)
        return data.json(), data.status_code

    def download_audio(self, audio_url):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suno_track_{timestamp}.mp3"
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        filepath = downloads_dir / filename

        urllib.request.urlretrieve(audio_url, filepath)
        return str(filepath)

generator = SunoMusicGenerator()

@app.route("/generate_lyrics", methods=["POST"])
def generate_lyrics():
    data = request.json
    response = generator.generate_lyrics(
        data.get("theme"), data.get("genre"), data.get("mood"), data.get("verse_count", 2))
    return jsonify({"lyrics": response})

@app.route("/generate_music", methods=["POST"])
def generate_music():
    data = request.json
    result, status = generator.generate_music(
        lyrics=data.get("lyrics"),
        style=data.get("style"),
        title=data.get("title"),
        callback_url=data.get("callback_url"),
        custom_mode=data.get("custom_mode", True),
        instrumental=data.get("instrumental", False)
    )
    return jsonify(result), status

@app.route("/check_status/<task_id>", methods=["GET"])
def check_status(task_id):
    result, status = generator.check_status(task_id)
    return jsonify(result), status

@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("audio_url")
    if not url:
        return jsonify({"error": "audio_url required"}), 400

    try:
        path = generator.download_audio(url)
        return jsonify({"message": "Downloaded successfully", "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
