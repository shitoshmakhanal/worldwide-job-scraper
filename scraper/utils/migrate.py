"""
scraper/utils/migrate.py
One-time migration: adds users, employer_posts, and applications tables.
Safe to re-run — uses CREATE TABLE IF NOT EXISTS throughout.

Run with:
    python -m scraper.utils.migrate
"""

import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

def get_db_config():
    return {
        "dbname":   os.getenv("DB_NAME", "worldjobs"),
        "user":     os.getenv("DB_USER", "jobscraper"),
        "password": os.getenv("DB_PASSWORD"),
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 5432)),
    }

import psycopg2.extras
from datetime import datetime, timezone

DB_CONFIG = get_db_config()

MIGRATIONS = []

def migration(fn):
    MIGRATIONS.append(fn)
    return fn


# ── 1. users ──────────────────────────────────────────────────────────────────
@migration
def create_users(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              SERIAL PRIMARY KEY,
            email           VARCHAR(255) NOT NULL UNIQUE,
            password_hash   VARCHAR(255) NOT NULL,
            full_name       VARCHAR(255),
            role            VARCHAR(20)  NOT NULL DEFAULT 'jobseeker',
                            -- 'jobseeker' | 'employer' | 'admin'
            is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
            last_login      TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email
        ON users (email);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_role
        ON users (role);
    """)
    print("  ✓ users")


# ── 2. jobseeker_profiles ─────────────────────────────────────────────────────
@migration
def create_jobseeker_profiles(cur):
    """
    Stores the one-click apply profile — resume path, cover letter template,
    skills, links. One row per user (jobseeker).
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobseeker_profiles (
            id                  SERIAL PRIMARY KEY,
            user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            current_title       VARCHAR(255),
            years_experience    INTEGER,
            skills              TEXT,           -- comma-separated
            resume_path         VARCHAR(500),   -- path to uploaded PDF
            linkedin_url        VARCHAR(500),
            github_url          VARCHAR(500),
            portfolio_url       VARCHAR(500),
            cover_letter_tpl    TEXT,           -- template with {role} {company} placeholders
            preferred_location  VARCHAR(255),
            preferred_job_type  VARCHAR(100),   -- 'remote' | 'onsite' | 'hybrid'
            updated_at          TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id)
        );
    """)
    print("  ✓ jobseeker_profiles")


# ── 3. employer_profiles ──────────────────────────────────────────────────────
@migration
def create_employer_profiles(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employer_profiles (
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company_name    VARCHAR(255) NOT NULL,
            company_website VARCHAR(500),
            company_logo    VARCHAR(500),
            company_size    VARCHAR(100),   -- e.g. '1-10', '11-50', '51-200', '200+'
            industry        VARCHAR(255),
            description     TEXT,
            verified        BOOLEAN DEFAULT FALSE,
            updated_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id)
        );
    """)
    print("  ✓ employer_profiles")


# ── 4. employer_posts ─────────────────────────────────────────────────────────
@migration
def create_employer_posts(cur):
    """
    Jobs posted directly by employers through the dashboard.
    Separate from the `jobs` table (scraped jobs) but can be joined with it
    for unified search — or inserted into `jobs` with source='employer'.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employer_posts (
            id              SERIAL PRIMARY KEY,
            employer_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title           VARCHAR(500) NOT NULL,
            company         VARCHAR(500),       -- denormalised for fast queries
            location        VARCHAR(500),
            country         VARCHAR(100),
            region          VARCHAR(100),
            job_type        VARCHAR(100),       -- 'full-time'|'part-time'|'contract'|'internship'
            category        VARCHAR(300),
            skills          TEXT,               -- comma-separated
            description     TEXT,
            salary_min      DOUBLE PRECISION,
            salary_max      DOUBLE PRECISION,
            salary_currency VARCHAR(10) DEFAULT 'USD',
            apply_url       VARCHAR(1000),      -- external apply link
            apply_email     VARCHAR(255),       -- or email to apply to
            deadline        DATE,
            is_active       BOOLEAN DEFAULT TRUE,
            is_approved     BOOLEAN DEFAULT FALSE,  -- admin approval before going live
            views           INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_employer_posts_employer
        ON employer_posts (employer_id);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_employer_posts_active
        ON employer_posts (is_active, is_approved);
    """)
    print("  ✓ employer_posts")


