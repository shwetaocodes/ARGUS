import json
import spacy
import ollama
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.entity import Entity, EntityType

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

VALID_TYPES = {e.value for e in EntityType}


_nlp_models = {
    "en": spacy.load("en_core_web_sm"),
    "zh": spacy.load("zh_core_web_sm") if spacy.util.is_package("zh_core_web_sm") else spacy.load("xx_ent_wiki_sm"),
    "ur": spacy.load("xx_ent_wiki_sm"),  
}


SPACY_LABEL_MAP = {
    "PERSON": "person",
    "PER": "person",
    "ORG": "org",
    "GPE": "location",
    "LOC": "location",
    "FAC": "location",
    "NORP": "org",  
}

NER_PROMPT = """Extract named entities from the following text (English, Urdu, or Chinese). Return entity names in their original script, do not translate. Return ONLY valid JSON.

Format:
{{"entities": [{{"name": "string", "type": "person|org|location|military_unit|weapon|topic", "confidence": "high|medium|low"}}]}}

If no entities found, return {{"entities": []}}.

Text:
{text}
"""


def extract_entities_ollama(text: str) -> list[dict] | None:
    """Primary extraction path. Returns None on failure (not an empty list — that's a valid result)."""
    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": NER_PROMPT.format(text=text[:8000])}],
            format="json",
        )
        parsed = json.loads(response["message"]["content"])
        entities = parsed.get("entities", [])
        valid = [e for e in entities if e.get("type") in VALID_TYPES and e.get("name")]
        return valid
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"[NER] Ollama extraction failed: {e}")
        return None


def extract_entities_spacy(text: str, language: str) -> list[dict]:
    """Fallback path — always returns a list, never raises."""
    nlp = _nlp_models.get(language, _nlp_models["en"])
    doc = nlp(text[:8000])

    results = []
    for ent in doc.ents:
        mapped_type = SPACY_LABEL_MAP.get(ent.label_)
        if mapped_type:
            results.append({
                "name": ent.text,
                "type": mapped_type,
                "confidence": "medium",  
            })
    return results


def extract_entities(text: str, language: str = "en") -> tuple[list[dict], str]:
    """Returns (entities, method_used). Tries Ollama first, falls back to spaCy on failure or empty result."""
    ollama_result = extract_entities_ollama(text)

    if ollama_result is not None and len(ollama_result) > 0:
        return ollama_result, "ollama"

    spacy_result = extract_entities_spacy(text, language)
    if spacy_result:
        print(f"[NER] Fell back to spaCy, found {len(spacy_result)} entities")
        return spacy_result, "spacy_fallback"

    return [], "none"


def upsert_entity(db: Session, name: str, entity_type: str) -> Entity:
    existing = db.query(Entity).filter(
        or_(Entity.name.ilike(name), Entity.aliases.any(name))
    ).first()
    if existing:
        return existing
    entity = Entity(name=name, type=EntityType(entity_type), aliases=[])
    db.add(entity)
    db.flush()
    return entity