import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
def today_ist():
    return datetime.now(IST).date()
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Battery Smart - Onboarding Calls", layout="wide", initial_sidebar_state="expanded")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CALL_SHEET_TAB = "Call Logs"
DOCS_SHEET_TAB = "Docs Tracker"

CALL_SCRIPT = "Hello {name}, welcome to Battery Smart! This is a courtesy call to confirm you're settling in well. Any questions about onboarding, your plan, or the app?"
DOCS_SCRIPT = "Hello {name}, this is Battery Smart calling regarding your vehicle documents. Have you received your RC and other vehicle documents yet?"

CALL_STATUS_OPTIONS = ["Pending", "Call Completed", "Escalated to DOM", "Follow-up Needed"]
DOCS_STATUS_OPTIONS = ["Pending", "Documents Received", "Escalated to DOM"]
DFE_OPTIONS = ["Not Checked", "Yes", "No"]

STATUS_DOT = {
    "Pending": "⚪",
    "Call Completed": "🟢",
    "Escalated to DOM": "🔴",
    "Follow-up Needed": "🔵",
    "Documents Received": "🟢",
}

BRAND_GREEN = "#00C389"
BRAND_NAVY = "#151272"

LOGO_SVG = "<svg width='46' height='46' viewBox='0 0 300 470' style='vertical-align:middle; margin-right:12px;'><rect x='95' y='0' width='110' height='45' rx='8' fill='#00C389'/><path d='M20 65 C5 65 0 80 10 92 L140 240 L10 388 C0 400 5 415 20 415 L280 415 C295 415 300 400 290 388 L160 240 L290 92 C300 80 295 65 280 65 Z M100 130 L200 130 L150 190 Z M100 350 L200 350 L150 290 Z' fill='#00C389'/></svg>"

METRIC_ICONS = {
    "Total Due": "▣",
    "Completed": "✓",
    "Escalated": "!",
    "Follow-up": "↻",
    "Pending": "◷",
    "Docs Received": "✓",
}

# DOM lookup, derived from the USC-to-DOM assignment log provided.
# Keyed by lowercased USC first name. Update this dict if the mapping changes.
DOM_MAP = {
    "shailendra": "Aman",
    "mohd shadab": "Aman",
    "shadab": "Aman",
    "shail mishra": "Aman",
    "sanjul": "Aman",
    "vinay": "Aman",
    "salman": "Aman",
    "ayush": "Sajid",
    "aojasvi": "Sajid",
    "shyam": "Sajid",
    "shayam nayak": "Sajid",
    "sunil": "Sajid",
    "sorabh": "Sajid",
    "khushi ram": "Sajid",
    "jasdeep": "Sajid",
    "mohd aarif": "Sajid",
    "aarif": "Sajid",
}

CALL_RESULT_OPTIONS = ["Connected", "Not Connected", "Incoming Not Available", "FollowUp Scheduled"]


def get_dom(usc_name):
    if not usc_name:
        return "Unassigned"
    full = str(usc_name).strip().lower()
    full = " ".join(full.split())
    if full in DOM_MAP:
        return DOM_MAP[full]

    words = full.split(" ")

    # Check consecutive two-word combinations (handles "shail mishra", "mohd shadab", etc.)
    for i in range(len(words) - 1):
        pair = words[i] + " " + words[i + 1]
        if pair in DOM_MAP:
            return DOM_MAP[pair]

    # Check each individual word (handles "Mohd Salman" -> "salman", "Sorabh Kumar" -> "sorabh")
    for word in words:
        if word in DOM_MAP:
            return DOM_MAP[word]

    return "Unassigned"


def send_slack_alert(message):
    webhook = st.secrets.get("slack_webhook_url", "")
    if not webhook:
        return False
    try:
        requests.post(webhook, json={"text": message}, timeout=6)
        return True
    except Exception:
        return False


