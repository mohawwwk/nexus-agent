import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def extract_youtube_url(text: str) -> str | None:
    """
    Extract a YouTube URL from arbitrary text.
    """
    patterns = [
        r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"https?://youtu\.be/([a-zA-Z0-9_-]{11})",
        r"https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def get_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_youtube_transcript(url: str) -> dict:
    """
    Fetch transcript from a YouTube video URL.
    Returns transcript text or fallback message.
    """
    video_id = get_video_id(url)
    if not video_id:
        return {
            "success": False,
            "text": "",
            "url": url,
            "error": "Could not extract video ID from URL.",
        }

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry["text"] for entry in transcript_list)
        duration = transcript_list[-1]["start"] + transcript_list[-1]["duration"] if transcript_list else 0

        return {
            "success": True,
            "text": text.strip(),
            "url": url,
            "video_id": video_id,
            "duration_seconds": round(duration),
        }
    except TranscriptsDisabled:
        return {
            "success": False,
            "text": "",
            "url": url,
            "error": "Transcripts are disabled for this video.",
        }
    except NoTranscriptFound:
        return {
            "success": False,
            "text": "",
            "url": url,
            "error": "No transcript found for this video (may not have captions).",
        }
    except VideoUnavailable:
        return {
            "success": False,
            "text": "",
            "url": url,
            "error": "Video is unavailable or private.",
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "url": url,
            "error": f"Failed to fetch transcript: {str(e)}",
        }
