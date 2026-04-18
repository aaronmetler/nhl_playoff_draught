import streamlit as st
import pandas as pd
import requests
import random
import datetime
import extra_streamlit_components as stx

# --- 1. CONFIG & SESSION INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Metler 2026 Playoff Tracker")

# Initialize Cookie Manager directly (Fixes CachedWidgetWarning)
cookie_manager = stx.CookieManager()

# Ensure session state exists
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.gm_name = None
    st.session_state.avatar = None

# --- 2. AUTHENTICATION LOGIC ---
USER_DB = {
    "mike.mastromattei@gmail.com": "Mike",
    "rhys.metler@gmail.com": "Rhys",
    "greg.metler@yahoo.com": "Big M",
    "peterwilliamhammond@gmail.com": "Pete",
    "ryan.torrie@gmail.com": "Torrie",
    "cochrane.jason@gmail.com": "Jay",
    "mattjames.duncan@gmail.com": "Duncs",
    "gtraks@gmail.com": "Trakas",
    "pgardner355@gmail.com": "Gardner",
    "aaronmetler@gmail.com": "Aaron"
}
SHARED_PWD = "playoffs2026"

def login_flow():
    # Attempt to read the cookie
    saved_email = cookie_manager.get('user_email_cookie')
    
    # Check if the cookie exists and is valid
    if saved_email in USER_DB:
        st.session_state.authenticated = True
        st.session_state.gm_name = USER_DB[saved_email]
        return True

    st.title("🏒 Playoff Pool Login")
    with st.form("login"):
        email = st.text_input("Email").lower().strip()
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            if email in USER_DB and pwd == SHARED_PWD:
                # Set cookie and force rerun
                cookie_manager.set('user_email_cookie', email, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                st.session_state.authenticated = True
                st.session_state.gm_name = USER_DB[email]
                st.rerun()
            else:
                st.error("Invalid credentials.")
    return False

# Stop execution if not logged in
if not login_flow():
    st.stop()
