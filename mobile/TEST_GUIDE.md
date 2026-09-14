# GridSentinel Mobile App - Testing Guide

## 🚀 Quick Start Testing (15 minutes)

### Step 1: Install Dependencies (2 minutes)
```bash
cd smartgrid_simulation/mobile
flutter pub get
```

**Expected Output:**
```
Running "flutter pub get" in mobile...
...
packages got (XX seconds)
```

### Step 2: Start the Backend API (30 seconds)
```bash
# In a new terminal, from project root
cd smartgrid_simulation
.venv\Scripts\python.exe api_server.py
```

**Expected Output:**
```
============================================================
SMART GRID API SERVER
============================================================
API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
Dashboard: http://127.0.0.1:8000/dashboard
WebSocket: ws://127.0.0.1:8000/ws
User Management: http://127.0.0.1:8000/api/users
============================================================
```

### Step 3: Run the Mobile App (2 minutes)
```bash
# In mobile directory
flutter run

# For iOS simulator:
# flutter run -d "iPhone 15 Pro"

# For specific Android device:
# flutter run -d <device_id>
```

**Expected Output:**
```
Multiple devices/emulators found:
1. emulator-5554 (mobile) • Android 14 (API 34)
2. iPhone 15 Pro (ios) • iOS 17.0

Choose device (or "q" to quit): 1
```

Press `1` for Android emulator or `2` for iOS simulator.

---

## ✅ Test Scenarios

### Test 1: App Startup (1 minute)
**Steps:**
1. App launches → splash screen
2. See login screen: username + password fields
3. Verify: No crashes, clean UI

**Expected Result:** ✅ Login screen visible

---

### Test 2: User Registration (2 minutes)
**Steps:**

First, register a test user via API:
```bash
curl -X POST http://127.0.0.1:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@smartgrid.local",
    "password": "TestUser@123!",
    "organization": "GridLabs"
  }'
```

**Expected Response:**
```json
{
  "id": "uuid...",
  "username": "testuser",
  "email": "test@smartgrid.local",
  "role": "viewer",
  "status": "active"
}
```

---

### Test 3: Login & Authentication (2 minutes)
**Steps in Mobile App:**
1. Enter username: `testuser`
2. Enter password: `TestUser@123!`
3. Tap "Sign in" button
4. Wait 2-3 seconds

**Expected Result:**
- ✅ Loading spinner appears
- ✅ Login succeeds → navigates to home/dashboard
- ✅ Token stored locally (in SharedPreferences)
- ✅ No error messages

**If it fails:**
```bash
# Check backend is running
curl http://127.0.0.1:8000/api/users/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "TestUser@123!"}'
```

---

### Test 4: Dashboard Real-Time Updates (2 minutes)
**After successful login:**

1. See dashboard with 14 bus cards (numbered 1-14)
2. Each card shows:
   - Bus ID
   - Voltage (220V)
   - Current (A)
   - Frequency (60 Hz)
   - Consumption (kW)
3. Watch numbers update every 500ms (2Hz refresh)

**Expected Result:**
- ✅ Numbers change smoothly every 0.5 seconds
- ✅ No lag or freezing
- ✅ "Last updated" timestamp progresses

**Debug Info** (in logs):
```
WebSocket connected to ws://127.0.0.1:8000/ws
Grid data received: 14 buses
```

---

### Test 5: WebSocket Connection (2 minutes)
**Check WebSocket is working:**

In mobile app logs (run `flutter run -v` for verbose output):
```
I/flutter ( 1234): ✓ WebSocket connected to ws://127.0.0.1:8000/ws
```

**Or manually test:**
```bash
# Install websocat if not present: cargo install websocat
# Or use Python:
python -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('ws://127.0.0.1:8000/ws') as ws:
        await ws.send('get_data')
        print(await ws.recv())
asyncio.run(test())
"
```

**Expected Output:**
```json
{
  "type": "grid_data",
  "timestamp": 1726000000.123,
  "data": [...]
}
```

---

### Test 6: Simulate Attack & Get Alert (3 minutes)
**Steps:**

1. **In a new terminal, trigger attack:**
```bash
curl -X POST http://127.0.0.1:8000/api/simulate/attack \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": 1,
    "attack_type": "FRAUD",
    "duration_seconds": 10
  }'
```

**Expected Response:**
```json
{
  "message": "Attack injected on bus 1 (FRAUD)"
}
```

2. **In mobile app:**
   - Watch bus 1 consumption spike
   - See "Alert" notification badge on Alerts tab
   - Tap Alerts tab → see anomaly with:
     - Bus ID
     - Attack type
     - Confidence score (0-100%)
     - Timestamp

3. **Backend logs:**
```
Anomaly detected: Bus 1, FRAUD, confidence 92.5%
WebSocket broadcast: 1 client(s)
```

**Expected Result:**
- ✅ Alert appears within 1 second
- ✅ Confidence score displayed
- ✅ Tap to see details

---

### Test 7: User Preferences (1 minute)
**Steps:**
1. Tap "More" tab → Settings
2. Change theme: Dark ↔ Light
3. Change language (if available)
4. Toggle notifications

**Expected Result:**
- ✅ Settings persist after app restart
- ✅ Theme changes immediately
- ✅ No crashes

---

### Test 8: Logout (30 seconds)
**Steps:**
1. More tab → Settings → Logout
2. Confirm logout

**Expected Result:**
- ✅ Returns to login screen
- ✅ Token cleared from storage
- ✅ Can log back in

---

## 🔥 Advanced Testing

### Test 9: Offline Mode (2 minutes)
**Steps:**
1. Disconnect device from WiFi/cellular
2. Still on dashboard
3. Refresh or navigate away and back

