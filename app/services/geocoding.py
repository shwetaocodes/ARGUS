from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

geolocator = Nominatim(user_agent="intel_platform")

def geocode_place(place_name: str) -> dict | None:
    """Returns {'lat': float, 'lon': float, 'confidence': str} or None if not found."""
    try:
        location = geolocator.geocode(place_name, timeout=10)
        if location is None:
            return None

        
        importance = location.raw.get("importance", 0)
        confidence = "high" if importance > 0.5 else "medium" if importance > 0.2 else "low"

        return {"lat": location.latitude, "lon": location.longitude, "confidence": confidence}

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"[Geocode] Failed for '{place_name}': {e}")
        return None
    finally:
        time.sleep(1)  