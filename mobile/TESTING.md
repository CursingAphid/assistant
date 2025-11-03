# Testing Guide for Supermarktscanner Mobile App

## Quick Start Testing

### Step 1: Start the Backend API

The mobile app needs the FastAPI backend to be running. Open a terminal:

```bash
# From project root
make run-backend

# OR manually
cd /Users/milanalbertz/Desktop/projects/n8n
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify it's running:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Step 2: Install Mobile App Dependencies

```bash
cd mobile
npm install
```

### Step 3: Configure API URL (if needed)

The app defaults to `http://localhost:8000`. This works for:
- ✅ iOS Simulator
- ✅ Android Emulator  
- ✅ Web browser

**For physical device testing**, you need to use your computer's IP address:

1. Find your local IP:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Windows
   ipconfig
   ```

2. Update `mobile/app.json`:
   ```json
   "extra": {
     "apiUrl": "http://192.168.1.XXX:8000"
   }
   ```
   Replace `XXX` with your actual IP (e.g., `192.168.1.100`)

3. Make sure your phone and computer are on the same WiFi network

### Step 4: Start the Mobile App

```bash
# From project root
make run-mobile

# OR from mobile directory
cd mobile
npm start
```

### Step 5: Choose Your Testing Method

When you run `npm start`, you'll see options:

```
› Metro waiting on exp://192.168.1.XXX:8081
› Scan the QR code above with Expo Go (Android) or the Camera app (iOS)

› Press a │ open Android
› Press i │ open iOS simulator
› Press w │ open web

› Press r │ reload app
› Press m │ toggle menu
```

#### Option A: Physical Device (Easiest)

1. Install **Expo Go** on your phone:
   - iOS: [App Store](https://apps.apple.com/app/expo-go/id982107779)
   - Android: [Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)

2. Scan the QR code:
   - **iOS**: Open Camera app → Scan QR code → Tap notification
   - **Android**: Open Expo Go app → Tap "Scan QR code"

3. Wait for app to load

#### Option B: iOS Simulator (macOS only)

1. Press `i` in the terminal
2. Wait for simulator to open and app to build
3. First time may take a few minutes

#### Option C: Android Emulator

1. Start Android Studio and launch an emulator first
2. Press `a` in the terminal
3. Wait for app to build and launch

#### Option D: Web Browser (Quick Test)

1. Press `w` in the terminal
2. Opens in browser (some features may be limited)

## Testing Checklist

### Location Setup Screen

1. **Enter Address**
   - Type: `Damrak 1, Amsterdam, Netherlands`
   - Should see input field

2. **Set Travel Distance**
   - Default: 5 km
   - Change to: 2 km (fewer results) or 10 km (more results)

3. **Save Location**
   - Tap "Save and Continue"
   - Should show loading indicator
   - Should navigate to Product Search screen
   - If error: Check backend is running and address is valid

4. **Test Invalid Address**
   - Enter: `asdfghjkl12345`
   - Should show error message

### Product Search Screen

1. **Verify Location Display**
   - Should show your address
   - Should show travel distance
   - Should show "Change location" button

2. **Search Products**
   - Enter keyword: `Knorr`
   - Tap "Search"
   - Should show loading indicator
   - Should display product cards

3. **Verify Product Cards**
   - Each card should show:
     - [ ] Product image (or placeholder)
     - [ ] Product title
     - [ ] Supermarket name with 🏪 icon
     - [ ] Price (highlighted if on discount)
     - [ ] Discount info (if applicable)
     - [ ] Product size (if available)

4. **Verify Supermarkets List**
   - Should show badges with supermarket brands
   - Should match supermarkets within your radius

5. **Verify Map**
   - Should show your location (red marker)
   - Should show radius circle
   - Should show supermarkets with colored pins
   - Each supermarket should have a different color

6. **Test Different Keywords**
   - Try: `coffee`, `milk`, `bread`, `chocolate`
   - Each search should filter products by location

7. **Test Empty Results**
   - Try: `xyz123nonexistentproduct`
   - Should show "No products found" message

8. **Change Location**
   - Tap "Change location"
   - Should return to Location Setup
   - Previous location should be cleared

### Edge Cases

1. **Very Small Radius**
   - Set radius to 0.1 km
   - Should find few or no supermarkets
   - Products should be very limited

2. **Very Large Radius**
   - Set radius to 50 km
   - Should find many supermarkets
   - Should show more products

3. **Network Issues**
   - Disconnect from WiFi
   - Try to search
   - Should show appropriate error

4. **Backend Down**
   - Stop backend (`Ctrl+C` or `make stop`)
   - Try to set location
   - Should show connection error

## Troubleshooting

### "Cannot connect to API"

**Symptoms:** App shows error when trying to geocode or search

**Solutions:**
1. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. For physical device, check IP address in `app.json`

3. Check firewall isn't blocking port 8000

4. Try using tunnel mode:
   ```bash
   npm start -- --tunnel
   ```

### App Won't Load

**Symptoms:** Expo Go shows "Unable to load" or blank screen

**Solutions:**
1. Clear Expo cache:
   ```bash
   npm start -- --clear
   ```

2. Restart Metro bundler:
   - Press `r` in terminal to reload
   - Or stop (`Ctrl+C`) and restart

3. Check network connection

### Maps Not Showing

**Symptoms:** Map shows blank or error

**Solutions:**
1. **iOS Simulator:** Maps should work by default (uses Apple Maps)

2. **Android Emulator:** May need Google Maps API key
   - Get key from [Google Cloud Console](https://console.cloud.google.com/)
   - Add to `app.json`:
     ```json
     "android": {
       "config": {
         "googleMaps": {
           "apiKey": "YOUR_API_KEY"
         }
       }
     }
     ```

3. **Web:** Maps have limited functionality, this is expected

### Build Errors

**Symptoms:** TypeScript errors or module not found

**Solutions:**
1. Reinstall dependencies:
   ```bash
   rm -rf node_modules
   npm install
   ```

2. Clear cache:
   ```bash
   npm start -- --clear
   ```

3. Check Node.js version:
   ```bash
   node --version  # Should be 18+
   ```

## Quick Test Script

Run this to verify everything works:

```bash
# Terminal 1: Start backend
make run-backend

# Terminal 2: Start mobile app
cd mobile && npm start

# Then press 'w' for web, 'i' for iOS, or 'a' for Android
```

## Expected Results

After setup, you should be able to:

1. ✅ Enter an address and set travel distance
2. ✅ See nearby supermarkets found
3. ✅ Search for products (e.g., "Knorr")
4. ✅ See products filtered by location
5. ✅ View products with images, prices, and supermarket info
6. ✅ See map with location and supermarkets
7. ✅ Change location and search again

## Next Steps

Once basic testing works:
- Test on multiple devices (iOS and Android)
- Test with different addresses and radii
- Test edge cases (no results, errors, etc.)
- Consider adding more features based on your needs

