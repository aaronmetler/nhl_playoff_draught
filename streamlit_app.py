import streamlit as st
import pandas as pd
import requests
import random
import datetime
import plotly.express as px
import extra_streamlit_components as stx

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler 2026 Playoff Tracker", page_icon="🏒")

# Initialize Cookie Manager directly
cookie_manager = stx.CookieManager()

# Ensure session state variables exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'gm_name' not in st.session_state:
    st.session_state.gm_name = None
if 'avatar' not in st.session_state:
    st.session_state.avatar = None

# --- 2. AUTHENTICATION LOGIC ---
USER_DB = {
    "mike.mastromattei@gmail.com": "Mike",
    "rhys.metler@gmail.com": "Rhys",
    "greg.metler@yahoo.com": "Big M",
    "peterwilliamhammond@gmail.com": "Pete",
    "ryan.torrie@gmail.com": "Torrie",
    "cochrane.jason@gmail.com": "Jay",
    "mattjames.duncan@gmail.com": "Duncs",
    "gtraks@gmail.com": "Trakas",
    "pgardner355@gmail.com": "Gardner",
    "aaronmetler@gmail.com": "Aaron"
}
SHARED_PWD = "playoffs2026"

def is_authenticated():
    # Instant session check
    if st.session_state.authenticated:
        return True
    # Persistent cookie check
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email and saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        return True
    return False

# --- LOGIN SCREEN ---
if not is_authenticated():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            email = st.text_input("Email").lower().strip()
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if email in USER_DB and pwd == SHARED_PWD:
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    st.session_state.authenticated = True
                    st.session_state.gm_name = USER_DB[email]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# ==========================================
# --- 3. MAIN APP (ONLY VISIBLE IF LOGGED IN) ---
# ==========================================

# --- TOP RIGHT USER PROFILE ---
# We use a large empty column on the left to push everything to the right edge.
spacer, content = st.columns([7, 3])

with content:
    # Nested columns to force the text, avatar, and button onto one tight line
    c_text, c_img, c_btn = st.columns([2, 0.5, 1], vertical_alignment="center")
    
    with c_text:
        st.markdown(f"<div style='text-align: right; font-size: 18px;'>Welcome {st.session_state.gm_name}</div>", unsafe_allow_html=True)
    
    with c_img:
        if st.session_state.avatar:
            st.image(st.session_state.avatar, width=40)
        else:
            st.markdown("<div style='font-size: 24px; text-align: left;'>👤</div>", unsafe_allow_html=True)
            
    with c_btn:
        if st.button("Log Out", use_container_width=True):
            cookie_manager.delete('user_email_cookie')
            st.session_state.authenticated = False
            st.session_state.gm_name = None
            st.session_state.avatar = None
            st.rerun()

st.divider()

# --- 4. DATA LOADING & NORMALIZATION ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    stats_url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3}
    try:
        resp = requests.get(stats_url, params=params)
        if resp.status_code == 200:
            stats_df = pd.DataFrame(resp.json().get('data', []))
            if not stats_df.empty:
                stats_df['totalPoints'] = stats_df['goals'] + stats_df['assists']
                return stats_df, []
    except:
        pass
    return pd.DataFrame(), []

def clean_and_match(player_str, stats_df):
    if pd.isna(player_str) or str(player_str).strip() == '': return None
    clean_p = str(player_str).replace('-', ' ').lower
