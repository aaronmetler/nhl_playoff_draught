import streamlit as st
import pandas as pd
import requests
import random
import datetime
import re
import extra_streamlit_components as stx

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# Initialize Cookie Controller
cookie_manager = stx.CookieManager()
saved_email = cookie_manager.get('user_email_cookie')

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.gm_name = None
    st.session_state.avatar = None

# --- 2. AUTHENTICATION & COOKIE CHECK ---
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

def login_flow():
    # If cookie exists, auto-login
    if saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        return

    st.title("🔒 Playoff Pool Login")
    with st.form("login"):
        email = st.text_input("Email").lower().strip()
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            if email in USER_DB and pwd == SHARED_PWD:
                # Set cookie for 30 days
                cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                st.session_state.authenticated = True
                st.session_state.gm_name = USER_DB[email]
                st.rerun()
            else:
                st.error("Invalid credentials.")

if not st.session_state.authenticated:
    login_flow()
    st.stop()

# --- 3. DATA LOADING ---
@st.cache_data(ttl=3600)
def get_stats():
    # NHL API Fetch logic (similar to previous steps)
    return pd.DataFrame()

df_stats = get_stats()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    all_gms = [col for col in df_raw.columns if col in USER_DB.values()]
except:
    st.error("Error loading CSV roster data.")
    st.stop()

# --- 4. AVATAR MODAL (st.dialog) ---
@st.dialog("Update Your Team Avatar")
def upload_avatar_modal():
    st.write("Upload a square image for your team icon.")
    file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])
    if st.button("Save Changes"):
        if file:
            st.session_state.avatar = file.getvalue()
            st.success("Avatar updated!")
            st.rerun()

# --- 5. NAVIGATION & UI ---
st.sidebar.title(f"Hello, {st.session_state.gm_name}!")
if st.session_state.avatar:
    st.sidebar.image(st.session_state.avatar, width=100)
if st.sidebar.button("Logout"):
    cookie_manager.delete('user_email_cookie')
    st.session_state.authenticated = False
    st.rerun()

nav = st.radio("Navigation", ["League", "My Team"], horizontal=True)

if nav == "League":
    st.title("🏆 League Leaderboard")
    # Leaderboard logic goes here...
    st.write("Sorting teams by Total Points (Tie-break: Goals)...")

else:
    st.title("🏒 My Team")
    
    # "Add my Avatar" Button - Triggers the Modal
    if st.button("👤 Add/Change My Avatar"):
        upload_avatar_modal()
    
    # GM Selection: Default to logged-in user
    default_idx = all_gms.index(st.session_state.gm_name) if st.session_state.gm_name in all_gms else 0
    current_gm = st.selectbox("Switch Team View:", all_gms, index=default_idx)
    
    st.subheader(f"Roster for {current_gm}")
    # Roster display logic goes here...