st.markdown(
    "<style>"
    "[data-testid='stAppViewContainer'] { background: linear-gradient(160deg, #f0fffa 0%, #ffffff 30%, #f1f2ff 100%); }"
    "[data-testid='stHeader'] { background: rgba(0,0,0,0); }"
    "[data-testid='stSidebar'] { background: linear-gradient(180deg, " + BRAND_NAVY + " 0%, #23197a 100%); min-width: 300px !important; }"
    "[data-testid='stSidebar'] * { color: #ffffff !important; }"
    "[data-testid='stSidebar'] .block-container { padding-top: 2rem; }"
    "[data-testid='stSidebar'] .stRadio label { font-size: 1.1rem !important; font-weight: 600; padding: 6px 0; }"
    "[data-testid='stSidebar'] .stRadio div[role='radiogroup'] { gap: 10px; }"
    "[data-testid='stSidebar'] div[data-testid='stMarkdownContainer'] p { font-size: 1.05rem !important; }"
    "[data-testid='stSidebar'] hr { border-color: rgba(255,255,255,0.15); margin: 18px 0; }"
    "[data-testid='stSidebar'] div.stButton > button { font-size: 1.0rem !important; padding: 10px 0 !important; }"
    ".sidebar-stat-box { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }"
    ".sidebar-stat-num { font-size: 1.6rem; font-weight: 800; color: " + BRAND_GREEN + "; }"
    ".sidebar-stat-label { font-size: 0.85rem; color: #d7d5ff; text-transform: uppercase; letter-spacing: 0.4px; }"
    "h1 { font-size: 2.3rem !important; color:" + BRAND_NAVY + " !important; font-weight: 800 !important; margin-bottom: 0px !important; }"
    "[data-testid='stCaptionContainer'] p { font-size: 1.05rem !important; color: #6b7280 !important; }"
    ".stTabs [data-baseweb='tab'] { font-size: 1.1rem !important; font-weight: 600; padding: 10px 20px !important; background: white; border-radius: 10px 10px 0 0; }"
    ".stTabs [data-baseweb='tab-list'] { gap: 8px; border-bottom: 2px solid #e5e7eb; }"
    ".stTabs [aria-selected='true'] { color: " + BRAND_GREEN + " !important; border-bottom: 3px solid " + BRAND_GREEN + " !important; }"
    ".detail-name { font-size: 1.4rem; font-weight: 700; margin-bottom: 2px; color:" + BRAND_NAVY + "; }"
    ".detail-sub { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }"
    ".detail-label { font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }"
    ".detail-value { font-size: 1.0rem; margin-bottom: 8px; color: #111827; font-weight: 500; }"
    ".call-link { display:inline-block; background:" + BRAND_GREEN + "; color: #ffffff !important; padding:6px 14px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.95rem; }"
    ".metric-box { background: linear-gradient(135deg, " + BRAND_NAVY + " 0%, #2a2496 100%); border-radius:16px; padding:20px 10px; text-align:center; box-shadow: 0 4px 14px rgba(21,18,114,0.22); border: 1px solid rgba(255,255,255,0.08); }"
    ".metric-num { font-size:2.0rem; font-weight:800; color: white; line-height: 1.1; }"
    ".metric-label { font-size:0.76rem; color:" + BRAND_GREEN + "; text-transform:uppercase; letter-spacing:0.5px; margin-top: 4px; font-weight: 600; }"
    "div.stButton > button[kind='primary'] { background-color: " + BRAND_GREEN + "; border-color: " + BRAND_GREEN + "; font-weight: 600; }"
    "div.stButton > button { border-radius: 10px; font-weight: 500; }"
    "div.stButton > button[kind='secondary'] { border: 1px solid #e5e7eb; background-color: #ffffff !important; color: #111827 !important; }"
    "div.stButton > button[kind='secondary']:hover { border-color: " + BRAND_GREEN + " !important; color: " + BRAND_GREEN + " !important; background-color: #f0fffa !important; }"
    "div.stButton > button[kind='primary'] p { color: #ffffff !important; }"
    "div.stButton > button[kind='secondary'] p { color: #111827 !important; }"
    "[data-testid='stDataFrame'] { border-radius: 12px; overflow: hidden; border: 1px solid #e5e7eb; }"
    ".stProgress > div > div { background-color: " + BRAND_GREEN + " !important; }"
    "[data-testid='stTextInput'] input { background-color: #f9fafb !important; color: #111827 !important; border: 1px solid #d1d5db !important; }"
    "[data-testid='stTextInput'] input::placeholder { color: #9ca3af !important; }"
    "[data-baseweb='select'] > div { background-color: #f9fafb !important; color: #111827 !important; border: 1px solid #d1d5db !important; }"
    "[data-baseweb='select'] input { color: #111827 !important; }"
    "[data-baseweb='select'] span { color: #111827 !important; }"
    "ul[data-testid='stSelectboxVirtualDropdown'] { background-color: #ffffff !important; }"
    "li[role='option'] { color: #111827 !important; background-color: #ffffff !important; }"
    "li[role='option']:hover { background-color: #eafff6 !important; }"
    ".escalation-card { border-left: 4px solid #dc2626; background: #fef2f2; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; color: #111827 !important; }"
    ".escalation-card b { color: #111827 !important; }"
    "html, body { background-color: #f5f9ff !important; }"
    "[data-testid='stMain'] { background: linear-gradient(160deg, #f0fffa 0%, #ffffff 30%, #f1f2ff 100%) !important; }"
    "[data-testid='stVerticalBlockBorderWrapper'] { background-color: #ffffff !important; border-color: #e5e7eb !important; }"
    "[data-testid='stVerticalBlockBorderWrapper'] * { color: inherit; }"
    "div[data-testid='stMarkdownContainer'] p, div[data-testid='stMarkdownContainer'] div { color: #111827; }"
    "[data-testid='stCaptionContainer'] p { color: #6b7280 !important; }"
    "[data-testid='stAlertContainer'] { background-color: #ffffff !important; border: 1px solid #e5e7eb !important; }"
    "[data-testid='stAlertContainer'] p, [data-testid='stAlertContainer'] div { color: #111827 !important; }"
    "[data-testid='stDataFrame'] * { color: #111827 !important; }"
    "[data-testid='stDataFrame'] { background-color: #ffffff !important; }"
    "[data-testid='stHeadingWithActionElements'] h1, [data-testid='stHeadingWithActionElements'] h2, [data-testid='stHeadingWithActionElements'] h3 { color:" + BRAND_NAVY + " !important; }"
    ".detail-name, .detail-value, .detail-label, .detail-sub { color-scheme: light; }"
    "</style>",
    unsafe_allow_html=True,
)


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
def get_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def get_call_sheet():
    client = get_client()
    spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
    return spreadsheet.worksheet(CALL_SHEET_TAB)


