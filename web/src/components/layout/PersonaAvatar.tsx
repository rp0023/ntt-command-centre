import { Box } from '@mui/material';
import type { PersonaId } from '@/types';

export const PERSONA_COLOR: Record<string, string> = {
  executive: '#0067B1',
  sales: '#00A9CE',
  manager: '#E6007E',
};

function faces(color: string) {
  return { light: color, mid: shade(color, -0.18), dark: shade(color, -0.36) };
}

function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const v = amount < 0 ? c * (1 + amount) : c + (255 - c) * amount;
    return Math.round(Math.max(0, Math.min(255, v)));
  });
  return `#${ch.map((c) => c.toString(16).padStart(2, '0')).join('')}`;
}

/** Globe + podium — entity executive. */
function ExecutiveGlyph({ color }: { color: string }) {
  const f = faces(color);
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" role="presentation">
      <defs>
        <radialGradient id="ex-globe" cx="35%" cy="28%" r="78%">
          <stop offset="0%" stopColor={shade(f.light, 0.42)} />
          <stop offset="55%" stopColor={f.light} />
          <stop offset="100%" stopColor={f.dark} />
        </radialGradient>
      </defs>
      <ellipse cx="24" cy="42" rx="13" ry="2.6" fill={f.dark} opacity="0.22" />
      <circle cx="24" cy="20" r="13.5" fill="url(#ex-globe)" />
      <g fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="1.1">
        <ellipse cx="24" cy="20" rx="5.6" ry="13.5" />
        <path d="M11.2 16.2h25.6M11.2 24h25.6" />
      </g>
      <circle cx="19" cy="14" r="3.8" fill="#fff" opacity="0.22" />
      <path d="M16 34l8-4 8 4v5l-8 3-8-3z" fill={shade(f.light, 0.35)} />
      <path d="M16 34v5l8 3V37z" fill={f.mid} />
      <path d="M32 34v5l-8 3V37z" fill={f.dark} />
    </svg>
  );
}

/** Isometric briefcase — account executive. */
function SalesGlyph({ color }: { color: string }) {
  const f = faces(color);
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" role="presentation">
      <defs>
        <linearGradient id="sa-top" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={shade(f.light, 0.5)} />
          <stop offset="100%" stopColor={f.light} />
        </linearGradient>
      </defs>
      <ellipse cx="24" cy="42" rx="15" ry="2.8" fill={f.dark} opacity="0.22" />
      <path d="M18 14c0-3 2.4-5.5 6-5.5s6 2.5 6 5.5" fill="none" stroke={f.dark} strokeWidth="2.4" strokeLinecap="round" />
      <path d="M24 12l16 8-16 8-16-8z" fill="url(#sa-top)" />
      <path d="M8 20v14l16 8V28z" fill={f.mid} />
      <path d="M40 20v14l-16 8V28z" fill={f.dark} />
      <path d="M24 28l6 3-6 3-6-3z" fill={shade(f.light, 0.2)} />
      <path d="M21 16.5h6v2.2h-6z" fill={f.dark} opacity="0.55" />
    </svg>
  );
}

/** 3D bars + magnifier — sales manager / coaching. */
function ManagerGlyph({ color }: { color: string }) {
  const f = faces(color);
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" role="presentation">
      <defs>
        <linearGradient id="mg-bar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={shade(f.light, 0.35)} />
          <stop offset="100%" stopColor={f.mid} />
        </linearGradient>
      </defs>
      <ellipse cx="24" cy="42" rx="15" ry="2.8" fill={f.dark} opacity="0.22" />
      {[
        { x: 7, h: 11 },
        { x: 17, h: 19 },
        { x: 27, h: 26 },
      ].map((b) => (
        <g key={b.x}>
          <path d={`M${b.x} ${38 - b.h}l5-2.5 5 2.5-5 2.5z`} fill={shade(f.light, 0.5)} />
          <path d={`M${b.x} ${38 - b.h}v${b.h}l5 2.5V${40.5 - b.h}z`} fill="url(#mg-bar)" />
          <path d={`M${b.x + 10} ${38 - b.h}v${b.h}l-5 2.5V${40.5 - b.h}z`} fill={f.dark} />
        </g>
      ))}
      <circle cx="35" cy="13" r="6.4" fill="#fff" fillOpacity="0.92" stroke={f.dark} strokeWidth="2.1" />
      <path d="M40 18l4.5 4.5" stroke={f.dark} strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}

const GLYPHS: Record<string, (p: { color: string }) => JSX.Element> = {
  executive: ExecutiveGlyph,
  sales: SalesGlyph,
  manager: ManagerGlyph,
};

export function PersonaAvatar({ personaId, size = 30 }: { personaId: PersonaId | string; size?: number }) {
  const color = PERSONA_COLOR[personaId] ?? '#0067B1';
  const Glyph = GLYPHS[personaId] ?? ExecutiveGlyph;
  return (
    <Box
      sx={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        background: `radial-gradient(circle at 32% 28%, ${shade(color, 0.9)}, ${shade(color, 0.72)})`,
        boxShadow: `inset 0 -1px 2px ${shade(color, 0.3)}55, 0 1px 2px rgba(15,23,42,.16)`,
        p: `${Math.round(size * 0.11)}px`,
      }}
    >
      <Glyph color={color} />
    </Box>
  );
}
