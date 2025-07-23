
from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import os
from datetime import datetime
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
from dotenv import load_dotenv 
load_dotenv() 

app = Flask(__name__)

# SQLAlchemy DB config
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DB')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define the SQLAlchemy model for storing generated song metadata
class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    lyrics = db.Column(db.Text, nullable=False)
    style = db.Column(db.String(100), nullable=False)
    mood = db.Column(db.String(100), nullable=False)
    theme = db.Column(db.String(100), nullable=False)
    audio_url = db.Column(db.String(500))
    task_id = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class SunoMusicGenerator:
    def __init__(self):
        self.suno_api_key = os.environ.get('SUNO_API_KEY')
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.base_url = "https://api.sunoapi.org"
        self.gemini_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.1, api_key=self.gemini_api_key
        )

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
            "model": "v4"
        }


        if callback_url:
            payload["callBackUrl"] = callback_url

        response = requests.post(
            f"{self.base_url}/api/v1/generate",
            headers=headers,
            json=payload
        )

        return response.json(), response.status_code


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
        "prompt": lyrics,
        "style": style,
        "title": title,
    }

    if callback_url:
        payload["callBackUrl"] = callback_url  

    print("Payload to Suno:", json.dumps(payload, indent=2))

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
    print("✅ /generate_music route was hit")

    try:
        data = request.json

        callback_url = data.get("callback_url") or data.get("callBackUrl")
        if not callback_url:
            return jsonify({"error": "Missing callBackUrl"}), 400

        lyrics = data.get("lyrics")
        style = data.get("style")
        title = data.get("title")
        mood = data.get("mood")
        theme = data.get("theme")
        custom_mode = data.get("custom_mode", True)
        instrumental = data.get("instrumental", False)

        if not lyrics:
            lyrics = generator.generate_lyrics(theme=theme, genre=style, mood=mood, verse_count=2)

        print("\n📩 Incoming Request Payload:")
        print(json.dumps(data, indent=2))

        # Call the Suno API generator
        result, status = generator.generate_music(
            lyrics=lyrics,
            style=style,
            title=title,
            callback_url=callback_url,
            custom_mode=custom_mode,
            instrumental=instrumental
        )

        print("\n🎵 Suno API Response:")
        print(json.dumps(result, indent=2) if isinstance(result, dict) else result)

        return jsonify(result), status

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e)
        }), 500



@app.route("/check_status/<task_id>", methods=["GET"])
def check_status(task_id):
    headers = {
        "Authorization": f"Bearer {os.getenv('SUNO_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.get(f"https://studio-api.suno.ai/api/tasks/{task_id}", headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Failed to get status from Suno API"}), 500

    data = response.json()
    audio_url = data.get("audio_url")
    status = data.get("status", "pending")

    # If audio_url is ready, update database
    if audio_url:
        song = Song.query.filter_by(task_id=task_id).first()
        if song:
            song.audio_url = audio_url
            db.session.commit()

    return jsonify({
        "status": status,
        "audio_url": audio_url
    })


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
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)

