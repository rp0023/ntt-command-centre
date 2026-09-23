import { Box, Chip, CircularProgress, Divider, Drawer, IconButton, Stack, Typography } from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { closeDrawer } from '@/app/store/uiSlice';
import { api } from '@/services/api';
import { useAsync } from '@/hooks/useAsync';
import { money, pct } from '@/utils/format';
import { ChartRenderer } from '@/components/charts/ChartRenderer';

export function DrawerHost() {
  const dispatch = useAppDispatch();
  const code = useAppSelector((s) => s.ui.selectedOpportunityId);
  const persona = useAppSelector((s) => s.persona.current);
  const { data, status } = useAsync(() => (code ? api.opportunity(code, persona) : Promise.resolve(null)), [code, persona]);
  const open = Boolean(code);
  const opp = (data?.opportunity ?? {}) as Record<string, unknown>;

  return (
    <Drawer anchor="right" open={open} onClose={() => dispatch(closeDrawer())} PaperProps={{ sx: { width: { xs: '100%', sm: 480, md: 560 } } }}>
      <Box sx={{ p: { xs: 2, sm: 2.5 }, pt: { xs: 9, sm: 10 }, position: 'relative' }}>
        <IconButton onClick={() => dispatch(closeDrawer())} sx={{ position: 'absolute', top: { xs: 64, sm: 72 }, right: 8 }} aria-label="Close">
          <CloseRoundedIcon />
        </IconButton>
        {status === 'loading' && <CircularProgress />}
        {opp && code && (
          <Stack spacing={1.5}>
            <Typography variant="h6">{String(opp.opportunity_name ?? code)}</Typography>
            <Typography variant="body2" color="text.secondary">
              {String(opp.account_name ?? '')} · {String(opp.owner ?? '')}
            </Typography>
            <Stack direction="row" gap={1} flexWrap="wrap">
              <Chip size="small" label={String(opp.stage ?? '')} />
              <Chip size="small" label={String(opp.risk_band ?? '')} color={opp.risk_band === 'high_risk' ? 'error' : 'default'} />
              <Chip size="small" label={money(Number(opp.acv_revenue))} />
              <Chip size="small" label={`Close p ${Number(opp.close_probability ?? 0)}`} />
            </Stack>
            <Typography variant="body2">{String(opp.risk_drivers ?? '')}</Typography>
            <Divider />
            <Typography variant="subtitle2">Lines</Typography>
            {(data?.lines as Record<string, unknown>[] | undefined)?.map((ln) => (
              <Stack key={String(ln.line_code)} direction="row" justifyContent="space-between">
                <Typography variant="caption">
                  {String(ln.lob)} · {String(ln.portfolio)}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  {money(Number(ln.acv_revenue))} · GM {pct(Number(ln.gm_pct) * 100)}
                </Typography>
              </Stack>
            ))}
            <Divider />
            <Typography variant="subtitle2">Stage movement</Typography>
            <ChartRenderer spec={{ type: 'gantt', title: 'Stage path', data: data?.gantt }} height={180} />
            <Typography variant="subtitle2">Anomalies</Typography>
            {(data?.anomalies as Record<string, unknown>[] | undefined)?.length
              ? (data?.anomalies as Record<string, unknown>[]).map((a) => (
                  <Box key={String(a.id)} sx={{ p: 1.25, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {String(a.id)} · {String(a.type)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {String(a.evidence ?? a.reason ?? '')}
                    </Typography>
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      {String(a.action ?? '')}
                    </Typography>
                  </Box>
                ))
              : (
                <Typography variant="caption" color="text.secondary">
                  No rows in Client_Anomaly_Report.csv for this opportunity.
                </Typography>
              )}
          </Stack>
        )}
      </Box>
    </Drawer>
  );
}
