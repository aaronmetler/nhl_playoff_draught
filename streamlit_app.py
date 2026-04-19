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

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# Try to import Gemini, handle gracefully if missing or secret not set
try:
    import google.generativeai as genai
    # Check if the secret exists
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        GEMINI_READY = True
    else:
        GEMINI_READY = False
        st.error("Gemini API Key missing from Streamlit Secrets.")
except Exception as e:
    GEMINI_READY = False
    st.sidebar.error(f"AI Error: {e}")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
        hr { margin-top: 0.5em; margin-bottom: 0.5em; }
        .roast-container {
            background-color: rgba(0, 104, 201, 0.08);
            border: 1px solid rgba(0, 104, 201, 0.2);
            border-radius: 0.5rem;
            padding: 0.5rem 1rem; 
            position: relative;
            min-height: 40px; 
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            margin-top: 5px;
        }
        .team-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem; }
        .team-table th { border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 8px; }
        .team-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: center; }
        .team-table td.text-left, .team-table th.text-left { text-align: left; }
        .team-table a { text-decoration: none; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None

PT_ZONE = ZoneInfo("America/Los_Angeles")

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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def is_authenticated():
    if st.session_state.authenticated: return True
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email and saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        if not st.session_state.display_name: st.session_state.display_name = USER_DB[saved_email]
        return True
    return False

if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            saved_email_input = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved_email_input).lower().strip()
            pwd = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember my email", value=bool(saved_email_input))
            if st.form_submit_button("Sign In"):
                if email in USER_DB and pwd == SHARED_PWD:
                    if remember_me: cookie_manager.set('saved_email_input', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=365), key="set_rem")
                    else: cookie_manager.delete('saved_email_input', key="del_rem")
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30), key="set_auth")
                    st.session_state.authenticated = True
                    st.session_state.gm_name = USER_DB[email]
                    st.session_state.display_name = USER_DB[email]
                    st.rerun()
                else: st.error("Invalid credentials.")
    st.stop()

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    base_url = "https://api.nhle.com/stats/rest/en/skater/summary"
    def get_data(gt):
        all_d = []; start = 0; limit = 100
        while True:
            res = requests.get(base_url, params={"isAggregate": "false", "isGame": "false", "start": start, "limit": limit, "cayenneExp": f"gameTypeId={gt} and seasonId=20252026"}, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                d = res.json().get('data', [])
                if not d: break
                all_d.extend(d)
                if len(d) < limit: break
                start += limit
            else: break
        df = pd.DataFrame(all_d)
        if not df.empty: df.rename(columns={'skaterFullName': 'playerName', 'teamAbbrevs': 'teamAbbrev', 'points': 'totalPoints'}, inplace=True)
        return df
    df_p = get_data(3); df_r = get_data(2)
    for df in [df_p, df_r]:
        if not df.empty:
            df['lastName'] = df['playerName'].apply(lambda x: str(x).split(' ', 1)[-1].lower() if ' ' in str(x) else str(x).lower())
            for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']:
                if col not in df.columns: df[col] = 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if not df_p.empty:
        if not df_r.empty:
            df_r = df_r[~df_r['playerId'].isin(df_p['playerId'].tolist())].copy()
            for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']: df_r[col] = 0
            return pd.concat([df_p, df_r], ignore_index=True)
        return df_p
    return df_r if not df_r.empty else pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_points(pids, days):
    cutoff = (datetime.datetime.now(PT_ZONE) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    pts_dict = {}
    for pid in pids:
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/now", headers=HEADERS, timeout=5)
            pts = 0
            if res.status_code == 200:
                for g in res.json().get('gameLog', []):
                    if g['gameDate'] >= cutoff: pts += g.get('goals', 0) + g.get('assists', 0)
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

# --- 4. AI ROAST LOGIC ---
@st.cache_data(ttl=600) # 10 minute cache
def generate_ai_roast(gm_name, pts, active, elim, t_type, salt):
    if not GEMINI_READY: return f"The pool is heating up! {gm_name} has {pts} points."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Write a 1-sentence sarcastic hockey roast about fantasy GM {gm_name} who has {pts} points and {elim} eliminated players. Use public sentiment about playoff failure."
        if t_type == "leafs":
            days = (datetime.datetime.now(PT_ZONE).date() - datetime.date(1967, 5, 2)).days
            prompt = f"Write a 1-sentence sarcastic roast about the Toronto Maple Leafs. Mention they have {pts} total points in our pool and it has been {days} days since 1967. Hit hard on public sentiment."
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"ROAST ERROR: {e}"

# --- 5. MAIN LOGIC ---
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])
with t_title: st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️"):
        new_name = st.text_input("Display Name", value=st.session_state.display_name)
        if st.button("Update Name"): st.session_state.display_name = new_name; st.rerun()
        if st.button("Log Out"): cookie_manager.delete('user_email_cookie'); st.session_state.authenticated = False; st.rerun()

st.divider()
nav = st.segmented_control("Navigation", ["League", "My Team", "All Rosters"], default="League", label_visibility="collapsed") or "League"

stats = fetch_live_data()
ELIMINATED_TEAMS = get_eliminated_teams()
TEAMS_PLAYING_TODAY = get_teams_playing_today()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    if 'Draft Rounds' not in df_raw.columns: df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [c for c in df_raw.columns if c in USER_DB.values()]
except: st.stop()

