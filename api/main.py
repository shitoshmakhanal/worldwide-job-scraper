from fastapi import FastAPI, Query
from sqlalchemy import text
from scraper.utils.db import SessionLocal, Job
from typing import Optional
import uvicorn

app = FastAPI(title="Worldwide Job Market API")

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

@app.get("/")
def root():
    db = SessionLocal()
    total = db.query(Job).count()
    sources = db.execute(text("SELECT source, COUNT(*) FROM jobs GROUP BY source")).fetchall()
    db.close()
    return {"total_jobs": total, "by_source": {r[0]: r[1] for r in sources}}

@app.get("/jobs")
def get_jobs(
    source: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    db = SessionLocal()
    q = db.query(Job)
    if source:
        q = q.filter(Job.source == source)
    if country:
        q = q.filter(Job.country.ilike(f"%{country}%"))
    if category:
        q = q.filter(Job.category.ilike(f"%{category}%"))
    if keyword:
        q = q.filter(Job.title.ilike(f"%{keyword}%"))
    total = q.count()
    jobs = q.offset(offset).limit(limit).all()
    db.close()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "jobs": [
            {"id": j.id, "title": j.title, "company": j.company,
             "location": j.location, "country": j.country,
             "salary": j.salary_raw, "category": j.category,
             "skills": j.skills, "source": j.source,
             "posted_date": j.posted_date, "job_url": j.job_url}
            for j in jobs
        ]
    }

@app.get("/stats")
def get_stats():
    db = SessionLocal()
    stats = db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT company) as companies,
            COUNT(DISTINCT location) as locations,
            COUNT(CASE WHEN salary_min IS NOT NULL THEN 1 END) as with_salary
        FROM jobs
    """)).fetchone()
    top_categories = db.execute(text("""
        SELECT category, COUNT(*) as cnt FROM jobs
        WHERE category IS NOT NULL
        GROUP BY category ORDER BY cnt DESC LIMIT 10
    """)).fetchall()
    top_locations = db.execute(text("""
        SELECT location, COUNT(*) as cnt FROM jobs
        WHERE location IS NOT NULL
        GROUP BY location ORDER BY cnt DESC LIMIT 10
    """)).fetchall()
    db.close()
    return {
        "total_jobs": stats[0],
        "unique_companies": stats[1],
        "unique_locations": stats[2],
        "jobs_with_salary": stats[3],
        "top_categories": [{"category": r[0], "count": r[1]} for r in top_categories],
        "top_locations": [{"location": r[0], "count": r[1]} for r in top_locations],
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
