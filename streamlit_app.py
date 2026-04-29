import streamlit as st
import pandas as pd
import requests
import datetime
import time
from zoneinfo import ZoneInfo
import extra_streamlit_components as stx
import difflib
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# MANUAL OVERRIDE CONFIGURATION
# ==========================================
# If the NHL API is slow to update, add eliminated team acronyms here.
# Example: MANUAL_ELIMINATED = ["TOR", "BOS", "LAK"]
MANUAL_ELIMINATED = []

# --- 1. SESSION MEMORY ---
if 'main_nav' not in st.session_state: st.session_state.main_nav = 'League'
if 'sel_gm_val' not in st.session_state: st.session_state.sel_gm_val = None
if 'display_name' not in st.session_state: st.session_state.display_name = "Guest"
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

# --- 2. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > header {display: none;}
        
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        hr { margin-top: 0.5em; margin-bottom: 0.5em; }
        
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.8rem 1.2rem; 
            margin-bottom: 1rem;
        }

        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
        
        /* PURE HTML TABLE STYLING */
        .table-header { 
            display: flex; font-weight: bold; border-bottom: 2px solid #ddd; 
            padding-bottom: 5px; margin-bottom: 5px; color: #888; font-size: 13px; text-align: center; 
        }
        .table-row { 
            display: flex; align-items: center; justify-content: center; 
            height: 40px; font-size: 14px; text-align: center; border-bottom: 1px solid #f9f9f9;
        }
        .table-row:hover { background-color: #f1f8ff; }
        .cell-left { text-align: left !important; justify-content: flex-start !important; }
        .header-left { text-align: left !important; }
        
        /* NATIVE LEAGUE TABLE STYLING */
        .header-text { 
            color: #888; font-weight: bold; font-size: 13px; 
            text-align: center; border-bottom: 2px solid #ddd; 
            padding-bottom: 5px; margin-bottom: 5px;
            white-space: nowrap;
        }
        .cell-text { 
            display: flex; align-items: center; justify-content: center;
            height: 40px; font-size: 14px; text-align: center;
            white-space: nowrap; border-bottom: 1px solid #f9f9f9;
        }
        
        /* CRITICAL: Make Streamlit buttons look exactly like HTML links */
        [data-testid="stButton"] {
            height: 40px; 
            display: flex; 
            align-items: center; 
            justify-content: flex-start; 
            border-bottom: 1px solid #f9f9f9;
        }
        [data-testid="stButton"] > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #0068c9 !important;
            padding: 0 !important;
            min-height: 0 !important;
            height: auto !important;
            line-height: normal !important;
            display: flex !important;
            justify-content: flex-start !important;
        }
        [data-testid="stButton"] > button:hover {
            text-decoration: underline !important;
            color: #004c99 !important;
            background: transparent !important;
        }
        [data-testid="stButton"] > button p {
            font-size: 14px !important;
            font-weight: 600 !important;
            margin: 0 !important;
        }
        
        /* HTML View Columns */
        .r-name { width: 24%; display: flex; align-items: center; justify-content: flex-start; text-align: left; }
        .r-team { width: 8%; }
        .r-pos { width: 8%; }
        .r-gp { width: 8%; }
        .r-pts { width: 10%; }
        .r-yest { width: 10%; }
        .r-g { width: 8%; }
        .r-a { width: 8%; }
        .r-rnd { width: 8%; }
        .r-top { width: 8%; }
        
        /* Links */
        .player-link { color: #0068c9; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #004c99; }
        .eliminated { text-decoration: line-through; color: #aaa; }
        .news-link { text-decoration: none; font-size: 12px; margin-left: 5px; }
        
        /* MOBILE PORTRAIT OPTIMIZATION */
        @media (max-width: 768px) and (orientation: portrait) {
            .hide-portrait { display: none !important; width: 0 !important; overflow: hidden !important; }
            
            /* Native League Table Selection */
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) { flex-wrap: nowrap !important; }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(3),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(5),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(6),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(8),
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(9) {
                display: none !important; width: 0 !important; flex: 0 0 0 !important; padding: 0 !important; margin: 0 !important; overflow: hidden !important;
            }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(1) { flex: 1 1 15% !important; width: 15% !important; }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(2) { flex: 1 1 45% !important; width: 45% !important; }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(4) { flex: 1 1 20% !important; width: 20% !important; }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(9)):not(:has(> [data-testid="column"]:nth-child(10))) > [data-testid="column"]:nth-child(7) { flex: 1 1 20% !important; width: 20% !important; }

            .r-name { width: 50%; }
            .r-pts { width: 25%; }
            .r-yest { width: 25%; }
            
            .table-row, .table-header, .cell-text, .header-text { font-size: 11px; }
            .table-row > div, .table-header > div, .cell-text { white-space: normal; line-height: 1.2; padding: 0 2px; }
            .news-link { display: none !important; }
            div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
            div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div id='top-of-page'></div>", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")