def clean_and_match(pick_str, stats_df):
    if pd.isna(pick_str) or str(pick_str).strip() == '': return None
    parts = str(pick_str).split('-'); raw_name = parts[0].strip(); t_part = parts[1].strip().upper() if len(parts) > 1 else ""
    t_part = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}.get(t_part, t_part)
    
    # Filter by team first
    team_df = stats_df[stats_df['teamAbbrev'] == t_part] if not stats_df.empty and t_part else stats_df
    if not team_df.empty:
        matches = difflib.get_close_matches(raw_name.lower(), team_df['playerName'].str.lower().tolist(), n=1, cutoff=0.5)
        if matches: return team_df[team_df['playerName'].str.lower() == matches[0]].iloc[0].to_dict()
    return {'playerName': raw_name.title(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '', 'playerId': None}

master_list = []
for idx, row in df_raw.iterrows():
    if "Round" not in str(row.get('Draft Rounds', '')): continue
    for gm in gms:
        pick = str(row.get(gm, '')).strip()
        if not pick or pick.lower() == 'nan': continue
        p_data = clean_and_match(pick, stats)
        master_list.append({
            'GM': gm, 'Player_Id': p_data.get('playerId'), 'Player_Name': p_data.get('playerName'),
            'Team_Raw': p_data.get('teamAbbrev'), 'Position': p_data.get('positionCode'),
            'Points': p_data.get('totalPoints'), 'G': p_data.get('goals'), 'A': p_data.get('assists'),
            'GP': p_data.get('gamesPlayed'), 'Round': str(row['Draft Rounds']).replace("Round", "").strip()
        })
master_df = pd.DataFrame(master_list)
master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).astype(int)
master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(lambda x: "🥇 1" if x==1 else "🥈 2" if x==2 else "🥉 3" if x==3 else str(x))

display_gms = sorted([st.session_state.display_name if g == st.session_state.gm_name else g for g in gms])
if st.session_state.display_name: master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)

def generate_table(df):
    h = "<table class='team-table'><tr><th class='text-left'>Round</th><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Top Pick</th></tr>"
    for _, r in df.iterrows():
        is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
        is_playing = r['Team_Raw'] in TEAMS_PLAYING_TODAY and not is_elim
        decor = "line-through" if is_elim else "none"
        active = " 🔥" if is_playing else ""
        news = f"<a href='https://news.google.com/search?q={r['Player_Name']}+NHL+when:2d' target='_blank' title='Player News'>📄</a>"
        h += f"<tr style='text-decoration: {decor};'><td>{r['Round']}</td><td class='text-left'>{r['Player_Name']} {news}{active}</td><td>{r['Team_Raw']}</td><td>{r['Position']}</td><td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Top Pick/Rnd']}</td></tr>"
    return h + "</table>"

# --- 6. UI ---
salt = str(random.randint(1, 1000000)) # Forces cache to refresh on manual rerun

if nav == "League":
    lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index().sort_values(['Points', 'G'], ascending=False)
    counts = master_df[~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    
    worst = lb.iloc[-1]; leafs_pts = master_df[master_df['Team_Raw'] == 'TOR']['Points'].sum()
    q1 = generate_ai_roast("Toronto", leafs_pts, 0, 0, "leafs", salt)
    q2 = generate_ai_roast(worst['GM'], worst['Points'], 0, 0, "normal", salt)
    
    col_roast, col_btn = st.columns([0.85, 0.15])
    with col_roast: st.markdown(f"<div class='roast-container'><div class='quote-1'><b>{q1}</b></div><div class='quote-2'><b>{q2}</b></div></div>", unsafe_allow_html=True)
    with col_btn: 
        if st.button("🔄 New Roasts"): st.cache_data.clear(); st.rerun()

    lb['Rank'] = range(1, len(lb)+1)
    lb_html = "<table class='team-table'><tr><th>Rank</th><th>Name</th><th>GP</th><th>Pts</th><th>G</th><th>A</th><th>Rem</th></tr>"
    for _, r in lb.iterrows(): lb_html += f"<tr><td>{r['Rank']}</td><td class='text-left'>{r['GM']}</td><td>{r['GP']}</td><td><b>{r['Points']}</b></td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Rem']}</td></tr>"
    st.markdown(lb_html + "</table>", unsafe_allow_html=True)

elif nav == "My Team":
    sel_gm = st.selectbox("View Team", display_gms, index=display_gms.index(st.session_state.display_name) if st.session_state.display_name in display_gms else 0)
    my_df = master_df[master_df['GM'] == sel_gm]
    
    q = generate_ai_roast(sel_gm, my_df['Points'].sum(), 0, len(my_df[my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]), "normal", salt)
    col_roast, col_btn = st.columns([0.85, 0.15])
    with col_roast: st.markdown(f"<div class='roast-container' style='animation:none;'><b style='color:#0068c9;'>{q}</b></div>", unsafe_allow_html=True)
    with col_btn: 
        if st.button("🔄 New Roast"): st.cache_data.clear(); st.rerun()

    k1, k2, k3 = st.columns(3)
    p_today = sum(get_historical_points(my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY)]['Player_Id'].dropna(), 0).values())
    k1.metric("Points Today", p_today)
    k2.metric("Players Active Today", len(my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY) & ~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))
    k3.metric("Players Remaining", len(my_df[~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))
    
    st.markdown(generate_table(my_df), unsafe_allow_html=True)

elif nav == "All Rosters":
    for g in display_gms:
        st.subheader(g)
        st.markdown(generate_table(master_df[master_df['GM'] == g]), unsafe_allow_html=True)

if st.sidebar.checkbox("Debug Mode"):
    st.sidebar.write("Ready:", GEMINI_READY)
    st.sidebar.write("Last Sync:", datetime.datetime.now(PT_ZONE))
