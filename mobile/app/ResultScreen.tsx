import * as React from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { themeFor } from '../constants/theme';
import type {
  ImageAnalysisData,
  MessageAnalysisData,
  MobileAnalyzeData,
  UrlAnalysisData,
} from '../types/api';
import {
  BodyText,
  Card,
  CardTitle,
  MutedText,
  ScreenContainer,
  SecondaryButton,
  Spacer,
} from '../components/ui';
import {
  EvidenceCard,
  ModuleStatusList,
  RiskBadge,
  SafetyChecklist,
  TechnicalDetails,
} from '../components/result';
import { RiskScoreCard } from '../components/cards';

function UrlFindings({ findings }: { findings: UrlAnalysisData }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <Card>
      <CardTitle>Link findings</CardTitle>
      {findings.reasons.length === 0 ? (
        <MutedText>No suspicious link indicators reported.</MutedText>
      ) : (
        findings.reasons.map((reason) => (
          <View key={reason} style={styles.row}>
            <Text style={[styles.bullet, { color: theme.warning }]}>•</Text>
            <Text style={[styles.rowText, { color: theme.text }]}>{reason}</Text>
          </View>
        ))
      )}
      <MutedText>Model status: {findings.ml_status || 'unknown'}</MutedText>
    </Card>
  );
}

/** Message findings with an explicit ML-vs-heuristics split. */
export function MessageFindings({
  findings,
  title,
  extractedText,
}: {
  findings: MessageAnalysisData;
  title: string;
  extractedText?: string | null;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const categories = Array.from(
    new Set(findings.heuristic_evidence.map((h) => h.category)),
  );
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      {extractedText !== undefined && extractedText !== null && extractedText !== '' ? (
        <View style={[styles.quote, { borderColor: theme.border }]}>
          <MutedText>Extracted text</MutedText>
          <BodyText>{extractedText}</BodyText>
        </View>
      ) : null}
      {findings.text_assessed ? (
        <View>
          <Text style={[styles.section, { color: theme.text }]}>ML assessment</Text>
          <BodyText>
            Signature: {findings.signature}
            {findings.intent !== null && findings.intent !== undefined
              ? ` · intent: ${findings.intent}`
              : ''}
          </BodyText>
          <MutedText>{findings.ml_status}</MutedText>
        </View>
      ) : (
        <View style={[styles.notice, { borderColor: theme.warning }]}>
          <BodyText>ML assessment unavailable for this text.</BodyText>
          <MutedText>Missing information — not a clean verdict.</MutedText>
        </View>
      )}
      <Text style={[styles.section, { color: theme.text }]}>
        Rule-based indicators (not ML verdicts)
      </Text>
      {findings.heuristic_evidence.length === 0 ? (
        <MutedText>No heuristic indicators matched.</MutedText>
      ) : (
        findings.heuristic_evidence.map((h) => (
          <View key={`${h.signal}-${h.matched}`} style={styles.row}>
            <Text style={[styles.bullet, { color: theme.primary }]}>•</Text>
            <Text style={[styles.rowText, { color: theme.text }]}>
              [{h.category} · {h.severity}] {h.matched}
            </Text>
          </View>
        ))
      )}
      {categories.length > 0 ? (
        <MutedText>Categories detected: {categories.join(', ')}</MutedText>
      ) : null}
    </Card>
  );
}

function OcrFindings({ findings }: { findings: ImageAnalysisData }): React.JSX.Element {
  return (
    <View>
      <MessageFindings
        findings={findings}
        title="Screenshot findings"
        extractedText={findings.ocr_text}
      />
      {findings.ocr_status !== null && findings.ocr_status !== 'ok' ? (
        <MutedText>OCR status: {findings.ocr_status}</MutedText>
      ) : null}
    </View>
  );
}

/** Reusable verdict screen used by every scanner. */
export function ResultScreen({
  title,
  result,
  onBack,
  onHome,
}: {
  title: string;
  result: MobileAnalyzeData;
  onBack: () => void;
  onHome: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <ScreenContainer>
      <Text style={[styles.title, { color: theme.text }]}>{title}</Text>
      <RiskBadge level={result.risk_level} />
      <BodyText>{result.summary}</BodyText>
      <Spacer />
      <RiskScoreCard score={result.score} riskIndex={result.risk_index} />
      <Spacer />
      {result.url_findings !== null && result.url_findings !== undefined ? (
        <UrlFindings findings={result.url_findings} />
      ) : null}
      {result.message_findings !== null && result.message_findings !== undefined ? (
        <MessageFindings findings={result.message_findings} title="Message findings" />
      ) : null}
      {result.ocr_findings !== null && result.ocr_findings !== undefined ? (
        <OcrFindings findings={result.ocr_findings} />
      ) : null}
      <Card>
        <CardTitle>Why this verdict</CardTitle>
        <BodyText>{result.explanation}</BodyText>
      </Card>
      {result.evidence.map((item, index) => (
        <EvidenceCard key={`${item.module}-${index}`} item={item} />
      ))}
      <ModuleStatusList
        contributing={result.contributing_modules}
        unavailable={result.unavailable_modules}
      />
      <Card>
        <CardTitle>What to do</CardTitle>
        <BodyText>{result.recommended_action}</BodyText>
      </Card>
      <SafetyChecklist actions={result.safety_actions} />
      <TechnicalDetails
        fusionVersion={result.fusion_version}
        warnings={result.warnings}
        limitations={result.limitations}
        details={result.details}
      />
      <Spacer height={4} />
      <SecondaryButton title="Back" onPress={onBack} />
      <SecondaryButton title="Home" onPress={onHome} />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '800', marginBottom: 4 },
  row: { flexDirection: 'row', alignItems: 'flex-start', marginVertical: 3, paddingRight: 8 },
  rowText: { fontSize: 14, lineHeight: 20, flex: 1, flexShrink: 1 },
  bullet: { fontSize: 18, marginRight: 8, lineHeight: 20 },
  section: { fontSize: 14, fontWeight: '700', marginTop: 10, marginBottom: 4 },
  quote: { borderLeftWidth: 3, paddingLeft: 10, marginVertical: 8 },
  notice: { borderWidth: 1, borderRadius: 8, padding: 10, marginVertical: 8 },
});
