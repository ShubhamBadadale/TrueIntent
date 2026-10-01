import type { ColorSchemeName } from 'react-native';

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

const DARK_BG = '#0a1628';
const DARK_SURFACE = '#111f38';
const DARK_BORDER = '#1e3a5f';
const DARK_TEXT = '#e8eef7';
const DARK_MUTED = '#8fa3c0';

const LIGHT_BG = '#f2f5fa';
const LIGHT_SURFACE = '#ffffff';
const LIGHT_BORDER = '#d4dde8';
const LIGHT_TEXT = '#12233a';
const LIGHT_MUTED = '#5b6f89';

export interface Theme {
  background: string;
  surface: string;
  border: string;
  text: string;
  muted: string;
  primary: string;
  primaryText: string;
  danger: string;
  warning: string;
  caution: string;
  safe: string;
  /** Dedicated risk palette — identical in dark and light mode. */
  risk: Record<RiskLevel, { background: string; foreground: string }>;
}

const SHARED = {
  primary: '#1f6feb',
  primaryText: '#ffffff',
  danger: '#e5484d',
  warning: '#f5a623',
  caution: '#d9930d',
  safe: '#2f9e44',
} as const;

/** One risk palette for both themes: green / amber / red / deep red. */
const RISK_PALETTE: Record<RiskLevel, { background: string; foreground: string }> = {
  Low: { background: '#2f9e44', foreground: '#ffffff' },
  Medium: { background: '#d9930d', foreground: '#ffffff' },
  High: { background: '#e5484d', foreground: '#ffffff' },
  Critical: { background: '#8f1d22', foreground: '#ffffff' },
};

export const darkTheme: Theme = {
  background: DARK_BG,
  surface: DARK_SURFACE,
  border: DARK_BORDER,
  text: DARK_TEXT,
  muted: DARK_MUTED,
  ...SHARED,
  risk: RISK_PALETTE,
};

export const lightTheme: Theme = {
  background: LIGHT_BG,
  surface: LIGHT_SURFACE,
  border: LIGHT_BORDER,
  text: LIGHT_TEXT,
  muted: LIGHT_MUTED,
  ...SHARED,
  risk: RISK_PALETTE,
};

export function themeFor(scheme: ColorSchemeName): Theme {
  return scheme === 'light' ? lightTheme : darkTheme;
}

/** Badge colors per risk level; unavailable modules use muted, never safe. */
export function riskColors(level: RiskLevel | null, theme: Theme): {
  background: string;
  foreground: string;
} {
  if (level === null) {
    return { background: theme.border, foreground: theme.muted };
  }
  return theme.risk[level];
}

export const RISK_ORDER: readonly RiskLevel[] = ['Low', 'Medium', 'High', 'Critical'];
