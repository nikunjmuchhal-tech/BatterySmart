import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def today_ist():
    return datetime.now(IST).date()
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Battery Smart - Onboarding Calls", layout="centered")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_TAB = "Call Logs"

D1_SCRIPT = "Hello {name}, welcome to Battery Smart! This is a courtesy call to confirm you're settling in well. Any questions about onboarding, your plan, or the app?"
D2_SCRIPT = "Hello {name}, following up — how has your experience been? Started using the vehicle regularly? Any issues with the battery or swap process?"

STATUS_OPTIONS = ["Pending", "Connected", "Not Connected", "Incoming Not Available", "FollowUp Scheduled"]


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
    df = pd.DataFrame(records)
    return df


def parse_date(val):
    if not val:
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def build_queue(df):
    today = today_ist()
    rows = []

    for i, row in df.iterrows():
        sheet_row = i + 2  # header is row 1

        d1_date = parse_date(row.get("D1_Due_Date"))
        d2_date = parse_date(row.get("D2_Due_Date"))
        d1_status = row.get("D1_Status", "Pending")
        d2_status = row.get("D2_Status", "Pending")

        if d1_date and d1_date <= today and d1_status != "Connected":
            overdue = (today - d1_date).days
            rows.append({
                "sheet_row": sheet_row, "stage": "D+1",
                "driver_id": row.get("Driver_ID"), "driver_name": row.get("Driver_Name"),
                "zone": row.get("Zone"), "onboarding_date": row.get("Onboarding_Date"),
                "due_date": d1_date, "overdue_days": overdue,
                "status_col": "D1_Status", "notes_col": "D1_Notes",
                "current_status": d1_status, "current_notes": row.get("D1_Notes", ""),
                "script": D1_SCRIPT.format(name=row.get("Driver_Name")),
            })

        if d2_date and d2_date <= today and d2_status != "Connected":
            overdue = (today - d2_date).days
            rows.append({
                "sheet_row": sheet_row, "stage": "D+2",
                "driver_id": row.get("Driver_ID"), "driver_name": row.get("Driver_Name"),
                "zone": row.get("Zone"), "onboarding_date": row.get("Onboarding_Date"),
                "due_date": d2_date, "overdue_days": overdue,
                "status_col": "D2_Status", "notes_col": "D2_Notes",
                "current_status": d2_status, "current_notes": row.get("D2_Notes", ""),
                "script": D2_SCRIPT.format(name=row.get("Driver_Name")),
            })

    rows.sort(key=lambda r: (-r["overdue_days"]))
    return rows


def save_update(sheet, df, sheet_row, status_col, notes_col, status, notes):
    header = df.columns.tolist()
    status_col_idx = header.index(status_col) + 1
    notes_col_idx = header.index(notes_col) + 1
    sheet.update_cell(sheet_row, status_col_idx, status)
    sheet.update_cell(sheet_row, notes_col_idx, notes)


def main():
    st.title("📞 Battery Smart — Onboarding Calls")
    st.caption("Financed (L5) drivers — D+1 / D+2 welcome calls")

    if not check_password():
        return

    sheet = get_sheet()
    df = load_data(sheet)
    queue = build_queue(df)

    if not queue:
        st.success("No calls due right now. Nice work!")
        return

    st.write(f"**{len(queue)} call(s) due**")

    for item in queue:
        badge = "🟢 D+1" if item["stage"] == "D+1" else "🟠 D+2"
        overdue_label = "" if item["overdue_days"] == 0 else f"  ⏰ {item['overdue_days']}d overdue"
        label = f"{badge} — {item['driver_name']} ({item['driver_id']}){overdue_label}"

        with st.expander(label):
            st.write(f"**Zone:** {item['zone']}  |  **Onboarded:** {item['onboarding_date']}  |  **Due:** {item['due_date']}")
            st.info(f"**Script:** {item['script']}")

            if item["current_notes"]:
                st.caption(f"Previous notes: {item['current_notes']}")

            status_key = f"status_{item['sheet_row']}_{item['stage']}"
            notes_key = f"notes_{item['sheet_row']}_{item['stage']}"

            default_idx = STATUS_OPTIONS.index(item["current_status"]) if item["current_status"] in STATUS_OPTIONS else 0
            status = st.selectbox("Outcome", STATUS_OPTIONS, index=default_idx, key=status_key)
            notes = st.text_input("Call notes", value=item["current_notes"], key=notes_key)

            if st.button("Save", key=f"save_{item['sheet_row']}_{item['stage']}"):
                save_update(sheet, df, item["sheet_row"], item["status_col"], item["notes_col"], status, notes)
                st.cache_resource.clear()
                st.success("Saved!")
                st.rerun()


if __name__ == "__main__":
    main()
