import type { CompileResponse } from '../types';

const phases = ['lex_parse', 'semantic', 'ir', 'codegen_aws', 'codegen_gcp', 'codegen_azure'];

export function PipelineBar({ result, status }: { result: CompileResponse | null; status: string }) {
  const timings = result?.report.phase_timings_ms ?? {};
  return (
    <footer className="pipeline">
      <span className={`status ${status}`}>{status}</span>
      {phases.map((phase) => (
        <span key={phase} className={timings[phase] !== undefined ? 'done' : ''}>
          {phase.replace('_', ' ')} {timings[phase] !== undefined ? `✓ ${timings[phase]}ms` : ''}
        </span>
      ))}
    </footer>
  );
}
