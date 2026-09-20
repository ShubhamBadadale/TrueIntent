import type { Diagnostic } from '../types';

export function DiagnosticsPanel({
  diagnostics,
  onJump
}: {
  diagnostics: Diagnostic[];
  onJump: (line: number, column: number) => void;
}) {
  if (diagnostics.length === 0) {
    return <div className="empty">No diagnostics.</div>;
  }
  const groups = diagnostics.reduce<Record<string, Diagnostic[]>>((acc, diag) => {
    acc[diag.phase] = [...(acc[diag.phase] ?? []), diag];
    return acc;
  }, {});
  return (
    <div className="stack">
      {Object.entries(groups).map(([phase, items]) => (
        <section key={phase} className="panel-section">
          <h3>{phase}</h3>
          {items.map((diag, index) => (
            <button
              key={`${diag.code}-${index}`}
              type="button"
              className={`diagnostic ${diag.severity}`}
              disabled={diag.line === null || diag.column === null}
              onClick={() => {
                if (diag.line !== null && diag.column !== null) onJump(diag.line, diag.column);
              }}
            >
              <div className="diagnostic-head">
                <strong>{diag.code}</strong>
                <span>{diag.line ? `line ${diag.line}, col ${diag.column}` : 'global'}</span>
              </div>
              <p>{diag.message}</p>
              {diag.hint && <small>{diag.hint}</small>}
            </button>
          ))}
        </section>
      ))}
    </div>
  );
}
