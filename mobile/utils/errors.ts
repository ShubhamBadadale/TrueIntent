import { ErrorCodes } from '../types/api';
import type { ErrorBody } from '../types/api';

/**
 * Friendly, display-safe messages per backend error code. The server message
 * is already client-safe, but these add concrete next steps for mobile users.
 */
const NEXT_STEPS: Record<string, string> = {
  [ErrorCodes.invalidUrl]: 'Check the link for typos and try again.',
  [ErrorCodes.missingInput]: 'Add a link, some message text, or a screenshot first.',
  [ErrorCodes.conflictingInput]: 'Send one value per field and retry.',
  [ErrorCodes.unsupportedMediaType]: 'Use a PNG, JPEG, WebP or BMP screenshot.',
  [ErrorCodes.payloadTooLarge]: 'The file is too large — try a smaller screenshot.',
  [ErrorCodes.unreadableImage]: 'Pick a readable chat screenshot and retry.',
  [ErrorCodes.ocrUnavailable]:
    'Text extraction is down right now. Paste the message text instead.',
  [ErrorCodes.messageNotAssessed]:
    'The message could not be assessed, so no verdict is shown. Try again later.',
  [ErrorCodes.modelUnavailable]:
    'The analysis service is temporarily unavailable. Try again in a moment.',
  [ErrorCodes.artifactIncompatible]:
    'The analysis service needs attention. Try again in a moment.',
};

export function friendlyErrorMessage(error: ErrorBody): string {
  const hint = NEXT_STEPS[error.code];
  return hint !== undefined && hint !== '' ? `${error.message} ${hint}` : error.message;
}

export const OFFLINE_MESSAGE =
  'Cannot reach the TrueIntent backend. Check your connection and that the server is running, then retry.';

export const TIMEOUT_MESSAGE =
  'The request timed out. Analysis (especially screenshots) can take up to a minute — please retry.';

export function isRetryableCode(code: string): boolean {
  // Client-side transient failures are always worth one more tap; validation
  // mistakes (bad URL, oversized file) need corrected input instead.
  return (
    code === 'timeout' ||
    code === 'offline' ||
    code === ErrorCodes.modelUnavailable ||
    code === ErrorCodes.artifactIncompatible ||
    code === ErrorCodes.internalError ||
    code === ErrorCodes.ocrUnavailable
  );
}
