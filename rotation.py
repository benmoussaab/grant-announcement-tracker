import time
from apify_client import ApifyClient
from google import genai

from config import APIFY_TOKENS, GEMINI_KEYS

_apify_index = 0
_gemini_index = 0


def get_apify_client():
    global _apify_index
    return ApifyClient(token=APIFY_TOKENS[_apify_index])


def get_gemini_client():
    global _gemini_index
    return genai.Client(api_key=GEMINI_KEYS[_gemini_index])


def call_apify_with_rotation(func, *args, **kwargs):
    global _apify_index
    attempts = 0
    while attempts < len(APIFY_TOKENS):
        try:
            client = get_apify_client()
            return func(client, *args, **kwargs)
        except Exception as e:
            error_text = str(e).lower()
            exhausted_signals = ["429", "rate limit", "exceed", "usage", "billing", "insufficient"]
            if any(signal in error_text for signal in exhausted_signals):
                print(f"Apify token {_apify_index} exhausted/rate-limited ({e}), rotating...")
                _apify_index = (_apify_index + 1) % len(APIFY_TOKENS)
                attempts += 1
                time.sleep(2)
            else:
                raise
    raise RuntimeError("All Apify tokens exhausted.")


def call_gemini_with_rotation(func, *args, **kwargs):
    global _gemini_index
    attempts = 0
    while attempts < len(GEMINI_KEYS):
        try:
            client = get_gemini_client()
            return func(client, *args, **kwargs)
        except Exception as e:
            error_text = str(e).lower()
            exhausted_signals = ["429", "resource_exhausted", "quota", "exceed"]
            if any(signal in error_text for signal in exhausted_signals):
                print(f"Gemini key {_gemini_index} exhausted, rotating...")
                _gemini_index = (_gemini_index + 1) % len(GEMINI_KEYS)
                attempts += 1
                time.sleep(2)
            else:
                raise
    raise RuntimeError("All Gemini keys exhausted.")
