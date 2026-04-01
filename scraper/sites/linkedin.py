import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger
from scraper.base import BaseScraper


# ── Country → Region mapping ──────────────────────────────────────────────────
# No hardcoding of what to scrape — this just maps whatever location LinkedIn
# returns into a clean country + continent at save time.

COUNTRY_TO_REGION = {
    # North America
    "United States": "North America", "Canada": "North America", "Mexico": "North America",
    # South America
    "Brazil": "South America", "Argentina": "South America", "Colombia": "South America",
    "Chile": "South America", "Peru": "South America", "Venezuela": "South America",
    "Ecuador": "South America", "Bolivia": "South America", "Paraguay": "South America",
    "Uruguay": "South America",
    # Europe
    "United Kingdom": "Europe", "Germany": "Europe", "France": "Europe",
    "Netherlands": "Europe", "Spain": "Europe", "Italy": "Europe", "Sweden": "Europe",
    "Norway": "Europe", "Denmark": "Europe", "Finland": "Europe", "Switzerland": "Europe",
    "Belgium": "Europe", "Poland": "Europe", "Portugal": "Europe", "Austria": "Europe",
    "Ireland": "Europe", "Czech Republic": "Europe", "Romania": "Europe",
    "Ukraine": "Europe", "Greece": "Europe", "Hungary": "Europe", "Serbia": "Europe",
    "Croatia": "Europe", "Slovakia": "Europe", "Bulgaria": "Europe",
    "Lithuania": "Europe", "Latvia": "Europe", "Estonia": "Europe", "Slovenia": "Europe",
    "Luxembourg": "Europe", "Malta": "Europe", "Cyprus": "Europe", "Iceland": "Europe",
    # Asia - East & Southeast
    "China": "Asia", "Japan": "Asia", "South Korea": "Asia", "Taiwan": "Asia",
    "Hong Kong": "Asia", "Mongolia": "Asia", "Singapore": "Asia", "Thailand": "Asia",
    "Vietnam": "Asia", "Philippines": "Asia", "Indonesia": "Asia", "Malaysia": "Asia",
    "Myanmar": "Asia", "Cambodia": "Asia", "Laos": "Asia", "Brunei": "Asia",
    "East Timor": "Asia",
    # Asia - South
    "India": "Asia", "Nepal": "Asia", "Bangladesh": "Asia", "Pakistan": "Asia",
    "Sri Lanka": "Asia", "Bhutan": "Asia", "Maldives": "Asia", "Afghanistan": "Asia",
    # Asia - Middle East
    "United Arab Emirates": "Asia", "Saudi Arabia": "Asia", "Qatar": "Asia",
    "Kuwait": "Asia", "Bahrain": "Asia", "Oman": "Asia", "Jordan": "Asia",
    "Lebanon": "Asia", "Israel": "Asia", "Turkey": "Asia", "Iran": "Asia",
    "Iraq": "Asia", "Syria": "Asia", "Yemen": "Asia",
    # Asia - Central
    "Kazakhstan": "Asia", "Uzbekistan": "Asia", "Kyrgyzstan": "Asia",
    "Tajikistan": "Asia", "Turkmenistan": "Asia",
    # Oceania
    "Australia": "Oceania", "New Zealand": "Oceania", "Papua New Guinea": "Oceania",
    "Fiji": "Oceania", "Solomon Islands": "Oceania", "Vanuatu": "Oceania",
    # Africa
    "Ethiopia": "Africa", "Nigeria": "Africa", "Kenya": "Africa",
    "South Africa": "Africa", "Ghana": "Africa", "Egypt": "Africa",
    "Morocco": "Africa", "Tanzania": "Africa", "Uganda": "Africa", "Rwanda": "Africa",
    "Senegal": "Africa", "Cameroon": "Africa", "Ivory Coast": "Africa",
    "Zimbabwe": "Africa", "Zambia": "Africa", "Mozambique": "Africa",
    "Madagascar": "Africa", "Tunisia": "Africa", "Algeria": "Africa",
    "Libya": "Africa", "Sudan": "Africa", "Angola": "Africa", "Botswana": "Africa",
    "Namibia": "Africa", "Mali": "Africa", "Burkina Faso": "Africa",
}

# US state abbreviations → United States
US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}

