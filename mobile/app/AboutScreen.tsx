import * as React from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { apiBaseUrl } from '../services/api';
import { themeFor } from '../constants/theme';
import { BackHeader } from '../components/nav';
import { Badge } from '../components/cards';
import { BodyText, Card, CardTitle, MutedText, ScreenContainer, Spacer } from '../components/ui';

function ModuleSection({
  name,
  text,
  badge,
}: {
  name: string;
  text: string;
  badge?: 'RESEARCH';
}): React.JSX.Element {
  return (
    <Card>
      <View style={styles.sectionHeader}>
        <CardTitle>{name}</CardTitle>
        {badge !== undefined ? <Badge label={badge} /> : null}
      </View>
      <BodyText>{text}</BodyText>
    </Card>
  );
}

/** Capabilities, limits, benchmark status, and privacy. */
export function AboutScreen({ onBack }: { onBack: () => void }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <ScreenContainer>
      <BackHeader onBack={onBack} />
      <Text style={[styles.title, { color: theme.text }]}>TrueIntent</Text>
      <Text style={[styles.subtitle, { color: theme.primary }]}>
        Multi-Layer AI Scam &amp; Phishing Defense System
      </Text>
      <Spacer />
      <ModuleSection
        name="Module B — URL Intelligence"
        text="Inspects link structure and phishing indicators without visiting the page, backed by a trained classifier."
      />
      <ModuleSection
        name="Module C — Scam Language Detection"
        text="Analyzes message wording with an ML intent model plus rule-based scam indicators, kept strictly separate in every result."
      />
      <ModuleSection
        name="Module D — Risk Fusion"
        text="Combines the supported signals into one unified, explainable risk assessment. Only modules that actually participated contribute."
      />
      <ModuleSection
        name="OCR — Screenshot Intelligence"
        text="Extracts text from chat screenshots for analysis. Currently experimental while extraction quality is being validated."
      />
      <Text style={[styles.sectionTitle, { color: theme.text }]}>Research Modules</Text>
      <ModuleSection
        name="Transaction Risk Research"
        text="Experimental IEEE-CIS based transaction-risk research module. Currently isolated from unified scam-risk fusion."
        badge="RESEARCH"
      />
      <Card>
        <CardTitle>Research Benchmark</CardTitle>
        <BodyText>
          The transaction research module is a benchmark, not a verdict source. It never
          feeds Smart Scan results.
        </BodyText>
      </Card>
      <Card>
        <CardTitle>Important</CardTitle>
        <BodyText>
          TrueIntent provides risk assessments and suspicious indicators. Results should
          assist user judgment rather than replace independent verification.
        </BodyText>
      </Card>
      <Card>
        <CardTitle>Privacy</CardTitle>
        <BodyText>
          The app stores nothing on this device. Everything you submit is sent to the
          configured backend for analysis — avoid submitting passwords or other secrets.
        </BodyText>
      </Card>
      <Spacer />
      <MutedText>Backend: {apiBaseUrl()}</MutedText>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: '800' },
  subtitle: { fontSize: 15, fontWeight: '700', marginTop: 2 },
  sectionTitle: { fontSize: 18, fontWeight: '800', marginTop: 10, marginBottom: 2 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
});
