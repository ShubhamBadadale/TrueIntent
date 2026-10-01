/**
 * Backend URL configuration. The mobile app never hard-codes a production
 * URL in components: everything reads {@link API_BASE_URL} from here, which
 * resolves from the `EXPO_PUBLIC_API_BASE_URL` environment variable
 * (`EXPO_PUBLIC_TRUEINTENT_API_URL` is still honoured as a legacy alias).
 *
 * Point it at your machine for physical devices (e.g. `http://192.168.1.5:8000`),
 * at `http://10.0.2.2:8000` for the Android emulator, or at
 * `http://127.0.0.1:8000` / `http://localhost:8000` for iOS simulator / web.
 * See docs/MOBILE_API.md ("Development networking") for why `localhost` on a
 * physical phone means the phone itself, not your PC.
 */

// Minimal ambient typing so this file typechecks without @types/node in the
// app config (Expo injects EXPO_PUBLIC_* at bundle time).
declare const process:
  | { env?: Record<string, string | undefined> }
  | undefined;

function readEnv(name: string): string | undefined {
  try {
    if (typeof process !== 'undefined' && process?.env !== undefined) {
      return process.env[name];
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function normalizeBaseUrl(raw: string | undefined): string {
  const fallback = 'http://127.0.0.1:8000';
  if (raw === undefined || raw.trim() === '') return fallback;
  return raw.trim().replace(/\/+$/, '');
}

export const API_BASE_URL: string = normalizeBaseUrl(
  readEnv('EXPO_PUBLIC_API_BASE_URL') ?? readEnv('EXPO_PUBLIC_TRUEINTENT_API_URL'),
);

/** Client timeouts mirror docs/MOBILE_API.md (server OCR has its own bound). */
export const TIMEOUT_JSON_MS = 30_000;
export const TIMEOUT_SCREENSHOT_MS = 60_000;
/** Splash health probe budget; the app always continues past it. */
export const HEALTH_CHECK_TIMEOUT_MS = 6_000;