# Metro area keyword → country
METRO_TO_COUNTRY = {
    "Jakarta":          "Indonesia",
    "Ho Chi Minh":      "Vietnam",
    "Hanoi":            "Vietnam",
    "Metro Manila":     "Philippines",
    "Cebu":             "Philippines",
    "Seoul":            "South Korea",
    "Busan":            "South Korea",
    "Bangkok":          "Thailand",
    "Kuala Lumpur":     "Malaysia",
    "Tokyo":            "Japan",
    "Osaka":            "Japan",
    "Johannesburg":     "South Africa",
    "Cape Town":        "South Africa",
    "Durban":           "South Africa",
    "Pune":             "India",
    "Mumbai":           "India",
    "Bangalore":        "India",
    "Hyderabad":        "India",
    "Chennai":          "India",
    "Delhi":            "India",
    "Kolkata":          "India",
    "Sydney":           "Australia",
    "Melbourne":        "Australia",
    "Brisbane":         "Australia",
    "Perth":            "Australia",
    "Auckland":         "New Zealand",
    "London":           "United Kingdom",
    "Manchester":       "United Kingdom",
    "Birmingham":       "United Kingdom",
    "Doha":             "Qatar",
    "Dubai":            "United Arab Emirates",
    "Abu Dhabi":        "United Arab Emirates",
    "Riyadh":           "Saudi Arabia",
    "Jeddah":           "Saudi Arabia",
    "Karachi":          "Pakistan",
    "Lahore":           "Pakistan",
    "Islamabad":        "Pakistan",
    "Dhaka":            "Bangladesh",
    "Chittagong":       "Bangladesh",
    "Colombo":          "Sri Lanka",
    "Cairo":            "Egypt",
    "Alexandria":       "Egypt",
    "Lagos":            "Nigeria",
    "Abuja":            "Nigeria",
    "Nairobi":          "Kenya",
    "Accra":            "Ghana",
    "Addis Ababa":      "Ethiopia",
    "San Francisco":    "United States",
    "New York":         "United States",
    "Los Angeles":      "United States",
    "Chicago":          "United States",
    "Seattle":          "United States",
    "Boston":           "United States",
    "Austin":           "United States",
    "Dallas":           "United States",
    "Atlanta":          "United States",
    "Washington":       "United States",
    "Toronto":          "Canada",
    "Vancouver":        "Canada",
    "Montreal":         "Canada",
    "Berlin":           "Germany",
    "Munich":           "Germany",
    "Paris":            "France",
    "Amsterdam":        "Netherlands",
    "Barcelona":        "Spain",
    "Madrid":           "Spain",
    "Milan":            "Italy",
    "Rome":             "Italy",
    "Stockholm":        "Sweden",
    "Oslo":             "Norway",
    "Copenhagen":       "Denmark",
    "Helsinki":         "Finland",
    "Zurich":           "Switzerland",
    "Geneva":           "Switzerland",
    "Brussels":         "Belgium",
    "Warsaw":           "Poland",
    "Lisbon":           "Portugal",
    "Vienna":           "Austria",
    "Dublin":           "Ireland",
    "Prague":           "Czech Republic",
    "Bucharest":        "Romania",
    "Budapest":         "Hungary",
    "Taipei":           "Taiwan",
    "Beijing":          "China",
    "Shanghai":         "China",
    "Shenzhen":         "China",
    "Guangzhou":        "China",
    "Singapore":        "Singapore",
    "Kathmandu":        "Nepal",
    "Nairobi":          "Kenya",
    "Mexico City":      "Mexico",
    "São Paulo":        "Brazil",
    "Buenos Aires":     "Argentina",
    "Bogotá":           "Colombia",
    "Lima":             "Peru",
    "Santiago":         "Chile",
}


def extract_country_region(location_str: str) -> tuple[str, str]:
    """
    Given a raw LinkedIn location string like:
      "Addis Ababa, Ethiopia"
      "San Francisco Bay Area"
      "CA"
      "Remote"
      "Worldwide"
      "Greater Tokyo Area"
    Returns (country, region) tuple.
    """
    if not location_str:
        return "Worldwide", "Remote"

    loc = location_str.strip()

    # Remote / Worldwide
    if loc.lower() in ("remote", "worldwide", "anywhere"):
        return "Remote", "Remote"
    if "remote" in loc.lower():
        return "Remote", "Remote"

    # Last part after last comma is usually the country
    parts = [p.strip() for p in loc.split(",")]
    last = parts[-1].strip()

    # Direct country match
    if last in COUNTRY_TO_REGION:
        return last, COUNTRY_TO_REGION[last]

    # US state abbreviation
    if last.upper() in US_STATES:
        return "United States", "North America"

    # Full string is a known country
    if loc in COUNTRY_TO_REGION:
        return loc, COUNTRY_TO_REGION[loc]

    # Metro area keyword search — check if any metro keyword appears in location
    for keyword, country in METRO_TO_COUNTRY.items():
        if keyword.lower() in loc.lower():
            region = COUNTRY_TO_REGION.get(country, "Worldwide")
            return country, region

    # First part might be city, last part might still give us something
    if len(parts) >= 2:
        second_last = parts[-2].strip()
        if second_last in COUNTRY_TO_REGION:
            return second_last, COUNTRY_TO_REGION[second_last]

    # Fallback
    return "Worldwide", "Worldwide"


