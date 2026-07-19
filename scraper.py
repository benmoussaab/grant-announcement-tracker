"""
scraper.py
Scrapes Facebook posts via Apify within a given date range, and filters
out non-photo media (videos/reels) so only real document images continue
down the pipeline.
"""

import requests
from datetime import date, timedelta

from rotation import call_apify_with_rotation


def _do_scrape(client, url, limit, newer_than=None, older_than=None):
    run_input = {"startUrls": [{"url": url}], "resultsLimit": limit}
    if newer_than:
        run_input["onlyPostsNewerThan"] = newer_than
    if older_than:
        run_input["onlyPostsOlderThan"] = older_than
    run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
    return list(client.dataset(run.default_dataset_id).iterate_items())


def scrape_posts(url, limit, newer_than=None, older_than=None):
    items = call_apify_with_rotation(_do_scrape, url, limit, newer_than, older_than)
    print(f"Got {len(items)} posts (range: {newer_than or 'start'} to {older_than or 'now'})")
    return items


def generate_monthly_chunks(years_back):
    """Yields (newer_than, older_than) date strings covering rolling 30-day
    windows going back `years_back` years, anchored on TODAY (not the 1st
    of the calendar month) — so the most recent chunk always ends today."""
    today = date.today()
    chunks = []
    end = today
    total_days = years_back * 365
    step = 30
    days_covered = 0
    while days_covered < total_days:
        start = end - timedelta(days=step)
        chunks.append((start.isoformat(), end.isoformat()))
        end = start
        days_covered += step
    return chunks


def get_yesterday_range():
    """Returns (newer_than, older_than) covering just yesterday — used by
    the daily incremental scrape."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    return yesterday.isoformat(), today.isoformat()


def is_reel_or_video(post):
    post_url = post.get("url") or post.get("postUrl") or ""
    return "/reel/" in post_url or "/videos/" in post_url


def get_post_content_images(post):
    media = post.get("media", [])
    return [m for m in media if m.get("__typename") == "Photo"]


def get_image_url(photo):
    return (
        photo.get("photo_image", {}).get("uri")
        or photo.get("image", {}).get("uri")
        or photo.get("thumbnail")
    )


def download_image(url):
    return requests.get(url).content
