import type { MobileAnalyzeData } from '../types/api';

export type Screen =
  | { name: 'Splash' }
  | { name: 'Home' }
  | { name: 'Scan' }
  | { name: 'Url' }
  | { name: 'Message' }
  | { name: 'Screenshot' }
  | { name: 'Combined' }
  | { name: 'Result'; title: string; result: MobileAnalyzeData }
  | { name: 'About' };

export type Navigate = (screen: Screen) => void;