class LinkedInScraper(BaseScraper):
    source   = "linkedin"
    base_url = "https://www.linkedin.com/jobs/search"

    def get_driver(self):
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.binary_location = "/usr/bin/google-chrome"
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

    def scrape(self):
        jobs = []
        searches = [
            # Global
            ("jobs", ""),
            ("remote jobs", "Worldwide"),
            ("engineer", ""),
            ("manager", ""),
            ("analyst", ""),
            ("designer", ""),
            ("nurse", ""),
            ("teacher", ""),
            ("accountant", ""),
            ("sales", ""),
            # Nepal
            ("jobs", "Nepal"),
            ("engineer", "Nepal"),
            ("teacher", "Nepal"),
            ("accountant", "Nepal"),
            ("marketing", "Nepal"),
            ("finance", "Nepal"),
            # India
            ("software engineer", "India"),
            ("data analyst", "India"),
            ("marketing manager", "India"),
            ("finance", "India"),
            ("nurse", "India"),
            ("teacher", "India"),
            ("sales", "India"),
            # Southeast Asia
            ("jobs", "Singapore"),
            ("jobs", "Philippines"),
            ("jobs", "Malaysia"),
            ("jobs", "Indonesia"),
            ("jobs", "Vietnam"),
            ("jobs", "Thailand"),
            ("jobs", "Bangladesh"),
            ("jobs", "Pakistan"),
            ("jobs", "Sri Lanka"),
            # East Asia
            ("jobs", "Japan"),
            ("jobs", "South Korea"),
            ("jobs", "China"),
            # Oceania
            ("jobs", "Australia"),
            ("engineer", "Australia"),
            ("nurse", "Australia"),
            ("teacher", "Australia"),
            ("jobs", "New Zealand"),
            # Middle East
            ("jobs", "United Arab Emirates"),
            ("engineer", "United Arab Emirates"),
            ("nurse", "United Arab Emirates"),
            ("jobs", "Saudi Arabia"),
            ("jobs", "Qatar"),
            ("jobs", "Kuwait"),
            ("jobs", "Bahrain"),
            # Africa
            ("jobs", "Nigeria"),
            ("jobs", "Kenya"),
            ("jobs", "South Africa"),
            ("jobs", "Ghana"),
            ("jobs", "Ethiopia"),
            ("jobs", "Egypt"),
            ("jobs", "Tanzania"),
            ("jobs", "Rwanda"),
            # Europe
            ("jobs", "United Kingdom"),
            ("engineer", "United Kingdom"),
            ("nurse", "United Kingdom"),
            ("jobs", "Germany"),
            ("jobs", "Netherlands"),
            ("jobs", "France"),
            ("jobs", "Spain"),
            ("jobs", "Sweden"),
            ("jobs", "Poland"),
            ("jobs", "Ireland"),
            ("jobs", "Switzerland"),
            # North America
            ("jobs", "United States"),
            ("engineer", "United States"),
            ("nurse", "United States"),
            ("teacher", "United States"),
            ("finance", "United States"),
            ("jobs", "Canada"),
            ("engineer", "Canada"),
            ("jobs", "Mexico"),
            # South America
            ("jobs", "Brazil"),
            ("jobs", "Argentina"),
            ("jobs", "Colombia"),
            ("jobs", "Chile"),
        ]
        driver = self.get_driver()
        try:
            for query, location in searches:
                logger.info(f"LinkedIn: {query} @ {location or 'global'}")
                try:
                    found = self._scrape_search(driver, query, location)
                    jobs += found
                    logger.info(f"  → {len(found)} jobs")
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"LinkedIn search failed ({query}, {location}): {e}")
        finally:
            driver.quit()
        return jobs

    def _scrape_search(self, driver, query, location, pages=3):
        jobs = []
        for page in range(pages):
            start = page * 25
            url = (
                f"{self.base_url}/?keywords={query.replace(' ', '%20')}"
                f"&location={location}&start={start}"
            )
            driver.get(url)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.base-card"))
                )
            except Exception:
                pass
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "lxml")
            cards = soup.select("div.base-card") or soup.select("div.job-search-card")
            logger.info(f"  Page {page+1}: {len(cards)} cards")
            if not cards:
                break

            for card in cards:
                t = card.select_one("h3.base-search-card__title") or card.select_one("h3")
                c = card.select_one("h4.base-search-card__subtitle a") or card.select_one("h4")
                l = card.select_one("span.job-search-card__location")
                d = card.select_one("time")

                title = t.text.strip() if t else None
                if not title:
                    continue

                a_tag = (
                    card.select_one("a.base-card__full-link")
                    or card.select_one("a[data-tracking-control-name]")
                )
                job_url = a_tag["href"].split("?")[0] if a_tag and a_tag.get("href") else None

                raw_location = l.text.strip() if l else None

                # ── Key fix: derive country + region from the actual location string ──
                country, region = extract_country_region(raw_location)

                jobs.append({
                    "title":           title,
                    "company":         c.text.strip() if c else None,
                    "location":        raw_location,
                    "country":         country,
                    "region":          region,
                    "salary_str":      None,
                    "salary_min":      None,
                    "salary_max":      None,
                    "salary_currency": "USD",
                    "job_type":        None,
                    "job_level":       None,
                    "category":        query,
                    "skills":          None,
                    "description":     None,
                    "posted_date":     d.get("datetime") if d else None,
                    "job_url":         job_url,
                    "source":          self.source,
                })
        return jobs


if __name__ == "__main__":
    from scraper.utils.db import init_db
    init_db()
    scraper = LinkedInScraper()
    scraper.run()
    print(f"Done: {scraper.jobs_found} found, {scraper.jobs_new} new")
