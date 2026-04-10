import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
import os
from prompts import SYSTEM_PROMPT
from places import get_venues, format_venues_for_prompt
from image_gen import generate_vibe_image

load_dotenv()

# ============================================
# MODEL 1: Claude Sonnet (anthropic/claude-sonnet-4.6)
# Via GMI Cloud API - handles conversation reasoning
# and venue recommendations
# ============================================
GMI_BASE_URL = "https://api.gmi-serving.com/v1"
GMI_CHAT_MODEL = "anthropic/claude-sonnet-4.6"

client = OpenAI(
    api_key=os.getenv("GMI_API_KEY"),
    base_url=GMI_BASE_URL,
)

# Singapore neighbourhoods for area detection
_AREAS = [
    "tiong bahru", "keong saik", "tanjong pagar", "dempsey", "clarke quay",
    "robertson quay", "chinatown", "ann siang", "east coast", "orchard",
    "joo chiat", "katong", "little india", "buona vista", "one-north",
    "marina bay", "cbd", "raffles place", "sentosa", "harbourfront",
    "novena", "newton", "holland village", "bugis", "city hall", "amk",
    "ang mo kio", "tampines", "jurong", "woodlands",
]

_OCCASION_KEYWORDS = {
    "first date": "first date romantic restaurant",
    "date night": "romantic restaurant bar",
    "date": "romantic restaurant",
    "business lunch": "restaurant quiet professional",
    "client dinner": "fine dining restaurant",
    "client": "fine dining restaurant",
    "birthday": "restaurant celebration",
    "anniversary": "romantic fine dining",
    "friends": "bar restaurant casual",
    "catching up": "casual restaurant bar",
    "solo": "restaurant solo friendly",
}


def _safe_get_content(h) -> str:
    if isinstance(h, dict):
        content = h.get("content", "")
        if isinstance(content, list):
            return " ".join(
                item.get("text", "") for item in content
                if isinstance(item, dict)
            )
        return str(content)
    elif isinstance(h, (list, tuple)) and len(h) > 0:
        return str(h[0])
    return str(h)


def _extract_search_params(history: list, message: str) -> tuple:
    """
    Heuristic extraction of search params from conversation text.
    Returns (area, occasion, price_level, keyword).
    """
    full_text = (" ".join(_safe_get_content(h) for h in history) + " " + message).lower()

    area = next((a for a in _AREAS if a in full_text), "Singapore")

    occasion = "dinner"
    keyword = "restaurant"
    for trigger, kw in _OCCASION_KEYWORDS.items():
        if trigger in full_text:
            occasion = trigger
            keyword = kw
            break

    price_level = None
    if any(w in full_text for w in ["cheap", "budget", "hawker", "affordable", "inexpensive"]):
        price_level = 1
    elif any(w in full_text for w in ["mid-range", "moderate", "casual", "mid range"]):
        price_level = 2
    elif any(w in full_text for w in ["fine dining", "fancy", "splurge", "high end", "impress"]):
        price_level = 3
    elif any(w in full_text for w in ["very expensive", "luxury", "michelin"]):
        price_level = 4

    return area, occasion, price_level, keyword


def _price_label(price_level) -> str:
    return {1: "budget", 2: "mid-range", 3: "upscale", 4: "luxury"}.get(price_level, "any budget")


