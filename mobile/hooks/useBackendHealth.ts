import * as React from 'react';
import { checkBackendReadiness } from '../services/api';
import type { Readiness } from '../services/api';
import { HEALTH_CHECK_TIMEOUT_MS } from '../constants/config';

export type BackendState =
  | { status: 'checking' }
  | { status: 'online' }
  | { status: 'degraded' }
  | { status: 'offline' };

/** Engine readiness: online, degraded (Partial), or offline. */
export function engineLabel(status: BackendState['status']): string {
  switch (status) {
    case 'online':
      return 'Online';
    case 'degraded':
      return 'Partial';
    case 'offline':
      return 'Offline';
    default:
      return 'Checking…';
  }
}

export function engineReachable(status: BackendState['status']): boolean {
  return status === 'online' || status === 'degraded';
}

/**
 * Backend availability probe. Never throws and never blocks indefinitely:
 * the splash screen caps the wait and continues regardless.
 */
export function useBackendHealth(): {
  state: BackendState;
  readiness: Readiness | 'checking';
  recheck: () => void;
} {
  const [state, setState] = React.useState<BackendState>({ status: 'checking' });
  const run = React.useCallback(() => {
    let cancelled = false;
    setState({ status: 'checking' });
    void checkBackendReadiness(HEALTH_CHECK_TIMEOUT_MS).then((readiness) => {
      if (!cancelled) setState({ status: readiness });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    const cancel = run();
    return cancel;
  }, [run]);

  const readiness: Readiness | 'checking' =
    state.status === 'checking' ? 'checking' : state.status;
  return { state, readiness, recheck: run };
}
