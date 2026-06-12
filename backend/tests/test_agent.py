"""
Sample test cases from the assignment spec.
Run: pytest tests/ -v
"""
import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ─── Helpers ────────────────────────────────────────────────────────────────

def post_agent(query: str, files: list[tuple] = None, session_id: str = "test-session"):
    data = {"query": query, "session_id": session_id}
    return client.post("/api/agent/run", data=data, files=files or [])


def assert_success(resp):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["final_answer"] is not None
    assert len(body["plan_trace"]) > 0
    return body


# ─── Test Case 3 — Image with Code (OCR + Code Explanation) ─────────────────

def test_tc3_image_code_explain():
    """
    TC3: Image screenshot with code + 'Explain'
    Expected: OCR → detect language → explain + warn about bugs
    """
    # Create a minimal valid PNG (1×1 white pixel)
    import struct, zlib
    def make_png():
        def chunk(name, data):
            c = struct.pack('>I', len(data)) + name + data
            return c + struct.pack('>I', zlib.crc32(c[4:]) & 0xffffffff)
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        raw = b'\x00\xff\xff\xff'
        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        return sig + ihdr + idat + iend

    png_bytes = make_png()
    resp = post_agent(
        query="Explain this code",
        files=[("files", ("code_screenshot.png", io.BytesIO(png_bytes), "image/png"))],
        session_id="tc3",
    )
    assert resp.status_code == 200
    body = resp.json()
    # Should attempt OCR (even if it returns empty text from a blank image)
    tools_used = [s["tool"] for s in body["plan_trace"]]
    assert "ocr_tool" in tools_used, f"Expected ocr_tool in plan trace, got: {tools_used}"
    assert body["status"] in ("success", "needs_clarification")


# ─── Test Case 2 — PDF + Natural Language Query ──────────────────────────────

def test_tc2_pdf_action_items():
    """
    TC2: PDF with meeting notes + 'What are the action items?'
    Expected: PDF extraction → find and return action items only
    """
    # Minimal valid PDF with meeting notes text
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 200>>
stream
BT /F1 12 Tf 50 750 Td
(Meeting Notes - Q1 Planning) Tj
0 -20 Td (Action Items:) Tj
0 -20 Td (1. John to send report by Friday) Tj
0 -20 Td (2. Alice to schedule follow-up call) Tj
0 -20 Td (3. Bob to review budget proposal) Tj
ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000526 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
605
%%EOF"""

    resp = post_agent(
        query="What are the action items?",
        files=[("files", ("meeting_notes.pdf", io.BytesIO(pdf_content), "application/pdf"))],
        session_id="tc2",
    )
    body = assert_success(resp)
    tools_used = [s["tool"] for s in body["plan_trace"]]
    assert "pdf_parser" in tools_used, f"Expected pdf_parser in trace, got: {tools_used}"
    # Answer should reference action items
    answer_lower = body["final_answer"].lower()
    assert any(kw in answer_lower for kw in ["action", "john", "alice", "bob", "report", "schedule"]), \
        f"Expected action items in answer, got: {body['final_answer'][:300]}"


# ─── Conversational Answering ─────────────────────────────────────────────────

def test_conversational_answer():
    """
    General conversational question — should return a friendly, helpful response.
    """
    resp = post_agent(
        query="What is machine learning in simple terms?",
        session_id="tc-conv",
    )
    body = assert_success(resp)
    assert len(body["final_answer"]) > 50


# ─── Summarization ────────────────────────────────────────────────────────────

def test_summarization_format():
    """
    Summarization: output must include 1-line summary, 3 bullets, 5-sentence summary.
    """
    resp = post_agent(
        query="Summarize this text: Artificial intelligence is transforming industries. "
              "Machine learning enables computers to learn from data. Deep learning uses neural "
              "networks for complex tasks. AI is used in healthcare, finance, and transportation. "
              "The technology continues to advance rapidly. Ethical considerations are important.",
        session_id="tc-sum",
    )
    body = assert_success(resp)
    answer = body["final_answer"]
    # Should contain summary indicators
    assert any(kw in answer.lower() for kw in ["summary", "bullet", "•", "-", "1.", "*"]), \
        f"Expected summary format in answer: {answer[:500]}"


# ─── Sentiment Analysis ───────────────────────────────────────────────────────

def test_sentiment_analysis():
    """
    Sentiment analysis: should return label + confidence + justification.
    """
    resp = post_agent(
        query="Analyze the sentiment of: 'This product is absolutely terrible. "
              "I wasted my money. The quality is poor and customer service was rude.'",
        session_id="tc-sent",
    )
    body = assert_success(resp)
    answer_lower = body["final_answer"].lower()
    assert any(kw in answer_lower for kw in ["negative", "sentiment", "confidence"]), \
        f"Expected sentiment result, got: {body['final_answer'][:300]}"


# ─── Code Explanation ─────────────────────────────────────────────────────────

def test_code_explanation():
    """
    Code explanation: should detect language, explain logic, identify bugs, time complexity.
    """
    resp = post_agent(
        query="""Explain this code:
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
""",
        session_id="tc-code",
    )
    body = assert_success(resp)
    answer_lower = body["final_answer"].lower()
    assert any(kw in answer_lower for kw in ["bubble", "sort", "python", "complexity", "o(n"]), \
        f"Expected code explanation, got: {body['final_answer'][:400]}"


# ─── Health Check ─────────────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── History Endpoint ─────────────────────────────────────────────────────────

def test_history_endpoint():
    resp = client.get("/api/agent/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── Empty Query Validation ───────────────────────────────────────────────────

def test_empty_query_rejected():
    resp = client.post("/api/agent/run", data={"query": "", "session_id": "test"})
    assert resp.status_code == 422 or resp.status_code == 400


# ─── YouTube URL Detection ────────────────────────────────────────────────────

def test_youtube_url_detection():
    """
    Agent should detect YouTube URL in text and attempt transcript fetch.
    """
    from app.tools.youtube_tool import extract_youtube_url, get_video_id
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    found = extract_youtube_url(f"Check out this video: {test_url}")
    assert found == test_url
    vid_id = get_video_id(test_url)
    assert vid_id == "dQw4w9WgXcQ"


# ─── OCR Tool Unit Test ───────────────────────────────────────────────────────

def test_ocr_tool_invalid_image():
    """
    OCR tool should handle invalid image bytes gracefully.
    """
    from app.tools.ocr_tool import run_ocr
    result = run_ocr(b"not an image", "test.png")
    assert result["success"] is False
    assert "error" in result


# ─── PDF Tool Unit Test ───────────────────────────────────────────────────────

def test_pdf_tool_invalid_pdf():
    """
    PDF tool should handle invalid PDF bytes gracefully.
    """
    from app.tools.pdf_tool import extract_pdf_text
    result = extract_pdf_text(b"not a pdf", "test.pdf")
    assert result["success"] is False
    assert "error" in result


# ─── Cost Estimate Returned ───────────────────────────────────────────────────

def test_cost_estimate_present():
    """
    Agent should return a cost estimate string with every response.
    """
    resp = post_agent("Hello!", session_id="tc-cost")
    body = resp.json()
    assert body.get("cost_estimate") is not None
    assert "$" in body["cost_estimate"]


# ─── Duration Returned ────────────────────────────────────────────────────────

def test_duration_present():
    """
    Agent should return duration_seconds with every response.
    """
    resp = post_agent("Hello!", session_id="tc-dur")
    body = resp.json()
    assert body.get("duration_seconds") is not None
    assert body["duration_seconds"] > 0
