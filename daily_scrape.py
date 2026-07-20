"""
daily_scrape.py
Scrapes only YESTERDAY's posts (a small, cheap daily scrape) and processes
them the same way as the backfill. Meant to be triggered once a day by
an Airflow DAG, after the 2-year historical backfill is complete.

Run manually with:
    python daily_scrape.py
Or import `run_daily_scrape()` directly from an Airflow PythonOperator.
"""

import sqlite3
import pandas as pd
from config import FACEBOOK_PAGE_URL, RESULTS_LIMIT
from scraper import scrape_posts, get_yesterday_range
from storage import init_db
from progress import load_progress, save_progress
from process import process_post

def export_csv():
    conn = sqlite3.connect("announcements.db")
    df = pd.read_sql("SELECT * FROM announcements", conn)
    conn.close()
    df.to_csv("announcements_export.csv", index=False, encoding="utf-8-sig")

def run_daily_scrape():
    init_db()
    conn = sqlite3.connect("announcements.db")

    progress = load_progress()
    newer_than, older_than = get_yesterday_range()

    print(f"\n=== Daily scrape: {newer_than} to {older_than} ===")
    items = scrape_posts(FACEBOOK_PAGE_URL, RESULTS_LIMIT, newer_than, older_than)

    for post in items:
        keep_going = process_post(post, progress, conn)
        if not keep_going:
            print("Stopped early due to key exhaustion — remaining posts will be picked up next run.")
            break

    conn.close()
    print("=== Daily scrape finished ===\n")
    export_csv()



if __name__ == "__main__":
    run_daily_scrape()