@st.cache_resource
def get_docs_sheet():
    client = get_client()
    spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
    return spreadsheet.worksheet(DOCS_SHEET_TAB)


@st.cache_data(ttl=60)
def load_call_data(_sheet):
    return pd.DataFrame(_sheet.get_all_records())


@st.cache_data(ttl=60)
def load_docs_data(_sheet):
    return pd.DataFrame(_sheet.get_all_records())


def parse_date(val):
    if not val:
        return None
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except Exception:
        return None


def fmt_val(val):
    text = str(val).strip() if val is not None else ""
    if text == "" or text.lower() == "nan":
        return "—"
    return text


def fmt_money(val):
    text = str(val).strip() if val is not None else ""
    if text == "" or text.lower() == "nan":
        return "—"
    return "Rs " + text


def build_call_due_list(df):
    today = today_ist()
    due = []
    for i, row in df.iterrows():
        due_date = parse_date(row.get("Call_Due_Date"))
        status = row.get("Call_Status", "Pending") or "Pending"
        if due_date == today and status == "Pending":
            item = {}
            item["sheet_row"] = i + 2
            item["driver_id"] = row.get("Driver_ID")
            item["driver_name"] = row.get("Driver_Name")
            item["contact_number"] = row.get("Contact_Number")
            item["zone"] = row.get("Zone")
            item["onboarding_date"] = row.get("Onboarding_Date")
            item["dealership"] = row.get("Dealership")
            item["vehicle_model"] = row.get("Vehicle_Model")
            item["total_signup_amount"] = row.get("Total_Signup_Amount")
            item["amount_paid"] = row.get("Amount_Paid")
            item["plan_amount"] = row.get("Plan_Amount")
            item["usc_id"] = row.get("USC_ID")
            item["usc_name"] = row.get("USC_Name")
            item["dom"] = get_dom(row.get("USC_Name"))
            item["dfe_status"] = row.get("DFE_Fees_Asked", "Not Checked") or "Not Checked"
            item["dfe_amount"] = row.get("DFE_Fee_Amount", "")
            item["is_followup"] = str(row.get("Is_Followup", "")).strip().upper() in ("TRUE", "1", "YES")
            item["current_notes"] = row.get("Call_Notes", "")
            item["call_result"] = row.get("Call_Outcome_Detail", "")
            item["script"] = CALL_SCRIPT.format(name=row.get("Driver_Name"))
            due.append(item)
    return due


