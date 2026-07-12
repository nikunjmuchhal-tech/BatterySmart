import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
def today_ist():
    return datetime.now(IST).date()
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Battery Smart - Onboarding Calls", layout="wide", initial_sidebar_state="expanded")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_TAB = "Call Logs"

D1_SCRIPT = "Hello {name}, welcome to Battery Smart! This is a courtesy call to confirm you're settling in well. Any questions about onboarding, your plan, or the app?"
D2_SCRIPT = "Hello {name}, following up — how has your experience been? Started using the vehicle regularly? Any issues with the battery or swap process?"

STATUS_OPTIONS = ["Pending", "Connected", "Not Connected", "Incoming Not Available", "FollowUp Scheduled"]
DFE_OPTIONS = ["Not Checked", "Yes", "No"]

STATUS_DOT = {
    "Pending": "⚪",
    "Connected": "🟢",
    "Not Connected": "🟡",
    "Incoming Not Available": "🔴",
    "FollowUp Scheduled": "🔵",
}

BRAND_GREEN = "#00C389"
BRAND_NAVY = "#151272"

st.markdown(
    "<style>"
    "[data-testid='stAppViewContainer'] { background: linear-gradient(160deg, #f0fffa 0%, #ffffff 30%, #f1f2ff 100%); }"
    "[data-testid='stHeader'] { background: rgba(0,0,0,0); }"
    "[data-testid='stSidebar'] { background: linear-gradient(180deg, " + BRAND_NAVY + " 0%, #23197a 100%); }"
    "[data-testid='stSidebar'] * { color: #ffffff !important; }"
    "[data-testid='stSidebar'] .stRadio label { font-size: 1.05rem !important; }"
    "h1 { font-size: 2.1rem !important; color:" + BRAND_NAVY + " !important; font-weight: 800 !important; }"
    "h1 span.logo-badge { background:" + BRAND_GREEN + "; padding: 4px 10px; border-radius: 8px; font-size:1.3rem; margin-right:10px; }"
    ".stTabs [data-baseweb='tab'] { font-size: 1.05rem !important; padding: 8px 16px !important; }"
    ".stTabs [data-baseweb='tab-list'] { gap: 6px; }"
    ".stTabs [aria-selected='true'] { color: " + BRAND_GREEN + " !important; }"
    "div[data-testid='stMarkdownContainer'] p { font-size: 1.0rem; }"
    ".detail-name { font-size: 1.4rem; font-weight: 700; margin-bottom: 2px; color:" + BRAND_NAVY + "; }"
    ".detail-sub { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }"
    ".detail-label { font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }"
    ".detail-value { font-size: 1.0rem;
