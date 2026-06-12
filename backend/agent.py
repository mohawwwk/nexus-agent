"""
Agentic pipeline: intent detection, tool routing, multi-step chaining.
Uses Groq llama-3.3-70b-versatile as the orchestrating LLM.
"""
import json
import time
import uuid
from typing import Optional
from groq import Groq

from app.config import settings
from app.models import PlanStep, AgentResult, ConversationEntry, conversation_history, get_or_create_session, sessions
from app.tools.ocr_tool import run_ocr
from app.tools.pdf_tool import extract_pdf_text
from app.tools.audio_tool import transcribe_audio
from app.tools.youtube_tool import fetch_youtube_transcript, extract_youtube_url

client = Groq(api_key=settings.groq_api_key)

# ─── System Prompt ────────────────────────────────────────────────────────────
# Key design: agent MUST be decisive. Clarification is a last resort only.

SYSTEM_PROMPT = """You are an intelligent agentic assistant that analyzes text, images, PDFs, and audio files.

Available tools (file extraction already happened — results are in the context):
- summarizer: 3-format summary: 1-line + 3 bullets + 5-sentence paragraph
- sentiment_analyzer: sentiment label + confidence % + one-line justification
- code_explainer: explain code, detect language, find bugs, state time complexity
- qa_answerer: answer specific questions from extracted content
- youtube_fetcher: fetch YouTube transcript from a URL
- conversational: answer general questions / explain capabilities / handle missing content gracefully
- cross_input_reasoner: compare/combine content from multiple sources

ABSOLUTE RULES — follow these exactly:
1. NEVER set needs_clarification=true. Always set it to false. Always proceed.
2. If content is unclear or missing, use the conversational tool and explain what you CAN do or what content you'd need — do this in final_answer, not as a clarification question.
3. If files were uploaded, ALWAYS process them — use their extracted text.
4. Pick the most sensible tool. Do not overthink.

Respond ONLY with valid JSON:
{
  "needs_clarification": false,
  "clarification_question": null,
  "plan": [
    {"step": 1, "tool": "tool_name", "description": "What this step does"}
  ],
  "final_answer": null
}

DECISION GUIDE:
- Has files + question → qa_answerer
- "summarize" / "summary" + has content → summarizer
- "summarize" / "summary" + NO content → conversational (explain: please share content)
- "sentiment" / "tone" / "feel" → sentiment_analyzer
- code in content or query → code_explainer
- YouTube URL present → youtube_fetcher → summarizer
- Multiple files, compare → cross_input_reasoner
- General knowledge question, no files → conversational
- Vague with no files → conversational (be helpful, explain capabilities)
"""


def estimate_cost(input_tokens: int, output_tokens: int) -> str:
    input_cost = (input_tokens / 1_000_000) * 0.59
    output_cost = (output_tokens / 1_000_000) * 0.79
    total = input_cost + output_cost
    return f"~${total:.4f} ({input_tokens} in + {output_tokens} out tokens)"


def run_llm_tool(tool_name: str, content: str, instruction: str) -> str:
    """Run a specific tool via the LLM."""
    tool_prompts = {
        "summarizer": f"""Summarize the following content in exactly this format:

**1-Line Summary:** [one sentence]

**Key Points:**
• [bullet 1]
• [bullet 2]
• [bullet 3]

**Detailed Summary:**
[5 complete sentences covering the main ideas]

Content:
{content[:8000]}""",

        "sentiment_analyzer": f"""Analyze the sentiment of the following text. Respond with:

**Sentiment:** [Positive / Negative / Neutral / Mixed]
**Confidence:** [0-100]%
**Justification:** [one sentence explaining why]

Text:
{content[:4000]}""",

        "code_explainer": f"""Analyze this code:

**Language Detected:** [language]
**What it does:** [clear explanation of the code's purpose and logic]
**Potential Bugs:** [list any bugs, edge cases, or issues found, or "None detected"]
**Time Complexity:** [Big-O notation with explanation]
**Suggestions:** [any improvements]

Code:
{content[:6000]}""",

        "qa_answerer": f"""Using the provided context, answer this question: {instruction}

Context:
{content[:8000]}

Provide a clear, accurate, and complete answer based on the context. If the context is an audio transcript or lecture, treat it as the source material.""",

        "cross_input_reasoner": f"""{instruction}

Content from multiple sources:
{content[:8000]}

Provide a thorough comparative analysis.""",

        "conversational": f"""Answer this question helpfully and conversationally: {instruction}""",
    }

    prompt = tool_prompts.get(tool_name, f"Process this for task '{instruction}':\n\n{content[:6000]}")

    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def build_context_from_extractions(extractions: list[dict]) -> str:
    parts = []
    for ext in extractions:
        source = ext.get("source", "unknown")
        text = ext.get("text", "")
        if text:
            parts.append(f"[Source: {source}]\n{text}")
    return "\n\n---\n\n".join(parts) if parts else ""


