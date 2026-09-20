import type { CompileResponse, Example, Target } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export async function compileSource(source: string, target: Target): Promise<CompileResponse> {
  const response = await fetch(`${API_BASE}/api/compile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, target })
  });
  if (!response.ok) {
    throw new Error(`Compiler service returned ${response.status}`);
  }
  return response.json();
}

export async function fetchExamples(): Promise<Example[]> {
  const response = await fetch(`${API_BASE}/api/examples`);
  if (!response.ok) {
    throw new Error(`Examples request failed with ${response.status}`);
  }
  return response.json();
}
