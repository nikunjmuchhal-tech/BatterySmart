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
DFE_OPTIONS = ["Not Checked", "Yes", "No"]

STATUS_COLOR = {
    "Pending": "#6b7280",
    "Connected": "#16a34a",
    "Not Connected": "#eab308",
    "Incoming Not Available": "#dc2626",
    "FollowUp Scheduled": "#2563eb",
}

st.markdown("<style>h1 { font-size: 2.4rem !important; } .stTabs [data-baseweb='tab'] { font-size: 1.2rem !important; padding: 10px 18px !important; } .stTabs [data-baseweb='tab-list'] { gap: 8px; } div[data-testid='stMarkdownContainer'] p { font-size: 1.05rem; } .detail-name { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; } .detail-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; } .detail-value { font-size: 1.15rem; margin-bottom: 10px; } .metric-box { background:#1e293b; border-radius:12px; padding:20px; text-align:center; } .metric-num { font-size:2.2rem; font-weight:800; } .metric-label { font-size:0.9rem; color:#94a3b8; text-transform:uppercase; }</style>", unsafe_allow_html=True)


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


def render_detail(item, sheet, df, unique_key):
    name_html = "<div class='detail-name'>" + str(item['driver_name']) + "</div>"
    st.markdown(name_html, unsafe_allow_html=True)

    id_html = "<div class='detail-label'>Driver ID</div><div class='detail-value'>" + str(item['driver_id']) + "</div>"
    st.markdown(id_html, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        contact_html = "<div class='detail-label'>Contact Number</div><div class='detail-value'>" + str(item['contact_number']) + "</div>"
        st.markdown(contact_html, unsafe_allow_html=True)

        zone_html = "<div class='detail-label'>Zone</div><div class='detail-value'>" + str(item['zone']) + "</div>"
        st.markdown(zone_html, unsafe_allow_html=True)

        onboard_html = "<div class='detail-label'>Onboarding Date</div><div class='detail-value'>" + str(item['onboarding_date']) + "</div>"
        st.markdown(onboard_html, unsafe_allow_html=True)

        dealer_html = "<div class='detail-label'>Dealership</div><div class='detail-value'>" + str(item['dealership']) + "</div>"
        st.markdown(dealer_html, unsafe_allow_html=True)

    with c2:
        vehicle_html = "<div class='detail-label'>Vehicle</div><div class='detail-value'>" + str(item['vehicle_model']) + "</div>"
        st.markdown(vehicle_html, unsafe_allow_html=True)

        price_html = "<div class='detail-label'>Vehicle Price / Amount Paid</div><div class='detail-value'>Rs " + str(item['total_signup_amount']) + " / Rs " + str(item['amount_paid']) + "</div>"
        st.markdown(price_html, unsafe_allow_html=True)

        plan_html = "<div class='detail-label'>Plan Amount (EMI/Subscription)</div><div class='detail-value'>Rs " + str(item['plan_amount']) + "</div>"
        st.markdown(plan_html, unsafe_allow_html=True)

    usc_html = "<div class='detail-label'>USC ID (Onboarding Agent)</div><div class='detail-value'>" + str(item['usc_id']) + "</div>"
    st.markdown(usc_html, unsafe_allow_html=True)

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

    status = st.selectbox("Outcome", STATUS_OPTIONS, index=default_idx, key=status_key)
    notes = st.text_input("Call notes", value=item["current_notes"], key=notes_key)

    dfe_value = None
    dfe_amount_value = ""
    if item["stage"] == "D+1":
        dfe_key = "dfe_" + unique_key
        dfe_default_idx = 0
        if item["dfe_status"] in DFE_OPTIONS:
            dfe_default_idx = DFE_OPTIONS.index(item["dfe_status"])
        dfe_value = st.selectbox("Did the DFE/dealer ask the driver to pay any fees?", DFE_OPTIONS, index=dfe_default_idx, key=dfe_key)

        if dfe_value == "Yes":
            dfe_amount_key = "dfeamt_" + unique_key
            existing_amount = str(item["dfe_amount"]) if item["dfe_amount"] else ""
            dfe_amount_value = st.text_input("How much did they ask for? (Rs)", value=existing_amount, key=dfe_amount_key)

    save_key = "save_" + unique_key
    if st.button("Save", key=save_key):
        errors = []
        if status == "Pending":
            errors.append("Please select an actual call Outcome (not Pending).")
        if not notes or not notes.strip():
            errors.append("Please enter Call notes before saving.")
        if item["stage"] == "D+1" and dfe_value == "Not Checked":
            errors.append("Please answer the DFE fees question before saving.")
        if item["stage"] == "D+1" and dfe_value == "Yes" and (not dfe_amount_value or not dfe_amount_value.strip()):
            errors.append("Please enter the fee amount asked, since you selected Yes.")

        if errors:
            for e in errors:
                st.warning(e)
        else:
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

    param_name = key_prefix + "_sel"
    selected_idx = 0
    if param_name in st.query_params:
        try:
            selected_idx = int(st.query_params[param_name])
        except Exception:
            selected_idx = 0
    if selected_idx >= len(items):
        selected_idx = 0

    list_col, detail_col = st.columns([1, 2])

    with list_col:
        links_html = ""
        for idx, item in enumerate(items):
            color = STATUS_COLOR.get(item["current_status"], "#6b7280")
            is_selected = (idx == selected_idx)
            if is_selected:
                border = "3px solid white"
            else:
                border = "3px solid transparent"
            label = item["driver_name"] + " (" + str(item["driver_id"]) + ")"
            link = "<a href='?" + param_name + "=" + str(idx) + "' target='_self' style='display:block;background:" + color + ";color:white;padding:12px 14px;border-radius:8px;margin-bottom:8px;text-decoration:none;font-weight:600;font-size:1.05rem;border:" + border + ";'>" + label + "</a>"
            links_html = links_html + link
        st.markdown(links_html, unsafe_allow_html=True)

    with detail_col:
        item = items[selected_idx]
        unique_key = key_prefix + "_" + str(item["sheet_row"])
        render_detail(item, sheet, df, unique_key)


def render_metric(label, value):
    html = "<div class='metric-box'><div class='metric-num'>" + str(value) + "</div><div class='metric-label'>" + label + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def show_table(df_table):
    st.dataframe(
        df_table,
        use_container_width=False,
        hide_index=True,
        column_config={
            "Driver Name": st.column_config.TextColumn(width="medium"),
            "Driver ID": st.column_config.TextColumn(width="small"),
            "Contact Number": st.column_config.TextColumn(width="small"),
            "USC ID": st.column_config.TextColumn(width="small"),
            "Fee Amount": st.column_config.TextColumn(width="small"),
        },
    )


def render_dashboard_stage(stage_name, items):
    st.subheader(stage_name)

    total = len(items)
    counts = {}
    for opt in STATUS_OPTIONS:
        counts[opt] = []
    for item in items:
        status = item["current_status"]
        if status not in counts:
            counts[status] = []
        counts[status].append(item)

    connected = len(counts.get("Connected", []))
    pending = len(counts.get("Pending", []))
    not_connected = len(counts.get("Not Connected", []))
    incoming_na = len(counts.get("Incoming Not Available", []))
    followup = len(counts.get("FollowUp Scheduled", []))
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

    for status_name in STATUS_OPTIONS:
        group = counts.get(status_name, [])
        label = status_name + " (" + str(len(group)) + ")"
        with st.expander(label):
            if not group:
                st.caption("Nobody in this category.")
            else:
                rows = []
                for g in group:
                    rows.append({
                        "Driver Name": str(g["driver_name"]),
                        "Driver ID": str(g["driver_id"]),
                        "Contact Number": str(g["contact_number"]),
                        "USC ID": str(g["usc_id"]),
                    })
                show_table(pd.DataFrame(rows))

    if stage_name == "D+1 Calls":
        st.markdown("**DFE Fees Asked Breakdown**")
        dfe_groups = {}
        for opt in DFE_OPTIONS:
            dfe_groups[opt] = []
        for item in items:
            dfe_val = item["dfe_status"]
            if dfe_val not in dfe_groups:
                dfe_groups[dfe_val] = []
            dfe_groups[dfe_val].append(item)

        dfe_cols = st.columns(3)
        with dfe_cols[0]:
            render_metric("Not Checked", len(dfe_groups.get("Not Checked", [])))
        with dfe_cols[1]:
            render_metric("Yes (Fees Asked)", len(dfe_groups.get("Yes", [])))
        with dfe_cols[2]:
            render_metric("No (Not Asked)", len(dfe_groups.get("No", [])))

        for dfe_name in DFE_OPTIONS:
            group = dfe_groups.get(dfe_name, [])
            label = "DFE: " + dfe_name + " (" + str(len(group)) + ")"
            with st.expander(label):
                if not group:
                    st.caption("Nobody in this category.")
                else:
                    rows = []
                    for g in group:
                        rows.append({
                            "Driver Name": str(g["driver_name"]),
                            "Driver ID": str(g["driver_id"]),
                            "Contact Number": str(g["contact_number"]),
                            "USC ID": str(g["usc_id"]),
                            "Fee Amount": str(g["dfe_amount"]),
                        })
                    show_table(pd.DataFrame(rows))

    if pending == 0 and total > 0:
        st.success(stage_name + " is fully done for today!")
    elif total > 0:
        st.warning(str(pending) + " driver(s) still pending for " + stage_name)


def main():
    st.title("📞 Battery Smart — Onboarding Calls")
    st.caption("Financed (L5) drivers — D+1 / D+2 welcome calls")

    if not check_password():
        return

    sheet = get_sheet()
    df = load_data(sheet)
    d1_list, d2_list = build_lists(df)

    view = st.radio("View", ["📞 Calling Sheet", "📊 Manager Dashboard"], horizontal=True, label_visibility="collapsed")

    st.divider()

    if view == "📞 Calling Sheet":
        tab1_label = "🟢 D+1 Calls (" + str(len(d1_list)) + ")"
        tab2_label = "🟠 D+2 Calls (" + str(len(d2_list)) + ")"
        tab1, tab2 = st.tabs([tab1_label, tab2_label])

        with tab1:
            render_tab(d1_list, sheet, df, "d1")

        with tab2:
            render_tab(d2_list, sheet, df, "d2")
    else:
        render_dashboard_stage("D+1 Calls", d1_list)
        st.divider()
        render_dashboard_stage("D+2 Calls", d2_list)
        st.divider()
        if st.button("🔄 Refresh Now"):
            load_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
