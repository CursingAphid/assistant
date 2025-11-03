# React Native Frontend Development Prompt

## Overview
Create a React Native mobile app that replicates the functionality of the Streamlit frontend for a Supermarktscanner product search application. The app should be a pure frontend that calls a FastAPI backend API - all business logic is in the API, the frontend only handles UI and API calls.

## Project Structure
Create a new React Native project (using Expo or React Native CLI) with the following structure:
```
supermarktscanner-app/
├── src/
│   ├── screens/
│   │   ├── LocationSetupScreen.tsx
│   │   ├── ProductSearchScreen.tsx
│   │   └── MapScreen.tsx
│   ├── components/
│   │   ├── ProductCard.tsx
│   │   ├── ProductList.tsx
│   │   ├── MapView.tsx
│   │   └── LocationHeader.tsx
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── context/
│   │   └── LocationContext.tsx
│   ├── utils/
│   │   └── constants.ts
│   └── App.tsx
├── package.json
└── README.md
```

## API Endpoints

The backend API is available at `http://localhost:8000` (or configurable via environment variable). All endpoints return JSON:

### 1. POST /geocode
**Request:**
```json
{
  "address": "Damrak 1, Amsterdam, Netherlands"
}
```

**Response:**
```json
{
  "latitude": 52.379189,
  "longitude": 4.900278,
  "address": "Damrak 1, Amsterdam, Netherlands"
}
```

### 2. POST /supermarkets
**Request:**
```json
{
  "latitude": 52.379189,
  "longitude": 4.900278,
  "radius_km": 5.0
}
```

**Response:**
```json
{
  "supermarkets": [
    {
      "name": "Albert Heijn Damrak",
      "brand": "Albert Heijn",
      "latitude": 52.379189,
      "longitude": 4.900278
    },
    ...
  ],
  "count": 12
}
```

### 3. GET /search
**Query Parameters:**
- `keyword` (required): Product name or brand to search
- `latitude` (optional): Filter by location
- `longitude` (optional): Filter by location
- `radius_km` (optional): Filter by radius

**Example:** `GET /search?keyword=Knorr&latitude=52.379189&longitude=4.900278&radius_km=5.0`

**Response:**
```json
{
  "keyword": "Knorr",
  "products": [
    {
      "title": "Knorr Aromat Kruiden",
      "price": "€2.99",
      "size": "100g",
      "image": "https://...",
      "supermarket": "Albert Heijn",
      "on_discount": true,
      "original_price": "€3.49",
      "discount_action": "2E GRATIS",
      "discount_date": "t/m di 04-11-2025",
      "discount_timestamp": 1733356799
    },
    ...
  ],
  "count": 25
}
```

### 4. GET /health
**Response:**
```json
{
  "status": "healthy"
}
```

## App Flow

### Screen 1: Location Setup Screen (Initial Screen)
**Purpose:** User sets their location and travel distance before accessing the main app.

**UI Elements:**
- Title: "📍 Set Your Location"
- Subtitle: "Enter your address and select how far you want to travel"
- Text input field for address (placeholder: "e.g., Damrak 1, Amsterdam, Netherlands")
- Number input/slider for travel distance (0.1 to 50.0 km, default: 5.0 km, step: 0.5)
- Primary button: "✅ Set Location"
- Loading indicator while geocoding and finding supermarkets

**Functionality:**
1. User enters address and selects radius
2. On "Set Location" button press:
   - Call `POST /geocode` with the address
   - If successful, call `POST /supermarkets` with lat/lon/radius
   - Store location data in app state/context
   - Navigate to main app screens
3. Show error message if geocoding fails

**State to Store:**
- `location`: { latitude, longitude, address }
- `radius_km`: number
- `supermarkets`: array of supermarket objects
- `location_set`: boolean

### Screen 2: Main App (Tab Navigation)

After location is set, show a tab navigator with two tabs:
1. **Product Search Tab** (default)
2. **Map Tab**

#### Header Component (shown on both tabs)
- Title: "🛒 Supermarktscanner Product Search"
- Subtitle: "📍 Location: [address] | 🚗 Max distance: [radius] km"
- Button: "✏️ Change Location" (resets to Location Setup Screen)

---

### Tab 1: Product Search Screen

**UI Elements:**
- Search input field at the top (placeholder: "Enter product keyword")
- Default value: "Knorr"
- Search button (primary style)
- Product list/scrollable view below

**Product Display:**
Products should be displayed in a scrollable list (FlatList or ScrollView with cards). Each product card should show:

1. **Product Image** (if available):
   - Fixed size: 200x200px container
   - Image should fit within container (object-fit: contain)
   - Background: #f8f9fa
   - Border: 1px solid #e0e0e0
   - Border radius: 8px
   - Padding: 10px
   - If no image, show placeholder: "No Image" in gray text

2. **Product Title**: Bold, prominent

3. **Supermarket Badge**: "🏪 [Supermarket Name]" (e.g., "🏪 Albert Heijn")

