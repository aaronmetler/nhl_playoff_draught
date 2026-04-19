import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo
import base64
import extra_streamlit_components as stx
import difflib
import random
import os

# --- 1. SESSION INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None

# --- 2. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        hr { margin-top: 0.5em; margin-bottom: 0.5em; }
        
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.8rem 1.2rem; 
            margin-bottom: 1rem;
        }
        
        .pool-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem; }
        .pool-table th { border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 12px 8px; }
        .pool-table td { border-bottom: 1px solid #eee; padding: 10px 8px; text-align: center; vertical-align: middle; }
        .pool-table td.text-left, .pool-table th.text-left { text-align: left; }
        
        /* Metric Alignment - Centering both label and value */
        [data-testid="stMetric"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }
        [data-testid="stMetricLabel"] {
            display: flex;
            justify-content: center;
            width: 100%;
        }
        div[data-testid="stMetricValue"] { 
            font-size: 1.8rem; 
            color: #0068c9; 
            text-align: center; 
            width: 100%;
        }

        .gm-label { color: #0068c9; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")
PT_ZONE = ZoneInfo("America/Los_Angeles")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

# --- 3. AUTHENTICATION ---
USER_DB = {
    "mike.mastromattei@gmail.com": "Mike", "rhys.metler@gmail.com": "Rhys",
    "greg.metler@yahoo.com": "Big M", "peterwilliamhammond@gmail.com": "Pete",
    "ryan.torrie@gmail.com": "Torrie", "cochrane.jason@gmail.com": "Jay",
    "mattjames.duncan@gmail.com": "Duncs", "gtraks@gmail.com": "Trakas",
    "pgardner355@gmail.com": "Gardner", "aaronmetler@gmail.com": "Aaron"
}
SHARED_PWD = "playoffs2026"
TEAM_URLS = { 'ANA': 'ducks', 'BOS': 'bruins', 'BUF': 'sabres', 'CGY': 'flames', 'CAR': 'hurricanes', 'CHI': 'blackhawks', 'COL': 'avalanche', 'CBJ': 'bluejackets', 'DAL': 'stars', 'DET': 'redwings', 'EDM': 'oilers', 'FLA': 'panthers', 'LAK': 'kings', 'MIN': 'wild', 'MTL': 'canadiens', 'NSH': 'predators', 'NJD': 'devils', 'NYI': 'islanders', 'NYR': 'rangers', 'OTT': 'senators', 'PHI': 'flyers', 'PIT': 'penguins', 'SJS': 'sharks', 'SEA': 'kraken', 'STL': 'blues', 'TBL': 'lightning', 'TOR': 'mapleleafs', 'UTA': 'utah', 'VAN': 'canucks', 'VGK': 'goldenknights', 'WSH': 'capitals', 'WPG': 'jets'}

if not st.session_state.authenticated:
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        st.session_state.display_name = USER_DB[saved_email]

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            email = st.text_input("Email").lower().strip()
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30), key="set_auth")
                    st.session_state.authenticated = True
                    st.session_state.gm_name = USER_DB[email]
                    st.session_state.display_name = USER_DB[email]
                    st.rerun()
                else: st.error("Invalid credentials.")
    st.stop()

# --- 4. DATA FETCHING ---
@st.cache_data(ttl=1800)
def fetch_live_playoff_data():
    base_url = "https://api.nhle.com/stats/rest/en/skater/summary"
    params = {"isAggregate": "false", "isGame": "false", "start": 0, "limit": 1000, "cayenneExp": "gameTypeId=3 and seasonId=20252026"}
    try:
        res = requests.get(base_url, params=params, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            df = pd.DataFrame(res.json().get('data', []))
            if not df.empty:
                df.rename(columns={'skaterFullName': 'playerName', 'teamAbbrevs': 'teamAbbrev', 'points': 'totalPoints'}, inplace=True)
                df['playerName'] = df['playerName'].fillna('')
                df['lastName'] = df['playerName'].apply(lambda x: str(x).split(' ', 1)[-1].lower() if ' ' in str(x) else str(x).lower())
                for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                return df
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_historical_points(pids, days):
    cutoff = (datetime.datetime.now(PT_ZONE) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    pts_dict = {}
    for pid in pids:
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/now", headers=HEADERS, timeout=5)
            pts = 0
            if res.status_code == 200:
                for g in res.json().get('gameLog', []):
                    if g.get('gameTypeId') == 3 and g['gameDate'] >= cutoff:
                        pts += g.get('goals', 0) + g.get('assists', 0)
            pts_dict[pid] = pts
        except: pts_dict[pid] = 0
    return pts_dict

@st.cache_data(ttl=3600)
def get_eliminated_teams():
    elim = set()
    try:
        res = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            series = data.get('series', []) if 'series' in data else [s for r in data.get('rounds', []) for s in r.get('series', [])]
            for s in series:
                m = s.get('matchupTeams', [])
                if len(m) == 2:
                    if m[0].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[1].get('teamAbbrev'))
                    if m[1].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[0].get('teamAbbrev'))
    except: pass
    return elim

