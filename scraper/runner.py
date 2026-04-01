from scraper.sites.remoteok import RemoteOKScraper
from scraper.sites.weworkremotely import WeWorkRemotelyScraper
from scraper.sites.linkedin import LinkedInScraper
from scraper.utils.db import init_db, SessionLocal, Job
from scraper.utils.dedup import run_dedup
from loguru import logger

SCRAPERS = [
    RemoteOKScraper,
    WeWorkRemotelyScraper,
    LinkedInScraper,
]

def run_all():
    init_db()
    logger.info("Starting all scrapers...")
    total_new = 0
    for ScraperClass in SCRAPERS:
        try:
            scraper = ScraperClass()
            scraper.run()
            total_new += scraper.jobs_new
        except Exception as e:
            logger.error(f"{ScraperClass.__name__} failed: {e}")
    db = SessionLocal()
    total = db.query(Job).count()
    db.close()
    logger.success(f"All done. {total_new} new jobs this run. {total} total in database.")

def expire_old_jobs():
    from scraper.utils.db import SessionLocal
    import sqlalchemy
    db = SessionLocal()
    result = db.execute(sqlalchemy.text(
        "UPDATE jobs SET is_active=FALSE WHERE scraped_at < NOW() - INTERVAL '30 days' AND is_active=TRUE"
    ))
    db.commit()
    count = result.rowcount
    db.close()
    logger.info(f"Expired {count} jobs older than 30 days.")

if __name__ == "__main__":
    run_all()
    expire_old_jobs()
    run_dedup()
