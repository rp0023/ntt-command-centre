import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
  ZAxis,
  Sankey,
} from 'recharts';
import { Box, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { CHART_COLORS } from '@/app/config/theme';
import { money, n } from '@/utils/format';
import type { ChartSpec } from '@/types';

function Tip({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <Box sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', p: 1.25, borderRadius: 1.5, boxShadow: 3 }}>
      {rows.map((r) => (
        <Typography key={r.k} variant="caption" sx={{ display: 'block', lineHeight: 1.55 }}>
          <Box component="span" sx={{ color: 'text.secondary' }}>{r.k}: </Box>
          <Box component="span" sx={{ fontWeight: 700 }}>{r.v}</Box>
        </Typography>
      ))}
    </Box>
  );
}

function Heat({ spec }: { spec: ChartSpec }) {
  const theme = useTheme();
  const rows = spec.rows ?? [];
  const cols = spec.cols ?? [];
  const values = spec.values ?? [];
  const max = Math.max(...values.flat(), 0.001);
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: `100px repeat(${cols.length}, minmax(72px, 1fr))`, gap: 0.65, overflow: 'auto', pb: 0.5 }}>
      <Box />
      {cols.map((c) => (
        <Typography key={c} variant="caption" sx={{ textAlign: 'center', color: 'text.secondary', fontWeight: 600, lineHeight: 1.2 }}>
          {c.replace('Consulting Services', 'Consulting').replace('Technical Services', 'Tech svc')}
        </Typography>
      ))}
      {rows.map((r, ri) => (
        <Box key={r} sx={{ display: 'contents' }}>
          <Typography variant="caption" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', pr: 0.5 }}>
            {r}
          </Typography>
          {cols.map((c, ci) => {
            const v = values[ri]?.[ci] ?? 0;
            const t = v / max;
            const dark = t > 0.55;
            return (
              <Box
                key={c}
                title={`${r} · ${c}: ${money(v)}`}
                sx={{
                  height: 44,
                  borderRadius: 1.25,
                  bgcolor: v ? alpha(theme.palette.primary.main, 0.1 + 0.78 * t) : alpha(theme.palette.divider, 0.35),
                  color: dark ? '#fff' : 'text.primary',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                {v ? money(v) : '—'}
              </Box>
            );
          })}
        </Box>
      ))}
    </Box>
  );
}

