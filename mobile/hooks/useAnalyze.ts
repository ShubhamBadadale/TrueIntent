import * as React from 'react';
import { ApiError } from '../services/api';
import type { ErrorBody } from '../types/api';

/** Async-operation state machine shared by every scanner screen. */
export type AnalyzeState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ErrorBody; retry: () => void }
  | { status: 'done'; result: T };

export function useAnalyze<T>(runner: () => Promise<T>): {
  state: AnalyzeState<T>;
  run: () => void;
  reset: () => void;
} {
  const [state, setState] = React.useState<AnalyzeState<T>>({ status: 'idle' });
  const runnerRef = React.useRef(runner);
  runnerRef.current = runner;

  const run = React.useCallback(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    void runnerRef
      .current()
      .then((result) => {
        if (!cancelled) setState({ status: 'done', result });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const body: ErrorBody =
          error instanceof ApiError
            ? error.toErrorBody()
            : {
                code: 'internal_error',
                message: 'Something went wrong. Please retry.',
                module: null,
                details: {},
              };
        setState({
          status: 'error',
          error: body,
          retry: () => run(),
        });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reset = React.useCallback(() => setState({ status: 'idle' }), []);
  return { state, run, reset };
}
