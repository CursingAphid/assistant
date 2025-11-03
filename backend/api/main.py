#!/usr/bin/env python3
"""
FastAPI backend for Supermarktscanner product search
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
try:
    from .supermarktscanner_scraper import search_supermarktscanner
    from .geocoding import geocode_address
    from .supermarkets import find_supermarkets_in_radius
except ImportError:
    # Fallback for direct execution
    from supermarktscanner_scraper import search_supermarktscanner
    from geocoding import geocode_address
    from supermarkets import find_supermarkets_in_radius

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Supermarktscanner API",
    description="API for searching products on Supermarktscanner.nl",
    version="1.0.0"
)

# Add CORS middleware to allow Streamlit to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Product(BaseModel):
    title: str
    price: str
    size: str
    image: str
    supermarket: str
    on_discount: bool = False
    original_price: Optional[str] = None
    discount_action: Optional[str] = None
    discount_date: Optional[str] = None
    discount_timestamp: Optional[int] = None

class SearchResponse(BaseModel):
    keyword: str
    products: List[Product]
    count: int

class SearchRequest(BaseModel):
    keyword: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    allowed_supermarkets: Optional[List[str]] = None

class GeocodeRequest(BaseModel):
    address: str

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    address: str

class SupermarketLocation(BaseModel):
    name: str
    brand: str
    latitude: float
    longitude: float

class FindSupermarketsRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float

class FindSupermarketsResponse(BaseModel):
    supermarkets: List[SupermarketLocation]
    count: int

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Supermarktscanner API",
        "version": "1.0.0",
        "endpoints": {
            "GET /search": "Search for products by keyword",
            "POST /search": "Search for products by keyword (POST)",
            "POST /geocode": "Geocode an address to get coordinates",
            "POST /supermarkets": "Find supermarkets within a radius",
        }
    }

@app.get("/search", response_model=SearchResponse)
async def search_products(
    keyword: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None
):
    """
    Search for products on Supermarktscanner.nl
    
    Args:
        keyword: Product name or brand to search for
        latitude: Optional latitude to filter by location
        longitude: Optional longitude to filter by location
        radius_km: Optional radius in km to filter supermarkets
        
    Returns:
        List of products with title, price, size, image, and supermarket
    """
    try:
        logger.info(f"Searching for products with keyword: {keyword}")
        products = search_supermarktscanner(keyword)
        
        # Filter by location if provided
        allowed_supermarkets = None
        if latitude and longitude and radius_km:
            try:
                supermarkets = find_supermarkets_in_radius(latitude, longitude, radius_km)
                allowed_supermarkets = {s['brand'] for s in supermarkets}
                logger.info(f"Filtering by {len(allowed_supermarkets)} supermarkets in radius")
            except Exception as e:
                logger.warning(f"Could not filter by location: {e}")
        
        # Filter products by allowed supermarkets
        if allowed_supermarkets:
            products = [p for p in products if p.get('supermarket', 'Unknown') in allowed_supermarkets]
        
        # Convert to Pydantic models
        product_models = [
            Product(
                title=p.get('title', ''),
                price=p.get('price', 'N/A'),
                size=p.get('size', 'N/A'),
                image=p.get('image', 'N/A'),
                supermarket=p.get('supermarket', 'Unknown'),
                on_discount=p.get('on_discount', False),
                original_price=p.get('original_price', None),
                discount_action=p.get('discount_action', None),
                discount_date=p.get('discount_date', None),
                discount_timestamp=p.get('discount_timestamp', None)
            )
            for p in products
        ]
        
        return SearchResponse(
            keyword=keyword,
            products=product_models,
            count=len(product_models)
        )
    
    except Exception as e:
        logger.error(f"Error searching for products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=SearchResponse)
async def search_products_post(request: SearchRequest):
    """
    Search for products on Supermarktscanner.nl (POST endpoint)
    
    Args:
        request: SearchRequest with keyword and optional location filters
        
    Returns:
        List of products with title, price, size, image, and supermarket
    """
    try:
        logger.info(f"Searching for products with keyword: {request.keyword}")
        products = search_supermarktscanner(request.keyword)
        
        # Filter by location if provided
        allowed_supermarkets = request.allowed_supermarkets
        if request.latitude and request.longitude and request.radius_km:
            try:
                supermarkets = find_supermarkets_in_radius(
                    request.latitude,
                    request.longitude,
                    request.radius_km
                )
                allowed_supermarkets = {s['brand'] for s in supermarkets}
                logger.info(f"Filtering by {len(allowed_supermarkets)} supermarkets in radius")
            except Exception as e:
                logger.warning(f"Could not filter by location: {e}")
        
        # Filter products by allowed supermarkets
        if allowed_supermarkets:
            products = [p for p in products if p.get('supermarket', 'Unknown') in allowed_supermarkets]
        
        # Convert to Pydantic models
        product_models = [
            Product(
                title=p.get('title', ''),
                price=p.get('price', 'N/A'),
                size=p.get('size', 'N/A'),
                image=p.get('image', 'N/A'),
                supermarket=p.get('supermarket', 'Unknown'),
                on_discount=p.get('on_discount', False),
                original_price=p.get('original_price', None),
                discount_action=p.get('discount_action', None),
                discount_date=p.get('discount_date', None),
                discount_timestamp=p.get('discount_timestamp', None)
            )
            for p in products
        ]
        
        return SearchResponse(
            keyword=request.keyword,
            products=product_models,
            count=len(product_models)
        )
    
    except Exception as e:
        logger.error(f"Error searching for products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/geocode", response_model=GeocodeResponse)
async def geocode_location(request: GeocodeRequest):
    """
    Geocode an address to get latitude and longitude
    
    Args:
        request: GeocodeRequest with address
        
    Returns:
        GeocodeResponse with latitude, longitude, and full address
    """
    try:
        logger.info(f"Geocoding address: {request.address}")
        location = geocode_address(request.address)
        
        if not location:
            raise HTTPException(status_code=404, detail="Address not found")
        
        return GeocodeResponse(
            latitude=location['latitude'],
            longitude=location['longitude'],
            address=location['address']
        )
    
    except Exception as e:
        logger.error(f"Error geocoding address: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/supermarkets", response_model=FindSupermarketsResponse)
async def find_supermarkets(request: FindSupermarketsRequest):
    """
    Find supermarkets within a radius
    
    Args:
        request: FindSupermarketsRequest with latitude, longitude, and radius_km
        
    Returns:
        FindSupermarketsResponse with list of supermarkets
    """
    try:
        logger.info(f"Finding supermarkets within {request.radius_km}km of ({request.latitude}, {request.longitude})")
        supermarkets = find_supermarkets_in_radius(
            request.latitude,
            request.longitude,
            request.radius_km
        )
        
        # Convert to Pydantic models
        supermarket_models = [
            SupermarketLocation(
                name=s['name'],
                brand=s['brand'],
                latitude=s['latitude'],
                longitude=s['longitude']
            )
            for s in supermarkets
        ]
        
        return FindSupermarketsResponse(
            supermarkets=supermarket_models,
            count=len(supermarket_models)
        )
    
    except Exception as e:
        logger.error(f"Error finding supermarkets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

