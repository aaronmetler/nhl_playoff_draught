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

# --- CUSTOM CSS: EXTREME PADDING REDUCTION & ANIMATIONS ---
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
        /* Rotating Roast Box CSS */
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 1rem;
            position: relative;
            min-height: 80px;
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
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager()

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

def is_authenticated():
    if st.session_state.authenticated: return True
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

# --- 3. MAIN APP HEADER (ULTRA COMPACT WITH LOGO) ---
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])

with t_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=55)
        
with t_title: 
    st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
    
with t_text: 
    st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
    
with t_img:
    if st.session_state.avatar: st.image(st.session_state.avatar, width=35)
    else: st.markdown("<div style='font-size: 24px; text-align: center; margin-top: -3px;'>👤</div>", unsafe_allow_html=True)
    
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

# --- 4. NAVIGATION ---
try:
    nav = st.segmented_control("Navigation", ["League", "My Team"], default="League", label_visibility="collapsed")
except AttributeError:
    nav = st.radio("Navigation", ["League", "My Team"], horizontal=True, label_visibility="collapsed")

if nav is None: nav = "League"

# --- 5. DATA FETCHING & LOGIC ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    stats_url = "https://api-web.nhle.com/v1/skater-stats-now"
    try:
        resp = requests.get(stats_url, params={"season": "20252026", "gameTypeId": 3})
        if resp.status_code == 200:
            df = pd.DataFrame(resp.json().get('data', []))
            if not df.empty:
                df['totalPoints'] = df['goals'] + df['assists']
                return df
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_eliminated_teams():
    eliminated = set()
    try:
        res = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026")
        if res.status_code == 200:
            data = res.json()
            series_list = data.get('series', [])
            if not series_list and 'rounds' in data:
                series_list = [s for r in data['rounds'] for s in r.get('series', [])]
            for s in series_list:
                m = s.get('matchupTeams', [])
                if len(m) == 2:
                    w1 = m[0].get('seriesRecord', {}).get('wins', 0)
                    w2 = m[1].get('seriesRecord', {}).get('wins', 0)
                    if w1 == 4: eliminated.add(m[1].get('team', {}).get('abbrev', m[1].get('teamAbbrev')))
                    if w2 == 4: eliminated.add(m[0].get('team', {}).get('abbrev', m[0].get('teamAbbrev')))
                top, bot = s.get('topSeed', {}), s.get('bottomSeed', {})
                if top and bot:
                    if top.get('wins', 0) == 4: eliminated.add(bot.get('abbrev', bot.get('teamAbbrev')))
                    if bot.get('wins', 0) == 4: eliminated.add(top.get('abbrev', top.get('teamAbbrev')))
    except: pass
    return [t for t in list(eliminated) if t]

@st.cache_data(ttl=3600)
def get_daily_headline():
    headline = "NHL playoffs continue with fierce matchups"
    try:
        resp = requests.get("https://www.espn.com/espn/rss/nhl/news", timeout=3)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall('.//item/title')
            if items: headline = items[0].text
    except: pass
    return headline

def get_worst_gm_roast(master_df, headline):
    if master_df.empty: return f"**NHL News:** {headline}. Meanwhile, everyone here is tied at 0 points."
    lb = master_df.groupby('GM').agg({'Points': 'sum'}).reset_index()
    lb = lb.sort_values('Points', ascending=True)
    worst_gm, worst_pts = lb.iloc[0]['GM'], lb.iloc[0]['Points']
    
    roasts = [
        f"📰 \"{headline}\" — Meanwhile, {worst_gm} is completely oblivious, sitting in last place with a pathetic {worst_pts} points.",
        f"📰 \"{headline}\" — A major story, unless you are {worst_gm}, whose team is currently a bigger disaster at {worst_pts} points.",
        f"📰 \"{headline}\" — Sadly, none of this helps {worst_gm}'s roster, which is participating in an active point-scoring boycott.",
        f"📰 \"{headline}\" — In unrelated news, {worst_gm}'s team continues to be an absolute dumpster fire."
    ]
    return roasts[datetime.datetime.now().day % len(roasts)]

def get_team_roast(selected_gm, my_team_df, headline):
    if my_team_df.empty: return "Where is your team?"
    pts = my_team_df['Points'].sum()
    eliminated = my_team_df[my_team_df['Team_Raw'].isin(ELIMINATED_TEAMS)].shape[0]
    
    if pts == 0:
        return f"📰 \"{headline}\" — None of this matters to {selected_gm}, whose entire roster is currently invisible (0 points)."
    elif eliminated >= 4:
        return f"📰 \"{headline}\" — Fun fact: Half of {selected_gm}'s roster is already golfing while generating a mediocre {pts} points."
    elif pts < 15:
        return f"📰 \"{headline}\" — Also, {selected_gm} is struggling to remain relevant with a sad {pts} points."
    else:
        return f"📰 \"{headline}\" — {selected_gm} is scraping together {pts} points, but we all know it won't last."

def clean_and_match(player_str, stats_df):
    if pd.isna(player_str) or str(player_str).strip() == '': return None
    clean_p = str(player_str).replace('-', ' ').lower()
    team_map = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}
    parts = clean_p.split()
    t_part = team_map.get(parts[-1].upper(), parts[-1].upper())
    n_part = parts[0].replace('ü', 'u')
    if "." in n_part: n_part = parts[1] if len(parts) > 1 else n_part
    if stats_df.empty:
        return {'lastName': str(player_str).split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': ''}
    match = stats_df[(stats_df['lastName'].str.lower().str.contains(n_part)) & (stats_df['teamAbbrev'] == t_part)]
    if not match.empty: return match.iloc[0].to_dict()
    return {'lastName': str(player_str).split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': ''}

stats = fetch_live_data()
ELIMINATED_TEAMS = get_eliminated_teams()
DAILY_HEADLINE = get_daily_headline()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    if 'Draft Rounds' not in df_raw.columns: df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [c for c in df_raw.columns if c in USER_DB.values()]
except:
    st.error("Missing or invalid CSV file.")
    st.stop()

master_list = []
for index, row in df_raw.iterrows():
    round_name = str(row.get('Draft Rounds', ''))
    if "Round" not in round_name: continue
    
    round_num = round_name.replace("Round", "").strip()
    
    for gm in gms:
        pick_str = row.get(gm, '')
        p_data = clean_and_match(pick_str, stats)
        if p_data is None: continue
        
        p_name = p_data.get('lastName', pick_str)
        if 'firstName' in p_data and 'lastName' in p_data: p_name = f"{p_data['firstName']} {p_data['lastName']}"
        p_id = p_data.get('playerId')
        player_url = f"https://www.nhl.com/player/{p_id}" if p_id else f"https://www.google.com/search?q=NHL+{p_name.replace(' ', '+')}"
        
        t_abbrev = p_data.get('teamAbbrev', '')
        t_url = f"https://www.nhl.com/{TEAM_URLS.get(t_abbrev.upper(), 'standings')}" if t_abbrev else "https://www.nhl.com"
        
        master_list.append({
            'GM': gm, 
            'Player': f"[{p_name}]({player_url})", 
            'Team': f"[{t_abbrev}]({t_url})" if t_abbrev else "",
            'Team_Raw': t_abbrev,
            'Position': p_data.get('positionCode
