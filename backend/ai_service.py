import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_ROOT / "profile"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


load_dotenv(PROJECT_ROOT / ".env")


class AIServiceError(Exception):
    """Raised when the AI workflow cannot complete successfully."""


def _read_text_file(path: Path, required: bool = True) -> str:
    if not path.exists():
        if required:
            raise AIServiceError(f"Missing required file: {path.name}")
        return ""
    return path.read_text(encoding="utf-8").strip()


def _build_profile_context(include_cover_letter: bool = True) -> str:
    sections = [
        ("CV", _read_text_file(PROFILE_DIR / "cv.md")),
        ("Courses", _read_text_file(PROFILE_DIR / "courses.md", required=False)),
        ("Extra Notes", _read_text_file(PROFILE_DIR / "extra_notes.md", required=False)),
    ]

    if include_cover_letter:
        sections.append(
            ("Current Cover Letter", _read_text_file(PROFILE_DIR / "cover_letter.md"))
        )

    rendered_sections = []
    for title, content in sections:
        if content:
            rendered_sections.append(f"{title}:\n{content}")
    return "\n\n".join(rendered_sections)


def _extract_text_blocks(payload: dict[str, Any]) -> str:
    blocks = payload.get("content", [])
    text_parts = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))
    return "\n".join(part for part in text_parts if part).strip()


def _extract_json(response_text: str) -> dict[str, Any]:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIServiceError("Claude response was not valid JSON.")
        try:
            return json.loads(response_text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIServiceError("Claude response was not valid JSON.") from exc


def _call_claude(prompt_name: str, job_description: str, include_cover_letter: bool) -> dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise AIServiceError("Missing `ANTHROPIC_API_KEY` in `.env`.")

    prompt_text = _read_text_file(PROMPTS_DIR / prompt_name)
    profile_context = _build_profile_context(include_cover_letter=include_cover_letter)

    user_message = (
        f"{prompt_text}\n\n"
        f"Candidate Profile:\n{profile_context}\n\n"
        f"Job Description:\n{job_description.strip()}"
    )

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        "max_tokens": 2200,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers=headers,
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise AIServiceError(f"Claude API request failed: {exc}") from exc

    response_text = _extract_text_blocks(response.json())
    if not response_text:
        raise AIServiceError("Claude API returned an empty response.")

    parsed = _extract_json(response_text)
    parsed["_raw_response"] = response_text
    return parsed


def analyze_job(job_description: str) -> dict[str, Any]:
    if not job_description or not job_description.strip():
        raise AIServiceError("Job description cannot be empty.")
    return _call_claude(
        prompt_name="analyze_job.md",
        job_description=job_description,
        include_cover_letter=True,
    )


def tailor_application(job_description: str) -> dict[str, Any]:
    if not job_description or not job_description.strip():
        raise AIServiceError("Job description cannot be empty.")
    return _call_claude(
        prompt_name="tailor_application.md",
        job_description=job_description,
        include_cover_letter=True,
    )
