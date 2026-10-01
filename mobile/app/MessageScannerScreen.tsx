import * as React from 'react';
import { StyleSheet, Text, TextInput, View, useColorScheme } from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { analyzeMobile } from '../services/api';
import { themeFor } from '../constants/theme';
import { DEMO_MESSAGE } from '../constants/demo';
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

/** Large text input for SMS / WhatsApp / email style content. */
export function MessageScannerScreen({
  onResult,
  onBack,
}: {
  onResult: (r: MobileAnalyzeData) => void;
  onBack: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const [message, setMessage] = React.useState('');
  const trimmed = message.trim();
  const { state, run, reset } = useAnalyze(() => analyzeMobile({ message: trimmed }));

  React.useEffect(() => {
    if (state.status === 'done') onResult(state.result);
  }, [state, onResult]);

  const paste = React.useCallback(() => {
    void Clipboard.getStringAsync()
      .then((text) => {
        if (text !== '') {
          setMessage(text);
          reset();
        }
      })
      .catch(() => undefined);
  }, [reset]);

  const loading = state.status === 'loading';
  return (
    <ScreenContainer>
      <BackHeader onBack={onBack} />
      <Text style={[styles.title, { color: theme.text }]}>Message Scanner</Text>
      <MutedText>Analyze suspicious SMS, WhatsApp or email messages.</MutedText>
      <Spacer />
      <TextInput
        accessibilityLabel="Message input"
        value={message}
        onChangeText={(value) => {
          setMessage(value);
          reset();
        }}
        placeholder={'Paste a suspicious message here...'}
        placeholderTextColor={theme.muted}
        multiline
        numberOfLines={8}
        textAlignVertical="top"
        editable={!loading}
        style={[
          styles.input,
          { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text },
        ]}
      />
      <MutedText>{trimmed.length} characters</MutedText>
      <View style={styles.row}>
        <View style={styles.rowButton}>
          <SecondaryButton title="Paste" onPress={paste} />
        </View>
        <View style={styles.rowButton}>
          <SecondaryButton
            title="Clear"
            onPress={() => {
              setMessage('');
              reset();
            }}
          />
        </View>
        <View style={styles.rowButton}>
          <SecondaryButton
            title="Use Demo Input"
            onPress={() => {
              setMessage(DEMO_MESSAGE);
              reset();
            }}
          />
        </View>
      </View>
      <PrimaryButton title="Analyze Message" onPress={run} disabled={trimmed === '' || loading} />
      {loading ? <LoadingState message="Analyzing message indicators…" /> : null}
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
    minHeight: 160,
    marginVertical: 6,
  },
  row: { flexDirection: 'row', marginHorizontal: -4 },
  rowButton: { flex: 1, marginHorizontal: 4 },
});
