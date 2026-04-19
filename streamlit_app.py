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
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# --- 1. SESSION & ROUTING INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'sel_gm_val' not in st.session_state: st.session_state.sel_gm_val = None
if 'nav_state' not in st.session_state: st.session_state.nav_state = 'League'

# Handle URL Navigation (Clicking a GM name in the League Table)
if "nav" in st.query_params:
    if st.query_params["nav"] == "team":
        st.session_state.nav_state = "My Team"
        st.session_state.sel_gm_val = urllib.parse.unquote(st.query_params.get("gm", ""))
    st.query_params.clear()

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
        /* Metric Centering */
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
        
        /* THE ULTIMATE TABLE STYLING - This guarantees perfect alignment */
        .pool-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem; }
        .pool-table th { border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 12px 8px; font-weight: bold; }
        .pool-table td { border-bottom: 1px solid #eee; padding: 10px 8px; text-align: center; vertical-align: middle; }
        .pool-table td.text-left, .pool-table th.text-left { text-align: left; }
        
        /* Clean Links */
        .player-link, .gm-link { color: #0068c9; text-decoration: none; font-weight: 600; }
        .player-link:hover, .gm-link:hover { text-decoration: underline; color: #004c99; }
        .eliminated { text-decoration: line-through; color: #aaa; }
        .news-link { text-decoration: none; font-size: 12px; margin-left: 5px; }
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
        st.title("🏒 Playoff Pool Login")
        with st.form("login"):
            saved = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved).lower().strip()
            pwd = st.text_input("Password", type="password")
            rem = st.checkbox("Remember my email", value=bool(saved))
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    if rem: cookie_manager.set('saved_email_input', email, expires_at=datetime.datetime.now()+datetime.timedelta(days=365), key="k1")
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now()+datetime.timedelta(days=30), key="k2")
                    st.session_state.authenticated, st.session_state.gm_name, st.session_state.display_name = True, USER_DB[email], USER_DB[email]
                    st.rerun()
                else: st.error("Invalid credentials.")
    st.stop()

# --- 4. DATA FETCHING (Optimized) ---
def fetch_single_roster(team):
    try:
        res = requests.get(f"https://api-web.nhle.com/v1/roster/{team}/current", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            players = []
            for group in ['forwards', 'defensemen']:
                for p in data.get(group, []):
                    name = f"{p['firstName']['default']} {p['lastName']['default']}"
                    players.append({'playerId': p.get('id'), 'playerName': name, 'playerName_clean': name.lower().replace('.', '').strip(), 'teamAbbrev': team, 'positionCode': p.get('positionCode', '---')})
            return players
    except: return []
    return []

@st.cache_data(ttl=3600*12)
def get_all_rosters_parallel():
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_single_roster, TEAM_URLS.keys()))
    return pd.DataFrame([p for sublist in results for p in sublist])

def fetch_player_logs(pid):
    try:
        res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/now", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            return {'pid': pid, 'logs': [g for g in res.json().get('gameLog', []) if g.get('gameTypeId') == 3]}
    except: return {'pid': pid, 'logs': []}
    return {'pid': pid, 'logs': []}

@st.cache_data(ttl=1800)
def get_all_historical_points(pids):
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_player_logs, pids))
    
    today_str = datetime.datetime.now(PT_ZONE).strftime("%Y-%m-%d")
    yesterday_str = (datetime.datetime.now(PT_ZONE) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    data = {}
    for r in results:
        pid = r['pid']
        logs = r['logs']
        data[pid] = {
            'today': sum(g.get('goals', 0) + g.get('assists', 0) for g in logs if g['gameDate'] == today_str),
            'yesterday': sum(g.get('goals', 0) + g.get('assists', 0) for g in logs if g['gameDate'] == yesterday_str),
            'last7': sum(g.get('goals', 0) + g.get('assists', 0) for g in logs if g['gameDate'] >= (datetime.datetime.now(PT_ZONE) - datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
        }
    return data

@st.cache_data(ttl=3600)
def get_playoff_status():
    elim, today = set(), []
    try:
        res1 = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026", headers=HEADERS, timeout=5)
        if res1.status_code == 200:
            series = res1.json().get('series', []) or [s for r in res1.json().get('rounds', []) for s in r.get('series', [])]
            for s in series:
                m = s.get('matchupTeams', [])
                if len(m) == 2:
                    if m[0].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[1].get('teamAbbrev'))
                    if m[1].get('seriesRecord', {}).get('wins', 0) == 4: elim.add(m[0].get('teamAbbrev'))
        res2 = requests.get("https://api-web.nhle.com/v1/schedule/now", headers=HEADERS, timeout=5)
        if res2.status_code == 200:
            today_str = datetime.datetime.now(PT_ZONE).strftime("%Y-%m-%d")
            today = [t['abbrev'] for d in res2.json().get('gameWeek', []) if d['date'] == today_str for g in d.get('games', []) for t in [g['awayTeam'], g['homeTeam']]]
    except: pass
    return elim, today

# --- 5. CORE LOGIC ---
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
    
    res_stats = requests.get("https://api.nhle.com/stats/rest/en/skater/summary", params={"cayenneExp": "gameTypeId=3 and seasonId=20252026"}, headers=HEADERS).json()
    stat_df = pd.DataFrame(res_stats.get('data', []))
    if not stat_df.empty:
        stat_df = stat_df[['playerId', 'points', 'goals', 'assists', 'gamesPlayed']].rename(columns={'points':'Pts','goals':'G','assists':'A','gamesPlayed':'GP'})
        master_df = pd.merge(master_df, stat_df, left_on='Player_Id', right_on='playerId', how='left').fillna(0)
    else:
        for c in ['Pts','G','A','GP']: master_df[c] = 0
        
    master_df['Pts_Today'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('today', 0))
    master_df['Pts_Yest'] = master_df['Player_Id'].map(lambda x: points_data.get(x, {}).get('yesterday', 0))
    master_df['Rank_Rnd'] = master_df.groupby('Round')['Pts'].rank(method='min', ascending=False).astype(int)
    master_df['Top_Pick'] = master_df['Rank_Rnd'].apply(lambda x: "🥇 1" if x==1 else "🥈 2" if x==2 else "🥉 3" if x==3 else "-")
    
    if st.session_state.display_name:
        master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    gms = sorted(master_df['GM'].unique().tolist())

except Exception as e:
    st.error(f"Critical Data Error: {e}")
    st.stop()

# --- 6. UI ---
t_logo, t_title, t_text, t_menu = st.columns([0.6, 4.9, 3.5, 1.0])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️ Settings"):
        new = st.text_input("Change Display Name", value=st.session_state.display_name)
        if st.button("Update"): st.session_state.display_name = new; st.rerun()
        if st.button("Log Out"): cookie_manager.delete('user_email_cookie'); st.session_state.authenticated = False; st.rerun()

st.divider()

# Navigation Control (using key ensures no double clicks)
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default=st.session_state.nav_state, key="nav_state", label_visibility="collapsed")

if nav == "League":
    lb = master_df.groupby('GM').agg({'GP':'sum','Pts':'sum','G':'sum','A':'sum','Pts_Yest':'sum'}).reset_index().sort_values(['Pts','G'], ascending=False)
    counts = master_df[~master_df['Team'].isin(ELIMINATED)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'], lb['Back'] = range(1, len(lb)+1), lb['Pts'].max() - lb['Pts']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> leads by {int(lb.iloc[0]['Pts'] - lb.iloc[1]['Pts'])} points.</div>", unsafe_allow_html=True)
    
    # THE UNIFIED LEAGUE HTML TABLE
    h_html = "<table class='pool-table'><thead><tr><th>Rank</th><th class='text-left'>Name</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Pts Yesterday</th><th>Pts Back</th><th>Remaining Players</th></tr></thead><tbody>"
    for _, r in lb.iterrows():
        gm_url = f"?nav=team&gm={urllib.parse.quote(r['GM'])}"
        gm_link = f"<a href='{gm_url}' target='_self' class='gm-link'>{r['GM']}</a>"
        
        # NOTE: Using <b> instead of ** to fix the markdown parsing bug in HTML
        h_html += f"<tr><td><b>{r['Rank']}</b></td><td class='text-left'>{gm_link}</td><td>{r['GP']}</td><td><b>{int(r['Pts'])}</b></td><td>{r['G']}</td><td>{r['A']}</td><td>{int(r['Pts_Yest'])}</td><td>{r['Back']}</td><td>{int(r['Rem'])}</td></tr>"
    h_html += "</tbody></table>"
    st.markdown(h_html, unsafe_allow_html=True)

elif nav == "My Team":
    # 1. Set default team to logged in user if empty
    if not st.session_state.sel_gm_val or st.session_state.sel_gm_val not in gms:
        st.session_state.sel_gm_val = st.session_state.display_name if st.session_state.display_name in gms else gms[0]
    
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{st.session_state.sel_gm_val}</b>'s roster.</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1, 1, 1])
    
    with c1: 
        curr = st.selectbox("View another team", gms, index=gms.index(st.session_state.sel_gm_val), key="team_dropdown")
        # Trigger page refresh only if dropdown changes
        if curr != st.session_state.sel_gm_val:
            st.session_state.sel_gm_val = curr
            st.rerun()

    with c2: horizon = st.selectbox("Stats", ['All Time', 'Yesterday', 'Last 7 Days'])
    
    my_df = master_df[master_df['GM'] == st.session_state.sel_gm_val].copy()
    with c3: st.metric("Points Today", int(my_df['Pts_Today'].sum()))
    with c4: st.metric("Active Today", len(my_df[my_df['Team'].isin(PLAYING_TODAY) & ~my_df['Team'].isin(ELIMINATED)]))
    with c5: st.metric("Remaining", len(my_df[~my_df['Team'].isin(ELIMINATED)]))

    if horizon != 'All Time':
        days = 1 if horizon == 'Yesterday' else 7
        h_pts = get_all_historical_points(my_df['Player_Id'].dropna().unique())
        my_df['Pts'] = my_df['Player_Id'].map(lambda x: h_pts.get(x, {}).get('yesterday' if days==1 else 'last7', 0)).fillna(0).astype(int)
        for c in ['G','A','GP','Top_Pick']: my_df[c] = "-"

    # SORT BY TOTAL POINTS DESC
    my_df = my_df.sort_values('Pts', ascending=False)
    
    # THE UNIFIED MY TEAM HTML TABLE
    t_html = "<table class='pool-table'><thead><tr><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th class='text-left'>Round Picked</th><th>Top Pick/Rnd</th></tr></thead><tbody>"
    
    for _, r in my_df.iterrows():
        is_elim = r['Team'] in ELIMINATED
        cls = "eliminated" if is_elim else "player-link"
        fire = " 🔥" if r['Team'] in PLAYING_TODAY and not is_elim else ""
        p_url = f"https://www.nhl.com/player/{int(r['Player_Id'])}" if r['Player_Id'] else "#"
        n_url = f"https://news.google.com/search?q={str(r['Player_Name']).replace(' ','+')}+NHL"
        
        player_cell = f"<a href='{p_url}' target='_blank' class='{cls}'>{r['Player_Name']}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{fire}"
        # NOTE: Using <b> for points
        t_html += f"<tr><td class='text-left'>{player_cell}</td><td class='{cls}'>{r['Team']}</td><td class='{cls}'>{r['Pos']}</td><td class='{cls}'>{r['GP']}</td><td class='{cls}'><b>{r['Pts']}</b></td><td class='{cls}'>{r['G']}</td><td class='{cls}'>{r['A']}</td><td class='text-left {cls}'>{r['Round']}</td><td class='{cls}'>{r['Top_Pick']}</td></tr>"
        
    t_html += "</tbody></table>"
    st.markdown(t_html, unsafe_allow_html=True)

elif nav == "All Rosters":
    st.markdown("<p style='color: #888;'>➤ 🔥 indicates playing today<br>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</p>", unsafe_allow_html=True)
    
    for g in gms:
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        g_df = master_df[master_df['GM'] == g].sort_values('Pts', ascending=False)
        
        r_html = "<table class='pool-table'><thead><tr><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th class='text-left'>Round Picked</th></tr></thead><tbody>"
        for _, r in g_df.iterrows():
            is_elim = r['Team'] in ELIMINATED
            cls = "eliminated" if is_elim else ""
            r_html += f"<tr><td class='text-left {cls}'>{r['Player_Name']}</td><td class='{cls}'>{r['Team']}</td><td class='{cls}'>{r['Pos']}</td><td class='{cls}'>{r['GP']}</td><td class='{cls}'><b>{r['Pts']}</b></td><td class='{cls}'>{r['G']}</td><td class='{cls}'>{r['A']}</td><td class='text-left {cls}'>{r['Round']}</td></tr>"
        r_html += "</tbody></table>"
        st.markdown(r_html, unsafe_allow_html=True)
