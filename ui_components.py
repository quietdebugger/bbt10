"""
UI Components & Styling for Gemini Market Terminal
"""

import streamlit as st
import pandas as pd
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    HAS_AGGRID = True
except ImportError:
    HAS_AGGRID = False

def render_aggrid(df: pd.DataFrame, height: int = 300, row_height: int = 35, key: str = None):
    """
    Renders a high-performance AgGrid table with Bloomberg styling.
    Fallback to st.dataframe if st_aggrid is not installed.
    """
    if not HAS_AGGRID:
        st.dataframe(df, height=height, use_container_width=True)
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        groupable=True, 
        value=True, 
        enableRowGroup=True, 
        aggFunc='sum', 
        editable=False,
        resizable=True,
        sortable=True,
        filter=True
    )
    gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=True, groupSelectsFiltered=True)
    gb.configure_grid_options(domLayout='normal', rowHeight=row_height)
    
    # Conditional Formatting for numeric columns (Change, P&L, %)
    numeric_cell_style = JsCode("""
    function(params) {
        if (typeof params.value === 'string' && (params.value.includes('%') || params.value.includes('₹'))) {
             // Basic heuristic for formatted strings
             if (params.value.includes('-')) {
                 return {'color': '#ff4444', 'fontWeight': 'bold'};
             } else if (params.value.includes('+') || !params.value.includes('-')) {
                 // Check if it looks like a number
                 return {'color': '#00ff00', 'fontWeight': 'bold'};
             }
        }
        if (typeof params.value === 'number') {
            if (params.value > 0) {
                return {'color': '#00ff00', 'fontWeight': 'bold'};
            } else if (params.value < 0) {
                return {'color': '#ff4444', 'fontWeight': 'bold'};
            }
        }
        return null;
    }
    """)
    
    # Apply to likely numeric columns
    for col in df.columns:
        if any(x in col.lower() for x in ['%', 'change', 'pnl', 'profit', 'loss', 'return', 'delta', 'gamma']):
             gb.configure_column(col, cellStyle=numeric_cell_style)

    gridOptions = gb.build()
    
    AgGrid(
        df, 
        gridOptions=gridOptions, 
        height=height, 
        width='100%',
        theme='balham-dark', # Close to terminal style
        fit_columns_on_grid_load=True, # Use horizontal scroll if needed
        allow_unsafe_jscode=True,
        key=key
    )

def load_custom_css():
    st.markdown("""
        <style>
        /* Bloomberg-style dark theme */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #ffffff;
        }

        [data-testid="stSidebar"] {
            background: #0f0f0f !important;
            border-right: 2px solid #333;
        }

        .plugin-card {
            background: linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 15px 0;
            border-left: 4px solid #007bff;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            color: #ffffff;
        }

        .category-header {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            padding: 15px 25px;
            border-radius: 12px;
            color: white;
            margin: 20px 0;
            font-weight: bold;
            font-size: 1.2em;
            box-shadow: 0 4px 15px rgba(0,123,255,0.3);
        }

        .metric-card {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #333;
            text-align: center;
            margin: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #007bff;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #9ca3af;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00ff00;
        }
        .metric-delta {
            font-size: 0.9rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .delta-pos { color: #00ff00; }
        .delta-neg { color: #ef4444; }
        .delta-neu { color: #9ca3af; }

        .watchlist-panel {
            background: #0f0f0f;
            border: 2px solid #333;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }

        .news-ticker {
            background: #000000;
            color: #00ff00;
            padding: 8px;
            border-radius: 5px;
            font-family: monospace;
            overflow: hidden;
            white-space: nowrap;
            margin-bottom: 20px;
        }

        .news-ticker-content {
            display: inline-block;
            padding-left: 100%;
            animation: ticker 30s linear infinite;
        }

        @keyframes ticker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-100%); }
        }

        /* Ticker Tape (Legacy Plugin Compatibility) */
        .ticker-tape {
            display: flex;
            gap: 20px;
            overflow-x: auto;
            padding: 10px 0;
            margin-bottom: 20px;
            background: #161b22;
            border-bottom: 1px solid #30363d;
            white-space: nowrap;
        }
        .ticker-item {
            display: inline-flex;
            flex-direction: column;
            padding: 0 15px;
            border-right: 1px solid #30363d;
        }

        /* Dataframe styling */
        [data-testid="stDataFrame"] {
            background: #1a1a1a !important;
            border-radius: 8px;
            border: 1px solid #333;
        }

        [data-testid="stDataFrame"] thead th {
            background: #2a2a2a !important;
            color: #ffffff !important;
            border-bottom: 2px solid #007bff;
        }

        /* Button styling */
        .stButton>button {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            transition: all 0.3s ease !important;
        }

        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(0,123,255,0.4) !important;
        }

        /* Metric styling */
        [data-testid="stMetricValue"] {
            color: #00ff00 !important;
            font-weight: bold !important;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.9em !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(label: str, value: str, delta: str = None, is_positive: bool = None, help_text: str = None):
    """
    Renders a styled metric card.
    """
    delta_html = ""
    if delta:
        if is_positive is True:
            color_class = "delta-pos"
            icon = "▲"
        elif is_positive is False:
            color_class = "delta-neg"
            icon = "▼"
        else:
            color_class = "delta-neu"
            icon = "•"
        delta_html = f'<div class="metric-delta {color_class}">{icon} {delta}</div>'

    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

def render_news_ticker(text: str):
    """
    Renders a horizontal news ticker.
    """
    st.markdown(f"""
        <div class="news-ticker">
            <div class="news-ticker-content">
                {text}
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_ticker_tape(metrics: list):
    """
    Renders a horizontal ticker tape (for legacy plugin compatibility).
    metrics: list of dicts with keys: label, value, delta, is_positive
    """
    items_html = ""
    for m in metrics:
        color = "#10b981" if m.get('is_positive') else "#ef4444"
        if m.get('is_positive') is None: color = "#9ca3af"
        
        items_html += f"""
            <div class="ticker-item">
                <span style="font-size: 0.8rem; color: #9ca3af;">{m['label']}</span>
                <div>
                    <span style="font-weight: bold; color: #e5e7eb;">{m['value']}</span>
                    <span style="font-size: 0.8rem; color: {color}; margin-left: 5px;">{m['delta']}</span>
                </div>
            </div>
        """
    
    st.markdown(f"""
        <div class="ticker-tape">
            {items_html}
        </div>
    """, unsafe_allow_html=True)
