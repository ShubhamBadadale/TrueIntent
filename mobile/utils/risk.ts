import type { RiskLevel } from '../types/api';

/** 0-1 score rendered for display; null only when the backend reports none. */
export function formatScore(score: number | null | undefined): string {
  if (typeof score !== 'number' || !Number.isFinite(score)) return '—';
  return `${Math.round(score * 100)}/100`;
}

export function formatRiskIndex(index: number | null | undefined): string {
  if (typeof index !== 'number' || !Number.isFinite(index)) return '—';
  return `${Math.max(0, Math.min(100, Math.round(index)))}`;
}

const LEVEL_LABEL: Record<RiskLevel, string> = {
  Low: 'LOW',
  Medium: 'MEDIUM',
  High: 'HIGH',
  Critical: 'CRITICAL',
};

export function levelLabel(level: RiskLevel | null | undefined): string {
  if (level === null || level === undefined) return 'NOT ANALYZED';
  return LEVEL_LABEL[level] ?? 'UNKNOWN';
}

/** Short channel names for module ids (module_b -> URL, ...). */
export function moduleLabel(module: string): string {
  switch (module) {
    case 'module_a':
      return 'Transaction benchmark (Module A)';
    case 'module_b':
      return 'Link check (Module B)';
    case 'module_c':
      return 'Message check (Module C)';
    default:
      return module;
  }
}
