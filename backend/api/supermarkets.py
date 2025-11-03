#!/usr/bin/env python3
"""
Supermarket location services
"""

import requests
from typing import List, Dict

def find_supermarkets_in_radius(lat: float, lon: float, radius_km: float) -> List[Dict]:
    """Find supermarkets within radius using Overpass API"""
    try:
        # Supermarket brands to search for
        supermarket_brands = {
            'albert heijn': 'Albert Heijn',
            'ah': 'Albert Heijn',
            'dirk': 'Dirk',
            'vomar': 'Vomar',
            'jumbo': 'Jumbo',
            'plus': 'Plus',
            'aldi': 'Aldi',
            'hoogvliet': 'Hoogvliet',
            'dekamarkt': 'Dekamarkt'
        }
        
        # Convert radius to meters
        radius_meters = radius_km * 1000
        
        # Overpass API query to find supermarkets within radius
        query = f"""
        [out:json][timeout:25];
        (
          node["shop"="supermarket"](around:{radius_meters},{lat},{lon});
          way["shop"="supermarket"](around:{radius_meters},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        
        # Use Overpass API
        overpass_url = "http://overpass-api.de/api/interpreter"
        response = requests.post(overpass_url, data=query, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            supermarkets = []
            seen_locations = set()
            
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                name = tags.get('name', '')
                brand = tags.get('brand', '').lower()
                shop = tags.get('shop', '')
                
                # Get coordinates
                if element.get('type') == 'node':
                    lat_elem = element.get('lat')
                    lon_elem = element.get('lon')
                else:
                    # For ways, calculate center from geometry
                    if 'geometry' in element:
                        coords = element['geometry']
                        if coords:
                            lats = [p.get('lat') for p in coords if 'lat' in p]
                            lons = [p.get('lon') for p in coords if 'lon' in p]
                            if lats and lons:
                                lat_elem = sum(lats) / len(lats)
                                lon_elem = sum(lons) / len(lons)
                            else:
                                continue
                    else:
                        continue
                
                if not lat_elem or not lon_elem:
                    continue
                
                # Avoid duplicates
                loc_key = (round(lat_elem, 5), round(lon_elem, 5))
                if loc_key in seen_locations:
                    continue
                
                # Check if it's one of our target supermarkets
                matched_brand = None
                if shop == 'supermarket':
                    # Check brand name
                    if brand:
                        for brand_key, brand_name in supermarket_brands.items():
                            if brand_key in brand:
                                matched_brand = brand_name
                                break
                    
                    # Check name if no brand match
                    if not matched_brand:
                        name_lower = name.lower()
                        for brand_key, brand_name in supermarket_brands.items():
                            if brand_key in name_lower:
                                if brand_key == 'ah' and 'albert heijn' not in name_lower:
                                    matched_brand = brand_name
                                    break
                                elif brand_key != 'ah':
                                    matched_brand = brand_name
                                    break
                
                if matched_brand:
                    supermarkets.append({
                        'name': name or matched_brand,
                        'brand': matched_brand,
                        'latitude': lat_elem,
                        'longitude': lon_elem
                    })
                    seen_locations.add(loc_key)
            
            return supermarkets
        
        return []
    except Exception as e:
        raise Exception(f"Error finding supermarkets: {e}")


