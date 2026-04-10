# ============================================
# MODEL 2: Gemini 3 Pro Image Preview
# Via GMI Cloud API - generates atmospheric vibe images
# ============================================

"""
GMI Cloud image generation helper.

Uses an async queue API — submit a request, then poll until done.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

_IMAGE_ENDPOINT = os.getenv("GMI_IMAGE_ENDPOINT")
_API_KEY = os.getenv("GMI_API_KEY")
_MODEL = os.getenv("GMI_IMAGE_MODEL", "gemini-3-pro-image-preview")

_POLL_INTERVAL = 3    # seconds between polls
_TIMEOUT = 120        # max seconds to wait


def generate_vibe_image(prompt: str) -> str | None:
    """
    Submit an image generation request to GMI Cloud and poll for the result.

    Args:
        prompt: Text prompt describing the desired image.

    Returns:
        Image URL string on success, None on failure or timeout.
    """
    if not _IMAGE_ENDPOINT or not _API_KEY:
        print("[ImageGen] Missing GMI_IMAGE_ENDPOINT or GMI_API_KEY — skipping")
        return None

    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }

    # Step 1: Submit request
    payload = {
        "model": _MODEL,
        "payload": {
            "prompt": prompt,
            "image_size": "1K",
            "aspect_ratio": "16:9",
        },
    }

    try:
        print(f"[ImageGen] Submitting request — model={_MODEL!r}, prompt={prompt[:80]!r}...")
        resp = requests.post(_IMAGE_ENDPOINT, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            print(f"[ImageGen] No request_id in response: {data}")
            return None
        print(f"[ImageGen] Queued — request_id={request_id!r}")
    except Exception as e:
        print(f"[ImageGen] Submit failed: {e!r}")
        return None

    # Step 2: Poll for result
    poll_url = f"{_IMAGE_ENDPOINT}/{request_id}"
    deadline = time.time() + _TIMEOUT

    while time.time() < deadline:
        time.sleep(_POLL_INTERVAL)
        try:
            poll_resp = requests.get(poll_url, headers=headers, timeout=30)
            poll_resp.raise_for_status()
            result = poll_resp.json()
            status = result.get("status")
            print(f"[ImageGen] Poll status={status!r}")

            if status == "success":
                try:
                    url = result["outcome"]["media_urls"][0]["url"]
                    print(f"[ImageGen] Success — url={url[:80]!r}...")
                    return url
                except (KeyError, IndexError, TypeError) as e:
                    print(f"[ImageGen] Unexpected success payload: {e!r} — {result}")
                    return None

            if status == "failed":
                print(f"[ImageGen] Generation failed: {result}")
                return None

            # Any other status (queued, processing) — keep polling

        except Exception as e:
            print(f"[ImageGen] Poll error: {e!r}")
            return None

    print(f"[ImageGen] Timed out after {_TIMEOUT}s")
    return None
