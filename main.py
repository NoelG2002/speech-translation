from fastapi import FastAPI, HTTPException
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env (only for local testing)
load_dotenv()

app = FastAPI()

# Bhashini API Credentials (Stored in Render)
BHASHINI_API_URL = os.getenv("BHASHINI_API_URL", "https://udyat-api.bhashini.gov.in/translate")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY")
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID")

HEADERS = {
    "Authorization": f"Bearer {BHASHINI_API_KEY}",
    "Content-Type": "application/json",
    "userID": BHASHINI_USER_ID  # Include User ID in headers
}
@app.head("/")
@app.get("/")
def root():
    return {"message": "Bhashini Translation API is running!"}

@app.post("/translate/")
def translate_text(source_text: str, source_lang: str, target_lang: str):
    if not BHASHINI_API_KEY or not BHASHINI_USER_ID:
        raise HTTPException(status_code=500, detail="Missing API Key or User ID")

    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_lang,
                        "targetLanguage": target_lang
                    }
                }
            }
        ],
        "inputData": {"input": [{"source": source_text}]}
    }

    response = requests.post(BHASHINI_API_URL, json=payload, headers=HEADERS)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    translated_text = response.json()["pipelineResponse"][0]["output"][0]["target"]
    return {"translated_text": translated_text}
