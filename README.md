A full-stack job aggregation platform that scrapes 4 major job sources globally, deduplicates listings, and delivers personalised job recommendations through a modern Streamlit dashboard.

Live Scraper| Smart Dedup |AI Recommendations | Global Coverage

---

 ✨ Features

🕷️ Multi-Source Scraping
- LinkedIn — 80+ searches across 40+ countries, all job categories
- Merojob (Nepal) — 300+ local jobs via REST API
- RemoteOK — 95+ remote positions via public API
- WeWorkRemotely — 130+ remote roles via BeautifulSoup scraper

Current Database: 6,000+ unique jobs across 6 continents

### 🧹 Intelligent Deduplication
- **Exact match removal** — SQL-based dedup (removed 15,497 duplicates)
- **Fuzzy matching** — SequenceMatcher-based title similarity
- **Auto-merge & manual review** — 541 jobs flagged for user review
- **Automatic expiry** — Jobs older than 30 days marked inactive

### 🤖 AI Job Recommendations
- TF-IDF matching — Ranks jobs against user profile
- Match score visualization — Colour-coded % scores
- Reason tags — Shows why a job matches
- One-click apply— Full cover letter + resume flow

### 📊 Full-Featured Dashboard
- **Job Boaard — Search, filter, advanced sorting
- For You — Personalised recommendations
- My Profile — Resume, cover letter, skills
- My Applications — Track application status
- Post a Job (Employer) — List jobs with view counts
- Scraper Logs (Admin) — Error tracking
- Login/Register — Cookie-backed persistent sessions

 ⏰ Automated Scheduling
- Cron job — Runs 6am + 6pm daily
- Auto-dedup — Runs after every scrape
  *Auto-expiry — Marks stale jobs inactive

---<img width="1919" height="947" alt="image" src="https://github.com/user-attachments/assets/e841b2d9-95ef-4b52-ab99-db45df3f3a3b" />
<img width="1919" height="937" alt="image" src="https://github.com/user-attachments/assets/b3f1356a-c2a7-4df6-bf53-c5d0dde38bde" />



## 🏗️ Architecture
