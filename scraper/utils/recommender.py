"""
scraper/utils/recommender.py
Job recommendation engine for WorldJobs.

Since most jobs (~90%) have no skills field, we match on:
  - User profile skills (comma-separated)
  - User profile current_title
  - Job title + category + skills (all combined into one text blob)

Algorithm: TF-IDF cosine similarity — no external APIs, runs fully local.

Usage:
    from scraper.utils.recommender import get_recommendations
    jobs = get_recommendations(user_id=1, limit=20)
"""

import os
import re
import math
from collections import Counter
from typing import Optional
import psycopg2
import psycopg2.extras
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


# ── Text helpers ──────────────────────────────────────────────────────────────

STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do",
    "does","did","will","would","could","should","may","might","shall",
    "this","that","these","those","i","you","he","she","it","we","they",
    "job","jobs","position","role","work","opportunity","experience",
    "required","preferred","team","company","looking","join","help",
}

def tokenise(text: str) -> list[str]:
    """Lowercase, remove punctuation, split, remove stopwords."""
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def build_job_text(job: dict) -> str:
    """Combine all searchable job fields into one text blob."""
    parts = [
        job.get("title") or "",
        job.get("category") or "",
        job.get("skills") or "",
        job.get("company") or "",
        job.get("location") or "",
        job.get("country") or "",
        job.get("region") or "",
        job.get("job_type") or "",
    ]
    return " ".join(p for p in parts if p)


def build_user_text(profile: dict) -> str:
    """Combine user profile into a query text blob."""
    parts = [
        profile.get("current_title") or "",
        profile.get("skills") or "",
        profile.get("preferred_location") or "",
        profile.get("preferred_job_type") or "",
    ]
    return " ".join(p for p in parts if p)


# ── TF-IDF ────────────────────────────────────────────────────────────────────

def compute_tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {word: count / total for word, count in counts.items()}


def compute_idf(documents: list[list[str]]) -> dict[str, float]:
    n = len(documents)
    df: dict[str, int] = {}
    for doc in documents:
        for word in set(doc):
            df[word] = df.get(word, 0) + 1
    return {
        word: math.log((n + 1) / (freq + 1)) + 1
        for word, freq in df.items()
    }


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = compute_tf(tokens)
    return {word: tf_val * idf.get(word, 1.0) for word, tf_val in tf.items()}


def cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[w] * vec_b[w] for w in common)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Keyword boost ─────────────────────────────────────────────────────────────

def keyword_boost(user_tokens: set, job: dict) -> float:
    """
    Extra score boost when user skill keywords appear directly in job title.
    Rewards exact title matches more heavily than category matches.
    """
    title_tokens = set(tokenise(job.get("title") or ""))
    overlap = user_tokens & title_tokens
    return len(overlap) * 0.05  # 0.05 boost per matching keyword in title


# ── Location preference boost ─────────────────────────────────────────────────

def location_boost(profile: dict, job: dict) -> float:
    """Boost jobs that match user's preferred location / job type."""
    boost = 0.0
    pref_loc = (profile.get("preferred_location") or "").lower()
    pref_type = (profile.get("preferred_job_type") or "").lower()

    job_country = (job.get("country") or "").lower()
    job_region = (job.get("region") or "").lower()
    job_type = (job.get("job_type") or "").lower()
    job_loc = (job.get("location") or "").lower()

    if pref_loc and (pref_loc in job_country or pref_loc in job_region or pref_loc in job_loc):
        boost += 0.15
    if pref_type and pref_type in job_type:
        boost += 0.10
    if "remote" in job_region or "remote" in job_loc:
        boost += 0.05  # slight boost for remote jobs (widely preferred)

    return boost


# ── Main recommendation function ──────────────────────────────────────────────

