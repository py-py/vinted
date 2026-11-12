import os

# Required settings that `.env` provides when the app runs.
os.environ.setdefault("LISTING_PROVIDER", "google")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")
