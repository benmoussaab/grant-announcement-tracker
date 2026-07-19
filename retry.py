"""
retry_failed_downloads.py
Retries any images that previously failed to download (e.g. due to a
transient DNS/network error), which would otherwise be silently lost once
their chunk gets marked complete. Run this periodically, especially after
network hiccups during a backfill or daily scrape.

Run with:
    python retry_failed_downloads.py
"""

import json
import sqlite3
import time

from scraper import download_image
from extract import is_grant_announcement, extract_announcement, clean_json_response
from storage import init_db, store_award, store_cancellation
from progress import load_progress, save_progress


def main():
    init_db()
    conn = sqlite3.connect("announcements.db")
    progress = load_progress()

    failed = list(progress["failed_downloads"])  # copy, since we'll mutate the original

    if not failed:
        print("No failed downloads recorded. Nothing to retry.")
        return

    print(f"Retrying {len(failed)} previously failed downloads...")

    for entry in failed:
        url = entry["url"]
        post_id = entry["post_id"]
        link = entry["link"]

        try:
            img_bytes = download_image(url)
        except Exception as e:
            print(f"Still failing: {url} -> {e}")
            continue  # leave it in failed_downloads for next time

        try:
            if is_grant_announcement(img_bytes):
                raw_text = extract_announcement(img_bytes)
                cleaned = clean_json_response(raw_text)

                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as e:
                    print(f"Could not parse JSON for {url}: {e}")
                    parsed = None

                if parsed is not None:
                    announcements = parsed if isinstance(parsed, list) else [parsed]
                    for ann in announcements:
                        if ann.get("valid") is False:
                            continue
                        if ann.get("document_type") == "cancellation":
                            print("CANCELLATION (retry):", post_id, "->", ann.get("company_name"))
                            store_cancellation(conn, ann, post_id, link, url)
                        else:
                            print("MATCH (retry):", post_id, "->", ann.get("company_name"))
                            store_award(conn, ann, post_id, link, url)
                    conn.commit()
            else:
                print("skip (retry):", post_id)

            # Success — remove from failed_downloads and mark processed
            progress["failed_downloads"] = [
                f for f in progress["failed_downloads"] if f["url"] != url
            ]
            progress["processed_image_urls"].append(url)
            save_progress(progress)

        except Exception as e:
            print(f"ERROR on retry for {post_id}: {e}")
            # leave it in failed_downloads for next time

        time.sleep(7)

    conn.close()
    remaining = len(progress["failed_downloads"])
    print(f"\nDone. {remaining} still failing (will remain for next retry attempt).")


if __name__ == "__main__":
    main()
