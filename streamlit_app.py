import streamlit as st
import pandas as pd
import requests
import random
import datetime
import extra_streamlit_components as stx

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# Initialize Cookie Manager
cookie_manager = stx.CookieManager()

# Ensure all session state variables exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'gm_name' not in st.session_state:
    st.session_state.gm_name = None
if 'display_name' not in st.session_state:
    st.session_state.display_name = None
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
    if st.session_state.authenticated:
        return True
    
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email and saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        if not st.session_state.display_name:
            st.session_state.display_name = USER_DB[saved_email]
        return True
    return False

# --- LOGIN SCREEN ---
if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
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
                    st.session_state.display_name = USER_DB[email]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# ==========================================
# --- 3. MAIN APP (ONLY VISIBLE IF LOGGED IN) ---
# ==========================================

# --- TOP HEADER: App Title (Left) & User Profile (Right) ---
t_title, t_text, t_img, t_menu = st.columns([6.5, 2.5, 0.5, 0.5])

with t_title:
    # Adds the App Name to the top left
    st.markdown("<h3 style='margin-top: 5px; margin-bottom: 0px;'>🏆 Metler Playoff Pool</h3>", unsafe_allow_html=True)

with t_text:
    # Adding margin to vertically align the text with the image/button
    st.markdown(f"<div style='text-align: right; margin-top: 10px; font-size: 18px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)

with t_img:
    if st.session_state.avatar:
        st.image(st.session_state.avatar, width=40)
    else:
        st.markdown("<div style='font-size: 26px; text-align: center; margin-top: -2px;'>👤</div>", unsafe_allow_html=True)

with t_menu:
    with st.popover("⚙️"):
        st.markdown("**Profile Settings**")
        
        new_name = st.text_input("Display Name", value=st.session_state.display_name)
        if st.button("Update Name"):
            st.session_state.display_name = new_name
            st.rerun()
            
        st.divider()
        
        file = st.file_uploader("Upload Avatar", type=["jpg", "png", "jpeg"])
        if st.button("Save Avatar"):
            if file:
                st.session_state.avatar = file.getvalue()
                st.rerun()
                
        st.divider()
        
        if st.button("Log Out", use_container_width=True):
            cookie_manager.delete('user_email_cookie')
            st.session_state.authenticated = False
            st.session_state.gm_name = None
            st.session_state.display_name = None
            st.session_state.avatar = None
            st.rerun()

st.divider()

# --- 4. WEB 3.0 MODERN NAVIGATION ---
try:
    nav = st.segmented_control("Navigation", ["League", "My Team"], default="League", label_visibility="collapsed")
except AttributeError:
    try:
        nav = st.pills("Navigation", ["League", "My Team"], default="League", label_visibility="collapsed")
    except AttributeError:
        nav = st.radio("Navigation", ["League", "My Team"], horizontal=True, label_visibility="collapsed")

if nav is None:
    nav = "League"

st.write("") # Tiny spacer

# --- 5. DATA LOADING & NORMALIZATION ---
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
                return stats_df
    except:
        pass
    return pd.DataFrame()

def clean_and_match(player_
