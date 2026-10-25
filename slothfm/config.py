"""Where Sloth FM keeps things, and which open models it uses. Everything stays on this machine."""
import os
from pathlib import Path

HOME = Path(os.environ.get("SLOTHFM_HOME", Path.home() / ".slothfm"))
DB = HOME / "slothfm.db"
OUT = HOME / "mornings"
OLLAMA = os.environ.get("SLOTHFM_OLLAMA", "http://127.0.0.1:11434")
MODEL = os.environ.get("SLOTHFM_MODEL", "gemma3:4b")
KOKORO_DIR = Path(os.environ.get("SLOTHFM_KOKORO", HOME / "kokoro"))
VOICE = os.environ.get("SLOTHFM_VOICE", "bm_george")    # an unhurried British voice, Apache-2.0 Kokoro
SPEED = float(os.environ.get("SLOTHFM_SPEED", "0.92"))  # a little slower than normal speech, on purpose
PACE_SECONDS = int(os.environ.get("SLOTHFM_PACE", "3"))  # rest between notifications, so the laptop stays cool
DAYS = int(os.environ.get("SLOTHFM_DAYS", "14"))
TASK_QUEUE = "sloth-fm"
