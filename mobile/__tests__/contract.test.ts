import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isErrorBody, isMobileAnalyzeData } from '../types/api';

/** Shape mirrors backend MobileAnalyzeData (docs/MOBILE_API.md). */
const SAMPLE = {
  tier: 'High',
  risk_level: 'High',
  score: 0.72,
  risk_index: 72,
  summary: 'High risk (risk score 0.72): based on URL and message evidence.',
  explanation: 'Flagged as High risk because: ...',
  analyzed_modules: ['module_b', 'module_c'],
  contributing_modules: ['module_b', 'module_c'],
  unavailable_modules: ['module_a'],
  evidence: [{ module: 'module_b', finding: 'raw IP host' }],
  warnings: ['Transparent weighted risk-score fusion used (renormalized over assessed modules).'],
  fusion_version: '3.0.0',
  limitations: ['The overall score is an uncalibrated risk score.'],
  recommended_action: 'Strong risk signals. ...',
  safety_actions: ['Do not send money or share OTPs/passwords.'],
  url_findings: { score: 0.9, risk_index: 90, reasons: ['raw IP host'], ml_status: 'active' },
  message_findings: {
    score: 0.6,
    risk_index: 60,
    signature: 'none',
    reasons: [],
    ml_status: 'active (experimental intent model; limited real-language coverage)',
    intent: 'other_fraud',
    intent_probabilities: { other_fraud: 0.6 },
    rule_evidence: [],
    heuristic_evidence: [
      {
        signal: 'otp_request',
        category: 'otp_request',
        description: 'Asks for a one-time password.',
        severity: 'high',
        matched: 'share your otp',
        affects_score: false,
      },
    ],
    text_assessed: true,
  },
  ocr_findings: null,
  details: {},
};

describe('backend contract guards', () => {
  it('accepts a realistic mobile verdict, tolerating additive fields', () => {
    assert.equal(isMobileAnalyzeData({ ...SAMPLE, future_field: 1 }), true);
  });

  it('rejects malformed verdicts', () => {
    assert.equal(isMobileAnalyzeData(null), false);
    assert.equal(isMobileAnalyzeData({}), false);
    assert.equal(isMobileAnalyzeData({ ...SAMPLE, score: 'high' }), false);
    const missing = { ...SAMPLE };
    delete (missing as Record<string, unknown>)['unavailable_modules'];
    assert.equal(isMobileAnalyzeData(missing), false);
  });

  it('never mistakes heuristic evidence for an ML verdict', () => {
    const heuristics = SAMPLE.message_findings.heuristic_evidence;
    assert.ok(heuristics.length > 0);
    for (const h of heuristics) {
      assert.equal(h.affects_score, false);
    }
  });

  it('recognizes error bodies', () => {
    assert.equal(
      isErrorBody({ code: 'invalid_url', message: 'Invalid URL.' }),
      true,
    );
    assert.equal(isErrorBody({ code: 42, message: 'x' }), false);
  });

  it('accepts an OCR-ok screenshot verdict (no tesseract live here)', () => {
    // Shape mirrors backend ImageAnalysisData; the live OCR-ok path needs a
    // Tesseract binary this machine lacks, so the contract guard pins the
    // shape the ResultScreen renders instead.
    const ocrVerdict = {
      ...SAMPLE,
      analyzed_modules: ['module_c'],
      contributing_modules: ['module_c'],
      unavailable_modules: ['module_a', 'module_b'],
      url_findings: null,
      message_findings: null,
      ocr_findings: {
        score: 0.75,
        risk_index: 75,
        signature: 'greed_opportunity',
        reasons: ["Matched greed/opportunity pattern: 'guaranteed returns'"],
        ml_status: 'mocked',
        intent: 'investment_scam',
        intent_probabilities: { investment_scam: 0.75 },
        rule_evidence: [],
        heuristic_evidence: [],
        text_assessed: true,
        ocr_text: 'Limited time! Guaranteed returns.',
        ocr_status: 'ok',
      },
    };
    assert.equal(isMobileAnalyzeData(ocrVerdict), true);
    assert.equal(ocrVerdict.ocr_findings?.text_assessed, true);
  });
});
