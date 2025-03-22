import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Database settings
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(DATA_DIR / "papers.db"))

# ArXiv API settings
ARXIV_KEYWORDS = [
    "red teaming",
    "adversarial attack",
    "jailbreak",
    "prompt injection",
    "model extraction",
    "data poisoning",
    "backdoor attack",
    "privacy attack",
    "model stealing",
    "LLM security",
    "AI security",
    "AI safety",
    "AI alignment",
    "reward hacking"
]
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "100"))

# LLM settings
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()  # "anthropic" or "openai"
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-3-haiku-20240307" if LLM_PROVIDER == "anthropic" else "gpt-4o-mini")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5"))
PROCESSING_DELAY = int(os.environ.get("PROCESSING_DELAY", "2"))  # seconds between batches

# Email settings
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "").split(",")
EMAIL_SUBJECT_PREFIX = "AI Red Teaming Research Digest -"
MIN_RELEVANCE_SCORE = int(os.environ.get("MIN_RELEVANCE_SCORE", "5"))

# Schedule settings (24-hour format)
COLLECTION_SCHEDULE = os.environ.get("COLLECTION_SCHEDULE", "02:00")  # 2 AM
PROCESSING_SCHEDULE = os.environ.get("PROCESSING_SCHEDULE", "03:00")  # 3 AM
DIGEST_SCHEDULE = os.environ.get("DIGEST_SCHEDULE", "08:00")  # 8 AM (Monday)

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", str(BASE_DIR / "arxiv_monitor.log"))
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Streamlit app
APP_TITLE = "AI Red Teaming Research Monitor"
APP_DESCRIPTION = """
This application monitors and analyzes recent AI red teaming research papers from arXiv. 
It provides summaries, technical explanations, and categorization of papers by attack types.
"""
