import * as React from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { apiBaseUrl } from '../services/api';
import { themeFor } from '../constants/theme';
import { ScreenContainer, Spacer, BodyText, Card, MutedText, PrimaryButton } from '../components/ui';
import { OfflineBanner } from '../components/ui';
import { FeatureCard, ModuleStatus } from '../components/cards';
import type { Navigate } from './navigation';
import type { BackendState } from '../hooks/useBackendHealth';
import { engineLabel } from '../hooks/useBackendHealth';

/** Home dashboard: hero, engine status, live feature cards, module chips. */
export function HomeScreen({
  navigate,
  backend,
  onRetryHealth,
  onStartScan,
}: {
  navigate: Navigate;
  backend: BackendState;
  onRetryHealth: () => void;
  onStartScan: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const online = backend.status === 'online' || backend.status === 'degraded';
  const dot =
    backend.status === 'online'
      ? theme.safe
      : backend.status === 'degraded'
        ? theme.caution
        : backend.status === 'checking'
          ? theme.muted
          : theme.danger;
  return (
    <ScreenContainer>
      <Text style={[styles.brand, { color: theme.text }]}>TrueIntent</Text>
      <Text style={[styles.subtitle, { color: theme.primary }]}>
        AI-Powered Scam &amp; Phishing Defense
      </Text>
      <Spacer height={12} />
      <View style={[styles.hero, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.heroTitle, { color: theme.text }]}>Check before you trust.</Text>
        <BodyText>
          Analyze suspicious digital content using multiple scam and phishing detection layers.
        </BodyText>
        <Spacer height={4} />
        <View style={styles.statusRow}>
          <View style={[styles.dot, { backgroundColor: dot }]} />
          <Text style={[styles.status, { color: theme.muted }]}>
            Engine {engineLabel(backend.status)}
          </Text>
        </View>
        <Spacer height={4} />
        <PrimaryButton title="Start Scan" onPress={onStartScan} />
      </View>
      <Spacer height={4} />
      {online ? null : <OfflineBanner onRetry={onRetryHealth} />}
      <FeatureCard
        title="URL Scanner"
        description="Inspect suspicious links for phishing and structural warning signs."
        badge="LIVE"
        module="Module B"
        action="Scan URL"
        onPress={() => navigate({ name: 'Url' })}
      />
      <FeatureCard
        title="Message Scanner"
        description="Detect scam language, urgency, impersonation and suspicious requests."
        badge="LIVE"
        module="Module C"
        action="Scan Message"
        onPress={() => navigate({ name: 'Message' })}
      />
      <FeatureCard
        title="Smart Scan"
        description="Combine supported signals into a unified risk assessment."
        badge="LIVE"
        module="Module D"
        action="Run Smart Scan"
        onPress={() => navigate({ name: 'Combined' })}
      />
      <FeatureCard
        title="Screenshot Scanner"
        description="Extract and analyze suspicious text from screenshots."
        badge="EXPERIMENTAL"
        module="OCR"
        action="Try Screenshot Scan"
        onPress={() => navigate({ name: 'Screenshot' })}
      />
      <Card>
        <Text style={[styles.section, { color: theme.text }]}>Detection Engine</Text>
        <ModuleStatus name="Module B" detail="URL Intelligence" status="Active" />
        <ModuleStatus name="Module C" detail="Scam Language Detection" status="Active" />
        <ModuleStatus name="Module D" detail="Risk Fusion Engine" status="Active" />
        <ModuleStatus name="OCR" detail="Screenshot Intelligence" status="Experimental" />
        <ModuleStatus name="Module A" detail="Transaction Research" status="Research" />
      </Card>
      <Spacer />
      <Card>
        <MutedText>Backend: {apiBaseUrl()}</MutedText>
        <MutedText>Status: {online ? 'reachable' : 'unreachable'}</MutedText>
      </Card>
      <View style={{ height: 8 }} />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  brand: { fontSize: 30, fontWeight: '800' },
  subtitle: { fontSize: 15, fontWeight: '700', marginTop: 2 },
  hero: { borderWidth: 1, borderRadius: 14, padding: 18, marginTop: 12 },
  heroTitle: { fontSize: 24, fontWeight: '800', marginBottom: 6 },
  statusRow: { flexDirection: 'row', alignItems: 'center' },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  status: { fontSize: 13, fontWeight: '700' },
  section: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
});
