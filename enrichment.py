import re, time, random
from loguru import logger
from sqlalchemy import text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
from scraper.utils.db import SessionLocal, Job

SKILL_TAXONOMY = {
    "python","javascript","typescript","java","kotlin","swift","go","golang",
    "rust","c++","c#","ruby","php","scala","r","matlab","bash","shell","sql",
    "html","css","react","vue","angular","next.js","nuxt","svelte","django",
    "flask","fastapi","spring","express","rails","laravel","node.js","nodejs",
    "pandas","numpy","scikit-learn","tensorflow","pytorch","keras","xgboost",
    "lightgbm","spark","hadoop","airflow","dbt","mlflow","huggingface",
    "aws","gcp","azure","docker","kubernetes","k8s","terraform","ansible",
    "jenkins","linux","nginx","redis","kafka","postgresql","mysql","mongodb",
    "sqlite","elasticsearch","cassandra","dynamodb","bigquery","snowflake",
    "git","graphql","figma","jira","agile","scrum","machine learning",
    "deep learning","nlp","computer vision","data analysis","data engineering",
    "devops","microservices","llm","openai",
}

def extract_salary(text):
    if not text: return None, None, None
    currency = "USD"
    if "€" in text: currency = "EUR"
    elif "£" in text: currency = "GBP"
    elif "₹" in text: currency = "INR"
    patterns = [
        r'\$\s*([\d,]+)\s*[kK]?\s*[-–—to]+\s*\$\s*([\d,]+)\s*[kK]?',
        r'([\d,]+)\s*[kK]\s*[-–—to]+\s*([\d,]+)\s*[kK]\s*(?:USD|usd)?',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                def n(s):
                    v = float(s.replace(",",""))
                    return int(v*1000 if v < 1000 else v)
                g = m.groups()
                return (n(g[0]), n(g[1]), currency) if len(g)==2 else (n(g[0]), n(g[0]), currency)
            except: continue
    return None, None, None

def extract_skills(text):
    if not text: return ""
    t = text.lower()
    return ", ".join(sorted(s for s in SKILL_TAXONOMY if re.search(r'\b'+re.escape(s)+r'\b', t)))

def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    opts.binary_location = "/usr/bin/google-chrome"
    return webdriver.Chrome(options=opts)

def fetch_selenium(url, driver, selectors, wait_sel=None):
    try:
        driver.get(url)
        if wait_sel:
            try: WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_sel)))
            except: pass
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if len(t) > 100: return t
        return ""
    except Exception as e:
        logger.warning(f"Selenium failed {url}: {e}")
        return ""

def fetch_remoteok(url, driver=None):
    try:
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        if res.status_code != 200: return ""
        soup = BeautifulSoup(res.text, "lxml")
        el = soup.select_one("div.markdown") or soup.select_one("div#job-description")
        return el.get_text(" ", strip=True) if el else ""
    except Exception as e:
        logger.warning(f"remoteok failed: {e}")
        return ""

def fetch_weworkremotely(url, driver):
    return fetch_selenium(url, driver, [
        "div.listing-container","div#job-listing-show-container",
        "div.main-content","article","section.content",
    ], wait_sel="div.listing-container")

def fetch_linkedin(url, driver):
    return fetch_selenium(url, driver, [
        "div.show-more-less-html__markup","div.description__text",
        "section.description","div.job-view-layout",
    ], wait_sel="div.description__text")

FETCHERS = {"remoteok": fetch_remoteok, "weworkremotely": fetch_weworkremotely, "linkedin": fetch_linkedin}
NEEDS_SELENIUM = {"weworkremotely", "linkedin"}

def enrich(batch_size=200, delay=(2.0, 4.0)):
    db = SessionLocal()
    driver = None
    try:
        jobs = db.query(Job).filter((Job.description == None) | (Job.description == "")).limit(batch_size).all()
        logger.info(f"Jobs to enrich: {len(jobs)}")
        if not jobs:
            logger.success("All done!"); return
        if {j.source for j in jobs} & NEEDS_SELENIUM:
            logger.info("Starting Chrome...")
            driver = make_driver()
        success = failed = 0
        for i, job in enumerate(jobs, 1):
            fetcher = FETCHERS.get(job.source)
            if not fetcher or not job.job_url:
                logger.warning(f"[{i}] Skipping {job.source}"); failed += 1; continue
            logger.info(f"[{i}/{len(jobs)}] {job.source} | {job.title[:55]}")
            desc = fetcher(job.job_url, driver) if job.source in NEEDS_SELENIUM else fetcher(job.job_url)
            if desc and len(desc) > 50:
                job.description = desc[:10000]
                job.skills = extract_skills(desc)
                if not job.salary_raw:
                    mn, mx, cur = extract_salary(desc)
                    if mn:
                        job.salary_min, job.salary_max, job.salary_currency = mn, mx, cur
                        job.salary_raw = f"{mn}-{mx} {cur}"
                db.commit()
                success += 1
                logger.success(f"  ✓ {len(desc)} chars | {len(job.skills.split(',')) if job.skills else 0} skills")
            else:
                logger.warning(f"  ✗ empty"); failed += 1
            time.sleep(random.uniform(*delay))
        logger.success(f"\nDone — {success} enriched, {failed} failed")
    finally:
        if driver: driver.quit()
        db.close()

def print_stats():
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT source, COUNT(*) total, COUNT(description) has_desc,
                   COUNT(NULLIF(skills,'')) has_skills, COUNT(salary_raw) has_salary
            FROM jobs GROUP BY source ORDER BY total DESC
        """)).fetchall()
        print(f"\n{'Source':<20} {'Total':>6} {'Desc':>6} {'Skills':>7} {'Salary':>7}")
        print("─"*52)
        for r in rows:
            print(f"{r[0]:<20} {r[1]:>6} {r[2]:>6} {r[3]:>7} {r[4]:>7}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting enrichment...")
    enrich(batch_size=200)
    print_stats()
