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
        
        /* --- PURE HTML TABLE STYLING --- */
        .table-header { 
            display: flex; border-bottom: 2px solid #ddd; 
            padding-bottom: 5px; margin-bottom: 5px; 
        }
        .table-header > div {
            color: #888; font-weight: bold; font-size: 13px; text-align: center; white-space: nowrap;
        }
        
        .table-row { 
            display: flex; align-items: center; justify-content: center; 
            height: 40px; border-bottom: 1px solid #f9f9f9;
        }
        .table-row > div {
            font-size: 14px; text-align: center; white-space: nowrap;
        }
        .table-row:hover { background-color: #f1f8ff; }
        
        .cell-left { text-align: left !important; justify-content: flex-start !important; }
        .header-left { text-align: left !important; }
        
        /* League View Columns */
        .l-rank { width: 8%; }
        .l-name { width: 24%; display: flex; align-items: center; justify-content: flex-start; text-align: left; }
        .l-gp { width: 8%; }
        .l-pts { width: 12%; }
        .l-g { width: 8%; }
        .l-a { width: 8%; }
        .l-yest { width: 12%; }
        .l-back { width: 10%; }
        .l-rem { width: 10%; }

        /* Roster View Columns */
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
        
        /* Links and Aesthetics */
        .player-link { color: #0068c9; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #004c99; }
        .plain-text { color: inherit; }
        .eliminated { text-decoration: line-through; color: #aaa; }
        .news-link { text-decoration: none; font-size: 12px; margin-left: 5px; }
        
        /* GM Header with Back to Top */
        .gm-header-bar {
            display: flex; justify-content: space-between; align-items: flex-end; 
            border-bottom: 2px solid #0068c9; padding-bottom: 5px; margin-bottom: 10px; margin-top: 30px;
        }
        .gm-header-bar h3 { color: #0068c9; margin: 0; padding: 0; }
        
        /* --- MOBILE PORTRAIT OPTIMIZATION --- */
        @media (max-width: 768px) and (orientation: portrait) {
            .hide-mobile { display: none !important; width: 0 !important; overflow: hidden !important; }
            
            /* Resize Remaining League Columns */
            .l-rank { width: 15%; }
            .l-name { width: 45%; }
            .l-pts { width: 20%; }
            .l-yest { width: 20%; }

            /* Resize Remaining Roster Columns */
            .r-name { width: 50%; }
            .r-pts { width: 25%; }
            .r-yest { width: 25%; }
            
            /* Shrink Text to Fit Vertically */
            .table-row > div, .table-header > div { font-size: 12px; white-space: normal; line-height: 1.2; padding: 0 2px; }
            .news-link { display: none !important; }
            
            /* Shrink KPIs */
            div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
            div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
        }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")
ET_ZONE = ZoneInfo("America/New_York")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

# --- 3. PASSWORDLESS AUTHENTICATION ---
GM_ROSTER = ["Mike", "Rhys", "Big M", "Pete", "Torrie", "Jay", "Duncs", "Trakas", "Gardner", "Aaron"]

def is_authenticated():
    if st.session_state.authenticated: return True
    auth_cookie = cookie_manager.get('user_identity_cookie')
    if auth_cookie in GM_ROSTER:
        st.session_state.authenticated, st.session_state.gm_name, st.session_state.display_name = True, auth_cookie, auth_cookie
        return True
    return False

if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Metler Playoff Pool")
        with st.form("login"):
            st.markdown("### Welcome! Who are you?")
            selected_gm = st.selectbox("Select your GM Profile", sorted(GM_ROSTER))
            if st.form_submit_button("Enter Pool"):
                cookie_manager.set('user_identity_cookie', selected_gm, expires_at=datetime.datetime.now()+datetime.timedelta(days=3650), key="k2")
                st.session_state.authenticated, st.session_state.gm_name, st.session_state.display_name = True, selected_gm, selected_gm
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
    
    st.markdown("""
        <div class='table-header'>
            <div class='l-rank'>Rank</div>
            <div class='l-name header-left'>Name</div>
            <div class='l-gp hide-mobile'>GP</div>
            <div class='l-pts'>Points</div>
            <div class='l-g hide-mobile'>G</div>
            <div class='l-a hide-mobile'>A</div>
            <div class='l-yest'>Pts Yest</div>
            <div class='l-back hide-mobile'>Pts Back</div>
            <div class='l-rem hide-mobile'>Remaining</div>
        </div>
    """, unsafe_allow_html=True)
    
    html_rows = []
    for _, r in lb.iterrows():
        gm_link = f"?nav=team&gm={urllib.parse.quote(r['GM'])}"
        row_html = f"""
        <div class='table-row'>
            <div class='l-rank'><b>{r['Rank']}</b></div>
            <div class='l-name cell-left'><a href='{gm_link}' target='_self' class='player-link' style='font-weight:600;'>{r['GM']}</a></div>
            <div class='l-gp hide-mobile'>{r['GP']}</div>
            <div class='l-pts'><b>{int(r['Pts'])}</b></div>
            <div class='l-g hide-mobile'>{r['G']}</div>
            <div class='l-a hide-mobile'>{r['A']}</div>
            <div class='l-yest'>{int(r['Pts_Yest'])}</div>
            <div class='l-back hide-mobile'>{r['Back']}</div>
            <div class='l-rem hide-mobile'>{int(r['Rem'])}</div>
        </div>
        """
        html_rows.append(row_html)
    st.markdown("".join(html_rows), unsafe_allow_html=True)

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
        my_df['GP'] = my_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('gp', 0)).fillna(0).astype(int)

    my_df = my_df.sort_values('Pts', ascending=False)
    
    st.markdown("""
        <div class='table-header'>
            <div class='r-name header-left'>Player</div>
            <div class='r-team hide-mobile'>Team</div>
            <div class='r-pos hide-mobile'>Pos</div>
            <div class='r-gp hide-mobile'>GP</div>
            <div class='r-pts'>Points</div>
            <div class='r-yest'>Pts Yest</div>
            <div class='r-g hide-mobile'>G</div>
            <div class='r-a hide-mobile'>A</div>
            <div class='r-rnd hide-mobile'>Round Picked</div>
            <div class='r-top hide-mobile'>Top Pick/Rnd</div>
        </div>
    """, unsafe_allow_html=True)
    
    html_rows = []
    for _, r in my_df.iterrows():
        safe_team = str(r['Team']).strip() if pd.notna(r['Team']) else ""
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
            <div class='r-team hide-mobile'><a href='{t_url}' target='_blank' class='{l_cls}'>{safe_team}</a></div>
            <div class='r-pos hide-mobile {t_cls}'>{r['Pos']}</div>
            <div class='r-gp hide-mobile {t_cls}'>{r['GP']}</div>
            <div class='r-pts {t_cls}'><b>{r['Pts']}</b></div>
            <div class='r-yest {t_cls}'>{r['Pts_Yest']}</div>
            <div class='r-g hide-mobile {t_cls}'>{r['G']}</div>
            <div class='r-a hide-mobile {t_cls}'>{r['A']}</div>
            <div class='r-rnd hide-mobile {t_cls}'>{r['Round']}</div>
            <div class='r-top hide-mobile {t_cls}'>{r['Top_Pick']}</div>
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
        total_df['GP'] = total_df['Player_Id'].map(lambda x: points_data.get(x, {}).get(h_key, {}).get('gp', 0)).fillna(0).astype(int)

    gm_totals = total_df.groupby('GM')['Pts'].sum().reset_index().sort_values('Pts', ascending=False)
    sorted_gms = gm_totals['GM'].tolist()
    
    # Pure Native Streamlit Markdown (No HTML Wrapper)
    c_leg, c_jump = st.columns([2, 1.5])
    with c_leg:
        st.markdown("""
            <div style='font-size: 0.85rem; color: #888;'>
                <div>➤ 🔥 indicates playing today</div>
                <div>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</div>
                <div>➤ 🥇 🥈 🥉 indicates the 1st, 2nd, and 3rd highest scoring pick in their respective draft round</div>
            </div>
        """, unsafe_allow_html=True)
    with c_jump:
        anchor_md = " | ".join([f"[{g}](#{g.replace(' ', '-').lower()})" for g in sorted_gms])
        st.markdown(f"**Jump to:** {anchor_md}")
    
    st.divider()

    for g in sorted_gms:
        gm_pts = gm_totals.loc[gm_totals['GM'] == g, 'Pts'].iloc[0]
        
        hc1, hc2 = st.columns([8, 2])
        with hc1:
            st.subheader(f"{g} ({gm_pts} Points)", anchor=g.replace(' ', '-').lower())
        with hc2:
            # HTML Break isolated from the Markdown Link
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**[↑ Back to Top](#metler-playoff-pool)**")
            
        st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px; border-top: 2px solid #0068c9;'>", unsafe_allow_html=True)
        
        st.markdown("""
            <div class='table-header'>
                <div class='r-name header-left'>Player</div>
                <div class='r-team hide-mobile'>Team</div>
                <div class='r-pos hide-mobile'>Pos</div>
                <div class='r-gp hide-mobile'>GP</div>
                <div class='r-pts'>Points</div>
                <div class='r-yest'>Pts Yest</div>
                <div class='r-g hide-mobile'>G</div>
                <div class='r-a hide-mobile'>A</div>
                <div class='r-rnd hide-mobile'>Round Picked</div>
                <div class='r-top hide-mobile'>Top Pick/Rnd</div>
            </div>
        """, unsafe_allow_html=True)
        
        g_df = total_df[total_df['GM'] == g].sort_values('Pts', ascending=False)
        
        html_rows = []
        for _, r in g_df.iterrows():
            safe_team = str(r['Team']).strip() if pd.notna(r['Team']) else ""
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
                <div class='r-team hide-mobile'><a href='{t_url}' target='_blank' class='{l_cls}'>{safe_team}</a></div>
                <div class='r-pos hide-mobile {t_cls}'>{r['Pos']}</div>
                <div class='r-gp hide-mobile {t_cls}'>{r['GP']}</div>
                <div class='r-pts {t_cls}'><b>{r['Pts']}</b></div>
                <div class='r-yest {t_cls}'>{r['Pts_Yest']}</div>
                <div class='r-g hide-mobile {t_cls}'>{r['G']}</div>
                <div class='r-a hide-mobile {t_cls}'>{r['A']}</div>
                <div class='r-rnd hide-mobile {t_cls}'>{r['Round']}</div>
                <div class='r-top hide-mobile {t_cls}'>{r['Top_Pick']}</div>
            </div>
            """
            html_rows.append(row_html)
        st.markdown("".join(html_rows), unsafe_allow_html=True)
