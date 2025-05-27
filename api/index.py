# api/index.py for vercel hosting
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # this imports the FastAPI app