@st.cache_data(ttl=3600)
def get_teams_playing_today():
    try:
        res = requests.get("https://api-web.nhle.com/v1/schedule/now", headers=HEADERS, timeout=10)
        today_str = datetime.datetime.now(PT_ZONE).strftime("%Y-%m-%d")
        if res.status_code == 200:
            return [t['abbrev'] for d in res.json().get('gameWeek', []) if d['date'] == today_str for g in d.get('games', []) for t in [g['awayTeam'], g['homeTeam']]]
    except: pass
    return []

# --- 5. MAIN HEADER ---
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_img:
    if st.session_state.get('avatar'): st.image(st.session_state.avatar, width=35)
    else: st.markdown("<div style='font-size: 24px; text-align: center; margin-top: -3px;'>👤</div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️"):
        new_disp = st.text_input("Display Name", value=st.session_state.display_name)
        if st.button("Update"): st.session_state.display_name = new_disp; st.rerun()
        file = st.file_uploader("Upload Avatar", type=["jpg", "png", "jpeg"])
        if st.button("Save Avatar") and file: st.session_state.avatar = file.getvalue(); st.rerun()
        if st.button("Log Out"): cookie_manager.delete('user_email_cookie'); st.session_state.authenticated = False; st.rerun()

st.divider()
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default="League", label_visibility="collapsed")

# --- 6. DATA PROCESSING ---
stats = fetch_live_playoff_data()
ELIMINATED_TEAMS = get_eliminated_teams()
TEAMS_PLAYING_TODAY = get_teams_playing_today()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    if 'Draft Rounds' not in df_raw.columns: df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms_cols = [c for c in df_raw.columns if c in USER_DB.values()]
except: st.stop()

def clean_and_match(pick_str, stats_df):
    if pd.isna(pick_str) or str(pick_str).strip() == '': return None
    parts = str(pick_str).split('-'); raw_name = parts[0].strip(); t_part = parts[1].strip().upper() if len(parts) > 1 else ""
    t_part = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}.get(t_part, t_part)
    lookup_df = stats_df[stats_df['teamAbbrev'] == t_part] if not stats_df.empty and t_part else stats_df
    if not lookup_df.empty:
        matches = difflib.get_close_matches(raw_name.lower(), lookup_df['playerName'].str.lower().tolist(), n=1, cutoff=0.35)
        if matches: return lookup_df[lookup_df['playerName'].str.lower() == matches[0]].iloc[0].to_dict()
    return {'playerName': raw_name.title(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '---', 'playerId': None}

master_list = []
for _, row in df_raw.iterrows():
    if "Round" not in str(row.get('Draft Rounds', '')): continue
    for gm in gms_cols:
        pick = str(row.get(gm, '')).strip()
        if not pick or pick.lower() == 'nan': continue
        p = clean_and_match(pick, stats)
        master_list.append({'GM': gm, 'Player_Id': p.get('playerId'), 'Player_Name': p.get('playerName'), 'Team_Raw': p.get('teamAbbrev'), 'Position': p.get('positionCode'), 'Points': p.get('totalPoints', 0), 'G': p.get('goals', 0), 'A': p.get('assists', 0), 'GP': p.get('gamesPlayed', 0), 'Round': str(row['Draft Rounds']).replace("Round", "").strip()})

master_df = pd.DataFrame(master_list)
master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).fillna(0).astype(int)
master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(lambda x: "🥇 1" if x==1 else "🥈 2" if x==2 else "🥉 3" if x==3 else str(x))