def build_docs_due_list(df):
    today = today_ist()
    due = []
    for i, row in df.iterrows():
        due_date = parse_date(row.get("Docs_Call_Due_Date"))
        status = row.get("Docs_Status", "Pending") or "Pending"
        if due_date == today and status == "Pending":
            item = {}
            item["sheet_row"] = i + 2
            item["driver_id"] = row.get("Driver_ID")
            item["driver_name"] = row.get("Driver_Name")
            item["contact_number"] = row.get("Contact_Number")
            item["zone"] = row.get("Zone")
            item["onboarding_date"] = row.get("Onboarding_Date")
            item["usc_id"] = row.get("USC_ID")
            item["usc_name"] = row.get("USC_Name")
            item["dom"] = get_dom(row.get("USC_Name"))
            item["current_notes"] = row.get("Docs_Notes", "")
            item["script"] = DOCS_SCRIPT.format(name=row.get("Driver_Name"))
            due.append(item)
    return due


def build_escalations(call_df, docs_df):
    escalations = []
    for i, row in call_df.iterrows():
        if str(row.get("Escalation_Status", "")).strip() == "Open":
            escalations.append({
                "source": "Onboarding Call",
                "sheet_row": i + 2,
                "driver_id": row.get("Driver_ID"),
                "driver_name": row.get("Driver_Name"),
                "contact_number": row.get("Contact_Number"),
                "usc_name": row.get("USC_Name"),
                "dom": get_dom(row.get("USC_Name")),
                "notes": row.get("Call_Notes", ""),
                "status_col": "Escalation_Status",
            })
    for i, row in docs_df.iterrows():
        if str(row.get("Escalation_Status", "")).strip() == "Open":
            escalations.append({
                "source": "Docs Tracker",
                "sheet_row": i + 2,
                "driver_id": row.get("Driver_ID"),
                "driver_name": row.get("Driver_Name"),
                "contact_number": row.get("Contact_Number"),
                "usc_name": row.get("USC_Name"),
                "dom": get_dom(row.get("USC_Name")),
                "notes": row.get("Docs_Notes", ""),
                "status_col": "Escalation_Status",
            })
    return escalations


def save_updates(sheet, df, sheet_row, updates):
    header = df.columns.tolist()
    batch = []
    for col_name in updates:
        if col_name not in header:
            continue
        col_idx = header.index(col_name) + 1
        cell_range = gspread.utils.rowcol_to_a1(sheet_row, col_idx)
        batch.append({"range": cell_range, "values": [[updates[col_name]]]})
    if batch:
        sheet.batch_update(batch)


