import sys
print("Python version:", sys.version, flush=True)

print("Importing torch...", flush=True)
import torch
print("Torch version:", torch.__version__, flush=True)

print("Importing soundfile...", flush=True)
import soundfile as sf
print("Soundfile ok", flush=True)

print("Importing faster_whisper...", flush=True)
from faster_whisper import WhisperModel
print("Faster-whisper ok", flush=True)

print("Importing pyannote.audio...", flush=True)
try:
    from pyannote.audio import Pipeline
    print("Pyannote Pipeline imported successfully!", flush=True)
except Exception as e:
    print("Pyannote import error:", e, flush=True)
