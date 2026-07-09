"""
LLM layer (Groq-only): the ONLY thing the LLM does is:
  1. Read the conversation so far.
  2. Extract/update a structured CitizenProfile (validated by Pydantic).
  3. Explain results back to the user in plain language.

It never decides eligibility itself — that's matching_engine.py's job.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from pydantic import ValidationError

from models import CitizenProfile

EXTRACTION_SYSTEM_PROMPT = """You are a structured data extraction assistant for a Danish public
services assistant called Borger Hjælp. You will be given:
1. The CURRENT known profile of a citizen (as JSON), which may be incomplete.
2. The latest message from the citizen (in any language: Danish, English, Ukrainian, Arabic, etc).

Your job: return an UPDATED profile as a single JSON object, merging any new information
you can confidently infer from the latest message into the current profile. Never remove
information that was already known unless the user explicitly corrects it.

Only include fields you are reasonably confident about. Leave fields you don't know as their
current value (don't guess).

The JSON object MUST have exactly these keys:
- age: integer or null
- residency_status: one of "citizen", "permanent_resident", "refugee", "student_visa",
  "work_visa", "eu_citizen", "unknown"
- municipality: string or null (Danish kommune name, e.g. "Aarhus", "Copenhagen")
- monthly_income_dkk: number or null
- is_student: boolean
- has_children: boolean
- number_of_children: integer
- employment_status: one of "employed", "unemployed", "sick_leave", "retired", "student", "unknown"
- years_in_denmark: number or null
- is_sick_or_injured: boolean

Respond with ONLY the JSON object. No markdown fences, no commentary, no preamble.
"""

EXPLAIN_SYSTEM_PROMPT = """You are Borger Hjælp, a warm, patient, plain-language assistant that
helps people in Denmark understand which public welfare services they may qualify for.

You will be given a list of scheme results (each with: name, description, eligible/not/needs-info,
which specific rules passed or failed, official URL, and required documents), plus the user's most
recent message.

CRITICAL LANGUAGE RULE: Detect the language of the user's most recent message ONLY (ignore Danish
proper nouns like place names, scheme names, or municipality names — those don't count as Danish
language, they're just names). Reply in that exact same language. If the user wrote in English,
reply in English, even if Danish words like "Aarhus", "SU", or "Boligstøtte" appear in the results
or their message. Never switch language just because scheme names or city names are Danish.

Write a short, friendly, encouraging response in that language.
Rules:
- Never use bureaucratic jargon; explain things simply, as if to someone unfamiliar with Danish systems.
- Group results into: "You likely qualify for", "You might qualify — I need a bit more information",
  and (briefly, if relevant) "Not likely a fit right now".
- For each "likely qualify" scheme, give a short checklist of documents/next steps and the official URL.
- If you need more info, ask ONE clear, specific follow-up question at the end (not a list of many).
- Keep it concise — this is a chat message, not a report.
"""


def _chat_completion(messages: list[dict], temperature: float = 0.0) -> str:
    """Sends a chat completion request to Groq and returns the assistant's raw text content."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file or the sidebar.")

    client = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def extract_profile(current_profile: CitizenProfile, user_message: str, max_retries: int = 2) -> CitizenProfile:
    """Calls Groq to update the CitizenProfile from a new user message.
    Retries with the validation error fed back to the model if the JSON
    doesn't validate against the Pydantic schema."""

    last_error: Optional[str] = None
    raw_output = ""

    for attempt in range(max_retries + 1):
        user_prompt = (
            f"CURRENT PROFILE (JSON):\n{current_profile.model_dump_json()}\n\n"
            f"LATEST CITIZEN MESSAGE:\n{user_message}\n"
        )
        if last_error:
            user_prompt += (
                f"\nNOTE: your previous JSON output failed validation with this error, "
                f"please fix it and return valid JSON only:\n{last_error}\n"
            )

        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_output = _chat_completion(messages, temperature=0.0)
        cleaned = raw_output.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

        try:
            data = json.loads(cleaned)
            return CitizenProfile(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = str(e)
            continue

    # If all retries failed, return the unchanged profile rather than crashing the app.
    return current_profile


def explain_results(results_summary: str, conversation_language_hint: str = "") -> str:
    """Calls Groq to turn eligibility results into a friendly chat message."""
    messages = [
        {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"{conversation_language_hint}\n\nSCHEME RESULTS:\n{results_summary}"
            ),
        },
    ]
    return _chat_completion(messages, temperature=0.4)