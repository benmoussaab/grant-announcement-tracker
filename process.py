"""
process.py
Shared logic: given one scraped post, classify and extract every real
photo in it, storing results in the database. Used by both the historical
backfill and the daily incremental scrape.
"""

import json
import time

from scraper import is_reel_or_video, get_post_content_images, get_image_url, download_image
from extract import is_grant_announcement, extract_announcement, clean_json_response
from storage import store_award, store_cancellation
from progress import save_progress


def process_post(post, progress, conn):
    """Runs classification/extraction/storage for every real photo in one
    post. Returns True normally, or False if all Gemini keys are exhausted
    and the caller should stop the run entirely (that image is NOT marked
    as done, so it will be retried on the next run)."""
    if is_reel_or_video(post):
        print("skip (reel/video):", post.get("postId"))
        return True

    real_photos = get_post_content_images(post)
    post_id = post.get("postId")
    link = post.get("url") or post.get("postUrl") or f"https://facebook.com/{post_id}"

    for photo in real_photos:
        url = get_image_url(photo)
        if not url:
            continue
        if url in progress["processed_image_urls"]:
            continue

        try:
            img_bytes = download_image(url)
        except Exception as e:
            print(f"Download error for {url}: {e} — recorded for retry")
            already_recorded = any(f["url"] == url for f in progress["failed_downloads"])
            if not already_recorded:
                progress["failed_downloads"].append({
                    "url": url, "post_id": post_id, "link": link,
                })
                save_progress(progress)
            continue  # not marked done — will be retried via retry_failed_downloads.py

        exhausted = False
        try:
            if is_grant_announcement(img_bytes):
                raw_text = extract_announcement(img_bytes)
                cleaned = clean_json_response(raw_text)

                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as e:
                    print(f"Could not parse JSON for {url}: {e}")
                    print("Raw:", repr(raw_text))
                    parsed = None

                if parsed is not None:
                    announcements = parsed if isinstance(parsed, list) else [parsed]

                    for ann in announcements:
                        if ann.get("valid") is False:
                            continue

                        doc_type = ann.get("document_type")

                        if doc_type == "cancellation":
                            print("CANCELLATION:", post_id, "->", ann.get("company_name"))
                            store_cancellation(conn, ann, post_id, link, url)
                        else:
                            print("MATCH (award):", post_id, "->", ann.get("company_name"))
                            store_award(conn, ann, post_id, link, url)

                    conn.commit()
            else:
                print("skip:", post_id)
        except RuntimeError as e:
            if "exhausted" in str(e).lower():
                print(f"All Gemini keys exhausted on {url} — stopping this run, image NOT marked done.")
                exhausted = True
            else:
                print(f"ERROR on {post_id}: {e}")
        except Exception as e:
            print(f"ERROR on {post_id}: {e}")

        if exhausted:
            return False

        # Successfully handled (or hit a non-fatal, non-download error) —
        # mark done, and clear it from failed_downloads if it was there
        # from a previous run's retry.
        progress["processed_image_urls"].append(url)
        progress["failed_downloads"] = [
            f for f in progress["failed_downloads"] if f["url"] != url
        ]
        save_progress(progress)
        time.sleep(7)

    return True
