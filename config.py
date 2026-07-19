import os

APIFY_TOKENS = [
    os.environ.get("APIFY_TOKEN_1"),
    os.environ.get("APIFY_TOKEN_2")
]

GEMINI_KEYS = [
    os.environ.get("GEMINI_API_KEY_1"),
    os.environ.get("GEMINI_API_KEY_2")
]
FACEBOOK_PAGE_URL = "https://www.facebook.com/profile.php?id=100083543343398"
RESULTS_LIMIT = 10000

BACKFILL_YEARS = 2

PROGRESS_FILE = "scrape_progress.json"
DB_PATH = "announcements.db"

CLASSIFY_MODEL = "gemini-3.1-flash-lite"
EXTRACT_MODEL = "gemini-3.1-flash-lite"

CLASSIFY_PROMPT = """Is this image have one of this titles ['إعلان عن المنح المؤقت' , 'إعلان عن إلغاء المنح المؤقت'] Answer only YES or NO."""

EXTRACT_PROMPT = """This is an Algerian municipal document. It is EITHER:
(A) a "Temporary Grant Announcement" (إعلان عن المنح المؤقت) — may contain ONE or MULTIPLE 
    rows in a table, each row being a separate award to a different company/lot, OR
(B) a "Cancellation of Temporary Grant Announcement" (إعلان عن إلغاء المنح المؤقت) — 
    cancelling a previously announced award.

First determine document_type: either "award" or "cancellation".

If document_title is (إعلان عن المنح المؤقت):
Return a JSON ARRAY, one object per row/lot in the table, each with:
company_name, amount_in_dinars, project_title, duration, date, wilaya, commune, document_type: "award"

IMPORTANT: If a row indicates the bid was unsuccessful / no company was awarded 
(e.g. "عدم جدوى" or similar wording meaning no feasible bid), SKIP that row entirely — 
do not include it in the output array at all.

If document_title is (إعلان عن إلغاء المنح المؤقت):
Return a JSON ARRAY with ONE object containing:
company_name, amount_in_dinars, project_title, duration, date, wilaya, commune, 
document_type: "cancellation",
cancellation_reason (the stated reason or null if not stated)

Do not guess or infer any field not clearly visible in the image text — use null if genuinely missing.
Return ONLY valid JSON, no markdown fences, no extra text."""

FUZZY_THRESHOLD = 80
