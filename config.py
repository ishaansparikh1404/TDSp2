"""
Configuration settings for the LLM Analysis Quiz Project
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys - Your Gemini API Key (already configured!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDkynxZQ_-UmitHKi0qi0avFjvkFDBg3S0")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Authentication - Set these before deployment!
# For the actual quiz, update these with your real values
SECRET = os.getenv("SECRET", "my_super_secret_key_2025")
EMAIL = os.getenv("EMAIL", "your_email@example.com")

# Timeouts - Must complete within 3 minutes
REQUEST_TIMEOUT = 180  # 3 minutes for quiz solving (CRITICAL)
BROWSER_TIMEOUT = 60000  # 60 seconds for browser operations
LLM_TIMEOUT = 120  # 2 minutes for LLM calls

# Timeouts
REQUEST_TIMEOUT = 180  # 3 minutes for quiz solving
BROWSER_TIMEOUT = 60000  # 60 seconds for browser operations
LLM_TIMEOUT = 120  # 2 minutes for LLM calls

# LLM Settings
GEMINI_MODEL = "gemini-2.0-flash"
MAX_TOKENS = 8192
TEMPERATURE = 0.1  # Low temperature for more deterministic outputs
