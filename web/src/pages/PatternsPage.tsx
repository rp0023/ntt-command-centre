import { Box } from '@mui/material';
import { PageHeader } from '@/components/layout/PageHeader';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { ChartCard } from '@/components/charts/ChartCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { useView } from '@/hooks/useView';
import { useAppDispatch } from '@/app/store/hooks';
import { setSelectedOpportunity } from '@/app/store/uiSlice';
import { DataGrid } from '@/components/tables/DataGrid';
import type { ChartSpec } from '@/types';

export default function PatternsPage() {
  const dispatch = useAppDispatch();
  const { data, status, error, reload } = useView('patterns');
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;
  const charts = data.charts as Record<string, unknown>;
  const rows = ((data.anomalies as Record<string, unknown>[]) ?? []).filter((a) => String(a.category) === 'Rep Behavior');

  return (
    <Box>
      <PageHeader title="Coaching" />
      <FilterPanel />
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, mb: 2 }}>
        <ChartCard title="Open book by owner" spec={{ type: 'bar', data: charts.byOwner } as ChartSpec} />
        <ChartCard title="LOB × order type" spec={{ type: 'mekko', data: charts.mekko } as ChartSpec} />
      </Box>
      <ChartCard title="Rep Behavior from client report">
        <DataGrid
          rows={rows}
          columns={[
            { key: 'id', label: 'Id' },
            { key: 'label', label: 'Rep' },
            { key: 'type', label: 'Type' },
            { key: 'severity_score', label: 'Score' },
            { key: 'evidence', label: 'Evidence' },
            { key: 'action', label: 'Action' },
            { key: 'value', label: 'GP', money: true },
          ]}
          onRow={(r) => r.opportunity_code && dispatch(setSelectedOpportunity(String(r.opportunity_code)))}
        />
      </ChartCard>
    </Box>
  );
}
