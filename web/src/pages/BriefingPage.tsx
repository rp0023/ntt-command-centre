import { Box, Button } from '@mui/material';
import { PageHeader } from '@/components/layout/PageHeader';
import { ChartCard } from '@/components/charts/ChartCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { useView } from '@/hooks/useView';
import type { ChartSpec } from '@/types';

export default function BriefingPage() {
  const { data, status, error, reload } = useView('brief');
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;
  const charts = data.charts as Record<string, unknown>;

  return (
    <Box>
      <PageHeader
        title="Review pack"
        actions={
          <Button variant="outlined" className="ntt-no-print" onClick={() => window.print()}>
            Print
          </Button>
        }
      />
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
        <ChartCard title="Coverage bridge" spec={{ type: 'waterfall', data: charts.waterfall } as ChartSpec} />
        <ChartCard title="Stage mix" spec={{ type: 'funnel', data: charts.funnel } as ChartSpec} />
        <ChartCard title="Won vs plan" spec={{ type: 'combo', data: charts.combo } as ChartSpec} />
        <ChartCard title="LOB mix" spec={{ type: 'bar', data: charts.byLob } as ChartSpec} />
      </Box>
    </Box>
  );
}
