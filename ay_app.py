import streamlit as st
import pandas as pd
import os, base64, json, uuid
from datetime import datetime
from data_manager import (
    load_applications, save_application, update_application_status,
    edit_application, get_next_officer, load_notifications, add_notification,
    mark_notification_read, mark_notifications_read_for_officer,
    save_uploaded_file, get_uploads_for_app
)
df_schools = pd.read_csv("TGM PATNERS.csv")
PARTNER_SCHOOLS = df_schools["school_name"].tolist()
st.set_page_config(page_title="TGM AppHub", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif;}
.stApp{background:#0b1120;color:#e2e8f0;}
[data-testid="stSidebar"]{background:#0f1729!important;border-right:1px solid rgba(255,255,255,0.06);}
[data-testid="stSidebar"] *{color:#94a3b8!important;}
.stButton>button{background:linear-gradient(135deg,#3b82f6,#06b6d4);color:white!important;border:none;border-radius:8px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;padding:.5rem 1.2rem;transition:all .2s;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(59,130,246,.4);}
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div,.stNumberInput>div>div>input{background:#1a2236!important;border:1px solid rgba(255,255,255,.1)!important;border-radius:8px!important;color:#e2e8f0!important;font-family:'Plus Jakarta Sans',sans-serif!important;}
[data-testid="metric-container"]{background:#111827;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:1rem;}
.stTabs [data-baseweb="tab-list"]{background:#111827;border-radius:10px;gap:10px;padding:6px 10px;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;color:#64748b;font-weight:600;padding:8px 20px!important;font-size:.88rem;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#3b82f6,#06b6d4)!important;color:white!important;}
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;}
hr{border-color:rgba(255,255,255,.07);}
[data-testid="stFileUploader"]{background:#1a2236;border:2px dashed rgba(59,130,246,.4);border-radius:12px;}
.app-card{background:#111827;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:.8rem;transition:all .2s;}
.app-card:hover{border-color:rgba(59,130,246,.4);}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}
.badge-notchecked{background:rgba(245,158,11,.15);color:#f59e0b;}
.badge-progress{background:rgba(59,130,246,.15);color:#3b82f6;}
.badge-submitted{background:rgba(139,92,246,.15);color:#8b5cf6;}
.notif-card{background:#1a2236;border-left:3px solid #3b82f6;border-radius:0 10px 10px 0;padding:.8rem 1rem;margin-bottom:.6rem;cursor:pointer;}
.notif-unread{border-left-color:#06b6d4;background:#1e2d45;}
.school-block{background:#1a2236;border:1px solid rgba(59,130,246,.25);border-radius:10px;padding:1rem 1.2rem;margin-bottom:.8rem;}
h1,h2,h3{color:#f1f5f9!important;font-family:'Plus Jakarta Sans',sans-serif!important;}
label{color:#94a3b8!important;font-size:.85rem!important;}
.section-title{color:#3b82f6;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.3rem;}
</style>
""", unsafe_allow_html=True)

STATUSES = ["Not Checked", "In Progress", "Submitted"]
MONTHS   = ["January", "May", "September"]

# session state
for k,v in [("role",None),("user_name",""),("editing",None),("active_tab",0),("preview_notif",None)]:
    if k not in st.session_state: st.session_state[k] = v

# ── helpers ────────────────────────────────────────────────────────────────────
def bc(status):
    return {"Not Checked":"badge-notchecked","In Progress":"badge-progress","Submitted":"badge-submitted"}.get(status,"badge-notchecked")

def clean(val):
    """Return empty string instead of nan/None."""
    if val is None: return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s

def parse_schools(raw):
    """Parse schools JSON string safely."""
    try:
        data = json.loads(raw)
        if isinstance(data, list): return data
    except: pass
    # legacy: if stored as plain text fall back gracefully
    return []

def schools_summary(raw):
    schools = parse_schools(raw)
    if not schools: return "—"
    return " · ".join([f"{s.get('university','?')} ({s.get('intake','?')})" for s in schools])

def preview_document(doc_path, doc_name):
    ext = os.path.splitext(doc_name)[1].lower()
    if ext in [".jpg",".jpeg",".png"]:
        st.image(doc_path, caption=doc_name, use_column_width=True)
    elif ext == ".pdf":
        with open(doc_path,"rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500px" style="border:none;border-radius:8px;"></iframe>', unsafe_allow_html=True)
    else:
        st.info(f"Preview not available for {ext} — please download.")

def unread_count_for_officer():
    notifs = load_notifications()
    return len([n for n in notifs if n.get("recipient")=="ALL_OFFICERS" and not n.get("read")])

def unread_count_for_counsellor(name):
    notifs = load_notifications()
    return len([n for n in notifs if n.get("recipient")==name and not n.get("read")])

# ── Login ──────────────────────────────────────────────────────────────────────
def show_login():
    st.markdown("""
    <div style='text-align:center;padding:3rem 0 1rem;'>
        <div style='display:inline-block;background:linear-gradient(135deg,#3b82f6,#06b6d4);
                    border-radius:16px;width:64px;height:64px;line-height:64px;font-size:2rem;margin-bottom:1rem;'>🎓</div>
        <h1 style='font-size:2.2rem;font-weight:800;margin:0;'>TGM AppHub</h1>
        <p style='color:#64748b;margin-top:.3rem;'>Application Management Platform</p>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        st.markdown("---")
        st.markdown("<p class='section-title'>Select Your Role</p>", unsafe_allow_html=True)
        role = st.selectbox("", ["— Choose role —","Counsellor","Application Officer"], label_visibility="collapsed")
        name = st.text_input("Your Name", placeholder="Enter your full name")
        if role=="Counsellor":     st.info("📤  Counsellor Portal — Submit and manage student applications")
        elif role=="Application Officer": st.info("📋  Officer Dashboard — Review, update and track all applications")
        if st.button("Enter AppHub →", use_container_width=True):
            if role in ["Counsellor","Application Officer"] and name.strip():
                st.session_state.role      = role
                st.session_state.user_name = name.strip()
                st.rerun()
            else: st.error("Please select a role and enter your name.")

# ── Sidebar with clickable bell ────────────────────────────────────────────────
def show_sidebar(unread=0, go_to_notifs_key="bell_sidebar"):
    with st.sidebar:
        st.markdown(f"""
        <div style='padding:.5rem 0 .5rem;'>
            <div style='display:flex;align-items:center;justify-content:space-between;'>
                <div style='display:flex;align-items:center;gap:10px;'>
                    <div style='background:linear-gradient(135deg,#3b82f6,#06b6d4);border-radius:8px;
                                width:32px;height:32px;display:flex;align-items:center;
                                justify-content:center;font-size:1rem;'>🎓</div>
                    <span style='font-size:1rem;font-weight:800;color:#f1f5f9;'>TGM AppHub</span>
                </div>
            </div>
            <span style='font-size:.65rem;color:#475569;letter-spacing:.1em;text-transform:uppercase;'>Application Management</span>
        </div>
        <hr style='margin-bottom:.8rem;'>
        <div style='background:#1a2236;border-radius:10px;padding:.8rem 1rem;margin-bottom:.8rem;'>
            <div style='font-size:.65rem;color:#475569;text-transform:uppercase;letter-spacing:.1em;'>Logged in as</div>
            <div style='color:#f1f5f9;font-weight:700;font-size:.95rem;'>{st.session_state.user_name}</div>
            <div style='color:#3b82f6;font-size:.75rem;font-weight:600;'>{st.session_state.role}</div>
        </div>
        """, unsafe_allow_html=True)

        # Clickable bell button
        bell_label = f"🔔  Notifications  ({unread} new)" if unread > 0 else "🔔  Notifications"
        if st.button(bell_label, use_container_width=True, key=go_to_notifs_key):
            st.session_state.active_tab = 3  # go to notifications tab
            st.rerun()

        st.markdown("<div style='margin-top:.4rem;'></div>", unsafe_allow_html=True)
        if st.button("🚪  Logout", use_container_width=True):
            for k in ["role","user_name","editing","active_tab","preview_notif"]:
                st.session_state[k] = None if k!="user_name" else ""
            st.rerun()

# ── School entry block ─────────────────────────────────────────────────────────
def school_entry_block(idx, prefill=None):
    p = prefill or {}
    st.markdown(f"<div class='school-block'>", unsafe_allow_html=True)
    st.markdown(f"<p class='section-title'>School {idx}</p>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns([3,3,2,1])
    with c1: uni    = st.text_input("University Name",    value=p.get("university",""),  key=f"uni_{idx}",    placeholder="e.g. University of Kent")
    with c2: course = st.text_input("Course / Programme", value=p.get("course",""),      key=f"course_{idx}", placeholder="e.g. MSc Computer Science")
    with c3:
        saved_month = p.get("intake","January").split(" ")[0] if p.get("intake") else "January"
        saved_year  = int(p.get("intake","January 2026").split(" ")[-1]) if p.get("intake") else 2026
        month = st.selectbox("Intake Month", MONTHS, index=MONTHS.index(saved_month) if saved_month in MONTHS else 0, key=f"month_{idx}")
        year  = st.number_input("Year", min_value=1900, max_value=3000, value=saved_year, step=1, key=f"year_{idx}")
    with c4:
        st.markdown("<div style='margin-top:1.65rem;'></div>", unsafe_allow_html=True)
        remove = st.button("✖", key=f"remove_{idx}", help="Remove this school")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"university": uni, "course": course, "intake": f"{month} {year}"}, remove

# ── COUNSELLOR VIEW ────────────────────────────────────────────────────────────
def counsellor_view():
    unread = unread_count_for_counsellor(st.session_state.user_name)
    show_sidebar(unread=unread, go_to_notifs_key="bell_counsellor")

    st.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;'>
        <div>
            <h1 style='margin:0;font-size:1.8rem;'>Counsellor Portal</h1>
            <p style='color:#64748b;margin:0;'>Submit and manage your student applications</p>
        </div>
    </div>""", unsafe_allow_html=True)

    active = st.session_state.active_tab or 0
    tab1, tab2, tab3 = st.tabs(["📤   Submit New Application","📋   My Applications","🔔   Notifications"])

    # ── TAB 1: Submit ──────────────────────────────────────────────────────────
    with tab1:
        if st.session_state.editing:
            df      = load_applications()
            app_row = df[df["app_id"]==st.session_state.editing]
            if app_row.empty:
                st.session_state.editing = None; st.rerun()
            p = app_row.iloc[0].to_dict()
            st.markdown(f"### ✏️ Edit Application — {p['app_id']}")
            st.warning("Editing existing application.")
            st.markdown("---")
            _render_submit_form(prefill=p, is_edit=True)
        else:
            st.markdown("### New Student Application")
            st.markdown("<p style='color:#64748b;'>Fill in student details, add up to 10 schools, and upload documents.</p>", unsafe_allow_html=True)
            st.markdown("---")
            _render_submit_form()

    # ── TAB 2: My Applications ─────────────────────────────────────────────────
    with tab2:
        st.markdown("### My Submitted Applications")
        df = load_applications()
        if df.empty: st.info("No applications yet.")
        else:
            my = df[df["counsellor_name"]==st.session_state.user_name]
            if my.empty: st.info("No applications found for your name.")
            else:
                for _, row in my.iterrows():
                    status   = clean(row.get("status","Not Checked"))
                    docs     = [d for d in clean(row.get("documents","")).split("|") if d.strip()]
                    schools  = parse_schools(clean(row.get("schools","")))
                    onote    = clean(row.get("officer_notes",""))
                    st.markdown(f"""
                    <div class='app-card'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                            <div>
                                <div style='font-weight:700;color:#f1f5f9;font-size:1rem;'>{clean(row["student_name"])}</div>
                                <div style='color:#64748b;font-size:.8rem;margin-top:2px;'>{len(schools)} school(s) · {len(docs)} doc(s) · 🆔 {clean(row["app_id"])}</div>
                                <div style='color:#475569;font-size:.75rem;margin-top:4px;'>📅 Submitted: {clean(row["submitted_at"])}</div>
                            </div>
                            <span class='badge {bc(status)}'>{status}</span>
                        </div>
                        {f"<div style='margin-top:.6rem;background:#1a2236;border-radius:8px;padding:.5rem .8rem;font-size:.8rem;color:#94a3b8;'>💬 Officer note: {onote}</div>" if onote else ""}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"✏️  Edit  {clean(row['app_id'])}", key=f"edit_{clean(row['app_id'])}"):
                        st.session_state.editing = clean(row["app_id"])
                        st.rerun()

    # ── TAB 3: Notifications ──────────────────────────────────────────────────
    with tab3:
        st.markdown("### Your Notifications")
        notifs    = load_notifications()
        my_notifs = [n for n in notifs if n.get("recipient")==st.session_state.user_name]
        mark_notification_read(st.session_state.user_name)
        if not my_notifs: st.info("No notifications yet.")
        else:
            for n in sorted(my_notifs, key=lambda x:x["time"], reverse=True):
                cls = "notif-unread" if not n.get("read") else "notif-card"
                msg = clean(n.get("message",""))
                aid = clean(n.get("app_id",""))
                st.markdown(f"""
                <div class='{cls}'>
                    <div style='font-size:.85rem;color:#e2e8f0;'>{msg}</div>
                    <div style='font-size:.72rem;color:#475569;margin-top:4px;'>🕐 {n["time"]} · From: {clean(n.get("sender","System"))} · App ID: {aid}</div>
                </div>""", unsafe_allow_html=True)
                if aid:
                    if st.button(f"👁 View Application {aid}", key=f"view_notif_c_{n['id']}"):
                        st.session_state.preview_notif = aid
                        st.rerun()

        # Show application preview if triggered from notification
        if st.session_state.preview_notif:
            df  = load_applications()
            row = df[df["app_id"]==st.session_state.preview_notif]
            if not row.empty:
                r = row.iloc[0]
                st.markdown("---")
                st.markdown(f"#### Application Detail — {clean(r['app_id'])}")
                st.markdown(f"**Student:** {clean(r['student_name'])}  |  **Status:** {clean(r['status'])}")
                schools = parse_schools(clean(r.get("schools","")))
                for i,s in enumerate(schools,1):
                    st.markdown(f"**School {i}:** {s.get('university','?')} — {s.get('course','?')} ({s.get('intake','?')})")
            if st.button("✖ Close Preview", key="close_preview_c"):
                st.session_state.preview_notif = None
                st.rerun()

# ── Submit / Edit form (shared) ────────────────────────────────────────────────
def _render_submit_form(prefill=None, is_edit=False):
    p = prefill or {}

    # Student + counsellor info
    col1,col2 = st.columns(2)
    with col1:
        st.markdown("<p class='section-title'>Student Information</p>", unsafe_allow_html=True)
        sn = st.text_input("Student Full Name *",  value=clean(p.get("student_name","")),  placeholder="e.g. Amina Bello")
        se = st.text_input("Student Email",        value=clean(p.get("student_email","")), placeholder="student@email.com")
        sp = st.text_input("Student Phone",        value=clean(p.get("student_phone","")), placeholder="+234...")
    with col2:
        st.markdown("<p class='section-title'>Counsellor Information</p>", unsafe_allow_html=True)
        cn = st.text_input("Your Full Name *",    value=clean(p.get("counsellor_name", st.session_state.user_name)))
        ce = st.text_input("Your Email *",        value=clean(p.get("counsellor_email","")), placeholder="counsellor@tgmeducation.com")
        cp = st.text_input("Your Phone Number *", value=clean(p.get("counsellor_phone","")), placeholder="+234...")

    st.markdown("---")

    # Schools — dynamic add/remove
    st.markdown("<p class='section-title'>Schools (add up to 10)</p>", unsafe_allow_html=True)
    if "num_schools" not in st.session_state: st.session_state.num_schools = 1
    if is_edit:
        existing = parse_schools(clean(p.get("schools","")))
        if existing and st.session_state.num_schools == 1:
            st.session_state.num_schools = len(existing)

    schools_data = []
    to_remove = None
    for i in range(1, st.session_state.num_schools + 1):
        pf = existing[i-1] if is_edit and "existing" in dir() and i <= len(existing) else {}
        data, remove = school_entry_block(i, prefill=pf)
        schools_data.append(data)
        if remove: to_remove = i

    if to_remove and st.session_state.num_schools > 1:
        schools_data.pop(to_remove - 1)
        st.session_state.num_schools -= 1
        st.rerun()

    cola, colb = st.columns(2)
    with cola:
        if st.session_state.num_schools < 10:
            if st.button("➕  Add Another School", use_container_width=True):
                st.session_state.num_schools += 1
                st.rerun()
    with colb:
        if st.session_state.num_schools > 1:
            if st.button("➖  Remove Last School", use_container_width=True):
                st.session_state.num_schools -= 1
                st.rerun()

    st.markdown("---")
    st.markdown("<p class='section-title'>Documents</p>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload documents (CV, Transcripts, IELTS, Passport, etc.)",
        accept_multiple_files=True, type=["pdf","docx","doc","jpg","jpeg","png"]
    )
    st.markdown("<p class='section-title' style='margin-top:1rem;'>Notes</p>", unsafe_allow_html=True)
    notes = st.text_area("Additional Notes", value=clean(p.get("notes","")), height=80)
    st.markdown("---")

    btn_label = "💾  Save Changes" if is_edit else "🚀  Submit Application"
    if st.button(btn_label, use_container_width=True):
        valid_schools = [s for s in schools_data if s.get("university","").strip()]
        if not all([sn, ce, cp]) or not valid_schools:
            st.error("Please fill in required fields and at least one school.")
            return

        if is_edit:
            app_id    = clean(p.get("app_id",""))
            doc_names = [d for d in clean(p.get("documents","")).split("|") if d.strip()]
            if uploaded_files:
                for f in uploaded_files:
                    saved = save_uploaded_file(app_id, f)
                    if saved not in doc_names: doc_names.append(saved)
            edit_application(app_id, {**p,
                "student_name":sn,"student_email":se,"student_phone":sp,
                "counsellor_name":cn,"counsellor_email":ce,"counsellor_phone":cp,
                "schools":json.dumps(valid_schools),"notes":notes,
                "documents":"|".join(doc_names),
                "last_updated":datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            st.session_state.editing   = None
            st.session_state.num_schools = 1
            st.success("✅ Application updated!")
            st.rerun()
        else:
            app_id = str(uuid.uuid4())[:8].upper()
            doc_names = []
            if uploaded_files:
                for f in uploaded_files: doc_names.append(save_uploaded_file(app_id, f))
            schools_str = json.dumps(valid_schools)
            school_summary = ", ".join([s.get("university","?") for s in valid_schools])
            save_application({
                "app_id":app_id,"student_name":sn,"student_email":se,"student_phone":sp,
                "schools":schools_str,
                "counsellor_name":cn,"counsellor_email":ce,"counsellor_phone":cp,
                "notes":notes,"documents":"|".join(doc_names),"status":"Not Checked",
                "assigned_officer":"All Officers",
                "submitted_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
                "last_updated":datetime.now().strftime("%Y-%m-%d %H:%M"),
                "officer_notes":"",
            })
            add_notification({
                "id":str(uuid.uuid4())[:8],"recipient":"ALL_OFFICERS","sender":cn,
                "type":"new_application",
                "message":f"📥 New application from {cn} — Student: {sn} | Schools: {school_summary}",
                "app_id":app_id,"time":datetime.now().strftime("%Y-%m-%d %H:%M"),"read":False,
            })
            st.session_state.num_schools = 1
            st.success(f"✅ Application submitted! ID: **{app_id}**")
            st.balloons()

# ── OFFICER VIEW ───────────────────────────────────────────────────────────────
def officer_view():
    unread = unread_count_for_officer()
    show_sidebar(unread=unread, go_to_notifs_key="bell_officer")

    df     = load_applications()
    notifs = load_notifications()

    unread_badge = f"<div style='background:#ef4444;color:white;border-radius:20px;padding:.4rem 1rem;font-weight:800;font-size:.9rem;'>🔔 {unread} new</div>" if unread > 0 else ""
    st.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;'>
        <div>
            <h1 style='margin:0;font-size:1.8rem;'>Applications Dashboard</h1>
            <p style='color:#64748b;margin:0;'>All applications — manage, preview and update</p>
        </div>
        {unread_badge}
    </div>""", unsafe_allow_html=True)

    if not df.empty:
        c1,c2,c3,c4 = st.columns(4)
        for col,label,val,color in [
            (c1,"Total",          len(df),                                    "#3b82f6"),
            (c2,"Not Checked",    len(df[df["status"]=="Not Checked"]),        "#f59e0b"),
            (c3,"In Progress",    len(df[df["status"]=="In Progress"]),        "#06b6d4"),
            (c4,"Submitted",      len(df[df["status"]=="Submitted"]),          "#8b5cf6"),
        ]:
            with col:
                st.markdown(f"""
                <div style='background:#111827;border:1px solid rgba(255,255,255,.07);
                            border-top:3px solid {color};border-radius:12px;padding:1rem;text-align:center;'>
                    <div style='color:{color};font-size:1.8rem;font-weight:800;'>{val}</div>
                    <div style='color:#64748b;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;'>{label}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    tab1,tab2,tab3,tab4 = st.tabs([
        "📋   All Applications",
        "🔍   Reports & Insights",
        "✏️   Update Application",
        "🔔   Notifications"
    ])

    # ── TAB 1 ────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### All Applications")
        if df.empty: st.info("No applications yet.")
        else:
            c1,c2,c3 = st.columns(3)
            with c1: f_uni    = st.selectbox("Filter by University",["All"]+sorted(df["counsellor_name"].dropna().unique().tolist()))
            with c2: f_status = st.selectbox("Filter by Status",["All"]+STATUSES)
            with c3: f_couns  = st.selectbox("Filter by Counsellor",["All"]+sorted(df["counsellor_name"].dropna().unique().tolist()))

            fdf = df.copy()
            if f_status != "All": fdf = fdf[fdf["status"]==f_status]
            if f_couns  != "All": fdf = fdf[fdf["counsellor_name"]==f_couns]

            st.markdown(f"<p style='color:#64748b;font-size:.85rem;'>Showing {len(fdf)} of {len(df)} applications</p>", unsafe_allow_html=True)

            for _, row in fdf.iterrows():
                status   = clean(row.get("status","Not Checked"))
                schools  = parse_schools(clean(row.get("schools","")))
                doc_list = [d for d in clean(row.get("documents","")).split("|") if d.strip()]
                onote    = clean(row.get("officer_notes",""))
                sname    = clean(row["student_name"])
                aid      = clean(row["app_id"])

                with st.expander(f"🧑 {sname}  ·  {len(schools)} school(s)  ·  [{status}]  ·  ID: {aid}"):
                    # Student + counsellor info
                    ci1,ci2 = st.columns(2)
                    with ci1:
                        st.markdown(f"**Student:** {sname}")
                        st.markdown(f"**Email:** {clean(row.get('student_email','—'))}")
                        st.markdown(f"**Phone:** {clean(row.get('student_phone','—'))}")
                    with ci2:
                        st.markdown(f"**Counsellor:** {clean(row.get('counsellor_name','—'))}")
                        st.markdown(f"**C. Email:** {clean(row.get('counsellor_email','—'))}")
                        st.markdown(f"**C. Phone:** {clean(row.get('counsellor_phone','—'))}")

                    # Schools list
                    if schools:
                        st.markdown("**🏫 Schools Applied To:**")
                        for i,s in enumerate(schools,1):
                            st.markdown(f"&nbsp;&nbsp;**{i}.** {s.get('university','?')} — _{s.get('course','?')}_ — {s.get('intake','?')}")

                    notes_val = clean(row.get("notes",""))
                    if notes_val: st.markdown(f"**Notes:** {notes_val}")
                    if onote:     st.info(f"💬 Officer Note: {onote}")

                    st.markdown(f"**Submitted:** {clean(row.get('submitted_at','—'))}  |  **App ID:** {aid}")

                    # Inline status update
                    st.markdown("---")
                    uc1,uc2,uc3 = st.columns([2,2,1])
                    with uc1:
                        cur = clean(row.get("status","Not Checked"))
                        new_s = st.selectbox("Update Status", STATUSES,
                            index=STATUSES.index(cur) if cur in STATUSES else 0,
                            key=f"st_{aid}")
                    with uc2:
                        note = st.text_input("Note to Counsellor", value=onote,
                            key=f"nt_{aid}", placeholder="Optional note...")
                    with uc3:
                        st.markdown("<div style='margin-top:1.65rem;'></div>", unsafe_allow_html=True)
                        if st.button("💾 Save", key=f"sv_{aid}"):
                            update_application_status(aid, new_s, note)
                            add_notification({
                                "id":str(uuid.uuid4())[:8],
                                "recipient":clean(row.get("counsellor_name","")),
                                "sender":st.session_state.user_name,
                                "type":"status_update",
                                "message":f"✅ Status updated for {sname} → {new_s}" + (f" | Note: {note}" if note else ""),
                                "app_id":aid,"time":datetime.now().strftime("%Y-%m-%d %H:%M"),"read":False,
                            })
                            st.success(f"Saved — {new_s}")
                            st.rerun()

                    # Documents
                    if doc_list:
                        st.markdown(f"**📎 Documents ({len(doc_list)}):**")
                        for doc in doc_list:
                            doc_path = os.path.join("uploads", aid, doc)
                            if os.path.exists(doc_path):
                                dc1,dc2 = st.columns([3,1])
                                with dc1:
                                    with st.expander(f"👁 Preview — {doc}"):
                                        preview_document(doc_path, doc)
                                with dc2:
                                    with open(doc_path,"rb") as f:
                                        st.download_button("⬇ Download", data=f.read(),
                                            file_name=doc, key=f"dl_{aid}_{doc}")
                    else:
                        st.markdown("**📎 Documents:** None uploaded")

    # ── TAB 2: Reports ────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Reports & Insights")
        if df.empty: st.info("No data yet.")
        else:
            st.markdown("#### 🔍 Quick Query — by University & Intake")
            qc1,qc2,qc3 = st.columns(3)
            with qc1: q_uni   = st.text_input("University name", placeholder="e.g. UCLan")
            with qc2: q_month = st.selectbox("Intake Month",["All"]+MONTHS)
            with qc3: q_year  = st.number_input("Intake Year",min_value=1900,max_value=3000,value=2026,step=1)

            if st.button("🔍  Run Query"):
                results = []
                for _,row in df.iterrows():
                    schools = parse_schools(clean(row.get("schools","")))
                    for s in schools:
                        uni_match    = q_uni.strip().lower() in s.get("university","").lower() if q_uni.strip() else True
                        month_match  = q_month in s.get("intake","") if q_month != "All" else True
                        year_match   = str(q_year) in s.get("intake","")
                        if uni_match and month_match and year_match:
                            results.append({
                                "App ID": clean(row["app_id"]),
                                "Student": clean(row["student_name"]),
                                "University": s.get("university",""),
                                "Course": s.get("course",""),
                                "Intake": s.get("intake",""),
                                "Status": clean(row["status"]),
                                "Counsellor": clean(row["counsellor_name"]),
                            })
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,rgba(59,130,246,.15),rgba(6,182,212,.15));
                            border:1px solid rgba(59,130,246,.3);border-radius:12px;padding:1.5rem;text-align:center;'>
                    <div style='font-size:3rem;font-weight:800;color:#3b82f6;'>{len(results)}</div>
                    <div style='color:#94a3b8;font-size:.9rem;'>Results for <b>{q_uni or "All Universities"}</b> — {q_month} {q_year}</div>
                </div>""", unsafe_allow_html=True)
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### 📊 Status Overview")
            sc = df["status"].value_counts().reset_index(); sc.columns=["Status","Count"]
            st.dataframe(sc, use_container_width=True, hide_index=True)

            st.markdown("#### 👤 By Counsellor")
            st.dataframe(df.groupby("counsellor_name").agg(Total=("app_id","count")).reset_index(),
                         use_container_width=True, hide_index=True)

    # ── TAB 3: Update ────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### Update Application")
        st.markdown("<p style='color:#64748b;'>All applications are visible to every officer.</p>", unsafe_allow_html=True)
        if df.empty: st.info("No applications yet.")
        else:
            opts = {f"{clean(r['app_id'])} — {clean(r['student_name'])} [{clean(r['status'])}]": clean(r['app_id'])
                    for _,r in df.iterrows()}
            sel_label = st.selectbox("Select Application", list(opts.keys()))
            sel_id    = opts[sel_label]
            app_row   = df[df["app_id"]==sel_id].iloc[0]
            cur       = clean(app_row.get("status","Not Checked"))
            onote     = clean(app_row.get("officer_notes",""))

            uc1,uc2 = st.columns(2)
            with uc1: new_s  = st.selectbox("Status", STATUSES, index=STATUSES.index(cur) if cur in STATUSES else 0)
            with uc2: o_note = st.text_area("Note to Counsellor", value=onote, height=100, placeholder="Optional note...")

            if st.button("💾  Save Update", use_container_width=True):
                update_application_status(sel_id, new_s, o_note)
                add_notification({
                    "id":str(uuid.uuid4())[:8],
                    "recipient":clean(app_row.get("counsellor_name","")),
                    "sender":st.session_state.user_name,"type":"status_update",
                    "message":f"✅ Status updated for {clean(app_row['student_name'])} → {new_s}" + (f" | Note: {o_note}" if o_note else ""),
                    "app_id":sel_id,"time":datetime.now().strftime("%Y-%m-%d %H:%M"),"read":False,
                })
                st.success(f"✅ Updated to **{new_s}**. Counsellor notified.")
                st.rerun()

    # ── TAB 4: Notifications ─────────────────────────────────────────────────
    with tab4:
        st.markdown("### All Notifications")
        st.markdown("<p style='color:#64748b;'>Every new application and status update appears here.</p>", unsafe_allow_html=True)
        notifs  = load_notifications()
        all_n   = [n for n in notifs if n.get("recipient")=="ALL_OFFICERS" or n.get("type") in ("new_application","status_update")]
        combined = list({n["id"]:n for n in all_n}.values())
        sorted_n = sorted(combined, key=lambda x:x["time"], reverse=True)

        mark_notifications_read_for_officer()

        if not sorted_n: st.info("No notifications yet.")
        else:
            st.markdown(f"<p style='color:#64748b;font-size:.85rem;'>{len(sorted_n)} notification(s)</p>", unsafe_allow_html=True)
            for n in sorted_n:
                cls = "notif-unread" if not n.get("read") else "notif-card"
                msg = clean(n.get("message",""))
                aid = clean(n.get("app_id",""))
                st.markdown(f"""
                <div class='{cls}'>
                    <div style='font-size:.85rem;color:#e2e8f0;'>{msg}</div>
                    <div style='font-size:.72rem;color:#475569;margin-top:4px;'>🕐 {n["time"]} · From: {clean(n.get("sender","System"))} · App: {aid}</div>
                </div>""", unsafe_allow_html=True)
                if aid:
                    if st.button(f"👁 View Application {aid}", key=f"view_notif_{n['id']}"):
                        st.session_state.preview_notif = aid
                        st.rerun()

        # Preview panel
        if st.session_state.preview_notif:
            dfp = load_applications()
            row = dfp[dfp["app_id"]==st.session_state.preview_notif]
            if not row.empty:
                r = row.iloc[0]
                st.markdown("---")
                st.markdown(f"#### 📋 Application Detail — {clean(r['app_id'])}")
                st.markdown(f"**Student:** {clean(r['student_name'])}  |  **Status:** {clean(r['status'])}")
                st.markdown(f"**Counsellor:** {clean(r.get('counsellor_name','—'))}  |  **Submitted:** {clean(r.get('submitted_at','—'))}")
                schools = parse_schools(clean(r.get("schools","")))
                if schools:
                    st.markdown("**Schools:**")
                    for i,s in enumerate(schools,1):
                        st.markdown(f"&nbsp;&nbsp;**{i}.** {s.get('university','?')} — {s.get('course','?')} ({s.get('intake','?')})")
                onote = clean(r.get("officer_notes",""))
                if onote: st.info(f"💬 Officer Note: {onote}")
            if st.button("✖ Close", key="close_preview_o"):
                st.session_state.preview_notif = None
                st.rerun()

# ── MAIN ───────────────────────────────────────────────────────────────────────
if st.session_state.role is None:
    show_login()
elif st.session_state.role == "Counsellor":
    counsellor_view()
elif st.session_state.role == "Application Officer":
    officer_view()
