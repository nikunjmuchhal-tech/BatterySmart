import streamlit as st
import pandas as pd
import requests
import json
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

CALL_SCRIPT = """Agent: Namaste! Main Battery Smart se Sheetal baat kar raha/rahi hoon. Kya mera baat [Customer Name] ji se ho raha hai?
Agent: Sir/Ma'am, sabse pehle Battery Smart family mein aapka swagat hai! Aur aapke naye vehicle ki purchase ke liye bahut-bahut badhaii!
Agent: Sir, kya aap please confirm kar sakte hain ki aapne kaunsa vehicle model liya hai?
Agent: Sir, aapki vehicle delivery kaisi rahi? Koi issue toh nahi aaya delivery ke time?

Agent: Sir, hamare data ke according aapne Autopay system chalu kr liya hai / nahi kra hai?
Agent: Kya aap confirm kar sakte hain ki EMI amount kitna set hua hai aur payment date kya hai?
EMI Amount confirmed: __________
Payment Date confirmed: __________
Agent: Perfect, bas make sure karein ki har mahine time par payment kar de, taaki koi late fee ya issue na ho.

If EMI not yet started:
Agent: Sir, agar aapne abhi tak UPI Autopay start nahi ki hai toh please jald hi start kar lein. Aapko payment specifically Upgrid Solutions ke through aayi ek link par karna hai.
Agent: Woh link aapke registered number par SMS/WhatsApp ke through aayega. Kindly us link par click karke apni payment details verify karke EMI setup complete kar lein.

Agent: Sir/Ma'am, aapka time dene ke liye bahut dhanyavaad. Agar aapko koi bhi query ho Battery Smart ya UPI payment se related, toh aap humein kabhi bhi isi number par contact kar sakte hain.
Agent: Ek baar phir se, Battery Smart family mein aapka swagat hai. Have a great day!"""

CALL_2_SCRIPT = CALL_SCRIPT

# Which onboarding-call stages are currently active. Scaling initially covers
# D+1 through D+7; once volume settles down, just change this list back to
# [1, 2] to reduce to the original D+1/D+2 flow - no other code changes needed.
CALL_STAGES = [1, 2, 3, 4, 5, 6, 7]


def call_stage_columns(stage):
    if stage == 1:
        return "Call_Due_Date", "Call_Status", "Call_Notes", "Is_Followup"
    return (
        "Call_" + str(stage) + "_Due_Date",
        "Call_" + str(stage) + "_Status",
        "Call_" + str(stage) + "_Notes",
        "Is_Followup_" + str(stage),
    )

DOCS_SCRIPT = """Agent: Namaste! Main Battery Smart se Sheetal baat kar raha/rahi hoon. Kya mera baat [Customer Name] ji se ho raha hai?
Agent: Sir/Ma'am, hum aapko ek chota sa follow-up call kar rahe hain, aapke vehicle ke documents ka status check karne ke liye.

1. Sir, kya aapko invoice number, number plate and insurance document mil gaye hai?
2. If not - reason
3. Sir, ek chota sa feedback chahiye tha - overall aapki Battery Smart ke saath ab tak ki service kaisi rahi hai? Koi issue ya complaint hai jo aap share karna chahenge?
4. Sir/Ma'am, aapka time dene ke liye bahut dhanyavaad. Agar aapko aage payment ya document ya koi query ho, toh aap humein contact kar sakte hain. Battery Smart family mein aapka saath dene ke liye shukriya!"""

CALL_STATUS_OPTIONS = ["Pending", "Call Attempted", "Escalated to DOM", "Follow-up Needed"]
DOCS_STATUS_OPTIONS = ["Pending", "Documents Received", "Not Received", "Escalated to DOM"]
DFE_OPTIONS = ["Not Checked", "Yes", "No"]

STATUS_DOT = {
    "Pending": "⚪",
    "Call Attempted": "🟢",
    "Escalated to DOM": "🔴",
    "Follow-up Needed": "🔵",
    "Documents Received": "🟢",
}

BRAND_GREEN = "#00C389"
BRAND_NAVY = "#151272"

LOGO_SVG = (
    "<svg width='40' height='40' viewBox='0 0 200 200' style='vertical-align:middle; margin-right:12px; border-radius:9px;'>"
    "<rect width='200' height='200' rx='38' fill='#151272'/>"
    "<rect x='88' y='34' width='24' height='18' rx='4' fill='#00C389'/>"
    "<path d='M58 50 C46 50 42 62 50 71 L94 100 L50 129 C42 138 46 150 58 150 L142 150 C154 150 158 138 150 129 L106 100 L150 71 C158 62 154 50 142 50 Z M74 68 L126 68 L100 96 Z M74 132 L126 132 L100 104 Z' fill='#00C389'/>"
    "</svg>"
)

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
    "shail kumar mishra": "Aman",
    "mishra": "Aman",
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
    "sahil": "Sajid",
    "mohd aarif": "Sajid",
    "aarif": "Sajid",
}

