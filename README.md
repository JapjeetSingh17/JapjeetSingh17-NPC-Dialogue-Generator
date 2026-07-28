# Real-Time Multi-Agent NPC Dialogue Engine

A stateful, graph-based conversational intelligence framework designed for non-player characters (NPCs) in interactive RPG environments. The architecture replaces traditional static dialogue trees with real-time autonomous LLM reasoning agents, speech-to-text input processing, text-to-speech multimodal synthesis, and spatial proximity state machines.

---

## Live Deployment

[Insert Vercel Deployment Link Here](https://your-vercel-deployment-link.vercel.app)

---

## System Architecture

The framework leverages a Directed Acyclic Graph (DAG) state machine managed via **LangGraph** to coordinate multi-turn conversational turns, context retention, and state transitions across distinct NPC entities.

```
+------------------+     +------------------------+     +-----------------------------+
| Microphone Input | --> | Groq Whisper STT Engine| --> | LangGraph State Graph Nodes |
+------------------+     +------------------------+     +-----------------------------+
                                                                      |
                                                                      v
+------------------+     +------------------------+     +-----------------------------+
| Client Voice Output| <--| gTTS Speech Synthesizer| <-- | Groq Llama 3.1 Inference    |
+------------------+     +------------------------+     +-----------------------------+
```

### Core Execution Flow

1. **Spatial Proximity Detection**: Dynamic distance calculation determines proximity between the player coordinate state $(x_p, y_p)$ and target NPC spatial coordinates $(x_{npc}, y_{npc})$.
2. **Multimodal Audio Processing**: Speech input captured from client audio hardware is processed via Groq's `whisper-large-v3-turbo` model for high-throughput speech-to-text transcription.
3. **Graph State Transition**: Transcribed text and contextual prompt history pass through the `StateGraph` compilation node.
4. **Autonomous Character Reasoning**: `langchain-groq` invokes `llama-3.1-8b-instant` with parameterized system prompt persona constraints, context history, and spatial parameters.
5. **Speech Synthesis Execution**: Response string outputs are processed through a sanitization filter to strip non-verbal tags before generating timestamp-isolated MP3 audio streams via `gTTS`.

---

## Technical Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language Runtime** | Python 3.14+ | Core application execution environment |
| **Orchestration** | LangGraph | Stateful multi-agent graph architecture |
| **LLM Interface** | LangChain / ChatGroq | Framework for language model integration |
| **Inference Model** | Llama 3.1 8B Instant | Ultra-low latency LLM inference via Groq Cloud |
| **Speech-to-Text** | Whisper Large v3 Turbo | Neural automatic speech recognition (ASR) |
| **Text-to-Speech** | gTTS | Audio synthesis pipeline for output stream generation |
| **User Interface** | Gradio 6.0+ | Server-rendered Web interface for audio/spatial control |
| **Image Processing** | Pillow (PIL) | Dynamic spatial map rendering and token overlay |
| **Deployment Server** | FastAPI / Vercel Serverless | WSGI/ASGI application wrapper for serverless functions |

---

## Repository Structure

```
.
├── api/
│   └── index.py            # Vercel serverless FastAPI entrypoint
├── app/
│   ├── config.py           # Application settings and environment schema
│   ├── graph.py            # LangGraph State Graph definitions and node functions
│   ├── main.py             # Local development server initialization
│   └── ui.py               # Gradio interface layout and event listener binding
├── static/
│   ├── map.png             # Environment spatial terrain map
│   └── npc_default.png     # Character sprite reference asset
├── .gitignore              # Artifact and environment exclusion rules
├── pyproject.toml          # Package workspace definition
├── requirements.txt        # Production dependency manifest
├── vercel.json             # Vercel deployment and routing specification
└── README.md               # Technical project documentation
```

---

## Local Setup Instructions

### Prerequisites

- Python 3.11 or higher
- `uv` package manager (`pip install uv`)
- Valid Groq API key (`GROQ_API_KEY`)

### Environment Setup

1. Clone repository:
   ```bash
   git clone https://github.com/JapjeetSingh17/JapjeetSingh17-NPC-Dialogue-Generator.git
   cd JapjeetSingh17-NPC-Dialogue-Generator
   ```

2. Create virtual environment and install dependencies:
   ```bash
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   ```

4. Launch local application server:
   ```bash
   uv run python -m app.main
   ```
   Access the local Web UI at `http://127.0.0.1:7860`.

---

## Serverless Deployment via Vercel

The application is pre-configured for Vercel serverless execution via `@vercel/python` and FastAPI (`api/index.py`).

1. Connect the GitHub repository to the Vercel platform.
2. In Project Settings, declare the following Environment Variables:
   - `GROQ_API_KEY`: Groq API authorization key
   - `GROQ_MODEL`: Set to `llama-3.1-8b-instant`
3. Execute deployment. The entrypoint `api/index.py` handles route redirection to the FastAPI-wrapped Gradio instance.
