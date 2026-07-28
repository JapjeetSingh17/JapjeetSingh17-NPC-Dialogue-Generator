import os
import math
import shutil
import tempfile
import gradio as gr
from gradio import utils as gr_utils
from PIL import Image, ImageDraw, ImageFont

from .graph import npc_graph, MultiNPCState, NPC_ROSTER
from .config import settings


def copy_to_gradio_cache(filepath):
    """Copy an audio file into Gradio's internal cache directory so it can be served without 403 errors."""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        # Use Gradio's temp directory (hash-based) for file serving
        cache_dir = os.path.join(tempfile.gettempdir(), "gradio")
        os.makedirs(cache_dir, exist_ok=True)
        dest = os.path.join(cache_dir, os.path.basename(filepath))
        shutil.copy2(filepath, dest)
        return dest
    except Exception as e:
        print(f"[Cache Copy Error] {e}")
        return filepath

MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "map.png"))
NPC_IMG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "npc_default.png"))

DEFAULT_PLAYER_POS = (260, 260)
PROXIMITY_THRESHOLD = 110

def get_closest_npc(player_pos):
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

        draw.ellipse([nx - 90, ny - 90, nx + 90, ny + 90], outline=color, width=2)

        if npc_id == active_npc_id:
            draw.ellipse([nx - 24, ny - 24, nx + 24, ny + 24], fill="#facc15", outline="#ffffff", width=3)
        else:
            draw.ellipse([nx - 18, ny - 18, nx + 18, ny + 18], fill=color, outline="#ffffff", width=2)

        draw.rectangle([nx - 55, ny + 22, nx + 55, ny + 42], fill=(15, 23, 42, 220), outline=color)
        draw.text((nx - 48, ny + 24), npc["name"].split()[0], fill="#ffffff", font=small_font)

    px, py = player_pos
    draw.ellipse([px - 16, py - 16, px + 16, py + 16], fill="#22c55e", outline="#ffffff", width=3)
    draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill="#ffffff")

    draw.rectangle([px - 35, py - 38, px + 35, py - 20], fill=(34, 197, 94, 230), outline="#ffffff")
    draw.text((px - 28, py - 36), "PLAYER", fill="#ffffff", font=small_font)

    return img