**Expected Result:**
- ✅ Shows cached data (last known values)
- ✅ "Offline" indicator appears
- ✅ No crashes, graceful degradation

**Reconnect:**
- Turn WiFi back on
- App auto-syncs within 2 seconds
- Updates resume

---

### Test 10: Performance Test (2 minutes)
**Run with profiling:**
```bash
flutter run --profile
```

**Check:**
1. Dashboard load time: **<2 seconds**
2. Alert response time: **<1 second**
3. Memory usage: **<150MB** (check Android Settings → Apps → SmartGrid)
4. Frame rate: **60 FPS** (smooth scrolling)

**View performance in DevTools:**
```bash
flutter pub global activate devtools
flutter pub global run devtools

# Open: http://localhost:9100
# Select device → Memory tab
```

---

### Test 11: Firebase Setup (5 minutes)
**Prerequisites:**
- Firebase project created
- google-services.json (Android) + GoogleService-Info.plist (iOS) in place

**Steps:**
1. Run app
2. Check Firebase initialization in logs:
```
I/flutter: ✓ Firebase Messaging authorized
I/flutter: FCM Token: <long_token_here>
I/flutter: ✓ Firebase initialized
```

3. Send test notification from Firebase Console:
   - Firebase Console → Engage → Cloud Messaging
   - Create notification
   - Title: "Test Alert"
   - Body: "Test from Firebase"
   - Select device running app
   - Send

4. In app:
   - If app open: notification appears in-app banner
   - If app in background: system notification appears
   - Tap notification → app opens

**Expected Result:**
- ✅ FCM token logged
- ✅ Test notification received
- ✅ Tapping opens correct screen

---

### Test 12: Blockchain Integration (3 minutes)
**Prerequisites:**
- Contracts deployed (see onchain/scripts/deploy.ts)
- CONTRACT_ADDRESS in lib/config/env.dart

**Steps:**
1. Trigger anomaly (Test 6)
2. Check blockchain service logs:
```
I/flutter: ✓ Blockchain connected (Chain ID: 80001)
I/flutter: Recording anomaly: BUS_001 - FRAUD
```

3. Verify on Polygonscan (if deployed to Mumbai):
   - URL: https://mumbai.polygonscan.com
   - Search for contract address
   - See `recordAnomaly` transaction

**Expected Result:**
- ✅ Chain connects successfully
- ✅ Anomaly recorded on-chain
- ✅ Transaction hash logged

---

## 🐛 Troubleshooting

### Issue: "API unreachable"
**Solution:**
```bash
# Check backend running
curl http://127.0.0.1:8000/health

# If using emulator, use host IP:
# In lib/config/env.dart:
# apiBaseUrl: 'http://10.0.2.2:8000'  # (Android)
# apiBaseUrl: 'http://127.0.0.1:8000' # (iOS)
```

### Issue: "WebSocket connection failed"
**Solution:**
```bash
# Check WebSocket port open
netstat -an | grep 8000

# Firewall blocking? Allow port 8000
```

### Issue: "Flutter pub get fails"
**Solution:**
```bash
cd mobile
rm -r pubspec.lock .dart_tool
flutter pub get --verbose
```

### Issue: "App crashes on login"
**Solution:**
```bash
# View full logs
flutter run -v 2>&1 | grep -i error

# Check SharedPreferences
# (Android: /data/data/com.smartgrid.mobile/shared_prefs/)
```

### Issue: "Firebase not initializing"
**Solution:**
- Verify google-services.json exists: `mobile/android/app/`
- Verify GoogleService-Info.plist exists: `mobile/ios/Runner/`
- Run: `flutter clean && flutter pub get`

---

## 📊 Test Checklist

Copy this checklist and mark off as you test:

```
Login & Auth:
- [ ] App launches without crash
- [ ] Login screen displays
- [ ] Can register new user (via API)
- [ ] Can login with credentials
- [ ] JWT token stored

Dashboard:
- [ ] Dashboard loads in <2 sec
- [ ] See 14 bus cards
- [ ] Numbers update every 500ms
- [ ] No lag/freezing

WebSocket:
- [ ] Connected message in logs
- [ ] Data updates real-time
- [ ] Survives app backgrounding
- [ ] Auto-reconnects on disconnect

Alerts:
- [ ] Simulated attack triggers alert
- [ ] Alert appears in <1 sec
- [ ] Confidence score displayed
- [ ] Can view alert details

Offline:
- [ ] Works without network
- [ ] Shows cached data
- [ ] Auto-syncs on reconnect

Performance:
- [ ] <150MB memory usage
- [ ] 60 FPS scrolling
- [ ] <2 sec dashboard load

Firebase:
- [ ] FCM token logged
- [ ] Test notification received
- [ ] Tapping opens correct screen

Blockchain:
- [ ] Chain connects
- [ ] Anomaly recorded on-chain
- [ ] Transaction hash logged
```

---

## 🎯 Expected Results Summary

| Test | Status | Time |
|------|--------|------|
| Startup | ✅ PASS | <3s |
| Login | ✅ PASS | <2s |
| Dashboard | ✅ PASS | <2s |
| WebSocket | ✅ PASS | Real-time |
| Attack Simulation | ✅ PASS | <1s |
| Offline Mode | ✅ PASS | Graceful |
| Performance | ✅ PASS | Smooth |
| Firebase | ✅ PASS | Configured |
| Blockchain | ✅ PASS | Connected |

---

## 🚀 Next Steps

1. ✅ Run all tests above
2. ✅ Verify production checklist
3. ✅ Prepare for App Store/Play Store submission
4. ✅ Create demo video (15-30 seconds showing login → alert)

---

**Last Updated**: 2026-08-23  
**Status**: Ready for Testing ✅
