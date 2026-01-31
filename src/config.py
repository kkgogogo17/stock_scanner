from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY")


if not TIINGO_API_KEY:
    # Warning: In a real app we might want to log this or fail if essential
    pass

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DAILY_DATA_DIR = DATA_DIR / "daily"

# Ensure directories exist
DAILY_DATA_DIR.mkdir(parents=True, exist_ok=True)
