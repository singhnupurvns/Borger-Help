# Borger Hjælp 🇩🇰

An AI agent that lets someone describe their life situation in plain language
(Danish, English, or another language) and get back a clear, explainable list
of Danish public welfare schemes they may be eligible for.



**Chat message → LLM extracts structured profile (Pydantic) → pure Python rules
engine checks eligibility against 7 encoded schemes (Pydantic) → LLM explains
the results in plain language → Streamlit chat UI.**

The LLM never decides eligibility — it only understands language and writes
explanations. Eligibility itself is a deterministic, unit-tested rules engine,
so you can always show *exactly* why someone did or didn't qualify.

## Files

| File | Purpose |
|---|---|
| `models.py` | Pydantic schemas: `CitizenProfile`, `SchemeRule`, `EligibilityResult` |
| `schemes.py` | 7 encoded Danish schemes (SU, boligstøtte, sygedagpenge, dagpenge, integration allowance, child benefit, folkepension) |
| `matching_engine.py` | Pure Python rules engine — no LLM calls, fully unit-tested |
| `llm_client.py` | Calls Groq or Mistral to extract profiles and explain results |
| `app.py` | Streamlit chat frontend |
| `test_matching_engine.py` | Unit tests for the rules engine (`pytest`) |
| `.env.example` | Template for your API keys |

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
cp .env.example .env
# then edit .env and paste in your key
```

### Getting a free API key

- **Groq** (recommended — very fast, generous free tier): https://console.groq.com/keys
  Set `PROVIDER=groq` and `GROQ_API_KEY=...` in `.env`.
-



## Run

```bash
streamlit run app.py
```

This opens a browser tab at `http://localhost:8501`. Start chatting, e.g.:

> "I'm 24, a full-time student in Aarhus, no income right now."

> "Jeg er 70 år, dansk statsborger, og har boet i Danmark hele mit liv."

The sidebar shows which profile fields have been filled in so far, and lets
you switch provider or reset the conversation.

## Run the tests

```bash
pip install pytest
pytest test_matching_engine.py -v
```

These tests prove the rules engine works correctly independent of any LLM —
a good thing to demo live in a viva.

## Extending with a new scheme

Just add one more `SchemeRule(...)` entry to the `SCHEMES` list in
`schemes.py`. No other file needs to change — the extraction prompt,
matching engine, and UI all work generically over whatever's in that list.

## Important caveats

- The numeric thresholds (income caps, age bands, years-of-residence
  requirements) in `schemes.py` are **illustrative placeholders**, not
  verified current legal figures — Danish benefit thresholds (satser) are
  updated yearly. Before using this for real advice, verify each value
  against the current text on [borger.dk](https://www.borger.dk).
- This tool gives *guidance*, not a legal decision. Always confirm with
  the relevant kommune or agency before relying on the result.
- Groq/Mistral models can occasionally misextract a field; the sidebar's
  "Raw profile JSON" lets you inspect and sanity-check what's been captured.

## Possible extensions

- Add Whisper speech-to-text for voice input (see original project brief).
- Add a translation pass (NLLB/MarianMT) for languages the LLM struggles with.
- Persist conversations/profiles to SQLite for session resume.
- Add LangGraph for more explicit multi-step conversation control.
- Add more schemes — each is just one more `SchemeRule` entry.
