import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import AccountTreeRounded from '@mui/icons-material/AccountTreeRounded';
import SavingsRounded from '@mui/icons-material/SavingsRounded';
import SpeedRounded from '@mui/icons-material/SpeedRounded';
import WarningAmberRounded from '@mui/icons-material/WarningAmberRounded';
import { PageHeader } from '@/components/layout/PageHeader';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { KpiCard } from '@/components/cards/KpiCard';
import { ActionCard } from '@/components/cards/ActionCard';
import { ChartCard } from '@/components/charts/ChartCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { useView } from '@/hooks/useView';
import { money, n, pct } from '@/utils/format';
import type { ChartSpec } from '@/types';

export default function CommandCentrePage() {
  const { data, status, error, reload } = useView('command');
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;
  const k = data.kpis;
  const charts = data.charts as Record<string, unknown>;

  return (
    <Box>
      <PageHeader title="Command Centre" />
      <FilterPanel />
      <Card sx={{ mb: 3, background: 'linear-gradient(135deg, rgba(0,103,177,.08), rgba(230,0,126,.05))' }}>
        <CardContent>
          <Stack spacing={0.75}>
            {data.tldr.map((line) => (
              <Typography key={line} variant="body2">
                {line}
              </Typography>
            ))}
          </Stack>
        </CardContent>
      </Card>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, mb: 3 }}>
        <KpiCard label="Open ACV" value={money(k.pipelineAcv)} hint={`${n(k.openOpportunities)} deals`} icon={AccountTreeRounded} />
        <KpiCard label="Past close" value={money(k.pastDueAcv)} hint={`${n(k.pastDueOpportunities)} deals`} intent="risk" icon={WarningAmberRounded} />
        <KpiCard label="Commit" value={money(k.commitAcv)} hint={`Best case ${money(k.bestCaseAcv)}`} icon={SpeedRounded} />
        <KpiCard label="Services GM" value={pct(k.servicesGmPct)} hint={`vs ${k.servicesGmTarget}%`} intent={k.servicesGmPct < k.servicesGmTarget ? 'negative' : 'positive'} icon={SavingsRounded} />
      </Box>
      <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 700 }}>
        This week
      </Typography>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, mb: 3 }}>
        {data.actions.map((a, i) => (
          <ActionCard key={a.id} item={a} index={i} />
        ))}
      </Box>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
        <ChartCard title="Stage mix" spec={{ type: 'funnel', data: charts.funnel } as ChartSpec} />
        <ChartCard title="Age vs confidence" spec={{ type: 'bubble', data: charts.bubble } as ChartSpec} />
      </Box>
    </Box>
  );
}