ET_ZONE = ZoneInfo("America/New_York")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

# --- 3. CLEAN & SAFE AUTHENTICATION GATE ---
GM_ROSTER = ["Mike", "Rhys", "Big M", "Pete", "Torrie", "Jay", "Duncs", "Trakas", "Gardner", "Aaron"]

if not st.session_state.authenticated and hasattr(st, 'context') and hasattr(st.context, 'cookies'):
    val = st.context.cookies.get('user_identity_cookie')
    if val in GM_ROSTER:
        st.session_state.authenticated = True
        st.session_state.display_name = val

if not st.session_state.authenticated:
    val = cookie_manager.get('user_identity_cookie')
    if val in GM_ROSTER:
        st.session_state.authenticated = True
        st.session_state.display_name = val

if not st.session_state.authenticated:
    if 'first_render' not in st.session_state:
        st.session_state.first_render = False
        st.stop() # Wait 1 render cycle for cookie to catch up
        
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Metler Playoff Pool")
        with st.form("login"):
            st.markdown("### Welcome! Who are you?")
            selected_gm = st.selectbox("Select your GM Profile", sorted(GM_ROSTER))
            if st.form_submit_button("Enter Pool"):
                cookie_manager.set('user_identity_cookie', selected_gm, expires_at=datetime.datetime.now()+datetime.timedelta(days=3650), key="k2")
                st.session_state.authenticated = True
                st.session_state.display_name = selected_gm
                st.rerun()
    st.stop()

# --- 4. STRICT API FETCHING ---
TEAM_URLS = {'ANA':'ducks','BOS':'bruins','BUF':'sabres','CGY':'flames','CAR':'hurricanes','CHI':'blackhawks','COL':'avalanche','CBJ':'bluejackets','DAL':'stars','DET':'redwings','EDM':'oilers','FLA':'panthers','LAK':'kings','MIN':'wild','MTL':'canadiens','NSH':'predators','NJD':'devils','NYI':'islanders','NYR':'rangers','OTT':'senators','PHI':'flyers','PIT':'penguins','SJS':'sharks','SEA':'kraken','STL':'blues','TBL':'lightning','TOR':'mapleleafs','UTA':'utah','VAN':'canucks','VGK':'goldenknights','WSH':'capitals','WPG':'jets'}

def get_team_url(team_val):
    try:
        t = str(team_val).strip()
        if pd.isna(team_val) or not t or t.lower() == 'nan': return "#"
        return f"https://www.nhl.com/{TEAM_URLS.get(t, t.lower())}/"
    except: return "#"

def get_player_url(pid_val):
    try:
        if pd.isna(pid_val): return "#"
        return f"https://www.nhl.com/player/{int(float(pid_val))}"
    except: return "#"

