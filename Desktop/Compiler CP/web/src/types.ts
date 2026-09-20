export type Target = 'aws' | 'gcp' | 'azure' | 'all';

export type Diagnostic = {
  severity: 'error' | 'warning';
  code: string;
  message: string;
  line: number | null;
  column: number | null;
  phase: string;
  hint?: string | null;
};

export type CompileResponse = {
  success: boolean;
  diagnostics: Diagnostic[];
  ast: AstNode | null;
  ir: IrGraph | null;
  generated: Record<'aws' | 'gcp' | 'azure', string | null>;
  report: {
    phase_timings_ms: Record<string, number>;
    resource_counts: Record<string, number>;
    backend_reports?: Record<string, unknown>;
  };
};

export type Example = {
  name: string;
  source: string;
};

export type AstNode = {
  type: string;
  name?: string;
  kind?: string;
  value?: unknown;
  loc?: { line: number; column: number; file?: string | null } | null;
  children?: AstNode[];
};

export type IrGraph = {
  appName: string;
  nodes: Array<{ id: string; type: string; label: string; attributes: Record<string, unknown> }>;
  edges: Array<{ from: string; to: string; kind: string }>;
};
