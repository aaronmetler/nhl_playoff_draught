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
import time

# --- 1. SESSION INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None
if 'sel_gm_val' not in st.session_state: st.session_state.sel_gm_val = None
if 'nav_state' not in st.session_state: st.session_state.nav_state = 'League'

# --- 2. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        hr { margin-top: 0.5em; margin-bottom: 0.5em; }
        
        /* Roast Container */
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.8rem 1.2rem; 
            margin-bottom: 1rem;
            font-size: 1rem;
        }

        /* Metric Centering */
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
        
        /* Table Header Styling (Streamlit Columns Emulation) */
        .header-row {
            border-bottom: 2px solid #ddd;
            color: #888;
            font-weight: bold;
            font-size: 13px;
            padding-bottom: 8px;
            margin-bottom: 8px;
            text-align: center;
        }
        
        /* GM Link Button Styling - Essential for sustainability */
        div.stButton > button {
            border: none !important;
            background: none !important;
            padding: 0 !important;
            color: #0068c9 !important;
            text-decoration: none !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            height: auto !important;
            line-height: inherit !important;
            min-height: 0px !important;
        }
        div.stButton > button:hover {
            text-decoration: underline !important;
            color: #004c99 !important;
        }

        /* Player links */
        .player-link { color: #333; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #0068c9; }
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
TEAM_URLS = {'ANA': 'ducks', 'BOS': 'bruins', 'BUF': 'sabres', 'CGY': 'flames', 'CAR': 'hurricanes', 'CHI': 'blackhawks', 'COL': 'avalanche', 'CBJ': 'bluejackets', 'DAL': 'stars', 'DET': 'redwings', 'EDM': 'oilers', 'FLA': 'panthers', 'LAK': 'kings', 'MIN': 'wild', 'MTL': 'canadiens', 'NSH': 'predators', 'NJD': 'devils', 'NYI': 'islanders', 'NYR': 'rangers', 'OTT': 'senators', 'PHI': 'flyers', 'PIT': 'penguins', 'SJS': 'sharks', 'SEA': 'kraken', 'STL': 'blues', 'TBL': 'lightning', 'TOR': 'mapleleafs', 'UTA': 'utah', 'VAN': 'canucks', 'VGK': 'goldenknights', 'WSH': 'capitals', 'WPG': 'jets'}

def is_authenticated():
    if st.session_state.authenticated: return True
    auth_cookie = cookie_manager.get('user_email_cookie')
    if auth_cookie and auth_cookie in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[auth_cookie]
        if not st.session_state.display_name: st.session_state.display_name = USER_DB[auth_cookie]
        return True
    return False

if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            saved_email = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved_email).lower().strip()
            pwd = st.text_input("Password", type="password")
            rem = st.checkbox("Remember my email", value=bool(saved_email))
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    if rem: cookie_manager.set('saved_email_input', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=365), key="s1")
                    else: cookie_manager.delete('saved_email_input', key="d1")
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30), key="s2")
                    st.session_state.authenticated = True
                    st.session_state.gm_name = USER_DB[email]
                    st.session_state.display_name = USER_DB[email]
                    st.rerun()
                else: st.error("Invalid credentials.")
    st.stop()

# --- 4. DATA FETCHING ---
@st.cache_data(ttl=3600*24)
def get_all_rosters():
    all_players = []
    for team in TEAM_URLS.keys():
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/roster/{team}/current", headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for group in ['forwards', 'defensemen']:
                    for p in data.get(group, []):
                        fn = p['firstName']['default']
                        ln = p['lastName']['default']
                        all_players.append({'playerId': p.get('id'), 'playerName': f"{fn} {ln}", 'playerName_clean': f"{fn} {ln}".lower().replace('.', '').strip(), 'teamAbbrev': team, 'positionCode': p.get('positionCode', '---')})
        except: pass
    return pd.DataFrame(all_players)

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
                for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                return df
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_historical_points(pids, days):
    today = datetime.datetime.now(PT_ZONE)
    cutoff_date = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    pts_dict = {}
    for pid in pids:
        if not pid: continue
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/now", headers=HEADERS, timeout=5)
            pts = 0
            if res.status_code == 200:
                logs = res.json().get('gameLog', [])
                for g in logs:
                    # Check for Playoff Game Type (3)
                    if g.get('gameTypeId') == 3:
                        if days == 0: # Logic for "Points Today"
                            if g['gameDate'] == today_str:
                                pts += g.get('goals', 0) + g.get('assists', 0)
                        else: # Logic for range
                            if g['gameDate'] >= cutoff_date:
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

