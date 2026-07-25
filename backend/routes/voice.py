"""
Voice route — accepts audio file and returns transcribed text.
Uses Gemini's multimodal audio understanding.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services import llm_service

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/x-m4a",
    "audio/aac",
}


class TranscribeResponse(BaseModel):
    transcribed_text: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    """
    Transcribe an audio file (Arabic or English) to text.
    The transcribed text is then sent to /api/chat as a regular message.
    """
    content_type = file.content_type or "audio/webm"

    # Normalize content type
    if "webm" in content_type:
        content_type = "audio/webm"
    elif "ogg" in content_type:
        content_type = "audio/ogg"
    elif "wav" in content_type:
        content_type = "audio/wav"
    elif "mp4" in content_type or "m4a" in content_type:
        content_type = "audio/mp4"
    elif "mpeg" in content_type or "mp3" in content_type:
        content_type = "audio/mpeg"
    elif "aac" in content_type:
        content_type = "audio/aac"

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    if len(audio_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=413, detail="Audio file too large (max 20MB).")

    try:
        transcribed_text = await llm_service.transcribe_audio(audio_bytes, content_type)
    except Exception as exc:
        print(f"[Voice] AI API error: {exc}")
        raise HTTPException(status_code=503, detail="Voice transcription is temporarily unavailable (API rate limits). Please type your message instead.")

    if not transcribed_text:
        raise HTTPException(status_code=422, detail="Could not transcribe the audio.")

    return TranscribeResponse(transcribed_text=transcribed_text)
