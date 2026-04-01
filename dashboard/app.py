"""
dashboard/app.py
WorldJobs Dashboard — full rebuild
Dark professional theme (Bloomberg-style)

Run:
    cd ~/worldwide-job-scraper && source venv/bin/activate
    streamlit run dashboard/app.py
"""

import streamlit as st
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

def get_db_config():
    return {
        "dbname":   os.getenv("DB_NAME", "worldjobs"),
        "user":     os.getenv("DB_USER", "jobscraper"),
        "password": os.getenv("DB_PASSWORD", "jobscraper123"),
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 5432)),
    }

import psycopg2.extras
import pandas as pd
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="WorldJobs",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
    background-color: #0a0b0d !important;
    color: #e2e8f0 !important;
}
.stApp { background-color: #0a0b0d !important; }

/* Keep sidebar always open */
[data-testid="stSidebar"] {
    min-width: 200px !important;
    max-width: 200px !important;
    transform: none !important;
}
[data-testid="stSidebarCollapseButton"] { visibility: hidden !important; }
[data-testid="collapsedControl"] { visibility: hidden !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111318 !important;
    border-right: 1px solid #2a3040 !important;
}
[data-testid="stSidebar"] * { color: #8899b0 !important; }
[data-testid="stSidebar"] .stRadio label { 
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.5px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #111318 !important;
    border: 1px solid #2a3040 !important;
    padding: 14px 16px !important;
    border-radius: 0 !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: #4a5a70 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 24px !important;
    color: #00d4aa !important;
}
[data-testid="stMetricDelta"] { font-size: 11px !important; }

/* Dataframe / tables */
[data-testid="stDataFrame"] {
    border: 1px solid #2a3040 !important;
}

/* Inputs */
input, textarea, select, [data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select {
    background-color: #181c24 !important;
    border: 1px solid #2a3040 !important;
    color: #e2e8f0 !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* Buttons */
.stButton button {
    background-color: transparent !important;
    border: 1px solid #00d4aa !important;
    color: #00d4aa !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
.stButton button:hover {
    background-color: rgba(0,212,170,0.1) !important;
}

/* Primary button */
.stButton.primary button {
    background-color: #00d4aa !important;
    color: #000 !important;
}

/* Headers */
h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #e2e8f0 !important;
    letter-spacing: 1px !important;
}
h1 { font-size: 18px !important; color: #00d4aa !important; }
h2 { font-size: 14px !important; border-bottom: 1px solid #2a3040; padding-bottom: 6px; }
h3 { font-size: 12px !important; color: #8899b0 !important; }

/* Tabs */
[data-testid="stTabs"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    color: #8899b0 !important;
    border-radius: 0 !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #00d4aa !important;
    border-bottom: 2px solid #00d4aa !important;
}

/* Success / error / warning */
.stSuccess { background: rgba(0,212,170,0.08) !important; border: 1px solid rgba(0,212,170,0.3) !important; border-radius: 0 !important; }
.stError   { background: rgba(255,69,96,0.08) !important; border: 1px solid rgba(255,69,96,0.3) !important; border-radius: 0 !important; }
.stWarning { background: rgba(245,166,35,0.08) !important; border: 1px solid rgba(245,166,35,0.3) !important; border-radius: 0 !important; }
.stInfo    { background: rgba(0,153,255,0.08) !important; border: 1px solid rgba(0,153,255,0.3) !important; border-radius: 0 !important; }

/* Divider */
hr { border-color: #2a3040 !important; }

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #2a3040 !important;
    border-radius: 0 !important;
    background: #111318 !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

</style>
""", unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────

DB_CONFIG = get_db_config()

RESUME_DIR = Path("uploads/resumes")
RESUME_DIR.mkdir(parents=True, exist_ok=True)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def query(sql, params=None, fetch="all"):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        if fetch == "all":
            result = [dict(r) for r in cur.fetchall()]
        elif fetch == "one":
            r = cur.fetchone()
            result = dict(r) if r else None
        else:
            result = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        st.error(f"DB error: {e}")
        return [] if fetch == "all" else None


def execute(sql, params=None):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        cur.close()
        conn.close()
        return 1
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        st.error(f"DB error: {e}")
        return 0


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def login(email: str, password: str):
    user = query(
        "SELECT * FROM users WHERE email=%s AND is_active=TRUE",
        (email,), fetch="one"
    )
    if user and user["password_hash"] == hash_password(password):
        execute(
            "UPDATE users SET last_login=%s WHERE id=%s",
            (datetime.now(timezone.utc), user["id"])
        )
        return user
    return None


def register(email, password, full_name, role):
    existing = query("SELECT id FROM users WHERE email=%s", (email,), fetch="one")
    if existing:
        return None, "Email already registered."
    execute(
        "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
        (email, hash_password(password), full_name, role)
    )
    return query("SELECT * FROM users WHERE email=%s", (email,), fetch="one"), None


def require_login():
    return st.session_state.get("user")


def require_role(role):
    user = require_login()
    return user and user.get("role") == role


# ── Session state init ────────────────────────────────────────────────────────

if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Job Board"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🌐 WORLDJOBS")
    st.markdown("---")

    user = st.session_state.user

    if user:
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"{user['email']} · `{user['role'].upper()}`")
        st.markdown("---")

    # Nav options based on auth state
    nav_options = ["Job Board"]
    if user:
        nav_options += ["For You", "My Profile", "My Applications"]
        if user["role"] in ("employer", "admin"):
            nav_options += ["Post a Job", "My Postings"]
        if user["role"] == "admin":
            nav_options += ["Scraper Logs", "Deduplication"]
    else:
        nav_options += ["Login / Register"]

    page = st.radio("Navigate", nav_options, label_visibility="collapsed")
    st.session_state.page = page

    st.markdown("---")

    # Live stats
    stats = query("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE scraped_at > NOW() - INTERVAL '24 hours') AS today
        FROM jobs WHERE is_active = TRUE
    """, fetch="one")
    if stats:
        st.markdown(f"""
        <div style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1px'>
        LIVE JOBS<br>
        <span style='font-size:20px;color:#00d4aa'>{stats['total']:,}</span><br>
        <span style='color:#8899b0'>+{stats['today']} today</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    if user:
        if st.button("LOGOUT"):
            st.session_state.user = None
            st.rerun()


# ── Pages ─────────────────────────────────────────────────────────────────────

page = st.session_state.page

# ═══════════════════════════════════════════════════════════════════════════════
# JOB BOARD
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Job Board":
    st.markdown("## JOB BOARD")

    # KPIs
    import psycopg2, psycopg2.extras as _extras
    _conn = psycopg2.connect(dbname="worldjobs", user="jobscraper", password="jobscraper123", host="localhost", port=5432)
    _cur = _conn.cursor(cursor_factory=_extras.RealDictCursor)
    _cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE source='linkedin') AS linkedin,
            COUNT(*) FILTER (WHERE source='merojob') AS nepal,
            COUNT(*) FILTER (WHERE source IN ('remoteok','weworkremotely') OR LOWER(location) LIKE '%remote%') AS remote
        FROM jobs WHERE is_active=TRUE
    """)
    kpi = dict(_cur.fetchone()) or {}
    _cur.close()
    _conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Jobs",    f"{kpi.get('total',0):,}")
    c2.metric("LinkedIn",      f"{kpi.get('linkedin',0):,}")
    c3.metric("Nepal",         f"{kpi.get('nepal',0):,}")
    c4.metric("Remote",        f"{kpi.get('remote',0):,}")

    st.markdown("---")

    # Charts row
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### JOBS BY REGION")
        region_data = query("""
            SELECT COALESCE(region,'Unknown') AS region, COUNT(*) AS count
            FROM jobs WHERE is_active=TRUE
            GROUP BY region ORDER BY count DESC LIMIT 8
        """)
        if region_data:
            df_region = pd.DataFrame(region_data).set_index("region")
            st.bar_chart(df_region, color="#00d4aa")

    with col_right:
        st.markdown("### BY SOURCE")
        source_data = query("""
            SELECT source, COUNT(*) AS count
            FROM jobs WHERE is_active=TRUE
            GROUP BY source ORDER BY count DESC
        """)
        if source_data:
            df_source = pd.DataFrame(source_data).set_index("source")
            st.bar_chart(df_source, color="#0099ff")

    st.markdown("---")
    st.markdown("### LIVE LISTINGS")

    # Search bar always visible
    search = st.text_input("🔍 Search title, company, skill...")

    # Toggle filters button
    if "show_filters" not in st.session_state:
        st.session_state.show_filters = True
    col_tog, col_sort = st.columns([1, 3])
    with col_tog:
        if st.button("🎛 Filters ▲" if st.session_state.show_filters else "🎛 Filters ▼"):
            st.session_state.show_filters = not st.session_state.show_filters
            st.rerun()
    with col_sort:
        sort_by = st.selectbox("↕ Sort By", ["Newest", "Oldest", "Company A-Z"], label_visibility="collapsed")

    # Collapsible filter row
    src_filter = None
    type_filter = None
    region_filter = None
    country_filter = None

    if st.session_state.show_filters:
        f1, f2, f3, f4 = st.columns([2, 2, 3, 3])
        with f1:
            sources = ["All Sources"] + [r["source"] for r in query("SELECT DISTINCT source FROM jobs WHERE source IS NOT NULL ORDER BY source")]
            src_filter = st.selectbox("📡 Source", sources)
            src_filter = None if src_filter == "All Sources" else src_filter
        with f2:
            types = ["All Types"] + [r["job_type"] for r in query("SELECT DISTINCT job_type FROM jobs WHERE job_type IS NOT NULL ORDER BY job_type")]
            type_filter = st.selectbox("💼 Job Type", types)
            type_filter = None if type_filter == "All Types" else type_filter
        with f3:
            regions = ["All Regions"] + [r["region"] for r in query("SELECT DISTINCT region FROM jobs WHERE region IS NOT NULL ORDER BY region")]
            region_filter = st.selectbox("🌍 Continent / Region", regions)
            region_filter = None if region_filter == "All Regions" else region_filter
        with f4:
            countries = ["All Countries"] + [r["country"] for r in query("""
                SELECT DISTINCT country FROM jobs
                WHERE country IS NOT NULL AND country != ''
                AND country IN (
                    SELECT country FROM jobs
                    GROUP BY country HAVING COUNT(*) >= 5
                )
                ORDER BY country
            """)]
            country_filter = st.selectbox("🏳 Country", countries)
            country_filter = None if country_filter == "All Countries" else country_filter

    # Build query
    where = ["is_active = TRUE"]
    params = []

    if search:
        where.append("(title ILIKE %s OR company ILIKE %s OR skills ILIKE %s)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if src_filter:
        where.append("source = %s")
        params.append(src_filter)
    if region_filter:
        where.append("region = %s")
        params.append(region_filter)
    if country_filter:
        where.append("country = %s")
        params.append(country_filter)
    if type_filter:
        where.append("job_type = %s")
        params.append(type_filter)

    order = {
        "Newest":      "scraped_at DESC",
        "Oldest":      "scraped_at ASC",
        "Company A-Z": "company ASC",
    }.get(sort_by, "scraped_at DESC")

    sql = f"""
        SELECT id, title, company, location, job_type, source,
               salary_min, salary_max, salary_currency, job_url, scraped_at
        FROM jobs
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT 100
    """
    jobs = query(sql, params)

    if not jobs:
        st.info("No jobs found matching your filters.")
    else:
        st.caption(f"Showing {len(jobs)} jobs")
        # Column headers
        h1, h2, h3, h4, h5 = st.columns([4, 3, 2, 2, 2])
        h1.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>TITLE / COMPANY</span>", unsafe_allow_html=True)
        h2.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>LOCATION</span>", unsafe_allow_html=True)
        h3.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>TYPE</span>", unsafe_allow_html=True)
        h4.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>SALARY / SOURCE</span>", unsafe_allow_html=True)
        h5.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>ACTION</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:4px 0;border-color:#2a3040'>", unsafe_allow_html=True)

        for job in jobs:
            with st.container():
                j1, j2, j3, j4, j5 = st.columns([4, 3, 2, 2, 2])

                with j1:
                    st.markdown(f"**{job['title']}**")
                    st.caption(job.get("company") or "—")

                with j2:
                    st.caption(job.get("location") or "—")

                with j3:
                    st.caption(job.get("job_type") or "Not specified")

                with j4:
                    smin = job.get("salary_min")
                    smax = job.get("salary_max")
                    cur_sym = job.get("salary_currency") or "USD"
                    src = job.get("source") or ""
                    if smin and smax:
                        st.caption(f"{cur_sym} {int(smin):,}–{int(smax):,}")
                        st.caption(f"`{src}`")
                    else:
                        st.caption(f"`{src}`")

                with j5:
                    user = st.session_state.user
                    job_url = job.get("job_url")
                    if user and user["role"] == "jobseeker":
                        already = query(
                            "SELECT id FROM applications WHERE user_id=%s AND job_id=%s",
                            (user["id"], job["id"]), fetch="one"
                        )
                        if already:
                            st.caption("✓ Applied")
                        else:
                            if st.button("APPLY", key=f"apply_{job['id']}"):
                                st.session_state[f"confirm_{job['id']}"] = True
                    elif job_url:
                        st.link_button("VIEW", job_url)
                    else:
                        st.caption("—")

                # Confirmation expander shown below the row
                if st.session_state.get(f"confirm_{job['id']}"):
                    with st.expander(f"Confirm application — {job['title']} at {job.get('company','')}", expanded=True):
                        user = st.session_state.user
                        profile = query("SELECT * FROM jobseeker_profiles WHERE user_id=%s", (user["id"],), fetch="one") or {}
                        cover = profile.get("cover_letter_tpl") or ""
                        cover = cover.replace("{role}", job["title"]).replace("{company}", job.get("company") or "")
                        st.markdown(f"**Role:** {job['title']}")
                        st.markdown(f"**Company:** {job.get('company') or '—'}")
                        st.markdown(f"**Location:** {job.get('location') or '—'}")
                        if job.get("salary_min"):
                            st.markdown(f"**Salary:** {job.get('salary_currency','USD')} {int(job['salary_min']):,} – {int(job.get('salary_max',0)):,}")
                        if job.get("job_url"):
                            st.markdown(f"[🔗 View Original Job Posting]({job['job_url']})", unsafe_allow_html=False)
                        cover_edit = st.text_area("Cover Letter", value=cover, height=120, key=f"cover_{job['id']}")
                        resume_path = profile.get("resume_path")
                        if resume_path:
                            st.caption(f"Resume: {resume_path.split('/')[-1]}")
                        else:
                            st.warning("No resume uploaded — go to My Profile to add one.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("CONFIRM & APPLY", key=f"confirm_btn_{job['id']}"):
                                execute("""
                                    INSERT INTO applications (user_id, job_id, cover_letter, resume_path)
                                    VALUES (%s, %s, %s, %s)
                                """, (user["id"], job["id"], cover_edit, resume_path))
                                st.session_state[f"confirm_{job['id']}"] = False
                                st.success("Applied!")
                                st.rerun()
                        with cc2:
                            if st.button("CANCEL", key=f"cancel_{job['id']}"):
                                st.session_state[f"confirm_{job['id']}"] = False
                                st.rerun()

                st.markdown("<hr style='margin:4px 0;border-color:#1e2330'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOR YOU
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "For You":
    user = require_login()
    if not user:
        st.warning("Please log in to see personalised recommendations.")
        st.stop()

    st.markdown("## FOR YOU")

    from scraper.utils.recommender import get_recommendations

    profile = query("SELECT * FROM jobseeker_profiles WHERE user_id=%s", (user["id"],), fetch="one")

    if not profile or not profile.get("skills"):
        st.info("Add your skills and current title in **My Profile** to get personalised recommendations.")
        st.stop()

    st.caption(f"Based on: **{profile.get('current_title','')}** · Skills: {profile.get('skills','')}")
    if profile.get("preferred_location"):
        st.caption(f"Preferred location: {profile['preferred_location']} · Type: {profile.get('preferred_job_type','any')}")

    st.markdown("---")

    with st.spinner("Finding best matches..."):
        recs = get_recommendations(user["id"], limit=30)

    if not recs:
        st.info("No matches found yet — try adding more skills to your profile.")
        st.stop()

    st.caption(f"Found {len(recs)} matches")

    # Column headers
    h1, h2, h3, h4, h5, h6 = st.columns([4, 3, 2, 2, 2, 2])
    h1.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>TITLE / COMPANY</span>", unsafe_allow_html=True)
    h2.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>LOCATION</span>", unsafe_allow_html=True)
    h3.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>MATCH</span>", unsafe_allow_html=True)
    h4.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>TYPE</span>", unsafe_allow_html=True)
    h5.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>SOURCE</span>", unsafe_allow_html=True)
    h6.markdown("<span style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5a70;letter-spacing:1.5px'>ACTION</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0;border-color:#2a3040'>", unsafe_allow_html=True)

    for rec in recs:
        c1, c2, c3, c4, c5, c6 = st.columns([4, 3, 2, 2, 2, 2])

        with c1:
            st.markdown(f"**{rec['title']}**")
            st.caption(rec.get("company") or "—")
            if rec.get("match_reasons"):
                st.caption("🎯 " + " · ".join(rec["match_reasons"][:2]))

        with c2:
            st.caption(rec.get("location") or "—")

        with c3:
            score_pct = int(rec["score"] * 100)
            if score_pct >= 50:
                color = "#00d4aa"
            elif score_pct >= 30:
                color = "#f5a623"
            else:
                color = "#8899b0"
            st.markdown(
                f"<span style='font-family:IBM Plex Mono,monospace;font-size:13px;color:{color};font-weight:500'>{score_pct}%</span>",
                unsafe_allow_html=True
            )

        with c4:
            st.caption(rec.get("job_type") or "—")

        with c5:
            st.caption(f"`{rec.get('source','')}`")

        with c6:
            already = query(
                "SELECT id FROM applications WHERE user_id=%s AND job_id=%s",
                (user["id"], rec["id"]), fetch="one"
            )
            if already:
                st.caption("✓ Applied")
            else:
                if st.button("APPLY", key=f"rec_apply_{rec['id']}"):
                    st.session_state[f"confirm_{rec['id']}"] = True

        if st.session_state.get(f"confirm_{rec['id']}"):
            with st.expander(f"Confirm — {rec['title']} at {rec.get('company','')}", expanded=True):
                cover = (profile.get("cover_letter_tpl") or "").replace(
                    "{role}", rec["title"]
                ).replace("{company}", rec.get("company") or "")
                st.markdown(f"**Role:** {rec['title']}")
                st.markdown(f"**Company:** {rec.get('company') or '—'}")
                st.markdown(f"**Location:** {rec.get('location') or '—'}")
                if rec.get("job_url"):
                    st.markdown(f"[🔗 View Original Posting]({rec['job_url']})")
                cover_edit = st.text_area("Cover Letter", value=cover, height=100, key=f"rec_cover_{rec['id']}")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("CONFIRM & APPLY", key=f"rec_confirm_{rec['id']}"):
                        execute("""
                            INSERT INTO applications (user_id, job_id, cover_letter, resume_path)
                            VALUES (%s, %s, %s, %s)
                        """, (user["id"], rec["id"], cover_edit, profile.get("resume_path")))
                        st.session_state[f"confirm_{rec['id']}"] = False
                        st.success("Applied!")
                        st.rerun()
                with cc2:
                    if st.button("CANCEL", key=f"rec_cancel_{rec['id']}"):
                        st.session_state[f"confirm_{rec['id']}"] = False
                        st.rerun()

        st.markdown("<hr style='margin:4px 0;border-color:#1e2330'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN / REGISTER
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Login / Register":
    st.markdown("## ACCESS")

    tab_login, tab_register = st.tabs(["LOGIN", "REGISTER"])

    with tab_login:
        st.markdown("### Sign in")
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            submitted = st.form_submit_button("LOGIN")
            if submitted:
                if email and password:
                    user = login(email, password)
                    if user:
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.warning("Please enter email and password.")

    with tab_register:
        st.markdown("### Create account")
        with st.form("register_form"):
            r_name  = st.text_input("Full Name", key="reg_name")
            r_email = st.text_input("Email", key="reg_email")
            r_pw    = st.text_input("Password", type="password", key="reg_pw")
            r_pw2   = st.text_input("Confirm Password", type="password", key="reg_pw2")
            r_role  = st.selectbox("I am a", ["jobseeker", "employer"], key="reg_role")
            submitted = st.form_submit_button("CREATE ACCOUNT")
            if submitted:
                if not all([r_name, r_email, r_pw, r_pw2]):
                    st.warning("Please fill in all fields.")
                elif r_pw != r_pw2:
                    st.error("Passwords do not match.")
                elif len(r_pw) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    user, err = register(r_email, r_pw, r_name, r_role)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.user = user
                        st.success("Account created! Welcome.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MY PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "My Profile":
    user = require_login()
    if not user:
        st.warning("Please log in first.")
        st.stop()

    st.markdown(f"## PROFILE — {user['full_name'].upper()}")

    profile = query(
        "SELECT * FROM jobseeker_profiles WHERE user_id=%s",
        (user["id"],), fetch="one"
    ) or {}

    with st.form("profile_form"):
        st.markdown("### One-Click Apply Settings")

        c1, c2 = st.columns(2)
        with c1:
            title      = st.text_input("Current Title",       value=profile.get("current_title") or "")
            yoe        = st.number_input("Years Experience",  value=profile.get("years_experience") or 0, min_value=0, max_value=50)
            linkedin   = st.text_input("LinkedIn URL",        value=profile.get("linkedin_url") or "")
        with c2:
            skills     = st.text_input("Skills (comma-separated)", value=profile.get("skills") or "")
            github     = st.text_input("GitHub URL",          value=profile.get("github_url") or "")
            portfolio  = st.text_input("Portfolio URL",       value=profile.get("portfolio_url") or "")

        cover_tpl = st.text_area(
            "Cover Letter Template",
            value=profile.get("cover_letter_tpl") or "Hi, I'm interested in the {role} position at {company}. ",
            height=120,
            help="Use {role} and {company} as placeholders — filled automatically on apply."
        )

        resume_file = st.file_uploader("Resume (PDF)", type=["pdf"])

        if st.form_submit_button("SAVE PROFILE"):
            resume_path = profile.get("resume_path")
            if resume_file:
                save_path = RESUME_DIR / f"user_{user['id']}_{resume_file.name}"
                with open(save_path, "wb") as f:
                    f.write(resume_file.read())
                resume_path = str(save_path)

            if profile:
                execute("""
                    UPDATE jobseeker_profiles SET
                        current_title=%s, years_experience=%s, skills=%s,
                        linkedin_url=%s, github_url=%s, portfolio_url=%s,
                        cover_letter_tpl=%s, resume_path=%s, updated_at=NOW()
                    WHERE user_id=%s
                """, (title, yoe, skills, linkedin, github, portfolio,
                      cover_tpl, resume_path, user["id"]))
            else:
                execute("""
                    INSERT INTO jobseeker_profiles
                        (user_id, current_title, years_experience, skills,
                         linkedin_url, github_url, portfolio_url,
                         cover_letter_tpl, resume_path)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (user["id"], title, yoe, skills, linkedin, github,
                      portfolio, cover_tpl, resume_path))
            st.success("Profile saved!")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MY APPLICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "My Applications":
    user = require_login()
    if not user:
        st.warning("Please log in first.")
        st.stop()

    st.markdown("## MY APPLICATIONS")

    apps = query("""
        SELECT
            a.id, a.status, a.applied_at,
            COALESCE(j.title, ep.title)   AS title,
            COALESCE(j.company, ep.company) AS company,
            COALESCE(j.location, ep.location) AS location,
            COALESCE(j.source, 'employer') AS source
        FROM applications a
        LEFT JOIN jobs j           ON j.id  = a.job_id
        LEFT JOIN employer_posts ep ON ep.id = a.employer_post_id
        WHERE a.user_id = %s
        ORDER BY a.applied_at DESC
    """, (user["id"],))

    if not apps:
        st.info("You haven't applied to any jobs yet. Head to the Job Board!")
    else:
        # KPIs
        statuses = [a["status"] for a in apps]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Applied",   len(apps))
        c2.metric("Viewed",    statuses.count("viewed"))
        c3.metric("Interview", statuses.count("interview"))
        c4.metric("Rejected",  statuses.count("rejected"))

        st.markdown("---")

        status_colors = {
            "pending":   "🟡",
            "viewed":    "🔵",
            "interview": "🟢",
            "offered":   "✅",
            "rejected":  "🔴",
            "withdrawn": "⚫",
        }

        for app in apps:
            c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 2])
            c1.markdown(f"**{app['title']}**")
            c2.caption(app.get("company") or "—")
            c3.caption(app.get("location") or "—")
            c4.caption(f"{status_colors.get(app['status'], '⚪')} `{app['status'].upper()}`")
            c5.caption(str(app["applied_at"])[:10] if app["applied_at"] else "—")
            st.markdown("<hr style='margin:4px 0;border-color:#1e2330'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# POST A JOB
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Post a Job":
    user = require_login()
    if not user or user["role"] not in ("employer", "admin"):
        st.error("Employer account required.")
        st.stop()

    st.markdown("## POST A JOB")

    with st.form("post_job_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_title    = st.text_input("Job Title *")
            p_location = st.text_input("Location")
            p_type     = st.selectbox("Job Type", ["full-time", "part-time", "contract", "internship"])
            p_smin     = st.number_input("Salary Min (USD)", min_value=0, value=0)
            p_apply    = st.text_input("Apply URL")
            p_deadline = st.text_input("Deadline (YYYY-MM-DD)")
        with c2:
            p_company  = st.text_input("Company Name")
            p_country  = st.text_input("Country")
            p_category = st.selectbox("Category", ["Engineering", "Design", "Marketing", "Data", "DevOps", "Product", "Sales", "Other"])
            p_smax     = st.number_input("Salary Max (USD)", min_value=0, value=0)
            p_email    = st.text_input("Or Apply Email")

        p_skills = st.text_input("Required Skills (comma-separated)")
        p_desc   = st.text_area("Job Description *", height=200)

        if st.form_submit_button("PUBLISH JOB"):
            if not p_title or not p_desc:
                st.error("Title and Description are required.")
            else:
                deadline = None
                if p_deadline:
                    try:
                        deadline = datetime.strptime(p_deadline, "%Y-%m-%d").date()
                    except ValueError:
                        st.error("Deadline must be YYYY-MM-DD format.")
                        st.stop()

                execute("""
                    INSERT INTO employer_posts
                        (employer_id, title, company, location, country, job_type,
                         category, skills, description, salary_min, salary_max,
                         apply_url, apply_email, deadline)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    user["id"], p_title, p_company, p_location, p_country,
                    p_type, p_category, p_skills, p_desc,
                    p_smin or None, p_smax or None,
                    p_apply or None, p_email or None, deadline
                ))
                st.success("Job posted! It will appear after admin approval.")


# ═══════════════════════════════════════════════════════════════════════════════
# MY POSTINGS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "My Postings":
    user = require_login()
    if not user or user["role"] not in ("employer", "admin"):
        st.error("Employer account required.")
        st.stop()

    st.markdown("## MY POSTINGS")

    postings = query("""
        SELECT ep.*, COUNT(a.id) AS application_count
        FROM employer_posts ep
        LEFT JOIN applications a ON a.employer_post_id = ep.id
        WHERE ep.employer_id = %s
        GROUP BY ep.id
        ORDER BY ep.created_at DESC
    """, (user["id"],))

    if not postings:
        st.info("You haven't posted any jobs yet.")
    else:
        for p in postings:
            with st.expander(f"{'🟢' if p['is_active'] else '⚫'} {p['title']} — {p.get('company') or ''}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Applications", p["application_count"])
                c2.metric("Status", "LIVE" if p["is_active"] and p["is_approved"] else "PENDING" if not p["is_approved"] else "PAUSED")
                c3.metric("Posted", str(p["created_at"])[:10])
                c4.metric("Deadline", str(p.get("deadline") or "—"))

                st.caption(p.get("description") or "")

                bc1, bc2 = st.columns(2)
                with bc1:
                    if p["is_active"]:
                        if st.button("PAUSE", key=f"pause_{p['id']}"):
                            execute("UPDATE employer_posts SET is_active=FALSE WHERE id=%s", (p["id"],))
                            st.rerun()
                    else:
                        if st.button("ACTIVATE", key=f"activate_{p['id']}"):
                            execute("UPDATE employer_posts SET is_active=TRUE WHERE id=%s", (p["id"],))
                            st.rerun()
                with bc2:
                    if st.button("DELETE", key=f"delete_{p['id']}"):
                        execute("DELETE FROM employer_posts WHERE id=%s", (p["id"],))
                        st.rerun()

                # Show applicants
                applicants = query("""
                    SELECT u.full_name, u.email, a.status, a.applied_at, a.resume_path
                    FROM applications a
                    JOIN users u ON u.id = a.user_id
                    WHERE a.employer_post_id = %s
                    ORDER BY a.applied_at DESC
                """, (p["id"],))

                if applicants:
                    st.markdown("**Applicants**")
                    for ap in applicants:
                        ac1, ac2, ac3, ac4, ac5 = st.columns([3, 3, 2, 2, 2])
                        ac1.caption(ap["full_name"])
                        ac2.caption(ap["email"])
                        ac3.caption(f"`{ap['status'].upper()}`")
                        ac4.caption(str(ap["applied_at"])[:10])
                        # Status update
                        new_status = ac5.selectbox(
                            "", ["pending","viewed","interview","offered","rejected"],
                            index=["pending","viewed","interview","offered","rejected"].index(ap["status"]),
                            key=f"status_{p['id']}_{ap['email']}"
                        )
                        if new_status != ap["status"]:
                            execute("""
                                UPDATE applications SET status=%s, status_updated_at=NOW()
                                WHERE employer_post_id=%s AND user_id=(
                                    SELECT id FROM users WHERE email=%s
                                )
                            """, (new_status, p["id"], ap["email"]))
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPER LOGS  (admin only)
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Scraper Logs":
    user = require_login()
    if not user or user["role"] != "admin":
        st.error("Admin access required.")
        st.stop()

    st.markdown("## SCRAPER LOGS")

    # Run dedup manually
    if st.button("▶ RUN DEDUP NOW"):
        with st.spinner("Running deduplication..."):
            try:
                from scraper.utils.dedup import run_dedup
                result = run_dedup()
                st.success(
                    f"Done — exact removed: {result['exact_removed']}, "
                    f"auto-merged: {result['auto_merged']}, "
                    f"review queue: {result['flagged_for_review']}, "
                    f"duration: {result['duration_seconds']}s"
                )
            except Exception as e:
                st.error(f"Dedup failed: {e}")

    st.markdown("---")

    # Recent errors
    logs = query("""
        SELECT * FROM scraper_logs
        ORDER BY run_at DESC
        LIMIT 50
    """)

    if not logs:
        st.info("No scraper logs found.")
    else:
        errors   = [l for l in logs if l.get("status") == "error"]
        warnings = [l for l in logs if l.get("status") == "warning"]

        if errors:
            st.markdown("### ERRORS")
            for e in errors:
                st.error(f"**{e.get('scraper_name')}** — {e.get('message')}")

        if warnings:
            st.markdown("### WARNINGS")
            for w in warnings:
                st.warning(f"**{w.get('scraper_name')}** — {w.get('message')}")

        st.markdown("### FULL LOG")
        df = pd.DataFrame(logs)
        st.dataframe(df, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION  (admin only)
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Deduplication":
    user = require_login()
    if not user or user["role"] != "admin":
        st.error("Admin access required.")
        st.stop()

    st.markdown("## DEDUPLICATION")

    # Stats
    d1, d2, d3, d4 = st.columns(4)
    pending = query("SELECT COUNT(*) AS n FROM dedup_review WHERE status='pending'", fetch="one")
    merged  = query("SELECT COUNT(*) AS n FROM dedup_log", fetch="one")
    auto    = query("SELECT COUNT(*) AS n FROM dedup_log WHERE method='auto_fuzzy'", fetch="one")
    manual  = query("SELECT COUNT(*) AS n FROM dedup_log WHERE method='manual'", fetch="one")

    d1.metric("Pending Review", pending["n"] if pending else 0)
    d2.metric("Total Merged",   merged["n"]  if merged  else 0)
    d3.metric("Auto-merged",    auto["n"]    if auto    else 0)
    d4.metric("Manual Merges",  manual["n"]  if manual  else 0)

    st.markdown("---")
    st.markdown("### REVIEW QUEUE")

    try:
        from scraper.utils.dedup import get_review_queue, resolve_review
        queue = get_review_queue(limit=30)

        if not queue:
            st.success("Review queue is empty — no duplicates to resolve.")
        else:
            st.caption(f"{len(queue)} pairs awaiting review (sorted by similarity)")
            for item in queue:
                sim_pct = f"{float(item['similarity'])*100:.0f}%"
                with st.expander(f"{sim_pct} — {item['a_title']} · {item['a_company']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**A — Job #{item['a_id']}**")
                        st.markdown(f"**{item['a_title']}**")
                        st.caption(f"{item['a_company']} · {item['a_location']} · `{item['a_source']}`")
                    with c2:
                        st.markdown(f"**B — Job #{item['b_id']}**")
                        st.markdown(f"**{item['b_title']}**")
                        st.caption(f"{item['b_company']} · {item['b_location']} · `{item['b_source']}`")

                    bc1, bc2, bc3 = st.columns(3)
                    with bc1:
                        if st.button(f"MERGE (keep A)", key=f"ma_{item['review_id']}"):
                            resolve_review(item["review_id"], "merge", keep_id=item["a_id"])
                            st.rerun()
                    with bc2:
                        if st.button(f"MERGE (keep B)", key=f"mb_{item['review_id']}"):
                            resolve_review(item["review_id"], "merge", keep_id=item["b_id"])
                            st.rerun()
                    with bc3:
                        if st.button("KEEP BOTH", key=f"kb_{item['review_id']}"):
                            resolve_review(item["review_id"], "keep_both")
                            st.rerun()

    except Exception as e:
        st.error(f"Could not load review queue: {e}")
