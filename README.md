# 🌐 Worldwide Job Scraper

A full-stack job aggregation platform that scrapes 4 major job sources globally, deduplicates listings, and delivers personalised job recommendations through a modern Streamlit dashboard.

**Live Scraper** | **Smart Dedup** | **AI Recommendations** | **Global Coverage**

---

## ✨ Features

### 🕷️ Multi-Source Scraping
- **LinkedIn** — 80+ searches across 40+ countries, all job categories
- **Merojob** (Nepal) — 300+ local jobs via REST API
- **RemoteOK** — 95+ remote positions via public API
- **WeWorkRemotely** — 130+ remote roles via BeautifulSoup scraper

**Current Database:** 6,000+ unique jobs across 6 continents

### 🧹 Intelligent Deduplication
- **Exact match removal** — SQL-based dedup (removed 15,497 duplicates)
- **Fuzzy matching** — SequenceMatcher-based title similarity
- **Auto-merge & manual review** — 541 jobs flagged for user review
- **Automatic expiry** — Jobs older than 30 days marked inactive

### 🤖 AI Job Recommendations
- **TF-IDF matching** — Ranks jobs against user profile
- **Match score visualization** — Colour-coded % scores
- **Reason tags** — Shows why a job matches
- **One-click apply** — Full cover letter + resume flow

### 📊 Full-Featured Dashboard
- **Dark Bloomberg terminal aesthetic**
- **Job Board** — Search, filter, advanced sorting
- **For You** — Personalised recommendations
- **My Profile** — Resume, cover letter, skills
- **My Applications** — Track application status
- **Post a Job** (Employer) — List jobs with view counts
- **Scraper Logs** (Admin) — Error tracking
- **Login/Register** — Cookie-backed persistent sessions

### ⏰ Automated Scheduling
- **Cron job** — Runs 6am + 6pm daily
- **Auto-dedup** — Runs after every scrape
- **Auto-expiry** — Marks stale jobs inactive

---

## 🏗️ Architecture


**Database:** PostgreSQL 16 with 6,000+ jobs

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/shitoshmakhanal/worldwide-job-scraper.git
cd worldwide-job-scraper

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database
python -m scraper.utils.migrate

# Run dashboard
streamlit run dashboard/app.py
```

Open http://localhost:8501

---

## 📊 Data Coverage

| Source | Jobs | Update Freq | Countries |
|--------|------|-------------|-----------|
| LinkedIn | 1,864 | Every 6h | 40+ |
| Merojob | 333 | Every 6h | Nepal |
| RemoteOK | 95 | Every 6h | Global |
| WeWorkRemotely | 130 | Every 6h | Global |
| **Total** | **6,000+** | **6h refresh** | **6 continents** |

---

## 🔧 Tech Stack

- **Backend:** Python, PostgreSQL, Selenium, BeautifulSoup
- **Frontend:** Streamlit
- **ML:** scikit-learn (TF-IDF)
- **Automation:** Cron, PostgreSQL triggers
- **Auth:** SHA-256 hashing, cookie-based sessions
- **Deployment:** WSL + PostgreSQL

---

## 📝 Usage

### Jobseeker
1. Register as jobseeker
2. Add skills to **My Profile**
3. View **For You** recommendations
4. **Apply** with auto-filled cover letter
5. Track in **My Applications**

### Employer
1. Register as employer
2. **Post a Job** (admin approval required)
3. View **My Postings** with application counts

### Admin
- **Scraper Logs** — Monitor errors
- **Deduplication** — Review fuzzy matches

---

## 🚨 Known Limitations

- LinkedIn scraper slower (Selenium) — ~8-10 min per 80 searches
- Indeed blocks requests (403s)
- European job coverage low (5 jobs) — add more searches

---

## 🎯 Future Features

- [ ] Deploy to AWS/Railway
- [ ] Email digest of matching jobs
- [ ] Salary trend analytics
- [ ] Job market heatmap
- [ ] Mobile app (React Native)
- [ ] External CRM integration

---

## 📄 License

MIT License — free for personal & commercial use

---

## 👤 Author

**Shitoshma Khanal**
- GitHub: [@shitoshmakhanal](https://github.com/shitoshmakhanal)
- LinkedIn: [shitoshma-khanal](https://linkedin.com/in/shitoshma-khanal-91a19b2a0/)

Built with Claude AI assistance

---

**Last updated:** April 1, 2026