4. **Price Display** (three different states):

   **State A: Product on Discount (with price reduction):**
   - Yellow background container (#fff3cd)
   - Red "SALE" badge
   - Strikethrough original price in gray
   - Current price in bold red
   - Discount action text (e.g., "🎁 2E GRATIS") if available
   - Discount expiration date (e.g., "📅 t/m di 04-11-2025") if available

   **State B: Product with Promotion (no price discount):**
   - Regular price display: "💰 Price: [price]"
   - Blue info box with discount action text (e.g., "🎁 2E GRATIS")

   **State C: Regular Price:**
   - Simple display: "💰 Price: [price]"

5. **Size** (if not "N/A"): "📦 Size: [size]"

**Styling:**
- Card layout with shadow
- White background
- Border radius: 8px
- Padding: 15px
- Margin between cards: 20px

**Functionality:**
- On search button press or when keyword changes:
  - Call `GET /search` with keyword, latitude, longitude, radius_km
  - Display loading indicator
  - Show products in scrollable list
  - Show message if no products found
  - Show count: "Found X products for '[keyword]' in your area"

**Optional Features:**
- Pull to refresh
- Infinite scroll/pagination (if API supports it later)
- Export to CSV (share functionality)

---

### Tab 2: Map Screen

**UI Elements:**
- Header: "📍 Supermarket Map"
- Info text: "🏪 Found X supermarkets within [radius] km"
- Map view (full screen or large container)
- Scrollable list of supermarkets below map (optional)

**Map Requirements:**
- Use React Native Maps library (react-native-maps or expo-maps)
- Show user's location as a marker (red pin)
- Show radius circle (red, semi-transparent fill)
- Show supermarket markers with different colors per brand:
  - **Albert Heijn**: Red (#ff0000)
  - **Dirk**: Blue (#0000ff)
  - **Vomar**: Green (#00ff00)
  - **Jumbo**: Yellow (#ffff00)
  - **Plus**: Orange (#ff8800)
  - **Aldi**: Purple (#8800ff)
  - **Hoogvliet**: Pink (#ff00ff)
  - **Dekamarkt**: Cyan (#00ffff)

**Supermarket Markers:**
- Each supermarket should have a colored marker
- Tapping marker shows info popup with:
  - Supermarket name (bold)
  - Brand name

**Map View:**
- Center on user location
- Zoom level: appropriate to show radius (approximately 13 zoom level)
- Show radius circle overlay

**Supermarket List (below map):**
- Table/list view showing:
  - Name
  - Brand
  - Distance (calculate from user location)
- Sort by distance (optional)

**Error States:**
- If no supermarkets found: "⚠️ No supermarkets found within [radius] km radius. Try increasing your travel distance."

---

## Technical Requirements

### Dependencies
Install the following packages:
- `@react-navigation/native` and `@react-navigation/bottom-tabs` for tab navigation
- `react-native-maps` or `expo-maps` for map functionality
- `axios` or `fetch` for API calls
- `@react-native-async-storage/async-storage` for persistent storage
- `react-native-vector-icons` for icons (optional)

### State Management
Use React Context API for global state:
- Location data (latitude, longitude, address)
- Radius
- Supermarkets list
- Location setup status

### API Service Layer
Create a service file (`src/services/api.ts`) with functions:
```typescript
- geocodeAddress(address: string): Promise<GeocodeResponse>
- findSupermarkets(lat: number, lon: number, radius: number): Promise<Supermarket[]>
- searchProducts(keyword: string, lat?: number, lon?: number, radius?: number): Promise<Product[]>
- checkHealth(): Promise<boolean>
```

### TypeScript Types
Define types in `src/types/index.ts`:
```typescript
interface Location {
  latitude: number;
  longitude: number;
  address: string;
}

interface Supermarket {
  name: string;
  brand: string;
  latitude: number;
  longitude: number;
}

interface Product {
  title: string;
  price: string;
  size: string;
  image: string;
  supermarket: string;
  on_discount: boolean;
  original_price?: string;
  discount_action?: string;
  discount_date?: string;
  discount_timestamp?: number;
}
```

### Constants
In `src/utils/constants.ts`:
- API base URL (default: "http://localhost:8000", configurable via environment)
- Brand color mapping
- Default radius
- Default search keyword

### Error Handling
- Show user-friendly error messages
- Handle network errors gracefully
- Show loading states during API calls
- Handle empty states (no products, no supermarkets)

### Styling
- Use consistent color scheme
- Responsive design for different screen sizes
- Follow React Native best practices
- Use StyleSheet or styled-components
- Support dark mode (optional, but recommended)

### Performance
- Implement image caching for product images
- Use FlatList for large product lists
- Optimize map rendering
- Debounce search input (optional)

### Platform Considerations
- Works on both iOS and Android
- Handle permissions (location, if needed)
- Test on both platforms

## Environment Configuration
Create `.env` file:
```
API_URL=http://localhost:8000
```

For production, use environment-specific URLs.

## Testing Requirements
- Test all API endpoints integration
- Test location setup flow
- Test product search with location filtering
- Test map display with markers
- Test error states
- Test on both iOS and Android

## Additional Features (Nice to Have)
1. **Settings Screen:**
   - Change API URL
   - Reset location
   - Clear cache

2. **Product Details:**
   - Tap on product to see full details
   - Share product

3. **Favorites:**
   - Save favorite products
   - Save favorite locations

4. **History:**
   - Recent searches
   - Recent locations

5. **Offline Support:**
   - Cache location data
   - Cache recent searches

## UI/UX Guidelines
- Use emojis for visual elements (🛒, 📍, 🏪, 💰, etc.)
- Consistent spacing and padding
- Clear visual hierarchy
- Loading indicators for async operations
- Error messages in red
- Success messages in green
- Info messages in blue
- Warning messages in yellow

## Deliverables
1. Complete React Native app with all screens
2. Working API integration
3. Map with markers and radius circle
4. Product search with location filtering
5. Product cards with discount information
6. README with setup instructions
7. Environment configuration file

## Getting Started
1. Initialize React Native project (Expo or CLI)
2. Install dependencies
3. Create folder structure
4. Implement API service layer
5. Implement Location Context
6. Build Location Setup Screen
7. Build Product Search Screen
8. Build Map Screen
9. Add navigation
10. Test all features
11. Polish UI/UX

## Notes
- The backend API must be running at the configured URL
- All business logic is in the API - frontend only handles UI and API calls
- The app should handle network errors gracefully
- Consider using React Query or SWR for API state management (optional but recommended)
- Follow React Native best practices and performance guidelines