def render_call_detail(item, sheet, df, unique_key):
    detail_box = st.container(border=True)
    with detail_box:
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC: " + fmt_val(item['usc_name']) + " &nbsp;|&nbsp; DOM: " + item['dom'] + "</div>"
        st.markdown(name_html, unsafe_allow_html=True)

        tel_number = str(item['contact_number']).strip()
        if tel_number and tel_number.lower() != "nan":
            call_html = "<a class='call-link' href='tel:" + tel_number + "'>📱 Call " + tel_number + "</a>"
            st.markdown(call_html, unsafe_allow_html=True)
        else:
            st.warning("No contact number on file for this driver.")
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            zone_html = "<div class='detail-label'>Zone</div><div class='detail-value'>" + fmt_val(item['zone']) + "</div>"
            st.markdown(zone_html, unsafe_allow_html=True)
            onboard_html = "<div class='detail-label'>Onboarding Date</div><div class='detail-value'>" + fmt_val(item['onboarding_date']) + "</div>"
            st.markdown(onboard_html, unsafe_allow_html=True)
            dealer_html = "<div class='detail-label'>Dealership</div><div class='detail-value'>" + fmt_val(item['dealership']) + "</div>"
            st.markdown(dealer_html, unsafe_allow_html=True)
        with c2:
            vehicle_html = "<div class='detail-label'>Vehicle</div><div class='detail-value'>" + fmt_val(item['vehicle_model']) + "</div>"
            st.markdown(vehicle_html, unsafe_allow_html=True)
            price_html = "<div class='detail-label'>Vehicle Price / Amount Paid</div><div class='detail-value'>" + fmt_money(item['total_signup_amount']) + " / " + fmt_money(item['amount_paid']) + "</div>"
            st.markdown(price_html, unsafe_allow_html=True)
            plan_html = "<div class='detail-label'>Plan Amount</div><div class='detail-value'>" + fmt_money(item['plan_amount']) + "</div>"
            st.markdown(plan_html, unsafe_allow_html=True)

        if item["is_followup"]:
            st.caption("⚠️ This is already a follow-up call (one repeat used).")

    st.write("")
    st.info("**Script:** " + item["script"])
    if item["current_notes"]:
        st.caption("Previous notes: " + str(item["current_notes"]))

    result_key = "result_" + unique_key
    result_default_idx = 0
    if item.get("call_result") in CALL_RESULT_OPTIONS:
        result_default_idx = CALL_RESULT_OPTIONS.index(item["call_result"])
    call_result = st.selectbox("Call Result", CALL_RESULT_OPTIONS, index=result_default_idx, key=result_key)

    notes_key = "notes_" + unique_key
    notes = st.text_input("Call notes", value=item["current_notes"], key=notes_key)

    dfe_key = "dfe_" + unique_key
    dfe_default_idx = 0
    if item["dfe_status"] in DFE_OPTIONS:
        dfe_default_idx = DFE_OPTIONS.index(item["dfe_status"])
    dfe_col1, dfe_col2 = st.columns(2)
    with dfe_col1:
        dfe_value = st.selectbox("DFE/dealer asked for fees?", DFE_OPTIONS, index=dfe_default_idx, key=dfe_key)
    dfe_amount_value = ""
    if dfe_value == "Yes":
        with dfe_col2:
            existing_amount = str(item["dfe_amount"]) if item["dfe_amount"] else ""
            dfe_amount_value = st.text_input("Fee amount asked (Rs)", value=existing_amount, key="dfeamt_" + unique_key)

    st.write("")
    btn1, btn2, btn3 = st.columns(3)

    base_updates = {"Call_Notes": notes, "DFE_Fees_Asked": dfe_value, "Call_Outcome_Detail": call_result}
    if dfe_value == "Yes":
        base_updates["DFE_Fee_Amount"] = dfe_amount_value
    else:
        base_updates["DFE_Fee_Amount"] = ""

    with btn1:
        if st.button("✅ Call Completed", key="complete_" + unique_key, type="primary", use_container_width=True):
            updates = dict(base_updates)
            updates["Call_Status"] = "Call Completed"
            updates["Escalation_Status"] = ""
            save_updates(sheet, df, item["sheet_row"], updates)
            load_call_data.clear()
            st.success("Marked complete!")
            st.rerun()

    with btn2:
        if st.button("🚨 Escalate to DOM", key="escalate_" + unique_key, use_container_width=True):
            if not notes or not notes.strip():
                st.warning("Please add call notes describing the issue before escalating.")
            else:
                updates = dict(base_updates)
                updates["Call_Status"] = "Escalated to DOM"
                updates["Escalation_Status"] = "Open"
                save_updates(sheet, df, item["sheet_row"], updates)
                load_call_data.clear()
                msg = "🚨 *Case Escalated* — Onboarding Call\nDriver: " + str(item["driver_name"]) + " (" + str(item["driver_id"]) + ")\nContact: " + str(item["contact_number"]) + "\nUSC: " + fmt_val(item["usc_name"]) + "\nDOM: " + item["dom"] + "\nIssue: " + notes
                sent = send_slack_alert(msg)
                if sent:
                    st.success("Escalated and posted to Slack!")
                else:
                    st.success("Escalated (Slack not configured yet).")
                st.rerun()

    with btn3:
        followup_disabled = item["is_followup"]
        if st.button("🔁 Follow-up Tomorrow", key="followup_" + unique_key, use_container_width=True, disabled=followup_disabled):
            updates = dict(base_updates)
            tomorrow = today_ist() + timedelta(days=1)
            updates["Call_Due_Date"] = tomorrow.strftime("%d/%m/%Y")
            updates["Call_Status"] = "Pending"
            updates["Is_Followup"] = True
            save_updates(sheet, df, item["sheet_row"], updates)
            load_call_data.clear()
            st.success("Scheduled for tomorrow!")
            st.rerun()
        if followup_disabled:
            st.caption("Already used the one-time follow-up for this driver.")


