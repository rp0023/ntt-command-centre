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

export default function BookPage() {
  const dispatch = useAppDispatch();
  const { data, status, error, reload } = useView('book');
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <Box>
      <PageHeader title="Open book" />
      <FilterPanel />
      <ChartCard title="Deals">
        <DataGrid
          rows={(data.opportunities as Record<string, unknown>[]) ?? []}
          columns={[
            { key: 'account_name', label: 'Account' },
            { key: 'opportunity_name', label: 'Opportunity' },
            { key: 'owner', label: 'Owner' },
            { key: 'stage', label: 'Stage' },
            { key: 'forecast_category', label: 'Forecast' },
            { key: 'risk_band', label: 'Risk' },
            { key: 'close_probability', label: 'Close p' },
            { key: 'acv_revenue', label: 'ACV', money: true },
            { key: 'close_date', label: 'Close' },
          ]}
          onRow={(r) => dispatch(setSelectedOpportunity(String(r.opportunity_code)))}
        />
      </ChartCard>
    </Box>
  );
}
