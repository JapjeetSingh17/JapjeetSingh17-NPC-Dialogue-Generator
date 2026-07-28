import os
from fastapi import FastAPI
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from app.ui import build_demo

app = FastAPI(title="Brightwood RPG NPC Dialogue Engine")

# Build Gradio demo interface
demo = build_demo()

# Mount Gradio app onto FastAPI app at root / with allowed_paths for serverless temp & static files
app = gr.mount_gradio_app(app, demo, path="/", allowed_paths=["/tmp", "static", "."])
