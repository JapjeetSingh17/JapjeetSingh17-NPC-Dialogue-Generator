"""
Local development entry point.
Run: python -m uvicorn app.main:app --reload --port 7860
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Import the FastAPI app from the API module
from api.index import app

if __name__ == "__main__":
    import uvicorn
    print("Launching Brightwood RPG NPC Dialogue Engine (local dev)...")
    uvicorn.run("api.index:app", host="127.0.0.1", port=7860, reload=True)
