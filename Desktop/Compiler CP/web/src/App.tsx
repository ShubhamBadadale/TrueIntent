import { useEffect, useMemo, useState } from 'react';
import { compileSource, fetchExamples } from './api/client';
import { AstGraph } from './components/AstGraph';
import { CodeOutput } from './components/CodeOutput';
import { DiagnosticsPanel } from './components/DiagnosticsPanel';
import { EditorPane } from './components/EditorPane';
import { IrGraph } from './components/IrGraph';
import { PipelineBar } from './components/PipelineBar';
import { ReportPanel } from './components/ReportPanel';
import { useCompilerStore } from './store/useCompilerStore';
import type { Example } from './types';

const tabs = [
  ['diagnostics', 'Diagnostics'],
  ['code', 'Generated Code'],
  ['ast', 'AST'],
  ['ir', 'IR Graph'],
  ['report', 'Report']
] as const;

export default function App() {
  const store = useCompilerStore();
  const [examples, setExamples] = useState<Example[]>([]);
  const [jumpTo, setJumpTo] = useState<{ line: number; column: number; nonce: number } | null>(null);

  useEffect(() => {
    fetchExamples().then(setExamples).catch((error) => store.setApiError(error.message));
  }, []);

  const errorCount = useMemo(() => store.result?.diagnostics.filter((diag) => diag.severity === 'error').length ?? 0, [store.result]);

  async function runCompile() {
    store.setStatus('compiling');
    store.setApiError(null);
    try {
      const result = await compileSource(store.source, store.target);
      store.setResult(result);
      store.setStatus(result.success ? 'success' : 'error');
    } catch (error) {
      store.setApiError(error instanceof Error ? error.message : 'Could not reach the compiler service.');
      store.setStatus('error');
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Multi-Cloud Deployment Compiler</h1>
          <p>DSL to Terraform/OpenTofu for AWS, GCP, and Azure</p>
        </div>
        <div className="summary">
          <span>{store.result ? `${errorCount} errors` : 'ready'}</span>
          <span>{store.target.toUpperCase()}</span>
        </div>
      </header>

      {store.apiError && <div className="api-error">{store.apiError}</div>}

      <div className="workspace">
        <EditorPane
          source={store.source}
          target={store.target}
          examples={examples}
          diagnostics={store.result?.diagnostics ?? []}
          compiling={store.status === 'compiling'}
          jumpTo={jumpTo}
          onSourceChange={store.setSource}
          onTargetChange={store.setTarget}
          onCompile={runCompile}
          onLoadExample={(source) => store.setSource(source)}
        />
        <section className="pane output-pane">
          <nav className="tabs">
            {tabs.map(([id, label]) => (
              <button key={id} className={store.activeTab === id ? 'active' : ''} onClick={() => store.setActiveTab(id)}>
                {label}
              </button>
            ))}
          </nav>
          <div className="tab-body">
            {store.activeTab === 'diagnostics' && (
              <DiagnosticsPanel
                diagnostics={store.result?.diagnostics ?? []}
                onJump={(line, column) => setJumpTo({ line, column, nonce: Date.now() })}
              />
            )}
            {store.activeTab === 'code' && <CodeOutput result={store.result} />}
            {store.activeTab === 'ast' && <AstGraph ast={store.result?.ast} />}
            {store.activeTab === 'ir' && <IrGraph ir={store.result?.ir} />}
            {store.activeTab === 'report' && <ReportPanel result={store.result} />}
          </div>
        </section>
      </div>

      <PipelineBar result={store.result} status={store.status} />
    </main>
  );
}