# ── 5. jobs (scraped listings) ───────────────────────────────────────────────
@migration
def create_jobs(cur):
    """
    Raw scraped job listings from external job boards.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id                  SERIAL PRIMARY KEY,
            title               VARCHAR(255) NOT NULL,
            company             VARCHAR(255),
            location            VARCHAR(255),
            country             VARCHAR(100),
            region              VARCHAR(100),
            job_type            VARCHAR(50),
            category            VARCHAR(100),
            skills              TEXT,
            salary_min          NUMERIC,
            salary_max          NUMERIC,
            salary_currency     VARCHAR(10),
            job_url             VARCHAR(1000),
            source              VARCHAR(100),
            posted_date         VARCHAR(100),
            is_active           BOOLEAN DEFAULT TRUE,
            scraped_at          TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_active
        ON jobs (is_active);
    """)
    print("  ✓ jobs")


# ── 6. applications ───────────────────────────────────────────────────────────
@migration
def create_applications(cur):
    """
    Tracks one-click applications. Can reference either a scraped job (job_id)
    or an employer post (employer_post_id) — one of the two will be set.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id                  SERIAL PRIMARY KEY,
            user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id              INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
            employer_post_id    INTEGER REFERENCES employer_posts(id) ON DELETE SET NULL,
            status              VARCHAR(50) DEFAULT 'pending',
                                -- 'pending'|'viewed'|'interview'|'offered'|'rejected'|'withdrawn'
            cover_letter        TEXT,       -- rendered from template at apply time
            resume_path         VARCHAR(500),
            applied_at          TIMESTAMP DEFAULT NOW(),
            status_updated_at   TIMESTAMP DEFAULT NOW(),
            notes               TEXT,       -- employer notes (internal)
            CONSTRAINT chk_one_job CHECK (
                (job_id IS NOT NULL)::int + (employer_post_id IS NOT NULL)::int = 1
            )
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_user
        ON applications (user_id);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_status
        ON applications (status);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_job
        ON applications (job_id);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_employer_post
        ON applications (employer_post_id);
    """)
    print("  ✓ applications")


# ── 7. post_views (optional analytics) ───────────────────────────────────────
@migration
def create_post_views(cur):
    """
    Lightweight view counter per employer post per day.
    Powers the 'Views: 142' stat in the dashboard.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS post_views (
            id              SERIAL PRIMARY KEY,
            post_id         INTEGER NOT NULL REFERENCES employer_posts(id) ON DELETE CASCADE,
            viewed_at       DATE NOT NULL DEFAULT CURRENT_DATE,
            view_count      INTEGER DEFAULT 1,
            UNIQUE (post_id, viewed_at)
        );
    """)
    print("  ✓ post_views")


# ── 8. Stamp existing jobs with source='employer' helper view ─────────────────
@migration
def create_unified_jobs_view(cur):
    """
    A VIEW that merges scraped jobs + approved employer posts into one
    queryable surface — used by the dashboard job board page.
    """
    cur.execute("DROP VIEW IF EXISTS unified_jobs;")
    cur.execute("""
        CREATE VIEW unified_jobs AS
            SELECT
                id,
                title,
                company,
                location,
                country,
                region,
                job_type,
                category,
                skills,
                salary_min,
                salary_max,
                salary_currency,
                job_url         AS apply_url,
                source,
                posted_date,
                scraped_at      AS created_at,
                is_active
            FROM jobs
            WHERE is_active = TRUE

        UNION ALL

            SELECT
                ep.id + 1000000 AS id,   -- offset to avoid PK clash in UI
                ep.title,
                COALESCE(ep.company, epr.company_name) AS company,
                ep.location,
                ep.country,
                ep.region,
                ep.job_type,
                ep.category,
                ep.skills,
                ep.salary_min,
                ep.salary_max,
                ep.salary_currency,
                COALESCE(ep.apply_url, ep.apply_email) AS apply_url,
                'employer'      AS source,
                ep.created_at::text AS posted_date,
                ep.created_at,
                ep.is_active
            FROM employer_posts ep
            LEFT JOIN employer_profiles epr ON epr.user_id = ep.employer_id
            WHERE ep.is_active = TRUE AND ep.is_approved = TRUE;
    """)
    print("  ✓ unified_jobs (view)")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_migrations():
    print("\n=== WorldJobs DB Migration ===")
    print(f"    DB: worldjobs @ localhost:5432")
    print(f"    Running {len(MIGRATIONS)} migrations...\n")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            for fn in MIGRATIONS:
                fn(cur)
        conn.commit()
        print("\n All migrations complete.\n")
        print("New tables created:")
        print("  • users")
        print("  • jobseeker_profiles")
        print("  • employer_profiles")
        print("  • employer_posts")
        print("  • jobs")
        print("  • applications")
        print("  • post_views")
        print("  • unified_jobs  (VIEW — merges scraped + employer jobs)\n")
        print("Next step: run the Streamlit app rebuild.")

    except Exception as e:
        conn.rollback()
        print(f"\n Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()