def build_demo():
    npc_img = Image.open(NPC_IMG_PATH) if os.path.exists(NPC_IMG_PATH) else None

    with gr.Blocks(title="Brightwood RPG - Continuous Voice Dialogue World") as demo:
        game_state = gr.State(value={
            "player_pos": DEFAULT_PLAYER_POS,
            "conversations": {npc_id: [] for npc_id in NPC_ROSTER},
            "active_npc_id": None
        })

        gr.Markdown(
            """
            # 🗺️ Brightwood Real-Time NPC World
            ### Speak continuously: Click '🎙️ Start Speaking to Villager' or record speech to talk with villagers!
            """
        )

        with gr.Row():
            # Left Column: Map & Controls
            with gr.Column(scale=5):
                gr.Markdown("### 🎮 Brightwood Map & Movement")
                map_display = gr.Image(
                    value=render_game_map(DEFAULT_PLAYER_POS),
                    label="Brightwood Map (Approach colored dots to talk)",
                    interactive=False,
                    type="pil"
                )

                gr.Markdown("**🚶 Move Character:**")
                with gr.Row():
                    btn_up = gr.Button("⬆️ Move North")
                with gr.Row():
                    btn_left = gr.Button("⬅️ Move West")
                    btn_reset = gr.Button("🏠 Center Map")
                    btn_right = gr.Button("➡️ Move East")
                with gr.Row():
                    btn_down = gr.Button("⬇️ Move South")

                gr.Markdown("**📍 Teleport to Villagers:**")
                with gr.Row():
                    tp_town = gr.Button("Silas (Town Sq)")
                    tp_market = gr.Button("Barnaby (Market Sq)")
                    tp_library = gr.Button("Elena (Library)")
                    tp_docks = gr.Button("Lyra (Docks)")
                    tp_gate = gr.Button("Marcus (South Gate)")

            # Right Column: Real-Time Dialogue Panel
            with gr.Column(scale=4):
                gr.Markdown("### 🎙️ Real-Time Voice Conversation")
                
                proximity_banner = gr.Markdown(
                    "**🚶 EXPLORING:** Walk near a villager marker to start voice chat!"
                )

                npc_info_box = gr.Markdown(
                    "*No villager in range. Approach a colored dot on the map!*"
                )

                chatbot = gr.Chatbot(
                    label="Live Speech Dialogue History",
                    height=280
                )

                with gr.Row():
                    start_speaking_btn = gr.Button("🎙️ Start Speaking to Villager", variant="primary", scale=2)
                    clear_chat_btn = gr.Button("🗑️ Clear Log", variant="secondary", scale=1)

                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="🎙️ Live Voice Microphone Capture",
                    interactive=True
                )

                text_input = gr.Textbox(
                    placeholder="Type a message (Optional)...",
                    label="Text Input (Optional)",
                    interactive=True
                )

                npc_voice_output = gr.Audio(
                    label="🔊 NPC Spoken Voice Response (Streaming Autoplay)",
                    autoplay=True,
                    interactive=False
                )

        # Movement Handler
        def move_player(direction, current_state):
            px, py = current_state.get("player_pos", DEFAULT_PLAYER_POS)
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
                px, py = DEFAULT_PLAYER_POS

            new_pos = (px, py)
            new_map = render_game_map(new_pos)

            npc_id, npc_info, dist = get_closest_npc(new_pos)

            if npc_id:
                banner = f"### 🟢 IN RANGE: **{npc_info['name']}** ({npc_info['title']})  \n*Click '🎙️ Start Speaking to Villager' to talk continuously!*"
                info_text = f"**Role:** {npc_info['title']} at {npc_info['location']}  \n*Ready for real-time voice conversation.*"
                chat_history = []
                for msg in current_state["conversations"].get(npc_id, []):
                    if msg.type == "human":
                        chat_history.append({"role": "user", "content": msg.content})
                    elif msg.type == "ai":
                        chat_history.append({"role": "assistant", "content": msg.content})
            else:
                banner = "### 🚶 EXPLORING BRIGHTWOOD  \n*Move closer to one of the colored dots on the map to initiate voice chat.*"
                info_text = "*No villager currently in range.*"
                chat_history = []

            new_state = dict(current_state)
            new_state["player_pos"] = new_pos
            new_state["active_npc_id"] = npc_id

            return new_map, banner, info_text, chat_history, new_state

        def teleport_player(target_location, current_state):
            target_pos = DEFAULT_PLAYER_POS
            for npc in NPC_ROSTER.values():
                if npc["location"] == target_location:
                    target_pos = npc["pos"]
                    break

            return move_player("teleport", {**current_state, "player_pos": target_pos})

        # Speech Dialogue Handler
        def handle_talk(text, audio, current_state):
            # Determine if we have any input to process
            has_text = bool(text and text.strip())
            has_audio = bool(audio and os.path.exists(str(audio)))

            if not has_text and not has_audio:
                # No input provided - just return current state without error
                npc_id = current_state.get("active_npc_id")
                chat_history = []
                if npc_id:
                    for msg in current_state["conversations"].get(npc_id, []):
                        if msg.type == "human":
                            chat_history.append({"role": "user", "content": msg.content})
                        elif msg.type == "ai":
                            chat_history.append({"role": "assistant", "content": msg.content})
                banner = f"### 🟢 IN RANGE: **{NPC_ROSTER[npc_id]['name']}** - Record your voice or type a message!" if npc_id else "🚶 Move near a villager!"
                return (
                    chat_history,
                    None,
                    banner,
                    "",
                    current_state
                )

            npc_id = current_state.get("active_npc_id")
            if not npc_id:
                return (
                    [],
                    None,
                    "### ⚠️ Move closer to a villager on the map first!",
                    "",
                    current_state
                )

            npc_msgs = current_state["conversations"].get(npc_id, [])

            graph_input: MultiNPCState = {
                "npc_id": npc_id,
                "messages": npc_msgs,
                "user_audio_path": audio if has_audio else None,
                "user_text": text.strip() if has_text else "",
                "npc_text": "",
                "npc_audio_path": None,
                "player_pos": current_state.get("player_pos", DEFAULT_PLAYER_POS),
                "zombie_threat": "ACTIVE"
            }

            final_state = npc_graph.invoke(graph_input)

            updated_msgs = final_state["messages"]
            current_state["conversations"][npc_id] = updated_msgs

            chat_history = []
            for msg in updated_msgs:
                if msg.type == "human":
                    chat_history.append({"role": "user", "content": msg.content})
                elif msg.type == "ai":
                    chat_history.append({"role": "assistant", "content": msg.content})

            # Copy audio to Gradio's cache directory so it can be served properly
            audio_output = copy_to_gradio_cache(final_state.get("npc_audio_path"))

            return (
                chat_history,
                audio_output,
                f"### 🟢 TALKING WITH: **{NPC_ROSTER[npc_id]['name']}** - Record again to continue!",
                "",   # Clear text input
                current_state
            )

        def clear_npc_chat(current_state):
            npc_id = current_state.get("active_npc_id")
            if npc_id:
                current_state["conversations"][npc_id] = []
            return [], None, current_state

        # Wire Movement
        btn_up.click(fn=lambda st: move_player("up", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        btn_down.click(fn=lambda st: move_player("down", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        btn_left.click(fn=lambda st: move_player("left", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        btn_right.click(fn=lambda st: move_player("right", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        btn_reset.click(fn=lambda st: move_player("reset", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])

        # Wire Teleport
        tp_town.click(fn=lambda st: teleport_player("Town Square", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        tp_market.click(fn=lambda st: teleport_player("Market Square", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        tp_library.click(fn=lambda st: teleport_player("Library", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        tp_docks.click(fn=lambda st: teleport_player("Docks", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])
        tp_gate.click(fn=lambda st: teleport_player("South Gate", st), inputs=[game_state], outputs=[map_display, proximity_banner, npc_info_box, chatbot, game_state])

        # Output list does NOT include audio_input - microphone state is never touched by backend
        talk_outputs = [chatbot, npc_voice_output, proximity_banner, text_input, game_state]

        # Wire speech handlers
        start_speaking_btn.click(
            fn=handle_talk,
            inputs=[text_input, audio_input, game_state],
            outputs=talk_outputs
        )
        audio_input.stop_recording(
            fn=handle_talk,
            inputs=[text_input, audio_input, game_state],
            outputs=talk_outputs
        )
        text_input.submit(
            fn=handle_talk,
            inputs=[text_input, audio_input, game_state],
            outputs=talk_outputs
        )
        clear_chat_btn.click(
            fn=clear_npc_chat,
            inputs=[game_state],
            outputs=[chatbot, npc_voice_output, game_state]
        )

    return demo