if st.session_state.display_name:
    master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    display_gms = sorted([st.session_state.display_name if g == st.session_state.gm_name else g for g in gms_cols])
else:
    display_gms = sorted(gms_cols)

# --- 7. UI VIEWS ---
if nav == "League":
    lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index().sort_values(['Points', 'G'], ascending=False)
    counts = master_df[~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'] = range(1, len(lb)+1)
    lb['Pts Back'] = lb['Points'].max() - lb['Points']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> is the team to beat. <b>{lb.iloc[-1]['GM']}</b> has some work to do.</div>", unsafe_allow_html=True)

    lb_html = "<table class='pool-table'><tr><th>Rank</th><th class='text-left'>Name</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Pts Back</th><th>Remaining Players</th></tr>"
    for _, r in lb.iterrows():
        lb_html += f"<tr><td>{r['Rank']}</td><td class='text-left'><span class='gm-label'>{r['GM']}</span></td><td>{r['GP']}</td><td><b>{r['Points']}</b></td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Pts Back']}</td><td>{int(r['Rem'])}</td></tr>"
    st.markdown(lb_html + "</table>", unsafe_allow_html=True)

elif nav == "My Team":
    current_gm = st.session_state.get('view_gm', st.session_state.display_name if st.session_state.display_name in display_gms else display_gms[0])
    my_df_total = master_df[master_df['GM'] == current_gm]
    
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{current_gm}</b>'s roster.</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1, 1, 1])
    with c1:
        current_gm = st.selectbox("View another team", display_gms, index=display_gms.index(current_gm), key="view_gm")
    with c2:
        horizon = st.selectbox("Stats", ['All Time', 'Yesterday', 'Last 48 Hours', 'Last 7 Days'])
    
    my_df = master_df[master_df['GM'] == current_gm]
    pids = my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY)]['Player_Id'].dropna()
    p_today = sum(get_historical_points(pids, 0).values()) if not pids.empty else 0
    with c3: st.metric("Points Today", p_today)
    with c4: st.metric("Active Today", len(my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY) & ~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))
    with c5: st.metric("Remaining", len(my_df[~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))

    st.markdown("<p style='font-size: 0.85rem; color: #888;'>➤ 🔥 indicates playing today<br>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</p>", unsafe_allow_html=True)
    
    disp_df = my_df.copy()
    if horizon != 'All Time':
        days = {'Yesterday': 1, 'Last 48 Hours': 2, 'Last 7 Days': 7}[horizon]
        hist_data = get_historical_points(disp_df['Player_Id'].dropna(), days)
        disp_df['Points'] = disp_df['Player_Id'].map(hist_data).fillna(0).astype(int)
        disp_df['G'] = "-"; disp_df['A'] = "-"; disp_df['GP'] = "-"; disp_df['Top Pick/Rnd'] = "-"

    t_html = "<table class='pool-table'><tr><th class='text-left'>Round</th><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Top Pick</th></tr>"
    for _, r in disp_df.iterrows():
        is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
        is_playing = r['Team_Raw'] in TEAMS_PLAYING_TODAY and not is_elim
        decor = "line-through" if is_elim else "none"
        active = " 🔥" if is_playing else ""
        t_html += f"<tr style='text-decoration: {decor};'><td>{r['Round']}</td><td class='text-left'>{r['Player_Name']}{active}</td><td>{r['Team_Raw']}</td><td>{r['Position']}</td><td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Top Pick/Rnd']}</td></tr>"
    st.markdown(t_html + "</table>", unsafe_allow_html=True)

elif nav == "All Rosters":
    st.markdown("<p style='font-size: 0.85rem; color: #888; margin-bottom: 20px;'>➤ 🔥 indicates playing today<br>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</p>", unsafe_allow_html=True)
    for g in display_gms:
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        g_df = master_df[master_df['GM'] == g]
        t_html = "<table class='pool-table'><tr><th class='text-left'>Round</th><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th></tr>"
        for _, r in g_df.iterrows():
            is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
            decor = "line-through" if is_elim else "none"
            t_html += f"<tr style='text-decoration: {decor};'><td>{r['Round']}</td><td class='text-left'>{r['Player_Name']}</td><td>{r['Team_Raw']}</td><td>{r['Position']}</td><td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td></tr>"
        st.markdown(t_html + "</table>", unsafe_allow_html=True)
