import requests
import time
import random
from loguru import logger
from scraper.base import BaseScraper


class RemoteOKScraper(BaseScraper):

    source   = "remoteok"
    country  = "Remote"
    region   = "Worldwide"
    base_url = "https://remoteok.com/api"

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    def scrape(self) -> list[dict]:
        jobs = []
        logger.info("Fetching RemoteOK API...")

        try:
            # RemoteOK requires a small delay before first request
            time.sleep(2)
            res = requests.get(
                self.base_url,
                headers=self.get_headers(),
                timeout=15
            )
            res.raise_for_status()
            data = res.json()

            # first item is always a legal notice, skip it
            data = [item for item in data if item.get("id")]

            logger.info(f"RemoteOK: {len(data)} jobs fetched from API")

            for item in data:
                # skills is a list in remoteok
                skills = item.get("tags", [])
                skills_str = ", ".join(skills) if skills else None

                # salary
                sal_min = item.get("salary_min")
                sal_max = item.get("salary_max")
                if sal_min and sal_max:
                    sal_str = f"${sal_min:,} - ${sal_max:,} / year"
                elif sal_min:
                    sal_str = f"${sal_min:,}+ / year"
                else:
                    sal_str = None

                jobs.append({
                    "title":           item.get("position"),
                    "company":         item.get("company"),
                    "location":        item.get("location") or "Remote",
                    "salary_str":      sal_str,
                    "salary_min":      sal_min,
                    "salary_max":      sal_max,
                    "salary_currency": "USD",
                    "job_type":        "Remote",
                    "job_level":       None,
                    "category":        ", ".join(item.get("tags", [])[:3]),
                    "skills":          skills_str,
                    "description":     item.get("description"),
                    "posted_date":     item.get("date"),
                    "job_url":         item.get("url"),
                    "source":          self.source
                })

                time.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            logger.error(f"RemoteOK scrape failed: {e}")

        return jobs


if __name__ == "__main__":
    from scraper.utils.db import init_db
    init_db()
    scraper = RemoteOKScraper()
    scraper.run()
    print(f"Done: {scraper.jobs_found} found, {scraper.jobs_new} new")