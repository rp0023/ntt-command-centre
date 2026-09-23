import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import type { SvgIconComponent } from '@mui/icons-material';

export function KpiCard({
  label,
  value,
  hint,
  intent = 'neutral',
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  intent?: 'positive' | 'negative' | 'risk' | 'neutral';
  icon?: SvgIconComponent;
}) {
  const theme = useTheme();
  const map = { positive: theme.palette.success.main, negative: theme.palette.error.main, risk: theme.palette.error.main, neutral: theme.palette.primary.main };
  const main = map[intent];
  return (
    <Card sx={{ height: '100%', borderLeft: `4px solid ${main}`, minWidth: 0 }}>
      <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
        <Stack direction="row" justifyContent="space-between">
          <Typography variant="caption" sx={{ letterSpacing: '0.08em', textTransform: 'uppercase', color: 'text.secondary' }}>
            {label}
          </Typography>
          {Icon && (
            <Box sx={{ width: 34, height: 34, borderRadius: 2, display: 'grid', placeItems: 'center', bgcolor: alpha(main, 0.12), color: main }}>
              <Icon sx={{ fontSize: 19 }} />
            </Box>
          )}
        </Stack>
        <Typography variant="h5" sx={{ mt: 1, fontWeight: 700, wordBreak: 'break-word' }}>
          {value}
        </Typography>
        {hint && (
          <Typography variant="caption" color="text.secondary">
            {hint}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
