#!/usr/bin/env python3
"""
Push project files to GitHub using the REST API.
Usage: GITHUB_PERSONAL_ACCESS_TOKEN=xxx python scripts/push_to_github.py
"""
import os, base64, json, time
import urllib.request, urllib.error

TOKEN = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
OWNER = "mohawwwk"
REPO  = "nexus-agent"
BASE  = f"https://api.github.com/repos/{OWNER}/{REPO}"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
    "Accept":        "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def gh(method, path, body=None):
    url  = BASE + path if path.startswith("/") else path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        print(f"  HTTP {e.code} for {method} {url}: {content[:200]}")
        return json.loads(content)

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def upsert_file(repo_path, local_path, message):
    """Create or update a single file in the repo."""
    existing = gh("GET", f"/contents/{repo_path}")
    sha = existing.get("sha")
    body = {
        "message": message,
        "content": encode_file(local_path),
    }
    if sha:
        body["sha"] = sha
    result = gh("PUT", f"/contents/{repo_path}", body)
    status = "updated" if sha else "created"
    print(f"  {status}: {repo_path}")
    time.sleep(0.3)  # rate limit courtesy
    return result

# Files to push: (repo_path, local_path, commit_message)
FILES = [
    # Root docs
    ("README.md",                    "artifacts/fastapi-backend/README.md",            "docs: full README with setup and API docs"),
    ("docs/architecture.svg",        "docs/architecture.svg",                          "docs: architecture diagram (assignment rubric deliverable)"),
    ("Dockerfile",                   "artifacts/fastapi-backend/Dockerfile",           "docker: production-ready Dockerfile"),
    ("requirements.txt",             "artifacts/fastapi-backend/requirements.txt",     "backend: Python dependencies"),
    (".env.example",                 "artifacts/fastapi-backend/.env.example",         "config: example env file") if os.path.exists("artifacts/fastapi-backend/.env.example") else None,

    # Backend
    ("backend/__init__.py",          "artifacts/fastapi-backend/app/__init__.py",      "backend: app init"),
    ("backend/main.py",              "artifacts/fastapi-backend/app/main.py",          "backend: FastAPI app entrypoint"),
    ("backend/agent.py",             "artifacts/fastapi-backend/app/agent.py",         "backend: agentic pipeline"),
    ("backend/models.py",            "artifacts/fastapi-backend/app/models.py",        "backend: Pydantic models"),
    ("backend/config.py",            "artifacts/fastapi-backend/app/config.py",        "backend: settings"),
    ("backend/routers/__init__.py",  "artifacts/fastapi-backend/app/routers/__init__.py", "backend: routers init"),
    ("backend/routers/agent.py",     "artifacts/fastapi-backend/app/routers/agent.py", "backend: agent routes"),
    ("backend/tools/__init__.py",    "artifacts/fastapi-backend/app/tools/__init__.py","backend: tools init"),
    ("backend/tools/ocr_tool.py",    "artifacts/fastapi-backend/app/tools/ocr_tool.py","backend: OCR tool (pytesseract)"),
    ("backend/tools/pdf_tool.py",    "artifacts/fastapi-backend/app/tools/pdf_tool.py","backend: PDF parser (pypdf)"),
    ("backend/tools/audio_tool.py",  "artifacts/fastapi-backend/app/tools/audio_tool.py","backend: audio transcriber (Groq Whisper)"),
    ("backend/tools/youtube_tool.py","artifacts/fastapi-backend/app/tools/youtube_tool.py","backend: YouTube transcript fetcher"),

    # Tests
    ("backend/tests/__init__.py",    "artifacts/fastapi-backend/tests/__init__.py",    "tests: init"),
    ("backend/tests/conftest.py",    "artifacts/fastapi-backend/tests/conftest.py",    "tests: pytest config"),
    ("backend/tests/test_agent.py",  "artifacts/fastapi-backend/tests/test_agent.py",  "tests: 14 test cases"),
]

def main():
    print(f"Pushing to https://github.com/{OWNER}/{REPO}\n")
    for entry in FILES:
        if entry is None:
            continue
        repo_path, local_path, message = entry
        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_path}")
            continue
        try:
            upsert_file(repo_path, local_path, message)
        except Exception as e:
            print(f"  ERROR {repo_path}: {e}")
    print("\nDone! Repo: https://github.com/mohawwwk/nexus-agent")

if __name__ == "__main__":
    main()