def _make_image_prompt(area: str, occasion: str) -> str:
    area_visuals = {
        "tiong bahru": "pastel art deco shophouses, indie cafes with warm fairy lights",
        "keong saik": "vibrant Keong Saik Road shophouses with neon bar signs and lanterns",
        "tanjong pagar": "glowing cocktail bar facades along a heritage Singapore street",
        "dempsey": "colonial bungalow surrounded by lush tropical jungle, candlelit terrace",
        "clarke quay": "neon-lit riverside promenade, lights shimmering on dark water",
        "robertson quay": "quiet riverside terrace, string lights over the Singapore River",
        "chinatown": "red lantern-lit Ann Siang Hill, atmospheric heritage shophouses",
        "ann siang": "red lantern-lit Ann Siang Hill, atmospheric heritage shophouses",
        "east coast": "breezy seaside seafood terrace, open sky and sea breeze",
        "joo chiat": "Peranakan shophouse facade in jewel-toned tiles, twilight glow",
        "katong": "Peranakan shophouse facade in jewel-toned tiles, twilight glow",
        "orchard": "sleek modern Singapore skyline at dusk, upscale dining room interior",
        "marina bay": "glittering Marina Bay skyline at night reflected on water",
    }
    occasion_mood = {
        "first date": "intimate and romantic, warm golden hour lighting, soft bokeh",
        "date night": "intimate and romantic, warm golden hour lighting, soft bokeh",
        "date": "intimate and romantic, warm candlelight, soft focus",
        "business lunch": "bright and professional, clean lines, elegant interior",
        "client dinner": "sophisticated and impressive, moody elegant lighting, premium feel",
        "birthday": "festive warm lighting, celebratory atmosphere, joyful energy",
        "anniversary": "deeply romantic, candlelit, luxurious and intimate",
        "friends": "lively and buzzy, vibrant energy, people laughing in background",
        "catching up": "relaxed and cosy, warm tones, casual weekend afternoon vibe",
        "solo": "peaceful and contemplative, single warm light, quiet corner of a cafe",
    }

    scene = area_visuals.get(area, "moody Singapore shophouse street at golden hour")
    mood = occasion_mood.get(occasion, "warm and inviting, cinematic photography")
    return f"{scene}, {mood}, Singapore, editorial food photography style, no text"


# Module-level cache — persists across turns in a session.
# Keyed on (area, occasion, price_level, keyword) so we only hit
# the Places API again when the extracted params actually change.
_places_cache: dict = {
    "params": None,
    "venues": [],
    "formatted": "",
    "image_url": None,
}


def chat(message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": _safe_get_content(h)})

    user_content = message
    trace = ""
    area, occasion = "Singapore", "dinner"  # fallback values for image prompt
    should_generate_image = False

    if len(history) >= 2:
        area, occasion, price_level, keyword = _extract_search_params(history, message)
        current_params = (area, occasion, price_level, keyword)

        if current_params != _places_cache["params"]:
            # ============================================
            # EXTERNAL API: Google Places
            # Fetches real-time venue data (ratings, hours, addresses)
            # ============================================
            # Params changed (or first call) — fetch fresh results
            print(f"[Places] Triggering API call — area={area!r}, occasion={occasion!r}, price_level={price_level}, keyword={keyword!r}")
            trace = f"🔍 Searching Google Places for: {area} | {keyword} | {_price_label(price_level)}"
            try:
                venues = get_venues(area=area, occasion=occasion, price_level=price_level, keyword=keyword)
                print(f"[Places] Returned {len(venues)} results")
                _places_cache["params"] = current_params
                _places_cache["venues"] = venues
                _places_cache["formatted"] = format_venues_for_prompt(venues) if venues else ""
                _places_cache["image_url"] = None  # reset — will generate fresh below
                if venues:
                    trace = (
                        f"🔍 Searching Google Places for: {area} | {keyword} | {_price_label(price_level)}\n"
                        f"📍 Found {len(venues)} real venues in {area} — reasoning on live data..."
                    )
                    should_generate_image = True
                else:
                    trace = "🔍 Searched Google Places — no venues matched. Falling back to local knowledge."
            except Exception as e:
                print(f"[Places] API call failed: {e!r}")
                trace = "💭 Using local knowledge (Places API unavailable)"
        else:
            # Same params as last turn — reuse cached results
            print(f"[Places] Cache hit — reusing {len(_places_cache['venues'])} results for params {current_params}")
            trace = (
                f"📍 Using cached venues for {area} ({len(_places_cache['venues'])} results) — no new search needed"
            )

        # Always inject the most recent Places results if we have any
        if _places_cache["venues"]:
            user_content = (
                f"{message}\n\n"
                f"PLACES_DATA: Here are real venues from Google Places matching the criteria "
                f"(area: {area}, occasion: {occasion}):\n\n{_places_cache['formatted']}\n\n"
                f"Use these as your primary source for recommendations, but add your own "
                f"knowledge about vibe, atmosphere, and what makes each place special."
            )
    else:
        trace = "💭 Still gathering context before searching venues..."

    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model=GMI_CHAT_MODEL,
        messages=messages
    )
    reply = response.choices[0].message.content

    # Step 1 — yield chat reply immediately, image panel stays hidden
    yield reply, trace, gr.update(visible=False)

    # Step 2 — generate image if new Places results came in
    if should_generate_image:
        img_prompt = _make_image_prompt(area, occasion)
        print(f"[ImageGen] Generating image for area={area!r}, occasion={occasion!r}")
        image_url = generate_vibe_image(img_prompt)
        _places_cache["image_url"] = image_url

        # Step 3 — reveal image panel only if generation succeeded
        if image_url:
            yield (
                reply + "\n\n✨ I've put together a visual of the kind of atmosphere I'm thinking — does this feel right for tonight, or would you prefer somewhere with a different energy?",
                trace,
                gr.update(visible=True, value=image_url),
            )


