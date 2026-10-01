import * as React from 'react';
import { StyleSheet, Text, TextInput, View, useColorScheme } from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { analyzeMobile } from '../services/api';
import { themeFor } from '../constants/theme';
import { DEMO_URL } from '../constants/demo';
import type { MobileAnalyzeData } from '../types/api';
import { useAnalyze } from '../hooks/useAnalyze';
import { BackHeader } from '../components/nav';
import {
  ErrorState,
  LoadingState,
  MutedText,
  PrimaryButton,
  ScreenContainer,
  SecondaryButton,
  Spacer,
} from '../components/ui';

/** Single-link analysis with optional clipboard paste. */
export function UrlScannerScreen({
  onResult,
  onBack,
}: {
  onResult: (r: MobileAnalyzeData) => void;
  onBack: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const [url, setUrl] = React.useState('');
  const trimmed = url.trim();
  const { state, run, reset } = useAnalyze(() => analyzeMobile({ url: trimmed }));

  React.useEffect(() => {
    if (state.status === 'done') onResult(state.result);
  }, [state, onResult]);

  const paste = React.useCallback(() => {
    void Clipboard.getStringAsync()
      .then((text) => {
        if (text !== '') setUrl(text);
      })
      .catch(() => undefined);
  }, []);

  const loading = state.status === 'loading';
  return (
    <ScreenContainer>
      <BackHeader onBack={onBack} />
      <Text style={[styles.title, { color: theme.text }]}>URL Scanner</Text>
      <MutedText>Inspect a link before opening it.</MutedText>
      <Spacer />
      <TextInput
        accessibilityLabel="URL input"
        value={url}
        onChangeText={(value) => {
          setUrl(value);
          reset();
        }}
        placeholder="https://example.com"
        placeholderTextColor={theme.muted}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        editable={!loading}
        style={[
          styles.input,
          { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text },
        ]}
      />
      <View style={styles.row}>
        <View style={styles.rowButton}>
          <SecondaryButton title="Paste" onPress={paste} />
        </View>
        <View style={styles.rowButton}>
          <SecondaryButton
            title="Clear"
            onPress={() => {
              setUrl('');
              reset();
            }}
          />
        </View>
        <View style={styles.rowButton}>
          <SecondaryButton
            title="Use Demo Input"
            onPress={() => {
              setUrl(DEMO_URL);
              reset();
            }}
          />
        </View>
      </View>
      <PrimaryButton title="Analyze URL" onPress={run} disabled={trimmed === '' || loading} />
      {loading ? <LoadingState message="Inspecting URL structure…" /> : null}
      {state.status === 'error' ? <ErrorState error={state.error} onRetry={run} /> : null}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '800', marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    marginVertical: 6,
  },
  row: { flexDirection: 'row', marginHorizontal: -4 },
  rowButton: { flex: 1, marginHorizontal: 4 },
});
