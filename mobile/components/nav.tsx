import * as React from 'react';
import { StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { themeFor } from '../constants/theme';
import { SecondaryButton } from './ui';

export type MainTab = 'Home' | 'Scan' | 'About';

/** Bottom navigation: Home / Scan / About. Scanner screens use BackHeader. */
export function BottomNav({
  active,
  onSelect,
}: {
  active: MainTab;
  onSelect: (tab: MainTab) => void;
}): React.JSX.Element {
  const theme = themeFor(useColorScheme());
  const insets = useSafeAreaInsets();
  const tabs: MainTab[] = ['Home', 'Scan', 'About'];
  return (
    <View
      style={[
        styles.bar,
        {
          backgroundColor: theme.surface,
          borderColor: theme.border,
          paddingBottom: Math.max(insets.bottom, 6),
        },
      ]}
    >
      {tabs.map((tab) => {
        const selected = tab === active;
        return (
          <TouchableOpacity
            key={tab}
            accessibilityRole="button"
            onPress={() => onSelect(tab)}
            style={styles.tab}
          >
            <Text style={[styles.label, { color: selected ? theme.primary : theme.muted }]}>
              {tab}
            </Text>
            <View
              style={[
                styles.dot,
                { backgroundColor: selected ? theme.primary : 'transparent' },
              ]}
            />
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

/** Simple back affordance for non-tab screens (scanners, results). */
export function BackHeader({ onBack }: { onBack: () => void }): React.JSX.Element {
  return (
    <View style={styles.backRow}>
      <SecondaryButton title="‹ Back" onPress={onBack} />
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    borderTopWidth: 1,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 8 },
  label: { fontSize: 14, fontWeight: '700' },
  dot: { width: 6, height: 6, borderRadius: 3, marginTop: 4 },
  backRow: { marginBottom: 4 },
});
