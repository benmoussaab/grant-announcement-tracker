"""
backfill.py
One-time historical backfill: scrapes the past BACKFILL_YEARS (2 years),
one month at a time, classifying/extracting/storing grant announcements
and cancellations. Safe to interrupt and rerun — already-completed months
are skipped, and the in-progress month resumes from where it left off.

Run manually (not via Airflow) until the full 2-year backfill is done:
    python backfill.py
"""

import sqlite3

from config import FACEBOOK_PAGE_URL, RESULTS_LIMIT, BACKFILL_YEARS
from scraper import scrape_posts, generate_monthly_chunks
from storage import init_db
from progress import load_progress, save_progress
from process import process_post


def main():
    init_db()
    conn = sqlite3.connect("announcements.db")

    progress = load_progress()
    chunks = generate_monthly_chunks(years_back=BACKFILL_YEARS)

    for newer_than, older_than in chunks:
        chunk_key = f"{newer_than}_to_{older_than}"
        if chunk_key in progress["completed_chunks"]:
            print(f"Skipping already-completed chunk: {chunk_key}")
            continue

        print(f"\n=== Processing chunk: {newer_than} to {older_than} ===")
        items = scrape_posts(FACEBOOK_PAGE_URL, RESULTS_LIMIT, newer_than, older_than)

        chunk_finished_cleanly = True
        for post in items:
            keep_going = process_post(post, progress, conn)
            if not keep_going:
                chunk_finished_cleanly = False
                break

        if chunk_finished_cleanly:
            progress["completed_chunks"].append(chunk_key)
            save_progress(progress)
            print(f"=== Finished chunk: {chunk_key} ===\n")
        else:
            print(f"=== Stopped mid-chunk: {chunk_key} (will resume here next run) ===\n")
            break

    conn.close()
    print("\nBackfill run finished (or paused — rerun this script to continue).")
    print("Check announcements.db for results.")


if __name__ == "__main__":
    main()
