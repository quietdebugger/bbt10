"""
Upstox Authentication Service
Handles OAuth2 login flow and token management.
Supports both Local (Headful) and Cloud (Headless) environments.
"""

import os
import json
import logging
import time
import requests
import streamlit as st
import webbrowser
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = "upstox_tokens.json"
BASE_URL = "https://api.upstox.com/v2"

class UpstoxAuth:
    def __init__(self, api_key=None, api_secret=None):
        # Try to load from arguments, then secrets, then config file
        self.api_key = api_key
        self.api_secret = api_secret
        
        if not self.api_key:
            # Check Streamlit Secrets (Cloud)
            if hasattr(st, "secrets") and "UPSTOX_API_KEY" in st.secrets:
                self.api_key = st.secrets["UPSTOX_API_KEY"]
                self.api_secret = st.secrets["UPSTOX_API_SECRET"]
            else:
                # Check Config File (Local)
                try:
                    from api_config import UPSTOX_API_KEY, UPSTOX_API_SECRET
                    self.api_key = UPSTOX_API_KEY
                    self.api_secret = UPSTOX_API_SECRET
                except ImportError:
                    logger.warning("api_config.py not found and no secrets provided.")

        self.access_token = None
        self.redirect_uri = "http://localhost:8501" # Default local callback
        self._load_token()

    def _load_token(self):
        """Load token from local file if it exists and is valid"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    # Check expiry (24 hours typically)
                    if time.time() - data.get('timestamp', 0) < 86400:
                        self.access_token = data.get('access_token')
                        logger.info("Loaded valid access token from file.")
                    else:
                        logger.warning("Token expired.")
            except Exception as e:
                logger.error(f"Error loading token file: {e}")

    def get_login_url(self):
        """Generate the login URL"""
        params = {
            'response_type': 'code',
            'client_id': self.api_key,
            'redirect_uri': self.redirect_uri,
            'state': 'bbt_terminal'
        }
        return f"{BASE_URL}/login/authorization/dialog?{urlencode(params)}"

    def login(self):
        """
        Interactive Login Flow.
        Handles both Local (Auto-open) and Cloud (Manual Code Input).
        """
        if self.access_token:
            return True

        login_url = self.get_login_url()
        
        # UI for Authentication
        st.warning("⚠️ Upstox Authentication Required")
        st.markdown(f"**[Click here to Login with Upstox]({login_url})**")
        st.info("After logging in, you will be redirected to a URL (e.g. localhost:8501/?code=...). Copy that 'code' and paste it below.")
        
        # Check URL params for code (if redirect happened to this app instance)
        # This works if deployed url matches redirect_uri, or localhost
        query_params = st.query_params
        code_from_url = query_params.get("code")
        
        auth_code = st.text_input("Enter Auth Code:", value=code_from_url if code_from_url else "", type="password")
        
        if st.button("Authenticate"):
            if auth_code:
                if self._generate_access_token(auth_code):
                    st.success("Authentication Successful! Reloading...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to generate token. Check code or API keys.")
            else:
                st.error("Please enter the auth code.")
        
        # Stop execution until logged in
        st.stop()
        return False

    def _generate_access_token(self, code):
        """Exchange auth code for access token"""
        url = f"{BASE_URL}/login/authorization/token"
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'code': code,
            'client_id': self.api_key,
            'client_secret': self.api_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            if response.status_code == 200:
                resp_json = response.json()
                self.access_token = resp_json.get('access_token')
                
                # Save token locally
                with open(TOKEN_FILE, 'w') as f:
                    json.dump({
                        'access_token': self.access_token,
                        'timestamp': time.time()
                    }, f)
                
                logger.info("Generated and saved new access token.")
                return True
            else:
                logger.error(f"Token generation failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Token request error: {e}")
            return False

    # --- COMPATIBILITY METHOD ---
    def get_access_token(self):
        """
        Method required by some legacy plugins/services.
        Ensures login flow is triggered if token is missing.
        """
        if not self.access_token:
            # If in Streamlit, trigger UI flow
            if self.login(): 
                return self.access_token
            else:
                # If login fails or stops, return None or raise
                return None
        return self.access_token
