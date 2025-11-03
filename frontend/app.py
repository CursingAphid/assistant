#!/usr/bin/env python3
"""
Streamlit app for Supermarktscanner product search
All logic is in the API - frontend is just for display
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
from typing import List, Dict, Optional
import time
import os
import pandas as pd
import json

# Page configuration
st.set_page_config(
    page_title="Supermarktscanner Product Search",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for product images
st.markdown("""
    <style>
    .product-image {
        width: 100%;
        max-width: 200px;
        height: 200px;
        object-fit: contain;
        margin: 0 auto;
        display: block;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .product-card {
        text-align: center;
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 20px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'location_set' not in st.session_state:
    st.session_state.location_set = False
if 'location' not in st.session_state:
    st.session_state.location = None
if 'radius_km' not in st.session_state:
    st.session_state.radius_km = 5.0
if 'supermarkets' not in st.session_state:
    st.session_state.supermarkets = []

# API helper functions (no logic, just API calls)
def get_api_url():
    """Get API URL from environment or default"""
    return os.getenv("API_URL", "http://localhost:8000")

def api_geocode(address: str) -> Optional[Dict]:
    """Call API to geocode address"""
    try:
        api_url = get_api_url()
        response = requests.post(
            f"{api_url}/geocode",
            json={"address": address},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Geocoding error: {e}")
        return None

def api_find_supermarkets(latitude: float, longitude: float, radius_km: float) -> List[Dict]:
    """Call API to find supermarkets"""
    try:
        api_url = get_api_url()
        response = requests.post(
            f"{api_url}/supermarkets",
            json={
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get('supermarkets', [])
    except Exception as e:
        st.error(f"Error finding supermarkets: {e}")
        return []

def api_search_products(keyword: str, latitude: Optional[float] = None, longitude: Optional[float] = None, radius_km: Optional[float] = None) -> List[Dict]:
    """Call API to search products"""
    try:
        api_url = get_api_url()
        params = {"keyword": keyword}
        if latitude and longitude and radius_km:
            params["latitude"] = latitude
            params["longitude"] = longitude
            params["radius_km"] = radius_km
        
        response = requests.get(
            f"{api_url}/search",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get('products', [])
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to API. Make sure the API server is running.")
        return []
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def create_map_html(lat: float, lon: float, radius_km: float, api_key: Optional[str] = None, supermarkets: List[Dict] = None):
    """Create map HTML (display only)"""
    supermarkets_json = json.dumps(supermarkets) if supermarkets else "[]"
    
    # Color mapping for each supermarket brand
    brand_colors = {
        'Albert Heijn': 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
        'Dirk': 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
        'Vomar': 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
        'Jumbo': 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
        'Plus': 'http://maps.google.com/mapfiles/ms/icons/orange-dot.png',
        'Aldi': 'http://maps.google.com/mapfiles/ms/icons/purple-dot.png',
        'Hoogvliet': 'http://maps.google.com/mapfiles/ms/icons/pink-dot.png',
        'Dekamarkt': 'http://maps.google.com/mapfiles/ms/icons/ltblue-dot.png'
    }
    
    if api_key:
        # Google Maps
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
            <meta charset="utf-8">
            <title>Supermarket Map</title>
            <style>
                html, body, #map {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
            </style>
        </head>
        <body>
            <div id="map" style="height: 500px; width: 100%;"></div>
            <script>
                function initMap() {{
                    var location = {{lat: {lat}, lng: {lon}}};
                    var map = new google.maps.Map(document.getElementById('map'), {{
                        zoom: 13,
                        center: location,
                        mapTypeId: 'roadmap'
                    }});
                    
                    // Add marker for user location
                    var marker = new google.maps.Marker({{
                        position: location,
                        map: map,
                        title: 'Your Location'
                    }});
                    
                    // Add circle for radius
                    var circle = new google.maps.Circle({{
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: '#FF0000',
                        fillOpacity: 0.35,
                        map: map,
                        center: location,
                        radius: {radius_km} * 1000
                    }});
                    
                    // Add supermarket markers
                    var brandColors = {json.dumps(brand_colors)};
                    var supermarkets = {supermarkets_json};
                    if (supermarkets && supermarkets.length > 0) {{
                        supermarkets.forEach(function(supermarket) {{
                            var brand = supermarket.brand || supermarket.name;
                            var iconUrl = brandColors[brand] || 'http://maps.google.com/mapfiles/ms/icons/green-dot.png';
                            
                            var marker = new google.maps.Marker({{
                                position: {{lat: supermarket.latitude, lng: supermarket.longitude}},
                                map: map,
                                title: supermarket.name,
                                icon: {{url: iconUrl}}
                            }});
                            marker.addListener('click', function() {{
                                var infoWindow = new google.maps.InfoWindow({{
                                    content: '<strong>' + supermarket.name + '</strong><br>Brand: ' + (supermarket.brand || 'Unknown')
                                }});
                                infoWindow.open(map, marker);
                            }});
                        }});
                    }}
                }}
            </script>
            <script async defer
                src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
            </script>
        </body>
        </html>
        """
    else:
        # OpenStreetMap with Leaflet
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body, #map {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
                #map {{
                    height: 500px;
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{lat}, {lon}], 13);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(map);
                
                // Add marker for user location
                var marker = L.marker([{lat}, {lon}]).addTo(map);
                marker.bindPopup('Your Location').openPopup();
                
                // Add circle for radius
                var circle = L.circle([{lat}, {lon}], {{
                    color: 'red',
                    fillColor: '#f03',
                    fillOpacity: 0.35,
                    radius: {radius_km} * 1000
                }}).addTo(map);
                
                // Add supermarket markers
                var brandColors = {{
                    'Albert Heijn': '#ff0000',
                    'Dirk': '#0000ff',
                    'Vomar': '#00ff00',
                    'Jumbo': '#ffff00',
                    'Plus': '#ff8800',
                    'Aldi': '#8800ff',
                    'Hoogvliet': '#ff00ff',
                    'Dekamarkt': '#00ffff'
                }};
                var supermarkets = {supermarkets_json};
                if (supermarkets && supermarkets.length > 0) {{
                    supermarkets.forEach(function(supermarket) {{
                        var brand = supermarket.brand || supermarket.name;
                        var markerColor = brandColors[brand] || '#3388ff';
                        
                        var customIcon = L.divIcon({{
                            className: 'custom-marker',
                            html: '<div style="background-color: ' + markerColor + '; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                            iconSize: [20, 20],
                            iconAnchor: [10, 10]
                        }});
                        
                        var marker = L.marker([supermarket.latitude, supermarket.longitude], {{icon: customIcon}}).addTo(map);
                        marker.bindPopup('<strong>' + supermarket.name + '</strong><br>Brand: ' + (supermarket.brand || 'Unknown'));
                    }});
                }}
            </script>
        </body>
        </html>
        """
    return html

# Main app
def main():
    # Location setup at the start
    if not st.session_state.location_set:
        st.title("📍 Set Your Location")
        st.markdown("Enter your address and select how far you want to travel")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            address_input = st.text_input(
                "Enter your address",
                placeholder="e.g., Damrak 1, Amsterdam, Netherlands",
                help="Enter a full address or location"
            )
        
        with col2:
            radius_km = st.number_input(
                "Travel distance (km)",
                min_value=0.1,
                max_value=50.0,
                value=5.0,
                step=0.5,
                help="How far you're willing to travel"
            )
        
        if address_input:
            if st.button("✅ Set Location", type="primary", use_container_width=True):
                with st.spinner("Setting up your location..."):
                    location = api_geocode(address_input)
                    
                    if location:
                        supermarkets = api_find_supermarkets(
                            location['latitude'],
                            location['longitude'],
                            radius_km
                        )
                        
                        st.session_state.location = location
                        st.session_state.radius_km = radius_km
                        st.session_state.supermarkets = supermarkets
                        st.session_state.location_set = True
                        st.rerun()
                    else:
                        st.error("❌ Could not find the address. Please try a more specific address.")
        else:
            st.info("👆 Enter your address above to get started")
        
        return
    
    # Main app after location is set
    st.title("🛒 Supermarktscanner Product Search")
    st.markdown(f"📍 Location: {st.session_state.location['address']} | 🚗 Max distance: {st.session_state.radius_km} km")
    
    # Option to change location
    if st.button("✏️ Change Location"):
        st.session_state.location_set = False
        st.rerun()
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔍 Product Search", "📍 Map"])
    
    # Sidebar
    with st.sidebar:
        st.header("Search Settings")
        keyword = st.text_input(
            "Enter product keyword",
            value="Knorr",
            help="Enter a product name or brand to search"
        )
        
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### API Settings")
        api_url = st.text_input(
            "API URL",
            value=os.getenv("API_URL", "http://localhost:8000"),
            help="URL of the FastAPI backend"
        )
        
        st.markdown("---")
        st.markdown(f"### Location Info")
        st.markdown(f"**Address:** {st.session_state.location['address']}")
        st.markdown(f"**Radius:** {st.session_state.radius_km} km")
        st.markdown(f"**Supermarkets found:** {len(st.session_state.supermarkets)}")
    
    # Tab 1: Product Search
    with tab1:
        if search_button or keyword:
            if not keyword:
                st.warning("Please enter a keyword to search")
            else:
                with st.spinner(f"Searching for '{keyword}' in nearby supermarkets..."):
                    products = api_search_products(
                        keyword,
                        st.session_state.location['latitude'],
                        st.session_state.location['longitude'],
                        st.session_state.radius_km
                    )
                
                if products:
                    st.success(f"Found {len(products)} products for '{keyword}' in your area")
                    
                    # Show table
                    st.markdown("### Product Table")
                    df = pd.DataFrame(products)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"supermarktscanner_{keyword}_{int(time.time())}.csv",
                        mime="text/csv"
                    )
                    
                    st.markdown("---")
                    
                    # Display products
                    st.markdown("### Product Results")
                    cols = st.columns(3)
                    
                    for idx, product in enumerate(products):
                        col_idx = idx % 3
                        
                        with cols[col_idx]:
                            with st.container():
                                # Display product image
                                if product.get('image') and product['image'] != 'N/A':
                                    image_html = f"""
                                    <div style="width: 200px; height: 200px; margin: 0 auto; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                                        <img src="{product['image']}" style="max-width: 100%; max-height: 100%; object-fit: contain; display: block;" alt="{product['title'][:50]}" />
                                    </div>
                                    """
                                    st.markdown(image_html, unsafe_allow_html=True)
                                else:
                                    st.markdown('<div style="width: 200px; height: 200px; background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin: 0 auto; margin-bottom: 10px; color: #6c757d;">No Image</div>', unsafe_allow_html=True)
                                
                                st.markdown(f"**{product['title']}**")
                                
                                supermarket = product.get('supermarket', 'Unknown')
                                if supermarket != 'Unknown':
                                    st.markdown(f"🏪 **{supermarket}**")
                                
                                # Display price with discount information
                                if product.get('on_discount') and product.get('original_price'):
                                    discount_action_html = ""
                                    if product.get('discount_action'):
                                        discount_action_html = f'<div style="margin-top: 5px; font-size: 0.9em; color: #856404; font-weight: bold;">🎁 {product["discount_action"]}</div>'
                                    
                                    discount_date_html = ""
                                    if product.get('discount_date'):
                                        discount_date_html = f'<div style="margin-top: 5px; font-size: 0.85em; color: #6c757d;">📅 {product["discount_date"]}</div>'
                                    
                                    st.markdown("""
                                        <div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 8px; margin: 10px 0;">
                                            <span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; font-weight: bold;">SALE</span>
                                            <div style="margin-top: 5px;">
                                                <span style="text-decoration: line-through; color: #6c757d; font-size: 0.9em;">{}</span>
                                                <span style="color: #dc3545; font-weight: bold; font-size: 1.1em; margin-left: 8px;">{}</span>
                                            </div>
                                            {}
                                            {}
                                        </div>
                                    """.format(product['original_price'], product['price'], discount_action_html, discount_date_html), unsafe_allow_html=True)
                                elif product.get('discount_action'):
                                    st.markdown(f"💰 Price: {product['price']}")
                                    st.markdown(f"""
                                        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 6px; margin: 5px 0;">
                                            <span style="color: #0c5460; font-weight: bold; font-size: 0.9em;">🎁 {product['discount_action']}</span>
                                        </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown(f"💰 Price: {product['price']}")
                                
                                if product['size'] != 'N/A':
                                    st.markdown(f"📦 Size: {product['size']}")
                                st.markdown("---")
                else:
                    st.warning(f"No products found for '{keyword}' in your area. Try a different keyword or increase your travel distance.")
        else:
            st.info("👈 Enter a keyword in the sidebar and click 'Search' to find products")
    
    # Tab 2: Map
    with tab2:
        st.header("📍 Supermarket Map")
        
        # Google Maps API key (optional)
        google_api_key = st.text_input(
            "Google Maps API Key (optional)",
            type="password",
            help="Leave empty to use OpenStreetMap (free)",
            value=os.getenv("GOOGLE_MAPS_API_KEY", "")
        )
        
        if st.session_state.supermarkets:
            st.info(f"🏪 Found {len(st.session_state.supermarkets)} supermarkets within {st.session_state.radius_km} km")
            
            # Create and display map
            map_html = create_map_html(
                st.session_state.location['latitude'],
                st.session_state.location['longitude'],
                st.session_state.radius_km,
                google_api_key if google_api_key else None,
                st.session_state.supermarkets
            )
            
            components.html(map_html, height=500)
            
            # Show list of supermarkets
            st.markdown("### 🏪 Supermarkets in Your Area")
            df_supermarkets = pd.DataFrame(st.session_state.supermarkets)
            st.dataframe(df_supermarkets, use_container_width=True, hide_index=True)
        else:
            st.warning(f"⚠️ No supermarkets found within {st.session_state.radius_km} km radius. Try increasing your travel distance.")

if __name__ == "__main__":
    main()