def render_docs_detail(item, sheet, df, unique_key):
    detail_box = st.container(border=True)
    with detail_box:
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC: " + fmt_val(item['usc_name']) + " &nbsp;|&nbsp; DOM: " + item['dom'] + "</div>"
        st.markdown(name_html, unsafe_allow_html=True)
        tel_number = str(item['contact_number']).strip()
        if tel_number and tel_number.lower() != "nan":
            call_html = "<a class='call-link' href='tel:" + tel_number + "'>📱 Call " + tel_number + "</a>"
            st.markdown(call_html, unsafe_allow_html=True)
        zone_html = "<div class='detail-label'>Zone</div><div class='detail-value'>" + fmt_val(item['zone']) + "</div>"
        st.markdown(zone_html, unsafe_allow_html=True)
        onboard_html = "<div class='detail-label'>Onboarding Date</div><div class='detail-value'>" + fmt_val(item['onboarding_date']) + "</div>"
        st.markdown(onboard_html, unsafe_allow_html=True)

    st.write("")
    st.info("**Script:** " + item["script"])
    if item["current_notes"]:
        st.caption("Previous notes: " + str(item["current_notes"]))

    notes = st.text_input("Call notes", value=item["current_notes"], key="docsnotes_" + unique_key)

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("✅ Documents Received", key="docsdone_" + unique_key, type="primary", use_container_width=True):
            updates = {"Docs_Notes": notes, "Docs_Status": "Documents Received", "Escalation_Status": ""}
            save_updates(sheet, df, item["sheet_row"], updates)
            load_docs_data.clear()
            st.success("Marked as received!")
            st.rerun()
    with btn2:
        if st.button("🚨 Escalate to DOM", key="docsescalate_" + unique_key, use_container_width=True):
            if not notes or not notes.strip():
                st.warning("Please add notes before escalating.")
            else:
                updates = {"Docs_Notes": notes, "Docs_Status": "Escalated to DOM", "Escalation_Status": "Open"}
                save_updates(sheet, df, item["sheet_row"], updates)
                load_docs_data.clear()
                msg = "🚨 *Case Escalated* — Documentation\nDriver: " + str(item["driver_name"]) + " (" + str(item["driver_id"]) + ")\nContact: " + str(item["contact_number"]) + "\nUSC: " + fmt_val(item["usc_name"]) + "\nDOM: " + item["dom"] + "\nIssue: " + notes
                sent = send_slack_alert(msg)
                if sent:
                    st.success("Escalated and posted to Slack!")
                else:
                    st.success("Escalated (Slack not configured yet).")
                st.rerun()


