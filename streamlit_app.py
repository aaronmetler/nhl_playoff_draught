import streamlit as st
import pandas as pd
import requests
import random
import datetime
import plotly.express as px
import re
from PIL import Image
import io

# --- 1. USER DATABASE & AUTH CONFIG ---
# Mapping of emails to GM names as they appear in your CSV
USER_DB = {
    "mike.mastromattei@gmail.com": "Mike",
    "rhys.metler@gmail.com": "Rhys", # Note: CSV has 'Rhys', map accordingly
    "greg.metler@yahoo.com": "Big M",
    "peterwilliamhammond@gmail.com": "Pete",
    "ryan.torrie@gmail.com": "Torrie",
    "cochrane.jason@gmail.com": "Jay",
    "mattjames.duncan@gmail.com": "Duncs",
    "gtraks@gmail.com": "Trakas",
    "pgardner355@gmail.com": "Gardner",
    "aaronmetler@gmail.com": "Aaron"
}
SHARED_PASSWORD = "playoffs2026" # Change this as needed

# --- 2. AUTHENTICATION LOGIC ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.gm_name = None
    st.session_state.avatar = None

def login():
    st.title("🏒 Metler Playoff Pool Login")
    with st.form("login_form"):
        email = st.text_input("Email").lower().strip()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if email in USER_DB and password == SHARED_PASSWORD:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.gm_name = USER_DB[email]
                st.rerun()
            else:
                st.error("Invalid email or password.")

if not st.session_state.authenticated:
    login()
    st.stop()

# --- 3. APP SETUP (POST-LOGIN) ---
st.set_page_config(layout="wide", page_title="Metler 2026 Tracker")

# Sidebar Account Management
with st.sidebar:
    st.title(f"Welcome, {st.session_state.gm_name}!")
    
    # Avatar Upload
    uploaded_file = st.file_uploader("Upload Avatar", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        st.session_state.avatar = uploaded_file.getvalue()
    
    if st.session_state.avatar:
        st.image(st.session_state.avatar, width=100)
    
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# --- 4. DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_data():
    # Attempting to pull 2026 Playoff Stats
    url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3}
    try:
        resp = requests.get(url, params=params).json()
        df = pd.DataFrame(resp.get('data', []))
        if not df.empty:
            df['Pts'] = df['goals'] + df['assists']
            return df
    except:
        return pd.DataFrame()
    return pd.DataFrame()

stats_df = fetch_data()

# Load Draft CSV
try:
    # Adjusted to skip the first row based on your sheet structure
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    all_gms = [col for col in df_raw.columns if col in USER_DB.values()]
except:
    st.error("CSV File not found or headers mismatched.")
    st.stop()

# --- 5. NAVIGATION ---
# Requirement: Labels "League" and "My Team"
nav = st.radio("Navigation", ["League", "My Team"], horizontal=True)

if nav == "League":
    st.header("🏆 Playoff Standings")
    # Sarcastic Leafs Statement
    leafs_jabs = ["The Leafs' playoff beard kits are already on clearance.", "Toronto: 1967 called, they're still waiting."]
    st.info(random.choice(leafs_jabs))
    
    # Leaderboard Logic
    # (Simplified for Zeros if stats_df is empty)
    lb_data = []
    for gm in all_gms:
        lb_data.append({"GM": gm, "Total Points": 0, "Goals": 0, "Players Left": 14})
    
    lb_df = pd.DataFrame(lb_data).sort_values("Total Points", ascending=False)
    st.table(lb_df)

else:
    st.header("🏒 Team Roster")
    
    # Requirement: Default to the logged-in user's team
    default_index = all_gms.index(st.session_state.gm_name) if st.session_state.gm_name in all_gms else 0
    selected_gm = st.selectbox("View Another Team", all_gms, index=default_index)
    
    # Requirement: Small note on bolding
    st.caption("* **Bold** indicates playing today. _Italicized_ indicates eliminated.")
    
    # Roster Table
    st.write(f"Displaying roster for: **{selected_gm}**")
    # (Placeholder table for roster points)
    st.write("Team stats will populate here based on NHL API data.")
