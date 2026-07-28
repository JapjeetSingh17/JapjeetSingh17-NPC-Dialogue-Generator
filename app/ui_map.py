"""
Brightwood RPG — Map Rendering & NPC Proximity Detection
Separated from the UI layer for use by the FastAPI REST backend.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

from .graph import NPC_ROSTER

MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "map.png"))
DEFAULT_PLAYER_POS = (260, 260)
PROXIMITY_THRESHOLD = 110


def get_closest_npc(player_pos):
    """Find the closest NPC to the player within PROXIMITY_THRESHOLD distance."""
    px, py = player_pos
    closest_npc = None
    min_dist = float("inf")

    for npc_id, npc in NPC_ROSTER.items():
        nx, ny = npc["pos"]
        dist = math.hypot(px - nx, py - ny)
        if dist < min_dist:
            min_dist = dist
            closest_npc = (npc_id, npc, dist)

    if closest_npc and min_dist <= PROXIMITY_THRESHOLD:
        return closest_npc[0], closest_npc[1], min_dist
    return None, None, min_dist


def render_game_map(player_pos):
    """Render the Brightwood map with NPC markers and the player dot."""
    if not os.path.exists(MAP_PATH):
        img = Image.new("RGB", (800, 600), color=(40, 44, 52))
    else:
        img = Image.open(MAP_PATH).convert("RGBA")

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    active_npc_id, _, _ = get_closest_npc(player_pos)

    for npc_id, npc in NPC_ROSTER.items():
        nx, ny = npc["pos"]
        color = npc["color"]

        # Proximity radius circle
        draw.ellipse([nx - 90, ny - 90, nx + 90, ny + 90], outline=color, width=2)

        # NPC dot (highlighted if active)
        if npc_id == active_npc_id:
            draw.ellipse([nx - 24, ny - 24, nx + 24, ny + 24], fill="#facc15", outline="#ffffff", width=3)
        else:
            draw.ellipse([nx - 18, ny - 18, nx + 18, ny + 18], fill=color, outline="#ffffff", width=2)

        # NPC name label
        draw.rectangle([nx - 55, ny + 22, nx + 55, ny + 42], fill=(15, 23, 42, 220), outline=color)
        draw.text((nx - 48, ny + 24), npc["name"].split()[0], fill="#ffffff", font=small_font)

    # Player marker
    px, py = player_pos
    draw.ellipse([px - 16, py - 16, px + 16, py + 16], fill="#22c55e", outline="#ffffff", width=3)
    draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill="#ffffff")

    draw.rectangle([px - 35, py - 38, px + 35, py - 20], fill=(34, 197, 94, 230), outline="#ffffff")
    draw.text((px - 28, py - 36), "PLAYER", fill="#ffffff", font=small_font)

    return img
