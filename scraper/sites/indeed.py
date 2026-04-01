import requests
import time
import random
import re
from bs4 import BeautifulSoup
from loguru import logger
from scraper.base import BaseScraper


class IndeedScraper(BaseScraper):

    source   = "indeed"
    country  = "Worldwide"
    region   = "Worldwide"
    base_url = "https://www.indeed.com/jobs"

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.indeed.com",
        }

    def scrape(self) -> list:
        jobs = []

        # search queries — customize these for worldwide coverage
        searches = [
            {"q": "software engineer",  "l": ""},
            {"q": "data analyst",       "l": ""},
            {"q": "marketing manager",  "l": ""},
            {"q": "project manager",    "l": ""},
            {"q": "remote",             "l": "Remote"},
        ]

        for search in searches:
            logger.info(f"Indeed searching: {search['q']} | {search['l']}")
            try:
                jobs += self._scrape_search(search["q"], search["l"])
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.error(f"Indeed search failed for '{search['q']}': {e}")

        return jobs

    def _scrape_search(self, query: str, location: str, pages: int = 3) -> list:
        jobs = []

        for page in range(pages):
            start = page * 10
            params = {
                "q":    query,
                "l":    location,
                "start": start,
                "remotejob": "032b3046-06a3-4876-8dfd-474eb5e7ed11" if location == "Remote" else ""
            }

            try:
                res = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=15
                )
                logger.info(f"  Page {page+1} status: {res.status_code}")

                if res.status_code != 200:
                    break

                soup = BeautifulSoup(res.text, "lxml")

                # Indeed job cards
                cards = soup.select("div.job_seen_beacon, div.cardOutline, td.resultContent")
                logger.info(f"  Cards found: {len(cards)}")

                if not cards:
                    break

                for card in cards:
                    title_tag    = card.select_one("h2.jobTitle a, h2.jobTitle span")
                    company_tag  = card.select_one("span.companyName, [data-testid='company-name']")
                    location_tag = card.select_one("div.companyLocation, [data-testid='text-location']")
                    salary_tag   = card.select_one("div.salary-snippet-container, [data-testid='attribute_snippet_testid']")
                    url_tag      = card.select_one("h2.jobTitle a")

                    title    = title_tag.text.strip()    if title_tag    else None
                    company  = company_tag.text.strip()  if company_tag  else None
                    location = location_tag.text.strip() if location_tag else None
                    salary   = salary_tag.text.strip()   if salary_tag   else None
                    job_url  = "https://www.indeed.com" + url_tag["href"] if url_tag and url_tag.get("href") else None

                    if not title:
                        continue

                    # parse salary
                    sal_min = sal_max = None
                    if salary:
                        nums = re.findall(r'[\d,]+', salary.replace(",", ""))
                        nums = [int(n) for n in nums if len(n) >= 4]
                        if len(nums) >= 2:
                            sal_min, sal_max = nums[0], nums[1]
                        elif len(nums) == 1:
                            sal_min = sal_max = nums[0]

                    jobs.append({
                        "title":           title,
                        "company":         company,
                        "location":        location,
                        "salary_str":      salary,
                        "salary_min":      sal_min,
                        "salary_max":      sal_max,
                        "salary_currency": "USD",
                        "job_type":        None,
                        "job_level":       None,
                        "category":        query,
                        "skills":          None,
                        "description":     None,
                        "posted_date":     None,
                        "job_url":         job_url,
                        "source":          self.source
                    })

                time.sleep(random.uniform(3, 5))

            except Exception as e:
                logger.error(f"  Page {page+1} error: {e}")
                break

        logger.info(f"  '{query}': {len(jobs)} jobs collected")
        return jobs


if __name__ == "__main__":
    from scraper.utils.db import init_db
    init_db()
    scraper = IndeedScraper()
    scraper.run()
    print(f"Done: {scraper.jobs_found} found, {scraper.jobs_new} new")