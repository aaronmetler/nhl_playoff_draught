import streamlit as st
import pandas as pd
import requests
import datetime
import base64
import extra_streamlit_components as stx
import os

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool", page_icon="🏒")

# --- CUSTOM CSS: EXTREME PADDING REDUCTION ---
# This CSS pulls the entire app up to the very top edge of the browser
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
        }
        /* Reduce space below the header */
        hr {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager()

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
            email = st.text_input("Email").lower().strip()
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            if submit:
                if email in USER_DB and pwd == SHARED_PWD:
                    cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    st.session_state.authenticated = True
                    st.session_state.gm_name = USER_DB[email]
                    st.session_state.display_name = USER_DB[email]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- 3. MAIN APP HEADER (ULTRA COMPACT WITH LOGO) ---
# Added a new tiny column (t_logo) at the far left for your uploaded image
t_logo, t_title, t_text, t_img, t_menu = st.columns([0.6, 4.9, 3.5, 0.5, 0.5])

with t_logo:
    # Checks if you uploaded logo.png to GitHub, and displays it if you did
    if os.path.exists("logo.png"):
        st.image("logo.png", width=55)
        
with t_title: 
    # Adjusted margins to align perfectly with the new logo
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
    nav = st.segmented_control("Navigation", ["League", "My Team"], default="League", label_visibility="collapsed")
except AttributeError:
    nav = st.radio("Navigation", ["League", "My Team"], horizontal=True, label_visibility="collapsed")

if nav is None: nav = "League"

# --- 5. DATA FETCHING & LOGIC ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    stats_url = "https://api-web.nhle.com/v1/skater-stats-now"
    try:
        resp = requests.get(stats_url, params={"season": "20252026", "gameTypeId": 3})
        if resp.status_code == 200:
            df = pd.DataFrame(resp.json().get('data', []))
            if not df.empty:
                df['totalPoints'] = df['goals'] + df['assists']
                return df
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_eliminated_teams():
    eliminated = set()
    try:
        res = requests.get("https://api-web.nhle.com/v1/playoff-bracket/2026")
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

def clean_and_match(player_str, stats_df):
    if pd.isna(player_str) or str(player_str).strip() == '': return None
    clean_p = str(player_str).replace('-', ' ').lower()
    team_map = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL', 'WAS': 'WSH'}
    parts = clean_p.split()
    t_part = team_map.get(parts[-1].upper(), parts[-1].upper())
    n_part = parts[0].replace('ü', 'u')
    if "." in n_part: n_part = parts[1] if len(parts) > 1 else n_part
    if stats_df.empty:
        return {'lastName': str(player_str).split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part}
    match = stats_df[(stats_df['lastName'].str.lower().str.contains(n_part)) & (stats_df['teamAbbrev'] == t_part)]
    if not match.empty: return match.iloc[0].to_dict()
    return {'lastName': str(player_str).split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0, 'teamAbbrev': t_part}

stats = fetch_live_data()
ELIMINATED_TEAMS = get_eliminated_teams()

try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv")
    if 'Draft Rounds' not in df_raw.columns: df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [c for c in df_raw.columns if c in USER_DB.values()]
except:
    st.error("Missing or invalid CSV file.")
    st.stop()

master_list = []
for index, row in df_raw.iterrows():
    round_name = str(row.get('Draft Rounds', ''))
    if "Round" not in round_name: continue
    for gm in gms:
        pick_str = row.get(gm, '')
        p_data = clean_and_match(pick_str, stats)
        if p_data is None: continue
        master_list.append({
            'GM': gm, 'Player': p_data['lastName'], 'Team': p_data.get('teamAbbrev', ''),
            'Pts': p_data.get('totalPoints', 0), 'G': p_data.get('goals', 0), 
            'A': p_data.get('assists', 0), 'GP': p_data.get('gamesPlayed', 0), 'Round': round_name
        })
master_df = pd.DataFrame(master_list)

# --- APPLY DISPLAY NAME GLOBALLY ---
if st.session_state.display_name and st.session_state.display_name != st.session_state.gm_name:
    master_df['GM'] = master_df['GM'].replace(st.session_state.gm_name, st.session_state.display_name)
    display_gms = [st.session_state.display_name if g == st.session_state.gm_name else g for g in gms]
else:
    display_gms = gms

# --- AVATAR CONVERTER ---
def get_avatar_uri(gm_check_name):
    if gm_check_name == st.session_state.display_name and st.session_state.avatar:
        b64 = base64.b64encode(st.session_state.avatar).decode()
        return f"data:image/png;base64,{b64}"
    default_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#a0aec0"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
    b64_svg = base64.b64encode(default_svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64_svg}"

# --- 6. UI VIEWS ---
if nav == "League":
    if not master_df.empty:
        lb = master_df.groupby('GM').agg({'GP': 'sum', 'Pts': 'sum', 'G': 'sum', 'A': 'sum'}).reset_index()
        
        active_mask = ~master_df['Team'].isin(ELIMINATED_TEAMS)
        active_counts = master_df[active_mask].groupby('GM').size().reset_index(name='Players Remaining')
        lb = pd.merge(lb, active_counts, on='GM', how='left').fillna(0)
        lb['Players Remaining'] = lb['Players Remaining'].astype(int)
        
        lb = lb.sort_values(by=['Pts', 'G'], ascending=False).reset_index(drop=True)
        lb['Rank'] = (lb.index + 1).astype(str) 
        
        max_pts = lb['Pts'].max() if not lb.empty else 0
        lb['Pts Back'] = max_pts - lb['Pts']
        
        def add_trophy(row):
            if row['Rank'] == '1': return f"🏆 {row['GM']}"
            elif row['Rank'] == '2': return f"🥈 {row['GM']}"
            return row['GM']
            
        lb['Name'] = lb.apply(add_trophy, axis=1)
        
        lb['Pts Yesterday'] = 0  
        lb[''] = lb['GM'].apply(get_avatar_uri) 
        lb = lb.rename(columns={'Pts': 'Points'})
        
        lb_final = lb[['Rank', '', 'Name', 'GP', 'Points', 'G', 'A', 'Pts Yesterday', 'Pts Back', 'Players Remaining']]
        
        st.dataframe(
            lb_final, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Rank": st.column_config.TextColumn("Rank", width="small"),
                "": st.column_config.ImageColumn(" ", help="Avatar", width="small")
            }
        )

else:
    default_idx = display_gms.index(st.session_state.display_name) if st.session_state.display_name in display_gms else 0
    selected_gm = st.selectbox("View Another Team", display_gms, index=default_idx)
    
    # Updated Legend with Arrows and Line Break
    st.markdown("""
        <p style='font-size: 0.85rem; color: #888; margin-bottom: 10px;'>
            ➤ <b>Bold</b> indicates playing today<br>
            ➤ <i>Red Strikethrough</i> indicates eliminated
        </p>
    """, unsafe_allow_html=True)
    
    if not master_df.empty:
        my_team = master_df[master_df['GM'] == selected_gm].copy()
        
        def style_eliminated(row):
            if row['Team'] in ELIMINATED_TEAMS: 
                return ['background-color: #e6f0fa; color: #0068c9; text-decoration: line-through;'] * len(row)
            return [''] * len(row)
            
        styled_team = my_team[['Round', 'Player', 'Team', 'GP', 'G', 'A', 'Pts']].style.apply(style_eliminated, axis=1)
        st.dataframe(styled_team, hide_index=True, use_container_width=True)
