from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import base64

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Define request models
class TranslationRequest(BaseModel):
    source_language: int
    content: str
    target_language: int

class TTSRequest(BaseModel):
    language: int
    text: str

# ✅ Language Mapping (Bhashini Supported)
languages = {
    0: "en",  # English
    1: "hi",  # Hindi
    2: "gom", # Gom
    3: "kn",  # Kannada
    4: "doi", # Dogri
    5: "brx", # Bodo
    6: "ur",  # Urdu
    7: "ta",  # Tamil
    8: "ks",  # Kashmiri
    9: "as",  # Assamese
    10: "bn", # Bengali
    11: "mr", # Marathi
    12: "sd", # Sindhi
    13: "mai", # Maithili
    14: "pa",  # Punjabi
    15: "ml",  # Malayalam
    16: "mni", # Manipuri
    17: "te",  # Telugu
    18: "sa",  # Sanskrit
    19: "ne",  # Nepali
    20: "sat", # Santali
    21: "gu",  # Gujarati
    22: "or"   # Odia
}

# ✅ Bhashini API credentials
HEADERS = {
    "Content-Type": "application/json",
    "userID": "your_user_id",  # Replace with Bhashini API user ID
    "ulcaApiKey": "your_ulca_api_key"  # Replace with Bhashini API Key
}

# ✅ Root Endpoint (Available Languages)
@app.head('/')
@app.get('/')
async def root():
    return {k: v.capitalize() for k, v in languages.items()}

# ✅ Translation Endpoint
@app.post('/bhashini/translate')
async def translate(request: TranslationRequest):
    source_language = languages.get(request.source_language)
    target_language = languages.get(request.target_language)

    if not source_language or not target_language:
        raise HTTPException(status_code=400, detail="Invalid language codes provided")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    }
                }
            }
        ],
        "inputData": {
            "input": [{"source": request.content}]
        }
    }

    response = requests.post('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute', json=payload, headers=HEADERS)

    if response.status_code != 200:
        return {"status_code": response.status_code, "message": "Translation failed", "translated_content": None}

    response_data = response.json()
    translated_content = response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("target")

    return {"status_code": 200, "message": "Translation successful", "translated_content": translated_content}

# ✅ Speech-to-Text (STT) Endpoint
@app.post("/bhashini/stt")
async def speech_to_text(language: int, audio: UploadFile = File(...)):
    lang_code = languages.get(language)
    if not lang_code:
        raise HTTPException(status_code=400, detail="Invalid language code")

    audio_bytes = await audio.read()
    encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')

    payload = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": lang_code}
                }
            }
        ],
        "inputData": {
            "audio": [{"audioContent": encoded_audio}]
        }
    }

    response = requests.post('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute', json=payload, headers=HEADERS)

    if response.status_code != 200:
        return {"status_code": response.status_code, "message": "STT failed", "transcription": None}

    response_data = response.json()
    transcription = response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("source")

    return {"status_code": 200, "message": "STT successful", "transcription": transcription}

# ✅ Text-to-Speech (TTS) Endpoint
@app.post("/bhashini/tts")
async def text_to_speech(request: TTSRequest):
    lang_code = languages.get(request.language)
    if not lang_code:
        raise HTTPException(status_code=400, detail="Invalid language code")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": lang_code}
                }
            }
        ],
        "inputData": {
            "input": [{"source": request.text}]
        }
    }

    response = requests.post('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute', json=payload, headers=HEADERS)

    if response.status_code != 200:
        return {"status_code": response.status_code, "message": "TTS failed", "audio_content": None}

    response_data = response.json()
    audio_content = response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("audioContent")

    return {"status_code": 200, "message": "TTS successful", "audio_content": audio_content}
