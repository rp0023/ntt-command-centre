import { Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import type { ActionItem } from '@/types';
import { money } from '@/utils/format';
import { useAppDispatch } from '@/app/store/hooks';
import { setSelectedOpportunity } from '@/app/store/uiSlice';

export function ActionCard({ item, index }: { item: ActionItem; index: number }) {
  const dispatch = useAppDispatch();
  return (
    <Card sx={{ cursor: item.opportunityCode ? 'pointer' : 'default' }} onClick={() => item.opportunityCode && dispatch(setSelectedOpportunity(item.opportunityCode))}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }}>
          <Chip size="small" label={index + 1} color="primary" />
          <Chip size="small" label={item.urgency.replace('_', ' ')} variant="outlined" />
          <Typography variant="caption" sx={{ ml: 'auto', fontWeight: 700 }}>
            {money(item.value)}
          </Typography>
        </Stack>
        <Typography variant="subtitle2">{item.title}</Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          {item.why}
        </Typography>
        <Typography variant="caption" display="block" sx={{ mt: 0.75, color: 'primary.main', fontWeight: 700 }}>
          {item.cta} · {item.owner}
        </Typography>
      </CardContent>
    </Card>
  );
}