def get_news_url(name_val):
    try:
        n = str(name_val).strip()
        if pd.isna(name_val) or not n or n.lower() == 'nan': return "#"
        return f"https://news.google.com/search?q={urllib.parse.quote(n)}+NHL"
    except: return "#"

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
def get_playoff_status_v5():
    elim, today = set(), []
    
    # 1. APPLY MANUAL OVERRIDES
    if 'MANUAL_ELIMINATED' in globals():
        for t in MANUAL_ELIMINATED:
            elim.add(str(t).strip().upper())
            
    # 2. DYNAMIC NHL API HUNTER
    def _find_elim(node):
        if isinstance(node, dict):
            if 'matchupTeams' in node and isinstance(node['matchupTeams'], list) and len(node['matchupTeams']) == 2:
                try:
                    m = node['matchupTeams']
                    t1 = m[0].get('team', {}).get('abbrev') or m[0].get('teamAbbrev') or m[0].get('abbrev') or ""
                    t2 = m[1].get('team', {}).get('abbrev') or m[1].get('teamAbbrev') or m[1].get('abbrev') or ""
                    
                    w1 = int(m[0].get('seriesRecord', {}).get('wins', m[0].get('wins', 0)))
                    w2 = int(m[1].get('seriesRecord', {}).get('wins', m[1].get('wins', 0)))
                    
                    if w1 == 4 and t2: elim.add(str(t2).upper())
                    if w2 == 4 and t1: elim.add(str(t1).upper())
                except Exception:
                    pass
            for v in node.values():
                _find_elim(v)
        elif isinstance(node, list):
            for item in node:
                _find_elim(item)

    urls_to_try = [
        "https://api-web.nhle.com/v1/playoff-bracket/2026",
        "https://api-web.nhle.com/v1/playoff-bracket/20252026",
        "https://api-web.nhle.com/v1/playoff-bracket/2025"
    ]
    
    for url in urls_to_try:
        try:
            res1 = requests.get(url, headers=HEADERS, timeout=5)
            if res1.status_code == 200:
                _find_elim(res1.json())
        except Exception:
            continue 
            
    try:
        res2 = requests.get("https://api-web.nhle.com/v1/schedule/now", headers=HEADERS, timeout=5)
        if res2.status_code == 200:
            today_str = datetime.datetime.now(ET_ZONE).strftime("%Y-%m-%d")
            for d in res2.json().get('gameWeek', []):
                if d['date'] == today_str:
                    for g in d.get('games', []):
                        t1 = g.get('awayTeam', {}).get('abbrev')
                        t2 = g.get('homeTeam', {}).get('abbrev')
                        if t1: today.append(t1)
                        if t2: today.append(t2)
    except Exception:
        pass
    
    return elim, today

# --- 5. DATA PREPARATION ---
rosters = get_all_rosters_parallel()
ELIMINATED, PLAYING_TODAY = get_playoff_status_v5()

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
    
    gms = sorted(master_df['GM'].unique().tolist())

except Exception as e:
    st.error("Critical Data Sync Error: Make sure your CSV file is accurate and the NHL API is online.")
    st.stop()

# --- 6. UI HEADER ---
t_logo, t_title, t_text = st.columns([0.6, 6.0, 3.4])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: 
    st.title("Metler Playoff Pool")
with t_text: 
    st.markdown(f"<div style='text-align: right; margin-top: 20px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)

st.divider()

# --- CLEAN NAVIGATION LOGIC ---
selected_nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default=st.session_state.main_nav, label_visibility="collapsed")

if selected_nav and selected_nav != st.session_state.main_nav:
    st.session_state.main_nav = selected_nav
    if selected_nav == "My Team":
        st.session_state.sel_gm_val = st.session_state.display_name if st.session_state.display_name in gms else gms[0]
    st.rerun()

nav = st.session_state.main_nav

