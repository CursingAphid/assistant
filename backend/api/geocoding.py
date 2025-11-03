#!/usr/bin/env python3
"""
Geocoding and location services
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from typing import Dict, Optional

def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """Geocode an address to get latitude and longitude"""
    try:
        geolocator = Nominatim(user_agent="supermarktscanner_api")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return {
                'latitude': location.latitude,
                'longitude': location.longitude,
                'address': location.address
            }
        return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        raise Exception(f"Geocoding error: {e}")
    except Exception as e:
        raise Exception(f"Error geocoding address: {e}")