DOM_SLACK_ID = {
    "Aman": "U09EHLRG3J7",
    "Sajid": "U0AMA1TAJ2Y",
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
        return False, "No slack_webhook_url found in secrets."
    try:
        resp = requests.post(webhook, json={"text": message}, timeout=6)
        if resp.status_code == 200:
            return True, ""
        return False, "Slack responded with status " + str(resp.status_code) + ": " + resp.text
    except Exception as e:
        return False, "Request failed: " + str(e)


def send_slack_message(text, thread_ts=None, driver_id=None, source=None, include_button=False):
    """
    Posts via the Slack Bot Token (chat.postMessage) instead of the Incoming Webhook,
    so we get back a message `ts` we can thread replies under, and so we can attach
    a real interactive "Mark Resolved" button.
    Requires st.secrets["slack_bot_token"] and st.secrets["slack_channel_id"].
    Returns (ok: bool, ts: str|None, error: str)

    If the bot token path isn't configured or fails outright, this automatically
    falls back to the Incoming Webhook (send_slack_alert) so the escalation still
    reaches Slack - just without threading/the Mark Resolved button.
    """
    token = st.secrets.get("slack_bot_token", "")
    channel = st.secrets.get("slack_channel_id", "")
    if not token or not channel:
        webhook_sent, webhook_err = send_slack_alert(text)
        if webhook_sent:
            return True, None, "(sent via webhook fallback - bot token not configured: add slack_bot_token + slack_channel_id to secrets for threading/buttons)"
        return False, None, "No slack_bot_token / slack_channel_id in secrets, AND webhook fallback failed: " + webhook_err

    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if include_button and driver_id and source:
        payload["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Mark Resolved", "emoji": True},
                        "style": "primary",
                        "action_id": "mark_resolved",
                        "value": json.dumps({"source": source, "driver_id": str(driver_id)}),
                    }
                ],
            },
        ]

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8"},
            json=payload,
            timeout=6,
        )
        data = resp.json()
        if data.get("ok"):
            return True, data.get("ts"), ""

        slack_err = str(data.get("error"))
        # Bot-token path failed (bad token, bot not in channel, wrong channel id, etc).
        # Fall back to the webhook so the escalation isn't silently lost.
        webhook_sent, webhook_err = send_slack_alert(text)
        if webhook_sent:
            return True, None, "(bot token failed: '" + slack_err + "' - sent via webhook fallback instead. Fix: check slack_bot_token is valid and the bot user is invited to the channel with 'chat:write' scope)"
        return False, None, "Slack bot-token error: " + slack_err + " | Webhook fallback also failed: " + webhook_err
    except Exception as e:
        webhook_sent, webhook_err = send_slack_alert(text)
        if webhook_sent:
            return True, None, "(bot token request crashed: " + str(e) + " - sent via webhook fallback instead)"
        return False, None, "Request failed: " + str(e) + " | Webhook fallback also failed: " + webhook_err


