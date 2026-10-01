import * as React from 'react';
import { StyleSheet, View, useColorScheme } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useBackendHealth } from './hooks/useBackendHealth';
import { themeFor } from './constants/theme';
import { BottomNav } from './components/nav';
import type { MainTab } from './components/nav';
import { AboutScreen } from './app/AboutScreen';
import { CombinedScreen } from './app/CombinedScreen';
import { HomeScreen } from './app/HomeScreen';
import { MessageScannerScreen } from './app/MessageScannerScreen';
import { ResultScreen } from './app/ResultScreen';
import { ScanScreen } from './app/ScanScreen';
import { ScreenshotScannerScreen } from './app/ScreenshotScannerScreen';
import { SplashScreen } from './app/SplashScreen';
import { UrlScannerScreen } from './app/UrlScannerScreen';
import type { Screen } from './app/navigation';
import type { MobileAnalyzeData } from './types/api';

const MAX_HISTORY = 20;

function tabFor(screen: Screen): MainTab {
  if (screen.name === 'Home') return 'Home';
  if (screen.name === 'About') return 'About';
  return 'Scan';
}

export default function App(): React.JSX.Element {
  const scheme = useColorScheme();
  const theme = themeFor(scheme);
  const { state: backend, recheck } = useBackendHealth();
  const [history, setHistory] = React.useState<Screen[]>([{ name: 'Splash' }]);
  const current = history[history.length - 1] ?? { name: 'Splash' };

  const navigate = React.useCallback((screen: Screen) => {
    setHistory((prev) => [...prev.slice(-MAX_HISTORY), screen]);
  }, []);

  const back = React.useCallback(() => {
    setHistory((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev));
  }, []);

  const goHome = React.useCallback(() => {
    setHistory([{ name: 'Home' }]);
  }, []);

  const goTab = React.useCallback((tab: MainTab) => {
    if (tab === 'Home') setHistory([{ name: 'Home' }]);
    else if (tab === 'Scan') setHistory([{ name: 'Scan' }]);
    else setHistory([{ name: 'About' }]);
  }, []);

  const showResult = React.useCallback(
    (title: string) => (result: MobileAnalyzeData) => {
      navigate({ name: 'Result', title, result });
    },
    [navigate],
  );

  if (current.name === 'Splash') {
    return (
      <SafeAreaProvider>
        <StatusBar style={scheme === 'light' ? 'dark' : 'light'} />
        <SplashScreen
          backend={backend}
          onContinue={() => navigate({ name: 'Home' })}
          onRetry={recheck}
        />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <StatusBar style={scheme === 'light' ? 'dark' : 'light'} />
      <View style={[styles.shell, { backgroundColor: theme.background }]}>
        <View style={styles.content}>
          {current.name === 'Home' ? (
            <HomeScreen
              navigate={navigate}
              backend={backend}
              onRetryHealth={recheck}
              onStartScan={() => navigate({ name: 'Scan' })}
            />
          ) : current.name === 'Scan' ? (
            <ScanScreen navigate={navigate} onBack={back} />
          ) : current.name === 'Url' ? (
            <UrlScannerScreen onResult={showResult('Link result')} onBack={back} />
          ) : current.name === 'Message' ? (
            <MessageScannerScreen onResult={showResult('Message result')} onBack={back} />
          ) : current.name === 'Screenshot' ? (
            <ScreenshotScannerScreen onResult={showResult('Screenshot result')} onBack={back} />
          ) : current.name === 'Combined' ? (
            <CombinedScreen onResult={showResult('Combined result')} onBack={back} />
          ) : current.name === 'Result' ? (
            <ResultScreen
              title={current.title}
              result={current.result}
              onBack={back}
              onHome={goHome}
            />
          ) : (
            <AboutScreen onBack={back} />
          )}
        </View>
        <BottomNav active={tabFor(current)} onSelect={goTab} />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1 },
  content: { flex: 1 },
});
