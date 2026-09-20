import type { CompileResponse } from '../types';

export function ReportPanel({ result }: { result: CompileResponse | null }) {
  if (!result) {
    return <div className="empty">Compile to view the report.</div>;
  }
  return (
    <div className="stack">
      <section className="panel-section">
        <h3>Phase Timings</h3>
        <table>
          <tbody>
            {Object.entries(result.report.phase_timings_ms).map(([phase, ms]) => (
              <tr key={phase}><td>{phase}</td><td>{ms} ms</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel-section">
        <h3>Resource Counts</h3>
        <table>
          <tbody>
            {Object.entries(result.report.resource_counts).map(([type, count]) => (
              <tr key={type}><td>{type}</td><td>{count}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
