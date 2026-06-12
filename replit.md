# Nexus Agent

A deployed, multi-modal agentic AI assistant that accepts Text, Images, PDFs, and Audio files simultaneously — extracts content, understands the user's goal, and autonomously performs the correct task including complex multi-step queries.

**GitHub:** https://github.com/mohawwwk/nexus-agent

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the Express proxy server (port 8080)
- `cd artifacts/fastapi-backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` — run FastAPI backend
- `pnpm --filter @workspace/agent-ui run dev` — run React frontend
- `pnpm run typecheck` — full TypeScript check across all packages
- `cd artifacts/fastapi-backend && python -m pytest tests/ -v` — run test suite (14 tests)
- Required env: `GROQ_API_KEY`

## Stack

- **Frontend:** React 19 · Vite 7 · TailwindCSS · shadcn/ui · pnpm workspaces
- **Backend:** FastAPI · Python 3.12 · Groq API (llama-3.3-70b-versatile + Whisper)
- **OCR:** pytesseract · Pillow
- **PDF:** pypdf
- **Audio:** Groq Whisper large-v3
- **Proxy:** Node.js Express (proxies `/api` → FastAPI on port 8000)
- **Infra:** Docker · Replit

## Where things live

- `artifacts/fastapi-backend/` — FastAPI agent backend (Python)
  - `app/agent.py` — main agentic pipeline
  - `app/tools/` — ocr_tool, pdf_tool, audio_tool, youtube_tool
  - `app/routers/agent.py` — API routes
  - `tests/test_agent.py` — 14 test cases
  - `Dockerfile` — production container
  - `README.md` — full API docs + deployment guide
- `artifacts/agent-ui/` — React chat frontend
- `artifacts/api-server/` — Express proxy (routes `/api` → FastAPI)
- `docs/architecture.svg` — Architecture diagram (assignment rubric deliverable)
- `lib/api-client-react/` — Orval-generated API hooks + Zod schemas

## Architecture decisions

1. **Groq for LLM + Whisper**: Single API provider for both language model and audio transcription — reduces latency and complexity.
2. **JSON-mode intent detection**: LLM plans tool sequences in structured JSON, enabling deterministic parsing and reliable multi-step chaining.
3. **Never block on clarification**: Agent is decisive by default — if content exists, it always processes it. Vague queries get helpful responses instead of question loops.
4. **Session-based context**: Extracted file content stored in session cache, so clarification answers can resume with full context.
5. **Express proxy pattern**: Frontend calls `/api` on the same domain → Express proxies to FastAPI. No CORS issues, no hardcoded backend URLs.

## Product

- **Text** — conversational Q&A, summarization, sentiment analysis, code explanation
- **Image** (PNG/JPG) → OCR via pytesseract → explains/analyzes extracted text
- **PDF** → pypdf text extraction → answers questions; auto-detects YouTube URLs
- **Audio** (MP3/WAV/M4A) → Groq Whisper transcription → summarizes
- **YouTube URLs** (anywhere in any input) → fetches transcript → summarizes
- **Multi-file** — combine any inputs in one query for cross-input reasoning
- **Plan trace** — every response shows each tool step with success/fail status
- **Cost estimate** — approximate USD cost per request shown in UI

## User preferences

- Keep the agent decisive — no unnecessary question loops
- All outputs text-only
- Show plan trace in UI

## Gotchas

- FastAPI must be running on port 8000 before the Express proxy starts
- `GROQ_API_KEY` must be set in environment secrets
- Tesseract and poppler must be installed for OCR and PDF tools
- OCR on blank/minimal images returns empty text (not an error)

## Pointers

- Architecture diagram: `docs/architecture.svg`
- Assignment PDF: `attached_assets/DSAI_Assignment_June_2026_1781226914084.pdf`
- See `artifacts/fastapi-backend/README.md` for full API docs and deployment guide
