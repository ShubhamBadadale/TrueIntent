import { create } from 'zustand';
import type { CompileResponse, Target } from '../types';

const starter = `cloud app "StudentPortal" {
  network "main" {
    cidr = "10.0.0.0/16"
  }

  subnet "public" {
    cidr = "10.0.1.0/24"
    depends_on = ["main"]
  }

  firewall "web-fw" {
    depends_on = ["main"]
    allow = [
      { port = 80, protocol = "tcp", source = "0.0.0.0/0" },
      { port = 443, protocol = "tcp", source = "0.0.0.0/0" }
    ]
  }

  compute "web" {
    image = "ubuntu-22.04"
    cpu = 2
    memory = 4
    depends_on = ["public", "web-fw"]
  }
}`;

type CompilerState = {
  source: string;
  target: Target;
  result: CompileResponse | null;
  activeTab: 'diagnostics' | 'code' | 'ast' | 'ir' | 'report';
  status: 'idle' | 'compiling' | 'success' | 'error';
  apiError: string | null;
  setSource: (source: string) => void;
  setTarget: (target: Target) => void;
  setResult: (result: CompileResponse | null) => void;
  setActiveTab: (tab: CompilerState['activeTab']) => void;
  setStatus: (status: CompilerState['status']) => void;
  setApiError: (message: string | null) => void;
};

export const useCompilerStore = create<CompilerState>((set) => ({
  source: starter,
  target: 'all',
  result: null,
  activeTab: 'diagnostics',
  status: 'idle',
  apiError: null,
  setSource: (source) => set({ source }),
  setTarget: (target) => set({ target }),
  setResult: (result) => set({ result }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setStatus: (status) => set({ status }),
  setApiError: (apiError) => set({ apiError })
}));
