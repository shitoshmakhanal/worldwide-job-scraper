import requests
import time
import random
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from loguru import logger
from scraper.base import BaseScraper

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

class WeWorkRemotelyScraper(BaseScraper):
    source   = "weworkremotely"
    country  = "Remote"
    region   = "Worldwide"
    base_url = "https://weworkremotely.com"

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def scrape(self) -> list:
        jobs = []
        categories = [
            ("/categories/remote-devops-sysadmin-jobs",  "DevOps"),
            ("/categories/remote-design-jobs",           "Design"),
            ("/categories/remote-full-stack-programming-jobs", "Full Stack"),
            ("/categories/remote-front-end-programming-jobs",  "Frontend"),
            ("/categories/remote-back-end-programming-jobs",   "Backend"),
        ]
        for path, cat_name in categories:
            logger.info(f"WWR scraping: {cat_name}")
            try:
                found = self._scrape_category(path, cat_name)
                jobs += found
                logger.info(f"  {cat_name}: {len(found)} jobs")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                logger.error(f"WWR failed {path}: {e}")
        return jobs

    def _scrape_category(self, path, cat_name):
        jobs = []
        res = requests.get(self.base_url + path, headers=self.get_headers(), timeout=15)
        if res.status_code != 200:
            logger.warning(f"  Status {res.status_code}")
            return jobs
        soup = BeautifulSoup(res.text, "lxml")
        cards = soup.select("li.new-listing-container")
        logger.info(f"  Cards found: {len(cards)}")
        for card in cards:
            title_tag   = card.select_one("h3.new-listing__header__title span")
            company_tag = card.select_one("h4.new-listing__header__company-name")
            region_tag  = card.select_one("span.new-listing__header__location")
            url_tag     = card.select_one("a.listing-link--unlocked, a[href*='/remote-jobs/']")
            title   = title_tag.text.strip()   if title_tag   else None
            company = company_tag.text.strip() if company_tag else None
            region  = region_tag.text.strip()  if region_tag  else "Remote"
            job_url = self.base_url + url_tag["href"] if url_tag else None
            if not title:
                continue
            jobs.append({
                "title": title, "company": company,
                "location": region, "salary_str": None,
                "salary_min": None, "salary_max": None,
                "salary_currency": "USD", "job_type": "Remote",
                "job_level": None, "category": cat_name,
                "skills": None, "description": None,
                "posted_date": None, "job_url": job_url,
                "source": self.source
            })
        return jobs

if __name__ == "__main__":
    from scraper.utils.db import init_db
    init_db()
    scraper = WeWorkRemotelyScraper()
    scraper.run()
    print(f"Done: {scraper.jobs_found} found, {scraper.jobs_new} new")
