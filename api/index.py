"""
Brightwood RPG — FastAPI Backend
Serves static frontend and REST API endpoints for the LangGraph NPC dialogue pipeline.
"""

import os
import io
import json
import math
import time
import tempfile

os.environ["GRADIO_TEMP_DIR"] = "/tmp"

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from app.graph import npc_graph, NPC_ROSTER, MultiNPCState
from app.ui_map import render_game_map, get_closest_npc, PROXIMITY_THRESHOLD

# ==================== App Setup ====================
app = FastAPI(title="Brightwood RPG NPC Dialogue Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory for CSS, JS, map, and assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# ==================== Static Files ====================
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), media_type="text/html")


@app.get("/static/{filepath:path}")
async def serve_static(filepath: str):
    full_path = os.path.join(STATIC_DIR, filepath)
    if os.path.exists(full_path) and not os.path.isdir(full_path):
        # Determine media type
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        media_types = {
            "css": "text/css",
            "js": "application/javascript",
            "png": "image/png",
            "jpg": "image/jpeg",
            "webp": "image/webp",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
        }
        return FileResponse(full_path, media_type=media_types.get(ext, "application/octet-stream"))
    return JSONResponse({"error": "Not found"}, status_code=404)


# ==================== API: Map Rendering ====================
@app.get("/api/map")
async def api_map(px: int = 260, py: int = 260):
    """Render the game map with the player at the given position and return as PNG."""
    img = render_game_map((px, py))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


# ==================== API: Movement ====================
@app.post("/api/move")
async def api_move(data: dict):
    """Move the player in a direction and return new position + active NPC info."""
    direction = data.get("direction", "reset")
    px, py = data.get("player_pos", [260, 260])
    step = 50

    if direction == "up":
        py = max(40, py - step)
    elif direction == "down":
        py = min(760, py + step)
    elif direction == "left":
        px = max(40, px - step)
    elif direction == "right":
        px = min(960, px + step)
    elif direction == "reset":
        px, py = 260, 260

    npc_id, npc_info, dist = get_closest_npc((px, py))

    active_npc = None
    if npc_id:
        active_npc = {
            "id": npc_id,
            "name": npc_info["name"],
            "title": npc_info["title"],
            "location": npc_info["location"],
        }

    return {
        "player_pos": [px, py],
        "active_npc": active_npc,
    }


# ==================== API: Teleport ====================
@app.post("/api/teleport")
async def api_teleport(data: dict):
    """Teleport the player to a named location."""
    location = data.get("location", "Town Square")
    target_pos = [260, 260]

    for npc in NPC_ROSTER.values():
        if npc["location"] == location:
            target_pos = list(npc["pos"])
            break

    npc_id, npc_info, dist = get_closest_npc(tuple(target_pos))

    active_npc = None
    if npc_id:
        active_npc = {
            "id": npc_id,
            "name": npc_info["name"],
            "title": npc_info["title"],
            "location": npc_info["location"],
        }

    return {
        "player_pos": target_pos,
        "active_npc": active_npc,
    }


# ==================== API: Talk (Voice + Text) ====================
@app.post("/api/talk")
async def api_talk(
    npc_id: str = Form(...),
    messages: str = Form("[]"),
    player_pos: str = Form("[260, 260]"),
    user_text: str = Form(""),
    audio: UploadFile = File(None),
):
    """
    Process user input (voice or text) through the LangGraph pipeline.
    Returns NPC response text and audio URL.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    # Parse conversation history from client
    msg_list = json.loads(messages)
    langchain_msgs = []
    for m in msg_list:
        if m["role"] == "user":
            langchain_msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            langchain_msgs.append(AIMessage(content=m["content"]))

    pos = json.loads(player_pos)

    # Save uploaded audio to temp file if provided
    audio_path = None
    if audio and audio.filename:
        tmp_dir = tempfile.gettempdir()
        audio_ext = audio.filename.rsplit(".", 1)[-1] if "." in audio.filename else "webm"
        audio_path = os.path.join(tmp_dir, f"user_audio_{int(time.time() * 1000)}.{audio_ext}")
        content = await audio.read()
        with open(audio_path, "wb") as f:
            f.write(content)

    # Invoke LangGraph pipeline
    graph_input: MultiNPCState = {
        "npc_id": npc_id,
        "messages": langchain_msgs,
        "user_audio_path": audio_path,
        "user_text": user_text or "",
        "npc_text": "",
        "npc_audio_path": None,
        "player_pos": tuple(pos),
        "zombie_threat": "ACTIVE",
    }

    final_state = npc_graph.invoke(graph_input)

    # Build audio URL
    audio_url = None
    npc_audio = final_state.get("npc_audio_path")
    if npc_audio and os.path.exists(npc_audio):
        audio_filename = os.path.basename(npc_audio)
        audio_url = f"/audio/{audio_filename}"

    # Extract what the user said (from STT or direct text)
    user_said = final_state.get("user_text", user_text)

    return {
        "npc_text": final_state.get("npc_text", ""),
        "user_text": user_said,
        "audio_url": audio_url,
    }


# ==================== API: Serve Audio Files ====================
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated TTS audio files from /tmp."""
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath) and filename.startswith("npc_speech_"):
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
        )
    return JSONResponse({"error": "Audio file not found"}, status_code=404)
