from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

# ✅ Enable CORS (Fix OPTIONS 405 issue)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend domain for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Define request model
class TranslationRequest(BaseModel):
    source_language: int
    content: str
    target_language: int

# ✅ Language Mapping
languages = {
    1: "hi", 2: "gom", 3: "kn", 4: "doi", 5: "brx", 6: "ur", 7: "ta", 8: "ks", 9: "as",
    10: "bn", 11: "mr", 12: "sd", 13: "mai", 14: "pa", 15: "ml", 16: "mni", 17: "te",
    18: "sa", 19: "ne", 20: "sat", 21: "gu", 22: "or"
}

# ✅ Root Endpoint (Returns Available Languages)
@app.get('/')
async def root():
    return {k: v.capitalize() for k, v in languages.items()}

# ✅ Translation Endpoint
@app.post('/scaler/translate', response_model=dict)
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
