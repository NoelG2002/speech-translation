from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

app = FastAPI()

BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY")
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID")
BHASHINI_API_URL = "https://udyat-api.bhashini.gov.in/translate"

class TranslationRequest(BaseModel):
    source_text: str
    source_lang: str
    target_lang: str

@app.get("/")
def root():
    return {"message": "Bhashini Translation API is running!"}

@app.post("/translate/")
def translate_text(request: TranslationRequest):
    if not BHASHINI_API_KEY or not BHASHINI_USER_ID:
        raise HTTPException(status_code=500, detail="Missing API Key or User ID")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": request.source_lang,
                        "targetLanguage": request.target_lang
                    },
                    "input": request.source_text
                }
            }
        ],
        "userId": BHASHINI_USER_ID
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BHASHINI_API_KEY}"
    }

    response = requests.post(BHASHINI_API_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    translated_text = response.json().get("output", "Translation failed")
    return {"translated_text": translated_text}
