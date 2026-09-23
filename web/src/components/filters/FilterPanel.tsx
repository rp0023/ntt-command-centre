import { useEffect, useState } from 'react';
import { Button, Card, CardContent, Stack, TextField } from '@mui/material';
import ClearRoundedIcon from '@mui/icons-material/ClearRounded';
import FilterAltRoundedIcon from '@mui/icons-material/FilterAltRounded';
import { MultiSelectFilter } from './MultiSelectFilter';
import { api } from '@/services/api';
import { useAsync } from '@/hooks/useAsync';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { clearFilters, countActiveFilters, patchFilters } from '@/app/store/filtersSlice';

export function FilterPanel() {
  const dispatch = useAppDispatch();
  const persona = useAppSelector((s) => s.persona.current);
  const filters = useAppSelector((s) => s.filters.value);
  const { data: meta } = useAsync(() => api.meta(persona), [persona]);
  const opts = (meta?.filters ?? {}) as Record<string, string[]>;
  const [searchDraft, setSearchDraft] = useState(filters.search ?? '');
  const debouncedSearch = useDebouncedValue(searchDraft, 350);
  useEffect(() => {
    if ((filters.search ?? '') !== debouncedSearch) dispatch(patchFilters({ search: debouncedSearch || undefined }));
  }, [debouncedSearch]);
  useEffect(() => setSearchDraft(filters.search ?? ''), [filters.search]);

  if (!opts.lobs) return null;
  const active = countActiveFilters(filters);

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
        <Stack direction="row" alignItems="flex-start" useFlexGap flexWrap="wrap" gap={1}>
          <Stack direction="row" alignItems="center" useFlexGap flexWrap="wrap" gap={1.25} sx={{ flexGrow: 1, minWidth: 0, pt: 1.75, pb: 0.5 }}>
            <FilterAltRoundedIcon fontSize="small" sx={{ color: 'primary.main', flexShrink: 0 }} />
            <MultiSelectFilter label="Country" options={opts.countries ?? []} value={filters.countries ?? []} onChange={(v) => dispatch(patchFilters({ countries: v }))} width={130} />
            <MultiSelectFilter label="LOB" options={opts.lobs ?? []} value={filters.lobs ?? []} onChange={(v) => dispatch(patchFilters({ lobs: v }))} width={160} />
            <MultiSelectFilter label="Portfolio" options={opts.portfolios ?? []} value={filters.portfolios ?? []} onChange={(v) => dispatch(patchFilters({ portfolios: v }))} width={170} />
            <MultiSelectFilter label="Stage" options={opts.stages ?? []} value={filters.stages ?? []} onChange={(v) => dispatch(patchFilters({ stages: v }))} width={170} />
            <MultiSelectFilter label="Forecast" options={opts.forecasts ?? []} value={filters.forecasts ?? []} onChange={(v) => dispatch(patchFilters({ forecasts: v }))} width={140} />
            <MultiSelectFilter label="Order type" options={opts.orderTypes ?? []} value={filters.orderTypes ?? []} onChange={(v) => dispatch(patchFilters({ orderTypes: v }))} width={150} />
            {persona !== 'sales' && (
              <MultiSelectFilter label="Owner" options={opts.owners ?? []} value={filters.owners ?? []} onChange={(v) => dispatch(patchFilters({ owners: v }))} width={170} />
            )}
            <TextField size="small" label="Search" value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} sx={{ minWidth: { xs: '100%', sm: 160 }, flex: { xs: '1 1 100%', sm: '0 0 auto' } }} />
          </Stack>
          {active > 0 && (
            <Button startIcon={<ClearRoundedIcon />} onClick={() => dispatch(clearFilters())} size="small">
              Clear
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
