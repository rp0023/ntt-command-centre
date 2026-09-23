import { Chip, Stack } from '@mui/material';
import FilterAltRoundedIcon from '@mui/icons-material/FilterAltRounded';
import { useAppSelector } from '@/app/store/hooks';
import { countActiveFilters } from '@/app/store/filtersSlice';

export function ScopeNote() {
  const filters = useAppSelector((s) => s.filters.value);
  const n = countActiveFilters(filters);
  if (n === 0) return null;
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Chip icon={<FilterAltRoundedIcon />} label={`${n} filter${n > 1 ? 's' : ''}`} color="primary" variant="outlined" size="small" />
    </Stack>
  );
}
