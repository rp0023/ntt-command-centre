import type { PersonaId } from '@/types';

export interface NavItemDef {
  label: string;
  to: string;
  iconKey: string;
  personas?: PersonaId[];
}
export interface NavGroupDef {
  heading: string;
  items: NavItemDef[];
}

export const NAV_GROUPS: NavGroupDef[] = [
  {
    heading: '',
    items: [
      { label: 'Command Centre', to: '/command-centre', iconKey: 'command', personas: ['sales'] },
      { label: 'Executive Brief', to: '/brief', iconKey: 'atlas', personas: ['executive'] },
      { label: 'Coaching Patterns', to: '/patterns', iconKey: 'hotspots', personas: ['manager'] },
    ],
  },
  {
    heading: 'Working deals',
    items: [
      { label: 'Open book', to: '/book', iconKey: 'lanes' },
      { label: 'Risk desk', to: '/anomalies', iconKey: 'actions' },
    ],
  },
  {
    heading: 'Board pack',
    items: [{ label: 'Review pack', to: '/briefing', iconKey: 'evidence' }],
  },
];

export function navGroupsForPersona(persona: PersonaId): NavGroupDef[] {
  return NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => !i.personas || i.personas.includes(persona)),
  })).filter((g) => g.items.length > 0);
}

const PERSONA_HOME: Record<PersonaId, string> = {
  sales: '/command-centre',
  executive: '/brief',
  manager: '/patterns',
};

export function personaHomePath(persona: PersonaId): string {
  const home = PERSONA_HOME[persona];
  const visible = navGroupsForPersona(persona).flatMap((g) => g.items.map((i) => i.to));
  return visible.includes(home) ? home : (visible[0] ?? '/brief');
}
