import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

UNIVERSE_CSV_PATH = CONFIG_DIR / "universe.csv"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
REFERENCE_DIR = DATA_DIR / "reference"
SAMPLES_DIR = DATA_DIR / "samples"

# Database connection URL
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'earnings_call.db'}")

# HTTP Scraper & Compliance Settings
USER_AGENT = os.getenv(
    "USER_AGENT",
    "EarningsCallCaptureBot/1.0 (Contact: research_intern@domain.com)"
)
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY_SECONDS", "2.5"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))
