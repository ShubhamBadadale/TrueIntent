# Android companion: course-project call signal demo

The Kotlin app in `android/` observes cellular call state while its activity is visible, then sends
one POST to `/check-transaction` when **Check transaction** is pressed. It does not transfer money
and it does not produce a transfer-risk verdict.

## What the app can and cannot do

**Current compatibility:** the app submits the amount-only IEEE-CIS research benchmark contract,
sending `"amount_unit": "ieee_cis_source"` explicitly. An amount entered here must come from the
IEEE-CIS source dataset in its original units — **do not type an INR transfer amount**. The backend
answers with `200` and an `analysis_scope: ieee_cis_amount_only_benchmark` notice when a benchmark
artifact is trained, and with **503** explaining that the artifact is missing when it is not (which
is the default on a clean checkout). Real INR transfer assessment is disabled and a genuine call
report does not make synthetic training telemetry valid. See
[Module A correctness](MODULE_A_CORRECTNESS.md).

## Build and run

Open `android/` in Android Studio, install Android SDK platform 35 and build tools 35.0.0, and
select JDK 17 or 21. The project pins AGP 8.9.2, Kotlin 2.1.20 and Gradle 8.11.1. From `android/`:
`./gradlew assembleDebug` (Windows: `.\gradlew.bat assembleDebug`). APK:
`app/build/outputs/apk/debug/app-debug.apk`. Local SDK paths are gitignored.

For a physical phone, run the backend from the repo root:

```powershell
.\.venv\Scripts\python.exe -m backend --host 0.0.0.0 --port 8000
```

Use your computer's LAN IP in the app and the same trusted network; the emulator's host address is
`http://10.0.2.2:8000`. A physical phone's own `localhost` is the phone itself. Debug builds permit
cleartext HTTP for local demos; release builds require HTTPS. **This backend has no authentication,
so do not expose it to the public Internet.**

Tap **Enable phone call signal** and grant `READ_PHONE_STATE`. Wait for a callback, enter the
benchmark amount and transaction count, then check. Permission denial, no telephony, or an unknown
state requires explicitly selecting **Use manual demo input**; unknown is never silently sent as
`false`. Manual active-call input is disabled outside manual mode. A random installation UUID is
stored locally; no phone number, IMEI, audio or message content is collected. Permission callbacks
upload nothing.

## Payload and precedence

```json
{
  "amount": 500,
  "amount_unit": "ieee_cis_source",
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

Timestamps above are illustrative; the app generates current time at submit. The telemetry
timestamp must include a timezone and be at most 120 seconds old or 30 seconds ahead, and the two
device IDs must match, otherwise the API returns 422. An accepted phone report overrides a
conflicting manual flag; without telemetry the manual flag or default is retained.

These fields are validated **legacy metadata**. They cannot influence the benchmark score, they are
not fusion inputs, and `/check-combined` refuses a `transaction` field entirely with 422 — the same
transaction object is *not* accepted there. The `/check-transaction` response is
`{score, analysis_scope, explanation}`; the app displays the response body or the server/network
error verbatim.

## Scope and what is NOT implemented

Only `READ_PHONE_STATE` is a runtime permission. `INTERNET` is declared as a normal permission for
the requested POST. Android 31+ uses `TelephonyCallback`; earlier supported versions (26–30) use
`PhoneStateListener`. `OFFHOOK` includes dialling, active and held cellular calls. It does not prove
conversation, coercion or a scam, and arbitrary WhatsApp/Telegram VoIP calls are not covered. The
default subscription is monitored; multi-SIM behaviour has not been established. Listeners
unregister when the activity stops; on return the state starts unknown until a new callback.

No foreground/background service, overlay detection, AccessibilityService, MediaProjection,
Play Integrity, mTLS, server-side attestation, authentication, replay protection or device-history
service is implemented. Client IDs, state and time can be forged; freshness checks are input
checks, not proof of origin. Production would require authenticated HTTPS transport,
consent/privacy controls, trusted device/session binding, replay protection, a retention policy,
lifecycle and multi-SIM validation, and independently collected outcome evaluation. Broader
telemetry would need a separate justified design and platform-policy review.

## Verification status

`assembleDebug` and `lintDebug` succeeded on 2026-09-26 with zero lint errors. The APK was
compiled, **not installed on a phone**. There is no `res/` directory and no `android:icon` in
either manifest, so no launcher icon is declared.

Backend suite at the time of that build: 81 passed, 2 OCR tests skipped. The current backend suite is
**149 passed, 2 skipped** (`docs/coverage.md`), and `tests/backend/test_call_telemetry.py` plus
`tests/backend/test_module_a_contract.py` cover manual compatibility, phone precedence, stale and
future timestamps, missing timezone, device mismatch, and the benchmark/fusion separation.

**No physical-phone call, permission or lifecycle scenario has been tested.** Before demonstrating
on a phone, check idle, `OFFHOOK`, permission denial, background/resume, server unavailable and the
manual fallback. Do not claim hardware verification from the backend tests alone.

References: [CallStateListener](https://developer.android.com/reference/android/telephony/TelephonyCallback.CallStateListener),
[PhoneStateListener](https://developer.android.com/reference/android/telephony/PhoneStateListener),
[AGP 8.9 compatibility](https://developer.android.com/build/releases/agp-8-9-0-release-notes).