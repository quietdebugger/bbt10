
import os
import streamlit as st

# Default to None
UPSTOX_API_KEY = None
UPSTOX_API_SECRET = None
GEMINI_API_KEY = None

# 1. Try Loading from Streamlit Secrets (Cloud)
if hasattr(st, "secrets"):
    if "UPSTOX_API_KEY" in st.secrets:
        UPSTOX_API_KEY = st.secrets["UPSTOX_API_KEY"]
    if "UPSTOX_API_SECRET" in st.secrets:
        UPSTOX_API_SECRET = st.secrets["UPSTOX_API_SECRET"]
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# 2. Fallback to Environment Variables (Docker/Local)
if not UPSTOX_API_KEY:
    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
if not UPSTOX_API_SECRET:
    UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 3. Fallback to Local Config File (Legacy Dev)
# We do NOT import this if on cloud to avoid errors if file is missing
if not UPSTOX_API_KEY:
    try:
        # Check if local config file exists
        if os.path.exists("api_config_local.py"):
            from api_config_local import UPSTOX_API_KEY as LOCAL_KEY, UPSTOX_API_SECRET as LOCAL_SECRET, GEMINI_API_KEY as LOCAL_GEMINI
            UPSTOX_API_KEY = LOCAL_KEY
            UPSTOX_API_SECRET = LOCAL_SECRET
            GEMINI_API_KEY = LOCAL_GEMINI
    except ImportError:
        pass
