import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { ErrorCodes } from '../types/api';
import {
  OFFLINE_MESSAGE,
  TIMEOUT_MESSAGE,
  friendlyErrorMessage,
  isRetryableCode,
} from '../utils/errors';

describe('error utils', () => {
  it('adds next steps without dropping the server message', () => {
    const message = friendlyErrorMessage({
      code: ErrorCodes.ocrUnavailable,
      message: 'OCR engine unavailable on the server.',
      module: 'module_c',
      details: {},
    });
    assert.match(message, /OCR engine unavailable/);
    assert.match(message, /Paste the message text instead/);
  });

  it('passes through messages with no known next step', () => {
    const message = friendlyErrorMessage({
      code: 'something_new',
      message: 'Custom failure.',
      module: null,
      details: {},
    });
    assert.equal(message, 'Custom failure.');
  });

  it('marks transient codes retryable only', () => {
    assert.equal(isRetryableCode(ErrorCodes.modelUnavailable), true);
    assert.equal(isRetryableCode(ErrorCodes.ocrUnavailable), true);
    assert.equal(isRetryableCode('timeout'), true);
    assert.equal(isRetryableCode('offline'), true);
    assert.equal(isRetryableCode(ErrorCodes.invalidUrl), false);
  });

  it('keeps offline/timeout copy non-empty', () => {
    assert.ok(OFFLINE_MESSAGE.length > 20);
    assert.ok(TIMEOUT_MESSAGE.length > 20);
  });
});
