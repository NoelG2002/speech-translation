from fastapi import FastAPI, HTTPException
import requests
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key from Render Environment Variables
UDYAT_API_KEY = os.getenv("UDYAT_API_KEY")
UDYAT_API_URL = "https://udyat-api.bhashini.gov.in/translate"  # Update if needed

# Request Body Model
class TranslateRequest(BaseModel):
    source_language: str
    target_language: str
    text: str

@app.post("/translate/")
def translate_text(request: TranslateRequest):
    headers = {
        "Authorization": f"Bearer {UDYAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "source_language": request.source_language,
        "target_language": request.target_language,
        "text": request.text
    }
    
    response = requests.post(UDYAT_API_URL, json=data, headers=headers)
    
    if response.status_code == 200:
        return {"translated_text": response.json().get("translated_text")}
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
