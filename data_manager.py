import pandas as pd
import json
import os
from datetime import datetime

DATA_DIR   = "data"
UPLOAD_DIR = "uploads"
APPS_FILE  = os.path.join(DATA_DIR, "applications.csv")
NOTIF_FILE = os.path.join(DATA_DIR, "notifications.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── No round-robin assignment — all officers see all apps ─────────────────────
def get_next_officer():
    return "All Officers"

# ── Applications ───────────────────────────────────────────────────────────────
# schools stored as JSON string: [{"university":"X","course":"Y","intake":"Z"}, ...]
COLS = [
    "app_id","student_name","student_email","student_phone",
    "schools",                          # NEW — JSON list of schools
    "counsellor_name","counsellor_email","counsellor_phone",
    "notes","documents","status","assigned_officer",
    "submitted_at","last_updated","officer_notes"
]

def load_applications():
    if os.path.exists(APPS_FILE):
        df = pd.read_csv(APPS_FILE, dtype=str)
        for c in COLS:
            if c not in df.columns:
                df[c] = ""
        # fill NaN with empty string — kills "nan"
        df = df.fillna("")
        return df[COLS]
    return pd.DataFrame(columns=COLS)

def save_application(app_data: dict):
    df  = load_applications()
    new = pd.DataFrame([{c: app_data.get(c, "") for c in COLS}])
    df  = pd.concat([df, new], ignore_index=True)
    df.to_csv(APPS_FILE, index=False)

def edit_application(app_id: str, updated_data: dict):
    df = load_applications()
    for col, val in updated_data.items():
        if col in df.columns:
            df.loc[df["app_id"] == app_id, col] = val
    df = df.fillna("")
    df.to_csv(APPS_FILE, index=False)

def update_application_status(app_id: str, new_status: str, officer_notes: str = ""):
    df   = load_applications()
    mask = df["app_id"] == app_id
    df.loc[mask, "status"]        = new_status
    df.loc[mask, "officer_notes"] = officer_notes if officer_notes else ""
    df.loc[mask, "last_updated"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
    df = df.fillna("")
    df.to_csv(APPS_FILE, index=False)

# ── Notifications ──────────────────────────────────────────────────────────────
def load_notifications():
    if os.path.exists(NOTIF_FILE):
        with open(NOTIF_FILE) as f:
            return json.load(f)
    return []

def save_notifications(notifs):
    with open(NOTIF_FILE, "w") as f:
        json.dump(notifs, f, indent=2)

def add_notification(notif: dict):
    notifs = load_notifications()
    notifs.insert(0, notif)
    save_notifications(notifs)

def mark_notifications_read_for_officer():
    notifs = load_notifications()
    for n in notifs:
        if n.get("recipient") == "ALL_OFFICERS":
            n["read"] = True
    save_notifications(notifs)

def mark_notification_read(recipient: str):
    notifs = load_notifications()
    for n in notifs:
        if n.get("recipient") == recipient:
            n["read"] = True
    save_notifications(notifs)

# ── File uploads ───────────────────────────────────────────────────────────────
def save_uploaded_file(app_id: str, uploaded_file) -> str:
    app_dir = os.path.join(UPLOAD_DIR, app_id)
    os.makedirs(app_dir, exist_ok=True)
    file_path = os.path.join(app_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return uploaded_file.name

def get_uploads_for_app(app_id: str):
    app_dir = os.path.join(UPLOAD_DIR, app_id)
    if os.path.exists(app_dir):
        return os.listdir(app_dir)
    return []

def get_stats():
    df = load_applications()
    if df.empty: return {}
    return {
        "total":      len(df),
        "not_checked":len(df[df["status"]=="Not Checked"]),
        "in_progress":len(df[df["status"]=="In Progress"]),
        "submitted":  len(df[df["status"]=="Submitted"]),
    }
