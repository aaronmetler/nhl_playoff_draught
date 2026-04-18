import streamlit as st
import pandas as pd
import requests
import random
import datetime
import plotly.express as px
import re

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Metler 2026 Playoff Tracker", page_icon="🏒")

# --- 2. SARCASM & JOKE ENGINES ---
def get_daily_joke(category):
    seed = int(datetime.datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    leafs = [
        "The Leafs have officially spent more on playoff beard oil than they have on 2nd round travel expenses.",
        "Breaking: Toronto pre-emptively cancels the 2026 parade to save on stationery costs.",
        "The Leafs' playoff run is like a TikTok video: short, loud, and ends before you can actually enjoy it.",
        "Science update: The shortest unit of time is no longer the nanosecond; it's a Leafs lead in Game 7."
    ]
    team = [
        "Your roster is currently providing the same offensive threat as a wet paper towel.",
        "I've seen more 'drive' in a retirement home parking lot than in your Round 3 picks.",
        "Congratulations! Your team is currently the #1 reason why 'Total Points' isn't a high-score contest.",
        "If your GMs were scouts, you'd all be looking for jobs in the KHL by Monday."
    ]
    return random.choice(leafs if category == "leafs" else team)

# --- 3. DATA FETCHING (NHL API) ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    # 2025-2026 Playoff Skater Stats (gameTypeId=3)
    stats_url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3}
    try:
        resp = requests.get(stats_url, params=params)
        if resp.status_code == 200:
            stats_data = resp.json().get('data', [])
            stats_df = pd.DataFrame(stats_data)
            if not stats_df.empty:
                stats_df['totalPoints'] = stats_df['goals'] + stats_df['assists']
        else:
            stats_df = pd.DataFrame()
    except:
        stats_df = pd.DataFrame()
    
    # Live Scores (To bold players active today)
    scores_url = "https://api-web.nhle.com/v1/score/now"
    try:
        scores = requests.get(scores_url).json()
        active_teams = [g['homeTeam']['abbrev'] for g in scores.get('games', [])] + \
                       [g['awayTeam']['abbrev'] for g in scores.get('games', [])]
    except:
        active_teams = []
        
    return stats_df, active_teams

# --- 4. NORMALIZATION ENGINE ---
def clean_and_match(player_str, stats_df):
    if pd.isna(player_str) or str(player_str).strip() == '': return None
    if stats_df.empty: return None

    # Handle formats like "McDavid - EDM", "L. Carlsson - ANA", or "Raddysh-Tb"
    player_str = str(player_str).replace('-', ' ')
    parts = player_str.split()
    
    # Team is usually the last part
    team_part = parts[-1].upper()
    team_map = {'TB': 'TBL', 'MON': 'MTL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'WAS': 'WSH'}
    team_part = team_map.get(team_part, team_part)
    
    # Name is the rest
    name_part = parts[0].lower().replace('ü', 'u')
    if "." in name_part: # Handles "L. Carlsson" -> "Carlsson"
        name_part = parts[1].lower() if len(parts) > 2 else name_part

    # Filter API data
    match = stats_df[(stats_df['lastName'].str.lower().str.contains(name_part)) & 
                     (stats_df['teamAbbrev'] == team_part)]
    
    return match.iloc[0] if not match.empty else None

# --- 5. APP EXECUTION ---
stats, active_today = fetch_live_data()

# Load Draft Data (skiprows=1 fixes the header offset in your CSV)
try:
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [col for col in df_raw.columns if col not in ['Draft Rounds', 'Rules'] and not str(col).startswith('Unnamed')]
except:
    st.error("Missing CSV: Ensure '2026 NHL Draught - Sheet1.csv' is uploaded to your GitHub.")
    st.stop()

# Build Master Data
master_list = []
for index, row in df_raw.iterrows():
    round_label = str(row.get('Draft Rounds', ''))
    if "Round" not in round_label: continue
    round_num = int(re.search(r'\d+', round_label).group())
    
    for gm in gms:
        pick_str = row[gm]
        matched = clean_and_match(pick_str, stats)
        if matched is not None:
            master_list.append({
                'GM': gm, 'Round': round_num, 'Player': matched['lastName'], 'Team': matched['teamAbbrev'],
                'GP': matched['gamesPlayed'], 'G': matched['goals'], 'A': matched['assists'],
                'Pts': matched['totalPoints'], 'ID': matched['playerId']
            })

master_df = pd.DataFrame(master_list)
if not master_df.empty:
    master_df['Rnd Rank'] = master_df.groupby('Round')['Pts'].rank(ascending=False, method='min').astype(int)

# --- 6. NAVIGATION ---
tab_league, tab_team = st.tabs(["🏆 League View", "🏒 Team View"])

with tab_league:
    st.title("The Leaderboard")
    st.info(f"**Leafs Daily Report:** {get_daily_joke('leafs')}")
    
    if not master_df.empty:
        leaders = master_df.groupby('GM').agg({'Pts': 'sum', 'G': 'sum', 'Player': 'count'}).reset_index()
        leaders = leaders.sort_values(by=['Pts', 'G'], ascending=False).reset_index(drop=True)
        leaders['Rank'] = leaders.index + 1
        st.dataframe(leaders[['Rank', 'GM', 'Pts', 'G', 'Player']].rename(columns={'Player': 'Active'}), use_container_width=True)
    else:
        st.warning("Stats aren't live yet. Check back once the first puck drops!")

with tab_team:
    selected_gm = st.selectbox("Select GM", gms)
    st.subheader(f"Team: {selected_gm}")
    st.warning(f"**Management Critique:** {get_daily_joke('team')}")
    st.caption("*Note: **Bolded** names indicate a game today. Click 'Doc' for News.*")

    if not master_df.empty:
        my_team = master_df[master_df['GM'] == selected_gm].copy()
        
        # Format the table with Links
        def format_row(r):
            name = f"**{r['Player']}**" if r['Team'] in active_today else r['Player']
            news_url = f"https://www.nhl.com/player/{r['ID']}?stats=gamelog"
            bio_url = f"https://www.nhl.com/player/{r['ID']}"
            return pd.Series([
                f'<a href="{news_url}">📄</a>',
                f'<a href="{bio_url}">{name}</a>',
                r['Team'], r['Round'], r['Rnd Rank'], r['GP'], r['G'], r['A'], r['Pts']
            ])

        team_display = my_team.apply(format_row, axis=1)
        team_display.columns = ['News', 'Player', 'Team', 'Rnd', 'Rnd Rank', 'GP', 'G', 'A', 'Total Pts']
        st.write(team_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # Performance Graph
        avg = master_df.groupby('GM')['Pts'].sum().mean()
        fig = px.bar(x=["Your Team", "League Avg"], y=[my_team['Pts'].sum(), avg], title="Performance vs. League Average")
        st.plotly_chart(fig)
