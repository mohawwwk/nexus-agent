import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agent as agent_router

app = FastAPI(
    title="Agentic AI Assistant",
    description="Multi-modal agentic pipeline: Text, Image, PDF, Audio → Intelligent analysis",
    version="1.0.0",
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/healthz")
async def health():
    return {"status": "ok"}


app.include_router(agent_router.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Agentic AI Assistant API — see /docs for OpenAPI docs"}
