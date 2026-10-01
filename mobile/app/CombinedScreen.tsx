import * as React from 'react';
import { Image, StyleSheet, Switch, Text, TextInput, View, useColorScheme } from 'react-native';
import { analyzeMobile, analyzeScreenshot } from '../services/api';
import { themeFor } from '../constants/theme';
import type { MobileAnalyzeData } from '../types/api';
import { useAnalyze } from '../hooks/useAnalyze';
import { BackHeader } from '../components/nav';
import { captureImageWithCamera, pickImageFromGallery } from '../utils/image';
import type { PickedImage } from '../utils/image';
import {
  BodyText,
  ErrorState,
  LoadingState,
  MutedText,
  PrimaryButton,
  ScreenContainer,
  SecondaryButton,
  Spacer,
} from '../components/ui';

/** Smart Scan: URL + message (+ optional screenshot) fused into one verdict. */
export function CombinedScreen({
  onResult,
  onBack,
}: {
  onResult: (r: MobileAnalyzeData) => void;
  onBack: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const [url, setUrl] = React.useState('');
  const [message, setMessage] = React.useState('');
  const [picked, setPicked] = React.useState<PickedImage | null>(null);
  const [choosing, setChoosing] = React.useState(false);
  const [activeCall, setActiveCall] = React.useState(false);

  const hasEvidence = url.trim() !== '' || message.trim() !== '' || picked !== null;

  const runner = React.useCallback(() => {
    const trimmedUrl = url.trim();
    const trimmedMessage = message.trim();
    const payload = {
      ...(trimmedUrl !== '' ? { url: trimmedUrl } : {}),
      ...(trimmedMessage !== '' ? { message: trimmedMessage } : {}),
      ...(activeCall ? { active_call: true as boolean } : {}),
    };
    if (picked === null) {
      return analyzeMobile(payload);
    }
    return analyzeScreenshot({
      ...payload,
      imageUri: picked.uri,
      imageMimeType: picked.mimeType,
      imageFileName: picked.fileName,
    });
  }, [url, message, picked, activeCall]);
  const { state, run, reset } = useAnalyze(runner);

  React.useEffect(() => {
    if (state.status === 'done') onResult(state.result);
  }, [state, onResult]);

  const choose = React.useCallback(
    (mode: 'gallery' | 'camera') => {
      setChoosing(true);
      const task = mode === 'gallery' ? pickImageFromGallery() : captureImageWithCamera();
      void task
        .then((image) => {
          if (image !== null) {
            setPicked(image);
            reset();
          }
        })
        .finally(() => setChoosing(false));
    },
    [reset],
  );

  return (
    <ScreenContainer>
      <BackHeader onBack={onBack} />
      <Text style={[styles.title, { color: theme.text }]}>Smart Scan</Text>
      <MutedText>
        URL and message are optional — provide at least one. The result shows which
        modules actually participated.
      </MutedText>
      <Spacer />
      <TextInput
        accessibilityLabel="URL input"
        value={url}
        onChangeText={(value) => {
          setUrl(value);
          reset();
        }}
        placeholder="Link (optional)"
        placeholderTextColor={theme.muted}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        style={[
          styles.input,
          { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text },
        ]}
      />
      <TextInput
        accessibilityLabel="Message input"
        value={message}
        onChangeText={(value) => {
          setMessage(value);
          reset();
        }}
        placeholder="Message text (optional)"
        placeholderTextColor={theme.muted}
        multiline
        numberOfLines={5}
        textAlignVertical="top"
        style={[
          styles.input,
          styles.tall,
          { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text },
        ]}
      />
      <SecondaryButton
        title={picked !== null ? 'Change screenshot' : choosing ? 'Opening…' : 'Attach screenshot (optional)'}
        onPress={() => choose('gallery')}
      />
      {picked !== null ? (
        <Image source={{ uri: picked.uri }} style={styles.preview} resizeMode="contain" />
      ) : null}
      <View style={styles.switchRow}>
        <Switch value={activeCall} onValueChange={setActiveCall} />
        <BodyText> I am on a call about this right now (unverified, self-reported)</BodyText>
      </View>
      <PrimaryButton title="Run Smart Scan" onPress={run} disabled={!hasEvidence} />
      {state.status === 'loading' ? <LoadingState message="Combining security signals…" /> : null}
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
  tall: { minHeight: 120 },
  preview: { width: '100%', height: 180, borderRadius: 10, marginVertical: 6 },
  switchRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 6, paddingRight: 12 },
});
