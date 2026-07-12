import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
def today_ist():
    return datetime.now(IST).date()
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Battery Smart - Onboarding Calls", layout="wide")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_TAB = "Call Logs"

D1_SCRIPT = "Hello {name}, welcome to Battery Smart! This is a courtesy call to confirm you're settling in well. Any questions about onboarding, your plan, or the app?"
D2_SCRIPT = "Hello {name}, following up — how has your experience been? Started using the vehicle regularly? Any issues with the battery or swap process?"

STATUS_OPTIONS = ["Pending", "Connected", "Not Connected", "Incoming Not Available", "FollowUp Scheduled"]

STATUS_COLOR = {
    "Pending": "#6b7280",
    "Connected": "#16a34a",
    "Not Connected": "#eab308",
    "Incoming Not Available": "#dc2626",
    "FollowUp Scheduled": "#2563eb",
}

st.markdown("""
<style>
h1 { font-size: 2.4rem !important; }
.stTabs [data-baseweb="tab"] { font-size: 1.2rem !important; padding: 10px 18px !important; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
div[data-testid="stMarkdownContainer"] p { font-size: 1.05rem; }
.detail-name { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
.detail-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.detail-value { font-size: 1.15rem; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)


def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated"):
        return True

    st.text_input("Password", type="password", on_change=password_entered, key="password")
    if "authenticated" in st.session_state and not st.session_state["authenticated"]:
        st.error("Incorrect password")
    return False


@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
    return spreadsheet.worksheet(SHEET_TAB)


def load_data(sheet):
    records = sheet.get_all_records()
    return pd.DataFrame(records)


def parse_date(val):
    if not val:
        return None
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except Exception:
        return None


def build_lists(df):
    today = today_ist()
    d1_list = []
    d2_list = []

    for i, row in df.iterrows():
        sheet_row = i + 2

        d1_date = parse_date(row.get("D_1_Date"))
        d2_date = parse_date(row.get("D_2_Date"))
        d1_status = row.get("D_1 Status", "Pending") or "Pending"
        d2_status = row.get("D_2_Status", "Pending") or "Pending"

        base = {}
        base["sheet_row"] = sheet_row
        base["driver_id"] = row.get("Driver_ID")
        base["driver_name"] = row.get("Driver_Name")
        base["contact_number"] = row.get("Contact_Number")
        base["zone"] = row.get("Zone")
        base["onboarding_date"] = row.get("Onboarding_Date")
        base["dealership"] = row.get("Dealership")
        base["vehicle_model"] = row.get("Vehicle_Model")
        base["total_signup_amount"] = row.get("Total_Signup_Amount")
        base["amount_paid"] = row.get("Amount_Paid")
        base["plan_amount"] = row.get("Plan_Amount")

        if d1_date == today:
            item = dict(base)
            item["stage"] = "D+1"
            item["due_date"] = d1_date
            item["status_col"] = "D_1 Status"
            item["notes_col"] = "D_1_Notes"
            item["current_status"] = d1_status
            item["current_notes"] = row.get("D_1_Notes", "")
            item["script"] = D1_SCRIPT.format(name=row.get("Driver_Name"))
            d1_list.append(item)

        if d2_date == today:
            item = dict(base)
            item["stage"] = "D+2"
            item["due_date"] = d2_date
            item["status_col"] = "D_2_Status"
            item["notes_col"] = "D_2_Notes"
            item["current_status"] = d2_status
            item["current_notes"] = row.get("D_2_Notes", "")
            item["script"] = D2_SCRIPT.format(name=row.get("Driver_Name"))
            d2_list.append(item)

    return d1_list, d2_list


def save_update(sheet, df, sheet_row, status_col, notes_col, status, notes):
    header = df.columns.tolist()
    status_col_idx = header.index(status_col) + 1
    notes_col_idx = header.index(notes_col) + 1
    sheet.update_cell(sheet_row, status_col_idx, status)
    sheet.update_cell(sheet_row, notes_col_idx, notes)


def render_detail(item, sheet, df, unique_key):
    st.markdown("<div class='detail-name'>" + str(item['driver_name']) + "</div>", unsafe_allow_html=True)
    st.markdown("<div class='detail-label'>Driver ID</div><div class='detail-value'>" + str(item['driver_id']) + "</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='detail-label'>Contact Number</div><div class='detail-value'>" + str(item['contact_number']) + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-label'>Zone</div><div class='detail-value'>" + str(item['zone']) + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-label'>Onboarding Date</div><div class='detail-value'>" + str(item['onboarding_date']) + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-label'>Dealership</div><div class='detail-value'>" + str(item['dealership']) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='detail-label'>Vehicle</div><div class='detail-value'>" + str(item['vehicle_model']) + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-label'>Vehicle Price / Amount Paid</div><div class='detail-value'>Rs " + str(item['total_signup_amount']) + " / Rs " + str(item['amount_paid']) + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='detail-label'>Plan Amount (EMI/Subscription)</div><div class='detail-value'>Rs " + str(item['plan_amount']) + "</div>", unsafe_allow_html=True)

    st.info("**Script:** " + item["script"])

    if item["current_notes"]:
        st.caption("Previous notes: " +