st.markdown(
    "<style>"
    "[data-testid='stAppViewContainer'] { background: linear-gradient(160deg, #f0fffa 0%, #ffffff 30%, #f1f2ff 100%); }"
    "[data-testid='stHeader'] { background: rgba(0,0,0,0); }"
    "[data-testid='stSidebarNav'] { display: none !important; visibility: hidden !important; height: 0 !important; min-height: 0 !important; }"
    "div[data-testid='stSidebarNavItems'] { display: none !important; }"
    "nav[data-testid='stSidebarNav'] { display: none !important; }"
    "[data-testid='stSidebar'] { background: linear-gradient(180deg, " + BRAND_NAVY + " 0%, #23197a 100%); min-width: 310px !important; box-shadow: 4px 0 20px rgba(0,0,0,0.15); }"
    "[data-testid='stSidebar'] * { color: #ffffff !important; }"
    "[data-testid='stSidebar'] .block-container { padding-top: 2.2rem; padding-left: 1.4rem; padding-right: 1.4rem; }"
    "[data-testid='stSidebar'] .stRadio { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 10px; }"
    "[data-testid='stSidebar'] .stRadio div[role='radiogroup'] { gap: 4px; }"
    "[data-testid='stSidebar'] .stRadio label { font-size: 1.02rem !important; font-weight: 600; padding: 12px 14px !important; border-radius: 12px; width: 100%; transition: background 0.15s ease; }"
    "[data-testid='stSidebar'] .stRadio label:hover { background: rgba(255,255,255,0.08); }"
    "[data-testid='stSidebar'] .stRadio label[data-checked='true'] { background: " + BRAND_GREEN + " !important; }"
    "[data-testid='stSidebar'] .stRadio label[data-checked='true'] p { color: " + BRAND_NAVY + " !important; font-weight: 800 !important; }"
    "[data-testid='stSidebar'] .stRadio input:checked + div { background: " + BRAND_GREEN + " !important; }"
    "[data-testid='stSidebar'] div[data-testid='stMarkdownContainer'] p { font-size: 1.02rem !important; }"
    "[data-testid='stSidebar'] hr { border: none; border-top: 1px solid rgba(255,255,255,0.12); margin: 22px 0; }"
    "[data-testid='stSidebar'] div.stButton > button { font-size: 0.98rem !important; padding: 11px 0 !important; background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important; }"
    "[data-testid='stSidebar'] div.stButton > button:hover { background: rgba(255,255,255,0.16) !important; border-color: " + BRAND_GREEN + " !important; }"
    ".sidebar-brand-box { padding: 4px 4px 20px 4px; }"
    ".sidebar-stat-box { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }"
    ".sidebar-stat-num { font-size: 1.6rem; font-weight: 800; color: " + BRAND_GREEN + " !important; }"
    ".sidebar-stat-label { font-size: 0.85rem; color: #d7d5ff !important; text-transform: uppercase; letter-spacing: 0.4px; }"
    "h1 { font-size: 2.3rem !important; color:" + BRAND_NAVY + " !important; font-weight: 800 !important; margin-bottom: 0px !important; }"
    "[data-testid='stCaptionContainer'] p { font-size: 1.05rem !important; color: #6b7280 !important; }"
".stTabs [data-baseweb='tab-list'] { gap: 10px; border-bottom: none; background: #eef0f5; padding: 6px; border-radius: 999px; display: inline-flex; }"
    ".stTabs [data-baseweb='tab'] { font-size: 1.0rem !important; font-weight: 600; padding: 8px 22px !important; background: transparent !important; border-radius: 999px !important; color: #6b7280 !important; border: none !important; outline: none !important; box-shadow: none !important; }"
    ".stTabs [data-baseweb='tab']:focus { outline: none !important; box-shadow: none !important; }"
    ".stTabs [aria-selected='true'] { color: " + BRAND_NAVY + " !important; background: #ffffff !important; box-shadow: 0 2px 6px rgba(21,18,114,0.15) !important; border: none !important; }"
    ".stTabs [aria-selected='true'] p { color: " + BRAND_NAVY + " !important; font-weight: 700 !important; }"
    ".stTabs [data-baseweb='tab-highlight'] { display: none !important; }"
    ".stTabs [data-baseweb='tab-border'] { display: none !important; }"
    ".bs-table { width: 100%; border-collapse: collapse; font-size: 1.05rem; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(21,18,114,0.08); }"
    ".bs-table thead th { background: " + BRAND_NAVY + "; color: " + BRAND_GREEN + " !important; text-align: left; padding: 14px 16px; font-weight: 700; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.4px; }"
    ".bs-table tbody td { padding: 12px 16px; border-bottom: 1px solid #eef0f5; color: #111827 !important; font-size: 1.05rem; }"
    ".bs-table tbody tr:hover { background: #f0fffa; }"
    ".status-pill { padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; display: inline-block; }"
    ".status-pill.pending { background: #f3f4f6; color: #6b7280 !important; }"
    ".status-pill.call-attempted { background: #dcfce7; color: #16a34a !important; }"
    ".status-pill.documents-received { background: #dcfce7; color: #16a34a !important; }"
    ".status-pill.escalated-to-dom { background: #fee2e2; color: #dc2626 !important; }"
    ".status-pill.not-received { background: #ffedd5; color: #ea580c !important; }"
    ".status-pill.follow-up-needed { background: #dbeafe; color: #2563eb !important; }"
    ".status-pill.connected { background: #dcfce7; color: #16a34a !important; }"
    ".status-pill.not-connected { background: #fee2e2; color: #dc2626 !important; }"
    ".status-pill.incoming-not-available { background: #ffedd5; color: #ea580c !important; }"
    ".status-pill.followup-scheduled { background: #dbeafe; color: #2563eb !important; }"
    ".detail-name { font-size: 1.4rem; font-weight: 700; margin-bottom: 2px; color:" + BRAND_NAVY + " !important; }"
    ".detail-sub { font-size: 0.9rem; color: #6b7280 !important; margin-bottom: 12px; }"
    ".detail-label { font-size: 0.72rem; color: #9ca3af !important; text-transform: uppercase; letter-spacing: 0.5px; }"
    ".detail-value { font-size: 1.0rem; margin-bottom: 8px; color: #111827 !important; font-weight: 500; }"
    ".call-link { display:inline-block; background:" + BRAND_GREEN + "; color: #ffffff !important; padding:6px 14px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.95rem; }"
    ".metric-box { background: linear-gradient(135deg, " + BRAND_NAVY + " 0%, #2a2496 100%); border-radius:16px; padding:20px 10px; text-align:center; box-shadow: 0 4px 14px rgba(21,18,114,0.22); border: 1px solid rgba(255,255,255,0.08); }"
    ".metric-num { font-size:2.0rem; font-weight:800; color: #ffffff !important; line-height: 1.1; }"
    ".metric-label { font-size:0.76rem; color:" + BRAND_GREEN + " !important; text-transform:uppercase; letter-spacing:0.5px; margin-top: 4px; font-weight: 600; }"
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
    "[data-testid='stDataFrame'] [role='columnheader'] { background-color: " + BRAND_NAVY + " !important; color: " + BRAND_GREEN + " !important; font-weight: 800 !important; font-size: 1.05rem !important; }"
    "[data-testid='stDataFrame'] [role='columnheader'] * { color: " + BRAND_GREEN + " !important; }"
    "[data-testid='stHeadingWithActionElements'] h1, [data-testid='stHeadingWithActionElements'] h2, [data-testid='stHeadingWithActionElements'] h3 { color:" + BRAND_NAVY + " !important; }"
    ".detail-name, .detail-value, .detail-label, .detail-sub { color-scheme: light; }"
    "[class*='st-key-docok_wrap_'] button { background-color: #f0fdf4 !important; border: 1.5px solid #16a34a !important; color: #16a34a !important; font-weight: 700 !important; }"
    "[class*='st-key-docok_wrap_'] button p { color: #16a34a !important; font-weight: 700 !important; }"
    "[class*='st-key-docok_wrap_'] button:hover { background-color: #16a34a !important; }"
    "[class*='st-key-docok_wrap_'] button:hover p { color: #ffffff !important; }"
    "[class*='st-key-docok_wrap_'] button[kind='primary'] { background-color: #16a34a !important; border-color: #16a34a !important; box-shadow: 0 2px 8px rgba(22,163,74,0.35) !important; }"
    "[class*='st-key-docok_wrap_'] button[kind='primary'] p { color: #ffffff !important; }"
    "[class*='st-key-docno_wrap_'] button { background-color: #fef2f2 !important; border: 1.5px solid #dc2626 !important; color: #dc2626 !important; font-weight: 700 !important; }"
    "[class*='st-key-docno_wrap_'] button p { color: #dc2626 !important; font-weight: 700 !important; }"
    "[class*='st-key-docno_wrap_'] button:hover { background-color: #dc2626 !important; }"
    "[class*='st-key-docno_wrap_'] button:hover p { color: #ffffff !important; }"
    "[class*='st-key-docno_wrap_'] button[kind='primary'] { background-color: #dc2626 !important; border-color: #dc2626 !important; box-shadow: 0 2px 8px rgba(220,38,38,0.35) !important; }"
    "[class*='st-key-docno_wrap_'] button[kind='primary'] p { color: #ffffff !important; }"
    "</style>",
    unsafe_allow_html=True,
)


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


@st.cache_data(ttl=180)
def load_call_data(_sheet):
    return pd.DataFrame(_sheet.get_all_records())


@st.cache_data(ttl=180)
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
        base = {}
        base["sheet_row"] = i + 2
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
        base["usc_id"] = row.get("USC_ID")
        base["usc_name"] = row.get("USC_Name")
        base["dom"] = get_dom(row.get("USC_Name"))
        base["dfe_status"] = row.get("DFE_Fees_Asked", "Not Checked") or "Not Checked"
        base["dfe_amount"] = row.get("DFE_Fee_Amount", "")
        base["call_result"] = row.get("Call_Outcome_Detail", "")
        base["autopay_status"] = row.get("Autopay_Mandate_Status", "")
        base["emi_due_date"] = row.get("EMI_Due_Date", "")

        for stage in CALL_STAGES:
            due_col, status_col, notes_col, followup_col = call_stage_columns(stage)
            due_date = parse_date(row.get(due_col))
            status = row.get(status_col, "Pending") or "Pending"
            if due_date == today and status == "Pending":
                item = dict(base)
                item["call_num"] = stage
                item["stage_label"] = "D+" + str(stage)
                item["status_col"] = status_col
                item["notes_col"] = notes_col
                item["due_col"] = due_col
                item["followup_flag_col"] = followup_col
                item["is_followup"] = str(row.get(followup_col, "")).strip().upper() in ("TRUE", "1", "YES")
                item["current_notes"] = row.get(notes_col, "")
                item["show_dfe"] = (stage == 1)
                item["script"] = CALL_SCRIPT.format(name=row.get("Driver_Name"))
                due.append(item)

    return due