def render_generic_tab(items, sheet, df, key_prefix, detail_fn):
    if not items:
        st.success("No calls due right now.")
        return

    selected_key = "selected_" + key_prefix
    search_key = "search_" + key_prefix
    if selected_key not in st.session_state:
        st.session_state[selected_key] = 0

    search_term = st.text_input("🔍 Search by name or ID", key=search_key, placeholder="Type to filter the list...")
    filtered = items
    if search_term:
        term = search_term.strip().lower()
        filtered = [it for it in items if term in str(it["driver_name"]).lower() or term in str(it["driver_id"]).lower()]

    if not filtered:
        st.warning("No matches for that search.")
        return

    if st.session_state[selected_key] >= len(filtered):
        st.session_state[selected_key] = 0

    list_col, detail_col = st.columns([1, 2])
    with list_col:
        for idx, item in enumerate(filtered):
            label = item["driver_name"] + "  (" + str(item["driver_id"]) + ")"
            btn_type = "primary" if idx == st.session_state[selected_key] else "secondary"
            if st.button(label, key=key_prefix + "_btn_" + str(item["sheet_row"]), use_container_width=True, type=btn_type):
                st.session_state[selected_key] = idx

    with detail_col:
        item = filtered[st.session_state[selected_key]]
        unique_key = key_prefix + "_" + str(item["sheet_row"])
        detail_fn(item, sheet, df, unique_key)


def render_metric(label, value):
    icon = METRIC_ICONS.get(label, "")
    icon_html = "<div style='font-size:1.4rem; color:" + BRAND_GREEN + "; font-weight:800;'>" + icon + "</div>"
    html = "<div class='metric-box'>" + icon_html + "<div class='metric-num'>" + str(value) + "</div><div class='metric-label'>" + label + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_escalations_panel(call_sheet, call_df, docs_sheet, docs_df):
    escalations = build_escalations(call_df, docs_df)
    st.subheader("🚨 Open Escalations (" + str(len(escalations)) + ")")

    if not escalations:
        st.success("No open escalations. Nice.")
        return

    dom_filter_options = ["All"] + sorted(set(e["dom"] for e in escalations))
    chosen_dom = st.selectbox("Filter by DOM", dom_filter_options, key="escalation_dom_filter")
    filtered = escalations if chosen_dom == "All" else [e for e in escalations if e["dom"] == chosen_dom]

    for e in filtered:
        card_html = "<div class='escalation-card'><b>" + str(e["driver_name"]) + "</b> (" + str(e["driver_id"]) + ") &nbsp;|&nbsp; " + e["source"] + " &nbsp;|&nbsp; USC: " + fmt_val(e["usc_name"]) + " &nbsp;|&nbsp; DOM: <b>" + e["dom"] + "</b><br>Contact: " + str(e["contact_number"]) + "<br>Notes: " + str(e["notes"]) + "</div>"
        st.markdown(card_html, unsafe_allow_html=True)
        resolve_key = "resolve_" + e["source"] + "_" + str(e["sheet_row"])
        if st.button("Mark Resolved", key=resolve_key):
            target_sheet = call_sheet if e["source"] == "Onboarding Call" else docs_sheet
            target_df = call_df if e["source"] == "Onboarding Call" else docs_df
            save_updates(target_sheet, target_df, e["sheet_row"], {"Escalation_Status": "Resolved"})
            if e["source"] == "Onboarding Call":
                load_call_data.clear()
            else:
                load_docs_data.clear()
            st.success("Marked resolved!")
            st.rerun()
        st.write("")


