"""
Al Shifa Medical Group — AI Chatbot Backend
FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import chat as chat_router
from routes import voice as voice_router
from services import llm_service, rag_service

load_dotenv(override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("WARNING: GEMINI_API_KEY is not set in backend/.env")
        print("  Get a free key at: https://aistudio.google.com/app/apikey")

    print("[Startup] Initializing RAG service...")
    rag_service.initialize()

    print("[Startup] Initializing LLM service...")
    llm_service.initialize()

    print("[Startup] All services ready!")
    yield
    print("[Shutdown] Shutting down...")


app = FastAPI(
    title="Al Shifa Medical Group - AI Chatbot API",
    description="AI-powered bilingual (Arabic/English) medical chatbot for Al Shifa Medical Group.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(chat_router.router, prefix="/api", tags=["Chat"])
app.include_router(voice_router.router, prefix="/api", tags=["Voice"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "Al Shifa Medical Group AI Chatbot",
        "version": "1.0.0",
    }


@app.get("/api/hospital-data", tags=["Hospital"])
async def get_hospital_data():
    """Return the hospital group data (branches, specializations, doctors)."""
    return rag_service.get_hospital_data()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
