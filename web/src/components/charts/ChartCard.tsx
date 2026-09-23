import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded';
import OpenInFullRoundedIcon from '@mui/icons-material/OpenInFullRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import type { ReactNode } from 'react';
import type { AskResult, ChartSpec } from '@/types';
import { ChartRenderer } from './ChartRenderer';
import { api } from '@/services/api';
import { useAppSelector } from '@/app/store/hooks';
import { chartPrompts } from '@/constants/prompts';

function promptSlot(text: string): 'Main takeaway' | 'What looks off' | 'What should I do next' | null {
  const t = text.toLowerCase();
  if (t.includes('takeaway') || t.includes('main')) return 'Main takeaway';
  if (t.includes('looks off') || t.includes('off')) return 'What looks off';
  if (t.includes('next') || t.includes('should i do')) return 'What should I do next';
  return null;
}

export function ChartCard({
  title,
  spec,
  children,
  height = 300,
}: {
  title: string;
  spec?: ChartSpec;
  children?: ReactNode;
  height?: number;
}) {
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down('sm'));
  const persona = useAppSelector((s) => s.persona.current);
  const filters = useAppSelector((s) => s.filters.value);
  const pack = useAppSelector((s) => s.ask.pack);
  const [askOpen, setAskOpen] = useState(false);
  const [wide, setWide] = useState(false);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [insight, setInsight] = useState<AskResult | null>(null);
  const chartH = compact ? Math.min(height, 220) : height;

  const fromPack = (q: string): AskResult | null => {
    const slot = promptSlot(q);
    const block = pack?.charts?.[title] || pack?.charts?.[title.toLowerCase()];
    if (slot && block?.[slot]) {
      const item = block[slot];
      return {
        answer: item.answer,
        tldr: item.tldr,
        chart: (item.chart as ChartSpec) || spec || { type: 'bar', data: [] },
        provider: 'precomputed',
        suggestions: [],
      };
    }
    return null;
  };

  const runAsk = async (q: string) => {
    const query = q.trim();
    if (!query || thinking) return;
    const cached = fromPack(query);
    if (cached) {
      setInsight(cached);
      setInput('');
      return;
    }
    setThinking(true);
    try {
      const result = await api.ask(`Using only the chart “${title}”: ${query}`, persona, filters);
      setInsight(result);
      setInput('');
    } finally {
      setThinking(false);
    }
  };

  const body = spec ? <ChartRenderer spec={spec} height={chartH} /> : children;

  const askPanel = (
    <Box sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
      <Stack direction="row" gap={0.75} flexWrap="wrap" sx={{ mb: 1 }}>
        {chartPrompts(title).map((p) => (
          <Button
            key={p.text}
            size="small"
            variant="outlined"
            startIcon={<p.icon sx={{ fontSize: 16 }} />}
            onClick={() => runAsk(p.text)}
            disabled={thinking}
            sx={{ textTransform: 'none', borderRadius: 99 }}
          >
            {p.text.replace(` from ${title}?`, '').replace(` in ${title}?`, '').replace(` on ${title}?`, '')}
          </Button>
        ))}
      </Stack>
      <Stack direction="row" spacing={1}>
        <TextField
          size="small"
          fullWidth
          placeholder="Ask this chart…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runAsk(input)}
        />
        <IconButton color="primary" onClick={() => runAsk(input)} disabled={thinking} aria-label="Send">
          {thinking ? <CircularProgress size={18} /> : <SendRoundedIcon />}
        </IconButton>
      </Stack>
      {insight && (
        <Box sx={{ mt: 1.25 }}>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {insight.answer}
          </Typography>
          {insight.chart?.type && (
            <Box sx={{ mt: 1.5 }}>
              <ChartRenderer spec={insight.chart} height={compact ? 200 : 240} />
            </Box>
          )}
        </Box>
      )}
    </Box>
  );

  return (
    <>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', '&:last-child': { pb: 2 } }}>
          <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 1.25 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, flex: 1, minWidth: 0 }} noWrap>
              {title}
            </Typography>
            <Tooltip title="Ask about this chart">
              <IconButton
                size="small"
                color={askOpen ? 'primary' : 'default'}
                onClick={() => setAskOpen((v) => !v)}
                aria-label="Ask about this chart"
              >
                <AutoAwesomeRoundedIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Expand">
              <IconButton size="small" onClick={() => setWide(true)} aria-label="Expand chart">
                <OpenInFullRoundedIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <Box sx={{ flex: 1, minHeight: spec ? chartH : 0, minWidth: 0, overflow: 'auto' }}>{body}</Box>
          <Collapse in={askOpen} unmountOnExit>
            {askPanel}
          </Collapse>
        </CardContent>
      </Card>

      <Dialog open={wide} onClose={() => setWide(false)} maxWidth="xl" fullWidth fullScreen={compact}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', pr: 1 }}>
          <Typography variant="h6" sx={{ flex: 1, fontWeight: 700 }} noWrap>
            {title}
          </Typography>
          <IconButton onClick={() => setWide(false)} aria-label="Close">
            <CloseRoundedIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {spec ? <ChartRenderer spec={spec} height={compact ? 280 : 520} /> : <Box sx={{ minHeight: 240 }}>{children}</Box>}
          {askPanel}
        </DialogContent>
      </Dialog>
    </>
  );
}