def run_agent_pipeline(
    query: str,
    files: list[dict],
    session_id: str,
    clarification: Optional[str] = None,
) -> AgentResult:
    start_time = time.time()
    plan_trace: list[PlanStep] = []
    step_num = 0
    extracted_texts: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0

    session = get_or_create_session(session_id)

    # ── CLARIFICATION RESUME: restore stored context from session ──────────────
    # When user answers a clarification, we resume with the original query +
    # previously extracted file content — no files are re-sent.
    if clarification and session.get("pending_clarification"):
        stored = session["pending_clarification"]
        query = stored["original_query"] + f"\n\nUser clarification: {clarification}"
        extracted_texts = stored.get("extracted_texts", [])
        session["pending_clarification"] = None
        # Skip file processing below since we restored from session
        files = []

    # ── STEP 1: Extract content from all uploaded files ────────────────────────
    for file_info in files:
        filename = file_info["filename"]
        file_bytes = file_info["bytes"]
        file_type = file_info["type"]
        step_num += 1

        if file_type.startswith("image/"):
            result = run_ocr(file_bytes, filename)
            success = result["success"]
            text = result.get("text", "")
            confidence = result.get("confidence", 0)
            plan_trace.append(PlanStep(
                step=step_num,
                tool="ocr_tool",
                description=f"OCR text extraction from image '{filename}'",
                result_preview=f"Extracted {len(text)} chars | Confidence: {confidence}%" if success else result.get("error", "OCR failed"),
                success=success,
            ))
            if text:
                extracted_texts.append({"source": f"Image: {filename}", "text": text})

        elif file_type == "application/pdf" or filename.lower().endswith(".pdf"):
            result = extract_pdf_text(file_bytes, filename)
            success = result["success"]
            text = result.get("text", "")
            pages = result.get("page_count", 0)
            plan_trace.append(PlanStep(
                step=step_num,
                tool="pdf_parser",
                description=f"PDF text extraction from '{filename}' ({pages} pages)",
                result_preview=f"Extracted {len(text)} chars from {pages} pages" if success else result.get("error", "PDF parse failed"),
                success=success,
            ))
            if text:
                extracted_texts.append({"source": f"PDF: {filename}", "text": text})
                # Auto-detect YouTube URLs inside PDF
                yt_url = extract_youtube_url(text)
                if yt_url:
                    step_num += 1
                    yt_result = fetch_youtube_transcript(yt_url)
                    yt_success = yt_result["success"]
                    yt_text = yt_result.get("text", "")
                    plan_trace.append(PlanStep(
                        step=step_num,
                        tool="youtube_fetcher",
                        description=f"Detected YouTube URL in PDF — fetching transcript: {yt_url}",
                        result_preview=f"Transcript: {len(yt_text)} chars" if yt_success else yt_result.get("error", "Fetch failed"),
                        success=yt_success,
                    ))
                    if yt_text:
                        extracted_texts.append({"source": f"YouTube: {yt_url}", "text": yt_text})

        elif file_type.startswith("audio/") or filename.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm")):
            result = transcribe_audio(file_bytes, filename)
            success = result["success"]
            text = result.get("text", "")
            duration = result.get("duration_seconds")
            duration_str = f" | Duration: {int(duration)}s" if duration else ""
            plan_trace.append(PlanStep(
                step=step_num,
                tool="audio_transcriber",
                description=f"Audio transcription of '{filename}' via Groq Whisper",
                result_preview=f"Transcribed {len(text)} chars{duration_str}" if success else result.get("error", "Transcription failed"),
                success=success,
            ))
            if text:
                extracted_texts.append({"source": f"Audio: {filename}", "text": text})

    # Auto-detect YouTube URL in query text
    yt_url_in_query = extract_youtube_url(query)
    if yt_url_in_query and not any(yt_url_in_query in e["source"] for e in extracted_texts):
        step_num += 1
        yt_result = fetch_youtube_transcript(yt_url_in_query)
        yt_success = yt_result["success"]
        yt_text = yt_result.get("text", "")
        plan_trace.append(PlanStep(
            step=step_num,
            tool="youtube_fetcher",
            description=f"Fetching YouTube transcript from URL in query: {yt_url_in_query}",
            result_preview=f"Transcript: {len(yt_text)} chars" if yt_success else yt_result.get("error", "Fetch failed"),
            success=yt_success,
        ))
        if yt_text:
            extracted_texts.append({"source": f"YouTube: {yt_url_in_query}", "text": yt_text})

    all_extracted_text = build_context_from_extractions(extracted_texts)

    # ── STEP 2: Intent detection via LLM ──────────────────────────────────────
    step_num += 1

    # Tell the LLM exactly what content is available so it doesn't get confused
    if all_extracted_text:
        content_summary = f"Extracted content ({len(all_extracted_text)} chars total):\n{all_extracted_text[:6000]}"
    else:
        content_summary = "No files uploaded — query only."

    # Track whether clarification was already asked this session
    already_clarified = session.get("clarification_count", 0) > 0

    user_message = f"""User query: {query}

{content_summary}

{"NOTE: Do NOT ask for clarification — the user already answered one. Proceed with best interpretation." if already_clarified else ""}

Determine the best tool sequence and respond in JSON."""

    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"},
    )

    usage = response.usage
    if usage:
        total_input_tokens += usage.prompt_tokens
        total_output_tokens += usage.completion_tokens

    try:
        llm_response = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        llm_response = {
            "needs_clarification": False,
            "plan": [{"step": 1, "tool": "conversational", "description": "Answer the question"}],
            "final_answer": response.choices[0].message.content,
        }

    # ── STEP 3: Clarification needed (strict gate) ─────────────────────────────
    # Never ask twice; never ask if content was extracted
    if llm_response.get("needs_clarification") and not already_clarified and not all_extracted_text:
        clarification_question = llm_response.get("clarification_question", "Could you clarify what you'd like me to do?")
        session["pending_clarification"] = {
            "original_query": query,
            "extracted_texts": extracted_texts,
        }
        session["clarification_count"] = session.get("clarification_count", 0) + 1

        plan_trace.append(PlanStep(
            step=step_num,
            tool="intent_detector",
            description="Intent ambiguous — asking clarification",
            result_preview=clarification_question,
            success=True,
        ))

        duration = time.time() - start_time
        return AgentResult(
            session_id=session_id,
            status="needs_clarification",
            clarification_question=clarification_question,
            extracted_text=all_extracted_text or None,
            plan_trace=plan_trace,
            final_answer=None,
            cost_estimate=estimate_cost(total_input_tokens, total_output_tokens),
            duration_seconds=round(duration, 2),
        )

    # ── STEP 4: Execute the tool plan ─────────────────────────────────────────
    plan_trace.append(PlanStep(
        step=step_num,
        tool="intent_detector",
        description="Intent analysis complete — plan determined",
        result_preview=f"Tools to run: {[p['tool'] for p in llm_response.get('plan', [])]}",
        success=True,
    ))

    llm_plan = llm_response.get("plan", [])
    final_answer = llm_response.get("final_answer")  # sometimes LLM fills this directly
    tool_context = all_extracted_text

    for planned_step in llm_plan:
        tool_name = planned_step.get("tool", "conversational")
        description = planned_step.get("description", "")
        step_num += 1

        # Skip extraction tools — already done above
        if tool_name in ("ocr_tool", "pdf_parser", "audio_transcriber"):
            continue

        # Skip youtube_fetcher if already fetched
        if tool_name == "youtube_fetcher" and any("YouTube" in e["source"] for e in extracted_texts):
            continue

        try:
            if tool_name == "youtube_fetcher":
                yt_url = extract_youtube_url(query) or extract_youtube_url(all_extracted_text)
                if yt_url:
                    yt_result = fetch_youtube_transcript(yt_url)
                    tool_output = yt_result.get("text", yt_result.get("error", "No transcript"))
                    tool_context = tool_output
                    success = yt_result["success"]
                else:
                    tool_output = "No YouTube URL found in query or files"
                    success = False
                plan_trace.append(PlanStep(
                    step=step_num, tool=tool_name,
                    description=description,
                    result_preview=tool_output[:200] if tool_output else None,
                    success=success,
                ))

            elif tool_name in ("summarizer", "sentiment_analyzer", "code_explainer", "qa_answerer", "cross_input_reasoner", "conversational"):
                # Use extracted content if available, otherwise use query text as content
                content_for_tool = tool_context or query
                tool_output = run_llm_tool(tool_name, content_for_tool, query)
                final_answer = tool_output
                plan_trace.append(PlanStep(
                    step=step_num, tool=tool_name,
                    description=description,
                    result_preview=tool_output[:200] if tool_output else None,
                    success=bool(tool_output),
                ))
                total_input_tokens += len(content_for_tool) // 4
                total_output_tokens += len(tool_output) // 4

            else:
                # Unknown tool — conversational fallback
                tool_output = run_llm_tool("conversational", tool_context or query, query)
                final_answer = tool_output
                plan_trace.append(PlanStep(
                    step=step_num, tool=tool_name,
                    description=description,
                    result_preview=tool_output[:200] if tool_output else None,
                    success=True,
                ))

        except Exception as e:
            plan_trace.append(PlanStep(
                step=step_num, tool=tool_name,
                description=description,
                result_preview=f"Error: {str(e)}",
                success=False,
            ))

    # ── Fallback: if no tool ran, produce an answer now ───────────────────────
    if not final_answer:
        if all_extracted_text:
            final_answer = run_llm_tool("qa_answerer", all_extracted_text, query)
        else:
            final_answer = run_llm_tool("conversational", "", query)
        total_output_tokens += len(final_answer) // 4

    duration = time.time() - start_time
    return AgentResult(
        session_id=session_id,
        status="success",
        extracted_text=all_extracted_text or None,
        plan_trace=plan_trace,
        final_answer=final_answer,
        cost_estimate=estimate_cost(total_input_tokens, total_output_tokens),
        duration_seconds=round(duration, 2),
    )
