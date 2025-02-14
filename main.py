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
    "userID": "1cfb9fb0efe34593aa1a75189df64199",  # Replace with Bhashini API user ID
    "ulcaApiKey": "42bb498f9a-14ee-4395-8d6a-57a2f947d32a"  # Replace with Bhashini API Key
}

# ✅ Root Endpoint (Available Languages)
@app.head('/')
@app.get('/')
async def root():
    return {k: v.capitalize() for k, v in languages.items()}

# ✅ Translation Endpoint
@app.post('/bhashini/translate', response_model=dict)
async def translate(request: TranslationRequest):
    # Map language codes
    source_language = languages.get(request.source_language)
    target_language = languages.get(request.target_language)

    if not source_language or not target_language:
        raise HTTPException(status_code=400, detail="Invalid language codes provided")

    # ✅ First Request: Get Model Service ID
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
        "pipelineRequestConfig": {
            "pipelineId": "64392f96daac500b55c543cd"
        }
    }

    headers = {
        "Content-Type": "application/json",
        "userID": "1cfb9fb0efe34593aa1a75189df64199",
        "ulcaApiKey": "42bb498f9a-14ee-4395-8d6a-57a2f947d32a"
    }

    response = requests.post('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline', json=payload, headers=headers)

    if response.status_code != 200:
        return {
            "status_code": response.status_code,
            "message": "Error fetching model service ID",
            "translated_content": None
        }

    response_data = response.json()
    service_id = response_data.get("pipelineResponseConfig", [{}])[0].get("config", [{}])[0].get("serviceId")

    if not service_id:
        return {
            "status_code": 500,
            "message": "Service ID not found in response",
            "translated_content": None
        }

    # ✅ Second Request: Compute Translation
    compute_payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language
                    },
                    "serviceId": service_id
                }
            }
        ],
        "inputData": {
            "input": [{"source": request.content}],
            "audio": [{"audioContent": None}]
        }
    }

    callback_url = response_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
    inference_api_key = response_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {})

    if not callback_url or not inference_api_key:
        return {
            "status_code": 500,
            "message": "Invalid callback URL or API key in response",
            "translated_content": None
        }

    headers2 = {
        "Content-Type": "application/json",
        inference_api_key["name"]: inference_api_key["value"]
    }

    compute_response = requests.post(callback_url, json=compute_payload, headers=headers2)

    if compute_response.status_code != 200:
        return {
            "status_code": compute_response.status_code,
            "message": "Error during translation",
            "translated_content": None
        }

    compute_response_data = compute_response.json()
    translated_content = compute_response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("target")

    if not translated_content:
        return {
            "status_code": 500,
            "message": "Translation output not found",
            "translated_content": None
        }

    return {
        "status_code": 200,
        "message": "Translation successful",
        "translated_content": translated_content
    }
# ✅ Speech-to-Text (STT) Endpoint
@app.post('/bhashini/stt', response_model=dict)
async def speech_to_text(language: str, audio: UploadFile = File(...)):
    # Get the correct language mapping
    source_language = languages.get(language)
    if not source_language:
        raise HTTPException(status_code=400, detail="Invalid language code")

    # ✅ Step 1: Get STT Model Service ID
    payload = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": source_language}
                }
            }
        ],
        "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"}
    }

    headers = {
        "Content-Type": "application/json",
        "userID": "1cfb9fb0efe34593aa1a75189df64199",
        "ulcaApiKey": "42bb498f9a-14ee-4395-8d6a-57a2f947d32a"
    }

    response = requests.post("https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline", json=payload, headers=headers)

    if response.status_code != 200:
        return {"status_code": response.status_code, "message": "Error fetching STT model service ID"}

    response_data = response.json()
    service_id = response_data.get("pipelineResponseConfig", [{}])[0].get("config", [{}])[0].get("serviceId")

    if not service_id:
        return {"status_code": 500, "message": "STT Service ID not found"}

    # ✅ Step 2: Send Audio for Transcription
    callback_url = response_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
    inference_api_key = response_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {})

    if not callback_url or not inference_api_key:
        return {"status_code": 500, "message": "Invalid STT callback URL or API key"}

    headers2 = {inference_api_key["name"]: inference_api_key["value"]}

    files = {"audio": (audio.filename, audio.file, "audio/wav")}
    compute_response = requests.post(callback_url, files=files, headers=headers2)

    if compute_response.status_code != 200:
        return {"status_code": compute_response.status_code, "message": "Error during STT processing"}

    compute_response_data = compute_response.json()
    transcript = compute_response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("source")

    if not transcript:
        return {"status_code": 500, "message": "No STT output found"}

    return {"status_code": 200, "message": "STT successful", "transcription": transcript}

# ✅ Text-to-Speech (TTS) Endpoint

@app.post('/bhashini/tts', response_model=dict)
async def text_to_speech(request: TTSRequest):
    # Get correct language mapping
    language = languages.get(request.language)
    if not language:
        raise HTTPException(status_code=400, detail="Invalid language code")

    # ✅ Step 1: Get TTS Model Service ID
    payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {"language": {"sourceLanguage": language}}
            }
        ],
        "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"}
    }

    headers = {
        "Content-Type": "application/json",
        "userID": "1cfb9fb0efe34593aa1a75189df64199",
        "ulcaApiKey": "42bb498f9a-14ee-4395-8d6a-57a2f947d32a"
    }

    response = requests.post("https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline", json=payload, headers=headers)

    if response.status_code != 200:
        return {"status_code": response.status_code, "message": "Error fetching TTS model service ID"}

    response_data = response.json()
    service_id = response_data.get("pipelineResponseConfig", [{}])[0].get("config", [{}])[0].get("serviceId")

    if not service_id:
        return {"status_code": 500, "message": "TTS Service ID not found"}

    # ✅ Step 2: Generate Speech
    callback_url = response_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
    inference_api_key = response_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {})

    if not callback_url or not inference_api_key:
        return {"status_code": 500, "message": "Invalid TTS callback URL or API key"}

    compute_payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": language},
                    "serviceId": service_id
                }
            }
        ],
        "inputData": {"input": [{"source": request.text}]}
    }

    headers2 = {inference_api_key["name"]: inference_api_key["value"]}

    compute_response = requests.post(callback_url, json=compute_payload, headers=headers2)

    if compute_response.status_code != 200:
        return {"status_code": compute_response.status_code, "message": "Error during TTS processing"}

    compute_response_data = compute_response.json()
    audio_content = compute_response_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("audioContent")

    if not audio_content:
        return {"status_code": 500, "message": "No TTS output found"}

    return {"status_code": 200, "message": "TTS successful", "audio_content": audio_content}
