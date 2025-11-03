# Supermarktscanner Mobile App

React Native mobile app for Supermarktscanner, built with Expo.

## Prerequisites

1. **Node.js** (v18 or later)
2. **npm** or **yarn**
3. **Expo CLI** (optional, but recommended)
   ```bash
   npm install -g expo-cli
   ```

4. **For iOS development:**
   - macOS required
   - Xcode (from App Store)
   - iOS Simulator (comes with Xcode)

5. **For Android development:**
   - Android Studio
   - Android SDK
   - Android Emulator (set up through Android Studio)

6. **Physical Device (optional):**
   - Expo Go app installed from App Store (iOS) or Play Store (Android)

## Setup

1. **Install dependencies:**
   ```bash
   cd mobile
   npm install
   ```

2. **Configure API URL:**
   
   The app will try to connect to the FastAPI backend. You have a few options:
   
   **Option A: Use default localhost (for iOS Simulator/Android Emulator)**
   - Default: `http://localhost:8000`
   - This works for iOS Simulator and Android Emulator
   
   **Option B: Use your computer's IP address (for physical device)**
   - Find your local IP: `ifconfig` (macOS/Linux) or `ipconfig` (Windows)
   - Update `app.json`:
     ```json
     "extra": {
       "apiUrl": "http://192.168.1.XXX:8000"
     }
     ```
   - Replace `XXX` with your actual IP address
   
   **Option C: Use Tailscale (for remote access)**
   - Install Tailscale on both your computer and mobile device
   - Find your Tailscale IP: `tailscale ip` (on your computer)
   - Update `app.json` or environment variable:
     ```json
     "extra": {
       "apiUrl": "http://100.XXX.XXX.XXX:8000"
     }
     ```
   - Replace with your actual Tailscale IP (usually starts with 100.x.x.x)
   - **Important:** The backend must be bound to `0.0.0.0` (already configured in Makefile)
   
   **Option D: Use environment variable**
   ```bash
   export API_URL=http://192.168.1.XXX:8000
   npm start
   ```

3. **Start the FastAPI backend:**
   ```bash
   # From project root (already configured for Tailscale with --host 0.0.0.0)
   make run-backend
   # OR
   cd backend && uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   **Important for Tailscale:** The backend must bind to `0.0.0.0` (not `127.0.0.1` or `localhost`) so Tailscale can access it. This is already configured in the Makefile.
   
   The backend should be running on `http://0.0.0.0:8000` (accessible via `http://localhost:8000` locally and via Tailscale IP remotely)

## Running the App

### Option 1: Expo Go (Easiest for Testing)

1. **Install Expo Go on your phone:**
   - iOS: [App Store](https://apps.apple.com/app/expo-go/id982107779)
   - Android: [Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)

2. **Start the development server:**
   ```bash
   cd mobile
   npm start
   ```

3. **Scan the QR code:**
   - iOS: Open Camera app and scan the QR code
   - Android: Open Expo Go app and scan the QR code

4. **Troubleshooting for physical device:**
   - Make sure your phone and computer are on the same WiFi network
   - If connection fails, check your firewall settings
   - Use the `--tunnel` option if same network doesn't work:
     ```bash
     npm start -- --tunnel
     ```

### Option 2: iOS Simulator (macOS only)

1. **Start the development server:**
   ```bash
   cd mobile
   npm start
   ```

2. **Press `i` in the terminal** to open iOS Simulator

3. **Wait for the app to build and launch**

### Option 3: Android Emulator

1. **Start Android Studio and launch an emulator**

2. **Start the development server:**
   ```bash
   cd mobile
   npm start
   ```

3. **Press `a` in the terminal** to open Android Emulator

### Option 4: Web (for quick testing)

1. **Start the development server:**
   ```bash
   cd mobile
   npm start
   ```

2. **Press `w` in the terminal** to open in web browser

   Note: Some features (like maps) may be limited in web version.

## Testing Checklist

### Location Setup Screen
- [ ] Enter an address (e.g., "Damrak 1, Amsterdam, Netherlands")
- [ ] Set travel distance (e.g., 5 km)
- [ ] Click "Save and Continue"
- [ ] Verify geocoding works (address should be found)
- [ ] Verify supermarkets are found within radius

### Product Search Screen
- [ ] Verify location is displayed correctly
- [ ] Enter a search keyword (e.g., "Knorr")
- [ ] Click "Search"
- [ ] Verify products are returned
- [ ] Verify products are filtered by location (only supermarkets within radius)
- [ ] Check product cards display correctly:
  - [ ] Product image
  - [ ] Product title
  - [ ] Supermarket name
  - [ ] Price (with discount if applicable)
  - [ ] Discount information (if on sale)
  - [ ] Product size
- [ ] Verify supermarket list shows nearby stores
- [ ] Verify map displays location and supermarkets
- [ ] Test "Change location" button

### Edge Cases
- [ ] Test with invalid address (should show error)
- [ ] Test with very small radius (0.1 km) - should find few/no supermarkets
- [ ] Test with very large radius (50 km) - should find many supermarkets
- [ ] Test with product that doesn't exist (should show empty state)
- [ ] Test with empty search keyword (should show validation error)

## Troubleshooting

### "Cannot connect to API"
- **Check backend is running:** `curl http://localhost:8000/health`
- **Check API URL in app.json** matches your backend URL
- **For physical device:** Use your computer's IP address, not `localhost`
- **For Tailscale:** 
  - Verify Tailscale is running on both devices: `tailscale status`
  - Get your Tailscale IP: `tailscale ip -4`
  - Verify backend is bound to `0.0.0.0`: Check Makefile or startup command
  - Test connection from mobile device: `curl http://[TAILSCALE_IP]:8000/health`
- **Check firewall:** Make sure port 8000 is not blocked

### "Metro bundler failed to start"
- Clear cache: `npm start -- --clear`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### Maps not showing
- **iOS:** Add Google Maps API key to `app.json` (optional, uses Apple Maps by default)
- **Android:** Add Google Maps API key to `app.json` (required)
- **Web:** Maps may have limited functionality

### Build errors
- Make sure all dependencies are installed: `npm install`
- Check Node.js version: `node --version` (should be 18+)
- Clear Expo cache: `expo start -c`

## Development Tips

1. **Hot Reload:** Changes to your code will automatically reload in the app
2. **Debugging:** Use React Native Debugger or Chrome DevTools
3. **Logs:** Check terminal output for console.log statements
4. **Network:** Use React Native's Network Inspector to see API calls

## Production Build

For production builds, see [Expo's documentation](https://docs.expo.dev/build/introduction/):
- **iOS:** `eas build --platform ios`
- **Android:** `eas build --platform android`

## API Endpoints Used

The app uses these FastAPI endpoints:
- `POST /geocode` - Geocode address to coordinates
- `POST /supermarkets` - Find supermarkets within radius
- `GET /search` - Search products with location filtering

All endpoints should be available at your configured API URL.

