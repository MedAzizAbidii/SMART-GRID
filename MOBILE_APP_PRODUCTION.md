# Mobile App — Production Readiness Checklist

## Phase 1: Core Production Features ✅ IMPLEMENTED

### 1. Push Notifications (Firebase Cloud Messaging)
**Status**: ✅ **INTEGRATED**

**What's implemented:**
- FCM token generation and persistence to device
- Token refresh handler for stale token rotation
- Foreground message handling with stream broadcasting
- Background message handling when app is terminated
- Auto-subscription to `alerts` and `grid_operator` topics
- Sound + badge notifications on iOS/Android

**Backend integration required:**
```bash
# Register user FCM token on login
POST /api/auth/fcm-register
{
  "token": "eGxY2fI6SzY:..."
}

# Send alert via FCM
POST /api/alerts/notify
{
  "user_id": "admin",
  "title": "Critical Alert",
  "body": "Bus 1 frequency deviation detected",
  "data": {
    "type": "critical",
    "bus_id": 1,
    "value": 49.8
  }
}
```

### 2. Offline Support (Local SQLite Cache)
**Status**: ✅ **IMPLEMENTED**

**What's cached:**
- Grid data readings (voltage, frequency, power per bus)
- Alert history (title, body, type, timestamp)
- API responses (5-min TTL for GET endpoints)

**Functionality:**
- Auto-cache on successful API calls
- Fallback to cache when offline
- Stale data cleaned up automatically
- Cache size: ~50 MB max (configurable)

**Database schema:**
```sql
CREATE TABLE cache (
  id TEXT PRIMARY KEY,
  key TEXT UNIQUE,
  value TEXT,
  expires_at INTEGER,
  created_at INTEGER
);

CREATE TABLE alerts (
  id TEXT PRIMARY KEY,
  title TEXT,
  body TEXT,
  type TEXT,
  data TEXT,
  read INTEGER DEFAULT 0,
  timestamp INTEGER
);

CREATE TABLE grid_data (
  id TEXT PRIMARY KEY,
  bus_id INTEGER,
  voltage REAL,
  frequency REAL,
  active_power REAL,
  reactive_power REAL,
  timestamp INTEGER
);
```

### 3. Error Handling & Retry Logic
**Status**: ✅ **IMPLEMENTED**

**Features:**
- Automatic retry (up to 3 attempts with exponential backoff)
- Network error detection (timeout, connection refused, DNS)
- Auth error detection (401 → force re-login)
- Graceful error UI with user-friendly messages
- Error severity classification (critical, warning, info)

**Error recovery flow:**
```
Network failure
  ↓
Retry (500ms delay)
  ↓
Retry (1s delay)
  ↓
Retry (1.5s delay)
  ↓
Check cache
  ↓
Show error UI with "Retry" button
```

### 4. Crash Reporting (Firebase Crashlytics)
**Status**: ✅ **INTEGRATED**

**What's tracked:**
- Unhandled exceptions
- Platform crashes (iOS/Android)
- Flutter framework errors
- Network timeouts
- JSON decode failures

**Dashboard**: Firebase Console → Crashlytics tab

---

## Phase 2: Deployment Preparation

### Building for Production

#### iOS Native Build (requires macOS)
```bash
# 1. Update build number in pubspec.yaml
version: 1.0.0+2

# 2. Configure code signing (Apple Developer account required)
open ios/Runner.xcworkspace

# 3. Build release IPA
flutter build ios --release

# 4. Upload to App Store using Xcode
open ios/Runner.xcworkspace
# Go to Product → Scheme → Runner
# Product → Archive → Validate → Upload
```

#### Android Native Build
```bash
# 1. Update version in pubspec.yaml

# 2. Generate keystore (one-time)
keytool -genkey -v -keystore ~/smartgrid.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias smartgrid_key

# 3. Create signing config in android/key.properties
storeFile=../smartgrid.jks
storePassword=YOUR_PASSWORD
keyAlias=smartgrid_key
keyPassword=YOUR_PASSWORD

# 4. Build release APK/AAB
flutter build appbundle --release

# 5. Upload to Play Store via Play Console
# Go to Play Console → Release → Production → Upload AAB
```

#### Web Build (Current LAN-only)
```bash
# Build for LAN (current approach)
flutter build web --no-web-resources-cdn \
  --dart-define=API_BASE_URL=https://your-domain.com:8000

# Serve on device
cd build/web
python -m http.server 5050 --bind 0.0.0.0

# Or deploy to Firebase Hosting
firebase deploy --only hosting
```

### Configuration for Production

#### 1. Update API Base URL
```bash
flutter build [ios|apk|web] \
  --dart-define=API_BASE_URL=https://api.smartgrid.io
```

#### 2. Firebase Project Setup
- Create Firebase project at console.firebase.google.com
- Register iOS app (bundle ID: `com.smartgrid.mobile`)
- Register Android app (package: `com.smartgrid.mobile`)
- Download and install:
  - `GoogleService-Info.plist` (iOS) → `ios/Runner/`
  - `google-services.json` (Android) → `android/app/`
- Enable services:
  - Cloud Messaging (FCM)
  - Crashlytics
  - Analytics

