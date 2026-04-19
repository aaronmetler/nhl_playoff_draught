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
        
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        [data-testid="stMetricLabel"] { display: flex; justify-content: center; width: 100%; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; width: 100%; }
        
        .gm-label { color: #0068c9; font-weight: 600; }
        .news-link { text-decoration: none; font-size: 12px; margin-left: 5px; }
        .player-link { color: inherit; text-decoration: none; font-weight: 500; }
        .player-link:hover { text-decoration: underline; color: #0068c9; }
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

def is_authenticated():
    if st.session_state.authenticated: return True
    auth_cookie = cookie_manager.get('user_email_cookie')
    if auth_cookie and auth_cookie in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[auth_cookie]
        if not st.session_state.display_name:
            st.session_state.display_name = USER_DB[auth_cookie]
        return True
    return False

if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            saved_email_val = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved_email_val).lower().strip()
            pwd = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember my email", value=bool(saved_email_val))
            
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    if remember_me:
                        cookie_manager.set('saved_email_input', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=365), key="set_rem")
                    else:
                        cookie_manager.delete('saved_email_input', key="del_rem")
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30), key="set_auth")
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
                        full_name = f"{p['firstName']['default']} {p['lastName']['default']}"
                        all_players.append({
                            'playerId': p.get('id'),
                            'playerName': full_name,
                            'playerName_clean': full_name.lower().replace('.', '').strip(),
                            'teamAbbrev': team,
                            'positionCode': p.get('positionCode', '---')
                        })
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
    cutoff = (datetime.datetime.now(PT_ZONE) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    pts_dict = {}
    for pid in pids:
        if not pid: continue
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

# --- 5. UI HELPERS ---
def generate_team_table_html(df, eliminated_teams, playing_today):
    # Round column moved to 2nd last position
    h = "<table class='pool-table'><thead><tr><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th class='text-left'>Round</th><th>Top Pick/Rnd</th></tr></thead><tbody>"
    for _, r in df.iterrows():
        is_elim = r['Team_Raw'] in eliminated_teams
        is_playing = r['Team_Raw'] in playing_today and not is_elim
        decor = "line-through" if is_elim else "none"
        active = " 🔥" if is_playing else ""
        
        # NHL Player Profile Link
        player_url = f"https://www.nhl.com/player/{r['Player_Id']}" if r['Player_Id'] else "#"
        p_link = f"<a href='{player_url}' target='_blank' class='player-link'>{r['Player_Name']}</a>"
        
        # News Link
        news_url = f"https://news.google.com/search?q={str(r['Player_Name']).replace(' ', '+')}+NHL+when:2d"
        news_link = f"<a href='{news_url}' target='_blank' class='news-link' title='Player News'>📄</a>"
        
        h += f"<tr style='text-decoration: {decor};'><td class='text-left'>{p_link}{news_link}{active}</td><td>{r['Team_Raw']}</td><td>{r['Position']}</td><td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td><td class='text-left'>{r['Round']}</td><td>{r['Top Pick/Rnd']}</td></tr>"
    return h + "</tbody></table>"

# --- 6. MAIN HEADER ---
t_logo, t_title, t_text, t_menu = st.columns([0.6, 4.9, 3.5, 1.0])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️ Settings"):
        new_disp = st.text_input("Change Display Name", value=st.session_state.display_name)
        if st.button("Update"): st.session_state.display_name = new_disp; st.rerun()
        if st.button("Log Out"): 
            cookie_manager.delete('user_email_cookie')
            st.session_state.authenticated = False
            st.rerun()

st.divider()
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default="League", label_visibility="collapsed")

# --- 7. DATA PROCESSING ---
stats = fetch_live_playoff_data()
rosters = get_all_rosters()
ELIMINATED_TEAMS = get_eliminated_teams()
TEAMS_PLAYING_TODAY = get_teams_playing_today()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    df_raw.columns = df_raw.columns.str.strip()
    gms_list = sorted(df_raw['GM Owner'].unique().tolist())
except: 
    st.error("Could not read CSV file.")
    st.stop()