# --- 5. DATA PREPARATION ---
stats = fetch_live_playoff_data()
rosters = get_all_rosters()
ELIMINATED_TEAMS = get_eliminated_teams()
TEAMS_PLAYING_TODAY = get_teams_playing_today()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    df_raw.columns = df_raw.columns.str.strip()
    gms_list = sorted(df_raw['GM Owner'].unique().tolist())
except: st.stop()

def clean_and_match(row_data, stats_df, roster_df):
    p_name, t_part = str(row_data['Player']).strip(), str(row_data['Acronym']).strip().upper()
    t_part = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH', 'LA': 'LAK', 'NJ': 'NJD', 'SJ': 'SJS'}.get(t_part, t_part)
    name_clean = p_name.lower().replace('.', '').strip()
    lookup_df = roster_df[roster_df['teamAbbrev'] == t_part] if not roster_df.empty and t_part else roster_df
    matches = difflib.get_close_matches(name_clean, lookup_df['playerName_clean'].tolist(), n=1, cutoff=0.4)
    if matches:
        base = lookup_df[lookup_df['playerName_clean'] == matches[0]].iloc[0].to_dict()
        if not stats_df.empty:
            scored = stats_df[stats_df['playerId'] == base['playerId']]
            if not scored.empty: base.update(scored.iloc[0].to_dict())
        return base
    return {'playerName': p_name.title(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '---', 'playerId': None}

master_list = []
for _, row in df_raw.iterrows():
    p = clean_and_match(row, stats, rosters)
    master_list.append({'GM': str(row['GM Owner']).strip(), 'Player_Id': p.get('playerId'), 'Player_Name': p.get('playerName'), 'Team_Raw': p.get('teamAbbrev'), 'Position': p.get('positionCode'), 'Points': p.get('totalPoints', 0), 'G': p.get('goals', 0), 'A': p.get('assists', 0), 'GP': p.get('gamesPlayed', 0), 'Round': str(row['Round'])})

master_df = pd.DataFrame(master_list)
master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).fillna(0).astype(int)
master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(lambda x: "🥇 1" if x == 1 else "🥈 2" if x == 2 else "🥉 3" if x == 3 else "-")

if st.session_state.display_name:
    master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    gms_list = sorted(master_df['GM'].unique().tolist())

# --- 6. HEADER ---
t_logo, t_title, t_text, t_menu = st.columns([0.6, 4.9, 3.5, 1.0])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️ Settings"):
        new_disp = st.text_input("Change Display Name", value=st.session_state.display_name)
        if st.button("Update"): st.session_state.display_name = new_disp; st.rerun()
        if st.button("Log Out"): cookie_manager.delete('user_email_cookie'); st.session_state.authenticated = False; st.rerun()

st.divider()
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default=st.session_state.nav_state, label_visibility="collapsed", key="main_nav")
st.session_state.nav_state = nav

# --- 7. VIEWS ---
if nav == "League":
    lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index().sort_values(['Points', 'G'], ascending=False)
    
    # Points Yesterday
    y_pts_map = get_historical_points(master_df['Player_Id'].dropna().unique(), 1)
    master_df['Pts_Yest'] = master_df['Player_Id'].map(y_pts_map).fillna(0)
    lb = pd.merge(lb, master_df.groupby('GM')['Pts_Yest'].sum().reset_index(), on='GM')
    
    # Remaining Players
    rem_counts = master_df[~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, rem_counts, on='GM', how='left').fillna(0)
    lb['Rank'] = range(1, len(lb)+1)
    lb['Pts Back'] = lb['Points'].max() - lb['Points']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> is holding the lead.</div>", unsafe_allow_html=True)

    # UNIFIED LEAGUE TABLE (Perfect Alignment)
    cols = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
    fields = ["Rank", "Name", "GP", "Points", "G", "A", "Points Yesterday", "Pts Back", "Remaining Players"]
    for i, f in enumerate(fields): cols[i].markdown(f"<div class='header-row'>{f}</div>", unsafe_allow_html=True)

    for _, r in lb.iterrows():
        row = st.columns([0.5, 2.0, 0.6, 0.8, 0.6, 0.6, 1.2, 0.8, 1.4])
        row[0].write(f"**{r['Rank']}**")
        with row[1]:
            if st.button(r['GM'], key=f"lk_{r['GM']}"):
                st.session_state.sel_gm_val = r['GM']
                st.session_state.nav_state = "My Team"
                st.rerun()
        row[2].write(r['GP'])
        row[3].write(f"**{r['Points']}**")
        row[4].write(r['G'])
        row[5].write(r['A'])
        row[6].write(int(r['Pts_Yest']))
        row[7].write(r['Pts Back'])
        row[8].write(int(r['Rem']))

