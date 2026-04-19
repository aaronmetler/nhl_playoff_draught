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

# AI Setup
try:
    import google.generativeai as genai
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        GEMINI_READY = True
    else:
        GEMINI_READY = False
except Exception:
    GEMINI_READY = False

# --- CUSTOM CSS (Restored Layout Specs) ---
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
            min-height: 45px; 
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
        .team-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem; }
        .team-table th { border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 8px; }
        .team-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: center; }
        .team-table td.text-left, .team-table th.text-left { text-align: left; }
        .team-table a { text-decoration: none; color: inherit; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0068c9; text-align: center; }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_manager")

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None

PT_ZONE = ZoneInfo("America/Los_Angeles")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

# --- 2. AUTHENTICATION ---
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
            try:
                res = requests.get(base_url, params={"isAggregate": "false", "isGame": "false", "start": start, "limit": limit, "cayenneExp": f"gameTypeId={gt} and seasonId=20252026"}, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    d = res.json().get('data', [])
                    if not d: break
                    all_d.extend(d)
                    if len(d) < limit: break
                    start += limit
                else: break
            except: break
        df = pd.DataFrame(all_d)
        if not df.empty: df.rename(columns={'skaterFullName': 'playerName', 'teamAbbrevs': 'teamAbbrev', 'points': 'totalPoints'}, inplace=True)
        return df
    df_p = get_data(3); df_r = get_data(2)
    for df in [df_p, df_r]:
        if not df.empty:
            df['playerName'] = df['playerName'].fillna('')
            df['lastName'] = df['playerName'].apply(lambda x: str(x).split(' ', 1)[-1].lower() if ' ' in str(x) else str(x).lower())
            for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']:
                if col not in df.columns: df[col] = 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
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
@st.cache_data(ttl=900) 
def generate_ai_roast(gm_name, pts, elim, t_type, salt):
    if not GEMINI_READY: return f"Meanwhile, {gm_name} has {pts} points."
    try:
        days = (datetime.datetime.now(PT_ZONE).date() - datetime.date(1967, 5, 2)).days
        if t_type == "leafs":
            prompt = f"Brutal 1-sentence sarcastic roast about Toronto Maple Leafs. Pool points: {pts}, {days} days since 1967. Use public sentiment."
        else:
            prompt = f"1-sentence sarcastic hockey roast about fantasy GM {gm_name} with {pts} points and {elim} eliminated players. Channel public sentiment."
        
        response = genai.GenerativeModel('gemini-2.0-flash').generate_content(prompt)
        return response.text.strip()
    except: return f"Meanwhile, {gm_name} is trying their best with {pts} points."

# --- 5. UI HELPERS ---
def get_avatar_uri(gm_check_name):
    if gm_check_name == st.session_state.display_name and st.session_state.avatar:
        b64 = base64.b64encode(st.session_state.avatar).decode()
        return f"data:image/png;base64,{b64}"
    default_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#a0aec0"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
    return f"data:image/svg+xml;base64,{base64.b64encode(default_svg.encode('utf-8')).decode('utf-8')}"

def generate_team_table_html(df):
    h = "<table class='team-table'><tr><th class='text-left'>Round</th><th class='text-left'>Player</th><th>Team</th><th>Pos</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Top Pick</th></tr>"
    for _, r in df.iterrows():
        is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
        is_playing = r['Team_Raw'] in TEAMS_PLAYING_TODAY and not is_elim
        decor = "line-through" if is_elim else "none"
        active = " 🔥" if is_playing else ""
        news = f"<a href='https://news.google.com/search?q={r['Player_Name']}+NHL+when:2d' target='_blank' title='Player News'>📄</a>"
        h += f"<tr style='text-decoration: {decor};'><td>{r['Round']}</td><td class='text-left'>{r['Player_Name']} {news}{active}</td><td>{r['Team_Raw']}</td><td>{r['Position']}</td><td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td><td>{r['Top Pick/Rnd']}</td></tr>"
    return h + "</table>"

# --- 6. MAIN APP HEADER ---
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])
with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
with t_title: st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
with t_text: st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
with t_img:
    if st.session_state.avatar: st.image(st.session_state.avatar, width=35)
    else: st.markdown("<div style='font-size: 24px; text-align: center; margin-top: -3px;'>👤</div>", unsafe_allow_html=True)
with t_menu:
    with st.popover("⚙️"):
        new_disp = st.text_input("Display Name", value=st.session_state.display_name)
        if st.button("Update"): st.session_state.display_name = new_disp; st.rerun()
        file = st.file_uploader("Upload Avatar", type=["jpg", "png", "jpeg"])
        if st.button("Save Avatar") and file: st.session_state.avatar = file.getvalue(); st.rerun()
        if st.button("Log Out"): cookie_manager.delete('user_email_cookie'); st.session_state.authenticated = False; st.rerun()

st.divider()
nav = st.segmented_control("Nav", ["League", "My Team", "All Rosters"], default="League", label_visibility="collapsed") or "League"

