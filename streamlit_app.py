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
from concurrent.futures import ThreadPoolExecutor

# --- 1. SESSION INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'sel_gm_val' not in st.session_state: st.session_state.sel_gm_val = None
if 'nav_state' not in st.session_state: st.session_state.nav_state = 'League'

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
        
        /* Consistent Header Styling */
        .header-text { color: #888; font-weight: bold; font-size: 13px; text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
        .header-left { text-align: left; }
        
        /* Link styling */
        .player-link { color: #333; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #0068c9; }
        .eliminated { text-decoration: line-through; color: #aaa; }
        
        /* Clean Link-Buttons for GMs */
        div.stButton > button {
            border: none !important; background: none !important; padding: 0 !important; color: #0068c9 !important;
            text-decoration: none !important; font-size: 14px !important; font-weight: 600 !important;
        }
        div.stButton > button:hover { text-decoration: underline !important; color: #004c99 !important; }
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

# --- 4. OPTIMIZED DATA FETCHING (Parallel) ---
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
    # Live stats merge
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
    
    # Points Injection
    pids = master_df['Player_Id'].dropna().unique()
    points_data = get_all_historical_points(pids)
    
    # Static data for points (API stats)
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
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default=st.session_state.nav_state, label_visibility="collapsed")
st.session_state.nav_state = nav

if nav == "League":
    lb = master_df.groupby('GM').agg({'GP':'sum','Pts':'sum','G':'sum','A':'sum','Pts_Yest':'sum'}).reset_index().sort_values(['Pts','G'], ascending=False)
    counts = master_df[~master_df['Team'].isin(ELIMINATED)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'], lb['Back'] = range(1, len(lb)+1), lb['Pts'].max() - lb['Pts']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> leads by {int(lb.iloc[0]['Pts'] - lb.iloc[1]['Pts'])} points.</div>", unsafe_allow_html=True)
    
    # SUSTAINABLE TABLE SYSTEM
    h_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
    h_labels = ["Rank", "Name", "GP", "Points", "G", "A", "Pts Yesterday", "Pts Back", "Remaining Players"]
    for i, l in enumerate(h_labels): h_cols[i].markdown(f"<div class='header-text {'header-left' if i==1 else ''}'>{l}</div>", unsafe_allow_html=True)
    
    for _, r in lb.iterrows():
        b_cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
        b_cols[0].write(f"**{r['Rank']}**")
        with b_cols[1]:
            if st.button(r['GM'], key=f"l_{r['GM']}"):
                st.session_state.sel_gm_val, st.session_state.nav_state = r['GM'], "My Team"
                st.rerun()
        for i, val in enumerate([r['GP'], f"**{int(r['Pts'])}**", r['G'], r['A'], int(r['Pts_Yest']), r['Back'], int(r['Rem'])]):
            b_cols[i+2].markdown(f"<div style='text-align:center;'>{val}</div>", unsafe_allow_html=True)

elif nav == "My Team":
    curr = st.session_state.sel_gm_val or (st.session_state.display_name if st.session_state.display_name in gms else gms[0])
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{curr}</b>'s roster.</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1, 1, 1])
    with c1: curr = st.selectbox("View another team", gms, index=gms.index(curr), key="sel_gm_val")
    with c2: horizon = st.selectbox("Stats", ['All Time', 'Yesterday', 'Last 7 Days'])
    
    my_df = master_df[master_df['GM'] == curr].copy()
    with c3: st.metric("Points Today", int(my_df['Pts_Today'].sum()))
    with c4: st.metric("Active Today", len(my_df[my_df['Team'].isin(PLAYING_TODAY) & ~my_df['Team'].isin(ELIMINATED)]))
    with c5: st.metric("Remaining", len(my_df[~my_df['Team'].isin(ELIMINATED)]))

    if horizon != 'All Time':
        days = 1 if horizon == 'Yesterday' else 7
        h_pts = get_all_historical_points(my_df['Player_Id'].dropna().unique())
        my_df['Pts'] = my_df['Player_Id'].map(lambda x: h_pts.get(x, {}).get('yesterday' if days==1 else 'last7', 0))
        for c in ['G','A','GP','Top_Pick']: my_df[c] = "-"

    my_df = my_df.sort_values('Pts', ascending=False)
    
    t_cols = st.columns([2.0, 0.6, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
    t_labels = ["Player", "Team", "Pos", "GP", "Points", "G", "A", "Round Picked", "Top Pick/Rnd"]
    for i, l in enumerate(t_labels): t_cols[i].markdown(f"<div class='header-text {'header-left' if i==0 else ''}'>{l}</div>", unsafe_allow_html=True)
    
    for _, r in my_df.iterrows():
        r_cols = st.columns([2.0, 0.6, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
        is_elim = r['Team'] in ELIMINATED
        cls = "eliminated" if is_elim else "player-link"
        fire = " 🔥" if r['Team'] in PLAYING_TODAY and not is_elim else ""
        p_url = f"https://www.nhl.com/player/{int(r['Player_Id'])}" if r['Player_Id'] else "#"
        n_url = f"https://news.google.com/search?q={r['Player_Name'].replace(' ','+')}+NHL"
        
        r_cols[0].markdown(f"<a href='{p_url}' target='_blank' class='{cls}'>{r['Player_Name']}</a><a href='{n_url}' target='_blank' style='text-decoration:none;margin-left:5px;'>📄</a>{fire}", unsafe_allow_html=True)
        for i, val in enumerate([r['Team'], r['Pos'], r['GP'], f"**{r['Pts']}**", r['G'], r['A'], r['Round'], r['Top_Pick']]):
            r_cols[i+1].markdown(f"<div class='{cls}' style='text-align:center;'>{val}</div>", unsafe_allow_html=True)

elif nav == "All Rosters":
    for g in gms:
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        st.dataframe(master_df[master_df['GM'] == g].sort_values('Pts', ascending=False)[['Player_Name', 'Team', 'Pos', 'Pts', 'GP', 'Round']], use_container_width=True, hide_index=True)
