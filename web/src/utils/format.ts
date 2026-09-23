export function money(v: number | undefined | null): string {
  const n = Number(v ?? 0);
  const abs = Math.abs(n);
  const sign = n < 0 ? '−' : '';
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

export function pct(v: number | undefined | null, digits = 1): string {
  return `${Number(v ?? 0).toFixed(digits)}%`;
}

export function n(v: number | undefined | null): string {
  return Number(v ?? 0).toLocaleString('en-US');
}
