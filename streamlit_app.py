import streamlit as st
import pandas as pd
import requests
import datetime
import random
import re

# --- CONFIG & STYLING ---
st.set_page_config(layout="wide", page_title="Metler Playoff Pool")
st.markdown("""<style>.eliminated { text-decoration: line-through; background-color: #ffcccc; opacity: 0.6; }</style>""", unsafe_allow_html=True)

# --- HUMOR ENGINES ---
def get_leafs_joke():
    jokes = [
        "The Leafs have officially won as many 2nd round games this year as your grandmother.",
        "Scientists found a new element: Leafium. It's stable until April, then it completely collapses.",
        "Why does the Maple Leafs' goalie use a pager? Because he can't handle a 'ring'."
    ]
    return random.choice(jokes)

def get_team_insult(points):
    insults = [
        f"With {points} points, this team is moving slower than a Zamboni on a coffee break.",
        "I've seen more offensive pressure from a peewee team with one skate on.",
        "This roster is so deep in the basement they're finding buried treasure."
    ]
    return random.choice(insults)

# --- DATA FETCHING (NHL API) ---
@st.cache_data(ttl=3600)
def get_playoff_stats():
    # Official NHL API for current playoff skaters
    url = "https://api-web.nhle.com/v1/skater-stats-now"
    params = {"season": "20252026", "gameTypeId": 3} # 3 is Playoff code
    data = requests.get(url, params=params).json()['data']
    df = pd.DataFrame(data)
    df['totalPoints'] = df['goals'] + df['assists']
    return df

def get_active_teams():
    # Checks who plays today
    url = "https://api-web.nhle.com/v1/score/now"
    games = requests.get(url).json().get('games', [])
    active = []
    for g in games:
        active.append(g['homeTeam']['abbrev'])
        active.append(g['awayTeam']['abbrev'])
    return active

# --- NORMALIZATION LOGIC ---
def parse_pick(pick_str, stats_df):
    # Cleans "McDavid - EDM" or "L. Carlsson - ANA"
    try:
        clean_name = re.split('-|\s', pick_str.strip())[0].lower()
        team_abbr = pick_str.split('-')[-1].strip().upper().replace("TB", "TBL").replace("VEGAS", "VGK")
        
        # Match against API data
        match = stats_df[(stats_df['lastName'].str.lower().str.contains(clean_name)) & 
                         (stats_df['teamAbbrev'] == team_abbr)]
        return match.iloc[0] if not match.empty else None
    except:
        return None

# --- APP UI ---
stats_df, active_today = get_playoff_stats(), get_active_teams()

# Sidebar: Manage Team Identity
st.sidebar.header("Team Management")
custom_name = st.sidebar.text_input("Change Team Name", "My Team")
custom_icon = st.sidebar.selectbox("Choose Icon", ["🏒", "🏆", "🔥", "🧊"])

view = st.sidebar.radio("Navigation", ["League View", "Team View"])

# --- VIEW: LEAGUE ---
if view == "League View":
    st.title(f"{custom_icon} The Leaderboard")
    st.info(f"**Daily Leafs Fact:** {get_leafs_joke()}")
    
    # Logic to aggregate GM scores from your CSV (mockup here)
    # leaderboard = process_csv_scores() 
    st.write("Aggregated league standings sorted by Total Points (Tie-break: Goals).")

# --- VIEW: TEAM ---
else:
    st.title(f"{custom_icon} {custom_name}")
    st.write(f"*{get_team_insult(10)}*")
    st.caption("*Italicized & Bold names are playing today (ET).*")
    
    # Metric Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Playing Today", "4")
    col2.metric("Players Remaining", "12/14")
    col3.metric("League Rank", "#2")

    # Table with all required columns
    # st.dataframe(processed_team_df) # Including Rank within Round and doc links