#### 3. Backend Changes Required
```python
# In backend fastapi/routes/auth.py

@app.post("/api/auth/fcm-register")
def register_fcm_token(user: User, token: str):
    """Store user's FCM token for push notifications"""
    user.fcm_token = token
    db.save(user)
    return {"status": "registered"}

# In backend fastapi/routes/alerts.py

@app.post("/api/alerts/notify")
def send_alert(request: SendAlertRequest):
    """Send push notification via FCM"""
    import firebase_admin
    from firebase_admin import messaging
    
    message = messaging.Message(
        notification=messaging.Notification(
            title=request.title,
            body=request.body,
        ),
        data=request.data,
        topic="alerts",  # or send to specific user token
    )
    
    response = messaging.send(message)
    return {"message_id": response}
```

### Testing Checklist (Before Production Release)

**Offline Mode**
- [ ] Disable WiFi, verify app still shows cached alerts
- [ ] Force-kill app, re-open, verify cached data loads
- [ ] Make network call in offline mode, verify retry queue
- [ ] Re-enable WiFi, verify sync with backend

**Push Notifications**
- [ ] Receive notification while app is open (foreground)
- [ ] Receive notification while app is in background
- [ ] Receive notification when app is terminated
- [ ] Tap notification, verify it opens correct alert detail
- [ ] Verify FCM token persists across app restarts

**Error Handling**
- [ ] Test 401 response (should force logout)
- [ ] Test 500 response (should show retry button)
- [ ] Test timeout (should retry 3x then cache fallback)
- [ ] Test network error (should fall back to cached data)
- [ ] Verify error messages are user-friendly (not stack traces)

**Crash Reporting**
- [ ] Trigger a crash (throw uncaught exception)
- [ ] Check Firebase Crashlytics dashboard within 5 min
- [ ] Verify stack trace is readable

**Performance**
- [ ] Cold start time < 3 seconds
- [ ] Alert list refresh < 1 second
- [ ] Grid data load < 2 seconds
- [ ] No memory leaks (test with DevTools)

---

## Phase 3: App Store Deployment

### iOS App Store
**Requirements:**
- Apple Developer account ($99/year)
- Provisioning profiles
- Code signing certificate
- macOS for building

**Steps:**
1. Create app in App Store Connect
2. Set app icons, screenshots, description
3. Configure privacy, permissions
4. Upload build via Xcode → Organizer
5. Submit for review (3-5 days approval time)

**Privacy Info (required):**
- [ ] Document data collection (location, contacts, etc.)
- [ ] Privacy policy URL
- [ ] Terms of service URL

### Play Store (Android)
**Requirements:**
- Google Play Developer account ($25 one-time)
- Signing keystore
- App listing
- Privacy policy

**Steps:**
1. Create app in Play Console
2. Set app icons, screenshots, description
3. Add privacy policy link
4. Upload AAB (signed release build)
5. Roll out to 10% → 50% → 100% (monitor crashes)

### Version Management

```yaml
# pubspec.yaml
version: 1.0.0+1
# Format: MAJOR.MINOR.PATCH+BUILD_NUMBER
# Increment BUILD_NUMBER for each release
# Increment PATCH for bugfixes
# Increment MINOR for new features
# Increment MAJOR for breaking changes
```

---

## Production Monitoring

### Firebase Dashboards
- **Crashlytics**: Monitor crashes, trends, affected users
- **Analytics**: Track user engagement, feature usage
- **Performance**: Monitor app startup, screen render times

### Alert Thresholds
```
Crash Rate > 1%       → Page on-call engineer
Performance degradation > 20% → Investigate backend
Failed auth > 5%      → Check auth service
```

### On-Call Runbook
1. Check Crashlytics for new crash patterns
2. Check backend API health endpoint
3. Verify Firebase services (message delivery)
4. Review error logs in CloudWatch/DataDog
5. Rollback if necessary (`flutter build` from previous tag)

---

## Known Limitations (Current)

❌ **Not Yet Production-Ready:**
- No OAuth2/Single Sign-On
- No biometric authentication (Face ID / fingerprint)
- No end-to-end encryption
- No VPN requirement
- No device compliance checking
- Limited to 5MB cache (expandable)

**Roadmap (Future):**
- [ ] Biometric unlock after first login
- [ ] E2E encryption for sensitive grid data
- [ ] Policy engine (enforce minimum iOS/Android version)
- [ ] Device attestation (verify legitimate device)
- [ ] Audit logging to backend

---

## Support & Troubleshooting

### Common Issues

**Q: Push notifications not arriving**
- A: Check FCM topic subscription, verify backend is sending, check notification permissions in Settings

**Q: App crashes on startup**
- A: Check Firebase initialization, verify AndroidManifest.xml has correct permissions

**Q: Offline cache not working**
- A: Check SQLite permissions, verify cache TTL settings

**Q: Slow network, many retries**
- A: Increase timeout duration in api_client.dart, reduce polling frequency in ViewModels

---

## Deployment SLA

| Component | Target Availability | RPO | RTO |
|-----------|-------------------|-----|-----|
| API Backend | 99.9% | 1 min | 5 min |
| FCM | 99.99% | N/A | 30 sec |
| Mobile App | N/A (client-side) | N/A | ~5 min (rollout) |
| Database | 99.95% | 1 min | 15 min |

---

Generated: 2026-08-25
Last Updated: Phase 1 complete, ready for Phase 2