elif nav == "My Team":
    current_gm = st.session_state.get('sel_gm_val') or (st.session_state.display_name if st.session_state.display_name in gms_list else gms_list[0])
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{current_gm}</b>'s roster.</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1, 1, 1])
    with c1: current_gm = st.selectbox("View another team", gms_list, index=gms_list.index(current_gm), key="sel_gm_val")
    with c2: horizon = st.selectbox("Stats", ['All Time', 'Yesterday', 'Last 48 Hours', 'Last 7 Days'])
    
    my_df = master_df[master_df['GM'] == current_gm].copy()
    
    # Points Today logic
    pids = my_df['Player_Id'].dropna().unique()
    t_pts_map = get_historical_points(pids, 0)
    p_today = sum(t_pts_map.values())
    
    with c3: st.metric("Points Today", p_today)
    with c4: st.metric("Active Today", len(my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY) & ~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))
    with c5: st.metric("Remaining", len(my_df[~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))

    if horizon != 'All Time':
        days = {'Yesterday': 1, 'Last 48 Hours': 2, 'Last 7 Days': 7}[horizon]
        h_map = get_historical_points(pids, days)
        my_df['Points'] = my_df['Player_Id'].map(h_map).fillna(0).astype(int)
        for c in ['G','A','GP','Top Pick/Rnd']: my_df[c] = "-"

    my_df = my_df.sort_values(by='Points', ascending=False)

    # UNIFIED TEAM TABLE
    t_cols = st.columns([2.0, 0.6, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
    t_fields = ["Player", "Team", "Pos", "GP", "Points", "G", "A", "Round Picked", "Top Pick/Rnd"]
    for i, f in enumerate(t_fields): t_cols[i].markdown(f"<div class='header-row'>{f}</div>", unsafe_allow_html=True)

    for _, r in my_df.iterrows():
        row = st.columns([2.0, 0.6, 0.6, 0.6, 0.8, 0.6, 0.6, 1.0, 1.0])
        is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
        active = " 🔥" if r['Team_Raw'] in TEAMS_PLAYING_TODAY and not is_elim else ""
        p_cls = "eliminated" if is_elim else "player-link"
        p_url = f"https://www.nhl.com/player/{r['Player_Id']}" if r['Player_Id'] else "#"
        n_url = f"https://news.google.com/search?q={str(r['Player_Name']).replace(' ', '+')}+NHL+when:2d"
        
        row[0].markdown(f"<a href='{p_url}' target='_blank' class='{p_cls}'>{r['Player_Name']}</a><a href='{n_url}' target='_blank' class='news-link'>📄</a>{active}", unsafe_allow_html=True)
        row[1].markdown(f"<span class='{p_cls}'>{r['Team_Raw']}</span>", unsafe_allow_html=True)
        row[2].markdown(f"<span class='{p_cls}'>{r['Position']}</span>", unsafe_allow_html=True)
        row[3].markdown(f"<span class='{p_cls}'>{r['GP']}</span>", unsafe_allow_html=True)
        row[4].markdown(f"<span class='{p_cls}'><b>{r['Points']}</b></span>", unsafe_allow_html=True)
        row[5].markdown(f"<span class='{p_cls}'>{r['G']}</span>", unsafe_allow_html=True)
        row[6].markdown(f"<span class='{p_cls}'>{r['A']}</span>", unsafe_allow_html=True)
        row[7].markdown(f"<span class='{p_cls}'>{r['Round']}</span>", unsafe_allow_html=True)
        row[8].markdown(f"<span class='{p_cls}'>{r['Top Pick/Rnd']}</span>", unsafe_allow_html=True)

elif nav == "All Rosters":
    st.markdown("<p style='color: #888;'>➤ 🔥 indicates playing today</p>", unsafe_allow_html=True)
    for g in gms_list:
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        g_df = master_df[master_df['GM'] == g].sort_values(by='Points', ascending=False)
        # Simplified list view for All Rosters
        st.dataframe(g_df[['Player_Name', 'Team_Raw', 'Position', 'Points', 'G', 'A', 'Round']], use_container_width=True, hide_index=True)
