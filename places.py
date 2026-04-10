"""
Google Places API helper.

Fetches real venue candidates based on search parameters.
Returns structured data suitable for passing to the LLM as context.

Usage:
    from places import get_venues
    results = get_venues(area="Tiong Bahru", occasion="first date", price_level=2)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# Price level mapping (Google's 0-4 scale)
PRICE_LEVEL_LABELS = {
    0: "Free",
    1: "Inexpensive (~$5-15/pax)",
    2: "Moderate (~$20-50/pax)",
    3: "Expensive (~$50-100/pax)",
    4: "Very expensive ($150+/pax)",
}

SINGAPORE_LOCATION = "1.3521,103.8198"  # lat,lng centre of Singapore
SINGAPORE_RADIUS_M = 20000              # 20km covers the whole island


def get_venues(
    area: str = "",
    occasion: str = "",
    price_level: int | None = None,
    keyword: str = "",
    max_results: int = 5,
) -> list[dict]:
    """
    Search Google Places for venues matching the given parameters.

    Args:
        area:        Neighbourhood or district, e.g. "Tiong Bahru", "Dempsey"
        occasion:    Occasion type, e.g. "first date", "business lunch"
        price_level: Google price level 1-4 (1=cheap, 4=very expensive). None = any.
        keyword:     Extra search keyword, e.g. "cocktail bar", "Italian"
        max_results: How many candidates to return (max 5 recommended).

    Returns:
        List of dicts with keys: name, rating, price_level, address, opening_hours
    """
    if not GOOGLE_PLACES_API_KEY:
        raise EnvironmentError("GOOGLE_PLACES_API_KEY is not set in the environment.")

    query_parts = [p for p in [keyword, occasion, area, "Singapore"] if p]
    query = " ".join(query_parts)

    params = {
        "query": query,
        "location": SINGAPORE_LOCATION,
        "radius": SINGAPORE_RADIUS_M,
        "key": GOOGLE_PLACES_API_KEY,
        "type": "restaurant",
    }

    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API error: {data.get('status')} — {data.get('error_message', '')}")

    candidates = []
    for place in data.get("results", [])[:max_results]:
        pl = place.get("price_level")

        # Filter by price_level if requested (±1 tolerance)
        if price_level is not None and pl is not None:
            if abs(pl - price_level) > 1:
                continue

        candidates.append({
            "name": place.get("name", ""),
            "rating": place.get("rating"),
            "price_level": pl,
            "address": place.get("formatted_address", ""),
            "opening_hours": _extract_hours(place),
        })

    return candidates[:max_results]


def _extract_hours(place: dict) -> str:
    """Return a concise opening hours string from a Places result."""
    hours = place.get("opening_hours", {})
    if hours.get("open_now") is True:
        return "Open now"
    if hours.get("open_now") is False:
        return "Closed now"
    return "Hours not available"


def format_venues_for_prompt(venues: list[dict]) -> str:
    """
    Format a list of venue dicts into a compact string for inclusion
    in an LLM prompt.
    """
    if not venues:
        return "No venues found."

    lines = []
    for i, v in enumerate(venues, 1):
        rating = f"{v['rating']}/5" if v["rating"] else "No rating"
        price = PRICE_LEVEL_LABELS.get(v["price_level"], "Unknown") if v["price_level"] is not None else "Unknown"
        lines.append(
            f"{i}. {v['name']}\n"
            f"   Rating: {rating} | Price: {price}\n"
            f"   Address: {v['address']}\n"
            f"   Hours: {v['opening_hours']}"
        )

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Quick manual test — run `python places.py` to check your API key works
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing Google Places API...\n")
    try:
        results = get_venues(area="Tiong Bahru", occasion="dinner", price_level=2)
        if results:
            print(format_venues_for_prompt(results))
        else:
            print("No results returned. Check your query or API key.")
    except Exception as e:
        print(f"Error: {e}")
