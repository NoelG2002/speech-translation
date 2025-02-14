from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
    0: "en", 1: "hi", 2: "gom", 3: "kn", 4: "doi", 5: "brx", 6: "ur",
    7: "ta", 8: "ks", 9: "as", 10: "bn", 11: "mr", 12: "sd", 13: "mai",
    14: "pa", 15: "ml", 16: "mni", 17: "te", 18: "sa", 19: "ne", 
    20: "sat", 21: "gu", 22: "or"
}

# ✅ Bhashini API credentials
HEADERS = {
    "Content-Type": "application/json",
    "userID": "1cfb9fb0efe34593aa1a75189df64199",  # Replace with Bhashini API user ID
    "ulcaApiKey": "42bb498f9a-14ee-4395-8d6a-57a2f947d32a"  # Replace with Bhashini API Key
}

# ✅ Root Endpoint (Available Languages)
@app.get('/')
async def root():
    return {k: v.capitalize() for k, v in languages.items()}

# ✅ Function to fetch service ID
def get_service_id(task_type, source_language, target_language=None):
    payload = {
        "pipelineTasks": [
            {"taskType": task_type, "config": {"language": {"sourceLanguage": source_language}}}
        ],
        "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"}
    }
    
    if target_language:
        payload["pipelineTasks"][0]["config"]["language"]["targetLanguage"] = target_language

    response = requests.post("https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline", json=payload, headers=HEADERS)

    if response.status_code != 200:
        return None, None

    response_data = response.json()
    service_id = response_data.get("pipelineResponseConfig", [{}])[0].get("config", [{}])[0].get("serviceId")
    callback_url = response_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl")
    inference_api_key = response_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {})

    return service_id, callback_url, inference_api_key

# ✅ Translation Endpoint
@app.post('/bhashini/translate', response_model=dict)
async def translate(request: TranslationRequest):
    source_language = languages[request.source_language]
    content = request.content
    target_language = languages[request.target_language] 

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
            "pipelineId" : "64392f96daac500b55c543cd"
        }
    }

    headers = {
        "Content-Type": "application/json",
        "userID": "e832f2d25d21443e8bb90515f1079041",
        "ulcaApiKey": "39e27ce432-f79c-46f8-9c8c-c0856007cb4b"
    }

    response = requests.post('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline', json=payload, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        service_id = response_data["pipelineResponseConfig"][0]["config"][0]["serviceId"]

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
                "input": [
                    {
                        "source": content
                    }
                ],
                "audio": [
                    {
                        "audioContent": None
                    }
                ]
            }
        }

        callback_url = response_data["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        
        headers2 = {
            "Content-Type": "application/json",
            response_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]:
                response_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]
        }

        compute_response = requests.post(callback_url, json=compute_payload, headers=headers2)

        if compute_response.status_code == 200:
            compute_response_data = compute_response.json()
            translated_content = compute_response_data["pipelineResponse"][0]["output"][0]["target"]
            return {
                "status_code": 200,
                "message": "Translation successful",
                "translated_content": translated_content
            }
        else:
            return {
                "status_code": compute_response.status_code,
                "message": "Error in translation",
                "translated_content": None
            }
    else:
        return {
            "status_code": response.status_code,
            "message": "Error in translation request",
            "translated_content": None
        }
# ✅ Speech-to-Text (STT) Endpoint
@app.post("/bhashini/stt")
async def speech_to_text(audio: UploadFile = File(...), language: int = Form(...)):
    source_language = languages.get(language)
    
    if not source_language:
        raise HTTPException(status_code=400, detail="Invalid language code")

    service_id, callback_url, inference_api_key = get_service_id("asr", source_language)

    if not service_id or not callback_url or not inference_api_key:
        raise HTTPException(status_code=500, detail="STT Service ID or API details not found")

    audio_data = await audio.read()
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {"language": {"sourceLanguage": source_language}, "serviceId": service_id}
            }
        ],
        "inputData": {"audio": [{"audioContent": audio_base64}]}
    }

    headers = {inference_api_key["name"]: inference_api_key["value"]}
    response = requests.post(callback_url, json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="STT processing failed")

    return {"transcription": response.json().get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("source")}

# ✅ Text-to-Speech (TTS) Endpoint
@app.post('/bhashini/tts')
async def text_to_speech(request: TTSRequest):
    language = languages.get(request.language)
    
    if not language:
        raise HTTPException(status_code=400, detail="Invalid language code")

    service_id, callback_url, inference_api_key = get_service_id("tts", language)

    if not service_id or not callback_url or not inference_api_key:
        raise HTTPException(status_code=500, detail="TTS Service ID or API details not found")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {"language": {"sourceLanguage": language}, "serviceId": service_id}
            }
        ],
        "inputData": {"input": [{"source": request.text}]}
    }

    headers = {inference_api_key["name"]: inference_api_key["value"]}
    response = requests.post(callback_url, json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="TTS processing failed")

    audio_content = response.json().get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("audioContent")
    
    return {"audio_content": audio_content}
