# Nexus Agent — Agentic AI Assistant

A deployed, multi-modal agentic application that accepts Text, Images, PDFs, and Audio files simultaneously, extracts content, understands the user's goal, and autonomously performs the correct task — including complex, multi-step queries.

## Live Architecture

```
User Browser
    │
    ▼
React Chat UI (Vite, port 21419)
    │  API calls to /api/*
    ▼
Express Proxy (port 8080)
    │  Forwards all /api/* to FastAPI
    ▼
FastAPI Backend (port 8000)
    │
    ├── OCR Tool         ← pytesseract + Pillow
    ├── PDF Parser       ← pypdf
    ├── Audio Transcriber ← Groq Whisper large-v3
    ├── YouTube Fetcher  ← youtube-transcript-api
    ├── Summarizer       ← Groq llama-3.3-70b-versatile
    ├── Sentiment Analyzer ← Groq llama-3.3-70b-versatile
    ├── Code Explainer   ← Groq llama-3.3-70b-versatile
    ├── QA Answerer      ← Groq llama-3.3-70b-versatile
    └── Cross-Input Reasoner ← Groq llama-3.3-70b-versatile
```

## Input Pipeline

```
[Text] ──────────────────────────────────────────────────┐
[Image JPG/PNG] → OCR (pytesseract) → extracted text ────┤
[PDF] → PDF parser (pypdf) → text; detect YouTube URLs ──┤→ Agent Core (LLM)
[Audio MP3/WAV/M4A] → Groq Whisper → transcript ─────────┤       │
[YouTube URL] → youtube-transcript-api → transcript ──────┘       │
                                                                   ▼
                                                          Tool Registry
                                                                   │
                                                                   ▼
                                                          Text Output + Plan Trace
```

## Setup & Running

### Prerequisites

- Python 3.12+
- `tesseract-ocr` (for OCR): `sudo apt-get install tesseract-ocr`
- `poppler-utils` (for PDF): `sudo apt-get install poppler-utils`

### Environment Variables

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Required:
- `GROQ_API_KEY` — your Groq API key

Optional:
- `MODEL_NAME` — defaults to `llama-3.3-70b-versatile`
- `WHISPER_MODEL` — defaults to `whisper-large-v3`

### Install & Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t nexus-agent .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key nexus-agent
```

### Run Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

## API Reference

### POST /api/agent/run

Accepts `multipart/form-data`:
- `query` (string, required) — user's text query
- `session_id` (string, optional) — for session continuity
- `files` (multiple files, optional) — images, PDFs, audio files

Returns `AgentResult`:
```json
{
  "session_id": "uuid",
  "status": "success | needs_clarification | error",
  "clarification_question": null,
  "extracted_text": "raw text from files",
  "plan_trace": [
    {"step": 1, "tool": "pdf_parser", "description": "...", "result_preview": "...", "success": true}
  ],
  "final_answer": "The agent's answer...",
  "cost_estimate": "~$0.0004 (498 in + 106 out tokens)",
  "duration_seconds": 0.59
}
```

### POST /api/agent/clarify

Body: `{ "session_id": "...", "clarification": "..." }`

### GET /api/agent/history

Returns array of `ConversationEntry` objects.

### GET /api/healthz

Health check.

## Sample Test Cases

| # | Input | Expected Output |
|---|-------|-----------------|
| TC1 | Audio lecture (MP3) | Transcript + 1-line summary + 3 bullets + 5-sentence summary + duration |
| TC2 | PDF (meeting notes) + "What are the action items?" | Action items extracted from PDF |
| TC3 | Image of code + "Explain" | OCR → language detected → explanation + bug warnings + complexity |
| TC4 | PDF with YouTube URL + "Give me a summary of the YouTube video" | PDF extracted → YT URL detected → transcript fetched → summary |
| TC5 | Audio + PDF + "Do they discuss the same topic?" | Audio transcribed + PDF parsed → comparative analysis |

## Design Decisions

1. **Groq for LLM + Whisper**: Single API provider for both language model (llama-3.3-70b-versatile) and audio transcription (whisper-large-v3), reducing complexity and latency.

2. **Agentic orchestration via JSON mode**: The LLM plans tool sequences in structured JSON, enabling deterministic parsing and reliable multi-step chaining without hallucinated tool names.

3. **Mandatory follow-up**: If intent is unclear, the pipeline returns `needs_clarification` status and a specific question rather than guessing — matches the assignment's mandatory follow-up rule.

4. **Cross-input YouTube detection**: PDF text is scanned for YouTube URLs automatically before the agent even plans — ensures TC4 chain works without user needing to explicitly mention "there's a URL in the PDF".

5. **Express proxy pattern**: React frontend calls `/api` on the same domain → Express server proxies to FastAPI on port 8000. No CORS issues, no hardcoded backend URLs in the frontend.

## Deployment

The app is deployed on Replit. For other platforms:

### Render

```yaml
# render.yaml
services:
  - type: web
    name: nexus-agent
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY
        sync: false
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
```
