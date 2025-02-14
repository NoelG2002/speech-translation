import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, change this for more restrictive access
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Load sensitive credentials from Render environment variables
ULCA_API_KEY = os.getenv("ULCA_API_KEY")
ULCA_USER_ID = os.getenv("ULCA_USER_ID")
ULCA_ENDPOINT = os.getenv("Ulca_endpoint")


class PipelineConfig:
    def __init__(self, source_lang="en", target_lang="hi"):
        self.sourceLanguage = source_lang
        self.targetLanguage = target_lang
        self.pipeLineId = "your_pipeline_id"  # Replace with the actual pipeline ID

    def getTaskTypeConfig(self, taskType):
        """Returns the correct task configuration for the given task type."""
        taskTypeConfig = {
            "translation": {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": self.sourceLanguage,
                        "targetLanguage": self.targetLanguage,
                    },
                },
            },
            "tts": {
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": self.sourceLanguage},
                    "gender": "female",
                },
            },
            "asr": {
                "taskType": "asr",
                "config": {"language": {"sourceLanguage": self.sourceLanguage}},
            },
        }
        if taskType not in taskTypeConfig:
            raise HTTPException(status_code=400, detail="Invalid task type provided.")
        return taskTypeConfig[taskType]

    def getPipeLineConfig(self, taskType):
        """Fetches pipeline configuration for a given task type."""
        taskTypeConfig = self.getTaskTypeConfig(taskType)
        payload = json.dumps(
            {
                "pipelineTasks": [taskTypeConfig],
                "pipelineRequestConfig": {"pipelineId": self.pipeLineId},
            }
        )
        response = requests.post(
            ULCA_ENDPOINT,
            data=payload,
            headers={
                "ulcaApiKey": ULCA_API_KEY,
                "userID": ULCA_USER_ID,
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Pipeline configuration request failed.")

        serviceId = (
            response.json()["pipelineResponseConfig"][0]
            .get("config")[0]
            .get("serviceId")
        )
        taskTypeConfig["config"]["serviceId"] = serviceId
        return taskTypeConfig


class Payloads(PipelineConfig):
    """Handles different API payload structures."""

    def nmt_payload(self, text: str):
        return json.dumps(
            {
                "pipelineTasks": [self.getPipeLineConfig("translation")],
                "pipelineRequestConfig": {"pipelineId": self.pipeLineId},
                "inputData": {"input": [{"source": text}]},
            }
        )

    def tts_payload(self, text: str):
        return json.dumps(
            {
                "pipelineTasks": [self.getPipeLineConfig("tts")],
                "pipelineRequestConfig": {"pipelineId": self.pipeLineId},
                "inputData": {"input": [{"source": text}]},
            }
        )

    def asr_payload(self, base64_audio: str):
        return json.dumps(
            {
                "pipelineTasks": [self.getPipeLineConfig("asr")],
                "pipelineRequestConfig": {"pipelineId": self.pipeLineId},
                "inputData": {"audio": [{"audioContent": base64_audio}]},
            }
        )

    def asr_nmt_tts_payload(self, base64_audio: str):
        return json.dumps(
            {
                "pipelineTasks": [
                    self.getPipeLineConfig("asr"),
                    self.getPipeLineConfig("translation"),
                    self.getPipeLineConfig("tts"),
                ],
                "pipelineRequestConfig": {"pipelineId": self.pipeLineId},
                "inputData": {"audio": [{"audioContent": base64_audio}]},
            }
        )


# Initialize payload handler
pipeline = Payloads()
    
    
# FastAPI Request Models
class AudioRequest(BaseModel):
    audio: str


class TextRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "Bhashini API FastAPI Backend is running!"}


@app.post("/stt")
def speech_to_text(request: AudioRequest):
    """Handles Speech-to-Text (ASR) requests."""
    try:
        payload = pipeline.asr_payload(request.audio)
        response = requests.post(
            ULCA_ENDPOINT,
            data=payload,
            headers={
                "ulcaApiKey": ULCA_API_KEY,
                "userID": ULCA_USER_ID,
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="ASR request failed.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts")
def text_to_speech(request: TextRequest):
    """Handles Text-to-Speech (TTS) requests."""
    try:
        payload = pipeline.tts_payload(request.text)
        response = requests.post(
            ULCA_ENDPOINT,
            data=payload,
            headers={
                "ulcaApiKey": ULCA_API_KEY,
                "userID": ULCA_USER_ID,
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="TTS request failed.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/asr_nmt_tts")
def asr_nmt_tts(request: AudioRequest):
    """Handles ASR → Translation → TTS pipeline."""
    try:
        payload = pipeline.asr_nmt_tts_payload(request.audio)
        response = requests.post(
            ULCA_ENDPOINT,
            data=payload,
            headers={
                "ulcaApiKey": ULCA_API_KEY,
                "userID": ULCA_USER_ID,
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="ASR-NMT-TTS request failed.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
