"""
UI Styles - Cyberpunk Financial Theme
High Contrast, Professional, Clean.
"""

import streamlit as st

def apply_terminal_style():
    st.markdown("""
        <style>
        /* GLOBAL RESET & BASICS */
        .stApp {
            background-color: #000000 !important; /* Pure Black */
            color: #e0e0e0 !important; /* Light Grey */
        }
        
        /* SHARP CORNERS & HIGH DENSITY */
        * {
            border-radius: 0px !important;
        }
        
        /* REMOVE TOP PADDING */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 98% !important; /* Maximize width */
        }
        
        /* TYPOGRAPHY */
        h1, h2, h3, h4, h5, h6 {
            color: #FFFFFF !important;
            font-family: 'Roboto Mono', 'Segoe UI', monospace !important;
            font-weight: 600 !important;
            letter-spacing: -0.5px;
            margin-bottom: 0.5rem !important;
        }
        p, div, span {
            font-family: 'Roboto Mono', monospace !important;
            font-size: 0.9rem;
        }
        
        /* COMPACT METRICS */
        [data-testid="stMetric"] {
            background-color: transparent !important;
            border: 1px solid #222;
            padding: 5px 10px !important;
            margin: 0px !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem !important;
            color: #888 !important;
            text-transform: uppercase;
            margin-bottom: 0px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
            color: #fff !important;
            font-family: 'Roboto Mono', monospace;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.7rem !important;
            margin-top: 0px !important;
        }

        /* TABLES */
        [data-testid="stDataFrame"] {
            border: 1px solid #333;
        }
        
        /* SIDEBAR */
        [data-testid="stSidebar"] {
            background-color: #050505;
            border-right: 1px solid #222;
        }
        
        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            border-bottom: 1px solid #333;
        }
        .stTabs [data-baseweb="tab"] {
            height: 35px;
            padding: 0 15px;
            background-color: transparent;
            border: none;
            color: #666;
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
        }
        .stTabs [aria-selected="true"] {
            background-color: #111;
            color: #ff9900; /* Bloomberg Orange/Yellow Highlight */
            border-top: 2px solid #ff9900;
            border-bottom: none;
        }
        
        /* REMOVE CONTAINER PADDING */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

def render_cyber_metric(label, value, delta=None, is_positive=None, large=False):
    # Minimalist render, no card background
    delta_color = "#00ff00" if is_positive else "#ff0000" if is_positive is False else "#888"
    delta_html = f'<span style="color: {delta_color}; font-size: 0.8rem; margin-left: 5px;">{delta}</span>' if delta else ""
    
    font_size = "1.8rem" if large else "1.2rem"
    
    st.markdown(f"""
    <div style="border-bottom: 1px solid #222; padding-bottom: 5px; margin-bottom: 10px;">
        <div style="font-size: 0.75rem; color: #666; text-transform: uppercase;">{label}</div>
        <div style="display: flex; align-items: baseline;">
            <div style="font-size: {font_size}; font-weight: 700; color: #fff;">{value}</div>
            {delta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
