# Municipal Grant Announcement Tracker

A fully automated pipeline that scrapes public contract award notices from a
municipal Facebook page, extracts structured data from scanned Arabic-language
document images using a vision-language model, and presents it in a public,
interactive dashboard — with zero manual maintenance required.

**Live dashboard:** [add your Streamlit Cloud URL here]

---

## What this project does

Algerian municipalities are required to publicly post official notices when a
government contract is awarded ("Temporary Grant Announcement") or cancelled.
In practice, these notices are published as scanned document images on
Facebook — readable one at a time, but impossible to search, aggregate, or
analyze at scale.

This project turns that raw, scattered information into a structured,
queryable dataset and a public dashboard, updated automatically every day.

## How it works

```
Facebook page
     │
     ▼
Apify (scraping)  ──────────►  filters out videos/reels, keeps real photos
     │
     ▼
Gemini Vision API  ─────────►  classifies each image (award / cancellation / irrelevant)
     │                          then extracts structured fields via prompt engineering
     ▼
Fuzzy matching (RapidFuzz) ──►  links cancellation notices back to their
     │                          original award, even when extracted text
     │                          differs slightly between the two posts
     ▼
SQLite database
     │
     ▼
Streamlit dashboard  ───────►  spend trends, top contractors, cancellation
                                rates, fuzzy-match auditing, and a
                                self-service chart builder
```

**Automation:** a GitHub Actions workflow runs daily, scraping the previous
day's posts and committing the updated data back to this repository. The
Streamlit dashboard reads directly from that data, so it reflects new
announcements automatically — no server, no manual updates.

## Features

- **Vision-based extraction, not traditional OCR** — a vision-language model
  (Gemini) reads tables, handwriting, and stamped/overlapping text far more
  reliably than classic OCR, especially on Arabic-script documents.
- **Multi-row table handling** — a single announcement image can contain
  several separate contract awards (one per lot); each is extracted as its
  own record.
- **Cancellation linking** — cancellation notices are automatically matched to
  their original award using fuzzy text matching on company name and project
  title, with a numeric amount check as a safeguard, since exact string
  matching isn't reliable across two independently-extracted documents.
- **Hallucination guarding** — the extraction prompt explicitly instructs the
  model to return null rather than guess when a field isn't clearly visible,
  and rows with no successful bidder are excluded rather than fabricated.
- **API key rotation** — rotates across multiple Apify/Gemini credentials on
  rate-limit or quota errors, so a single exhausted key doesn't halt the
  pipeline.
- **Checkpointed, resumable backfill** — the historical backfill processes
  data in date-range chunks and can be safely interrupted and resumed without
  reprocessing already-completed work.
- **Fuzzy match auditing** — a dedicated dashboard tab lets anyone inspect
  which company/commune name variants were automatically grouped together,
  with a separate tab to manually correct any wrong groupings.
- **Fully serverless automation** — runs entirely on GitHub Actions' free
  tier; no VPS, no always-on server, no cost.

## Tech stack

| Layer | Tool |
|---|---|
| Scraping | Apify (Facebook Posts Scraper) |
| Extraction | Google Gemini (vision, via Google AI Studio) |
| Fuzzy matching | RapidFuzz |
| Storage | SQLite |
| Dashboard | Streamlit, Plotly, Pandas |
| Automation | GitHub Actions (scheduled + on-demand) |
| Prototyping | Apache Airflow on Docker (used during development to learn orchestration before settling on GitHub Actions for deployment) |

## Repository structure

```
config.py            Configuration and prompts
rotation.py           API key/token rotation logic
scraper.py             Scraping and media filtering
extract.py               Gemini classification and extraction
storage.py                 SQLite storage and fuzzy-match linking
progress.py                  Checkpoint tracking
process.py                     Shared per-post processing logic
backfill.py                      Historical backfill script (run manually)
daily_scrape.py                    Daily incremental scrape (run by GitHub Actions)
dashboard.py                          Streamlit dashboard
.github/workflows/daily_scrape.yml       Automation
```

## Running it yourself

```bash
pip install -r requirements.txt

export APIFY_TOKEN_1="..."
export APIFY_TOKEN_2="..."
export GEMINI_API_KEY_1="..."
export GEMINI_API_KEY_2="..."
export GEMINI_API_KEY_3="..."

python backfill.py       # historical backfill, resumable
streamlit run dashboard.py
```

## Known limitations

This is documented transparently in the dashboard's About tab as well:

- **School transport projects (النقل المدرسي) are excluded.** Some posts
  contained multiple transport lots in one table, but extraction only
  reliably captured the first row's section title — the rest were
  inconsistently extracted. Rather than show incomplete data, this category
  is excluded entirely.
- **Only Arabic-language posts are analyzed.** A small number of French-
  language announcements on the same page (2-3, estimated) were not detected,
  since classification depends on the Arabic title of the notice.
- **Extracted text fields may contain minor typos or inconsistencies** from
  the automated extraction process. Company and commune names are
  fuzzy-matched to reduce this effect, but the matching is approximate.
- **Some cancellations could not be automatically linked** to a matching
  award post and appear as standalone, limited-detail entries.

## Why this project

Built as a hands-on project to learn end-to-end data engineering: API
integration, prompt engineering for structured extraction from real-world
messy documents, data cleaning and matching at scale, and CI/CD-style
automation — starting with Airflow/Docker to understand orchestration
fundamentals, then moving to a simpler, free, serverless deployment for the
actual production automation.
