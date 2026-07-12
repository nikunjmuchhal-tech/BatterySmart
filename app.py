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
    ".stTabs [data-baseweb='tab'] { font-size: 1.05rem !important; padding: 8px 16px !important; }"
    ".stTabs [data-baseweb='tab-list'] { gap: 6px; }"
    ".stTabs [aria-selected='true'] { color: " + BRAND_GREEN + " !important; }"
    "div[data-testid='stMarkdownContainer'] p { font-size: 1.0rem; }"
    ".detail-name { font-size: 1.4rem; font-weight: 700; margin-bottom: 2px; color:" + BRAND_NAVY + "; }"
    ".detail-sub { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }"
    ".detail-label { font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }"
    ".detail-value { font-size: 1.0rem; margin-bottom: 8px; color: #111827; font-weight: 500; }"
    ".call-link { display:inline-block; background:" + BRAND_GREEN + "; color: #ffffff !important; padding:6px 14px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.95rem; }"
    ".metric-box { background: linear-gradient(135deg, " + BRAND_NAVY + " 0%, #2a2496 100%); border-radius:14px; padding:16px 8px; text-align:center; box-shadow: 0 3px 10px rgba(21,18,114,0.18); }"
    ".metric-num { font-size:1.8rem; font-weight:800; color: white; }"
    ".metric-label { font-size:0.72rem; color:" + BRAND_GREEN + "; text-transform:uppercase; letter-spacing:0.4px; }"
    "div.stButton > button[kind='primary'] { background-color: " + BRAND_GREEN + "; border-color: " + BRAND_GREEN + "; }"
    "div.stButton > button { border-radius: 10px; }"
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
        dfe_status = row.get("DFE_Fees_Asked", "Not Checked") or "Not Checked"
        dfe_amount = row.get("DFE_Fee_Amount", "")

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
        base["dfe_status"] = dfe_status
        base["dfe_amount"] = dfe_amount
        base["usc_id"] = row.get("USC_ID")

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


def save_call(sheet, df, sheet_row, updates):
    header = df.columns.tolist()
    batch = []
    for col_name in updates:
        col_idx = header.index(col_name) + 1
        cell_range = gspread.utils.rowcol_to_a1(sheet_row, col_idx)
        batch.append({"range": cell_range, "values": [[updates[col_name]]]})
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
        name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div><div class='detail-sub'>Driver ID: " + str(item['driver_id']) + " &nbsp;|&nbsp; USC ID: " + fmt_val(item['usc_id']) + "</div>"
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
        notes = st.text_input("Call notes (optional)", value=item["current_notes"], key=notes_key)

    dfe_value = None
    dfe_amount_value = ""
    if item["stage"] == "D+1":
        dfe_key = "dfe_" + unique_key
        dfe_default_idx = 0
        if item["dfe_status"] in DFE_OPTIONS:
            dfe_default_idx = DFE_OPTIONS.index(item["dfe_status"])

        col_c, col_d = st.columns(2)
        with col_c:
            dfe_value = st.selectbox("DFE/dealer asked for fees? (optional)", DFE_OPTIONS, index=dfe_default_idx, key=dfe_key)
        if dfe_value == "Yes":
            with col_d:
                dfe_amount_key = "dfeamt_" + unique_key
                existing_amount = str(item["dfe_amount"]) if item["dfe_amount"] else ""
                dfe_amount_value = st.text_input("Fee amount asked (Rs)", value=existing_amount, key=dfe_amount_key)

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
    html = "<div class='metric-box'><div class='metric-num'>" + str(value) + "</div><div class='metric-label'>" + label + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_dashboard_stage(items):
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
            st.bar_chart(chart_df.set_index("Status"))
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
        if "dfe_status" in g:
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


LOGO_SVG = "<svg width='34' height='34' viewBox='0 0 300 470' style='vertical-align:middle; margin-right:10px;'><rect x='95' y='0' width='110' height='45' rx='8' fill='#00C389'/><path d='M20 65 C5 65 0 80 10 92 L140 240 L10 388 C0 400 5 415 20 415 L280 415 C295 415 300 400 290 388 L160 240 L290 92 C300 80 295 65 280 65 Z M100 130 L200 130 L150 190 Z M100 350 L200 350 L150 290 Z' fill='#00C389'/></svg>"

def main():
    title_html = "<h1>" + LOGO_SVG + "Battery Smart — Onboarding Calls</h1>"
    st.markdown(title_html, unsafe_allow_html=True)
    st.caption("Financed (L5) drivers — D+1 / D+2 welcome calls")

    if not check_password():
        return

    sheet = get_sheet()
    df = load_data(sheet)
    d1_list, d2_list = build_lists(df)

    with st.sidebar:
        sidebar_logo_html = "<div style='display:flex;align-items:center;gap:8px;'>" + LOGO_SVG + "<span style='font-weight:700;font-size:1.1rem;'>Battery Smart</span></div>"
        st.markdown(sidebar_logo_html, unsafe_allow_html=True)
        view = st.radio("View", ["📞 Calling Sheet", "📊 Manager Dashboard"], label_visibility="collapsed")
        st.divider()
        st.caption("D+1 due today: " + str(len(d1_list)))
        st.caption("D+2 due today: " + str(len(d2_list)))
        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            load_data.clear()
            st.rerun()

    if view == "📞 Calling Sheet":
        tab1_label = "🟢 D+1 Calls (" + str(len(d1_list)) + ")"
        tab2_label = "🟠 D+2 Calls (" + str(len(d2_list)) + ")"
        tab1, tab2 = st.tabs([tab1_label, tab2_label])

        with tab1:
            render_tab(d1_list, sheet, df, "d1")

        with tab2:
            render_tab(d2_list, sheet, df, "d2")
    else:
        dash_tab1, dash_tab2 = st.tabs(["D+1 Calls", "D+2 Calls"])
        with dash_tab1:
            render_dashboard_stage(d1_list)
        with dash_tab2:
            render_dashboard_stage(d2_list)


if __name__ == "__main__":
    main()