def build_call_all_records(df):
    """
    Every driver, every stage, regardless of due date or current status.
    Used by the 'Search & Edit Any Record' box so an agent can reopen and
    correct an entry (e.g. a driver who calls back later after being marked
    Not Connected earlier), even though it's no longer in today's due list.
    """
    records = []
    for i, row in df.iterrows():
        base = {}
        base["sheet_row"] = i + 2
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
        base["usc_id"] = row.get("USC_ID")
        base["usc_name"] = row.get("USC_Name")
        base["dom"] = get_dom(row.get("USC_Name"))
        base["dfe_status"] = row.get("DFE_Fees_Asked", "Not Checked") or "Not Checked"
        base["dfe_amount"] = row.get("DFE_Fee_Amount", "")
        base["call_result"] = row.get("Call_Outcome_Detail", "")
        base["autopay_status"] = row.get("Autopay_Mandate_Status", "")
        base["emi_due_date"] = row.get("EMI_Due_Date", "")

        for stage in CALL_STAGES:
            due_col, status_col, notes_col, followup_col = call_stage_columns(stage)
            due_date = row.get(due_col)
            if not due_date:
                continue
            item = dict(base)
            item["call_num"] = stage
            item["stage_label"] = "D+" + str(stage)
            item["status_col"] = status_col
            item["notes_col"] = notes_col
            item["due_col"] = due_col
            item["followup_flag_col"] = followup_col
            item["is_followup"] = str(row.get(followup_col, "")).strip().upper() in ("TRUE", "1", "YES")
            item["current_notes"] = row.get(notes_col, "")
            item["current_status"] = row.get(status_col, "Pending") or "Pending"
            item["show_dfe"] = (stage == 1)
            item["script"] = CALL_SCRIPT.format(name=row.get("Driver_Name"))
            records.append(item)

    return records


def build_call_today_all(df):
    today = today_ist()
    rows = []
    for i, row in df.iterrows():
        for stage in CALL_STAGES:
            due_col, status_col, _, _ = call_stage_columns(stage)
            due_date = parse_date(row.get(due_col))
            if due_date == today:
                rows.append({
                    "driver_id": row.get("Driver_ID"),
                    "driver_name": row.get("Driver_Name") + " [D+" + str(stage) + "]",
                    "contact_number": row.get("Contact_Number"),
                    "usc_name": row.get("USC_Name"),
                    "dom": get_dom(row.get("USC_Name")),
                    "status": row.get(status_col, "Pending") or "Pending",
                    "call_result": row.get("Call_Outcome_Detail", "") or "—",
                })
    return rows


def build_docs_today_all(df):
    today = today_ist()
    rows = []
    for i, row in df.iterrows():
        due_date = parse_date(row.get("Docs_Call_Due_Date"))
        if due_date == today:
            rows.append({
                "driver_id": row.get("Driver_ID"),
                "driver_name": row.get("Driver_Name"),
                "contact_number": row.get("Contact_Number"),
                "usc_name": row.get("USC_Name"),
                "dom": get_dom(row.get("USC_Name")),
                "status": row.get("Docs_Status", "Pending") or "Pending",
            })
    return rows


def _build_docs_item(i, row):
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
    item["dealership"] = row.get("Dealership")
    item["vehicle_model"] = row.get("Vehicle_Model")
    item["total_signup_amount"] = row.get("Total_Signup_Amount")
    item["amount_paid"] = row.get("Amount_Paid")
    item["plan_amount"] = row.get("Plan_Amount")
    item["autopay_status"] = row.get("Autopay_Mandate_Status", "")
    item["emi_due_date"] = row.get("EMI_Due_Date", "")
    item["current_notes"] = row.get("Docs_Notes", "")
    item["current_status"] = row.get("Docs_Status", "Pending") or "Pending"
    item["invoice_status"] = row.get("Invoice_Status", "Not Received") or "Not Received"
    item["number_plate_status"] = row.get("Number_Plate_Status", "Not Received") or "Not Received"
    item["insurance_status"] = row.get("Insurance_Status", "Not Received") or "Not Received"
    item["script"] = DOCS_SCRIPT
    return item


def build_docs_due_list(df):
    today = today_ist()
    due = []
    for i, row in df.iterrows():
        due_date = parse_date(row.get("Docs_Call_Due_Date"))
        status = row.get("Docs_Status", "Pending") or "Pending"
        if due_date == today and status == "Pending":
            due.append(_build_docs_item(i, row))
    return due


def build_docs_all_records(df):
    """
    Every driver in the Docs Tracker, regardless of due date or current status -
    mirrors build_call_all_records so a manager can reopen/correct any past
    documentation record (e.g. a document arrives later, or was marked wrong).
    """
    records = []
    for i, row in df.iterrows():
        due_date = row.get("Docs_Call_Due_Date")
        if not due_date:
            continue
        records.append(_build_docs_item(i, row))
    return records


def build_escalations(call_df, docs_df):
    escalations = []
    for i, row in call_df.iterrows():
        if str(row.get("Escalation_Status", "")).strip() == "Open":
            escalated_status_col = None
            for stage in CALL_STAGES:
                s_due_col, s_status_col, _, _ = call_stage_columns(stage)
                if str(row.get(s_status_col, "")).strip() == "Escalated to DOM":
                    escalated_status_col = s_status_col
                    break
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
                "escalated_status_col": escalated_status_col,
                "slack_ts": row.get("Slack_Message_Ts", "") or "",
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
                "escalated_status_col": "Docs_Status",
                "invoice_status": row.get("Invoice_Status", "Not Received") or "Not Received",
                "number_plate_status": row.get("Number_Plate_Status", "Not Received") or "Not Received",
                "insurance_status": row.get("Insurance_Status", "Not Received") or "Not Received",
                "slack_ts": row.get("Slack_Message_Ts", "") or "",
            })
    return escalations


