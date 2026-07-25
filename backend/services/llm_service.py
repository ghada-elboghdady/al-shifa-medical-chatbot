"""
LLM Service — calls Google Gemini to generate responses.
Uses the new google-genai SDK with robust fallback handling.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from google import genai
from google.genai import types
from dotenv import load_dotenv

from services import rag_service

load_dotenv(override=True)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
# Use the correct free Gemini model name
GEMINI_MODEL = "gemini-flash-latest"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


def initialize():
    """Initialize and verify Gemini client."""
    _get_client()
    print(f"[LLM] Initialized Gemini client (model: {GEMINI_MODEL})")


def _load_system_prompt(hospital_context: str) -> str:
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    return template.replace("{hospital_context}", hospital_context)


def _detect_language(text: str) -> str:
    """Detect if text is primarily Arabic or English."""
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    return "ar" if arabic_chars > len(text) * 0.3 else "en"


def _is_valid_dict(res: Any) -> bool:
    return isinstance(res, dict) and ("answer" in res or "action" in res or "type" in res)


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response with multiple fallback strategies.
    Guarantees a valid response dict (medical/general text or structured action).
    """
    if not text or not text.strip():
        return {"type": "general", "language": "en", "answer": "I'm here to help. Could you please rephrase your question?"}

    original_text = text.strip()

    # Strategy 1: Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", original_text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        text = original_text

    # Strategy 2: Try direct JSON parse
    try:
        result = json.loads(text)
        if _is_valid_dict(result):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find first { ... } block and try to parse it
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        json_candidate = obj_match.group(0)
        try:
            result = json.loads(json_candidate)
            if _is_valid_dict(result):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: Regex extraction for "answer" field if JSON is truncated or malformed
    ans_match = re.search(r'"answer"\s*:\s*"([\s\S]*?)"(?=\s*[,}\n]|\s*"[a-z_]+")', text)
    if not ans_match:
        ans_match = re.search(r'"answer"\s*:\s*"([\s\S]*?)"', text)

    if ans_match:
        extracted_ans = ans_match.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').strip()
        if extracted_ans:
            lang = _detect_language(extracted_ans)
            spec_match = re.search(r'"suggested_specialty"\s*:\s*"([^"]+)"', text)
            booking_match = re.search(r'"suggest_booking"\s*:\s*(true|false)', text)
            res = {
                "type": "medical" if spec_match else "general",
                "language": lang,
                "answer": extracted_ans,
            }
            if spec_match:
                res["suggested_specialty"] = spec_match.group(1)
            if booking_match:
                res["suggest_booking"] = booking_match.group(1) == "true"
            return res

    # Strategy 5: Clean up all JSON syntax artifacts if raw text leaked
    clean = re.sub(r'```(?:json)?|```', '', original_text).strip()
    clean = re.sub(r'^\s*[\{\}\]\,]+', '', clean).strip()
    clean = re.sub(r'[\{\}\]\,]+\s*$', '', clean).strip()
    clean = re.sub(r'"(?:type|language|suggested_specialty|suggest_booking|action)"\s*:\s*"?[^",\n}]+"?', '', clean)
    clean = re.sub(r'"answer"\s*:\s*', '', clean).replace('"', '').strip()

    lang = _detect_language(clean)
    return {"type": "general", "language": lang, "answer": clean or "I'm here to help. Could you please rephrase your question?"}


async def chat(
    message: str,
    history: List[Dict],
    session_id: str,
) -> Dict[str, Any]:
    """
    Send a message to Gemini with conversation history and RAG context.
    Returns a parsed response dict that always contains 'answer' or action object.
    """
    client = _get_client()

    # Retrieve relevant hospital context
    hospital_context = rag_service.retrieve(message, n_results=8)

    # Build system prompt
    system_prompt = _load_system_prompt(hospital_context)

    # Build full prompt including history
    if history:
        history_str = "\n".join(
            [f"{'Patient' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
             for h in history[-8:]]
        )
        full_prompt = (
            f"{system_prompt}\n\n"
            f"Previous conversation:\n{history_str}\n\n"
            f"Now respond to this message from the patient:\n\nPatient: {message}"
        )
    else:
        full_prompt = (
            f"{system_prompt}\n\n"
            f"Now respond to this message from the patient:\n\nPatient: {message}"
        )

    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text
        print(f"[LLM] Raw response length: {len(raw_text)} chars")
        result = _extract_json(raw_text)
    except Exception as e:
        print(f"[LLM] Error during generation: {e}")
        raise

    # Final safety net: ensure response always has required fields
    if "answer" not in result:
        result["answer"] = str(result.get("response", "I'm here to help. Could you please try again?"))
    if "type" not in result:
        result["type"] = "general"
    if "language" not in result:
        result["language"] = _detect_language(result["answer"])

    return result


async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """
    Transcribe audio using Gemini's multimodal capabilities.
    Returns transcribed text.
    """
    client = _get_client()

    prompt = (
        "Please transcribe the following audio recording exactly as spoken. "
        "The speaker may be speaking in Arabic or English. "
        "Return ONLY the transcribed text, nothing else."
    )

    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return response.text.strip()
