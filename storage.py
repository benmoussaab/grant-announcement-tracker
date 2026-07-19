"""
storage.py
SQLite storage for extracted announcements. Cancellations are linked to
their original award via fuzzy text matching (company_name + project_title)
plus a numeric amount check, since cancellation notices don't reliably
restate any shared reference number and OCR/extraction wording can differ
slightly between an award post and its later cancellation post.
"""

import sqlite3
from rapidfuzz import fuzz

from config import DB_PATH, FUZZY_THRESHOLD


def normalize_amount(amount_str):
    """Turns '3.895.546,22' or '4 453 250,00' into a plain float so amounts
    can be compared regardless of separator style. Returns None if unparsable."""
    if not amount_str:
        return None
    s = str(amount_str)
    s = s.replace("دج", "").strip()
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            amount_in_dinars TEXT,
            project_title TEXT,
            duration TEXT,
            date TEXT,
            wilaya TEXT,
            commune TEXT,
            cancelled INTEGER DEFAULT 0,
            cancellation_reason TEXT,
            source_post_id TEXT,
            source_link TEXT,
            source_image_url TEXT,
            UNIQUE(company_name, project_title, amount_in_dinars)
        )
    """)
    conn.commit()
    conn.close()


def find_fuzzy_match(conn, company, project, amount, only_cancelled=None):
    """Searches existing rows for the best fuzzy match on company_name +
    project_title, with a numeric amount sanity check. `only_cancelled`
    can be True (search only cancelled=1 rows), False (only cancelled=0),
    or None (search all rows)."""
    if only_cancelled is True:
        query = "SELECT id, company_name, project_title, amount_in_dinars FROM announcements WHERE cancelled = 1"
    elif only_cancelled is False:
        query = "SELECT id, company_name, project_title, amount_in_dinars FROM announcements WHERE cancelled = 0"
    else:
        query = "SELECT id, company_name, project_title, amount_in_dinars FROM announcements"

    candidates = conn.execute(query).fetchall()
    target_amount = normalize_amount(amount)

    best_id, best_score = None, 0
    for row_id, existing_company, existing_project, existing_amount in candidates:
        company_score = fuzz.ratio(company or "", existing_company or "")
        project_score = fuzz.ratio(project or "", existing_project or "")
        combined = (company_score + project_score) / 2

        amounts_match = True
        norm_existing = normalize_amount(existing_amount)
        if target_amount is not None and norm_existing is not None:
            amounts_match = abs(target_amount - norm_existing) < 1.0

        if combined >= FUZZY_THRESHOLD and amounts_match and combined > best_score:
            best_score, best_id = combined, row_id

    return best_id, best_score


def store_award(conn, ann, post_id, link, image_url):
    """Insert an award row — but first check if a cancellation placeholder
    for this same award already exists (cancellation processed before the
    award, in an out-of-order scrape). If so, fill in the placeholder's
    missing details instead of creating a disconnected duplicate row."""
    company = ann.get("company_name")
    project = ann.get("project_title")
    amount = ann.get("amount_in_dinars")

    placeholder_id, score = find_fuzzy_match(conn, company, project, amount, only_cancelled=True)

    if placeholder_id is not None:
        print(f"  found earlier cancellation placeholder (row id={placeholder_id}, score={score:.1f}) — filling in award details")
        conn.execute("""
            UPDATE announcements
            SET company_name = ?, amount_in_dinars = ?, project_title = ?,
                duration = ?, date = ?, wilaya = ?, commune = ?,
                source_post_id = ?, source_link = ?, source_image_url = ?
            WHERE id = ?
        """, (
            company, amount, project, ann.get("duration"), ann.get("date"),
            ann.get("wilaya"), ann.get("commune"), post_id, link, image_url,
            placeholder_id,
        ))
    else:
        conn.execute("""
            INSERT OR IGNORE INTO announcements
            (company_name, amount_in_dinars, project_title,
             duration, date, wilaya, commune, cancelled, source_post_id, source_link, source_image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """, (
            company, amount, project, ann.get("duration"), ann.get("date"),
            ann.get("wilaya"), ann.get("commune"), post_id, link, image_url,
        ))


def store_cancellation(conn, ann, post_id, link, image_url):
    """Find the matching award row using fuzzy text matching. If no good
    match is found, insert a placeholder row so the cancellation isn't
    lost — even if it arrives before its award."""
    target_company = ann.get("company_name") or ""
    target_project = ann.get("project_title") or ""

    best_match_id, best_score = find_fuzzy_match(
        conn, target_company, target_project, ann.get("amount_in_dinars"), only_cancelled=False
    )

    if best_match_id is not None:
        print(f"  matched cancellation to existing row id={best_match_id} (score={best_score:.1f})")
        conn.execute("""
            UPDATE announcements
            SET cancelled = 1, cancellation_reason = ?
            WHERE id = ?
        """, (ann.get("cancellation_reason"), best_match_id))
    else:
        print("  no match found for cancellation, inserting placeholder")
        conn.execute("""
            INSERT OR IGNORE INTO announcements
            (company_name, amount_in_dinars, project_title,
             duration, date, wilaya, commune, cancelled, cancellation_reason,
             source_post_id, source_link, source_image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            target_company, ann.get("amount_in_dinars"),
            target_project, ann.get("duration"), ann.get("date"),
            ann.get("wilaya"), ann.get("commune"), ann.get("cancellation_reason"),
            post_id, link, image_url,
        ))