def get_recommendations(
    user_id: int,
    limit: int = 20,
    exclude_applied: bool = True,
    min_score: float = 0.05,
) -> list[dict]:
    """
    Returns ranked list of recommended jobs for a user.

    Args:
        user_id:         ID from the users table
        limit:           Max number of recommendations to return
        exclude_applied: Skip jobs the user already applied to
        min_score:       Minimum similarity score to include

    Returns:
        List of job dicts with added 'score' and 'match_reasons' fields
    """
    conn = psycopg2.connect(**get_db_config())
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Load user profile
        cur.execute("""
            SELECT jp.*, u.full_name
            FROM jobseeker_profiles jp
            JOIN users u ON u.id = jp.user_id
            WHERE jp.user_id = %s
        """, (user_id,))
        profile = cur.fetchone()

        if not profile:
            return []

        profile = dict(profile)
        user_text = build_user_text(profile)
        user_tokens = tokenise(user_text)

        if not user_tokens:
            return []

        user_token_set = set(user_tokens)

        # Get jobs the user already applied to (to exclude)
        applied_ids = set()
        if exclude_applied:
            cur.execute(
                "SELECT job_id FROM applications WHERE user_id=%s AND job_id IS NOT NULL",
                (user_id,)
            )
            applied_ids = {r["job_id"] for r in cur.fetchall()}

        # Load active jobs
        cur.execute("""
            SELECT id, title, company, location, country, region,
                   job_type, category, skills, salary_min, salary_max,
                   salary_currency, job_url, source, scraped_at
            FROM jobs
            WHERE is_active = TRUE
            ORDER BY scraped_at DESC
            LIMIT 3000
        """)
        jobs = [dict(r) for r in cur.fetchall()]

    finally:
        conn.close()

    if not jobs:
        return []

    # Build corpus for IDF
    job_tokens_list = [tokenise(build_job_text(j)) for j in jobs]
    all_docs = [user_tokens] + job_tokens_list
    idf = compute_idf(all_docs)

    # User vector
    user_vec = tfidf_vector(user_tokens, idf)

    # Score each job
    scored = []
    for job, job_tokens in zip(jobs, job_tokens_list):
        if job["id"] in applied_ids:
            continue

        job_vec = tfidf_vector(job_tokens, idf)
        sim = cosine_similarity(user_vec, job_vec)

        # Apply boosts
        sim += keyword_boost(user_token_set, job)
        sim += location_boost(profile, job)

        if sim >= min_score:
            # Build match reason tags
            reasons = []
            title_overlap = user_token_set & set(tokenise(job.get("title") or ""))
            skill_overlap = user_token_set & set(tokenise(job.get("skills") or ""))
            cat_overlap = user_token_set & set(tokenise(job.get("category") or ""))

            if title_overlap:
                reasons.append(f"Title match: {', '.join(list(title_overlap)[:3])}")
            if skill_overlap:
                reasons.append(f"Skills: {', '.join(list(skill_overlap)[:3])}")
            if cat_overlap:
                reasons.append(f"Category: {', '.join(list(cat_overlap)[:3])}")
            pref_loc = (profile.get("preferred_location") or "").lower()
            if pref_loc and pref_loc in (job.get("country") or "").lower():
                reasons.append(f"Location: {job.get('country')}")
            if "remote" in (job.get("region") or "").lower():
                reasons.append("Remote")

            scored.append({
                **job,
                "score": round(sim, 4),
                "match_reasons": reasons,
            })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def get_similar_jobs(job_id: int, limit: int = 6) -> list[dict]:
    """
    Given a job ID, return similar jobs.
    Used for 'You might also like' on job detail view.
    """
    conn = psycopg2.connect(**get_db_config())
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, title, company, location, country, region,
                   job_type, category, skills, salary_min, salary_max,
                   salary_currency, job_url, source, scraped_at
            FROM jobs WHERE is_active=TRUE
            ORDER BY scraped_at DESC LIMIT 2000
        """)
        all_jobs = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    target = next((j for j in all_jobs if j["id"] == job_id), None)
    if not target:
        return []

    job_tokens_list = [tokenise(build_job_text(j)) for j in all_jobs]
    idf = compute_idf(job_tokens_list)

    target_idx = next(i for i, j in enumerate(all_jobs) if j["id"] == job_id)
    target_vec = tfidf_vector(job_tokens_list[target_idx], idf)

    scored = []
    for i, (job, tokens) in enumerate(zip(all_jobs, job_tokens_list)):
        if job["id"] == job_id:
            continue
        sim = cosine_similarity(target_vec, tfidf_vector(tokens, idf))
        if sim > 0.1:
            scored.append({**job, "score": round(sim, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


if __name__ == "__main__":
    # Quick test — pass a user_id that exists in your DB
    import sys
    uid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    recs = get_recommendations(uid, limit=10)
    print(f"\nTop {len(recs)} recommendations for user {uid}:\n")
    for r in recs:
        print(f"  [{r['score']:.3f}] {r['title']} @ {r['company']} — {r['location']}")
        if r['match_reasons']:
            print(f"           ↳ {' | '.join(r['match_reasons'])}")
