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
                    st.rerun() # Force a refresh to load the main app
                else:
                    st.error("Invalid credentials.")
    st.stop() # Prevent the rest of the app from loading if not logged in

# ==========================================
# --- 3. MAIN APP (ONLY VISIBLE IF LOGGED IN) ---
# ==========================================

# --- TOP RIGHT USER PROFILE ---
# Create 3 columns. The first takes up most of the space to push the others to the right.
head_c1, head_c2, head_c3 = st.columns([8, 1.5, 1])

with head_c2:
    if st.session_state.avatar:
        st.image(st.session_state.avatar, width=40)
    else:
        st.markdown("👤")
    st.markdown(f"**{st.session_state.gm_name}**")

with head_c3:
    st.write("") # Spacer
    if st.button("Log Out"):
        cookie_manager.delete('user_email_cookie')
        st.session_state.authenticated = False
        st.session_state.gm_name = None
        st.session_state.avatar = None
        st.rerun()

st.divider() # Draw a line under the header

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
    clean_p = str(player_str).replace('-', ' ').lower()
    team_map = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}
    
    if stats_df.empty:
        return {'lastName': str(player_str).split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0}

    parts = clean_p.split()
    team_part = team_map.get(parts[-1].upper(), parts[-1].upper())
    name_part = parts[0].replace('ü', 'u')
    if "." in name_part: name_part = parts[1] if len(parts) > 1 else name_part

    match = stats_df[(stats_df['lastName'].str.lower().str.contains(name_part)) & 
                     (stats_df['teamAbbrev'] == team_part)]
    
    return match.iloc[0].to_dict() if not match.empty else None

stats, active_today = fetch_live_data()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [col for col in df_raw.columns if col in USER_DB.values()]
except:
    st.error("Missing or invalid CSV file: Ensure '2026 NHL Draught - Sheet1.csv' is uploaded to GitHub.")
    st.stop()

master_list = []
for index, row in df_raw.iterrows():
    round_name = str(row.get('Draft Rounds', ''))
    if "Round" not in round_name: continue
    
    for gm in gms:
        pick_str = row.get(gm, '')
        p_data = clean_and_match(pick_str, stats)
        
        if p_data is None:
            p_data = {'lastName': pick_str, 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0}
            
        master_list.append({
            'GM': gm, 'Player': p_data['lastName'], 'Pts': p_data.get('totalPoints', 0), 
            'G': p_data.get('goals', 0), 'A': p_data.get('assists', 0), 'GP': p_data.get('gamesPlayed', 0), 'Round': round_name
        })

master_df = pd.DataFrame(master_list)

# --- 5. AVATAR MODAL ---
@st.dialog("Update Team Avatar")
def avatar_dialog():
    st.write("Upload a square image for your team profile.")
    file = st.file_uploader("Select Image", type=["jpg", "png", "jpeg"])
    if st.button("Save Changes"):
        if file:
            st.session_state.avatar = file.getvalue()
            st.success("Avatar updated!")
            st.rerun()

# --- 6. NAVIGATION & UI VIEWS ---
nav = st.radio("Navigation", ["League", "My Team"], horizontal=True)

if nav == "League":
    st.title("🏆 League Standings")
    st.info("Toronto Maple Leafs Update: Currently scheduling tee times for May.")
    
    if not master_df.empty:
        leaderboard = master_df.groupby('GM').agg({'Pts': 'sum', 'G': 'sum'}).reset_index()
        leaderboard = leaderboard.sort_values(by=['Pts', 'G'], ascending=False).reset_index(drop=True)
        leaderboard.index += 1
        st.dataframe(leaderboard, use_container_width=True)

else:
    st.title("🏒 My Team")
    
    # Avatar Button is only on the Team page now
