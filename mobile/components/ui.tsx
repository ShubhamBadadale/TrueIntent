import * as React from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useColorScheme,
} from 'react-native';
import { themeFor } from '../constants/theme';
import { friendlyErrorMessage } from '../utils/errors';
import type { ErrorBody } from '../types/api';

export { ScreenContainer, Spacer } from './ScreenContainer';

export function Card({ children }: { children: React.ReactNode }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      {children}
    </View>
  );
}

export function CardTitle({ children }: { children: React.ReactNode }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return <Text style={[styles.cardTitle, { color: theme.text }]}>{children}</Text>;
}

export function MutedText({ children }: { children: React.ReactNode }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return <Text style={[styles.muted, { color: theme.muted }]}>{children}</Text>;
}

export function BodyText({ children }: { children: React.ReactNode }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return <Text style={[styles.body, { color: theme.text }]}>{children}</Text>;
}

export function PrimaryButton({
  title,
  onPress,
  disabled = false,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <TouchableOpacity
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.button,
        { backgroundColor: theme.primary, opacity: disabled ? 0.5 : 1 },
      ]}
    >
      <Text style={[styles.buttonText, { color: theme.primaryText }]}>{title}</Text>
    </TouchableOpacity>
  );
}

export function SecondaryButton({
  title,
  onPress,
}: {
  title: string;
  onPress: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <TouchableOpacity
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.button, styles.secondary, { borderColor: theme.border }]}
    >
      <Text style={[styles.buttonText, { color: theme.text }]}>{title}</Text>
    </TouchableOpacity>
  );
}

export function LoadingState({ message }: { message: string }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <View style={styles.center}>
      <ActivityIndicator size="large" color={theme.primary} />
      <View style={{ height: 8 }} />
      <Text style={{ color: theme.muted }}>{message}</Text>
    </View>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: ErrorBody;
  onRetry: () => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <View style={[styles.card, styles.center, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      <Text style={[styles.errorTitle, { color: theme.danger }]}>Analysis failed</Text>
      <Text style={[styles.body, { color: theme.text, textAlign: 'center' }]}>
        {friendlyErrorMessage(error)}
      </Text>
      <View style={{ height: 4 }} />
      <Text style={[styles.muted, { color: theme.muted }]}>Error: {error.code}</Text>
      <View style={{ height: 12 }} />
      <PrimaryButton title="Retry" onPress={onRetry} />
    </View>
  );
}

export function OfflineBanner({ onRetry }: { onRetry: () => void }): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  return (
    <View style={[styles.banner, { backgroundColor: theme.surface, borderColor: theme.warning }]}>
      <Text style={[styles.body, { color: theme.text }]}>
        Backend unreachable — results need the TrueIntent server.
      </Text>
      <View style={{ height: 8 }} />
      <SecondaryButton title="Retry connection" onPress={onRetry} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginVertical: 6,
  },
  cardTitle: { fontSize: 16, fontWeight: '700', marginBottom: 8 },
  muted: { fontSize: 13, lineHeight: 18 },
  body: { fontSize: 14, lineHeight: 20 },
  button: {
    borderRadius: 10,
    paddingVertical: 13,
    paddingHorizontal: 16,
    alignItems: 'center',
    marginVertical: 6,
  },
  secondary: { borderWidth: 1, backgroundColor: 'transparent' },
  buttonText: { fontSize: 16, fontWeight: '700' },
  center: { alignItems: 'center', paddingVertical: 12 },
  errorTitle: { fontSize: 16, fontWeight: '700', marginBottom: 6 },
  banner: { borderWidth: 1, borderRadius: 12, padding: 14, marginVertical: 6 },
});