def clean_and_match(row_data, stats_df, roster_df):
    p_name = str(row_data['Player']).strip()
    t_part = str(row_data['Acronym']).strip().upper()
    t_part = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH', 'LA': 'LAK', 'NJ': 'NJD', 'SJ': 'SJS'}.get(t_part, t_part)
    name_clean = p_name.lower().replace('.', '').strip()
    lookup_df = roster_df[roster_df['teamAbbrev'] == t_part] if not roster_df.empty and t_part else roster_df
    matches = difflib.get_close_matches(name_clean, lookup_df['playerName_clean'].tolist(), n=1, cutoff=0.4)
    if matches:
        base_info = lookup_df[lookup_df['playerName_clean'] == matches[0]].iloc[0].to_dict()
        if not stats_df.empty:
            scored = stats_df[stats_df['playerId'] == base_info['playerId']]
            if not scored.empty: base_info.update(scored.iloc[0].to_dict())
        return base_info
    return {'playerName': p_name.title(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '---', 'playerId': None}

master_list = []
for _, row in df_raw.iterrows():
    p = clean_and_match(row, stats, rosters)
    master_list.append({
        'GM': str(row['GM Owner']).strip(), 
        'Player_Id': p.get('playerId'), 
        'Player_Name': p.get('playerName'), 
        'Team_Raw': p.get('teamAbbrev'), 
        'Position': p.get('positionCode'), 
        'Points': p.get('totalPoints', 0), 
        'G': p.get('goals', 0), 
        'A': p.get('assists', 0), 
        'GP': p.get('gamesPlayed', 0), 
        'Round': str(row['Round'])
    })

master_df = pd.DataFrame(master_list)
master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).fillna(0).astype(int)

# New Top Pick logic: Only Top 3 show medals, others show "-"
master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(
    lambda x: "🥇 1" if x == 1 else "🥈 2" if x == 2 else "🥉 3" if x == 3 else "-"
)

if st.session_state.display_name:
    master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)

# --- 8. UI VIEWS ---
if nav == "League":
    lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index().sort_values(['Points', 'G'], ascending=False)
    counts = master_df[~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'] = range(1, len(lb)+1)
    lb['Pts Back'] = lb['Points'].max() - lb['Points']
    
    st.markdown(f"<div class='roast-container'>🏆 <b>{lb.iloc[0]['GM']}</b> is holding the lead. <b>{lb.iloc[-1]['GM']}</b> is scouting for next year's draft.</div>", unsafe_allow_html=True)

    lb_html = "<table class='pool-table'><tr><th>Rank</th><th class='text-left'>Name</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Pts Back</th><th>Remaining Players</th></tr>"
    for _, r in lb.iterrows():
        lb_html += f"<tr><td>{r['Rank']}</td><td class='text-left'><span class='gm-label'>{r['GM']}</span></td><td>{r['GP']}</td><td><b>{r['Points']}</b></td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Pts Back']}</td><td>{int(r['Rem'])}</td></tr>"
    st.markdown(lb_html + "</table>", unsafe_allow_html=True)

elif nav == "My Team":
    display_gms = sorted(master_df['GM'].unique().tolist())
    current_gm = st.session_state.get('view_gm', st.session_state.display_name if st.session_state.display_name in display_gms else display_gms[0])
    
    st.markdown(f"<div class='roast-container'>🏒 Viewing <b>{current_gm}</b>'s roster.</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1, 1, 1])
    with c1:
        current_gm = st.selectbox("View another team", display_gms, index=display_gms.index(current_gm), key="view_gm")
    with c2:
        horizon = st.selectbox("Stats", ['All Time', 'Yesterday', 'Last 48 Hours', 'Last 7 Days'])
    
    my_df = master_df[master_df['GM'] == current_gm]
    p_today = sum(get_historical_points(my_df['Player_Id'].dropna(), 0).values())
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

    disp_df = disp_df.sort_values(by='Points', ascending=False)
    st.markdown(generate_team_table_html(disp_df, ELIMINATED_TEAMS, TEAMS_PLAYING_TODAY), unsafe_allow_html=True)

elif nav == "All Rosters":
    for g in sorted(master_df['GM'].unique().tolist()):
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        g_df = master_df[master_df['GM'] == g].sort_values(by='Points', ascending=False)
        st.markdown(generate_team_table_html(g_df, ELIMINATED_TEAMS, TEAMS_PLAYING_TODAY), unsafe_allow_html=True)
