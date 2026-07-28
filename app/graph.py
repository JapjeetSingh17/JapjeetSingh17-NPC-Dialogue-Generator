import os
import re
import tempfile
from typing import TypedDict, List, Optional, Dict, Tuple, Any
from gtts import gTTS

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from groq import Groq
from langgraph.graph import StateGraph, START, END

from .config import settings

NPC_ROSTER: Dict[str, Dict[str, Any]] = {
    "elena": {
        "name": "Elena the Arcane Weaver",
        "title": "Mage & Lorekeeper",
        "location": "Library",
        "pos": (720, 280),
        "color": "#3b82f6",
        "system_prompt": """You are Elena, an Arcane Mage residing in Brightwood Library during the Zombie Outbreak.
You grew up in the High Citadel studying ancient relics and elemental magic before coming to Brightwood.
When the user talks to you, act like a real, living person in this world. Explain your background, how you grew up, what you do at the library, and share insights about the undead uprising.
IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "marcus": {
        "name": "Captain Marcus",
        "title": "Veteran Guard Captain",
        "location": "South Gate",
        "pos": (180, 720),
        "color": "#ef4444",
        "system_prompt": """You are Captain Marcus, a gruff veteran guard stationed at Brightwood South Gate.
Born and raised right here at the South Gate, son of a watch captain. You've protected Brightwood your whole life.
When the user talks to you, act like a real person. Talk about your childhood growing up near the gatehouse, your soldier duties, and current defense efforts against the zombie horde.
IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "barnaby": {
        "name": "Barnaby the Blacksmith",
        "title": "Master Craftsman & Trader",
        "location": "Market Square",
        "pos": (400, 380),
        "color": "#f59e0b",
        "system_prompt": """You are Barnaby, the master blacksmith in Market Square.
You grew up in your father's smithy in Market Square, hammering iron since age seven.
When the user talks to you, act like a real person. Share stories of your childhood in the forge, what weapons and armor work best against zombies, and how market life used to be.
IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "silas": {
        "name": "Old Silas",
        "title": "Village Herbalist & Elder",
        "location": "Town Square",
        "pos": (220, 180),
        "color": "#10b981",
        "system_prompt": """You are Old Silas, the village herbalist and elder in Town Square.
Raised in the surrounding Brightwood forest, you have lived in this village for over 60 years.
When the user talks to you, act like a real person. Share tales of how you grew up foraging herbs in the woods, village history, and herbal remedies against infection.
IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "lyra": {
        "name": "Lyra the Fisherwoman",
        "title": "River Scout & Navigator",
        "location": "Docks",
        "pos": (580, 560),
        "color": "#8b5cf6",
        "system_prompt": """You are Lyra, a sharp river scout and fisherwoman at Brightwood Docks.
You grew up on wooden riverboats with your family, learning every bend of the river that splits Brightwood.
When the user talks to you, act like a real person. Explain your childhood on the water, your fishing scout work, and how river routes offer escape from zombies.
IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    }
}

class MultiNPCState(TypedDict):
    npc_id: str
    messages: List[BaseMessage]
    user_audio_path: Optional[str]
    user_text: str
    npc_text: str
    npc_audio_path: Optional[str]
    player_pos: Tuple[int, int]
    zombie_threat: str

def clean_text_for_tts(text: str) -> str:
    """Cleans text so Text-to-Speech synthesizes the entire response fully without stopping."""
    if not text:
        return ""
    
    # Strip character prefixes if present
    if "]:" in text:
        text = text.split("]:", 1)[1]
    elif ":" in text and len(text.split(":", 1)[0]) < 25:
        text = text.split(":", 1)[1]
        
    # Remove bracketed actions [looks around], asterisk actions *nods*, and special symbols
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'[*#_`~]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def stt_and_input_processor(state: MultiNPCState) -> dict:
    """Processes user input cleanly. Transcribes microphone voice input if provided."""
    user_audio = state.get("user_audio_path")
    user_text = state.get("user_text", "").strip()

    if not user_text and user_audio and os.path.exists(user_audio):
        try:
            api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
            if api_key:
                client = Groq(api_key=api_key)
                with open(user_audio, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(user_audio, file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                user_text = str(transcription).strip()
        except Exception as e:
            print(f"[Groq Whisper STT Error] {e}")

    if not user_text:
        user_text = "Hello!"

    updated_messages = list(state.get("messages", []))
    updated_messages.append(HumanMessage(content=user_text))

    return {
        "user_text": user_text,
        "messages": updated_messages
    }

def npc_reasoning_node(state: MultiNPCState) -> dict:
    """Invokes LangChain ChatGroq (llama-3.1-8b-instant) for real-time NPC dialogue."""
    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    npc_id = state.get("npc_id", "elena")
    npc_info = NPC_ROSTER.get(npc_id, NPC_ROSTER["elena"])

    if not api_key:
        npc_text = f"[{npc_info['name']}]: I cannot hear you. (Please set your GROQ_API_KEY in .env!)"
    else:
        try:
            llm = ChatGroq(
                model=settings.groq_model,
                api_key=api_key,
                temperature=0.7,
                max_tokens=300
            )
            sys_msg = SystemMessage(content=npc_info["system_prompt"])
            prompt_messages = [sys_msg] + state.get("messages", [])
            
            response = llm.invoke(prompt_messages)
            npc_text = response.content
        except Exception as e:
            npc_text = f"[{npc_info['name']}]: (Error communicating: {str(e)})"

    updated_messages = list(state.get("messages", []))
    updated_messages.append(AIMessage(content=npc_text))

    return {
        "npc_text": npc_text,
        "messages": updated_messages
    }

import time

def tts_node(state: MultiNPCState) -> dict:
    """Converts NPC response text to speech audio file using gTTS, saved to /tmp for Vercel serverless execution."""
    npc_text = state.get("npc_text", "")
    audio_path = None
    
    if npc_text:
        try:
            speech_text = clean_text_for_tts(npc_text)
            if speech_text:
                tmp_dir = tempfile.gettempdir()
                audio_name = f"npc_speech_{int(time.time() * 1000)}.mp3"
                audio_path = os.path.join(tmp_dir, audio_name)
                tts = gTTS(text=speech_text, lang='en', slow=False)
                tts.save(audio_path)
        except Exception as e:
            print(f"[TTS Error] {e}")

    return {
        "npc_audio_path": audio_path
    }

def state_update_node(state: MultiNPCState) -> dict:
    return {}

# Build LangGraph workflow
workflow = StateGraph(MultiNPCState)

workflow.add_node("input_processor", stt_and_input_processor)
workflow.add_node("npc_brain", npc_reasoning_node)
workflow.add_node("tts_generator", tts_node)
workflow.add_node("state_updater", state_update_node)

workflow.add_edge(START, "input_processor")
workflow.add_edge("input_processor", "npc_brain")
workflow.add_edge("npc_brain", "tts_generator")
workflow.add_edge("tts_generator", "state_updater")
workflow.add_edge("state_updater", END)

npc_graph = workflow.compile()
