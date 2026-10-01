import * as React from 'react';
import { StyleSheet, Text, useColorScheme } from 'react-native';
import { themeFor } from '../constants/theme';
import { ScreenContainer, Spacer, MutedText } from '../components/ui';
import { BackHeader } from '../components/nav';
import { FeatureCard } from '../components/cards';
import type { Navigate } from './navigation';

/** Scanner selection hub behind the Scan tab. */
export function ScanScreen({
  navigate,
  onBack,
}: {
  navigate: Navigate;
  onBack: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <ScreenContainer>
      <BackHeader onBack={onBack} />
      <Text style={[styles.title, { color: theme.text }]}>Scan</Text>
      <MutedText>Choose what to inspect. Results are risk assessments, not guarantees.</MutedText>
      <Spacer />
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
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '800', marginBottom: 4 },
});
