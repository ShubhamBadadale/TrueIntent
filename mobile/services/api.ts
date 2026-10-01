/**
 * Centralized TrueIntent API client. Components and screens never call
 * `fetch` directly and never embed URLs: the base URL comes from
 * `constants/config.ts` (environment), timeouts follow docs/MOBILE_API.md.
 */
import {
  API_BASE_URL,
  TIMEOUT_JSON_MS,
  TIMEOUT_SCREENSHOT_MS,
} from '../constants/config';
import { isErrorBody } from '../types/api';
import type {
  Envelope,
  ErrorBody,
  MobileAnalyzeData,
  MobileAnalyzeInput,
  ScreenshotInput,
} from '../types/api';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly module: string | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(args: {
    message: string;
    status: number;
    code: string;
    module?: string | null;
    details?: Record<string, unknown>;
    requestId?: string | null;
  }) {
    super(args.message);
    this.name = 'ApiError';
    this.status = args.status;
    this.code = args.code;
    this.module = args.module ?? null;
    this.details = args.details ?? {};
    this.requestId = args.requestId ?? null;
  }

  toErrorBody(): ErrorBody {
    return {
      code: this.code,
      message: this.message,
      module: this.module,
      details: this.details,
    };
  }
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}

async function parseEnvelope<T>(response: Response): Promise<Envelope<T>> {
  let json: unknown = null;
  try {
    json = await response.json();
  } catch {
    throw new ApiError({
      message: 'The server returned an unreadable response. Please retry.',
      status: response.status,
      code: 'internal_error',
    });
  }
  const body = json as {
    success?: unknown;
    data?: unknown;
    error?: unknown;
    meta?: { request_id?: unknown };
  };
  const requestId =
    typeof body.meta?.request_id === 'string' ? body.meta.request_id : null;
  if (body.success === true) {
    return { success: true, data: body.data, meta: body.meta } as Envelope<T>;
  }
  if (isErrorBody(body.error)) {
    throw new ApiError({
      message: body.error.message,
      status: response.status,
      code: body.error.code,
      module: body.error.module,
      details:
        typeof body.error.details === 'object' && body.error.details !== null
          ? (body.error.details as Record<string, unknown>)
          : {},
      requestId,
    });
  }
  throw new ApiError({
    message: 'The request could not be completed. Please retry.',
    status: response.status,
    code: 'internal_error',
    requestId,
  });
}

async function postJson<T>(
  path: string,
  payload: Record<string, unknown>,
  timeoutMs: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const envelope = await parseEnvelope<T>(response);
    if (envelope.success === true) return envelope.data;
    throw new Error('unreachable');
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError({
        message:
          'The request timed out. Analysis (especially screenshots) can take up to a minute — please retry.',
        status: 0,
        code: 'timeout',
      });
    }
    throw new ApiError({
      message:
        'Cannot reach the TrueIntent backend. Check your connection and that the server is running, then retry.',
      status: 0,
      code: 'offline',
    });
  } finally {
    clearTimeout(timer);
  }
}

/** POST /api/v1/analyze — URL and/or message text. */
export async function analyzeMobile(
  input: MobileAnalyzeInput,
): Promise<MobileAnalyzeData> {
  const payload: Record<string, unknown> = {};
  if (input.url !== undefined && input.url.trim() !== '') payload['url'] = input.url.trim();
  if (input.message !== undefined && input.message.trim() !== '') {
    payload['message'] = input.message.trim();
  }
  if (input.active_call !== undefined) payload['active_call'] = input.active_call;
  return postJson<MobileAnalyzeData>('/api/v1/analyze', payload, TIMEOUT_JSON_MS);
}

/** POST /api/v1/analyze/screenshot — multipart with image + optional fields. */
export async function analyzeScreenshot(
  input: ScreenshotInput,
): Promise<MobileAnalyzeData> {
  const form = new FormData();
  const photo = {
    uri: input.imageUri,
    type: input.imageMimeType,
    name: input.imageFileName,
  } as unknown as Blob;
  form.append('image', photo);
  if (input.url !== undefined && input.url.trim() !== '') {
    form.append('url', input.url.trim());
  }
  if (input.message !== undefined && input.message.trim() !== '') {
    form.append('message', input.message.trim());
  }
  if (input.active_call !== undefined) {
    form.append('active_call', input.active_call ? 'true' : 'false');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_SCREENSHOT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze/screenshot`, {
      method: 'POST',
      body: form,
      signal: controller.signal,
    });
    const envelope = await parseEnvelope<MobileAnalyzeData>(response);
    if (envelope.success === true) return envelope.data;
    throw new Error('unreachable');
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError({
        message:
          'Screenshot analysis timed out. OCR can take up to a minute — please retry.',
        status: 0,
        code: 'timeout',
      });
    }
    throw new ApiError({
      message:
        'Cannot reach the TrueIntent backend. Check your connection and that the server is running, then retry.',
      status: 0,
      code: 'offline',
    });
  } finally {
    clearTimeout(timer);
  }
}

export interface HealthStatus {
  reachable: boolean;
  status?: string | undefined;
}

export type Readiness = 'online' | 'degraded' | 'offline';

/** GET /ready — component readiness. `degraded` means serving with fallbacks. */
export async function checkBackendReadiness(timeoutMs = 6000): Promise<Readiness> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}/ready`, {
      signal: controller.signal,
    });
    if (!response.ok) return 'offline';
    const json = (await response.json()) as {
      data?: { status?: unknown; degraded?: unknown };
    };
    if (json.data?.degraded === true) return 'degraded';
    return 'online';
  } catch {
    return 'offline';
  } finally {
    clearTimeout(timer);
  }
}

/** GET /health — lightweight liveness probe used by the splash screen. */
export async function checkBackendHealth(timeoutMs = 6000): Promise<HealthStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      signal: controller.signal,
    });
    if (!response.ok) return { reachable: false };
    const json = (await response.json()) as { status?: unknown };
    return { reachable: true, status: typeof json.status === 'string' ? json.status : undefined };
  } catch {
    return { reachable: false };
  } finally {
    clearTimeout(timer);
  }
}
