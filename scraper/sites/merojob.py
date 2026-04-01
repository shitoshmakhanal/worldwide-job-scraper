import requests
import time
import random
from loguru import logger
from scraper.base import BaseScraper


class MerojobScraper(BaseScraper):
    source   = "merojob"
    country  = "Nepal"
    region   = "Asia"
    base_url = "https://api.merojob.com/api/v1/jobs/"

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://merojob.com/",
            "Origin": "https://merojob.com",
        }

    def safe_join(self, lst):
        if not lst:
            return None
        return ", ".join([str(x) for x in lst if x is not None and str(x).strip()])

    def safe_location(self, lst):
        if not lst:
            return None
        parts = []
        for item in lst:
            if not isinstance(item, dict):
                continue
            val = (item.get("name") or item.get("address") or "").strip()
            if val:
                parts.append(val)
        return ", ".join(parts) if parts else "Kathmandu, Nepal"

    def safe_dict_join(self, lst, key="name"):
        if not lst:
            return None
        parts = [item.get(key, "") if isinstance(item, dict) else str(item) for item in lst if item]
        parts = [p.strip() for p in parts if p.strip()]
        return ", ".join(parts) if parts else None

    def scrape(self):
        jobs = []
        for page in range(1, 26):
            logger.info(f"Merojob page {page}/25...")
            try:
                res = requests.get(
                    self.base_url,
                    params={"page": page, "page_size": 20, "q": ""},
                    headers=self.get_headers(),
                    timeout=15
                )
                if res.status_code != 200:
                    break
                results = res.json().get("results", [])
                if not results:
                    break

                for job in results:
                    client = job.get("client")
                    if job.get("hide_org_name"):
                        company = "Confidential"
                    elif isinstance(client, dict):
                        company = client.get("client_name") or client.get("org_name")
                    else:
                        company = None

                    sal = job.get("offered_salary") or {}
                    if isinstance(sal, dict) and not job.get("hide_salary"):
                        sal_min = sal.get("minimum")
                        sal_max = sal.get("maximum")
                        sal_str = f"NPR {sal_min}-{sal_max} Monthly" if sal_min and sal_max else (f"NPR {sal_min}+ Monthly" if sal_min else None)
                    else:
                        sal_min = sal_max = sal_str = None

                    exp = job.get("experience_required") or {}
                    if isinstance(exp, dict) and exp.get("minimum") is not None:
                        exp_str = f"{exp['minimum']}-{exp.get('maximum')} years" if exp.get("maximum") else f"{exp['minimum']}+ years"
                    else:
                        exp_str = None

                    skills_raw = job.get("skills") or []
                    skills_str = self.safe_join([s.get("name") if isinstance(s, dict) else s for s in skills_raw if s])

                    jobs.append({
                        "title":           job.get("title"),
                        "company":         company,
                        "location":        self.safe_location(job.get("job_locations") or []) or "Kathmandu, Nepal",
                        "salary_str":      sal_str,
                        "salary_min":      sal_min,
                        "salary_max":      sal_max,
                        "salary_currency": "NPR",
                        "job_type":        job.get("available_for"),
                        "job_level":       job.get("job_level"),
                        "category":        self.safe_dict_join(job.get("categories") or [], "name"),
                        "skills":          skills_str,
                        "description":     None,
                        "deadline":        job.get("deadline"),
                        "posted_date":     job.get("posted_date"),
                        "job_url":         f"https://merojob.com{job.get('absolute_url') or ''}",
                        "source":          self.source
                    })

                time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.error(f"Merojob page {page} error: {e}")
                break

        logger.info(f"Merojob: {len(jobs)} jobs scraped")
        return jobs


if __name__ == "__main__":
    from scraper.utils.db import init_db
    init_db()
    scraper = MerojobScraper()
    scraper.run()
    print(f"Done: {scraper.jobs_found} found, {scraper.jobs_new} new")
