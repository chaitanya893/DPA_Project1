import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HF_TOKEN")
print(f"HF_TOKEN present: {bool(token and len(token) > 5)}", flush=True)

try:
    from pyannote.audio import Pipeline
    print("Imported pyannote.audio.Pipeline successfully.", flush=True)
    
    print("Loading pyannote/speaker-diarization-3.1...", flush=True)
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=token)
    print("Pyannote speaker-diarization-3.1 loaded successfully!", flush=True)
except Exception as e:
    print(f"Error loading pyannote: {type(e).__name__}: {e}", flush=True)
