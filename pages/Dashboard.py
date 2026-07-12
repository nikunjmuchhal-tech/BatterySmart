import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(page_title="Battery Smart - Manager Dashboard", layout="wide")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_TAB = "Call Logs"

STATUS_OPTIONS = ["Pending", "Connected", "Not Connected", "Incoming Not Available", "FollowUp Scheduled"]

st.markdown("<style>h1 { font-size: 2.4rem !important; } .metric-box { background:#1e293b; border-radius:12px; padding:20px; text-align:center; } .metric-num { font-size:2.2rem; font-weight:800; } .metric-label { font-size:0.9rem; color:#94a3b8; text-transform:uppercase; }</style>", unsafe_allow_html=True)


def check_password():
    def password_entered():
        if st.session_state["dash_password"] == st.secrets["app_password"]:
            st.session_state["dash_authenticated"] = True
            del st.session_state["dash_password"]
        else:
            st.session_state["dash_authenticated"] = False

    if st.session_state.get("dash_authenticated"):
        return True

    st.text_input("Password", type="password", on_change=password_entered, key="dash_password")
    if "dash_authenticated" in st.session_state and not st.session_state["dash_authenticated"]:
        st.error("Incorrect password")
    return False


@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
    return spreadsheet.worksheet(SHEET_TAB)


@st.cache_data(ttl=30)
def load_data(_sheet):
    records = _sheet.get_all_records()
    return pd.DataFrame(records)


def parse_date(val):
    if not val:
        return None
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except Exception:
        return None


def today_ist():
    return datetime.now(IST).date()


def compute_stage_stats(df, date_col, status_col):
    today = today_ist()
    counts = {opt: 0 for opt in STATUS_OPTIONS}
    total = 0

    for i, row in df.iterrows():
        d = parse_date(row.get(date_col))
        if d == today:
            total += 1
            status = row.get(status_col, "Pending") or "Pending"
            if status not in counts:
                counts[status] = 0
            counts[status] += 1

    return total, counts


def render_metric(label, value):
    html = "<div class='metric-box'><div class='metric-num'>" + str(value) + "</div><div class='metric-label'>" + label + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_stage_section(stage_name, total, counts):
    st.subheader(stage_name)

    connected = counts.get("Connected", 0)
    pending = counts.get("Pending", 0)
    not_connected = counts.get("Not Connected", 0)
    incoming_na = counts.get("Incoming Not Available", 0)
    followup = counts.get("FollowUp Scheduled", 0)
    attempted = total - pending

    cols = st.columns(6)
    with cols[0]:
        render_metric("Total Due", total)
    with cols[1]:
        render_metric("Attempted", attempted)
    with cols[2]:
        render_metric("Connected", connected)
    with cols[3]:
        render_metric("Not Connected", not_connected)
    with cols[4]:
        render_metric("No Incoming", incoming_na)
    with cols[5]:
        render_metric("Follow-up", followup)

    if total > 0:
        progress = attempted / total
    else:
        progress = 0

    st.progress(progress, text=str(attempted) + " / " + str(total) + " attempted today")

    if pending == 0 and total > 0:
        st.success(stage_name + " is fully done for today! 🎉")
    elif total > 0:
        st.warning(str(pending) + " driver(s) still pending for " + stage_name)


def main():
    st.title("📊 Battery Smart — Manager Dashboard")
    st.caption("Live view of today's D+1 / D+2 calling progress")
    st.page_link("app.py", label="📞 Back to Agent Calls", icon="📞")

    if not check_password():
        return

    sheet = get_sheet()
    df = load_data(sheet)

    d1_total, d1_counts = compute_stage_stats(df, "D_1_Date", "D_1 Status")
    d2_total, d2_counts = compute_stage_stats(df, "D_2_Date", "D_2_Status")

    render_stage_section("D+1 Calls", d1_total, d1_counts)
    st.divider()
    render_stage_section("D+2 Calls", d2_total, d2_counts)

    st.divider()
    if st.button("🔄 Refresh Now"):
        load_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
