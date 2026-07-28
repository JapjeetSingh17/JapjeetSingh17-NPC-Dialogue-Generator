import os

os.environ["GRADIO_TEMP_DIR"] = "/tmp"
os.environ["GRADIO_ALLOWED_PATHS"] = "/tmp,static,."

from dotenv import load_dotenv

load_dotenv()

from .ui import build_demo

demo = build_demo()

if __name__ == "__main__":
    print("🧟 Launching Brightwood Zombie RPG LangGraph Application...")
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
