"""
Step 4-5 of the workflow: AI generates a HYPOTHESIS from an uploaded photo,
never a final memory.

DECISION (this session): reverted from the local-Ollama/llava plan back to
Gemini (cloud) as the ONLY vision path. Running a local vision-language
model needs a GPU (or a very patient CPU) that isn't available for this
build, so "offline/local AI" as originally scoped is not realistic here.

Honest tradeoff: this makes photo analysis require internet connectivity.
If "offline support" still needs to be true in your pitch, be explicit that
it now means "reminders/quiz/memory browsing work offline, photo analysis
needs a connection" rather than fully offline AI - don't claim more than
this code does.

Reliability measures given this is now a hard dependency on a 3rd-party
cloud API: a fast timeout (never hang a demo), graceful JSON-parse
fallback, and a safe default hypothesis if Gemini is unreachable or
misconfigured so the rest of the flow (face detection, human review) can
still proceed even if the vision hypothesis comes back empty.
"""
import json
import logging
from app.config import settings

logger = logging.getLogger("vision_service")

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except Exception as e:
    genai = None
    _GENAI_AVAILABLE = False
    logger.warning(f"google-generativeai unavailable ({e}). Photo hypothesis will use the offline fallback.")

GEMINI_MODEL = "gemini-3.6-flash"  # fast + cheap, good fit for a real-time upload flow
GEMINI_TIMEOUT_S = 12  # fail fast rather than hang a demo on a slow/stuck request

PROMPT = """You are analyzing a personal photo for a memory-recall system for an elderly patient with dementia.
Carefully look at the image and respond with ONLY valid JSON (no markdown fences, no extra text).

Classify the image into exactly one of these scene_type values:
  - "people"       — one or more identifiable people are the main subject
  - "landmark"     — a famous place, monument, tourist attraction, or recognizable building
  - "event"        — a celebration, ceremony, or special occasion (wedding, birthday, festival)
  - "place"        — a non-famous but meaningful location (home, garden, hospital, school)
  - "object"       — a significant object (heirloom, gift, food, document)
  - "mixed"        — multiple equally important elements

Return exactly this JSON structure:

{
  "scene_type": "<one of the 6 values above>",
  "scene": "short scene description, e.g. beach, living room, Taj Mahal",
  "activity": "what is happening or being shown",
  "location_hint": "best guess at location name or null if unclear",
  "landmark_name": "if scene_type is landmark or event, official name of the place or event, else null",
  "landmark_description": "if scene_type is landmark, 1–2 sentence factual description a senior might remember, else null",
  "objects": ["list", "of", "notable", "objects"],
  "people_count": <integer — number of faces or people visible>,
  "context": "A detailed paragraph describing the context of the image. Add as much relevant context as possible to help with memory recall.",
  "quiz_questions": [
    "Who added this photo?",
    "What is the context of this photo?",
    "Who is this? (include if people are in the photo)",
    "What is this place? (include if it is a tourism place or landmark)"
  ],
  "confidence": <float between 0 and 1>
}

For quiz_questions, ALWAYS include "Who added this photo?" and "What is the context of this photo?". 
If people are in the photo, include "Who is this?". 
If it is a tourism place or landmark, include "What is this place?".
Add any other relevant questions that would help with memory recall based on the image context.

Be honest about uncertainty, lower confidence when ambiguous. Never invent specific names of people."""


_configured = False


def _ensure_configured():
    global _configured
    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-generativeai is not installed.")
    if not _configured:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


def analyze_photo(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    if not _GENAI_AVAILABLE:
        return _fallback_hypothesis("Vision AI library not installed on the server.")
    if not settings.GEMINI_API_KEY:
        return _fallback_hypothesis("No Gemini API key configured.")

    try:
        _ensure_configured()
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            [PROMPT, {"mime_type": mime_type, "data": image_bytes}],
            request_options={"timeout": GEMINI_TIMEOUT_S},
        )
        text = response.text.strip().strip("```json").strip("```").strip()
        result = json.loads(text)
        result["source"] = "cloud"
        return result
    except json.JSONDecodeError as e:
        print(f"Gemini returned non-JSON response: {e}")
        return _fallback_hypothesis("AI response could not be parsed. Please fill in details manually.")
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
        return _fallback_hypothesis("Could not analyze image automatically - AI may be rate-limited, offline, or unreachable.")


def _fallback_hypothesis(reason: str) -> dict:
    """
    Used if no API key set, no connectivity, rate-limited, or the call fails.
    Keeps the rest of the flow (face suggestions, human review, save) working
    even when the vision hypothesis itself couldn't be generated.
    """
    return {
        "scene_type": "unknown",
        "scene": "unknown",
        "activity": "unknown",
        "location_hint": None,
        "landmark_name": None,
        "landmark_description": None,
        "objects": [],
        "people_count": 0,
        "context": f"{reason}",
        "quiz_questions": [],
        "confidence": 0.0,
        "source": "none",
    }

