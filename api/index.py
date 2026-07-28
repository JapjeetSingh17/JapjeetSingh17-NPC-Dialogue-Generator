import os

# Configure Gradio temporary directory and allowed paths BEFORE any Gradio import
os.environ["GRADIO_TEMP_DIR"] = "/tmp"
os.environ["GRADIO_ALLOWED_PATHS"] = "/tmp"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from app.ui import build_demo

app = FastAPI(title="Brightwood RPG NPC Dialogue Engine")

# Add CORS middleware to allow all origins (needed for Vercel preview deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dedicated endpoint to serve audio files from /tmp, bypassing Gradio's file security
@app.get("/serve_audio/{filename:path}")
async def serve_audio(filename: str):
    filepath = os.path.join("/tmp", filename)
    if os.path.exists(filepath) and filepath.startswith("/tmp"):
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
        )
    return {"error": "File not found"}, 404

# Build Gradio demo interface
demo = build_demo()

# Mount Gradio app onto FastAPI with /tmp in allowed_paths
app = gr.mount_gradio_app(app, demo, path="/", allowed_paths=["/tmp"])
