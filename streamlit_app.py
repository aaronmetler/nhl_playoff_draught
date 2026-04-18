import streamlit as st
import pandas as pd
import requests
import random
import datetime
import extra_streamlit_components as stx

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler 2026 Playoff Tracker")

# Initialize Cookie Manager
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()
saved_email = cookie_manager.get('user_email_cookie')

# Ensure session state exists
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.gm_name = None
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

def login_flow():
    # Check if we have a cookie first
    if saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        return True # Authorized

    st.title("🏒 Playoff Pool Login")
    with st.form("login"):
        email = st.text_input("Email").lower().strip()
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            if email in USER_DB and pwd == SHARED_PWD:
                # Set cookie and force a rerun to recognize it
                cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                st.session_state.authenticated = True
                st.session_state.gm_name = USER_DB[email]
                st.rerun()
            else:
                st.error("Invalid credentials.")
    return False

# STOP everything if not logged in
if not login_flow():
    st.stop()

# --- 3. DATA LOADING (Only runs if authorized) ---
@st.cache_data(ttl=3600)
def load_all_data():
    # Load Stats from NHL
    url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3}
    stats = pd.DataFrame()
    try:
        r = requests.get(url, params=params).json()
        stats = pd.DataFrame(r.get('data', []))
        if not stats.empty:
            stats['Pts'] = stats['goals'] + stats['assists']
    except:
        pass

    # Load Roster CSV
    try:
        # Use skiprows=1 to align your specific CSV columns
        rosters = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    except:
        rosters = pd.DataFrame()
        
    return stats, rosters

stats_df, rosters_df = load_all_data()

# --- 4. AVATAR MODAL ---
@st.dialog("Update Team Avatar")
def avatar_dialog():
    file = st.file_uploader("Select Image", type=["jpg", "png", "jpeg"])
    if st.button("Save"):
        if file:
            st.session_state.avatar = file.getvalue()
            st.rerun()

# --- 5. NAVIGATION ---
st.sidebar.title(f"GM: {st.session_state.gm_name}")
if st.session_state.avatar:
    st.sidebar.image(st.session_state.avatar, width=100)
if st.sidebar.button("Log Out"):
    cookie_manager.delete('user_email_cookie')
    st.session_state.authenticated = False
    st.rerun()

nav = st.radio("Navigation", ["League", "My Team"], horizontal=True)

if nav == "League":
    st.header("🏆 League Standings")
    st.info("Toronto: Currently planning the 2027 parade.")
    
    # Simple table logic to ensure it appears even with 0s
    gms_list = list(USER_DB.values())
    leaderboard = pd.DataFrame({
        "Rank": range(1, len(gms_list) + 1),
        "GM": gms_list,
        "Total Points": 0,
        "Goals": 0,
        "Players Left": 14
    })
    st.table(leaderboard)

else:
    st.header("🏒 Team Roster")
    if st.button("👤 Add my Avatar"):
        avatar_dialog()
    
    gms_list = list(USER_DB.values())
    default_idx = gms_list.index(st.session_state.gm_name) if st.session_state.gm_name in gms_list else 0
    selected_gm = st.selectbox("View Team:", gms_list, index=default_idx)
    
    st.write(f"Showing roster for **{selected_gm}**")
    st.caption("* **Bold** = Playing today | _Italics_ = Eliminated")
    # Table logic...