# --- 7. VIEWS ---
if nav == "League":
    lb = master_df.groupby('GM').agg({'GP':'sum','Pts':'sum','G':'sum','A':'sum','Pts_Yest':'sum'}).reset_index().sort_values(['Pts','G'], ascending=False)
    counts = master_df[~master_df['Team'].isin(ELIMINATED)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'], lb['Back'] = range(1, len(lb)+1), lb['Pts'].max() - lb['Pts']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> leads by {int(lb.iloc[0]['Pts'] - lb.iloc[1]['Pts'])} points.</div>", unsafe_allow_html=True)
    
    # NATIVE COLUMNS for the League Table (Zero browser reloads = zero login loops)
    h_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
    h_labels = ["Rank", "Name", "GP", "Points", "G", "A", "Pts Yest", "Pts Back", "Remaining"]
    for i, l in enumerate(h_labels):
        css_hide = "hide-portrait" if i not in [0, 1, 3, 6] else ""
        h_cols[i].markdown(f"<div class='header-text {'header-left' if i==1 else ''} {css_hide}'>{l}</div>", unsafe_allow_html=True)
    
    for _, r in lb.iterrows():
        b_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
        b_cols[0].markdown(f"<div class='cell-text'><b>{r['Rank']}</b></div>", unsafe_allow_html=True)
        with b_cols[1]:
            # This is a WebSocket Button disguised flawlessly as a Hyperlink via CSS
            if st.button(r['GM'], key=f"nav_{r['GM']}"):
                st.session_state.sel_gm_val = r['GM']
                st.session_state.main_nav = "My Team"
                st.rerun()
        b_cols[2].markdown(f"<div class='cell-text hide-portrait'>{r['GP']}</div>", unsafe_allow_html=True)
        b_cols[3].markdown(f"<div class='cell-text'><b>{int(r['Pts'])}</b></div>", unsafe_allow_html=True)
        b_cols[4].markdown(f"<div class='cell-text hide-portrait'>{r['G']}</div>", unsafe_allow_html=True)
        b_cols[5].markdown(f"<div class='cell-text hide-portrait'>{r['A']}</div>", unsafe_allow_html=True)
        b_cols[6].markdown(f"<div class='cell-text'>{int(r['Pts_Yest'])}</div>", unsafe_allow_html=True)
        b_cols[7].markdown(f"<div class='cell-text hide-portrait'>{r['Back']}</div>", unsafe_allow_html=True)
        b_cols[8].markdown(f"<div class='cell-text hide-portrait'>{int(r['Rem'])}</div>", unsafe_allow_html=True)

elif nav == "My Team":
    if not st.session_state.sel_gm_val or st.session_state.sel_gm_val not in gms:
        st.session_state.sel_gm_val = st.session_state.display_name if st.session_state.display_name in gms else gms[0]
    
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{st.session_state.sel_gm_val}</b>'s roster.</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.4, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1])
    with c1: 
        curr = st.selectbox("Other Teams", gms, index=gms.index(st.session_state.sel_gm_val), key="dropdown")
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

    st.markdown("""
        <div style='font-size: 0.85rem; color: #888; margin-bottom: 15px;'>
            <div>➤ 🔥 indicates playing today</div>
            <div>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</div>
            <div>➤ 🥇 🥈 🥉 indicates the 1st, 2nd, and 3rd highest scoring pick in their respective draft round</div>
        </div>
    """, unsafe_allow_html=True)

    if horizon != 'All Time':
        key_map = {'Yesterday':'yesterday', 'Last 7 Days':'last7', 'Last 14 Days':'last14', 'Last 30 Days':'last30'}
        h_key = key_map[horizon]
        
        my_df['Pts'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('pts', 0)).fillna(0).astype(int)
        my_df['G'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('g', 0)).fillna(0).astype(int)
        my_df['A'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('a', 0)).fillna(0).astype(int)
        my_df['GP'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('gp', 0)).fillna(0).astype(int)

    my_df = my_df.sort_values('Pts', ascending=False)
    
    st.markdown("""
        <div class='table-header'>
            <div class='r-name header-left'>Player</div>
            <div class='r-team hide-portrait'>Team</div>
            <div class='r-pos hide-portrait'>Pos</div>
            <div class='r-gp hide-portrait'>GP</div>
            <div class='r-pts'>Points</div>
            <div class='r-yest'>Pts Yest</div>
            <div class='r-g hide-portrait'>G</div>
            <div class='r-a hide-portrait'>A</div>
            <div class='r-rnd hide-portrait'>Round Picked</div>
            <div class='r-top hide-portrait'>Top Pick/Rnd</div>
        </div>
    """, unsafe_allow_html=True)
    
    html_rows = []
    for _, r in my_df.iterrows():
        safe_team = str(r['Team']).strip().upper() if pd.notna(r['Team']) else ""
        is_elim = safe_team in ELIMINATED
        t_cls = "eliminated" if is_elim else ""
        l_cls = "eliminated" if is_elim else "player-link"
        fire = " 🔥" if safe_team in PLAYING_TODAY and not is_elim else ""
        
        p_name = str(r['Player_Name']).strip() if pd.notna(r['Player_Name']) else "Unknown"
        p_url = get_player_url(r['Player_Id'])
        n_url = get_news_url(r['Player_Name'])
        t_url = get_team_url(r['Team'])
        
        row_html = f"""
        <div class='table-row'>
            <div class='r-name cell-left'><a href='{p_url}' target='_blank' class='{l_cls}'>{p_name}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{fire}</div>
            <div class='r-team hide-portrait'><a href='{t_url}' target='_blank' class='{l_cls}'>{safe_team}</a></div>
            <div class='r-pos hide-portrait {t_cls}'>{r['Pos']}</div>
            <div class='r-gp hide-portrait {t_cls}'>{r['GP']}</div>
            <div class='r-pts {t_cls}'><b>{r['Pts']}</b></div>
            <div class='r-yest {t_cls}'>{r['Pts_Yest']}</div>
            <div class='r-g hide-portrait {t_cls}'>{r['G']}</div>
            <div class='r-a hide-portrait {t_cls}'>{r['A']}</div>
            <div class='r-rnd hide-portrait {t_cls}'>{r['Round']}</div>
            <div class='r-top hide-portrait {t_cls}'>{r['Top_Pick']}</div>
        </div>
        """
        html_rows.append(row_html)
    st.markdown("".join(html_rows), unsafe_allow_html=True)

elif nav == "All Rosters":
    
    c1, c2 = st.columns([2, 8])
    with c1: horizon = st.selectbox("Stats Filter", ['All Time', 'Yesterday', 'Last 7 Days', 'Last 14 Days', 'Last 30 Days'], key="horiz2")
    
    total_df = master_df.copy()
    if horizon != 'All Time':
        key_map = {'Yesterday':'yesterday', 'Last 7 Days':'last7', 'Last 14 Days':'last14', 'Last 30 Days':'last30'}
        h_key = key_map[horizon]
        
        total_df['Pts'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('pts', 0)).fillna(0).astype(int)
        total_df['G'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('g', 0)).fillna(0).astype(int)
        total_df['A'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('a', 0)).fillna(0).astype(int)
        total_df['GP'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('gp', 0)).fillna(0).astype(int)

    gm_totals = total_df.groupby('GM')['Pts'].sum().reset_index().sort_values('Pts', ascending=False)
    sorted_gms = gm_totals['GM'].tolist()
    
    def make_anchor(name):
        return "".join([c for c in name if c.isalnum()]).lower()

    c_leg, c_jump = st.columns([1.5, 2.5])
    with c_leg:
        st.markdown("""
            <div style='font-size: 0.85rem; color: #888;'>
                <div>➤ 🔥 indicates playing today</div>
                <div>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</div>
                <div>➤ 🥇 🥈 🥉 indicates the 1st, 2nd, and 3rd highest scoring pick in their respective draft round</div>
            </div>
        """, unsafe_allow_html=True)
    with c_jump:
        st.write("") 
        anchor_html = " | ".join([f"<a href='#{make_anchor(g)}' target='_self' style='color:#0068c9; text-decoration:none; font-weight:bold;'>{g}</a>" for g in sorted_gms])
        st.markdown(f"<div style='text-align:right; margin-top: 5px;'><b>Jump to:</b> {anchor_html}</div>", unsafe_allow_html=True)
    
    st.divider()

    for g in sorted_gms:
        gm_pts = gm_totals.loc[gm_totals['GM'] == g, 'Pts'].iloc[0]
        
        st.markdown(f"<div id='{make_anchor(g)}' style='position: relative; top: -50px;'></div>", unsafe_allow_html=True)
        
        hc1, hc2 = st.columns([8, 2])
        with hc1:
            st.subheader(f"{g} ({gm_pts} Points)")
        with hc2:
            st.markdown("<div style='margin-top: 15px; text-align:right;'><a href='#top-of-page' target='_self' style='color:#0068c9; text-decoration:none; font-weight:bold;'>[↑ Back to Top]</a></div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px; border-top: 2px solid #0068c9;'>", unsafe_allow_html=True)
        
        st.markdown("""
            <div class='table-header'>
                <div class='r-name header-left'>Player</div>
                <div class='r-team hide-portrait'>Team</div>
                <div class='r-pos hide-portrait'>Pos</div>
                <div class='r-gp hide-portrait'>GP</div>
                <div class='r-pts'>Points</div>
                <div class='r-yest'>Pts Yest</div>
                <div class='r-g hide-portrait'>G</div>
                <div class='r-a hide-portrait'>A</div>
                <div class='r-rnd hide-portrait'>Round Picked</div>
                <div class='r-top hide-portrait'>Top Pick/Rnd</div>
            </div>
        """, unsafe_allow_html=True)
        
        g_df = total_df[total_df['GM'] == g].sort_values('Pts', ascending=False)
        
        html_rows = []
        for _, r in g_df.iterrows():
            safe_team = str(r['Team']).strip().upper() if pd.notna(r['Team']) else ""
            is_elim = safe_team in ELIMINATED
            t_cls = "eliminated" if is_elim else ""
            l_cls = "eliminated" if is_elim else "player-link"
            fire = " 🔥" if safe_team in PLAYING_TODAY and not is_elim else ""
            
            p_name = str(r['Player_Name']).strip() if pd.notna(r['Player_Name']) else "Unknown"
            p_url = get_player_url(r['Player_Id'])
            n_url = get_news_url(r['Player_Name'])
            t_url = get_team_url(r['Team'])
            
            row_html = f"""
            <div class='table-row'>
                <div class='r-name cell-left'><a href='{p_url}' target='_blank' class='{l_cls}'>{p_name}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{fire}</div>
                <div class='r-team hide-portrait'><a href='{t_url}' target='_blank' class='{l_cls}'>{safe_team}</a></div>
                <div class='r-pos hide-portrait {t_cls}'>{r['Pos']}</div>
                <div class='r-gp hide-portrait {t_cls}'>{r['GP']}</div>
                <div class='r-pts {t_cls}'><b>{r['Pts']}</b></div>
                <div class='r-yest {t_cls}'>{r['Pts_Yest']}</div>
                <div class='r-g hide-portrait {t_cls}'>{r['G']}</div>
                <div class='r-a hide-portrait {t_cls}'>{r['A']}</div>
                <div class='r-rnd hide-portrait {t_cls}'>{r['Round']}</div>
                <div class='r-top hide-portrait {t_cls}'>{r['Top_Pick']}</div>
            </div>
            """
            html_rows.append(row_html)
        st.markdown("".join(html_rows), unsafe_allow_html=True)
