from abc import ABC, abstractmethod
from loguru import logger
from sqlalchemy.orm import Session
from scraper.utils.db import Job, ScraperLog, SessionLocal
import hashlib


class BaseScraper(ABC):

    source   = None
    country  = None
    region   = None
    base_url = None

    def __init__(self):
        self.db         = SessionLocal()
        self.jobs_found = 0
        self.jobs_new   = 0
        logger.info(f"Initialised scraper: {self.source}")

    @abstractmethod
    def scrape(self) -> list:
        pass

    def job_exists(self, title: str, company: str) -> bool:
        h = hashlib.md5(
            f"{title}{company}{self.source}".encode()
        ).hexdigest()
        return self.db.query(Job).filter(Job.job_url == h).first() is not None

    def save_job(self, job: dict) -> bool:
        try:
            title   = job.get("title", "")
            company = job.get("company", "")

            if self.job_exists(title, company):
                return False

            h = hashlib.md5(
                f"{title}{company}{self.source}".encode()
            ).hexdigest()

            record = Job(
                title           = title,
                company         = company,
                location        = job.get("location"),
                country         = self.country,
                region          = self.region,
                salary_raw      = job.get("salary_str"),
                salary_min      = job.get("salary_min"),
                salary_max      = job.get("salary_max"),
                salary_currency = job.get("salary_currency", "USD"),
                job_type        = job.get("job_type"),
                job_level       = job.get("job_level"),
                category        = job.get("category"),
                skills          = job.get("skills"),
                description     = job.get("description"),
                deadline        = job.get("deadline"),
                posted_date     = job.get("posted_date"),
                job_url         = job.get("job_url", h),
                source          = self.source,
                is_active       = True
            )
            self.db.add(record)
            self.db.commit()
            self.jobs_new += 1
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save job '{job.get('title')}': {e}")
            return False

    def run(self):
        logger.info(f"Starting {self.source} scraper...")
        status = "success"
        error  = None
        try:
            jobs = self.scrape()
            self.jobs_found = len(jobs)
            for job in jobs:
                self.save_job(job)
            logger.success(
                f"{self.source}: {self.jobs_found} found, "
                f"{self.jobs_new} new saved"
            )
        except Exception as e:
            status = "failed"
            error  = str(e)
            logger.error(f"{self.source} scraper failed: {e}")
        finally:
            log = ScraperLog(
                source     = self.source,
                jobs_found = self.jobs_found,
                jobs_new   = self.jobs_new,
                status     = status,
                error      = error
            )
            self.db.add(log)
            self.db.commit()
            self.db.close()