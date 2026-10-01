/**
 * TypeScript mirrors of `backend/app/v1_schemas.py` and `backend/app/envelope.py`.
 * The backend is the source of truth: no ML logic lives here, these interfaces
 * only describe the wire contract. `extra='forbid'` on the server means the
 * app must tolerate (ignore) unknown additive fields, never require them.
 */

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';
export type Signature = 'fear_authority' | 'greed_opportunity' | 'none';

export interface ResponseMeta {
  request_id: string;
  api_version: string;
}

export interface ErrorBody {
  code: string;
  message: string;
  module: string | null;
  details: Record<string, unknown>;
}

export type SuccessEnvelope<T> = {
  success: true;
  data: T;
  meta: ResponseMeta;
};

export type ErrorEnvelope = {
  success: false;
  error: ErrorBody;
  meta: ResponseMeta;
};

export type Envelope<T> = SuccessEnvelope<T> | ErrorEnvelope;

export function isErrorEnvelope<T>(env: Envelope<T>): env is ErrorEnvelope {
  return env.success === false;
}

/** Stable machine-readable error codes (backend/app/errors.py::ErrorCode). */
export const ErrorCodes = {
  validationError: 'validation_error',
  invalidUrl: 'invalid_url',
  missingInput: 'missing_input',
  conflictingInput: 'conflicting_input',
  unsupportedMediaType: 'unsupported_media_type',
  payloadTooLarge: 'payload_too_large',
  unreadableImage: 'unreadable_image',
  ocrUnavailable: 'ocr_unavailable',
  messageNotAssessed: 'message_not_assessed',
  modelUnavailable: 'model_unavailable',
  artifactIncompatible: 'artifact_incompatible',
  transactionFusionDisabled: 'transaction_fusion_disabled',
  amountUnitRejected: 'amount_unit_rejected',
  internalError: 'internal_error',
} as const;

export interface UrlAnalysisData {
  score: number;
  risk_index: number;
  reasons: string[];
  ml_status: string;
}

export interface HeuristicEvidence {
  signal: string;
  category: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  matched: string;
  affects_score: boolean;
}

export interface MessageAnalysisData {
  score: number;
  risk_index: number;
  signature: Signature;
  reasons: string[];
  ml_status: string;
  intent: string | null;
  intent_probabilities: Record<string, number>;
  rule_evidence: Array<Record<string, unknown>>;
  heuristic_evidence: HeuristicEvidence[];
  text_assessed: boolean;
}

export interface ImageAnalysisData extends MessageAnalysisData {
  ocr_text: string | null;
  ocr_status: string | null;
}

export interface FusionEvidence {
  module: string;
  finding: string;
}

export interface MobileAnalyzeData {
  tier: RiskLevel;
  risk_level: RiskLevel;
  score: number;
  risk_index: number;
  summary: string;
  explanation: string;
  analyzed_modules: string[];
  contributing_modules: string[];
  unavailable_modules: string[];
  evidence: FusionEvidence[];
  warnings: string[];
  fusion_version: string;
  limitations: string[];
  recommended_action: string;
  safety_actions: string[];
  url_findings: UrlAnalysisData | null;
  message_findings: MessageAnalysisData | null;
  ocr_findings: ImageAnalysisData | null;
  details: Record<string, unknown>;
}

export interface MobileAnalyzeInput {
  url?: string;
  message?: string;
  active_call?: boolean;
}

export interface ScreenshotInput extends MobileAnalyzeInput {
  imageUri: string;
  imageMimeType: string;
  imageFileName: string;
}

/** Runtime guard: is this plausibly a MobileAnalyzeData (tolerates additives)? */
export function isMobileAnalyzeData(value: unknown): value is MobileAnalyzeData {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v['risk_level'] === 'string' &&
    typeof v['score'] === 'number' &&
    typeof v['summary'] === 'string' &&
    Array.isArray(v['analyzed_modules']) &&
    Array.isArray(v['unavailable_modules'])
  );
}

/** Runtime guard for an error envelope body. */
export function isErrorBody(value: unknown): value is ErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v['code'] === 'string' && typeof v['message'] === 'string';
}
