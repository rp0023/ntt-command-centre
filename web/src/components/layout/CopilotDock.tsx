import { useEffect, useRef, useState } from 'react';
import { Badge, Box, Button, CircularProgress, Fab, IconButton, Paper, Stack, TextField, Tooltip, Typography } from '@mui/material';
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { api } from '@/services/api';
import { useAppSelector } from '@/app/store/hooks';
import type { AskResult } from '@/types';
import { ChartRenderer } from '@/components/charts/ChartRenderer';
import { PROMPTS } from '@/constants/prompts';

export function CopilotDock() {
  const persona = useAppSelector((s) => s.persona.current);
  const filters = useAppSelector((s) => s.filters.value);
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [answers, setAnswers] = useState<{ id: string; query: string; result: AskResult }[]>([]);
  const bodyRef = useRef<HTMLDivElement>(null);
  const pack = useAppSelector((s) => s.ask.pack);
  const prompts = pack?.prompts?.length
    ? pack.prompts.map((p) => ({ text: p.text || '', answer: p.answer, chart: p.chart, tldr: p.tldr }))
    : PROMPTS[persona].map((p) => ({ text: p.text, answer: '', chart: undefined, tldr: '' }));

  useEffect(() => {
    setAnswers([]);
    setInput('');
    setThinking(false);
  }, [persona]);

  useEffect(() => {
    if (open) bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' });
  }, [answers, thinking, open]);

  const ask = async (q: string) => {
    const query = q.trim();
    if (!query || thinking) return;
    const ready = pack?.prompts?.find((p) => p.text === query);
    if (ready?.answer) {
      setInput('');
      setAnswers((prev) => [
        ...prev,
        {
          id: `${Date.now()}`,
          query,
          result: {
            answer: ready.answer,
            tldr: ready.tldr,
            chart: ready.chart || { type: 'bar', data: [] },
            provider: 'precomputed',
            suggestions: [],
          },
        },
      ]);
      return;
    }
    setInput('');
    setThinking(true);
    try {
      const result = await api.ask(query, persona, filters);
      setAnswers((prev) => [...prev, { id: `${Date.now()}`, query, result }]);
    } finally {
      setThinking(false);
    }
  };

  if (!open) {
    return (
      <Tooltip title="Ask" placement="left">
        <Fab className="ntt-copilot-dock" color="primary" variant="extended" onClick={() => setOpen(true)} sx={{ position: 'fixed', bottom: { xs: 16, sm: 24 }, right: { xs: 16, sm: 24 }, zIndex: (t) => t.zIndex.drawer - 1, fontWeight: 700, boxShadow: 6, pb: 'env(safe-area-inset-bottom)' }}>
          <Badge color="error" variant="dot" invisible={answers.length === 0}>
            <AutoAwesomeRoundedIcon sx={{ mr: 1 }} />
          </Badge>
          Ask
        </Fab>
      </Tooltip>
    );
  }

  return (
    <Paper className="ntt-copilot-dock" elevation={8} sx={{ position: 'fixed', bottom: { xs: 12, sm: 24 }, right: { xs: 12, sm: 24 }, zIndex: (t) => t.zIndex.drawer + 2, width: { xs: 'calc(100vw - 24px)', sm: 440 }, height: { xs: 'min(640px, calc(100dvh - 88px))', sm: 640 }, maxHeight: 'calc(100dvh - 88px)', display: 'flex', flexDirection: 'column', borderRadius: 3, overflow: 'hidden' }}>
      <Stack direction="row" alignItems="center" sx={{ px: 2, py: 1.25, borderBottom: 1, borderColor: 'divider' }}>
        <AutoAwesomeRoundedIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 800, flex: 1 }}>
          Ask
        </Typography>
        <IconButton onClick={() => setOpen(false)} aria-label="Close">
          <CloseRoundedIcon />
        </IconButton>
      </Stack>
      <Box ref={bodyRef} sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {answers.length === 0 && !thinking && (
          <Stack spacing={1}>
            {prompts.map((p) => {
              const Icon = PROMPTS[persona].find((x) => x.text === p.text)?.icon;
              return (
                <Button
                  key={p.text}
                  variant="outlined"
                  startIcon={Icon ? <Icon /> : <AutoAwesomeRoundedIcon />}
                  onClick={() => ask(p.text)}
                  sx={{
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    textTransform: 'none',
                    borderRadius: 2,
                    py: 1.1,
                    px: 1.25,
                    fontWeight: 600,
                  }}
                >
                  {p.text}
                </Button>
              );
            })}
          </Stack>
        )}
        {answers.map((a) => (
          <Box key={a.id} sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 700 }}>
              {a.query}
            </Typography>
            <Typography variant="body2" sx={{ mb: 1.5, whiteSpace: 'pre-wrap' }}>
              {a.result.answer}
            </Typography>
            {a.result.chart && <ChartRenderer spec={a.result.chart} height={220} />}
          </Box>
        ))}
        {thinking && (
          <Stack direction="row" spacing={1} alignItems="center">
            <CircularProgress size={16} />
            <Typography variant="caption">Working…</Typography>
          </Stack>
        )}
      </Box>
      <Stack direction="row" spacing={1} sx={{ p: 1.5, borderTop: 1, borderColor: 'divider' }}>
        <TextField size="small" fullWidth placeholder="Ask…" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask(input)} />
        <IconButton color="primary" onClick={() => ask(input)} disabled={thinking}>
          <SendRoundedIcon />
        </IconButton>
      </Stack>
    </Paper>
  );
}
