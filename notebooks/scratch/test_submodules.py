import sys

for mod in [
    'torch',
    'scipy',
    'torchaudio',
    'pytorch_lightning',
    'lightning',
    'pyannote.core',
    'pyannote.database',
    'pyannote.metrics',
    'pyannote.pipeline',
    'pyannote.audio.core',
    'pyannote.audio.pipelines',
    'pyannote.audio'
]:
    print(f"Importing {mod}...", flush=True)
    try:
        __import__(mod)
        print(f"  {mod} OK", flush=True)
    except Exception as e:
        print(f"  {mod} ERROR: {e}", flush=True)

print("Done checking modules!", flush=True)
