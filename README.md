# Singapore Venue Finder

A conversational agent that recommends restaurants, bars, and venues in Singapore — built for occasions that matter.

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:
- `GMI_API_KEY` — your GMI Cloud API key
- `GOOGLE_PLACES_API_KEY` — your Google Places API key (for Phase 2)

## Run

```bash
python app.py
```

Opens at `http://localhost:7860`

## Test Places API

```bash
python places.py
```

## Project Structure

| File | Purpose |
|------|---------|
| `app.py` | Gradio chat UI + GMI Cloud LLM integration |
| `prompts.py` | System prompt — the agent's personality and knowledge |
| `places.py` | Google Places API helper (standalone, not yet wired in) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
