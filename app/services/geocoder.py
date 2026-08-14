import json
import requests
import ollama
from app.core.config import settings

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

GEONAMES_URL = "http://api.geonames.org/searchJSON"


def gazetteer_lookup(place_name: str, max_results: int = 5) -> list[dict]:
    """Query GeoNames gazetteer. Returns list of candidate matches, empty list if none."""
    try:
        response = requests.get(GEONAMES_URL, params={
            "q": place_name,
            "maxRows": max_results,
            "username": settings.GEONAMES_USERNAME,
            "featureClass": "P",  
        }, timeout=5)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "name": g["name"],
                "lat": float(g["lat"]),
                "lon": float(g["lng"]),
                "country": g.get("countryName", ""),
                "admin": g.get("adminName1", ""),  
                "population": g.get("population", 0),
            }
            for g in data.get("geonames", [])
        ]
    except Exception as e:
        print(f"[Geocoder] Gazetteer lookup failed for '{place_name}': {e}")
        return []


DISAMBIGUATION_PROMPT = """A place name mentioned in intelligence reporting needs disambiguation. Given the surrounding context and a list of candidate locations, pick the correct one.

Context text: "{context}"

Place name mentioned: "{place_name}"

Candidates:
{candidates}

Return ONLY valid JSON: {{"selected_index": 0, "confidence": "high|medium|low", "reasoning": "one short sentence"}}
If none of the candidates plausibly match the context, return {{"selected_index": -1, "confidence": "low", "reasoning": "..."}}.
"""


def disambiguate_with_llm(place_name: str, context: str, candidates: list[dict]) -> dict | None:
    candidates_str = "\n".join(
        f"{i}: {c['name']}, {c['admin']}, {c['country']} (population: {c['population']})"
        for i, c in enumerate(candidates)
    )
    prompt = DISAMBIGUATION_PROMPT.format(
        context=context[:1000], place_name=place_name, candidates=candidates_str
    )

    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        return json.loads(response["message"]["content"])
    except Exception as e:
        print(f"[Geocoder] Disambiguation failed: {e}")
        return None


def geocode_place(place_name: str, context: str = "") -> dict | None:
    """
    Main entry point. Returns {'lat', 'lon', 'confidence', 'method'} or None.
    """
    candidates = gazetteer_lookup(place_name)

    if len(candidates) == 0:
        return None  

    if len(candidates) == 1:
        
        c = candidates[0]
        return {"lat": c["lat"], "lon": c["lon"], "confidence": "high", "method": "gazetteer"}

    
    result = disambiguate_with_llm(place_name, context, candidates)

    if result is None or result.get("selected_index", -1) == -1:
        
        best = max(candidates, key=lambda c: c["population"])
        return {"lat": best["lat"], "lon": best["lon"], "confidence": "low", "method": "population_fallback"}

    idx = result["selected_index"]
    if 0 <= idx < len(candidates):
        chosen = candidates[idx]
        confidence = result.get("confidence", "medium")
        return {"lat": chosen["lat"], "lon": chosen["lon"], "confidence": confidence, "method": "llm_disambiguation"}

    return None