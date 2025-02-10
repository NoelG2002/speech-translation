pip install fastapi uvicorn soundfile transformers nemo_toolkit[asr] torch
from fastapi import FastAPI, UploadFile, File
import nemo.collections.asr as nemo_asr
from transformers import MarianMTModel, MarianTokenizer
import soundfile as sf
import torch

app = FastAPI()

# Load NeMo ASR Model (Hindi speech recognition)
asr_model = nemo_asr.models.EncDecCTCModel.restore_from("exported_model.nemo")
asr_model = asr_model.to("cuda" if torch.cuda.is_available() else "cpu")

# Load Translator Model (English ↔ Hindi)
model_name = "Helsinki-NLP/opus-mt-hi-en"  # Change to en-hi for reverse
translator = MarianMTModel.from_pretrained(model_name)
tokenizer = MarianTokenizer.from_pretrained(model_name)

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...), target_lang: str = "en"):
    # Step 1: Load & Preprocess Audio
    audio, _ = sf.read(file.file)

    # Step 2: Speech-to-Text (STT)
    transcription = asr_model.transcribe([audio])[0]

    # Step 3: Translation (if needed)
    if target_lang == "en":
        translated = tokenizer.decode(
            translator.generate(**tokenizer(transcription, return_tensors="pt"))[0], 
            skip_special_tokens=True
        )
    else:
        translated = transcription  # No translation

    # Step 4: Save Transcription
    with open("transcription.txt", "w") as f:
        f.write(translated)

    return {"original": transcription, "translated": translated}

