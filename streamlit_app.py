import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo
import extra_streamlit_components as stx
import difflib
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# --- 1. SESSION & ROUTING INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'sel_gm_val' not in st.session_state: st.session_state.sel_gm_val = None

# Bulletproof Navigation State Management
if 'main_nav' not in st.session_state: st.session_state.main_nav = 'League'
if 'nav_override' not in st.session_state: st.session_state.nav_override = None
if 'last_nav' not in st.session_state: st.session_state.last_nav = 'League'
if 'is_jump' not in st.session_state: st.session_state.is_jump = False

# Handle Safe URL Navigation (Deep Linking)
if "nav" in st.query_params:
    if st.query_params["nav"] == "team":
        st.session_state.nav_override = "My Team"
        st.session_state.sel_gm_val = urllib.parse.unquote(st.query_params.get("gm", ""))
        st.session_state.is_jump = True
    st.query_params.clear()

# --- 2. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

st.markdown("""
    <style>
        /* --- PRIVACY & WHITE-LABELING --- */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > header {display: none;}
        
        /* --- MOBILE SCALING & RESPONSIVENESS --- */
        @media (max-width: 768px) {
            [data-testid="stHorizontalBlock"] {
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                padding-bottom: 5px;
            }
        }

        /* --- GENERAL AESTHETICS --- */
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        hr { margin-top: 0.5em; margin-bottom: 0.5em; }
        
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.8rem 1.2rem; 
            margin-bottom: 1rem;
        }

        /* KPIs */
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
        
        /* Native Table Styling */
        .header-text { 
            color: #888; font-weight: bold; font-size: 13px; 
            text-align: center; border-bottom: 2px solid #ddd; 
            padding-bottom: 5px; margin-bottom: 5px;
            white-space: nowrap;
        }
        .header-left { text-align: left; }
        
        .cell-text { 
            display: flex; align-items: center; justify-content: center;
            height: 40px; font-size: 14px; text-align: center;
            white-space: nowrap;
        }
        .cell-left { justify-content: flex-start; text-align: left; }
        
        /* Links and Aesthetics */
        .player-link { color: #0068c9; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #004c99; }
        .plain-text { color: inherit; }
        .eliminated { text-decoration: line-through; color: #aaa; }
        .news-link { text-decoration: none; font-size: 12px; margin-left: 5px; }
        
        /* Invisible Buttons for GM Links */
        div.stButton { height: 40px; display: flex; align-items: center; justify-content: center; }
        div.stButton > button {
            border: none !important; background: none !important; padding: 0 !important; color: #0068c9 !important;
            text-decoration: none !important; font-size: 14px !important; font-weight: 600 !important; box-shadow: none !important;
        }
        div.stButton > button:hover { text-decoration: underline !important; color: #004c99 !important; }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")
ET_ZONE = ZoneInfo("America/New_York") # Standardizing to NHL Eastern Time
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
TEAM_URLS = {'ANA':'ducks','BOS':'bruins','BUF':'sabres','CGY':'flames','CAR':'hurricanes','CHI':'blackhawks','COL':'avalanche','CBJ':'bluejackets','DAL':'stars','DET':'redwings','EDM':'oilers','FLA':'panthers','LAK':'kings','MIN':'wild','MTL':'canadiens','NSH':'predators','NJD':'devils','NYI':'islanders','NYR':'rangers','OTT':'senators','PHI':'flyers','PIT':'penguins','SJS':'sharks','SEA':'kraken','STL':'blues','TBL':'lightning','TOR':'mapleleafs','UTA':'utah','VAN':'canucks','VGK':'goldenknights','WSH':'capitals','WPG':'jets'}

def is_authenticated():
    if st.session_state.authenticated: return True
    auth_cookie = cookie_manager.get('user_email_cookie')
    if auth_cookie in USER_DB:
        st.session_state.authenticated, st.session_state.gm_name, st.session_state.display_name = True, USER_DB[auth_cookie], USER_DB[auth_cookie]
        return True
    return False

if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Metler Playoff Pool Login")
        with st.form("login"):
            saved = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved).lower().strip()
            pwd = st.text_input("Password", type="password")
            rem = st.checkbox("Remember my email", value=bool(saved))
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    if rem: cookie_manager.set('saved_email_input', email, expires_at=datetime.datetime.now()+datetime.timedelta(days=365), key="k1")
                    else: cookie_manager.delete('saved_email_input', key="k_del")
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now()+datetime.timedelta(days=30), key="k2")
                    st.session_state.authenticated, st.session_state.gm_name, st.session_state.display_name = True, USER_DB[email], USER_DB[email]
                    st.rerun()
                else: st.error("Invalid credentials.")
    st.stop()

# --- 4. STRICT API FETCHING ---
def fetch_single_roster(team):
    res = requests.get(f"https://api-web.nhle.com/v1/roster/{team}/current", headers=HEADERS, timeout=5)
    res.raise_for_status() 
    data = res.json()
    players = []
    for group in ['forwards', 'defensemen']:
        for p in data.get(group, []):
            name = f"{p['firstName']['default']} {p['lastName']['default']}"
            players.append({'playerId': p.get('id'), 'playerName': name, 'playerName_clean': name.lower().replace('.', '').strip(), 'teamAbbrev': team, 'positionCode': p.get('positionCode', '---')})
    return players

@st.cache_data(ttl=3600*12)
def get_all_rosters_parallel():
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_single_roster, TEAM_URLS.keys()))
    return pd.DataFrame([p for sublist in results for p in sublist])

def fetch_playoff_logs(pid):
    try:
        res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/20252026/3", headers=HEADERS, timeout=5)
        res.raise_for_status()
        return {'pid': pid, 'logs': res.json().get('gameLog', [])}
    except: return {'pid': pid, 'logs': []}

@st.cache_data(ttl=1800)
def get_all_historical_points(pids):
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_playoff_logs, pids))
    
    today_str = datetime.datetime.now(ET_ZONE).strftime("%Y-%m-%d")
    yesterday_str = (datetime.datetime.now(ET_ZONE) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    last7_str = (datetime.datetime.now(ET_ZONE) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    last14_str = (datetime.datetime.now(ET_ZONE) - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    last30_str = (datetime.datetime.now(ET_ZONE) - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    data = {}
    for r in results:
        pid, logs = r['pid'], r['logs']
        
        def calc_stats(cond):
            v_logs = [g for g in logs if cond(g['gameDate'])]
            return {
                'pts': sum(g.get('goals', 0) + g.get('assists', 0) for g in v_logs),
                'g': sum(g.get('goals', 0) for g in v_logs),
                'a': sum(g.get('assists', 0) for g in v_logs),
                'gp': len(v_logs)
            }

        data[pid] = {
            'all_time': calc_stats(lambda d: True),
            'today': calc_stats(lambda d: d == today_str),
            'yesterday': calc_stats(lambda d: d == yesterday_str),
            'last7': calc_stats(lambda d: d >= last7_str),
            'last14': calc_stats(lambda d: d >= last14_str),
            'last30': calc_stats(lambda d: d >= last30_str)
        }
    return data

@st.cache_data(ttl=3600)
def get_playoff_status():
    elim, today = set(), []
    try:
        res1 = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026", headers=HEADERS, timeout=5)
        res1.raise_for_status()
        series = res1.json().get('series', []) or [s for r in res1.json().get('rounds', []) for s in r.get('series', [])]
        for s in series:
            m = s.get('matchupTeams', [])
            if len(m) == 2:
                if m[0].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[1].get('teamAbbrev'))
                if m[1].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[0].get('teamAbbrev'))
        res2 = requests.get("https://api-web.nhle.com/v1/schedule/now", headers=HEADERS, timeout=5)
        res2.raise_for_status()
        today_str = datetime.datetime.now(ET_ZONE).strftime("%Y-%m-%d")
        today = [t['abbrev'] for d in res2.json().get('gameWeek', []) if d['date'] == today_str for g in d.get('games', []) for t in [g['awayTeam'], g['homeTeam']]]
    except: pass
    return elim, today

# --- 5. DATA PREPARATION ---
rosters = get_all_rosters_parallel()
ELIMINATED, PLAYING_TODAY = get_playoff_status()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    df_raw.columns = df_raw.columns.str.strip()
    
    def match_p(row):
        name, team = str(row['Player']).lower().replace('.','').strip(), str(row['Acronym']).strip().upper()
        team = {'TB':'TBL','VEGAS':'VGK','VGS':'VGK','MON':'MTL','WAS':'WSH','LA':'LAK'}.get(team, team)
        lookup = rosters[rosters['teamAbbrev'] == team] if team in rosters['teamAbbrev'].values else rosters
        match = difflib.get_close_matches(name, lookup['playerName_clean'].tolist(), n=1, cutoff=0.4)
        if match: return lookup[lookup['playerName_clean'] == match[0]].iloc[0].to_dict()
        return {'playerName': row['Player'], 'playerId': None, 'teamAbbrev': team, 'positionCode': '---'}
    
    master_list = []
    for _, row in df_raw.iterrows():
        p = match_p(row)
        master_list.append({'GM': str(row['GM Owner']).strip(), 'Player_Id': p['playerId'], 'Player_Name': p['playerName'], 'Team': p['teamAbbrev'], 'Pos': p['positionCode'], 'Round': str(row['Round'])})
    master_df = pd.DataFrame(master_list)
    
    pids = master_df['Player_Id'].dropna().unique()
    points_data = get_all_historical_points(pids)
    
    master_df['Pts'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('all_time', {}).get('pts', 0)).fillna(0).astype(int)
    master_df['G'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('all_time', {}).get('g', 0)).fillna(0).astype(int)
    master_df['A'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('all_time', {}).get('a', 0)).fillna(0).astype(int)
    master_df['GP'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('all_time', {}).get('gp', 0)).fillna(0).astype(int)
    
    master_df['Pts_Today'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('today', {}).get('pts', 0))
    master_df['Pts_Yest'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('yesterday', {}).get('pts', 0))
    master_df['Rank_Rnd'] = master_df.groupby('Round')['Pts'].rank(method='min', ascending=False).astype(int)
    master_df['Top_Pick'] = master_df['Rank_Rnd'].apply(lambda x: "🥇 1" if x==1 else "🥈 2" if x==2 else "🥉 3" if x==3 else "-")
    
    if st.session_state.display_name:
        master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    gms = sorted(master_df['GM'].unique().tolist())

except Exception as e:
    st.error("Critical Data Sync Error: Make sure your CSV file is accurate and the NHL API is online.")
    st.stop()

# --- 6. UI HEADER ---
t_logo, t_title, t_text = st.columns([0.6, 6.0, 3.4])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; font-size: 2.6rem;' id='metler-playoff-pool'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)

st.divider()

# --- CLEAN NAVIGATION LOGIC ---
if st.session_state.nav_override:
    st.session_state.main_nav = st.session_state.nav_override
    st.session_state.nav_override = None

selected_nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default=st.session_state.main_nav, label_visibility="collapsed")

if selected_nav and selected_nav != st.session_state.main_nav:
    if selected_nav == "My Team":
        st.session_state.sel_gm_val = st.session_state.display_name
    st.session_state.main_nav = selected_nav
    st.rerun()

nav = st.session_state.main_nav

# --- 7. VIEWS ---
if nav == "League":
    lb = master_df.groupby('GM').agg({'GP':'sum','Pts':'sum','G':'sum','A':'sum','Pts_Yest':'sum'}).reset_index().sort_values(['Pts','G'], ascending=False)
    counts = master_df[~master_df['Team'].isin(ELIMINATED)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'], lb['Back'] = range(1, len(lb)+1), lb['Pts'].max() - lb['Pts']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> leads by {int(lb.iloc[0]['Pts'] - lb.iloc[1]['Pts'])} points.</div>", unsafe_allow_html=True)
    
    h_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
    h_labels = ["Rank", "Name", "GP", "Points", "G", "A", "Pts Yesterday", "Pts Back", "Remaining Players"]
    for i, l in enumerate(h_labels): h_cols[i].markdown(f"<div class='header-text {'header-left' if i==1 else ''}'>{l}</div>", unsafe_allow_html=True)
    
    for _, r in lb.iterrows():
        b_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
        b_cols[0].markdown(f"<div class='cell-text plain-text'><b>{r['Rank']}</b></div>", unsafe_allow_html=True)
        with b_cols[1]:
            if st.button(r['GM'], key=f"nav_{r['GM']}"):
                st.session_state.sel_gm_val = r['GM']
                st.session_state.nav_override = "My Team"
                st.rerun()
        b_cols[2].markdown(f"<div class='cell-text plain-text'>{r['GP']}</div>", unsafe_allow_html=True)
        b_cols[3].markdown(f"<div class='cell-text plain-text'><b>{int(r['Pts'])}</b></div>", unsafe_allow_html=True)
        b_cols[4].markdown(f"<div class='cell-text plain-text'>{r['G']}</div>", unsafe_allow_html=True)
        b_cols[5].markdown(f"<div class='cell-text plain-text'>{r['A']}</div>", unsafe_allow_html=True)
        b_cols[6].markdown(f"<div class='cell-text plain-text'>{int(r['Pts_Yest'])}</div>", unsafe_allow_html=True)
        b_cols[7].markdown(f"<div class='cell-text plain-text'>{r['Back']}</div>", unsafe_allow_html=True)
        b_cols[8].markdown(f"<div class='cell-text plain-text'>{int(r['Rem'])}</div>", unsafe_allow_html=True)

elif nav == "My Team":
    if not st.session_state.sel_gm_val or st.session_state.sel_gm_val not in gms:
        st.session_state.sel_gm_val = st.session_state.display_name if st.session_state.display_name in gms else gms[0]
    
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{st.session_state.sel_gm_val}</b>'s roster.</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.4, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1])
    with c1: 
        curr = st.selectbox("View another team", gms, index=gms.index(st.session_state.sel_gm_val), key="dropdown")
        if curr != st.session_state.sel_gm_val:
            st.session_state.sel_gm_val = curr
            st.rerun()
    with c2: horizon = st.selectbox("Stats Filter", ['All Time', 'Yesterday', 'Last 7 Days', 'Last 14 Days', 'Last 30 Days'], key="horiz1")
    
    my_df = master_df[master_df['GM'] == st.session_state.sel_gm_val].copy()
    
    with c3: st.metric("Total Pts", int(my_df['Pts'].sum()))
    with c4: st.metric("Points Today", int(my_df['Pts_Today'].sum()))
    with c5: st.metric("Points Yesterday", int(my_df['Pts_Yest'].sum()))
    with c6: st.metric("Players Active Today", len(my_df[my_df['Team'].isin(PLAYING_TODAY) & ~my_df['Team'].isin(ELIMINATED)]))
    with c7: st.metric("Players Remaining", len(my_df[~my_df['Team'].isin(ELIMINATED)]))

    st.markdown("<p style='font-size: 0.85rem; color: #888;'>➤ 🔥 indicates playing today<br>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</p>", unsafe_allow_html=True)

    if horizon != 'All Time':
        key_map = {'Yesterday':'yesterday', 'Last 7 Days':'last7', 'Last 14 Days':'last14', 'Last 30 Days':'last30'}
        h_key = key_map[horizon]
        
        my_df['Pts'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('pts', 0)).fillna(0).astype(int)
        my_df['G'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('g', 0)).fillna(0).astype(int)
        my_df['A'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('a', 0)).fillna(0).astype(int)
        my_df['GP'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('gp', 0)).fillna(0).astype(int)

    my_df = my_df.sort_values('Pts', ascending=False)
    
    t_cols = st.columns([2.0, 0.8, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
    t_labels = ["Player", "Team", "Pos", "GP", "Points", "G", "A", "Round Picked", "Top Pick/Rnd"]
    for i, l in enumerate(t_labels): t_cols[i].markdown(f"<div class='header-text {'header-left' if i==0 else ''}'>{l}</div>", unsafe_allow_html=True)
    
    for _, r in my_df.iterrows():
        r_cols = st.columns([2.0, 0.8, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
        is_elim = r['Team'] in ELIMINATED
        t_cls = "eliminated" if is_elim else "plain-text"
        l_cls = "eliminated" if is_elim else "player-link"
        fire = " 🔥" if r['Team'] in PLAYING_TODAY and not is_elim else ""
        
        p_url = f"https://www.nhl.com/player/{int(r['Player_Id'])}" if r['Player_Id'] else "#"
        n_url = f"https://news.google.com/search?q={str(r['Player_Name']).replace(' ','+')}+NHL"
        t_url = f"https://www.nhl.com/{TEAM_URLS.get(r['Team'], r['Team'].lower())}/"
        
        r_cols[0].markdown(f"<div class='cell-text cell-left'><a href='{p_url}' target='_blank' class='{l_cls}'>{r['Player_Name']}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{fire}</div>", unsafe_allow_html=True)
        r_cols[1].markdown(f"<div class='cell-text'><a href='{t_url}' target='_blank' class='{l_cls}'>{r['Team']}</a></div>", unsafe_allow_html=True)
        r_cols[2].markdown(f"<div class='cell-text {t_cls}'>{r['Pos']}</div>", unsafe_allow_html=True)
        r_cols[3].markdown(f"<div class='cell-text {t_cls}'>{r['GP']}</div>", unsafe_allow_html=True)
        r_cols[4].markdown(f"<div class='cell-text {t_cls}'><b>{r['Pts']}</b></div>", unsafe_allow_html=True)
        r_cols[5].markdown(f"<div class='cell-text {t_cls}'>{r['G']}</div>", unsafe_allow_html=True)
        r_cols[6].markdown(f"<div class='cell-text {t_cls}'>{r['A']}</div>", unsafe_allow_html=True)
        r_cols[7].markdown(f"<div class='cell-text {t_cls}'>{r['Round']}</div>", unsafe_allow_html=True)
        r_cols[8].markdown(f"<div class='cell-text {t_cls}'>{r['Top_Pick']}</div>", unsafe_allow_html=True)

elif nav == "All Rosters":
    c1, c2, c3 = st.columns([1.5, 1.2, 7.3])
    with c1: 
        if 'all_rost_jump' not in st.session_state: st.session_state.all_rost_jump = "(Select Team)"
        jump_gm = st.selectbox("View another team", ["(Select Team)"] + gms, key="all_rost_jump")
        if jump_gm != "(Select Team)":
            st.session_state.sel_gm_val = jump_gm
            st.session_state.nav_override = "My Team"
            st.session_state.all_rost_jump = "(Select Team)"
            st.rerun()
            
    with c2: horizon = st.selectbox("Stats Filter", ['All Time', 'Yesterday', 'Last 7 Days', 'Last 14 Days', 'Last 30 Days'], key="horiz2")
    
    total_df = master_df.copy()
    if horizon != 'All Time':
        key_map = {'Yesterday':'yesterday', 'Last 7 Days':'last7', 'Last 14 Days':'last14', 'Last 30 Days':'last30'}
        h_key = key_map[horizon]
        
        total_df['Pts'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('pts', 0)).fillna(0).astype(int)
        total_df['G'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('g', 0)).fillna(0).astype(int)
        total_df['A'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('a', 0)).fillna(0).astype(int)
        total_df['GP'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('gp', 0)).fillna(0).astype(int)

    gm_totals = total_df.groupby('GM')['Pts'].sum().reset_index().sort_values('Pts', ascending=False)
    sorted_gms = gm_totals['GM'].tolist()
    
    # Anchor Links matching the right alignment
    anchor_html = " | ".join([f"<a href='#{g.replace(' ', '-').lower()}' style='color:#0068c9; text-decoration:none; font-weight:bold; margin:0 5px;'>{g}</a>" for g in sorted_gms])
    
    st.markdown(f"""
        <div style='font-size: 0.85rem; color: #888; margin-bottom: 20px;'>
            <div style='margin-bottom: 5px;'>➤ 🔥 indicates playing today</div>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</div>
                <div style='text-align: right;'>{anchor_html}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    for g in sorted_gms:
        gm_pts = gm_totals.loc[gm_totals['GM'] == g, 'Pts'].iloc[0]
        
        hc1, hc2 = st.columns([9, 1])
        with hc1:
            st.subheader(f"{g} ({gm_pts} Points)", anchor=g.replace(' ', '-').lower())
        with hc2:
            st.markdown("<div style='text-align:right; margin-top:15px;'><a href='#metler-playoff-pool' style='color:#0068c9; text-decoration:none; font-size:14px; font-weight:500;'>[↑ Back to Top]</a></div>", unsafe_allow_html=True)
            
        g_df = total_df[total_df['GM'] == g].sort_values('Pts', ascending=False)
        
        t_cols = st.columns([2.0, 0.8, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
        t_labels = ["Player", "Team", "Pos", "GP", "Points", "G", "A", "Round Picked", "Top Pick/Rnd"]
        for i, l in enumerate(t_labels): t_cols[i].markdown(f"<div class='header-text {'header-left' if i==0 else ''}'>{l}</div>", unsafe_allow_html=True)
        
        for _, r in g_df.iterrows():
            r_cols = st.columns([2.0, 0.8, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
            is_elim = r['Team'] in ELIMINATED
            t_cls = "eliminated" if is_elim else "plain-text"
            l_cls = "eliminated" if is_elim else "player-link"
            fire = " 🔥" if r['Team'] in PLAYING_TODAY and not is_elim else ""
            
            p_url = f"https://www.nhl.com/player/{int(r['Player_Id'])}" if r['Player_Id'] else "#"
            n_url = f"https://news.google.com/search?q={str(r['Player_Name']).replace(' ','+')}+NHL"
            t_url = f"https://www.nhl.com/{TEAM_URLS.get(r['Team'], r['Team'].lower())}/"
            
            r_cols[0].markdown(f"<div class='cell-text cell-left'><a href='{p_url}' target='_blank' class='{l_cls}'>{r['Player_Name']}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{fire}</div>", unsafe_allow_html=True)
            r_cols[1].markdown(f"<div class='cell-text'><a href='{t_url}' target='_blank' class='{l_cls}'>{r['Team']}</a></div>", unsafe_allow_html=True)
            r_cols[2].markdown(f"<div class='cell-text {t_cls}'>{r['Pos']}</div>", unsafe_allow_html=True)
            r_cols[3].markdown(f"<div class='cell-text {t_cls}'>{r['GP']}</div>", unsafe_allow_html=True)
            r_cols[4].markdown(f"<div class='cell-text {t_cls}'><b>{r['Pts']}</b></div>", unsafe_allow_html=True)
            r_cols[5].markdown(f"<div class='cell-text {t_cls}'>{r['G']}</div>", unsafe_allow_html=True)
            r_cols[6].markdown(f"<div class='cell-text {t_cls}'>{r['A']}</div>", unsafe_allow_html=True)
            r_cols[7].markdown(f"<div class='cell-text {t_cls}'>{r['Round']}</div>", unsafe_allow_html=True)
            r_cols[8].markdown(f"<div class='cell-text {t_cls}'>{r['Top_Pick']}</div>", unsafe_allow_html=True)
