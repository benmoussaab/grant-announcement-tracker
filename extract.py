"""
extract.py
Classifies an image as a genuine grant announcement (or cancellation),
and extracts structured JSON from confirmed matches, using Gemini.
"""

from google.genai import types

from config import CLASSIFY_MODEL, EXTRACT_MODEL, CLASSIFY_PROMPT, EXTRACT_PROMPT
from rotation import call_gemini_with_rotation


def _do_classify(client, image_bytes):
    response = client.models.generate_content(
        model=CLASSIFY_MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            types.Part.from_text(text=CLASSIFY_PROMPT),
        ])],
    )
    return response.text.strip().upper() == "YES"


def is_grant_announcement(image_bytes):
    return call_gemini_with_rotation(_do_classify, image_bytes)


def _do_extract(client, image_bytes):
    response = client.models.generate_content(
        model=EXTRACT_MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            types.Part.from_text(text=EXTRACT_PROMPT),
        ])],
    )
    return response.text


def extract_announcement(image_bytes):
    return call_gemini_with_rotation(_do_extract, image_bytes)


def clean_json_response(text):
    """Strips markdown code fences (```json ... ```) if Gemini adds them
    despite being told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text