def save_updates(sheet, df, sheet_row, updates):
    """
    Writes `updates` to the sheet AND patches the same cells into the
    in-memory (cached) dataframe, so callers don't need to clear the
    st.cache_data cache and force a full re-fetch of the whole sheet just
    to see their own write reflected. This avoids:
      1) an extra Google Sheets API round-trip on every single button click
         (this was the main source of the "app feels slow" complaints), and
      2) a read-after-write race, where the immediate refetch could return
         a not-yet-propagated (stale) version of the row and appear to
         "undo" or "overwrite" a value that was in fact saved correctly.
    """
    header = df.columns.tolist()
    batch = []
    row_idx = sheet_row - 2  # dataframe is 0-indexed; sheet row 2 == df index 0
    for col_name in updates:
        if col_name not in header:
            continue
        col_idx = header.index(col_name) + 1
        cell_range = gspread.utils.rowcol_to_a1(sheet_row, col_idx)
        batch.append({"range": cell_range, "values": [[updates[col_name]]]})
        if 0 <= row_idx < len(df):
            df.at[row_idx, col_name] = updates[col_name]
    if batch:
        sheet.batch_update(batch)


def render_call_detail(item, sheet, df, unique_key):
    detail_box = st.container(border=True)
    with detail_box:
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC: " + fmt_val(item['usc_name']) + " &nbsp;|&nbsp; DOM: " + item['dom'] + " &nbsp;|&nbsp; Stage: <b>" + item["stage_label"] + "</b></div>"
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
            price_html = "<div class='detail-label'>Signup Amount / Signup Amount Paid</div><div class='detail-value'>" + fmt_money(item['total_signup_amount']) + " / " + fmt_money(item['amount_paid']) + "</div>"
            st.markdown(price_html, unsafe_allow_html=True)
            plan_html = "<div class='detail-label'>Plan Amount</div><div class='detail-value'>" + fmt_money(item['plan_amount']) + "</div>"
            st.markdown(plan_html, unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            autopay_html = "<div class='detail-label'>Autopay Mandate</div><div class='detail-value'>" + fmt_val(item.get('autopay_status')) + "</div>"
            st.markdown(autopay_html, unsafe_allow_html=True)
        with c4:
            emi_html = "<div class='detail-label'>EMI Due Date</div><div class='detail-value'>" + fmt_val(item.get('emi_due_date')) + "</div>"
            st.markdown(emi_html, unsafe_allow_html=True)

        if item["is_followup"]:
            st.caption("⚠️ This is already a follow-up call (one repeat used).")

    st.write("")
    with st.expander("▶ Show call script"):
        st.markdown(item["script"])
    if item["current_notes"]:
        st.caption("Previous notes: " + str(item["current_notes"]))

    result_key = "result_" + unique_key
    result_default_idx = 0
    if item.get("call_result") in CALL_RESULT_OPTIONS:
        result_default_idx = CALL_RESULT_OPTIONS.index(item["call_result"])
    call_result = st.selectbox("Call Result", CALL_RESULT_OPTIONS, index=result_default_idx, key=result_key)

    notes_key = "notes_" + unique_key
    notes = st.text_input("Call notes", value=item["current_notes"], key=notes_key)

    dfe_value = None
    dfe_amount_value = ""
    if item["show_dfe"]:
        dfe_key = "dfe_" + unique_key
        dfe_default_idx = 0
        if item["dfe_status"] in DFE_OPTIONS:
            dfe_default_idx = DFE_OPTIONS.index(item["dfe_status"])
        dfe_col1, dfe_col2 = st.columns(2)
        with dfe_col1:
            dfe_value = st.selectbox("Did DFE ask for any fee?", DFE_OPTIONS, index=dfe_default_idx, key=dfe_key)
        if dfe_value == "Yes":
            with dfe_col2:
                existing_amount = str(item["dfe_amount"]) if item["dfe_amount"] else ""
                dfe_amount_value = st.text_input("Fee amount asked (Rs)", value=existing_amount, key="dfeamt_" + unique_key)

    st.write("")
    btn1, btn2, btn3 = st.columns(3)

    base_updates = {item["notes_col"]: notes, "Call_Outcome_Detail": call_result}
    if dfe_value is not None:
        base_updates["DFE_Fees_Asked"] = dfe_value
        if dfe_value == "Yes":
            base_updates["DFE_Fee_Amount"] = dfe_amount_value
        else:
            base_updates["DFE_Fee_Amount"] = ""

    with btn1:
        if st.button("✅ Call Attempted", key="complete_" + unique_key, type="primary", use_container_width=True):
            updates = dict(base_updates)
            updates[item["status_col"]] = "Call Attempted"
            updates["Escalation_Status"] = ""
            save_updates(sheet, df, item["sheet_row"], updates)
            st.toast("Marked as attempted!", icon="✅")
            st.rerun()

    with btn2:
        if st.button("🚨 Escalate to DOM", key="escalate_" + unique_key, use_container_width=True):
            updates = dict(base_updates)
            updates[item["status_col"]] = "Escalated to DOM"
            updates["Escalation_Status"] = "Open"
            save_updates(sheet, df, item["sheet_row"], updates)
            dom_id = DOM_SLACK_ID.get(item["dom"])
            dom_mention = ("<@" + dom_id + "> ") if dom_id else ""
            issue_line = ("\nIssue: " + notes) if notes and notes.strip() else ""
            msg = dom_mention + "🚨 *Case Escalated* — Onboarding Call (" + item["stage_label"] + ")\nDriver: " + str(item["driver_name"]) + " (" + str(item["driver_id"]) + ")\nContact: " + str(item["contact_number"]) + "\nUSC: " + fmt_val(item["usc_name"]) + "\nDOM: " + item["dom"] + issue_line
            sent, ts, err = send_slack_message(msg, driver_id=item["driver_id"], source="Onboarding Call", include_button=True)
            if sent and ts:
                save_updates(sheet, df, item["sheet_row"], {"Slack_Message_Ts": ts})
            st.session_state["last_slack_result"] = (sent, err, item["driver_name"])
            st.rerun()

    with btn3:
        if item["is_followup"]:
            st.button("🔁 Follow-up Tomorrow", key="followup_" + unique_key, use_container_width=True, disabled=True)
            st.caption("⚠️ Already followed up once on this stage. Please mark Attempted or Escalate to DOM instead.")
        else:
            if st.button("🔁 Follow-up Tomorrow", key="followup_" + unique_key, use_container_width=True):
                updates = dict(base_updates)
                tomorrow = today_ist() + timedelta(days=1)
                updates[item["due_col"]] = tomorrow.strftime("%d/%m/%Y")
                updates[item["status_col"]] = "Pending"
                updates[item["followup_flag_col"]] = True
                updates["Escalation_Status"] = ""
                save_updates(sheet, df, item["sheet_row"], updates)
                st.toast("Scheduled for tomorrow!", icon="🔁")
                st.rerun()


DOC_ITEMS = [
    ("invoice_status", "Invoice_Status", "🧾 Invoice"),
    ("number_plate_status", "Number_Plate_Status", "🔢 Number Plate"),
    ("insurance_status", "Insurance_Status", "🛡️ Insurance"),
]


def render_docs_detail(item, sheet, df, unique_key):
    detail_box = st.container(border=True)
    with detail_box:
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC: " + fmt_val(item['usc_name']) + " &nbsp;|&nbsp; DOM: " + item['dom'] + "</div>"
        st.markdown(name_html, unsafe_allow_html=True)

        tel_number = str(item['contact_number']).strip()
        if tel_number and tel_number.lower() != "nan":
            call_html = "<a class='call-link' href='tel:" + tel_number + "'>📱 Call " + tel_number + "</a>"
            st.markdown(call_html, unsafe_allow_html=True)
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
            price_html = "<div class='detail-label'>Signup Amount / Signup Amount Paid</div><div class='detail-value'>" + fmt_money(item['total_signup_amount']) + " / " + fmt_money(item['amount_paid']) + "</div>"
            st.markdown(price_html, unsafe_allow_html=True)
            plan_html = "<div class='detail-label'>Plan Amount (EMI/Subscription)</div><div class='detail-value'>" + fmt_money(item['plan_amount']) + "</div>"
            st.markdown(plan_html, unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            autopay_html = "<div class='detail-label'>Autopay Mandate</div><div class='detail-value'>" + fmt_val(item.get('autopay_status')) + "</div>"
            st.markdown(autopay_html, unsafe_allow_html=True)
        with c4:
            emi_html = "<div class='detail-label'>EMI Due Date</div><div class='detail-value'>" + fmt_val(item.get('emi_due_date')) + "</div>"
            st.markdown(emi_html, unsafe_allow_html=True)

    st.write("")
    with st.expander("▶ Show call script"):
        st.markdown(item["script"])
    if item["current_notes"]:
        st.caption("Previous notes: " + str(item["current_notes"]))

    notes = st.text_input("Call notes", value=item["current_notes"], key="docsnotes_" + unique_key)

    st.write("")
    st.markdown("**Document Checklist**")

    checklist_box = st.container(border=True)
    current_doc_values = {}
    with checklist_box:
        header_c1, header_c3, header_c4 = st.columns([2.4, 1.3, 1.3])
        with header_c1:
            st.markdown("<span class='detail-label'>DOCUMENT</span>", unsafe_allow_html=True)
        with header_c3:
            st.markdown("<span class='detail-label'>&nbsp;</span>", unsafe_allow_html=True)
        with header_c4:
            st.markdown("<span class='detail-label'>&nbsp;</span>", unsafe_allow_html=True)

        for item_key, sheet_col, label in DOC_ITEMS:
            raw_status = str(item.get(item_key, "")).strip()
            # Three states: "Received" and "Not Received" are only shown as
            # filled/selected when that exact value was explicitly set by a
            # click. Anything else (blank cell, or legacy values like "Not
            # Collected" from before the rename) is "unset" - neither button
            # is highlighted, same look as an untouched Received button.
            if raw_status == "Received":
                current_status = "Received"
            elif raw_status == "Not Received":
                current_status = "Not Received"
            else:
                current_status = "Unset"
            current_doc_values[label] = current_status

            # "Flash" state: buttons only show filled for one render pass right
            # after you click them (immediate feedback), then go back to plain
            # outlined on every subsequent load/rerun - they never persist a
            # filled look just because that's what's saved in the sheet.
            flash_key = "doc_flash_" + item_key + "_" + unique_key
            flash = st.session_state.pop(flash_key, None)

            row_c1, row_c3, row_c4 = st.columns([2.4, 1.3, 1.3])
            with row_c1:
                st.markdown("**" + label + "**")
            with row_c3:
                with st.container(key="docok_wrap_" + item_key + "_" + unique_key):
                    ok_type = "primary" if flash == "Received" else "secondary"
                    if st.button("✅ Received", key="doc_ok_" + item_key + "_" + unique_key, type=ok_type, use_container_width=True):
                        save_updates(sheet, df, item["sheet_row"], {sheet_col: "Received"})
                        st.session_state[flash_key] = "Received"
                        st.toast(label + " marked received!", icon="✅")
                        st.rerun()
            with row_c4:
                with st.container(key="docno_wrap_" + item_key + "_" + unique_key):
                    no_type = "primary" if flash == "Not Received" else "secondary"
                    if st.button("❌ Not Received", key="doc_no_" + item_key + "_" + unique_key, type=no_type, use_container_width=True):
                        save_updates(sheet, df, item["sheet_row"], {sheet_col: "Not Received"})
                        st.session_state[flash_key] = "Not Received"
                        st.toast(label + " marked not received.", icon="❌")
                        st.rerun()

    received_count = sum(1 for v in current_doc_values.values() if v == "Received")
    st.caption(str(received_count) + " of " + str(len(current_doc_values)) + " documents marked Received.")

    st.write("")
    all_collected = all(v == "Received" for v in current_doc_values.values())

    bfoot1, bfoot2 = st.columns(2)
    with bfoot1:
        if st.button("✅ Mark All Documents Received", key="docsdone_" + unique_key, type="primary", use_container_width=True):
            updates = {
                "Docs_Notes": notes,
                "Docs_Status": "Documents Received",
                "Escalation_Status": "",
                "Invoice_Status": "Received",
                "Number_Plate_Status": "Received",
                "Insurance_Status": "Received",
            }
            save_updates(sheet, df, item["sheet_row"], updates)
            st.toast("All documents marked received!", icon="✅")
            st.rerun()
    with bfoot2:
        if st.button("🚨 Escalate to DOM", key="docsescalate_" + unique_key, use_container_width=True):
            docs_status = "Documents Received" if all_collected else "Not Received"
            updates = {"Docs_Notes": notes, "Docs_Status": docs_status, "Escalation_Status": "Open"}
            save_updates(sheet, df, item["sheet_row"], updates)
            dom_id = DOM_SLACK_ID.get(item["dom"])
            dom_mention = ("<@" + dom_id + "> ") if dom_id else ""
            missing = [label for label, v in current_doc_values.items() if v != "Received"]
            missing_text = ", ".join(missing) if missing else "None — all documents collected"
            issue_line = ("\nIssue: " + notes) if notes and notes.strip() else ""
            msg = (
                dom_mention + "🚨 *Case Escalated* — Documentation\n"
                "Driver: " + str(item["driver_name"]) + " (" + str(item["driver_id"]) + ")\n"
                "Contact: " + str(item["contact_number"]) + "\n"
                "USC: " + fmt_val(item["usc_name"]) + "\n"
                "DOM: " + item["dom"] + "\n"
                "Invoice: " + current_doc_values.get("🧾 Invoice", "Not Received") + "\n"
                "Number Plate: " + current_doc_values.get("🔢 Number Plate", "Not Received") + "\n"
                "Insurance: " + current_doc_values.get("🛡️ Insurance", "Not Received") + "\n"
                "Not Received: " + missing_text
                + issue_line
            )
            sent, ts, err = send_slack_message(msg, driver_id=item["driver_id"], source="Docs Tracker", include_button=True)
            if sent and ts:
                save_updates(sheet, df, item["sheet_row"], {"Slack_Message_Ts": ts})
            st.session_state["last_slack_result"] = (sent, err, item["driver_name"])
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
            stage_tag = (" [" + item["stage_label"] + "]") if "stage_label" in item else ""
            label = item["driver_name"] + stage_tag + "  (" + str(item["driver_id"]) + ")"
            btn_type = "primary" if idx == st.session_state[selected_key] else "secondary"
            row_key = key_prefix + "_btn_" + str(item["sheet_row"]) + "_" + str(item.get("call_num", 0))
            if st.button(label, key=row_key, use_container_width=True, type=btn_type):
                st.session_state[selected_key] = idx

    with detail_col:
        item = filtered[st.session_state[selected_key]]
        unique_key = key_prefix + "_" + str(item["sheet_row"]) + "_" + str(item.get("call_num", 0))
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
        docs_line = ""
        if e["source"] == "Docs Tracker":
            docs_line = (
                "<br>🧾 Invoice: <b>" + e.get("invoice_status", "Not Received") + "</b>"
                " &nbsp;|&nbsp; 🔢 Number Plate: <b>" + e.get("number_plate_status", "Not Received") + "</b>"
                " &nbsp;|&nbsp; 🛡️ Insurance: <b>" + e.get("insurance_status", "Not Received") + "</b>"
            )
        card_html = "<div class='escalation-card'><b>" + str(e["driver_name"]) + "</b> (" + str(e["driver_id"]) + ") &nbsp;|&nbsp; " + e["source"] + " &nbsp;|&nbsp; USC: " + fmt_val(e["usc_name"]) + " &nbsp;|&nbsp; DOM: <b>" + e["dom"] + "</b><br>Contact: " + str(e["contact_number"]) + docs_line + "<br>Notes: " + str(e["notes"]) + "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        resolution_key = "resolution_note_" + e["source"] + "_" + str(e["sheet_row"])
        resolution_note = st.text_input("Resolution notes (optional)", key=resolution_key, placeholder="What was done to fix this?")

        resolve_key = "resolve_" + e["source"] + "_" + str(e["sheet_row"])
        if st.button("Mark Resolved", key=resolve_key):
            target_sheet = call_sheet if e["source"] == "Onboarding Call" else docs_sheet
            target_df = call_df if e["source"] == "Onboarding Call" else docs_df

            resolved_updates = {"Escalation_Status": "Resolved"}
            reset_col = e.get("escalated_status_col")
            if reset_col:
                reset_value = "Call Attempted" if e["source"] == "Onboarding Call" else "Documents Received"
                resolved_updates[reset_col] = reset_value

            save_updates(target_sheet, target_df, e["sheet_row"], resolved_updates)

            resolve_msg = "✅ *Case Resolved* — " + e["source"] + "\nDriver: " + str(e["driver_name"]) + " (" + str(e["driver_id"]) + ")\nDOM: " + e["dom"]
            if resolution_note and resolution_note.strip():
                resolve_msg += "\nResolution: " + resolution_note
            thread_ts = e.get("slack_ts") or None
            if thread_ts:
                sent, _, err = send_slack_message(resolve_msg, thread_ts=thread_ts)
            else:
                sent, err = send_slack_alert(resolve_msg)
            st.session_state["last_slack_result"] = (sent, err, e["driver_name"] + " (resolved)")
            st.rerun()
        st.write("")


def render_dashboard_stage(items, status_options):
    total = len(items)
    counts = {}
    for opt in status_options:
        counts[opt] = 0
    for item in items:
        s = item["status"]
        if s not in counts:
            counts[s] = 0
        counts[s] += 1

    pending = counts.get("Pending", 0)
    attempted = counts.get("Call Attempted", 0) + counts.get("Documents Received", 0)
    escalated = counts.get("Escalated to DOM", 0)
    followup = counts.get("Follow-up Needed", 0)

    cols = st.columns(4)
    with cols[0]:
        render_metric("Total Due", total)
    with cols[1]:
        render_metric("Pending", pending)
    with cols[2]:
        render_metric("Completed", attempted)
    with cols[3]:
        render_metric("Escalated", escalated)

    if total == 0:
        st.caption("Nobody in this list today.")
        return

    st.write("")
    status_filter_options = ["All"] + sorted(set(item["status"] for item in items))
    chosen_status = st.selectbox("Filter by Call Status", status_filter_options, key="dash_status_filter_" + str(id(items)))
    filtered_items = items if chosen_status == "All" else [it for it in items if it["status"] == chosen_status]

    rows = []
    for g in filtered_items:
        call_result = g.get("call_result")
        display_status = call_result if call_result and call_result != "—" else g["status"]
        rows.append({
            "Driver Name": str(g["driver_name"]),
            "Driver ID": str(g["driver_id"]),
            "Contact Number": str(g["contact_number"]),
            "USC": fmt_val(g["usc_name"]),
            "Call Status": display_status,
        })

    table_html = "<table class='bs-table'><thead><tr>"
    for col_name in ["Driver Name", "Driver ID", "Contact Number", "USC", "Call Status"]:
        table_html += "<th>" + col_name + "</th>"
    table_html += "</tr></thead><tbody>"
    for row in rows:
        table_html += "<tr>"
        table_html += "<td>" + row["Driver Name"] + "</td>"
        table_html += "<td>" + row["Driver ID"] + "</td>"
        table_html += "<td>" + row["Contact Number"] + "</td>"
        table_html += "<td>" + row["USC"] + "</td>"
        status_class = "status-pill " + row["Call Status"].replace(" ", "-").lower()
        table_html += "<td><span class='" + status_class + "'>" + row["Call Status"] + "</span></td>"
        table_html += "</tr>"
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)


def main():
    title_html = "<h1>" + LOGO_SVG + "Battery Smart</h1>"
    st.markdown(title_html, unsafe_allow_html=True)
    st.caption("Onboarding Call Tracker & Documentation Tracker")

    if "last_slack_result" in st.session_state:
        sent, err, driver_name = st.session_state.pop("last_slack_result")
        if sent and not err:
            st.success(driver_name + " — posted to Slack!")
        elif sent and err:
            st.warning(driver_name + " — posted to Slack, but with a note: " + err)
        else:
            st.error(driver_name + " — Slack post FAILED: " + err)

    call_sheet = get_call_sheet()
    docs_sheet = get_docs_sheet()
    call_df = load_call_data(call_sheet)
    docs_df = load_docs_data(docs_sheet)

    call_due = build_call_due_list(call_df)
    docs_due = build_docs_due_list(docs_df)
    escalations = build_escalations(call_df, docs_df)

    with st.sidebar:
        sidebar_logo_html = "<div class='sidebar-brand-box' style='display:flex;align-items:center;gap:10px;'>" + LOGO_SVG + "<span style='font-weight:800;font-size:1.25rem;letter-spacing:0.2px;'>Battery Smart</span></div>"
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

        if st.button("🔧 Test Slack Connection", use_container_width=True):
            test_msg = "🔧 Test message from Battery Smart app — sent at " + today_ist().strftime("%d/%m/%Y") + " IST. If you see this, Slack is working."
            token_set = bool(st.secrets.get("slack_bot_token", ""))
            channel_set = bool(st.secrets.get("slack_channel_id", ""))
            webhook_set = bool(st.secrets.get("slack_webhook_url", ""))
            st.caption("Bot token in secrets: " + ("✅" if token_set else "❌ missing"))
            st.caption("Channel ID in secrets: " + ("✅" if channel_set else "❌ missing"))
            st.caption("Webhook URL in secrets (fallback): " + ("✅" if webhook_set else "❌ missing"))
            sent, ts, err = send_slack_message(test_msg)
            if sent and not err:
                st.success("Slack is working! Message posted via Bot Token.")
            elif sent and err:
                st.warning("Message got through, but: " + err)
            else:
                st.error("Slack test FAILED: " + err)

    if view == "📞 Onboarding Call Tracker":
        with st.expander("✏️ Search & edit any record (past calls, wrong result, callback later, etc.)"):
            edit_search = st.text_input("🔍 Search by driver name or ID", key="edit_search_call", placeholder="Type a name or Driver ID...")
            if edit_search and edit_search.strip():
                term = edit_search.strip().lower()
                all_records = build_call_all_records(call_df)
                matches = [r for r in all_records if term in str(r["driver_name"]).lower() or term in str(r["driver_id"]).lower()]
                if not matches:
                    st.warning("No matching records found.")
                else:
                    labels = [
                        r["driver_name"] + " — " + r["stage_label"] + " (" + str(r["driver_id"]) + ") — currently: " + r["current_status"]
                        for r in matches
                    ]
                    chosen_idx = st.selectbox("Select the exact record to edit", range(len(matches)), format_func=lambda i: labels[i], key="edit_pick_call")
                    chosen = matches[chosen_idx]
                    edit_key = "edit_call_" + str(chosen["sheet_row"]) + "_" + str(chosen["call_num"])
                    render_call_detail(chosen, call_sheet, call_df, edit_key)

        render_generic_tab(call_due, call_sheet, call_df, "call", render_call_detail)
    elif view == "📄 Documentation Tracker":
        with st.expander("✏️ Search & edit any record (document arrived late, wrong entry, etc.)"):
            edit_search_docs = st.text_input("🔍 Search by driver name or ID", key="edit_search_docs", placeholder="Type a name or Driver ID...")
            if edit_search_docs and edit_search_docs.strip():
                term = edit_search_docs.strip().lower()
                all_docs_records = build_docs_all_records(docs_df)
                matches = [r for r in all_docs_records if term in str(r["driver_name"]).lower() or term in str(r["driver_id"]).lower()]
                if not matches:
                    st.warning("No matching records found.")
                else:
                    labels = [
                        r["driver_name"] + " (" + str(r["driver_id"]) + ") — currently: " + r["current_status"]
                        for r in matches
                    ]
                    chosen_idx = st.selectbox("Select the exact record to edit", range(len(matches)), format_func=lambda i: labels[i], key="edit_pick_docs")
                    chosen = matches[chosen_idx]
                    edit_key = "edit_docs_" + str(chosen["sheet_row"])
                    render_docs_detail(chosen, docs_sheet, docs_df, edit_key)

        render_generic_tab(docs_due, docs_sheet, docs_df, "docs", render_docs_detail)
    elif view == "🚨 Escalations":
        render_escalations_panel(call_sheet, call_df, docs_sheet, docs_df)
    elif view == "📊 Dashboard":
        call_today_all = build_call_today_all(call_df)
        docs_today_all = build_docs_today_all(docs_df)
        dash_tab1, dash_tab2 = st.tabs(["Onboarding Call Tracker", "Documentation Tracker"])
        with dash_tab1:
            render_dashboard_stage(call_today_all, CALL_STATUS_OPTIONS)
        with dash_tab2:
            render_dashboard_stage(docs_today_all, DOCS_STATUS_OPTIONS)


if __name__ == "__main__":
    main()

