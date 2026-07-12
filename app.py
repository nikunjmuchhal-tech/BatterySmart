import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
def today_ist():
    return datetime.now(IST).date()
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Battery Smart - Onboarding Calls", layout="wide", initial_sidebar_state="expanded")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_TAB = "Call Logs"

MAX_STAGE = 7

STAGE_SCRIPTS = {
    1: "Hello {name}, welcome to Battery Smart! This is a courtesy call to confirm you're settling in well. Any questions about onboarding, your plan, or the app?",
    2: "Hello {name}, following up — how has your experience been? Started using the vehicle regularly? Any issues with the battery or swap process?",
}
DEFAULT_SCRIPT = "Hello {name}, this is a scheduled follow-up call from Battery Smart. Checking in on how things are going and if you need any help."

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

METRIC_ICONS = {
    "Total Due": "📋",
    "Attempted": "☎️",
    "Connected": "✅",
    "Not Connected": "🕗",
    "No Incoming": "🚫",
    "Follow-up": "🔁",
}

LOGO_SVG = "<svg width='46' height='46' viewBox='0 0 300 470' style='vertical-align:middle; margin-right:12px;'><rect x='95' y='0' width='110' height='45' rx='8' fill='#00C389'/><path d='M20 65 C5 65 0 80 10 92 L140 240 L10 388 C0 400 5 415 20 415 L280 415 C295 415 300 400 290 388 L160 240 L290 92 C300 80 295 65 280 65 Z M100 130 L200 130 L150 190 Z M100 350 L200 350 L150 290 Z' fill='#00C389'/></svg>"