function Waterfall({ data }: { data: { label: string; value: number; kind?: string }[] }) {
  const theme = useTheme();
  let running = 0;
  const rows = (data ?? []).map((step) => {
    const kind = step.kind ?? 'delta';
    if (kind === 'start' || kind === 'end') {
      running = step.value;
      return { ...step, base: 0, bar: Math.max(step.value, 0), fill: CHART_COLORS[0], display: money(step.value) };
    }
    const from = running;
    running += step.value;
    return {
      ...step,
      base: Math.min(from, running),
      bar: Math.abs(step.value),
      fill: step.value <= 0 ? '#2E7D32' : '#E6007E',
      display: `${step.value > 0 ? '+' : '−'}${money(Math.abs(step.value))}`,
    };
  });
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 28, right: 8, left: 4, bottom: 8 }}>
        <CartesianGrid vertical={false} stroke={theme.palette.divider} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fontWeight: 600 }} interval={0} stroke={theme.palette.text.secondary} />
        <YAxis tickFormatter={(v) => money(v)} width={58} tick={{ fontSize: 11 }} stroke={theme.palette.text.secondary} />
        <Tooltip
          content={({ payload, label }) =>
            payload?.[0] ? <Tip rows={[{ k: String(label), v: money(Number(payload[0].payload.value)) }]} /> : null
          }
        />
        <Bar dataKey="base" stackId="a" fill="transparent" isAnimationActive={false} />
        <Bar dataKey="bar" stackId="a" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {rows.map((r, i) => (
            <Cell key={i} fill={r.fill} />
          ))}
          <LabelList dataKey="display" position="top" fontSize={10} fill={theme.palette.text.secondary} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function Mekko({ data }: { data: { label: string; total: number; series: Record<string, number> }[] }) {
  const keys = Array.from(new Set((data ?? []).flatMap((d) => Object.keys(d.series))));
  const grand = (data ?? []).reduce((s, d) => s + d.total, 0) || 1;
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
        {keys.map((k, i) => (
          <Typography key={k} variant="caption" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontWeight: 600 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: 0.5, bgcolor: CHART_COLORS[i % CHART_COLORS.length] }} />
            {k}
          </Typography>
        ))}
      </Box>
      <Box sx={{ display: 'flex', flex: 1, gap: 0.75, alignItems: 'stretch', minHeight: 0 }}>
        {(data ?? []).map((d) => (
          <Box key={d.label} sx={{ flex: `${Math.max(d.total / grand, 0.08)} 1 0`, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: 1.25, overflow: 'hidden' }}>
              {keys.map((k, i) => {
                const v = d.series[k] ?? 0;
                const h = d.total ? (v / d.total) * 100 : 0;
                if (!h) return null;
                return (
                  <Box key={k} title={`${d.label} · ${k}: ${money(v)}`} sx={{ height: `${h}%`, bgcolor: CHART_COLORS[i % CHART_COLORS.length], minHeight: 6 }} />
                );
              })}
            </Box>
            <Typography variant="caption" sx={{ mt: 0.75, textAlign: 'center', fontWeight: 700 }} noWrap>
              {d.label}
            </Typography>
            <Typography variant="caption" sx={{ textAlign: 'center', color: 'text.secondary' }}>
              {money(d.total)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function Gantt({ data }: { data: { label: string; start: string; end: string }[] }) {
  if (!data?.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No stage path on this deal.
      </Typography>
    );
  }
  const starts = data.map((d) => new Date(d.start).getTime());
  const ends = data.map((d) => new Date(d.end).getTime());
  const min = Math.min(...starts);
  const max = Math.max(...ends, min + 1);
  const span = max - min;
  return (
    <Box>
      {data.map((d, i) => {
        const a = new Date(d.start).getTime();
        const b = new Date(d.end).getTime();
        const left = ((a - min) / span) * 100;
        const width = Math.max(((b - a) / span) * 100, 6);
        return (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="caption" sx={{ width: 128, flexShrink: 0, fontWeight: 600 }} noWrap>
              {d.label}
            </Typography>
            <Box sx={{ flex: 1, height: 18, bgcolor: 'action.hover', borderRadius: 1, position: 'relative' }}>
              <Box sx={{ position: 'absolute', left: `${left}%`, width: `${width}%`, height: '100%', bgcolor: CHART_COLORS[i % CHART_COLORS.length], borderRadius: 1 }} />
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

function FunnelBars({ data }: { data: { label: string; acv: number; count?: number }[] }) {
  const theme = useTheme();
  const rows = (data ?? []).filter((d) => d.acv > 0 || (d.count ?? 0) > 0);
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 48, left: 8, bottom: 8 }}>
        <CartesianGrid horizontal={false} stroke={theme.palette.divider} />
        <XAxis type="number" tickFormatter={(v) => money(v)} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="label" width={128} tick={{ fontSize: 11, fontWeight: 600 }} />
        <Tooltip
          content={({ payload }) => {
            const p = payload?.[0]?.payload as { label: string; acv: number; count?: number } | undefined;
            if (!p) return null;
            return <Tip rows={[{ k: p.label, v: money(p.acv) }, ...(p.count != null ? [{ k: 'Deals', v: n(p.count) }] : [])]} />;
          }}
        />
        <Bar dataKey="acv" radius={[0, 6, 6, 0]} isAnimationActive={false}>
          {rows.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
          <LabelList dataKey="acv" position="right" formatter={(v: number) => money(v)} fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function TreeLeaf(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  value?: number;
  index?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, value, index = 0 } = props;
  if (width < 4 || height < 4) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={CHART_COLORS[index % CHART_COLORS.length]} stroke="#fff" strokeWidth={2} rx={4} />
      {width > 72 && height > 28 && (
        <>
          <text x={x + 8} y={y + 18} fill="#fff" fontSize={11} fontWeight={700}>
            {String(name ?? '').slice(0, 18)}
          </text>
          <text x={x + 8} y={y + 34} fill="rgba(255,255,255,.9)" fontSize={11}>
            {money(Number(value ?? 0))}
          </text>
        </>
      )}
    </g>
  );
}

export function ChartRenderer({ spec, height = 300, showTitle = false }: { spec: ChartSpec; height?: number; showTitle?: boolean }) {
  const theme = useTheme();
  const type = spec.type;
  const data = (spec.data ?? []) as never[];

  return (
    <Box sx={{ width: '100%', height, minHeight: height }}>
      {showTitle && spec.title && (
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {spec.title}
        </Typography>
      )}
      {type === 'heatmap' && <Heat spec={spec} />}
      {type === 'waterfall' && <Waterfall data={spec.data as { label: string; value: number; kind?: string }[]} />}
      {type === 'mekko' && <Mekko data={spec.data as { label: string; total: number; series: Record<string, number> }[]} />}
      {type === 'gantt' && <Gantt data={(spec.data as { label: string; start: string; end: string }[]) ?? []} />}
      {type === 'funnel' && <FunnelBars data={data as { label: string; acv: number; count?: number }[]} />}
      {type === 'combo' && (
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid vertical={false} stroke={theme.palette.divider} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} tickFormatter={(v: string) => String(v).slice(5)} />
            <YAxis tickFormatter={(v) => money(v)} width={56} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => money(v)} />
            <Legend iconType="circle" />
            <Bar dataKey="won" fill={CHART_COLORS[0]} name="Won" radius={[4, 4, 0, 0]} />
            <Bar dataKey="pipeline" fill={CHART_COLORS[2]} name="Open" radius={[4, 4, 0, 0]} />
            <Line dataKey="budget" stroke={CHART_COLORS[1]} name="Plan" strokeWidth={2.4} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
      {type === 'bubble' && (
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 12, right: 16, left: 4, bottom: 12 }}>
            <CartesianGrid stroke={theme.palette.divider} />
            <XAxis dataKey="x" name="Age (days)" tick={{ fontSize: 11 }} label={{ value: 'Age (days)', position: 'bottom', offset: 0, fontSize: 11 }} />
            <YAxis dataKey="y" name="Confidence" tick={{ fontSize: 11 }} unit="%" width={46} />
            <ZAxis dataKey="z" range={[60, 380]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ payload }) => {
                const p = payload?.[0]?.payload as { name?: string; x: number; y: number; z: number; stage?: string } | undefined;
                if (!p) return null;
                return (
                  <Tip
                    rows={[
                      { k: 'Deal', v: String(p.name ?? '') },
                      { k: 'Age', v: `${p.x}d` },
                      { k: 'Confidence', v: `${p.y}%` },
                      { k: 'ACV', v: money(p.z) },
                    ]}
                  />
                );
              }}
            />
            <Scatter data={data} fill={CHART_COLORS[0]} fillOpacity={0.75} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
      {type === 'treemap' && (
        <ResponsiveContainer>
          <Treemap data={data} dataKey="value" nameKey="name" stroke="#fff" content={<TreeLeaf />} isAnimationActive={false} />
        </ResponsiveContainer>
      )}
      {type === 'sankey' && spec.nodes && spec.links && (
        <ResponsiveContainer>
          <Sankey
            data={{ nodes: spec.nodes, links: spec.links }}
            nodePadding={22}
            nodeWidth={12}
            margin={{ left: 8, right: 120, top: 12, bottom: 12 }}
          >
            <Tooltip formatter={(v: number) => money(v)} />
          </Sankey>
        </ResponsiveContainer>
      )}
      {type === 'bar' && (
        <ResponsiveContainer>
          <BarChart
            data={(data as { label?: string; acv?: number; name?: string; value?: number }[]).map((r) => ({
              label: r.label ?? r.name,
              acv: r.acv ?? r.value,
            }))}
            margin={{ top: 8, right: 8, left: 4, bottom: 28 }}
          >
            <CartesianGrid vertical={false} stroke={theme.palette.divider} />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} angle={-28} textAnchor="end" height={48} />
            <YAxis tickFormatter={(v) => money(v)} width={56} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => money(v)} />
            <Bar dataKey="acv" fill={CHART_COLORS[0]} radius={[5, 5, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Box>
  );
}

