# Android companion: course-project call signal demo

The Kotlin app in `android/` obtains cellular call state while its activity is
visible, then sends one POST to `/check-transaction` when Check transaction is
pressed. It does not transfer money. The web checkbox remains supported unchanged.

## Build and run

**Current compatibility:** The legacy Android request does not assert IEEE-CIS
source units and is now rejected with HTTP 422. Real INR transaction assessment
is disabled; a fresh call report does not make synthetic training telemetry valid.
The app is retained as a historical call-state demo and is not a working fraud
detector. See [Module A correctness update](MODULE_A_CORRECTNESS.md).

Open `android/` in Android Studio, install Android SDK platform 35 and build tools
35.0.0, and select JDK 17 or 21. The project pins AGP 8.9.2, Kotlin 2.1.20 and
Gradle 8.11.1. From `android/`: `./gradlew assembleDebug` (Windows: `./gradlew.bat assembleDebug`).
APK: `app/build/outputs/apk/debug/app-debug.apk`. Local SDK paths are gitignored.
For a physical phone, run the backend from the repo root:

```powershell
.\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Use your computer's LAN IP in the app and the same trusted network; emulator host
address is `http://10.0.2.2:8000`. A physical phone's localhost is the phone itself.
Debug builds permit HTTP for local demos; release builds require HTTPS. This backend
has no authentication, so do not expose it to the public Internet.

Tap Enable phone call signal and grant READ_PHONE_STATE. Wait for a callback, enter
amount and transaction count, then check. Permission denial, no telephony, or an
unknown state requires explicitly selecting Use manual demo input; unknown is not
silently sent as false. Manual active-call input is disabled outside manual mode.
A random installation UUID is stored locally; no phone number, IMEI, audio or
message content is collected. Permission callbacks do not upload anything.

## Payload and precedence

```json
{
  "amount": 500,
  "transaction_velocity": 1,
  "device_id": "installation-uuid",
  "timestamp": "2026-09-26T12:00:00Z",
  "call_telemetry": {
    "device_id": "installation-uuid",
    "is_active_call": true,
    "timestamp": "2026-09-26T12:00:00Z"
  }
}
```

Timestamps above are illustrative: use current time. The same transaction object
works under `/check-combined`. The telemetry timestamp must include timezone and
be at most 120 seconds old or 30 seconds ahead. Device IDs must match. An accepted
phone report overrides a conflicting manual flag; no telemetry means the manual
flag/default is retained. The transaction timestamp remains transaction time.
No inference feature is renamed or added. API response remains `{score}` for the
transaction endpoint; the app displays the response or server/network error.

## Scope and what is NOT implemented

Only READ_PHONE_STATE is a runtime permission. INTERNET is also declared as a normal
permission for the requested POST. Android 31+ uses TelephonyCallback; earlier
supported versions (26-30) use PhoneStateListener. OFFHOOK includes dialing, active
and held cellular calls. It does not prove conversation, coercion or a scam, and
arbitrary WhatsApp/Telegram VoIP calls are not covered. The default subscription
is monitored; multi-SIM behavior has not been established. Listeners unregister
when the activity stops; on return the state starts unknown until a new callback.

No foreground/background service, overlay detection, AccessibilityService,
MediaProjection, Play Integrity, mTLS, server-side attestation, authentication,
replay protection or device-history service is implemented. Client IDs, state and
time can be forged; freshness checks are input checks, not proof of origin.
Production would require authenticated HTTPS transport, consent/privacy controls,
trusted device/session binding, replay protection, retention policy, lifecycle and
multi-SIM validation, and independently collected outcome evaluation. Broader
telemetry would need a separate justified design and platform-policy review.
Real inference call state does not make Module A's synthetic training telemetry real.

## Verification

`assembleDebug` and `lintDebug` succeeded on 2026-09-26. Lint reported zero
errors; remaining warnings concern English-only text, the placeholder launcher
icon and backup configuration. The APK was compiled, not installed on a phone.
Backend suite: 81 passed, 2 OCR tests skipped. Frontend production build passed.

Backend tests cover manual compatibility, phone precedence, both transaction and
combined routes, stale/future timestamps, missing timezone and device mismatch.
No physical-phone call or permission/lifecycle scenario has been tested in this
session. Before demonstrating on a phone: check idle, OFFHOOK, permission denial,
background/resume, server unavailable, and manual fallback. Do not claim hardware
verification from the backend tests alone.

References: [CallStateListener](https://developer.android.com/reference/android/telephony/TelephonyCallback.CallStateListener),
[PhoneStateListener](https://developer.android.com/reference/android/telephony/PhoneStateListener),
[AGP 8.9 compatibility](https://developer.android.com/build/releases/agp-8-9-0-release-notes).
