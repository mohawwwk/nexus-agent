from groq import Groq
from app.config import settings
import io


def transcribe_audio(audio_bytes: bytes, filename: str = "") -> dict:
    """
    Transcribe audio using Groq Whisper.
    Returns transcribed text and detected language.
    """
    try:
        client = Groq(api_key=settings.groq_api_key)

        # Determine content type from filename
        ext = filename.lower().split(".")[-1] if "." in filename else "mp3"
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "m4a": "audio/mp4",
            "ogg": "audio/ogg",
            "flac": "audio/flac",
            "webm": "audio/webm",
        }
        content_type = content_type_map.get(ext, "audio/mpeg")
        safe_filename = f"audio.{ext}"

        transcription = client.audio.transcriptions.create(
            file=(safe_filename, audio_bytes, content_type),
            model=settings.whisper_model,
            response_format="verbose_json",
        )

        text = transcription.text.strip()
        duration = getattr(transcription, "duration", None)
        language = getattr(transcription, "language", "unknown")

        return {
            "success": True,
            "text": text,
            "language": language,
            "duration_seconds": duration,
            "filename": filename,
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "language": "unknown",
            "duration_seconds": None,
            "filename": filename,
            "error": str(e),
        }
