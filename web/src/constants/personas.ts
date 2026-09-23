import type { PersonaDef, PersonaId } from '@/types';

export const PERSONAS: PersonaDef[] = [
  {
    id: 'executive',
    name: 'Executive',
    role: 'Entity review and coverage vs plan.',
    lens: 'TLDR and the decisions that cannot wait.',
  },
  {
    id: 'sales',
    name: 'Account executive',
    role: 'Open book, slips, and this week’s moves.',
    lens: 'At-risk deals and the next action.',
  },
  {
    id: 'manager',
    name: 'Sales manager',
    role: 'Team patterns, coaching, upsell.',
    lens: 'Rep benchmarks and anomaly clusters.',
  },
];

export const DEFAULT_PERSONA: PersonaId = 'sales';

export function getPersona(id: PersonaId): PersonaDef {
  return PERSONAS.find((p) => p.id === id) ?? PERSONAS[0];
}