# ---------------------------------------------------------------------------
# UI — ChatInterface on top, Agent Activity trace below
# render=False lets us define the trace component before ChatInterface
# (so it can be passed to additional_outputs) while rendering it after
# ---------------------------------------------------------------------------
_CSS = """
/* ── Main background: dark with radial centre-glow ── */
body, .gradio-container {
    background: radial-gradient(ellipse at center, #222222 0%, #1A1A1A 70%, #111111 100%) !important;
    color: #E8DCC8 !important;
}

/* ── Title ── */
.gradio-container h1 {
    color: #D4A847 !important;
    font-weight: 700 !important;
}

/* ── Subtitle / description ── */
.gradio-container .description p,
.gradio-container .description {
    color: #A89070 !important;
}

/* ── Chat bubbles ── */
.message.user, .message.bot {
    background: #242424 !important;
    border: 1px solid #2E2E2E !important;
    color: #E8DCC8 !important;
}

/* ── Input textbox ── */
textarea, input[type="text"] {
    background: #242424 !important;
    color: #E8DCC8 !important;
    border: 1px solid #3A3020 !important;
}

/* ── Send button ── */
button.primary, button[variant="primary"] {
    background: #D4A847 !important;
    color: #1A1A1A !important;
    font-weight: 600 !important;
    border: none !important;
}
button.primary:hover, button[variant="primary"]:hover {
    background: #E0B84E !important;
}

/* ── Agent Activity panel ── */
#agent-activity textarea {
    background: #242424 !important;
    border-left: 3px solid #D4A847 !important;
    border-top: none !important;
    border-right: none !important;
    border-bottom: none !important;
    color: #A89070 !important;
    padding-left: 12px !important;
    border-radius: 0 4px 4px 0 !important;
}
#agent-activity label {
    color: #D4A847 !important;
}

/* ── Tonight's Vibe image ── */
#vibe-image img {
    border-radius: 12px !important;
}
"""

with gr.Blocks(title="Makan Maestro", css=_CSS) as demo:
    trace_box = gr.Textbox(
        label="Agent Activity",
        interactive=False,
        lines=2,
        max_lines=4,
        elem_id="agent-activity",
        render=False,
    )
    vibe_image = gr.Image(
        label="Tonight's Vibe",
        interactive=False,
        visible=False,
        elem_id="vibe-image",
        render=False,
    )

    gr.ChatInterface(
        fn=chat,
        title="🍜 Makan Maestro",
        description="<p style='text-align: center; color: #A89070'>Your local insider for any meal that matters — dates, business dinners, client lunches, catching up with friends</p>",
        textbox=gr.Textbox(placeholder="Tell me who you're meeting — a date, a business contact, friends — and what kind of venue you're looking for", show_label=False),
        chatbot=gr.Chatbot(label="Chat with your local insider"),
        additional_outputs=[trace_box, vibe_image],
    )

    trace_box.render()
    vibe_image.render()

demo.launch()
