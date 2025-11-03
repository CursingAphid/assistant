# API Reference - Quick Reference

## Base URL
`http://localhost:8000` (configurable via environment variable)

## Endpoints

### 1. Health Check
```
GET /health
Response: { "status": "healthy" }
```

### 2. Geocode Address
```
POST /geocode
Body: { "address": "string" }
Response: {
  "latitude": number,
  "longitude": number,
  "address": "string"
}
```

### 3. Find Supermarkets
```
POST /supermarkets
Body: {
  "latitude": number,
  "longitude": number,
  "radius_km": number
}
Response: {
  "supermarkets": [
    {
      "name": "string",
      "brand": "string",
      "latitude": number,
      "longitude": number
    }
  ],
  "count": number
}
```

### 4. Search Products
```
GET /search?keyword=string&latitude=number&longitude=number&radius_km=number
Response: {
  "keyword": "string",
  "products": [
    {
      "title": "string",
      "price": "string",
      "size": "string",
      "image": "string",
      "supermarket": "string",
      "on_discount": boolean,
      "original_price": "string" (optional),
      "discount_action": "string" (optional),
      "discount_date": "string" (optional),
      "discount_timestamp": number (optional)
    }
  ],
  "count": number
}
```

## Brand Colors for Map Markers
- Albert Heijn: Red (#ff0000)
- Dirk: Blue (#0000ff)
- Vomar: Green (#00ff00)
- Jumbo: Yellow (#ffff00)
- Plus: Orange (#ff8800)
- Aldi: Purple (#8800ff)
- Hoogvliet: Pink (#ff00ff)
- Dekamarkt: Cyan (#00ffff)

