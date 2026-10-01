import * as React from 'react';
import { StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { riskColors, themeFor } from '../constants/theme';
import { levelLabel, moduleLabel } from '../utils/risk';
import { formatScore } from '../utils/risk';
import type { FusionEvidence, RiskLevel } from '../types/api';
import { BodyText, Card, CardTitle, MutedText } from './ui';

/** LOW / MEDIUM / HIGH / CRITICAL badge (muted when nothing was analyzed). */
export function RiskBadge({ level }: { level: RiskLevel | null }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const colors = riskColors(level, theme);
  return (
    <View style={[styles.badge, { backgroundColor: colors.background }]}>
      <Text style={[styles.badgeText, { color: colors.foreground }]}>
        {levelLabel(level)}
      </Text>
    </View>
  );
}

/** 0-100 score bar. Prefer RiskScoreCard for full score display. */
export function ScoreBar({
  score,
  riskIndex,
}: {
  score: number;
  riskIndex: number;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const clamped = Math.max(0, Math.min(1, score));
  const level = clamped >= 0.75 ? 'Critical' : clamped >= 0.5 ? 'High' : clamped >= 0.25 ? 'Medium' : 'Low';
  const barColor = theme.risk[level].background;
  return (
    <View>
      <View style={[styles.track, { backgroundColor: theme.border }]}>
        <View style={[styles.fill, { width: `${Math.round(clamped * 100)}%`, backgroundColor: barColor }]} />
      </View>
      <MutedText>
        Risk score {formatScore(score)} · index {riskIndex}/100 (uncalibrated)
      </MutedText>
    </View>
  );
}

/** One fused evidence finding. */
export function EvidenceCard({ item }: { item: FusionEvidence }): React.JSX.Element {
  return (
    <Card>
      <MutedText>{moduleLabel(item.module)}</MutedText>
      <BodyText>{item.finding}</BodyText>
    </Card>
  );
}

/** Contributing vs unavailable modules. Unavailable is "not analyzed", never safe. */
export function ModuleStatusList({
  contributing,
  unavailable,
}: {
  contributing: string[];
  unavailable: string[];
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <Card>
      <CardTitle>Modules</CardTitle>
      {contributing.map((m) => (
        <View key={`in-${m}`} style={styles.row}>
          <View style={[styles.dot, { backgroundColor: theme.safe }]} />
          <Text style={[styles.rowText, { color: theme.text }]}>{moduleLabel(m)} — analyzed</Text>
        </View>
      ))}
      {unavailable.map((m) => (
        <View key={`out-${m}`} style={styles.row}>
          <View style={[styles.dot, { backgroundColor: theme.muted }]} />
          <Text style={[styles.rowText, { color: theme.muted }]}>
            {moduleLabel(m)} — not analyzed (missing information, not safe)
          </Text>
        </View>
      ))}
    </Card>
  );
}

/** Recommended safety checklist. */
export function SafetyChecklist({ actions }: { actions: string[] }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <Card>
      <CardTitle>Recommended actions</CardTitle>
      {actions.map((action) => (
        <View key={action} style={styles.row}>
          <Text style={[styles.bullet, { color: theme.primary }]}>•</Text>
          <Text style={[styles.rowText, { color: theme.text }]}>{action}</Text>
        </View>
      ))}
    </Card>
  );
}

/** Expandable technical details (fusion version, warnings, limitations). */
export function TechnicalDetails({
  fusionVersion,
  warnings,
  limitations,
  details,
}: {
  fusionVersion: string;
  warnings: string[];
  limitations: string[];
  details: Record<string, unknown>;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const [open, setOpen] = React.useState(false);
  return (
    <Card>
      <TouchableOpacity accessibilityRole="button" onPress={() => setOpen((v) => !v)}>
        <Text style={[styles.toggle, { color: theme.primary }]}>
          {open ? 'Hide technical details' : 'Show technical details'}
        </Text>
      </TouchableOpacity>
      {open ? (
        <View style={{ marginTop: 8 }}>
          <MutedText>Fusion {fusionVersion}</MutedText>
          {warnings.map((w) => (
            <Text key={w} style={[styles.small, { color: theme.muted }]}>
              Warning: {w}
            </Text>
          ))}
          {limitations.map((l) => (
            <Text key={l} style={[styles.small, { color: theme.muted }]}>
              Limitation: {l}
            </Text>
          ))}
          <Text style={[styles.small, { color: theme.muted }]}>
            Details: {JSON.stringify(details)}
          </Text>
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginVertical: 8,
  },
  badgeText: { fontSize: 20, fontWeight: '800', letterSpacing: 1 },
  track: { height: 10, borderRadius: 5, overflow: 'hidden', marginVertical: 8 },
  fill: { height: 10, borderRadius: 5 },
  row: { flexDirection: 'row', alignItems: 'flex-start', marginVertical: 4, paddingRight: 8 },
  rowText: { fontSize: 14, lineHeight: 20, flex: 1, flexShrink: 1 },
  dot: { width: 10, height: 10, borderRadius: 5, marginTop: 5, marginRight: 8 },
  bullet: { fontSize: 18, marginRight: 8, lineHeight: 20 },
  toggle: { fontSize: 14, fontWeight: '700' },
  small: { fontSize: 12, lineHeight: 17, marginTop: 4 },
});
