import * as React from 'react';
import { StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { themeFor } from '../constants/theme';
import type { RiskLevel } from '../types/api';
import { formatScore } from '../utils/risk';
import { BodyText, Card, CardTitle, MutedText } from './ui';
import { RiskBadge } from './result';

export type FeatureBadge = 'LIVE' | 'PROTOTYPE' | 'EXPERIMENTAL' | 'RESEARCH';

const BADGE_COLORS: Record<FeatureBadge, { background: string; foreground: string }> = {
  LIVE: { background: '#2f9e44', foreground: '#ffffff' },
  PROTOTYPE: { background: '#d9930d', foreground: '#ffffff' },
  EXPERIMENTAL: { background: '#d9930d', foreground: '#ffffff' },
  RESEARCH: { background: '#5b6f89', foreground: '#ffffff' },
};

export function Badge({ label }: { label: FeatureBadge }): React.JSX.Element {
  const colors = BADGE_COLORS[label];
  return (
    <View style={[styles.badge, { backgroundColor: colors.background }]}>
      <Text style={[styles.badgeText, { color: colors.foreground }]}>{label}</Text>
    </View>
  );
}

/** Polished home feature card with status badge, module label and action. */
export function FeatureCard({
  title,
  description,
  badge,
  module,
  action,
  onPress,
}: {
  title: string;
  description: string;
  badge: FeatureBadge;
  module: string;
  action: string;
  onPress: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <TouchableOpacity
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
    >
      <View style={styles.cardHeader}>
        <Text style={[styles.cardTitle, { color: theme.text }]}>{title}</Text>
        <Badge label={badge} />
      </View>
      <Text style={[styles.module, { color: theme.primary }]}>{module}</Text>
      <Text style={[styles.cardHint, { color: theme.muted }]}>{description}</Text>
      <Text style={[styles.cardAction, { color: theme.primary }]}>{action} →</Text>
    </TouchableOpacity>
  );
}

/** Small status chip for a detection-engine module. */
export function ModuleStatus({
  name,
  detail,
  status,
}: {
  name: string;
  detail: string;
  status: 'Active' | 'Prototype' | 'Experimental' | 'Research';
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const dot =
    status === 'Active'
      ? theme.safe
      : status === 'Prototype' || status === 'Experimental'
        ? theme.caution
        : theme.muted;
  return (
    <View style={[styles.moduleRow, { borderColor: theme.border }]}>
      <View style={[styles.dot, { backgroundColor: dot }]} />
      <View style={styles.moduleText}>
        <Text style={[styles.moduleName, { color: theme.text }]}>{name}</Text>
        <Text style={[styles.moduleDetail, { color: theme.muted }]}>{detail}</Text>
      </View>
      <Text style={[styles.moduleState, { color: theme.muted }]}>{status}</Text>
    </View>
  );
}

/** Score display using the backend's own representation (score 0-1 + index). */
export function RiskScoreCard({
  score,
  riskIndex,
}: {
  score: number;
  riskIndex: number;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const clamped = Math.max(0, Math.min(1, score));
  const level = clamped >= 0.75 ? 'Critical' : clamped >= 0.5 ? 'High' : clamped >= 0.25 ? 'Medium' : 'Low';
  return (
    <Card>
      <CardTitle>Risk Score</CardTitle>
      <Text style={[styles.score, { color: theme.risk[level].background }]}>
        {formatScore(score)}
      </Text>
      <View style={[styles.track, { backgroundColor: theme.border }]}>
        <View
          style={[
            styles.fill,
            {
              width: `${Math.round(clamped * 100)}%`,
              backgroundColor: theme.risk[level].background,
            },
          ]}
        />
      </View>
      <MutedText>
        Backend risk score {score.toFixed(2)} · index {riskIndex}/100 (uncalibrated)
      </MutedText>
    </Card>
  );
}

/** Compact verdict header reused on the result screen. */
export function ResultSummary({
  level,
  summary,
}: {
  level: RiskLevel;
  summary: string;
}): React.JSX.Element {
  return (
    <Card>
      <RiskBadge level={level} />
      <BodyText>{summary}</BodyText>
    </Card>
  );
}

const styles = StyleSheet.create({
  badge: { borderRadius: 6, paddingVertical: 3, paddingHorizontal: 8 },
  badgeText: { fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },
  card: { borderWidth: 1, borderRadius: 12, padding: 16, marginVertical: 6 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { fontSize: 17, fontWeight: '700', flex: 1, paddingRight: 8 },
  module: { fontSize: 12, fontWeight: '700', marginTop: 2 },
  cardHint: { fontSize: 13, marginTop: 4, lineHeight: 18 },
  cardAction: { fontSize: 14, fontWeight: '700', marginTop: 8 },
  moduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    paddingVertical: 10,
  },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  moduleText: { flex: 1 },
  moduleName: { fontSize: 15, fontWeight: '700' },
  moduleDetail: { fontSize: 12, marginTop: 1 },
  moduleState: { fontSize: 12, fontWeight: '700' },
  score: { fontSize: 40, fontWeight: '800', marginVertical: 4 },
  track: { height: 10, borderRadius: 5, overflow: 'hidden', marginVertical: 8 },
  fill: { height: 10, borderRadius: 5 },
});
