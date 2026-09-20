import JSZip from 'jszip';
import type { CompileResponse } from '../types';

const targets = ['aws', 'gcp', 'azure'] as const;

export function CodeOutput({ result }: { result: CompileResponse | null }) {
  if (!result) {
    return <div className="empty">Compile to view generated Terraform.</div>;
  }
  const available = targets.filter((target) => result.generated[target]);
  if (available.length === 0) {
    return <div className="empty">No generated files.</div>;
  }
  return (
    <div className="stack">
      <div className="actions">
        <button onClick={() => downloadZip(result)}>Download all as .zip</button>
      </div>
      {available.map((target) => (
        <section key={target} className="panel-section">
          <div className="section-title">
            <h3>{target.toUpperCase()} main.tf</h3>
            <div>
              <button onClick={() => navigator.clipboard.writeText(result.generated[target] ?? '')}>Copy</button>
              <button onClick={() => downloadText(`${target}-main.tf`, result.generated[target] ?? '')}>Download .tf</button>
            </div>
          </div>
          <pre className="code"><code>{result.generated[target]}</code></pre>
        </section>
      ))}
    </div>
  );
}

function downloadText(name: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

async function downloadZip(result: CompileResponse) {
  const zip = new JSZip();
  targets.forEach((target) => {
    const content = result.generated[target];
    if (content) zip.file(`${target}/main.tf`, content);
  });
  const blob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'mcdc-generated.zip';
  link.click();
  URL.revokeObjectURL(url);
}
