import { useState } from 'react';
import { Box, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import { PageHeader } from '@/components/layout/PageHeader';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { ChartCard } from '@/components/charts/ChartCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { useView } from '@/hooks/useView';
import { useAppDispatch } from '@/app/store/hooks';
import { setSelectedOpportunity } from '@/app/store/uiSlice';
import { n } from '@/utils/format';
import { DataGrid } from '@/components/tables/DataGrid';

export default function AnomaliesPage() {
  const dispatch = useAppDispatch();
  const { data, status, error, reload } = useView('anomalies');
  const [category, setCategory] = useState<string>('all');
  const [demoOnly, setDemoOnly] = useState(false);
  if (status === 'loading' && !data) return <RouteFallback />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;

  const source = data.anomalySource;
  const catalog = (data.anomalyCatalog ?? []) as {
    type: string;
    label: string;
    category: string;
    meaning: string;
    action: string;
    count: number;
  }[];
  const items = ((data.anomalies as Record<string, unknown>[]) ?? []).filter((a) => {
    if (category !== 'all' && String(a.category) !== category) return false;
    if (demoOnly && !a.demo_priority) return false;
    return true;
  });
  const categories = ['all', ...Array.from(new Set(catalog.map((c) => c.category)))];
  const catalogInView = catalog.filter((c) => (category === 'all' || c.category === category) && c.count > 0);

  return (
    <Box>
      <PageHeader title="Risk desk" />
      <FilterPanel />
      {source && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {source.file}: {n(source.rowsInScope)} of {n(source.rowsInFile)} rows in this scope. {n(source.matchedToExcel)} joined to Opportunities.xlsx, {n(source.unmatchedToExcel)} unmatched.
        </Typography>
      )}
      <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mb: 2 }}>
        {categories.map((c) => (
          <Chip
            key={c}
            label={c === 'all' ? 'All' : c}
            color={category === c ? 'primary' : 'default'}
            onClick={() => setCategory(c)}
            variant={category === c ? 'filled' : 'outlined'}
          />
        ))}
        <Chip
          label="Demo priority"
          color={demoOnly ? 'secondary' : 'default'}
          onClick={() => setDemoOnly((v) => !v)}
          variant={demoOnly ? 'filled' : 'outlined'}
        />
      </Stack>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '280px 1fr' }, mb: 2 }}>
        <Card>
          <CardContent>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Types in this file
            </Typography>
            <Stack spacing={1.25} sx={{ maxHeight: 420, overflow: 'auto' }}>
              {catalogInView.map((c) => (
                <Box key={c.type}>
                  <Typography variant="caption" sx={{ fontWeight: 800 }}>
                    {c.label} · {c.count}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {c.meaning}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
        <ChartCard title="Flagged rows">
          <Box sx={{ maxHeight: 640, overflow: 'auto' }}>
            <DataGrid
              rows={items}
              columns={[
                { key: 'id', label: 'Id' },
                { key: 'entity_type', label: 'Entity' },
                { key: 'label', label: 'Name' },
                { key: 'type', label: 'Type' },
                { key: 'severity_score', label: 'Score' },
                { key: 'evidence', label: 'Evidence' },
                { key: 'action', label: 'Action' },
                { key: 'value', label: 'GP', money: true },
              ]}
              onRow={(r) => r.opportunity_code && dispatch(setSelectedOpportunity(String(r.opportunity_code)))}
            />
          </Box>
        </ChartCard>
      </Box>
    </Box>
  );
}
