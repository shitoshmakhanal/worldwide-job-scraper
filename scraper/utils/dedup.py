"""
scraper/utils/dedup.py
Deduplication module for the worldjobs database.

Algorithm:
  1. Exact-match dedupe  — same (title_normalized, company_normalized, source)
  2. Fuzzy-match dedupe  — title similarity >= FUZZY_THRESHOLD + same company_normalized

Run standalone:  python -m scraper.utils.dedup
Or import:       from scraper.utils.dedup import run_dedup
"""

import re
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional
from itertools import groupby
from operator import itemgetter

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

DB_CONFIG = get_db_config()

FUZZY_THRESHOLD = 0.70
AUTO_MERGE_THRESHOLD = 0.95

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [dedup] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def normalise(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.lower()
    abbrevs = {
        r"\bsr\.?\b": "senior", r"\bjr\.?\b": "junior",
        r"\beng\.?\b": "engineer", r"\bdev\.?\b": "developer",
        r"\bmgr\.?\b": "manager", r"\bvp\b": "vice president",
    }
    for pattern, replacement in abbrevs.items():
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_dedup_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dedup_log (
            id          SERIAL PRIMARY KEY,
            kept_id     INTEGER NOT NULL,
            removed_id  INTEGER NOT NULL,
            similarity  NUMERIC(5,4),
            method      TEXT,
            merged_at   TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dedup_review (
            id          SERIAL PRIMARY KEY,
            job_a_id    INTEGER NOT NULL,
            job_b_id    INTEGER NOT NULL,
            similarity  NUMERIC(5,4),
            status      TEXT DEFAULT 'pending',
            created_at  TIMESTAMP DEFAULT NOW(),
            resolved_at TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_dedup_review_status
        ON dedup_review (status);
    """)


def log_scraper_event(cur, scraper, status, message, jobs_added=0):
    try:
        cur.execute("""
            INSERT INTO scraper_logs (scraper_name, status, message, jobs_added, run_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (scraper, status, message, jobs_added, datetime.now(timezone.utc)))
    except Exception:
        pass


def dedupe_exact(cur) -> int:
    log.info("Running exact deduplication...")
    cur.execute("""
        DELETE FROM jobs
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            LOWER(REGEXP_REPLACE(title,   '[^\\w\\s]', '', 'g')),
                            LOWER(REGEXP_REPLACE(company, '[^\\w\\s]', '', 'g')),
                            source
                        ORDER BY id ASC
                    ) AS rn
                FROM jobs
            ) ranked
            WHERE rn > 1
        )
        RETURNING id;
    """)
    removed = cur.rowcount
    log.info(f"Exact dedup: removed {removed} rows.")
    return removed


def already_flagged(cur, id_a, id_b) -> bool:
    cur.execute("""
        SELECT 1 FROM dedup_review
        WHERE (job_a_id=%s AND job_b_id=%s) OR (job_a_id=%s AND job_b_id=%s)
        LIMIT 1
    """, (id_a, id_b, id_b, id_a))
    if cur.fetchone():
        return True
    cur.execute("""
        SELECT 1 FROM dedup_log
        WHERE (kept_id=%s AND removed_id=%s) OR (kept_id=%s AND removed_id=%s)
        LIMIT 1
    """, (id_a, id_b, id_b, id_a))
    return bool(cur.fetchone())


def merge_jobs(cur, keep_id, remove_id, sim, method):
    cur.execute("DELETE FROM jobs WHERE id = %s", (remove_id,))
    cur.execute("""
        INSERT INTO dedup_log (kept_id, removed_id, similarity, method)
        VALUES (%s, %s, %s, %s)
    """, (keep_id, remove_id, round(sim, 4), method))


def flag_for_review(cur, id_a, id_b, sim):
    cur.execute("""
        INSERT INTO dedup_review (job_a_id, job_b_id, similarity)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (id_a, id_b, round(sim, 4)))


def dedupe_fuzzy(cur) -> tuple[int, int]:
    log.info("Running fuzzy deduplication...")
    cur.execute("""
        SELECT id, title, company,
               LOWER(REGEXP_REPLACE(title,   '[^\\w\\s]', '', 'g')) AS title_norm,
               LOWER(REGEXP_REPLACE(company, '[^\\w\\s]', '', 'g')) AS company_norm
        FROM jobs
        ORDER BY company_norm, id
    """)
    all_jobs = [dict(row) for row in cur.fetchall()]

    auto_merged = 0
    flagged = 0
    deleted_ids: set[int] = set()

    for company_norm, group in groupby(all_jobs, key=itemgetter("company_norm")):
        jobs = [j for j in group if j["id"] not in deleted_ids]
        if len(jobs) < 2:
            continue
        for i in range(len(jobs)):
            for j in range(i + 1, len(jobs)):
                a, b = jobs[i], jobs[j]
                if a["id"] in deleted_ids or b["id"] in deleted_ids:
                    continue
                if already_flagged(cur, a["id"], b["id"]):
                    continue
                sim = similarity(a["title_norm"], b["title_norm"])
                if sim >= AUTO_MERGE_THRESHOLD:
                    keep, remove = (a, b) if a["id"] < b["id"] else (b, a)
                    merge_jobs(cur, keep["id"], remove["id"], sim, "auto_fuzzy")
                    deleted_ids.add(remove["id"])
                    auto_merged += 1
                    log.debug(f"Auto-merged: '{a['title']}' + '{b['title']}' (sim={sim:.2f})")
                elif sim >= FUZZY_THRESHOLD:
                    flag_for_review(cur, a["id"], b["id"], sim)
                    flagged += 1
                    log.debug(f"Flagged: '{a['title']}' vs '{b['title']}' (sim={sim:.2f})")

    log.info(f"Fuzzy dedup: auto_merged={auto_merged}, flagged={flagged}")
    return auto_merged, flagged


def get_review_queue(limit=50) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    r.id AS review_id, r.similarity,
                    a.id AS a_id, a.title AS a_title, a.company AS a_company,
                    a.location AS a_location, a.source AS a_source,
                    b.id AS b_id, b.title AS b_title, b.company AS b_company,
                    b.location AS b_location, b.source AS b_source
                FROM dedup_review r
                JOIN jobs a ON a.id = r.job_a_id
                JOIN jobs b ON b.id = r.job_b_id
                WHERE r.status = 'pending'
                ORDER BY r.similarity DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]


def resolve_review(review_id: int, action: str, keep_id: Optional[int] = None):
    assert action in ("merge", "keep_both")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT job_a_id, job_b_id, similarity
                FROM dedup_review WHERE id = %s
            """, (review_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Review ID {review_id} not found.")
            a_id, b_id, sim = row
            if action == "merge":
                if keep_id not in (a_id, b_id):
                    raise ValueError("keep_id must be one of the two job IDs.")
                remove_id = b_id if keep_id == a_id else a_id
                merge_jobs(cur, keep_id, remove_id, sim, "manual")
            cur.execute("""
                UPDATE dedup_review
                SET status=%s, resolved_at=NOW()
                WHERE id=%s
            """, ("merged" if action == "merge" else "keep_both", review_id))
        conn.commit()


def run_dedup(log_to_db=True) -> dict:
    start = datetime.now(timezone.utc)
    log.info("=== Deduplication run starting ===")
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            ensure_dedup_tables(cur)
            conn.commit()
            exact_removed = dedupe_exact(cur)
            conn.commit()
            auto_merged, flagged = dedupe_fuzzy(cur)
            conn.commit()
            duration = (datetime.now(timezone.utc) - start).seconds
            summary = {
                "exact_removed": exact_removed,
                "auto_merged": auto_merged,
                "flagged_for_review": flagged,
                "duration_seconds": duration,
                "ran_at": start.isoformat(),
            }
            if log_to_db:
                log_scraper_event(cur, "dedup", "success",
                    f"exact={exact_removed}, auto_merged={auto_merged}, review={flagged}, duration={duration}s")
                conn.commit()
    log.info(f"=== Dedup done — {summary} ===")
    return summary


if __name__ == "__main__":
    result = run_dedup()
    print("\nSummary:")
    for k, v in result.items():
        print(f"  {k}: {v}")
