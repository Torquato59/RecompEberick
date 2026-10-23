import type { SupportType } from './types.js';

export const SUPPORT_LABELS: Record<SupportType, string> = {
  pinned: 'Articulado', roller: 'Móvel', fixed: 'Engastado', free: 'Livre',
};
export const SUPPORT_CONDITIONS: Record<SupportType, string> = {
  pinned: 'δ = 0; M = 0', roller: 'δ = 0; M = 0',
  fixed: 'δ = 0; θ = 0', free: 'M = 0; reação externa = 0',
};