# --- 7. DATA PROCESSING ---
stats = fetch_live_data()
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
        matches = difflib.get_close_matches(raw_name.lower(), lookup_df['playerName'].str.lower().tolist(), n=1, cutoff=0.5)
        if matches: return lookup_df[lookup_df['playerName'].str.lower() == matches[0]].iloc[0].to_dict()
    return {'playerName': raw_name.title(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '', 'playerId': None}

master_list = []
for _, row in df_raw.iterrows():
    if "Round" not in str(row.get('Draft Rounds', '')): continue
    for gm in gms_cols:
        pick = str(row.get(gm, '')).strip()
        if not pick or pick.lower() == 'nan': continue
        p = clean_and_match(pick, stats)
        master_list.append({'GM': gm, 'Player_Id': p.get('playerId'), 'Player_Name': p.get('playerName'), 'Team_Raw': p.get('teamAbbrev'), 'Position': p.get('positionCode'), 'Points': p.get('totalPoints', 0), 'G': p.get('goals', 0), 'A': p.get('assists', 0), 'GP': p.get('gamesPlayed', 0), 'Round': str(row['Draft Rounds']).replace("Round", "").strip()})
master_df = pd.DataFrame(master_list)
master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).astype(int)
master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(lambda x: "🥇 1" if x==1 else "🥈 2" if x==2 else "🥉 3" if x==3 else str(x))

display_gms = sorted([st.session_state.display_name if g == st.session_state.gm_name else g for g in gms_cols])
if st.session_state.display_name: master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)

# --- 8. UI VIEWS ---
salt = str(random.randint(1, 1000000))

if nav == "League":
    lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index().sort_values(['Points', 'G'], ascending=False)
    counts = master_df[~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)].groupby('GM').size().reset_index(name='Rem')
    lb = pd.merge(lb, counts, on='GM', how='left').fillna(0)
    lb['Rank'] = range(1, len(lb)+1)
    max_pts = lb['Points'].max()
    lb['Pts Back'] = max_pts - lb['Points']
    
    worst = lb.iloc[-1]; leafs_pts = master_df[master_df['Team_Raw'] == 'TOR']['Points'].sum()
    q1 = generate_ai_roast("Toronto", leafs_pts, 0, "leafs", salt)
    q2 = generate_ai_roast(worst['GM'], worst['Points'], 10 - int(worst['Rem']), "normal", salt)
    
    col_roast, col_btn = st.columns([0.85, 0.15])
    with col_roast: st.markdown(f"<div class='roast-container'><div class='quote-1'><b>{q1}</b></div><div class='quote-2'><b>{q2}</b></div></div>", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Roasts"): st.cache_data.clear(); st.rerun()

    lb_html = "<table class='team-table'><tr><th>Rank</th><th></th><th class='text-left'>Name</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Pts Yesterday</th><th>Pts Back</th><th>Remaining</th></tr>"
    for _, r in lb.iterrows():
        avatar = f"<img src='{get_avatar_uri(r['GM'])}' width='30' style='border-radius:50%; vertical-align: middle;'>"
        lb_html += f"<tr><td>{r['Rank']}</td><td>{avatar}</td><td class='text-left'>{r['GM']}</td><td>{r['GP']}</td><td><b>{r['Points']}</b></td><td>{r['G']}</td><td>{r['A']}</td><td>0</td><td>{r['Pts Back']}</td><td>{int(r['Rem'])}</td></tr>"
    st.markdown(lb_html + "</table>", unsafe_allow_html=True)

elif nav == "My Team":
    sel_gm = st.selectbox("View Another Team", display_gms, index=display_gms.index(st.session_state.display_name) if st.session_state.display_name in display_gms else 0)
    my_df = master_df[master_df['GM'] == sel_gm]
    q = generate_ai_roast(sel_gm, my_df['Points'].sum(), len(my_df[my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]), "normal", salt)
    
    col_roast, col_btn = st.columns([0.85, 0.15])
    with col_roast: st.markdown(f"<div class='roast-container' style='animation:none;'><b style='color:#0068c9;'>{q}</b></div>", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh AI"): st.cache_data.clear(); st.rerun()

    c1, c2, c3, c4, c5 = st.columns([2.2, 2.0, 1.2, 1.4, 1.4])
    with c1: st.empty() # Placeholder for selection
    with c2: time_options = {'All Time': 0, 'Yesterday': 1, 'Last 48 Hours': 2, 'Last 7 Days': 7, 'Last 14 Days': 14, 'Last 30 Days': 30}; stat_filter = st.selectbox("Stats", list(time_options.keys()))
    
    pids = my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY)]['Player_Id'].dropna()
    p_today = sum(get_historical_points(pids, 0).values()) if not pids.empty else 0
    with c3: st.metric("Points Today", p_today)
    with c4: st.metric("Players Active Today", len(my_df[my_df['Team_Raw'].isin(TEAMS_PLAYING_TODAY) & ~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))
    with c5: st.metric("Players Remaining", len(my_df[~my_df['Team_Raw'].isin(ELIMINATED_TEAMS)]))

    st.markdown("<p style='font-size: 0.85rem; color: #888;'>➤ 🔥 indicates playing today<br>➤ <span style='text-decoration: line-through;'>Strikethrough</span> indicates player is eliminated</p>", unsafe_allow_html=True)
    st.markdown(generate_team_table_html(my_df), unsafe_allow_html=True)

elif nav == "All Rosters":
    for g in display_gms:
        st.markdown(f"<h3 style='color:#0068c9; margin-top:20px;'>{g}</h3>", unsafe_allow_html=True)
        st.markdown(generate_team_table_html(master_df[master_df['GM'] == g]), unsafe_allow_html=True)
