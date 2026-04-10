# Makan Maestro
*Your local insider for any meal that matters*

---

## Product Name, Form & Pain Point

Makan Maestro is a conversational web agent that recommends restaurants, bars and venues in Singapore for any occasion — first dates, business lunches, client dinners, catching up with friends, or a solo treat.

The pain point is familiar to anyone in Singapore: when the meal matters, generic search results fail you. Google returns SEO-optimised listicles. Review apps give popularity rankings divorced from context. Asking friends gets you their small personal repertoire. None of these understand your specific situation — who you're meeting, what vibe you need, what's at stake.

Makan Maestro reasons about your situation the way a well-connected local friend would. It asks the right questions and gives you an opinionated recommendation with reasoning shown — not a ranked list, but a confident suggestion with honest caveats.

---

## API Usage

Makan Maestro orchestrates three services in a single conversation flow:

**Claude Sonnet via GMI Cloud** handles conversational reasoning — asking follow-up questions, interpreting context, and synthesising live data into locally-aware recommendations.

**Google Places API** is called as a live tool once enough context is gathered, fetching real venue candidates with current ratings, addresses, opening hours and price levels.

**Gemini 3 Pro Image Preview via GMI Cloud** generates an atmospheric mood image matched to the occasion and neighbourhood. The agent then asks the user to confirm whether the vibe matches — making image generation functional, not decorative.

This three-part orchestration demonstrates GMI Cloud's ability to serve multiple model types through a unified API layer.

---

## Tech Stack & Core Features

**Stack:** Python, Gradio, OpenAI SDK (via GMI Cloud), Google Places API, python-dotenv

**Features:**
- Occasion-aware recommendations across dating, business, social and solo contexts
- Live venue data with real ratings, addresses and opening hours
- Singapore-specific knowledge baked in — neighbourhood vibes, hawker vs restaurant, supper culture
- Transparent agent activity panel showing when live data is fetched
- Atmospheric vibe image generated per session
- Graceful fallback to model knowledge if any external API is unavailable

---

## Setup

### Prerequisites
- Python 3.10+
- GMI Cloud API key
- Google Places API key

### Installation
```bash
git clone https://github.com/khoodose/GMI-ZAI-hackathon.git
cd GMI-ZAI-hackathon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### Run
```bash
python app.py
```
Then open http://localhost:7860 in your browser.

## Project Structure

| File | Purpose |
|------|---------|
| `app.py` | Gradio chat UI + GMI Cloud LLM integration |
| `prompts.py` | System prompt — the agent's personality and knowledge |
| `places.py` | Google Places API helper |
| `image_gen.py` | GMI Cloud image generation with async polling |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
