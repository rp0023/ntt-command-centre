import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import PublicRounded from '@mui/icons-material/PublicRounded';
import SavingsRounded from '@mui/icons-material/SavingsRounded';
import SpeedRounded from '@mui/icons-material/SpeedRounded';
import EmojiEventsRounded from '@mui/icons-material/EmojiEventsRounded';
import { PageHeader } from '@/components/layout/PageHeader';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { KpiCard } from '@/components/cards/KpiCard';
import { ChartCard } from '@/components/charts/ChartCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { useView } from '@/hooks/useView';
import { money, n, pct } from '@/utils/format';
import type { ChartSpec } from '@/types';

export default function BriefPage() {
  const { data, status, error, reload } = useView('brief');
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;
  const k = data.kpis;
  const charts = data.charts as Record<string, unknown>;
  const heat = charts.heatmap as { rows: string[]; cols: string[]; values: number[][] };

  return (
    <Box>
      <PageHeader title="Executive Brief" />
      <FilterPanel />
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={1}>
            {data.tldr.map((line, i) => (
              <Typography key={i} variant="h6" sx={{ fontWeight: i === 0 ? 800 : 500, fontSize: i === 0 ? 22 : 16 }}>
                {line}
              </Typography>
            ))}
          </Stack>
        </CardContent>
      </Card>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, mb: 3 }}>
        <KpiCard label="Won ACV" value={money(k.wonAcv)} hint={`${n(k.wonOpportunities)} deals`} icon={EmojiEventsRounded} intent="positive" />
        <KpiCard label="Open ACV" value={money(k.pipelineAcv)} hint={`${n(k.openOpportunities)} live`} icon={PublicRounded} />
        <KpiCard label="Coverage" value={`${k.coverage.toFixed(1)}×`} hint={money(k.budgetAcv)} intent={k.coverage < 3 ? 'risk' : 'positive'} icon={SpeedRounded} />
        <KpiCard label="GM" value={pct(k.gmPct)} hint={`Services ${pct(k.servicesGmPct)}`} icon={SavingsRounded} />
      </Box>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, mb: 2 }}>
        <ChartCard title="Coverage bridge" spec={{ type: 'waterfall', data: charts.waterfall } as ChartSpec} />
        <ChartCard title="Won vs open vs plan" spec={{ type: 'combo', data: charts.combo } as ChartSpec} />
        <ChartCard title="Industry mix" spec={{ type: 'treemap', data: charts.treemap } as ChartSpec} />
        <ChartCard title="Order type to stage" spec={{ type: 'sankey', ...(charts.sankey as object) } as ChartSpec} height={320} />
      </Box>
      <ChartCard title="LOB × portfolio" spec={{ type: 'heatmap', ...heat } as ChartSpec} height={240} />
    </Box>
  );
}
