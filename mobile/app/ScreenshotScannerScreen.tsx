import * as React from 'react';
import { Image, StyleSheet, Text, TextInput, useColorScheme } from 'react-native';
import { analyzeScreenshot } from '../services/api';
import { themeFor } from '../constants/theme';
import type { MobileAnalyzeData } from '../types/api';
import { useAnalyze } from '../hooks/useAnalyze';
import { BackHeader } from '../components/nav';
import { captureImageWithCamera, pickImageFromGallery } from '../utils/image';
import type { PickedImage } from '../utils/image';
import {
  BodyText,
  Card,
  CardTitle,
  ErrorState,
  LoadingState,
  MutedText,
  PrimaryButton,
  ScreenContainer,
  SecondaryButton,
  Spacer,
} from '../components/ui';

/** Gallery / camera screenshot upload with optional link + message context. */
export function ScreenshotScannerScreen({
  onResult,
  onBack,
}: {
  onResult: (r: MobileAnalyzeData) => void;
  onBack: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const [picked, setPicked] = React.useState<PickedImage | null>(null);
  const [choosing, setChoosing] = React.useState(false);
  const [url, setUrl] = React.useState('');
  const [message, setMessage] = React.useState('');

  const runner = React.useCallback(() => {
    if (picked === null) {
      return Promise.reject(new Error('unreachable'));
    }
    const trimmedUrl = url.trim();
    const trimmedMessage = message.trim();
    return analyzeScreenshot({
      imageUri: picked.uri,
      imageMimeType: picked.mimeType,
      imageFileName: picked.fileName,
      ...(trimmedUrl !== '' ? { url: trimmedUrl } : {}),
      ...(trimmedMessage !== '' ? { message: trimmedMessage } : {}),
    });
  }, [picked, url, message]);
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
      <Text style={[styles.title, { color: theme.text }]}>Screenshot Scanner</Text>
      <MutedText>Analyze suspicious text from screenshots.</MutedText>
      <Spacer />
      <Card>
        <CardTitle>Experimental Feature</CardTitle>
        <BodyText>
          Screenshot intelligence is currently an experimental feature. Screenshot analysis
          is being validated — results may be limited.
        </BodyText>
      </Card>
      <Spacer />
      <SecondaryButton
        title={choosing ? 'Opening…' : 'Choose from gallery'}
        onPress={() => choose('gallery')}
      />
      <SecondaryButton
        title={choosing ? 'Opening…' : 'Take a photo'}
        onPress={() => choose('camera')}
      />
      {picked !== null ? (
        <Image source={{ uri: picked.uri }} style={styles.preview} resizeMode="contain" />
      ) : (
        <MutedText>No image selected yet.</MutedText>
      )}
      <Spacer />
      <TextInput
        accessibilityLabel="Optional URL"
        value={url}
        onChangeText={(value) => {
          setUrl(value);
          reset();
        }}
        placeholder="Optional related link"
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
        accessibilityLabel="Optional message"
        value={message}
        onChangeText={(value) => {
          setMessage(value);
          reset();
        }}
        placeholder="Optional related message text"
        placeholderTextColor={theme.muted}
        multiline
        style={[
          styles.input,
          { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text },
        ]}
      />
      <PrimaryButton title="Analyze screenshot" onPress={run} disabled={picked === null} />
      {state.status === 'loading' ? <LoadingState message="Uploading & extracting text…" /> : null}
      {state.status === 'error' ? <ErrorState error={state.error} onRetry={run} /> : null}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '800', marginBottom: 4 },
  preview: { width: '100%', height: 220, borderRadius: 10, marginVertical: 6 },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    marginVertical: 6,
  },
});
