import streamlit as st
import pandas as pd
import requests
import datetime
import base64
import extra_streamlit_components as stx
import xml.etree.ElementTree as ET
import os

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
        }
        hr {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        
        /* Roast Box CSS */
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.5rem 1rem; 
            position: relative;
            min-height: 40px; 
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }
        .quote-1, .quote-2 {
            position: absolute;
            width: calc(100% - 2rem);
            color: #0068c9;
            font-size: 1rem;
            animation: fadeSwap 20s infinite;
        }
        .quote-1 { animation-delay: 0s; }
        .quote-2 { animation-delay: 10s; opacity: 0; }

        @keyframes fadeSwap {
            0%, 45% { opacity: 1; visibility: visible; }
            50%, 95% { opacity: 0; visibility: hidden; }
            100% { opacity: 1; visibility: visible; }
        }
        
        /* Custom Team HTML Table CSS */
        .team-table {
            width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem;
        }
        .team-table th {
            border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 8px;
        }
        .team-table td {
            border-bottom: 1px solid #eee; padding: 8px; text-align: center;
        }
        .team-table td.text-left, .team-table th.text-left {
            text-align: left;
        }
        .team-table a { text-decoration: none; }
        .team-table a:hover { text-decoration: underline; }
        
        /* KPI Centering */
        [data-testid="stMetric"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        [data-testid="stMetricValue"] { 
            font-size: 1.8rem; 
            color: #0068c9; 
            text-align: center; 
        }
        [data-testid="stMetricLabel"] { 
            text-align: center; 
        }
    </style>
""", unsafe_allow_html=True)

# Added a unique key to the cookie manager itself
cookie_manager = stx.CookieManager(key="cookie_manager")

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None

# --- 2. AUTHENTICATION LOGIC ---
USER_DB = {
    "mike.mastromattei@gmail.com": "Mike", "rhys.metler@gmail.com": "Rhys",
    "greg.metler@yahoo.com": "Big M", "peterwilliamhammond@gmail.com": "Pete",
    "ryan.torrie@gmail.com": "Torrie", "cochrane.jason@gmail.com": "Jay",
    "mattjames.duncan@gmail.com": "Duncs", "gtraks@gmail.com": "Trakas",
    "pgardner355@gmail.com": "Gardner", "aaronmetler@gmail.com": "Aaron"
}
SHARED_PWD = "playoffs2026"

TEAM_URLS = {
    'ANA': 'ducks', 'BOS': 'bruins', 'BUF': 'sabres', 'CGY': 'flames',
    'CAR': 'hurricanes', 'CHI': 'blackhawks', 'COL': 'avalanche', 'CBJ': 'bluejackets',
    'DAL': 'stars', 'DET': 'redwings', 'EDM': 'oilers', 'FLA': 'panthers',
    'LAK': 'kings', 'MIN': 'wild', 'MTL': 'canadiens', 'NSH': 'predators',
    'NJD': 'devils', 'NYI': 'islanders', 'NYR': 'rangers', 'OTT': 'senators',
    'PHI': 'flyers', 'PIT': 'penguins', 'SJS': 'sharks', 'SEA': 'kraken',
    'STL': 'blues', 'TBL': 'lightning', 'TOR': 'mapleleafs', 'UTA': 'utah',
    'VAN': 'canucks', 'VGK': 'goldenknights', 'WSH': 'capitals', 'WPG': 'jets'
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def is_authenticated():
    if st.session_state.authenticated: return True
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email and saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        if not st.session_state
