import streamlit as st
import pandas as pd
import requests
import random
import datetime
import plotly.express as px
import re

# --- PAGE SETUP ---
st.set_page_config(layout="wide", page_title="Metler 2026 Playoff Tracker")

# --- SARCASM ENGINES ---
def get_joke(category):
    seed = int(datetime.datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    leafs = [
        "The Leafs have officially spent more on playoff beard oil than they have on 2nd round travel expenses.",
        "Breaking: Toronto pre-emptively cancels the 2026 parade to save on stationery costs.",
        "The shortest unit of time is no longer the nanosecond; it's a Leafs lead in Game 7."
    ]
    team = [
        "Your roster is currently providing the same offensive threat as a wet paper towel.",
        "I've seen more 'drive' in a retirement home parking lot than in your Round 3 picks."
    ]
    return random.choice(leafs if category == "leafs" else team)

# --- API DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_live_data():
    # 2025-2026 Playoff Skater Stats
    stats_url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3}
    try:
        resp = requests.get(stats_url, params=params)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            stats_df = pd.DataFrame(data)
            if not stats_df.empty:
                stats_df['totalPoints'] = stats_df['goals'] + stats_df['assists']
                return stats_df, []
    except:
        pass
    return pd.DataFrame(), []

# --- NAME MATCHING ---
def clean_and_match(player_str, stats_df):
    if pd.isna(player_str) or str(player_str).strip() == '': return None
    # Basic cleaning
    clean_p = str(player_str).replace('-', ' ').lower()
    # Team Mapping
    team_map = {'TB': 'TBL', 'VEGAS': 'VGK', 'VGS': 'VGK', 'MON': 'MTL'}
    
    # If stats_df is empty, we return a shell for the player
    if stats_df.empty:
        return {'lastName': player_str.split('-')[0].strip(), 'totalPoints': 0, 'goals': 0, 'assists': 0, 'gamesPlayed': 0}

    # Filtering logic...
    parts = clean_p.split()
    name_part = parts[0]
    match = stats_df[stats_df['lastName'].str.lower().str.contains(name_part)]
    return match.iloc[0].to_dict() if not match.empty else None

# --- LOAD CSV & INITIALIZE ---
try:
    # Use skiprows=1 to fix the header alignment from your CSV
    df_raw = pd.read_csv("2026 NHL Draught - Sheet1.csv", skiprows=1)
    gms = [col for col in df_raw.columns if col not in ['Draft Rounds', 'Rules'] and not str(col).startswith('Unnamed')]
except:
    st.error("CSV '2026 NHL Draught - Sheet1.csv' not found.")
    st.stop()

stats, active_today = fetch_live_data()

# Build the master list even if stats are 0
master_list = []
for index, row in df_raw.iterrows():
    round_name = str(row.get('Draft Rounds', ''))
    if "Round" not in round_name: continue
    
    for gm in gms:
        pick_str = row[gm]
        p_data = clean_and_match(pick_str, stats)
        
        # If API is empty, manually assign 0s so the league view works
        if stats.empty or p_data is None:
            master_list.append({
                'GM': gm, 'Player': pick_str, 'Pts': 0, 'G': 0, 'A': 0, 'GP': 0, 'Round': round_name
            })
        else:
            master_list.append({
                'GM': gm, 'Player': p_data['lastName'], 'Pts': p_data['totalPoints'], 
                'G': p_data['goals'], 'A': p_data['assists'], 'GP': p_data['gamesPlayed'], 'Round': round_name
            })

master_df = pd.DataFrame(master_list)

# --- VIEWS ---
tab_league, tab_team = st.tabs(["🏆 League View", "🏒 Team View"])

with tab_league:
    st.title("League Standings")
    st.info(f"**Daily Leafs Jab:** {get_joke('leafs')}")
    
    # Aggregate data for the leaderboard
    leaderboard = master_df.groupby('GM').agg({'Pts': 'sum', 'G': 'sum', 'GP': 'sum'}).reset_index()
    leaderboard = leaderboard.sort_values(by=['Pts', 'G'], ascending=False).reset_index(drop=True)
    leaderboard.index += 1 # Ranking
    
    st.dataframe(leaderboard, use_container_width=True)

with tab_team:
    selected_gm = st.selectbox("Select GM", gms)
    st.subheader(f"{selected_gm}'s Roster")
    st.warning(f"**Management Note:** {get_joke('team')}")
    
    my_team = master_df[master_df['GM'] == selected_gm]
    st.table(my_team[['Round', 'Player', 'GP', 'G', 'A', 'Pts']])
