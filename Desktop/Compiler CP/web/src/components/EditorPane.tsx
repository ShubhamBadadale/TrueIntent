import Editor, { type Monaco, type OnMount } from '@monaco-editor/react';
import { useEffect, useRef } from 'react';
import type { editor } from 'monaco-editor';
import type { Example, Target } from '../types';
import { registerMcdLanguage } from '../monaco/mcdLanguage';

type Props = {
  source: string;
  target: Target;
  examples: Example[];
  diagnostics: Array<{ severity: 'error' | 'warning'; code: string; message: string; line: number | null; column: number | null }>;
  compiling: boolean;
  jumpTo: { line: number; column: number; nonce: number } | null;
  onSourceChange: (source: string) => void;
  onTargetChange: (target: Target) => void;
  onCompile: () => void;
  onLoadExample: (source: string) => void;
};

export function EditorPane(props: Props) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);

  const handleMount: OnMount = (instance, monaco) => {
    editorRef.current = instance;
    monacoRef.current = monaco;
    registerMcdLanguage(monaco);
    instance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, props.onCompile);
  };

  useEffect(() => {
    const monaco = monacoRef.current;
    const instance = editorRef.current;
    if (!monaco || !instance) return;
    const model = instance.getModel();
    if (!model) return;
    const markers = props.diagnostics
      .filter((diag) => diag.line !== null && diag.column !== null)
      .map((diag) => ({
        severity: diag.severity === 'error' ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
        message: `${diag.code}: ${diag.message}`,
        startLineNumber: diag.line ?? 1,
        startColumn: diag.column ?? 1,
        endLineNumber: diag.line ?? 1,
        endColumn: (diag.column ?? 1) + 1
      }));
    monaco.editor.setModelMarkers(model, 'mcdc', markers);
  }, [props.diagnostics]);

  useEffect(() => {
    const instance = editorRef.current;
    if (!instance || !props.jumpTo) return;
    const position = { lineNumber: props.jumpTo.line, column: props.jumpTo.column };
    instance.focus();
    instance.setPosition(position);
    instance.revealPositionInCenter(position);
  }, [props.jumpTo]);

  return (
    <section className="pane editor-pane">
      <div className="toolbar">
        <div className="toolbar-main">
          <label className="field">
            <span>Example</span>
            <select onChange={(event) => props.onLoadExample(event.target.value)} defaultValue="">
              <option value="" disabled>Choose a demo</option>
              {props.examples.map((example) => (
                <option key={example.name} value={example.source}>{formatExampleName(example.name)}</option>
              ))}
            </select>
          </label>
          <div className="field">
            <span>Target</span>
            <div className="segmented">
              {(['aws', 'gcp', 'azure', 'all'] as Target[]).map((target) => (
                <button key={target} className={props.target === target ? 'active' : ''} onClick={() => props.onTargetChange(target)}>
                  {target.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button className="primary" disabled={!props.source.trim() || props.compiling} onClick={props.onCompile}>
          {props.compiling ? 'Compiling' : 'Compile'}
        </button>
      </div>
      <Editor
        height="100%"
        language="mcd"
        theme="vs-dark"
        value={props.source}
        onChange={(value) => props.onSourceChange(value ?? '')}
        onMount={handleMount}
        options={{ minimap: { enabled: false }, fontSize: 14, tabSize: 2, wordWrap: 'on' }}
      />
    </section>
  );
}

function formatExampleName(name: string) {
  return name
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
