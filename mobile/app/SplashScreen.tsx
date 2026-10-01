import * as React from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { themeFor } from '../constants/theme';
import { ScreenContainer, Spacer, MutedText, PrimaryButton } from '../components/ui';
import type { BackendState } from '../hooks/useBackendHealth';

const MIN_SPLASH_MS = 1200;

/** Branding + backend availability probe. Never blocks: always continuable. */
export function SplashScreen({
  backend,
  onContinue,
  onRetry,
}: {
  backend: BackendState;
  onContinue: () => void;
  onRetry: () => void;
}): React.JSX.Element {
  const scheme = useColorScheme();
  const theme = themeFor(scheme);
  const [elapsed, setElapsed] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => setElapsed(true), MIN_SPLASH_MS);
    return () => clearTimeout(timer);
  }, []);

  React.useEffect(() => {
    if (elapsed && backend.status !== 'checking') {
      const timer = setTimeout(onContinue, 400);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [elapsed, backend.status, onContinue]);

  return (
    <ScreenContainer>
      <StatusBar style={scheme === 'light' ? 'dark' : 'light'} />
      <View style={styles.hero}>
        <View style={[styles.mark, { borderColor: theme.primary }]}>
          <Text style={[styles.markText, { color: theme.primary }]}>TI</Text>
        </View>
        <Text style={[styles.name, { color: theme.text }]}>TrueIntent</Text>
        <MutedText>Verify before you trust. Scam & phishing indicators, explained.</MutedText>
        <Spacer />
        {backend.status === 'checking' ? (
          <MutedText>Checking backend availability…</MutedText>
        ) : backend.status === 'online' ? (
          <Text style={[styles.online, { color: theme.safe }]}>Backend reachable</Text>
        ) : backend.status === 'degraded' ? (
          <Text style={[styles.online, { color: theme.caution }]}>
            Backend reachable (partial service)
          </Text>
        ) : (
          <View style={styles.center}>
            <Text style={[styles.offline, { color: theme.warning }]}>
              Backend unreachable — you can continue, but analyses need the server.
            </Text>
            <Spacer height={8} />
            <PrimaryButton title="Retry connection" onPress={onRetry} />
          </View>
        )}
        <Spacer />
        <PrimaryButton title="Continue" onPress={onContinue} />
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  mark: {
    width: 84,
    height: 84,
    borderRadius: 20,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  markText: { fontSize: 36, fontWeight: '800' },
  name: { fontSize: 32, fontWeight: '800', marginBottom: 8 },
  online: { fontSize: 14, fontWeight: '700' },
  offline: { fontSize: 14, textAlign: 'center' },
  center: { alignItems: 'center' },
});