st.markdown(
    "<style>"
    "[data-testid='stAppViewContainer'] { background: linear-gradient(160deg, #f0fffa 0%, #ffffff 30%, #f1f2ff 100%); }"
    "[data-testid='stHeader'] { background: rgba(0,0,0,0); }"
    "[data-testid='stSidebar'] { background: linear-gradient(180deg, " + BRAND_NAVY + " 0%, #23197a 100%); min-width: 300px !important; }"
    "[data-testid='stSidebar'] * { color: #ffffff !important; }"
    "[data-testid='stSidebar'] .block-container { padding-top: 2rem; }"
    "[data-testid='stSidebar'] .stRadio label { font-size: 1.15rem !important; font-weight: 600; padding: 6px 0; }"
    "[data-testid='stSidebar'] .stRadio div[role='radiogroup'] { gap: 10px; }"
    "[data-testid='stSidebar'] div[data-testid='stMarkdownContainer'] p { font-size: 1.05rem !important; }"
    "[data-testid='stSidebar'] div[data-testid='stCaptionContainer'] p { font-size: 1.1rem !important; color: #d7d5ff !important; font-weight: 500; }"
    "[data-testid='stSidebar'] hr { border-color: rgba(255,255,255,0.15); margin: 18px 0; }"
    "[data-testid='stSidebar'] div.stButton > button { font-size: 1.05rem !important; padding: 10px 0 !important; }"
    ".sidebar-stat-box { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }"
    ".sidebar-stat-num { font-size: 1.6rem; font-weight: 800; color: " + BRAND_GREEN + "; }"
    ".sidebar-stat-label { font-size: 0.85rem; color: #d7d5ff; text-transform: uppercase; letter-spacing: 0.4px; }"
    "h1 { font-size: 2.4rem !important; color:" + BRAND_NAVY + " !important; font-weight: 800 !important; margin-bottom: 0px !important; }"
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
    ".metric-num { font-size:2.1rem; font-weight:800; color: white; line-height: 1.1; }"
    ".metric-label { font-size:0.78rem; color:" + BRAND_GREEN + "; text-transform:uppercase; letter-spacing:0.5px; margin-top: 4px; font-weight: 600; }"
    "div.stButton > button[kind='primary'] { background-color: " + BRAND_GREEN + "; border-color: " + BRAND_GREEN + "; font-weight: 600; }"
    "div.stButton > button { border-radius: 10px; font-weight: 500; }"
    "div.stButton > button[kind='secondary'] { border: 1px solid #e5e7eb; }"
    "[data-testid='stDataFrame'] { border-radius: 12px; overflow: hidden; border: 1px solid #e5e7eb; }"
    ".stProgress > div > div { background-color: " + BRAND_GREEN + " !important; }"
    "[data-testid='stTextInput'] input { background-color: #f9fafb !important; color: #111827 !important; border: 1px solid #d1d5db !important; }"
    "[data-testid='stTextInput'] input::placeholder { color: #9ca3af !important; }"
    "[data-baseweb='select'] > div { background-color: #f9fafb !important; color: #111827 !important; border: 1px solid #d1d5db !important; }"
    "[data-baseweb='select'] input { color: #111827 !important; }"
    "[data-baseweb='select'] span { color: #111827 !important; }"
    "ul[data-testid='stSelectboxVirtualDropdown'] { background-color: #ffffff !important; }"
    "ul[data-testid='stSelectboxVirtualDropdown'] li { color: #111827 !important; }"
    "li[role='option'] { color: #111827 !important; background-color: #ffffff !important; }"
    "li[role='option']:hover { background-color: #eafff6 !important; }"
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
def get_sheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
    return spreadsheet.worksheet(SHEET_TAB)


@st.cache_data(ttl=60)
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


def stage_status_col(n):
    if n == 1:
        return "D_1 Status"
    return "D_" + str(n) + "_Status"


def stage_date_col(n):
    return "D_" + str(n) + "_Date"


def stage_notes_col(n):
    return "D_" + str(n) + "_Notes"


def stage_script(n, name):
    template = STAGE_SCRIPTS.get(n, DEFAULT_SCRIPT)
    return template.format(name=name)


def build_all_stage_lists(df):
    today = today_ist()
    stage_lists = {}
    for n in range(1, MAX_STAGE + 1):
        stage_lists[n] = []

    for i, row in df.iterrows():
        sheet_row = i + 2

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
        base["dfe_status"] = row.get("DFE_Fees_Asked", "Not Checked") or "Not Checked"
        base["dfe_amount"] = row.get("DFE_Fee_Amount", "")
        base["usc_id"] = row.get("USC_ID")

        for n in range(1, MAX_STAGE + 1):
            due_date = parse_date(row.get(stage_date_col(n)))
            if due_date == today:
                item = dict(base)
                item["stage_num"] = n
                item["stage"] = "D+" + str(n)
                item["due_date"] = due_date
                item["status_col"] = stage_status_col(n)
                item["notes_col"] = stage_notes_col(n)
                item["current_status"] = row.get(stage_status_col(n), "Pending") or "Pending"
                item["current_notes"] = row.get(stage_notes_col(n), "")
                item["script"] = stage_script(n, row.get("Driver_Name"))
                stage_lists[n].append(item)

    return stage_lists


def save_call(sheet, df, sheet_row, updates):
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


def render_detail(item, sheet, df, unique_key):
    detail_box = st.container(border=True)
    with detail_box:
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC ID: " + fmt_val(item['usc_id']) + " &nbsp;|&nbsp; Stage: " + item["stage"] + "</div>"
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

            plan_html = "<div class='detail-label'>Plan Amount (EMI/Subscription)</div><div class='detail-value'>" + fmt_money(item['plan_amount']) + "</div>"
            st.markdown(plan_html, unsafe_allow_html=True)

    st.write("")

    script_text = "**Script:** " + item["script"]
    st.info(script_text)

    if item["current_notes"]:
        notes_caption = "Previous notes: " + str(item["current_notes"])
        st.caption(notes_caption)

    status_key = "status_" + unique_key
    notes_key = "notes_" + unique_key

    default_idx = 0
    if item["current_status"] in STATUS_OPTIONS:
        default_idx = STATUS_OPTIONS.index(item["current_status"])

    col_a, col_b = st.columns(2)
    with col_a:
        status = st.selectbox("Outcome", STATUS_OPTIONS, index=default_idx, key=status_key)
    with col_b:
        notes = st.text_input("Call notes", value=item["current_notes"], key=notes_key)

    dfe_value = None
    dfe_amount_value = ""
    if item["stage_num"] == 1:
        dfe_key = "dfe_" + unique_key
        dfe_default_idx = 0
        if item["dfe_status"] in DFE_OPTIONS:
            dfe_default_idx = DFE_OPTIONS.index(item["dfe_status"])

        col_c, col_d = st.columns(2)
        with col_c:
            dfe_value = st.selectbox("DFE/dealer asked for fees?", DFE_OPTIONS, index=dfe_default_idx, key=dfe_key)
        if dfe_value == "Yes":
            with col_d:
                dfe_amount_key = "dfeamt_" + unique_key
                existing_amount = str(item["dfe_amount"]) if item["dfe_amount"] else ""
                dfe_amount_value = st.text_input("Fee amount asked (Rs)", value=existing_amount, key=dfe_amount_key)

    if status == "FollowUp Scheduled" and item["stage_num"] < MAX_STAGE:
        next_n = item["stage_num"] + 1
        st.caption("This driver will automatically appear under D+" + str(next_n) + " tomorrow for the follow-up call.")

    save_key = "save_" + unique_key
    if st.button("💾 Save", key=save_key, type="primary", use_container_width=True):
        updates = {}
        updates[item["status_col"]] = status
        updates[item["notes_col"]] = notes
        if dfe_value is not None:
            updates["DFE_Fees_Asked"] = dfe_value
            if dfe_value == "Yes":
                updates["DFE_Fee_Amount"] = dfe_amount_value
            else:
                updates["DFE_Fee_Amount"] = ""

        if status == "FollowUp Scheduled" and item["stage_num"] < MAX_STAGE:
            next_n = item["stage_num"] + 1
            tomorrow = today_ist() + timedelta(days=1)
            updates[stage_date_col(next_n)] = tomorrow.strftime("%d/%m/%Y")
            updates[stage_status_col(next_n)] = "Pending"

        save_call(sheet, df, item["sheet_row"], updates)
        load_data.clear()
        st.success("Saved!")
        st.rerun()


def render_tab(items, sheet, df, key_prefix):
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
            dot = STATUS_DOT.get(item["current_status"], "⚪")
            label = dot + " " + item["driver_name"] + " (" + str(item["driver_id"]) + ")"
            btn_type = "primary" if idx == st.session_state[selected_key] else "secondary"
            if st.button(label, key=key_prefix + "_btn_" + str(item["sheet_row"]), use_container_width=True, type=btn_type):
                st.session_state[selected_key] = idx

    with detail_col:
        item = filtered[st.session_state[selected_key]]
        unique_key = key_prefix + "_" + str(item["sheet_row"])
        render_detail(item, sheet, df, unique_key)


def render_metric(label, value):
    icon = METRIC_ICONS.get(label, "")
    html = "<div class='metric-box'><div style='font-size:1.3rem;'>" + icon + "</div><div class='metric-num'>" + str(value) + "</div><div class='metric-label'>" + label + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_dashboard_stage(items, is_stage_1):
    total = len(items)
    counts = {}
    for opt in STATUS_OPTIONS:
        counts[opt] = 0
    for item in items:
        status = item["current_status"]
        if status not in counts:
            counts[status] = 0
        counts[status] += 1

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

    st.write("")

    if total > 0:
        progress = attempted / total
    else:
        progress = 0
    st.progress(progress, text=str(attempted) + " / " + str(total) + " attempted today")

    chart_col, table_col = st.columns([1, 2])

    with chart_col:
        chart_df = pd.DataFrame({
            "Status": list(counts.keys()),
            "Count": list(counts.values()),
        })
        chart_df = chart_df[chart_df["Count"] > 0]
        if not chart_df.empty:
            st.bar_chart(chart_df.set_index("Status"), color=BRAND_GREEN)
        else:
            st.caption("No data to chart yet.")

    all_rows = []
    for g in items:
        row = {
            "Driver Name": str(g["driver_name"]),
            "Driver ID": str(g["driver_id"]),
            "Contact Number": str(g["contact_number"]),
            "USC ID": str(g["usc_id"]),
            "Status": g["current_status"],
        }
        if is_stage_1:
            row["DFE Asked"] = g["dfe_status"]
            row["Fee Amount"] = str(g["dfe_amount"]) if g["dfe_amount"] else ""
        all_rows.append(row)

    with table_col:
        if all_rows:
            table_df = pd.DataFrame(all_rows)
            filter_options = ["All"] + STATUS_OPTIONS
            chosen = st.selectbox("Filter by status", filter_options, key="filter_" + str(id(items)))
            if chosen != "All":
                table_df = table_df[table_df["Status"] == chosen]
            st.dataframe(table_df, use_container_width=True, hide_index=True, height=min(360, 45 + 35 * len(table_df)))
        else:
            st.caption("Nobody in this list today.")

    if pending == 0 and total > 0:
        st.success("Fully done for today!")
    elif total > 0:
        st.warning(str(pending) + " driver(s) still pending")


def main():
    title_html = "<h1>" + LOGO_SVG + "Battery Smart — Onboarding Calls</h1>"
    st.markdown(title_html, unsafe_allow_html=True)
    st.caption("Financed (L5) drivers — D+1 through D+7 calling workflow")

    if not check_password():
        return

    sheet = get_sheet()
    df = load_data(sheet)
    stage_lists = build_all_stage_lists(df)

    active_stages = [1, 2]
    for n in range(3, MAX_STAGE + 1):
        if len(stage_lists[n]) > 0:
            active_stages.append(n)

    total_due_today = sum(len(stage_lists[n]) for n in range(1, MAX_STAGE + 1))

    with st.sidebar:
        sidebar_logo_html = "<div style='display:flex;align-items:center;gap:8px;'>" + LOGO_SVG + "<span style='font-weight:700;font-size:1.1rem;'>Battery Smart</span></div>"
        st.markdown(sidebar_logo_html, unsafe_allow_html=True)
        view = st.radio("View", ["📞 Calling Sheet", "📊 Manager Dashboard"], label_visibility="collapsed")
        st.divider()

        total_stat_html = "<div class='sidebar-stat-box'><div class='sidebar-stat-num'>" + str(total_due_today) + "</div><div class='sidebar-stat-label'>Total Due Today (All Stages)</div></div>"
        st.markdown(total_stat_html, unsafe_allow_html=True)

        for n in active_stages:
            stat_html = "<div class='sidebar-stat-box'><div class='sidebar-stat-num'>" + str(len(stage_lists[n])) + "</div><div class='sidebar-stat-label'>D+" + str(n) + " Due Today</div></div>"
            st.markdown(stat_html, unsafe_allow_html=True)

        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            load_data.clear()
            st.rerun()

    if view == "📞 Calling Sheet":
        tab_labels = []
        for n in active_stages:
            dot = "🟢" if n == 1 else ("🟠" if n == 2 else "🔵")
            tab_labels.append(dot + " D+" + str(n) + " (" + str(len(stage_lists[n])) + ")")

        tabs = st.tabs(tab_labels)
        for idx, n in enumerate(active_stages):
            with tabs[idx]:
                render_tab(stage_lists[n], sheet, df, "stage" + str(n))
    else:
        dash_labels = ["D+" + str(n) for n in active_stages]
        dash_tabs = st.tabs(dash_labels)
        for idx, n in enumerate(active_stages):
            with dash_tabs[idx]:
                render_dashboard_stage(stage_lists[n], n == 1)


if __name__ == "__main__":
    main()
