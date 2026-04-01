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

if __name__ == "__main__":
    run_all()
    run_dedup()
