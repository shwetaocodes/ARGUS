import json
import ollama
from app.core.config import settings
from app.models.event_classification import EventCategory, ConfidenceLevel

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

VALID_CATEGORIES = {c.value for c in EventCategory}
VALID_CONFIDENCE = {c.value for c in ConfidenceLevel}


FEW_SHOT_EXAMPLES = """Example 1:
Text: "Unidentified individuals were spotted crossing the fence near the border post at night, evading patrol."
Classification: {"category": "infiltration_attempt", "confidence": "high"}

Example 2:
Text: "A roadside explosive device detonated as a military vehicle passed, causing damage but no confirmed casualties."
Classification: {"category": "ied", "confidence": "high"}

Example 3:
Text: "Hundreds gathered in the city center demanding government action, chanting slogans for several hours."
Classification: {"category": "protest", "confidence": "high"}

Example 4:
Text: "Satellite imagery shows armored vehicles repositioning approximately 5km from the border, formation consistent with routine rotation."
Classification: {"category": "troop_movement", "confidence": "medium"}

Example 5:
Text: "State media aired a broadcast condemning foreign interference, calling for national unity against external threats."
Classification: {"category": "propaganda_broadcast", "confidence": "high"}

Example 6:
Text: "Gunfire was exchanged across the ceasefire line for the third time this month, both sides blaming the other."
Classification: {"category": "ceasefire_violation", "confidence": "high"}

Example 7:
Text: "A convoy of trucks carrying food and medical supplies crossed the checkpoint under military escort."
Classification: {"category": "supply_convoy", "confidence": "high"}

Example 8:
Text: "Fighter jets were seen conducting low-altitude passes along the border region for the second consecutive day."
Classification: {"category": "aerial_activity", "confidence": "high"}
"""

CLASSIFIER_PROMPT = """You are classifying security/conflict-related text into a fixed taxonomy. Study the examples, then classify the new text. Return ONLY valid JSON.

Categories: infiltration_attempt, ied, protest, troop_movement, propaganda_broadcast, ceasefire_violation, supply_convoy, aerial_activity, other

Use "other" only if none of the eight categories genuinely fit — do not force a weak match.

Confidence guide:
- high: text explicitly and unambiguously describes the category
- medium: text is suggestive but lacks a key confirming detail
- low: text is vague, indirect, or the category is a best guess

{examples}

Now classify this text:
Text: "{text}"

Return format: {{"category": "...", "confidence": "high|medium|low", "reasoning": "one short sentence"}}
"""


def classify_event(text: str) -> dict | None:
    prompt = CLASSIFIER_PROMPT.format(examples=FEW_SHOT_EXAMPLES, text=text[:4000])

    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        result = json.loads(response["message"]["content"])

        if result.get("category") not in VALID_CATEGORIES:
            print(f"[Classifier] Invalid category returned: {result.get('category')}, defaulting to 'other'")
            result["category"] = "other"

        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "low"  

        return result

    except Exception as e:
        print(f"[Classifier] Failed: {e}")
        return None