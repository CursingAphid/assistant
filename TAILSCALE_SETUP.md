# Tailscale Setup Guide

## Quick Setup for Supermarktscanner Mobile App

### ✅ Backend Configuration (Already Done!)

Your backend is already configured correctly:
- Makefile uses `--host 0.0.0.0` (line 22, 36)
- start_api.sh uses `--host 0.0.0.0` (line 5)
- main.py uses `host="0.0.0.0"` when run directly (line 301)

**No changes needed!** The backend will accept connections from Tailscale.

### Steps to Connect Mobile App via Tailscale

1. **Install Tailscale on Both Devices:**
   - Computer: Install from [tailscale.com](https://tailscale.com/download)
   - Mobile device: Install Tailscale app from App Store (iOS) or Play Store (Android)

2. **Connect Both Devices to Same Tailscale Network:**
   - Sign in with the same Tailscale account on both devices
   - Verify both devices are connected: `tailscale status` (on your computer)

3. **Find Your Tailscale IP:**
   ```bash
   tailscale ip -4
   ```
   This will show your Tailscale IP (usually starts with `100.x.x.x`)

4. **Start the Backend:**
   ```bash
   # From project root
   make run-backend
   ```
   
   Or manually:
   ```bash
   uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   **Important:** The `--host 0.0.0.0` flag is already included in the Makefile.

5. **Verify Backend is Accessible:**
   ```bash
   # Test locally
   curl http://localhost:8000/health
   
   # Test via Tailscale IP (from your mobile device or another computer on Tailscale)
   curl http://[YOUR_TAILSCALE_IP]:8000/health
   ```
   
   Both should return: `{"status":"healthy"}`

6. **Configure Mobile App:**
   - Update `mobile/app.json` or environment variable with your Tailscale IP:
     ```json
     "extra": {
       "apiUrl": "http://100.XXX.XXX.XXX:8000"
     }
     ```
   - Replace `100.XXX.XXX.XXX` with your actual Tailscale IP

7. **Test Connection:**
   - Start the mobile app
   - Try to set location - it should connect to the API via Tailscale

### Troubleshooting

**"Cannot connect to API" from mobile app:**
1. Verify Tailscale is running on both devices:
   ```bash
   tailscale status
   ```

2. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

3. Verify backend is bound to 0.0.0.0:
   ```bash
   # Check if process is listening on all interfaces
   lsof -i :8000
   # Should show 0.0.0.0:8000, not 127.0.0.1:8000
   ```

4. Test connection from mobile device:
   ```bash
   # From mobile device (if you have terminal access)
   curl http://[YOUR_TAILSCALE_IP]:8000/health
   ```

5. Check firewall settings:
   - Make sure port 8000 is not blocked
   - Tailscale should bypass most firewall rules, but verify

**Backend shows "Connection refused":**
- Make sure you're using `--host 0.0.0.0` (already in Makefile)
- Restart the backend after checking

**Tailscale IP not working:**
- Verify both devices are on the same Tailscale network
- Check Tailscale status: `tailscale status`
- Try pinging the Tailscale IP from mobile device

### Quick Command Reference

```bash
# Get your Tailscale IP
tailscale ip -4

# Check Tailscale status
tailscale status

# Start backend (already configured for Tailscale)
make run-backend

# Test backend health
curl http://localhost:8000/health

# Test via Tailscale IP (replace with your IP)
curl http://100.XXX.XXX.XXX:8000/health
```

### Notes

- The backend is already configured correctly - no changes needed!
- Tailscale IPs typically start with `100.x.x.x`
- You can use either IPv4 or IPv6 Tailscale IPs
- The backend will be accessible both locally (`localhost:8000`) and via Tailscale (`[TAILSCALE_IP]:8000`)


