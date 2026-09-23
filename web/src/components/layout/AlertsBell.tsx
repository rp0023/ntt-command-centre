import { useState } from 'react';
import { Badge, Chip, Divider, IconButton, Popover, Stack, Tooltip, Typography } from '@mui/material';
import NotificationsRoundedIcon from '@mui/icons-material/NotificationsRounded';
import { api } from '@/services/api';
import { useAsync } from '@/hooks/useAsync';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { setSelectedOpportunity } from '@/app/store/uiSlice';
import { money } from '@/utils/format';

export function AlertsBell() {
  const persona = useAppSelector((s) => s.persona.current);
  const dispatch = useAppDispatch();
  const { data } = useAsync(() => api.alerts(persona), [persona]);
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const items = data?.items ?? [];
  const high = items.filter((e) => e.severity === 'critical' || e.severity === 'high').length;

  return (
    <>
      <Tooltip title="Pipeline exceptions">
        <IconButton onClick={(e) => setAnchor(e.currentTarget)} aria-label="Alerts">
          <Badge badgeContent={items.length} color={high > 0 ? 'error' : 'primary'} max={99}>
            <NotificationsRoundedIcon />
          </Badge>
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 420, maxWidth: '94vw', borderRadius: 3, mt: 1 } } }}
      >
        <Stack direction="row" alignItems="center" spacing={1} sx={{ px: 2, pt: 1.5, pb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Exceptions
          </Typography>
          {high > 0 && <Chip size="small" color="error" label={`${high} high`} />}
        </Stack>
        <Divider />
        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2.5, textAlign: 'center' }}>
            Nothing flagged in this persona’s scope.
          </Typography>
        ) : (
          <Stack sx={{ maxHeight: 420, overflowY: 'auto', py: 0.5 }}>
            {items.map((e) => (
              <Stack
                key={e.id}
                spacing={0.25}
                onClick={() => {
                  dispatch(setSelectedOpportunity(e.opportunityCode));
                  setAnchor(null);
                }}
                sx={{ px: 2, py: 1.1, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
              >
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {e.title}
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>
                    {money(e.value)}
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {e.subtitle}
                </Typography>
              </Stack>
            ))}
          </Stack>
        )}
      </Popover>
    </>
  );
}
