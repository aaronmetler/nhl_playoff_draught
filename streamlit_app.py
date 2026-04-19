import streamlit as st
import pandas as pd
import requests
import datetime
import base64
import extra_streamlit_components as stx
import xml.etree.ElementTree as ET
import os

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
        }
        hr {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        
        /* Roast Box CSS */
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
        
        /* Custom HTML Table CSS */
        .team-table {
            width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 2rem;
        }
        .team-table th {
            border-bottom: 2px solid #ddd; color: #888; text-align: center; padding: 8px;
        }
        .team-table td {
            border-bottom: 1px solid #eee; padding: 8px; text-align: center;
        }
        .team-table td.text-left, .team-table th.text-left {
            text-align: left;
        }
        .team-table a { text-decoration: none; }
        .team-table a:hover { text-decoration: underline; }
        
        /* KPI Centering */
        [data-testid="stMetric"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        [data-testid="stMetricValue"] { 
            font-size: 1.8rem; 
            color: #0068c9; 
            text-align: center; 
        }
        [data-testid="stMetricLabel"] { 
            text-align: center; 
        }
    </style>
""", unsafe_allow_html=True)

# Cookie Manager with Unique Key to prevent Streamlit Duplicate Element errors
cookie_manager = stx.CookieManager(key="cookie_manager")

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'gm_name' not in st.session_state: st.session_state.gm_name = None
if 'display_name' not in st.session_state: st.session_state.display_name = None
if 'avatar' not in st.session_state: st.session_state.avatar = None

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

# Anti-Bot Header to bypass Cloudflare
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def is_authenticated():
    if st.session_state.authenticated: return True
    saved_email = cookie_manager.get('user_email_cookie')
    if saved_email and saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        if not st.session_state.display_name:
            st.session_state.display_name = USER_DB[saved_email]
        return True
    return False

# --- LOGIN SCREEN ---
if not is_authenticated():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏒 Playoff Pool Login")
        with st.form("login_form"):
            saved_email_input = cookie_manager.get('saved_email_input') or ""
            email = st.text_input("Email", value=saved_email_input).lower().strip()
            pwd = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember my email", value=bool(saved_email_input))
            submit = st.form_submit_button("Sign In")
            
            if submit:
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
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- 3. MAIN APP HEADER ---
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])

with t_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=55)
        
with t_title: 
    st.markdown("<h1 style='margin-top: -10px; margin-bottom: -15px; font-size: 2.6rem;'>Metler Playoff Pool</h1>", unsafe_allow_html=True)
    
with t_text: 
    st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 16px;'>Welcome, <b>{st.session_state.display_name}</b></div>", unsafe_allow_html=True)
    
with t_img:
    if st.session_state.avatar: st.image(st.session_state.avatar, width=35)
    else: st.markdown("<div style='font-size: 24px; text-align: center; margin-top: -3px;'>👤</div>", unsafe_allow_html=True)
    
with t_menu:
    with st.popover("⚙️"):
        st.markdown("**Profile Settings**")
        new_name = st.text_input("Display Name", value=st.session_state.display_name)
        if st.button("Update Name"):
            st.session_state.display_name = new_name
            st.rerun()
        st.divider()
        file = st.file_uploader("Upload Avatar", type=["jpg", "png", "jpeg"])
        if st.button("Save Avatar"):
            if file:
                st.session_state.avatar = file.getvalue()
                st.rerun()
        st.divider()
        if st.button("Log Out", use_container_width=True):
            cookie_manager.delete('user_email_cookie')
            st.session_state.authenticated = False
            st.session_state.gm_name = None
            st.session_state.display_name = None
            st.session_state.avatar = None
            st.rerun()
            
st.divider()

# --- 4. NAVIGATION ---
try:
    nav = st.segmented_control("Navigation", ["League", "My Team", "All Rosters"], default="League", label_visibility="collapsed")
except AttributeError:
    nav = st.radio("Navigation", ["League", "My Team", "All Rosters"], horizontal=True, label_visibility="collapsed")

if nav is None: nav = "League"

# --- 5. DATA FETCHING & LOGIC ---
@st.cache_data(ttl=3600*24)
def get_roster_dictionary():
    roster_dict = {}
    for t in TEAM_URLS.keys():
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/roster/{t}/current", headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for group in ['forwards', 'defensemen', 'goalies']:
                    for p in data.get(group, []):
                        name = f"{p['firstName']['default']} {p['lastName']['default']}".lower()
                        clean_name = name.replace('ü', 'u').replace('.', '')
                        roster_dict[clean_name] = {'id': p.get('id'), 'pos': p.get('positionCode', 'G')}
        except: pass
    return roster_dict

@st.cache_data(ttl=3600)
def fetch_live_data():
    base_url_skater = "https://api.nhle.com/stats/rest/en/skater/summary"
    base_url_goalie = "https://api.nhle.com/stats/rest/en/goalie/summary"
    
    def get_data(url, game_type):
        all_data = []
        start = 0
        limit = 100
        while True:
            params = {
                "isAggregate": "false", 
                "isGame": "false", 
                "start": start, 
                "limit": limit, 
                "cayenneExp": f"gameTypeId={game_type} and seasonId=20252026"
            }
            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json().get('data', [])
                    if not data: break
                    all_data.extend(data)
                    if len(data) < limit: break
                    start += limit
                else:
                    break
            except Exception:
                break
        return pd.DataFrame(all_data)

    df_p_s = get_data(base_url_skater, 3)
    df_r_s = get_data(base_url_skater, 2)
    df_p_g = get_data(base_url_goalie, 3)
    df_r_g = get_data(base_url_goalie, 2)
    
    df_p = pd.concat([df_p_s, df_p_g], ignore_index=True) if not df_p_s.empty or not df_p_g.empty else pd.DataFrame()
    df_r = pd.concat([df_r_s, df_r_g], ignore_index=True) if not df_r_s.empty or not df_r_g.empty else pd.DataFrame()

    for df in [df_p, df_r]:
        if not df.empty:
            df.rename(columns={'skaterFullName': 'playerName', 'goalieFullName': 'playerName', 'teamAbbrevs': 'teamAbbrev', 'points': 'totalPoints'}, inplace=True)
            if 'playerName' not in df.columns: df['playerName'] = ''
            df['lastName'] = df['playerName'].apply(lambda x: str(x).split(' ', 1)[-1].lower() if ' ' in str(x) else str(x).lower())
            
            for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']:
                if col not in df.columns: df[col] = 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if not df_p.empty:
        if not df_r.empty:
            existing_ids = df_p['playerId'].tolist()
            df_r = df_r[~df_r['playerId'].isin(existing_ids)].copy()
            for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']: df_r[col] = 0
            return pd.concat([df_p, df_r], ignore_index=True)
        return df_p
        
    elif not df_r.empty:
        for col in ['goals', 'assists', 'totalPoints', 'gamesPlayed']: df_r[col] = 0
        return df_r
        
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_points(player_ids, days):
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    hist_pts = {}
    for pid in player_ids:
        if not pid: 
            hist_pts[pid] = 0
            continue
        try:
            res = requests.get(f"https://api-web.nhle.com/v1/player/{pid}/game-log/now", headers=HEADERS, timeout=5)
            pts = 0
            if res.status_code == 200:
                for g in res.json().get('gameLog', []):
                    if g['gameDate'] >= cutoff_date:
                        pts += g.get('goals', 0) + g.get('assists', 0)
            hist_pts[pid] = pts
        except:
            hist_pts[pid] = 0
    return hist_pts

@st.cache_data(ttl=3600)
def get_eliminated_teams():
    eliminated = set()
    try:
        res = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            series_list = data.get('series', [])
            if not series_list and 'rounds' in data:
                series_list = [s for r in data['rounds'] for s in r.get('series', [])]
            for s in series_list:
                m = s.get('matchupTeams', [])
                if len(m) == 2:
                    w1 = m[0].get('seriesRecord', {}).get('wins', 0)
                    w2 = m[1].get('seriesRecord', {}).get('wins', 0)
                    if w1 == 4: eliminated.add(m[1].get('team', {}).get('abbrev', m[1].get('teamAbbrev')))
                    if w2 == 4: eliminated.add(m[0].get('team', {}).get('abbrev', m[0].get('teamAbbrev')))
                top, bot = s.get('topSeed', {}), s.get('bottomSeed', {})
                if top and bot:
                    if top.get('wins', 0) == 4: eliminated.add(bot.get('abbrev', bot.get('teamAbbrev')))
                    if bot.get('wins', 0) == 4: eliminated.add(top.get('abbrev', top.get('teamAbbrev')))
    except: pass
    return [t for t in list(eliminated) if t]

@st.cache_data(ttl=3600)
def get_teams_playing_today():
    try:
        res = requests.get("https://api-web.nhle.com/v1/schedule/now", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            teams = set()
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            for day in data.get('gameWeek', []):
                if day.get('date') == today_str:
                    for game in day.get('games', []):
                        teams.add(game['awayTeam']['abbrev'])
                        teams.add(game['homeTeam']['abbrev'])
            return list(teams)
    except: pass
    return []

@st.cache_data(ttl=3600)
def get_daily_headline():
    headline = "NHL playoffs continue with fierce matchups"
    try:
        resp = requests.get("https://www.espn.com/espn/rss/nhl/news", headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall('.//item/title')
            if items: headline = items[0].text
    except: pass
    return headline

def get_worst_gm_roast(master_df, headline):
    if master_df.empty: return f"**NHL News:** {headline}. Meanwhile, everyone here is tied at 0 points."
    lb = master_df.groupby('GM').agg({'Points': 'sum'}).reset_index()
    lb = lb.sort_values('Points', ascending=True)
    worst_gm, worst_pts = lb.iloc[0]['GM'], lb.iloc[0]['Points']
    
    roasts = [
        f"📰 \"{headline}\" — Meanwhile, {worst_gm} is completely oblivious, sitting in last place with a pathetic {worst_pts} points.",
        f"📰 \"{headline}\" — A major story, unless you are {worst_gm}, whose team is currently a bigger disaster at {worst_pts} points.",
        f"📰 \"{headline}\" — Sadly, none of this helps {worst_gm}'s roster, which is participating in an active point-scoring boycott.",
        f"📰 \"{headline}\" — In unrelated news, {worst_gm}'s team continues to be an absolute dumpster fire."
    ]
    return roasts[datetime.datetime.now().day % len(roasts)]

def get_team_roast(selected_gm, my_team_df, headline):
    if my_team_df.empty: return "Where is your team?"
    pts = my_team_df['Points'].sum()
    eliminated = my_team_df[my_team_df['Team_Raw'].isin(ELIMINATED_TEAMS)].shape[0]
    
    if pts == 0:
        return f"📰 \"{headline}\" — None of this matters to {selected_gm}, whose entire roster is currently invisible (0 points)."
    elif eliminated >= 4:
        return f"📰 \"{headline}\" — Fun fact: Half of {selected_gm}'s roster is already golfing while generating a mediocre {pts} points."
    elif pts < 15:
        return f"📰 \"{headline}\" — Also, {selected_gm} is struggling to remain relevant with a sad {pts} points."
    else:
        return f"📰 \"{headline}\" — {selected_gm} is scraping together {pts} points, but we all know it won't last."

roster_dict = get_roster_dictionary()
stats = fetch_live_data()
ELIMINATED_TEAMS = get_eliminated_teams()
TEAMS_PLAYING_TODAY = get_teams_playing_today()
DAILY_HEADLINE = get_daily_headline()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    if 'Draft Rounds' not in df_raw.columns: df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [c for c in df_raw.columns if c in USER_DB.values()]
except:
    st.error("Missing or invalid CSV file.")
    st.stop()

def clean_and_match(pick_str, stats_df):
    if pd.isna(pick_str) or str(pick_str).strip() == '': return None
    
    parts = str(pick_str).split('-')
    name_str = parts[0].strip().replace('ü', 'u')
    t_part = parts[1].strip().upper() if len(parts) > 1 else ""
    
    team_map = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}
    t_part = team_map.get(t_part, t_part)
    
    name_tokens = name_str.split()
    n_part = name_tokens[-1].lower() if name_tokens else ""
    
    if stats_df.empty:
        return {'lastName': n_part, 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '', 'playerId': None, 'playerName': name_str.title()}
    
    if t_part:
        match = stats_df[(stats_df['lastName'].str.contains(n_part, case=False, na=False)) & (stats_df['teamAbbrev'].str.contains(t_part, case=False, na=False))]
    else:
        match = pd.DataFrame()
        
    if not match.empty: return match.iloc[0].to_dict()
    
    match_name_only = stats_df[stats_df['lastName'].str.contains(n_part, case=False, na=False)]
    if not match_name_only.empty: return match_name_only.iloc[0].to_dict()
    
    return {'lastName': n_part, 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part, 'positionCode': '', 'playerId': None, 'playerName': name_str.title()}

master_list = []
for index, row in df_raw.iterrows():
    round_name = str(row.get('Draft Rounds', ''))
    if "Round" not in round_name: continue
    
    round_num = round_name.replace("Round", "").strip()
    
    for gm in gms:
        pick_str = str(row.get(gm, '')).strip()
        if not pick_str or pd.isna(pick_str) or pick_str.lower() == 'nan': continue
        
        p_data = clean_and_match(pick_str, stats)
        if p_data is None: continue
        
        p_name = p_data.get('playerName', '')
        if not p_name: p_name = pick_str.split('-')[0].strip()
        
        p_id = p_data.get('playerId')
        pos = p_data.get('positionCode', '')
        
        if not p_id or not pos:
            search_name = pick_str.split('-')[0].strip().replace('ü','u').lower()
            for full_name, info in roster_dict.items():
                if search_name in full_name or full_name in search_name:
                    p_id = p_id or info['id']
                    pos = pos or info['pos']
                    break
        
        player_url = f"https://www.nhl.com/player/{p_id}" if p_id else f"https://www.google.com/search?q=NHL+{p_name.replace(' ', '+')}"
        t_abbrev = p_data.get('teamAbbrev', pick_str.split()[-1].upper() if '-' in pick_str else "")
        t_url = f"https://www.nhl.com/{TEAM_URLS.get(t_abbrev, 'standings')}" if t_abbrev else "https://www.nhl.com"
        
        master_list.append({
            'GM': gm, 
            'Player_Id': p_id,
            'Player_Name': p_name,
            'Player_URL': player_url,
            'Team_Raw': t_abbrev,
            'Team_URL': t_url,
            'Position': pos,
            'Points': p_data.get('totalPoints', 0), 
            'G': p_data.get('goals', 0), 
            'A': p_data.get('assists', 0), 
            'GP': p_data.get('gamesPlayed', 0), 
            'Round': round_num
        })
        
master_df = pd.DataFrame(master_list)

if not master_df.empty:
    master_df['Points'] = pd.to_numeric(master_df['Points'], errors='coerce').fillna(0).astype(int)
    master_df['G'] = pd.to_numeric(master_df['G'], errors='coerce').fillna(0).astype(int)
    master_df['A'] = pd.to_numeric(master_df['A'], errors='coerce').fillna(0).astype(int)
    master_df['GP'] = pd.to_numeric(master_df['GP'], errors='coerce').fillna(0).astype(int)

    master_df['P/PG'] = master_df.apply(lambda r: f"{r['Points'] / r['GP']:.2f}" if r['GP'] > 0 else "0.00", axis=1)
    master_df['Rank by Round'] = master_df.groupby('Round')['Points'].rank(method='min', ascending=False).fillna(0).astype(int)
    
    def get_medal(rank):
        if rank == 1: return "🥇 1"
        if rank == 2: return "🥈 2"
        if rank == 3: return "🥉 3"
        return str(rank)
    master_df['Top Pick/Rnd'] = master_df['Rank by Round'].apply(get_medal)

if st.session_state.display_name and st.session_state.display_name != st.session_state.gm_name:
    master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    display_gms = sorted([st.session_state.display_name if g == st.session_state.gm_name else g for g in gms])
else:
    display_gms = sorted(gms)

def get_avatar_uri(gm_check_name):
    if gm_check_name == st.session_state.display_name and st.session_state.avatar:
        b64 = base64.b64encode(st.session_state.avatar).decode()
        return f"data:image/png;base64,{b64}"
    default_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#a0aec0"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
    b64_svg = base64.b64encode(default_svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64_svg}"

active_img_html = "<span title='Active Today' style='margin-left: 4px;'>🔥</span>"

# --- HTML TABLE GENERATORS ---
def generate_team_html(team_df):
    html = "<table class='team-table'>"
    html += "<tr><th class='text-left'>Round</th><th class='text-left'>Player</th><th>Team</th><th>Position</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>P/PG</th><th>Top Pick/Rnd</th></tr>"
    
    for _, r in team_df.iterrows():
        is_elim = r['Team_Raw'] in ELIMINATED_TEAMS
        is_playing = r['Team_Raw'] in TEAMS_PLAYING_TODAY and not is_elim
        
        bg = "transparent" 
        color = "inherit"  
        text_decor = "line-through" if is_elim else "none"
        
        p_link = f"<a href='{r['Player_URL']}' target='_blank' style='color: {color}; text-decoration: {text_decor};'>{r['Player_Name']}</a>"
        news_link = f"<a href='https://news.google.com/search?q={str(r['Player_Name']).replace(' ', '+')}+NHL+when:2d' target='_blank' title='Player News' style='text-decoration: none;'>📄</a>"
        active_indicator = f" {active_img_html}" if is_playing else ""
        
        player_cell = f"{p_link} {news_link}{active_indicator}"
        t_link = f"<a href='{r['Team_URL']}' target='_blank' style='color: {color}; text-decoration: {text_decor};'>{r['Team_Raw']}</a>"
        
        html += f"<tr style='background-color: {bg}; color: {color}; text-decoration: {text_decor};'>"
        html += f"<td class='text-left'>{r['Round']}</td><td class='text-left'>{player_cell}</td><td>{t_link}</td><td>{r['Position']}</td>"
        html += f"<td>{r['GP']}</td><td>{r['Points']}</td><td>{r['G']}</td><td>{r['A']}</td>"
        html += f"<td>{r['P/PG']}</td><td>{r['Top Pick/Rnd']}</td></tr>"
        
    html += "</table>"
    return html

def generate_league_html(lb_df):
    html = "<table class='team-table'>"
    html += "<tr><th>Rank</th><th></th><th class='text-left'>Name</th><th>GP</th><th>Points</th><th>G</th><th>A</th><th>Pts Yesterday</th><th>Pts Back</th><th>Players Remaining</th></tr>"
    
    for _, r in lb_df.iterrows():
        avatar_img = f"<img src='{r['Avatar']}' width='30' style='border-radius:50%; vertical-align: middle;'>"
        
        html += f"<tr>"
        html += f"<td><b>{r['Rank']}</b></td><td>{avatar_img}</td><td class='text-left'>{r['Name']}</td>"
        html += f"<td>{r['GP']}</td><td><b>{r['Points']}</b></td><td>{r['G']}</td><td>{r['A']}</td>"
        html += f"<td>{r['Pts Yesterday']}</td><td>{r['Pts Back']}</td><td>{r['Players Remaining']}</td></tr>"
        
    html += "</table>"
    return html

# --- 6. UI VIEWS ---
LEAFS_ROASTS = [
    "Toronto Maple Leafs Update: Currently scheduling tee times for May.",
    "Toronto Maple Leafs Update: Planning the Stanley Cup parade... for the Marlies.",
    "Toronto Maple Leafs Update: Local golf courses report surge in tee time bookings from Scotiabank Arena.",
    "Toronto Maple Leafs Update: 1967 was a great year. Too bad it's 2026."
]

if nav == "League":
    leafs_quote = LEAFS_ROASTS[datetime.datetime.now().day % len(LEAFS_ROASTS)]
    worst_gm_quote = get_worst_gm_roast(master_df, DAILY_HEADLINE)
    st.markdown(f"""
        <div class="roast-container">
            <div class="quote-1">🍁 <b>{leafs_quote}</b></div>
            <div class="quote-2">🚨 <b>{worst_gm_quote}</b></div>
        </div>
    """, unsafe_allow_html=True)

    if not master_df.empty:
        lb = master_df.groupby('GM').agg({'GP': 'sum', 'Points': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index()
        
        active_mask = ~master_df['Team_Raw'].isin(ELIMINATED_TEAMS)
        active_counts = master_df[active_mask].groupby('GM').size().reset_index(name='Players Remaining')
        lb = pd.merge(lb, active_counts, on='GM', how='left').fillna(0)
        lb['Players Remaining'] = lb['Players Remaining'].astype(int)
        
        lb = lb.sort_values(by=['Points', 'G'], ascending=False).reset_index(drop=True)
        lb['Rank'] = (lb.index + 1).astype(str) 
        
        max_pts = lb['Points'].max() if not lb.empty else 0
        lb['Pts Back'] = max_pts - lb['Points']
        
        def add_trophy(row):
            if row['Rank'] == '1': return f"🏆 {row['GM']}"
            elif row['Rank'] == '2': return f"🥈 {row['GM']}"
            return row['GM']
            
        lb['Name'] = lb.apply(add_trophy, axis=1)
        lb['Pts Yesterday'] = 0  
        lb['Avatar'] = lb['GM'].apply(get_avatar_uri) 
        
        st.markdown(generate_league_html(lb), unsafe_allow_html=True)

elif nav == "My Team":
    default_idx = display_gms.index(st.session_state.display_name) if st.session_state.display_name in display_gms else 0
    selected_gm_temp = st.session_state.get('selected_gm_val', display_gms[default_idx])
    my_team_df_preview = master_df[master_df['GM'] == selected_gm_temp] if not master_df.empty else pd.DataFrame()
    
    gm_specific_roast = get_team_roast(selected_gm_temp, my_team_df_preview, DAILY_HEADLINE)
    st.markdown(f"""
        <div class="roast-container" style="animation: none;">
            <div style="color: #0068c9; font-size: 1rem;">🔥 <b>{gm_specific_roast}</b></div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([2.2, 2.0, 1.2, 1.4, 1.4])
    
    with c1:
        selected_gm = st.selectbox("View Another Team", display_gms, index=default_idx, key="selected_gm_val")
    with c2:
        time_options = {'All Time': 0, 'Yesterday': 1, 'Last 48 Hours': 2, 'Last 7 Days': 7, 'Last 14 Days': 14, 'Last 30 Days': 30}
        stat_filter = st.selectbox("Stats", list(time_options.keys()))
        
    my_team = master_df[master_df['GM'] == selected_gm].copy() if not master_df.empty else pd.DataFrame()
    
    with c3:
        pts_today = 0
        if not my_team.empty:
            active_pids = my_team[my_team['Team_Raw'].isin(TEAMS_PLAYING_TODAY)]['Player_Id'].dropna().tolist()
            if active_pids:
                today_data = get_historical_points(active_pids, 0)
                pts_today = sum(today_data.values())
        st.metric("Points Today", pts_today)
        
    with c4:
        active_count = my_team[my_team['Team_Raw'].isin(TEAMS_PLAYING_TODAY) & ~my_team['Team_Raw'].isin(ELIMINATED_TEAMS)].shape[0] if not my_team.empty else 0
        st.metric("Players Active Today", active_count)
        
    with c5:
        alive_count = my_team[~my_team['Team_Raw'].isin(ELIMINATED_TEAMS)].shape[0] if not my_team.empty else 0
        st.metric("Players Remaining", alive_count)

    st.markdown(f"""
        <p style='font-size: 0.85rem; color: #888; margin-bottom: 10px; line-height: 1.6;'>
            ➤ {active_img_html} indicates playing today<br>
            ➤ <span style="text-decoration: line-through;">Strikethrough</span> indicates player is eliminated
        </p>
    """, unsafe_allow_html=True)
    
    if not my_team.empty:
        days = time_options[stat_filter]
        if days > 0:
            hist_data = get_historical_points(my_team['Player_Id'].tolist(), days)
            my_team['Points'] = my_team['Player_Id'].map(hist_data).fillna(0).astype(int)
            my_team['G'] = "-" 
            my_team['A'] = "-"
            my_team['P/PG'] = "-"
            my_team['Top Pick/Rnd'] = "-"
        
        st.markdown(generate_team_html(my_team), unsafe_allow_html=True)

elif nav == "All Rosters":
    st.markdown(f"""
        <p style='font-size: 0.85rem; color: #888; margin-bottom: 10px; line-height: 1.6;'>
            ➤ {active_img_html} indicates playing today<br>
            ➤ <span style="text-decoration: line-through;">Strikethrough</span> indicates player is eliminated
        </p>
    """, unsafe_allow_html=True)
    
    if not master_df.empty:
        for gm in display_gms:
            st.markdown(f"<h3 style='color: #0068c9; margin-top: 20px;'>{gm}</h3>", unsafe_allow_html=True)
            gm_team = master_df[master_df['GM'] == gm].copy()
            st.markdown(generate_team_html(gm_team), unsafe_allow_html=True)