def render_dashboard_stage(items, status_field, status_options, title):
    total = len(items)
    counts = {}
    for opt in status_options:
        counts[opt] = 0
    for item in items:
        pass

    cols = st.columns(3)
    with cols[0]:
        render_metric("Total Due", total)
    with cols[1]:
        render_metric("Pending", total)
    with cols[2]:
        render_metric("Completed", 0)

    if total == 0:
        st.caption("Nobody in this list today.")
        return

    rows = []
    for g in items:
        rows.append({
            "Driver Name": str(g["driver_name"]),
            "Driver ID": str(g["driver_id"]),
            "Contact Number": str(g["contact_number"]),
            "USC": fmt_val(g["usc_name"]),
            "DOM": g["dom"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def main():
    title_html = "<h1>" + LOGO_SVG + "Battery Smart</h1>"
    st.markdown(title_html, unsafe_allow_html=True)
    st.caption("Onboarding Call Tracker & Documentation Tracker")

    if not check_password():
        return

    call_sheet = get_call_sheet()
    docs_sheet = get_docs_sheet()
    call_df = load_call_data(call_sheet)
    docs_df = load_docs_data(docs_sheet)

    call_due = build_call_due_list(call_df)
    docs_due = build_docs_due_list(docs_df)
    escalations = build_escalations(call_df, docs_df)

    with st.sidebar:
        sidebar_logo_html = "<div style='display:flex;align-items:center;gap:8px;'>" + LOGO_SVG + "<span style='font-weight:700;font-size:1.1rem;'>Battery Smart</span></div>"
        st.markdown(sidebar_logo_html, unsafe_allow_html=True)
        view = st.radio("View", ["📞 Onboarding Call Tracker", "📄 Documentation Tracker", "🚨 Escalations", "📊 Dashboard"], label_visibility="collapsed")
        st.divider()

        call_stat_html = "<div class='sidebar-stat-box'><div class='sidebar-stat-num'>" + str(len(call_due)) + "</div><div class='sidebar-stat-label'>Calls Due Today</div></div>"
        st.markdown(call_stat_html, unsafe_allow_html=True)
        docs_stat_html = "<div class='sidebar-stat-box'><div class='sidebar-stat-num'>" + str(len(docs_due)) + "</div><div class='sidebar-stat-label'>Docs Checks Due Today</div></div>"
        st.markdown(docs_stat_html, unsafe_allow_html=True)
        esc_stat_html = "<div class='sidebar-stat-box'><div class='sidebar-stat-num'>" + str(len(escalations)) + "</div><div class='sidebar-stat-label'>Open Escalations</div></div>"
        st.markdown(esc_stat_html, unsafe_allow_html=True)

        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            load_call_data.clear()
            load_docs_data.clear()
            st.rerun()

    if view == "📞 Onboarding Call Tracker":
        render_generic_tab(call_due, call_sheet, call_df, "call", render_call_detail)
    elif view == "📄 Documentation Tracker":
        render_generic_tab(docs_due, docs_sheet, docs_df, "docs", render_docs_detail)
    elif view == "🚨 Escalations":
        render_escalations_panel(call_sheet, call_df, docs_sheet, docs_df)
    elif view == "📊 Dashboard":
        dash_tab1, dash_tab2 = st.tabs(["Onboarding Call Tracker", "Documentation Tracker"])
        with dash_tab1:
            render_dashboard_stage(call_due, "current_status", CALL_STATUS_OPTIONS, "Onboarding Call Tracker")
        with dash_tab2:
            render_dashboard_stage(docs_due, "current_status", DOCS_STATUS_OPTIONS, "Documentation Tracker")


if __name__ == "__main__":
    main()
